"""Data model backed by a local SQLite database (<app folder>/StickyNotesDB/notes.db).

Everything is loaded into memory on start; every change is written straight through to SQLite.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from . import repeat
from .system import app_bundle, fallback_data_dir

LEGACY_NAME = "StickyNotesDee"         # folder name used by the first versions
DB_FOLDER = "StickyNotesDB"
OLD_DB_FOLDERS = ("DeeStickyNotesDB",)   # earlier names of DB_FOLDER, renamed automatically
DB_FILE = "notes.db"
SCHEMA_VERSION = 9
DEFAULT_FONT_SIZE = 10.5
DEFAULT_SATURATION = 0.5

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id          TEXT PRIMARY KEY,
    title       TEXT    NOT NULL DEFAULT 'Today',
    kind        TEXT    NOT NULL DEFAULT 'daily',
    color       TEXT    NOT NULL DEFAULT 'lemon',
    x           INTEGER,
    y           INTEGER,
    w           INTEGER NOT NULL DEFAULT 340,
    h           INTEGER NOT NULL DEFAULT 440,
    visible     INTEGER NOT NULL DEFAULT 1,
    pin         TEXT    NOT NULL DEFAULT 'desktop',
    completed   TEXT    NOT NULL DEFAULT 'strike',
    collapsed   INTEGER NOT NULL DEFAULT 0,
    font_family TEXT    NOT NULL DEFAULT '',
    font_size   REAL    NOT NULL DEFAULT 10.5,
    saturation  REAL    NOT NULL DEFAULT 0.5,
    deleted_at  TEXT,
    layouts     TEXT    NOT NULL DEFAULT '{}',
    style       TEXT    NOT NULL DEFAULT '3d',
    emoji       TEXT    NOT NULL DEFAULT '',
    header      TEXT    NOT NULL DEFAULT 'plain',
    background  TEXT    NOT NULL DEFAULT 'plain',
    color2      TEXT    NOT NULL DEFAULT '',
    checkbox    TEXT    NOT NULL DEFAULT 'circle',
    done_look   TEXT    NOT NULL DEFAULT 'strike',
    title_font  TEXT    NOT NULL DEFAULT '',
    text_color  TEXT    NOT NULL DEFAULT '',
    spacing     TEXT    NOT NULL DEFAULT 'normal'
);
CREATE TABLE IF NOT EXISTS tasks (
    id        TEXT PRIMARY KEY,
    note_id   TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    text      TEXT NOT NULL,
    done      INTEGER NOT NULL DEFAULT 0,
    archived  INTEGER NOT NULL DEFAULT 0,
    created   TEXT NOT NULL,
    done_at   TEXT,
    remind_at TEXT,
    reminded  INTEGER NOT NULL DEFAULT 0,
    "order"   REAL NOT NULL DEFAULT 0,
    deleted_at TEXT,
    pinned    INTEGER NOT NULL DEFAULT 0,
    repeat    TEXT NOT NULL DEFAULT '',
    repeat_from TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_note ON tasks(note_id);
CREATE INDEX IF NOT EXISTS idx_tasks_done_at ON tasks(done_at);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Upgrades for databases created by older versions: {new version: statements}.
MIGRATIONS = {
    2: ["ALTER TABLE notes ADD COLUMN font_family TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE notes ADD COLUMN font_size REAL NOT NULL DEFAULT 10.5"],
    3: ["ALTER TABLE notes ADD COLUMN saturation REAL NOT NULL DEFAULT 0.5"],
    4: ["ALTER TABLE notes ADD COLUMN deleted_at TEXT",
        "ALTER TABLE tasks ADD COLUMN deleted_at TEXT"],
    5: ["ALTER TABLE tasks ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0"],
    6: ["ALTER TABLE notes ADD COLUMN layouts TEXT NOT NULL DEFAULT '{}'"],
    7: ["ALTER TABLE tasks ADD COLUMN repeat TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN repeat_from TEXT"],
    8: ["ALTER TABLE notes ADD COLUMN style TEXT NOT NULL DEFAULT '3d'"],
    9: [f"ALTER TABLE notes ADD COLUMN {column} TEXT NOT NULL DEFAULT '{default}'" for column, default in (
        ("emoji", ""), ("header", "plain"), ("background", "plain"), ("color2", ""), ("checkbox", "circle"),
        ("done_look", "strike"), ("title_font", ""), ("text_color", ""), ("spacing", "normal"))],
}

# A note's look, in the groups that can be copied to other notes (see Controller.apply_to_all / copy_style).
LOOK_GROUPS = {
    "colour": ("color", "saturation", "color2", "text_color"),
    "style": ("style", "background", "header", "checkbox", "done_look", "spacing"),
    "font": ("font_family", "font_size", "title_font"),
}


def look_of(note, groups=tuple(LOOK_GROUPS)) -> dict:
    """The note's look (colour, card style, fonts...), as changes to give another note."""
    return {field: getattr(note, field) for group in groups for field in LOOK_GROUPS[group]}


def app_root() -> Path:
    """The folder the app lives in: next to the .exe when packaged, else the project folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def legacy_dir() -> Path:
    """Where the first (Windows-only) versions kept the database."""
    return Path(os.environ.get("APPDATA") or Path.home()) / LEGACY_NAME


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _current_db_folder() -> Path:
    """<app folder>/StickyNotesDB, first renaming a folder left by an earlier version (e.g. DeeStickyNotesDB).

    If the old folder can't be renamed (files in use), it keeps being used so no notes go missing.
    """
    target = app_root() / DB_FOLDER
    if target.exists():
        return target
    for name in OLD_DB_FOLDERS:
        old = app_root() / name
        if (old / DB_FILE).exists():
            try:
                old.rename(target)
                return target
            except OSError:
                return old
    return target


@lru_cache(maxsize=1)
def data_dir() -> Path:
    """<app folder>/StickyNotesDB, falling back to a per-user folder if the app folder is read-only.

    STICKYNOTES_DATA_DIR overrides it (used for testing against a throwaway database).
    """
    override = os.environ.get("STICKYNOTES_DATA_DIR")
    if override:
        candidates = [Path(override)]
    elif sys.platform == "darwin" and (getattr(sys, "frozen", False) or app_bundle() is not None):
        candidates = [fallback_data_dir()]   # never write inside an .app: it may be read-only or replaced
    else:
        candidates = [_current_db_folder(), fallback_data_dir()]
    for path in candidates:
        if _writable(path):
            return path
    raise OSError(f"No writable folder for the database (tried {', '.join(map(str, candidates))})")


def adopt_legacy_database(target: Path) -> Path:
    """Move notes from the old %APPDATA% location into `target`, once. Returns the database path to use.

    Uses SQLite's backup API so a database in WAL mode is copied consistently, into a temporary file that
    only takes `target`'s name once complete. The old file is renamed, not deleted, so it stays around as
    a safety copy. If the copy fails, the old location keeps being used rather than starting empty.
    """
    old = legacy_dir() / DB_FILE
    if target.exists() or not old.exists() or old.resolve() == target.resolve():
        return target
    partial = target.with_name(target.name + ".partial")
    try:
        with closing(sqlite3.connect(old)) as src, closing(sqlite3.connect(partial)) as dst:
            src.backup(dst)
        partial.replace(target)
    except (sqlite3.Error, OSError):
        partial.unlink(missing_ok=True)
        return old
    try:
        old.replace(old.with_name("notes.moved-to-app-folder.db"))
    except OSError:
        pass  # still in use somewhere; the new copy is used from now on regardless
    return target


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def from_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Task:
    note_id: str
    text: str
    id: str = field(default_factory=new_id)
    done: bool = False
    archived: bool = False          # hidden from the note, still in history
    created: str = field(default_factory=lambda: to_iso(now()))
    done_at: str | None = None
    remind_at: str | None = None
    reminded: bool = False
    order: float = 0.0
    deleted_at: str | None = None   # set while it sits in the Recycle Bin
    pinned: bool = False            # kept at the top of its note
    repeat: str = ""                # how the reminder repeats, e.g. "15min", "1d", "weekdays" (see repeat.py)
    repeat_from: str | None = None  # when a repeating reminder's series began

    @property
    def created_date(self) -> date:
        return (from_iso(self.created) or now()).date()

    @property
    def done_dt(self) -> datetime | None:
        return from_iso(self.done_at)

    @property
    def remind_dt(self) -> datetime | None:
        return from_iso(self.remind_at)

    @property
    def deleted_dt(self) -> datetime | None:
        return from_iso(self.deleted_at)

    @property
    def repeat_from_dt(self) -> datetime | None:
        return from_iso(self.repeat_from)

    def next_reminder(self, after: datetime) -> datetime | None:
        """For a repeating reminder: its first time later than `after`."""
        start = self.repeat_from_dt or self.remind_dt
        return repeat.next_after(self.repeat, start, after) if self.repeat and start else None


@dataclass
class Note:
    id: str = field(default_factory=new_id)
    title: str = "Today"
    kind: str = "daily"             # daily | checklist
    color: str = "lemon"            # a palette name from theme.py, or a custom colour as "#RRGGBB"
    x: int | None = None
    y: int | None = None
    w: int = 340
    h: int = 440
    visible: bool = True
    pin: str = "desktop"            # desktop | top
    completed: str = "strike"       # strike | hide
    collapsed: bool = False
    font_family: str = ""           # "" = the app's default UI font
    font_size: float = DEFAULT_FONT_SIZE
    saturation: float = DEFAULT_SATURATION  # 0 = barely tinted, 0.5 = classic pastel, 1 = full colour
    deleted_at: str | None = None   # set while it sits in the Recycle Bin
    layouts: str = "{}"             # JSON: position per monitor arrangement (see screens.py)
    style: str = "3d"               # flat | soft (flat with a soft shadow) | 3d (glossy) | paper
    emoji: str = ""                 # shown before the title
    header: str = "plain"           # title area: plain | tinted | solid (the accent colour)
    background: str = "plain"       # plain | lined | grid | dots | gradient
    color2: str = ""                # where a gradient ends: a palette name or "#RRGGBB"; "" = a deeper shade
    checkbox: str = "circle"        # circle | square | heart
    done_look: str = "strike"       # finished tasks: strike (struck through) | fade
    title_font: str = ""            # "" = the system's display font
    text_color: str = ""            # "#RRGGBB", or "" for dark or light text to suit the colour
    spacing: str = "normal"         # compact | normal | roomy

    @property
    def deleted_dt(self) -> datetime | None:
        return from_iso(self.deleted_at)


@dataclass
class Settings:
    autostart: bool = False
    pin: str = "desktop"
    completed: str = "strike"
    style: str = "3d"               # card style for new notes
    appearance: str = "system"      # the app's own windows: system (follow the OS) | light | dark
    radius: int = 16                # corner roundness of every note, in px
    recent_colors: str = ""         # custom colours used lately, newest first, comma-separated


def _columns(cls) -> list[str]:
    return [f.name for f in fields(cls)]


def _from_row(cls, row: sqlite3.Row):
    values = {}
    for f in fields(cls):
        value = row[f.name]
        if f.type == "bool":
            value = bool(value)
        values[f.name] = value
    return cls(**values)


def _to_row(obj) -> tuple:
    return tuple(int(v) if isinstance(v, bool) else v for v in (getattr(obj, c) for c in _columns(type(obj))))


class Store(QObject):
    note_changed = Signal(str)      # a note's tasks or appearance changed
    notes_changed = Signal()        # notes added, removed, shown or hidden
    settings_changed = Signal()
    bin_changed = Signal()          # something in the Recycle Bin was deleted for good

    def __init__(self, path: Path | None = None):
        super().__init__()
        if path is None:
            path = data_dir() / DB_FILE
            if not os.environ.get("STICKYNOTES_DATA_DIR"):  # never touch real data from a test run
                path = adopt_legacy_database(path)
        self.path = path
        self.notes: list[Note] = []         # live notes
        self.tasks: list[Task] = []         # live tasks on live notes
        self.bin_notes: list[Note] = []     # deleted notes; their tasks wait in bin_tasks
        self.bin_tasks: list[Task] = []     # deleted tasks, plus every task of a deleted note
        self.settings = Settings()
        self.db = self._open()
        self.load()

    # ------------------------------------------------------------- database
    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, isolation_level=None)  # autocommit; explicit transactions below
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            db.close()
            raise sqlite3.DatabaseError("integrity check failed")
        existing = db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'notes'").fetchone()
        version = db.execute("PRAGMA user_version").fetchone()[0] if existing else SCHEMA_VERSION
        db.executescript(SCHEMA)
        for target in range(max(version, 1) + 1, SCHEMA_VERSION + 1):
            db.execute("BEGIN")
            for statement in MIGRATIONS.get(target, []):
                db.execute(statement)
            db.execute(f"PRAGMA user_version={target}")
            db.execute("COMMIT")
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return db

    def _open(self) -> sqlite3.Connection:
        backup = self.path.with_name("notes.bak.db")
        try:
            db = self._connect()
        except sqlite3.DatabaseError:
            # Keep the damaged file for inspection and fall back to the last good backup.
            stamp = f"{now():%Y%m%d-%H%M%S}"
            for suffix in ("", "-wal", "-shm"):
                damaged = Path(f"{self.path}{suffix}")
                if damaged.exists():
                    damaged.replace(self.path.with_name(f"notes.corrupt-{stamp}.db{suffix}"))
            if backup.exists():
                with sqlite3.connect(backup) as src, sqlite3.connect(self.path) as dst:
                    src.backup(dst)
            db = self._connect()
        with sqlite3.connect(backup) as dst:
            db.backup(dst)
        return db

    def _write(self, sql: str, params=()) -> None:
        self.db.execute(sql, params)

    def _upsert(self, table: str, obj) -> None:
        # A true UPSERT: "INSERT OR REPLACE" would delete the row first and cascade-delete a note's tasks.
        cols = [f'"{c}"' for c in _columns(type(obj))]
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c != '"id"')
        self._write(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            _to_row(obj),
        )

    def _save_note(self, note: Note) -> None:
        self._upsert("notes", note)

    def _save_task(self, task: Task) -> None:
        self._upsert("tasks", task)

    def load(self) -> None:
        notes = [_from_row(Note, r) for r in self.db.execute("SELECT * FROM notes ORDER BY rowid")]
        tasks = [_from_row(Task, r) for r in self.db.execute("SELECT * FROM tasks ORDER BY rowid")]
        self.notes = [n for n in notes if not n.deleted_at]
        self.bin_notes = [n for n in notes if n.deleted_at]
        live = {n.id for n in self.notes}
        self.tasks = [t for t in tasks if t.note_id in live and not t.deleted_at]
        self.bin_tasks = [t for t in tasks if t.note_id not in live or t.deleted_at]
        stored = {r["key"]: r["value"] for r in self.db.execute("SELECT key, value FROM settings")}
        defaults = Settings()
        values = {}
        for f in fields(Settings):
            raw, default = stored.get(f.name), getattr(defaults, f.name)
            if raw is None:
                values[f.name] = default
            elif isinstance(default, bool):
                values[f.name] = raw == "1"
            elif isinstance(default, int):
                values[f.name] = int(raw)
            else:
                values[f.name] = raw
        self.settings = Settings(**values)
        if not self.notes:
            self._seed()

    def _seed(self) -> None:
        note = Note(title="Today")
        welcome = [
            Task(note.id, text, order=i + 1) for i, text in enumerate((
                "Double-click a task to edit it",
                "End a task with @5pm or @tomorrow 9am to get a reminder",
                "Unfinished tasks roll over to tomorrow automatically",
            ))
        ]
        self.db.execute("BEGIN")
        self._save_note(note)
        for task in welcome:
            self._save_task(task)
        self.db.execute("COMMIT")
        self.notes.append(note)
        self.tasks.extend(welcome)

    def close(self) -> None:
        self.db.close()

    # ------------------------------------------------------------------ notes
    def note(self, note_id: str) -> Note | None:
        return next((n for n in self.notes if n.id == note_id), None)

    def add_note(self, kind: str = "daily", **props) -> Note:
        props.setdefault("title", "Today" if kind == "daily" else "Checklist")
        props.setdefault("style", self.settings.style)
        note = Note(kind=kind, pin=self.settings.pin, completed=self.settings.completed, **props)
        self.notes.append(note)
        self._save_note(note)
        self.notes_changed.emit()
        return note

    def update_note(self, note: Note, emit: bool = True, **changes) -> None:
        for key, value in changes.items():
            setattr(note, key, value)
        self._save_note(note)
        if emit:
            self.note_changed.emit(note.id)

    def set_note_visible(self, note: Note, visible: bool) -> None:
        note.visible = visible
        self._save_note(note)
        self.notes_changed.emit()

    def delete_note(self, note: Note) -> None:
        """Move a note, with its tasks, to the Recycle Bin."""
        note.deleted_at = to_iso(now())
        self._save_note(note)
        self.notes = [n for n in self.notes if n.id != note.id]
        self.bin_notes.append(note)
        self.bin_tasks += [t for t in self.tasks if t.note_id == note.id]
        self.tasks = [t for t in self.tasks if t.note_id != note.id]
        self.notes_changed.emit()

    def restore_note(self, note: Note) -> None:
        """Bring a note back from the Recycle Bin and show it. Tasks deleted on their own stay in the bin."""
        note.deleted_at = None
        note.visible = True
        self._save_note(note)
        self.bin_notes = [n for n in self.bin_notes if n.id != note.id]
        self.notes.append(note)
        self.tasks += [t for t in self.bin_tasks if t.note_id == note.id and not t.deleted_at]
        self.bin_tasks = [t for t in self.bin_tasks if t.note_id != note.id or t.deleted_at]
        self.notes_changed.emit()

    def purge_note(self, note: Note) -> None:
        """Delete a note in the Recycle Bin, and all of its tasks, for good."""
        self.bin_notes = [n for n in self.bin_notes if n.id != note.id]
        self.bin_tasks = [t for t in self.bin_tasks if t.note_id != note.id]
        self._write("DELETE FROM notes WHERE id = ?", (note.id,))  # tasks cascade
        self.bin_changed.emit()

    # ------------------------------------------------------------------ tasks
    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def tasks_for(self, note_id: str) -> list[Task]:
        """A note's tasks: pinned ones first, each group in its own order."""
        return sorted((t for t in self.tasks if t.note_id == note_id), key=lambda t: (not t.pinned, t.order))

    def add_task(self, note_id: str, text: str, remind_at: datetime | None = None) -> Task:
        order = max((t.order for t in self.tasks if t.note_id == note_id), default=0) + 1
        task = Task(note_id, text, order=order, remind_at=to_iso(remind_at))
        self.tasks.append(task)
        self._save_task(task)
        self.note_changed.emit(note_id)
        return task

    def update_task(self, task: Task, **changes) -> None:
        for key, value in changes.items():
            setattr(task, key, value)
        self._save_task(task)
        self.note_changed.emit(task.note_id)

    def set_reminder(self, task: Task, when: datetime | None, repeat_code: str | None = None) -> None:
        """Remind about `task` at `when`; None removes the reminder and any repeat.

        `repeat_code` is how it repeats ("" for once, see repeat.py); None keeps the task's current repeat.
        A repeat runs from `when`, so if that time has passed the next reminder is the series' next time.
        """
        if when is None:
            self.update_task(task, remind_at=None, reminded=False, repeat="", repeat_from=None)
            return
        code = task.repeat if repeat_code is None else repeat_code
        upcoming = when
        if code and when <= now():
            upcoming = repeat.next_after(code, when, now()) or when
        self.update_task(task, remind_at=to_iso(upcoming), reminded=False, repeat=code,
                         repeat_from=to_iso(when) if code else None)

    def set_pinned(self, task: Task, pinned: bool) -> None:
        """Pin a task (it joins the end of the pinned tasks) or unpin it (it leads the unpinned ones)."""
        orders = [t.order for t in self.tasks if t.note_id == task.note_id]
        self.update_task(task, pinned=pinned, order=max(orders) + 1 if pinned else min(orders) - 1)

    def set_done(self, task: Task, done: bool) -> None:
        """Ticking a task off also stops its reminders. Unticking a repeating one picks the series up at
        its next time, so it doesn't fire at once for a time that went by while it was done."""
        changes = {"done": done, "archived": False, "done_at": to_iso(now()) if done else None}
        if not done and task.repeat and task.remind_dt and task.remind_dt <= now():
            changes.update(remind_at=to_iso(task.next_reminder(now())), reminded=False)
        self.update_task(task, **changes)

    def delete_task(self, task: Task) -> None:
        """Move a task to the Recycle Bin."""
        task.deleted_at = to_iso(now())
        self._save_task(task)
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.bin_tasks.append(task)
        self.note_changed.emit(task.note_id)

    def deleted_tasks(self) -> list[Task]:
        """Tasks deleted on their own from notes that still exist, newest first.
        (Those of a deleted note come back as deleted tasks when the note is restored.)"""
        live = {n.id for n in self.notes}
        return sorted((t for t in self.bin_tasks if t.deleted_at and t.note_id in live),
                      key=lambda t: t.deleted_at, reverse=True)

    def restore_task(self, task: Task) -> None:
        """Put a deleted task back in its place on its note."""
        task.deleted_at = None
        self._save_task(task)
        self.bin_tasks = [t for t in self.bin_tasks if t.id != task.id]
        self.tasks.append(task)
        self.note_changed.emit(task.note_id)

    def purge_task(self, task: Task) -> None:
        """Delete a task in the Recycle Bin for good."""
        self.bin_tasks = [t for t in self.bin_tasks if t.id != task.id]
        self._write("DELETE FROM tasks WHERE id = ?", (task.id,))
        self.bin_changed.emit()

    def empty_bin(self) -> None:
        self.db.execute("BEGIN")
        self._write("DELETE FROM notes WHERE deleted_at IS NOT NULL")  # their tasks cascade
        self._write("DELETE FROM tasks WHERE deleted_at IS NOT NULL")
        self.db.execute("COMMIT")
        self.bin_notes, self.bin_tasks = [], []
        self.bin_changed.emit()

    def reorder(self, tasks: list[Task]) -> None:
        """Put `tasks` in the given order by reshuffling the order values they already hold,
        so their position relative to every other task stays the same."""
        if not tasks:
            return
        slots = sorted(t.order for t in tasks)
        self.db.execute("BEGIN")
        for task, order in zip(tasks, slots):
            task.order = order
            self._save_task(task)
        self.db.execute("COMMIT")
        self.note_changed.emit(tasks[0].note_id)

    def clear_completed(self, note_id: str) -> None:
        for t in self.tasks:
            if t.note_id == note_id and t.done:
                t.archived = True
        self._write("UPDATE tasks SET archived = 1 WHERE note_id = ? AND done = 1", (note_id,))
        self.note_changed.emit(note_id)

    # --------------------------------------------------------------- settings
    def update_settings(self, **changes) -> None:
        self.db.execute("BEGIN")
        for key, value in changes.items():
            setattr(self.settings, key, value)
            stored = ("1" if value else "0") if isinstance(value, bool) else str(value)
            self._write("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, stored))
        self.db.execute("COMMIT")
        self.settings_changed.emit()
