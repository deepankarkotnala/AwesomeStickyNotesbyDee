"""A running log of every task, kept next to the database as plain text and as an Excel workbook.

Rows are never removed: a task keeps its row after it is completed, moved to the Recycle Bin or
deleted for good, and only its status columns change. Because deleting for good removes a task from
notes.db, the history lives in its own file (notes-log.json), and both readable files are rebuilt from
it a moment after anything changes. The app never reads the .txt or .xlsx back.
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from PySide6.QtCore import QObject, QTimer

from . import APP_NAME
from .store import Store, from_iso, now, to_iso

HISTORY_FILE = "notes-log.json"
TEXT_FILE = "notes-log.txt"
EXCEL_FILE = "notes-log.xlsx"
DELAY_MS = 1_000        # wait for a burst of changes to settle before rewriting
RETRY_MS = 30_000       # a file couldn't be replaced (e.g. the workbook is open in Excel)


class NotesLog(QObject):
    def __init__(self, store: Store):
        super().__init__(store)
        self.store = store
        self.folder = store.path.parent
        self.records: dict[str, dict] = self._load()
        self._timer = QTimer(self, singleShot=True, interval=DELAY_MS)
        self._timer.timeout.connect(self.write)
        for signal in (store.note_changed, store.notes_changed, store.bin_changed):
            signal.connect(self.schedule)
        self.schedule()

    def schedule(self, *_) -> None:
        self.sync()     # record straight away, so a task added and deleted for good within DELAY_MS still counts
        self._timer.start(DELAY_MS)

    def flush(self) -> None:
        """Write now if a change is still waiting (called on quit)."""
        if self._timer.isActive():
            self._timer.stop()
            self.write()

    def _load(self) -> dict[str, dict]:
        path = self.folder / HISTORY_FILE
        if not path.exists():
            return {}
        try:
            return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["tasks"]}
        except (OSError, ValueError, KeyError, TypeError):
            # Keep the unreadable file for inspection rather than overwrite it, and start again from notes.db.
            try:
                path.replace(path.with_name(f"notes-log.corrupt-{now():%Y%m%d-%H%M%S}.json"))
            except OSError:
                pass
            return {}

    # ------------------------------------------------------------------ update
    def sync(self) -> None:
        """Bring every record up to date with the database. Tasks no longer in it are marked, never dropped."""
        notes = {n.id: n for n in self.store.notes + self.store.bin_notes}
        present = set()
        for task in self.store.tasks + self.store.bin_tasks:
            note = notes.get(task.note_id)
            record = self.records.setdefault(task.id, {"id": task.id})
            record.update(
                created=task.created,
                note=note.title if note else record.get("note", ""),
                text=task.text,
                done=task.done,
                done_at=task.done_at if task.done else None,
                deleted_at=task.deleted_at or (note.deleted_at if note else None),
                purged_at=None,
            )
            present.add(task.id)
        stamp = to_iso(now())
        for record in self.records.values():
            if record["id"] not in present and not record.get("purged_at"):
                record["purged_at"] = stamp
                record["deleted_at"] = record.get("deleted_at") or stamp

    def write(self) -> None:
        self.sync()
        rows = sorted(self.records.values(), key=lambda r: r.get("created") or "")
        ok = all([
            _replace(self.folder / HISTORY_FILE, lambda p: p.write_text(
                json.dumps({"tasks": list(self.records.values())}, ensure_ascii=False, indent=1),
                encoding="utf-8")),
            _replace(self.folder / TEXT_FILE, lambda p: p.write_text(_text(rows), encoding="utf-8-sig")),
            _replace(self.folder / EXCEL_FILE, lambda p: _write_xlsx(p, rows)),
        ])
        if not ok:
            self._timer.start(RETRY_MS)


def _replace(path: Path, write) -> bool:
    """Write to a temporary file first, so a crash or a locked file never leaves a half-written log."""
    partial = path.with_name(path.name + ".partial")
    try:
        write(partial)
        os.replace(partial, path)
        return True
    except OSError:
        partial.unlink(missing_ok=True)
        return False


def _status(record: dict) -> str:
    return "Completed" if record.get("done") else "Pending"


def _deleted(record: dict) -> str:
    if record.get("purged_at"):
        return "Deleted for good"
    return "In Recycle Bin" if record.get("deleted_at") else ""


def _minute(value: str | None) -> str:
    return (value or "")[:16].replace("T", " ")


# -------------------------------------------------------------------- text
def _text(rows: list[dict]) -> str:
    deleted = sum(1 for r in rows if _deleted(r))
    completed = sum(1 for r in rows if not _deleted(r) and r.get("done"))
    pending = len(rows) - deleted - completed
    width = min(max((len(r.get("note", "")) for r in rows), default=4), 24)
    lines = [
        f"{APP_NAME} - notes log",
        f"Updated {now():%Y-%m-%d %H:%M} | {len(rows)} tasks: {pending} pending, {completed} completed, "
        f"{deleted} deleted",
        "Every task ever added, oldest first. Rows are never removed; only their status changes.",
        "",
        f"{'CREATED':<16}  {'STATUS':<9}  {'NOTE':<{width}}  TASK",
    ]
    day = None
    for r in rows:
        created = _minute(r.get("created"))
        if day is not None and created[:10] != day:
            lines.append("")
        day = created[:10]
        extra = []
        if r.get("done_at"):
            extra.append(f"(completed {_minute(r['done_at'])})")
        if _deleted(r):
            extra.append(f"[{_deleted(r)}, {_minute(r.get('deleted_at'))}]")
        prefix = f"{created:<16}  {_status(r):<9}  {r.get('note', ''):<{width}}  "
        text = r.get("text", "").replace("\n", "\n" + " " * len(prefix))
        lines.append(prefix + "  ".join([text, *extra]))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- excel
# A minimal .xlsx written by hand (it is a zip of XML parts), so the app needs no extra library.
COLUMNS = [("Created", 18), ("Note", 20), ("Task", 60), ("Status", 12), ("Completed on", 18),
           ("Deleted", 17), ("Deleted on", 18)]
HEADER, DATE, GREEN, AMBER, RED = 1, 2, 3, 4, 5      # cell style ids, see STYLES
EXCEL_EPOCH = datetime(1899, 12, 30)
ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Notes log" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd hh:mm"/></numFmts>
<fonts count="5">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
<font><sz val="11"/><color rgb="FF2E7D32"/><name val="Calibri"/></font>
<font><sz val="11"/><color rgb="FFB26A00"/><name val="Calibri"/></font>
<font><sz val="11"/><color rgb="FFC62828"/><name val="Calibri"/></font>
</fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFFE9A8"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _cell(ref: str, value, style: int = 0) -> str:
    s = f' s="{style}"' if style else ""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return f'<c r="{ref}" s="{DATE}"><v>{(value - EXCEL_EPOCH).total_seconds() / 86400:.8f}</v></c>'
    text = escape(ILLEGAL_XML.sub("", str(value)))
    return f'<c r="{ref}"{s} t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _row(number: int, cells: list) -> str:
    body = "".join(_cell(f"{'ABCDEFG'[i]}{number}", *(c if isinstance(c, tuple) else (c,)))
                   for i, c in enumerate(cells))
    return f'<row r="{number}">{body}</row>'


def _write_xlsx(path: Path, rows: list[dict]) -> None:
    lines = [_row(1, [(name, HEADER) for name, _ in COLUMNS])]
    for n, r in enumerate(rows, start=2):
        status = _status(r)
        lines.append(_row(n, [
            from_iso(r.get("created")), r.get("note", ""), r.get("text", ""),
            (status, GREEN if status == "Completed" else AMBER), from_iso(r.get("done_at")),
            (_deleted(r), RED), from_iso(r.get("deleted_at")) if _deleted(r) else None,
        ]))
    last = f"G{len(rows) + 1}"
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                   for i, (_, w) in enumerate(COLUMNS, start=1))
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<dimension ref="A1:{last}"/>'
             '<sheetViews><sheetView workbookViewId="0">'
             '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             f'<sheetFormatPr defaultRowHeight="15"/><cols>{cols}</cols>'
             f'<sheetData>{"".join(lines)}</sheetData>'
             f'<autoFilter ref="A1:{last}"/></worksheet>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
