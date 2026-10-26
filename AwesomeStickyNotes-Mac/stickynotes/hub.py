"""The hub window: all notes, completed-task history, upcoming reminders, the Recycle Bin and settings."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel,
                               QLayout, QLineEdit, QMessageBox, QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)

from . import APP_NAME, APP_SHORT_NAME, DEVELOPER, __version__, decor, icons, repeat, system, theme
from .note import ElidedLabel
from .store import Note, Task, data_dir
from .timeparse import clock, day_label, friendly
from .widgets import IconButton, Pill, PillButton, Segmented, Toggle

TEXT, SUB = QColor(theme.HUB_TEXT), QColor(60, 60, 67, 150)

HUB_QSS = f"""
QWidget#hub {{ background: {theme.HUB_BG}; }}
QWidget {{ color: {theme.HUB_TEXT}; }}
QScrollArea, QWidget#pageContent {{ background: transparent; border: none; }}
QFrame#card {{ background: #FFFFFF; border: 1px solid rgba(0, 0, 0, 12); border-radius: 14px; }}
QFrame#divider {{ background: rgba(0, 0, 0, 14); border: none; }}
QLineEdit#search {{
    background: #FFFFFF; border: 1px solid rgba(0, 0, 0, 20); border-radius: 9px; padding: 7px 10px;
    selection-background-color: {theme.HUB_ACCENT};
}}
QLineEdit#search:focus {{ border: 1px solid {theme.HUB_ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: rgba(0, 0, 0, 40); border-radius: 4px; min-height: 30px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(0, 0, 0, 70); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
""" + theme.tooltip_qss()


# ---------------------------------------------------------------- helpers
def label(text: str, pt: float = 10, weight=QFont.Weight.Normal, color: QColor = TEXT,
          wrap: bool = False, display: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(theme.font(pt, weight, display))
    lbl.setStyleSheet(f"color: {theme.rgba(color)};")
    lbl.setWordWrap(wrap)
    return lbl


def section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    f = theme.font(8, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {theme.rgba(SUB)};")
    lbl.setContentsMargins(6, 14, 0, 6)
    return lbl


def clear(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if w := item.widget():
            w.hide()
            w.deleteLater()
        elif child := item.layout():
            clear(child)


def soft_shadow(widget: QWidget, blur: int = 26, dy: int = 4, alpha: int = 20) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        soft_shadow(self)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(6, 4, 6, 4)
        self.lay.setSpacing(0)

    def add_row(self, widget: QWidget) -> None:
        if self.lay.count():
            line = QFrame()
            line.setObjectName("divider")
            line.setFixedHeight(1)
            line.setContentsMargins(0, 0, 0, 0)
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(44, 0, 10, 0)
            hl.addWidget(line)
            self.lay.addWidget(holder)
        self.lay.addWidget(widget)


class Dot(QWidget):
    """Small status glyph: a filled check, a bell, a repeat arrow, or a colour dot."""

    def __init__(self, kind: str, color: str | QColor, parent=None):
        super().__init__(parent)
        self.kind, self.color = kind, QColor(color)
        self.setFixedSize(22, 22)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        if self.kind == "check":
            p.setBrush(self.color)
            p.drawEllipse(QRectF(2, 2, 18, 18))
            icons.paint(p, "check", QRectF(5.5, 5.8, 11, 11), "#FFFFFF", 3.2)
        elif self.kind in ("bell", "repeat"):
            icons.paint(p, self.kind, QRectF(2, 2, 18, 18), self.color, 2.0)
        else:
            p.setBrush(self.color)
            p.drawEllipse(QRectF(6, 6, 10, 10))


def note_pill(note: Note | None) -> Pill:
    pal = theme.palette(note.color if note else "cloud", note.saturation if note else 0.5)
    fg = QColor(pal.accent).darker(115)
    bg = QColor(pal.accent)
    bg.setAlphaF(0.13)
    return Pill(note.title if note else "Deleted note", fg, bg)


def scroll_page(parent: QWidget) -> tuple[QScrollArea, QVBoxLayout]:
    area = QScrollArea(parent)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = QWidget()
    content.setObjectName("pageContent")
    lay = QVBoxLayout(content)
    lay.setContentsMargins(4, 0, 12, 16)  # room for card shadows
    lay.setSpacing(6)
    area.setWidget(content)
    return area, lay


def confirm(parent: QWidget, title: str, text: str) -> bool:
    return QMessageBox.question(parent.window(), title, text) == QMessageBox.StandardButton.Yes


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def empty_message(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 70, 0, 0)
    for lbl in (label(title, 12, QFont.Weight.DemiBold), label(subtitle, 9.5, color=SUB, wrap=True)):
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(lbl)
    return w


class Page(QWidget):
    def __init__(self, hub: "HubWindow"):
        super().__init__()
        self.hub, self.ctl, self.store = hub, hub.ctl, hub.ctl.store

    def refresh(self) -> None:
        pass


# ---------------------------------------------------------------- notes
class SelectDot(QAbstractButton):
    """The circle in a note tile's corner that selects it, to restyle several notes at once."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Select, to change the look of several notes at once")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.HUB_ACCENT))
            p.drawEllipse(r)
            icons.paint(p, "check", r.adjusted(4.5, 4.8, -4.5, -4.2), "#FFFFFF", 3.0)
        else:
            p.setPen(QColor(0, 0, 0, 70))
            p.setBrush(QColor(255, 255, 255, 230))
            p.drawEllipse(r)


class NoteTile(QFrame):
    TITLE_BOTTOM = 44     # where the title area ends, for the header band

    def __init__(self, page: "NotesPage", note: Note):
        super().__init__()
        self.page, self.note = page, note
        pal = self.pal = theme.note_palette(note)
        head = theme.header_palette(pal, note.header)
        self.setFixedHeight(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        soft_shadow(self, 24, 4, 26)
        self.select = SelectDot(self)
        self.select.setChecked(note.id in page.selected)
        self.select.toggled.connect(lambda on: page.set_selected(note.id, on))
        store = page.store
        tasks = store.tasks_for(note.id)
        pending = [t for t in tasks if not t.done]
        today_done = [t for t in tasks if t.done and t.done_dt and t.done_dt.date() == date.today()]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 10, 10)
        lay.setSpacing(3)
        title = ElidedLabel()
        title.setText(f"{note.emoji}  {note.title}" if note.emoji else note.title)
        title.color = head.text
        title_font = theme.title_font(note.title_font)
        title_font.setPointSizeF(title_font.pointSizeF() * 0.89)
        title.setFont(title_font)
        title.setFixedHeight(24)
        title.reserve = 28        # clear of the select circle
        lay.addWidget(title)
        lay.addSpacing(6 if note.header != "plain" else 0)
        kind = "Daily to-do" if note.kind == "daily" else "Checklist"
        status = f"{kind}  ·  {len(pending)} pending  ·  {len(today_done)} done today"
        if not note.visible:
            status += "  ·  hidden"
        lay.addWidget(self._text(status, 8.5, pal.sub))
        lay.addSpacing(6)
        for t in pending[:4]:
            line = ElidedLabel()
            line.setText(f"○  {t.text}")
            line.color = pal.ink(0.8)
            line.setFont(theme.font(9.5))
            line.setFixedHeight(20)
            lay.addWidget(line)
        if len(pending) > 4:
            lay.addWidget(self._text(f"+ {len(pending) - 4} more", 8.5, pal.sub))
        if not pending:
            lay.addWidget(self._text("Nothing pending", 9.5, pal.sub))
        lay.addStretch(1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        eye = IconButton("eye_off" if note.visible else "eye", pal.ink(0.6), 28, 16,
                         "Hide from desktop" if note.visible else "Show on desktop", pal.wash(0.08))
        eye.clicked.connect(lambda: store.set_note_visible(note, not note.visible))
        trash = IconButton("trash", pal.ink(0.6), 28, 16, "Delete note", pal.wash(0.08))
        trash.clicked.connect(self._delete)
        bar.addWidget(eye)
        bar.addWidget(trash)
        lay.addLayout(bar)
        self.select.raise_()

    @staticmethod
    def _text(text: str, pt: float, color: QColor) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(theme.font(pt))
        lbl.setStyleSheet(f"color: {theme.rgba(color)};")
        return lbl

    def _delete(self) -> None:
        if confirm(self, "Delete note", f"Move “{self.note.title}” and all of its tasks to the Recycle Bin?"):
            self.page.store.delete_note(self.note)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.page.selected:      # while choosing notes, a click selects rather than opens
            self.select.toggle()
        else:
            self.page.ctl.focus_note(self.note.id)

    def resizeEvent(self, e):
        self.select.move(self.width() - self.select.width() - 8, 8)

    def enterEvent(self, e):
        self.select.show()

    def leaveEvent(self, e):
        self.select.setVisible(bool(self.page.selected))

    def showEvent(self, e):
        self.select.setVisible(bool(self.page.selected))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 3.0 if self.note.style == "paper" else 14.0
        decor.paint_card(p, r, self.note, self.pal, radius, 0.0, r.top() + self.TITLE_BOTTOM, scale=0.85)
        if self.select.isChecked():          # selected: an accent outline
            p.setPen(QPen(QColor(theme.HUB_ACCENT), 2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


class NotesPage(Page):
    COLUMNS = 3

    def __init__(self, hub):
        super().__init__(hub)
        self.selected: set[str] = set()      # ids of the notes chosen for restyling
        self.tiles: list[NoteTile] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        self.top = QWidget()
        top = QHBoxLayout(self.top)
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(label("Your notes", 12, QFont.Weight.DemiBold))
        top.addWidget(label("Hover a note and tick its circle to restyle several at once", 9, color=SUB))
        top.addStretch(1)
        for text, kind in (("+  Daily note", "daily"), ("+  Checklist", "checklist")):
            b = PillButton(text, theme.HUB_ACCENT, primary=kind == "daily")
            b.clicked.connect(lambda _=False, k=kind: self.ctl.new_note(k))
            top.addWidget(b)
        root.addWidget(self.top)

        self.bar = QWidget()          # shown instead while notes are selected
        bar = QHBoxLayout(self.bar)
        bar.setContentsMargins(0, 0, 0, 0)
        self.count = label("", 12, QFont.Weight.DemiBold)
        bar.addWidget(self.count)
        bar.addStretch(1)
        customise = PillButton("Customise…", theme.HUB_ACCENT, primary=True)
        customise.clicked.connect(lambda: self.ctl.customise(self._chosen()))
        self.paste = PillButton("Paste style", theme.HUB_ACCENT)
        self.paste.clicked.connect(lambda: self.ctl.paste_style(self._chosen()))
        everything = PillButton("Select all", theme.HUB_ACCENT)
        everything.clicked.connect(self.select_all)
        cancel = PillButton("Cancel", theme.HUB_ACCENT)
        cancel.clicked.connect(self.clear_selection)
        for b in (customise, self.paste, everything, cancel):
            bar.addWidget(b)
        root.addWidget(self.bar)
        self.bar.hide()
        area, self.lay = scroll_page(self)
        self.grid = QGridLayout()
        self.grid.setContentsMargins(4, 6, 4, 6)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(16)
        self.lay.addLayout(self.grid)
        self.lay.addStretch(1)
        root.addWidget(area, 1)

    def refresh(self) -> None:
        clear(self.grid)
        self.selected &= {n.id for n in self.store.notes}
        self.tiles = [NoteTile(self, note) for note in self.store.notes]
        for i, tile in enumerate(self.tiles):
            self.grid.addWidget(tile, i // self.COLUMNS, i % self.COLUMNS)
        for c in range(self.COLUMNS):
            self.grid.setColumnStretch(c, 1)
        self._show_bar()

    def _chosen(self) -> list[Note]:
        return [n for n in self.store.notes if n.id in self.selected]

    def set_selected(self, note_id: str, on: bool) -> None:
        (self.selected.add if on else self.selected.discard)(note_id)
        self._show_bar()

    def select_all(self) -> None:
        for tile in self.tiles:
            tile.select.setChecked(True)

    def clear_selection(self) -> None:
        for tile in self.tiles:
            tile.select.setChecked(False)

    def _show_bar(self) -> None:
        n = len(self.selected)
        self.top.setVisible(not n)
        self.bar.setVisible(bool(n))
        self.count.setText(f"{n} note{'s' if n != 1 else ''} selected")
        self.paste.setEnabled(self.ctl.copied_style is not None)
        for tile in self.tiles:
            tile.select.setVisible(bool(n) or tile.underMouse())
            tile.update()


# ---------------------------------------------------------------- completed history
class TaskLine(QWidget):
    def __init__(self, glyph: QWidget, text: str, pill: QWidget, meta: str, actions: list[IconButton],
                 meta_color: QColor = SUB):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 9, 8, 9)
        lay.setSpacing(10)
        lay.addWidget(glyph)
        txt = label(text, 10, wrap=True)
        txt.setMinimumWidth(120)
        lay.addWidget(txt, 1)
        lay.addWidget(pill)
        m = label(meta, 9, color=meta_color)
        m.setMinimumWidth(64)
        m.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(m)
        for a in actions:
            lay.addWidget(a)


class CompletedPage(Page):
    LIMIT = 400

    def __init__(self, hub):
        super().__init__(hub)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Search completed tasks")
        self.search.addAction(icons.icon("x", "#8E8E93"), QLineEdit.ActionPosition.TrailingPosition) \
            .triggered.connect(self.search.clear)
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(lambda: self.refresh())
        top.addWidget(self.search)
        top.addStretch(1)
        self.count = label("", 9.5, color=SUB)
        top.addWidget(self.count)
        root.addLayout(top)
        area, self.lay = scroll_page(self)
        root.addWidget(area, 1)

    def refresh(self) -> None:
        clear(self.lay)
        query = self.search.text().strip().casefold()
        done = [t for t in self.store.tasks if t.done and t.done_dt and query in t.text.casefold()]
        done.sort(key=lambda t: t.done_at, reverse=True)
        self.count.setText(f"{len(done)} completed")
        if not done:
            self.lay.addWidget(empty_message("Nothing completed yet" if not query else "No matches",
                                             "Tasks you tick off are kept here, grouped by day."))
            self.lay.addStretch(1)
            return
        groups: dict[date, list[Task]] = defaultdict(list)
        for t in done[:self.LIMIT]:
            groups[t.done_dt.date()].append(t)
        for day, tasks in groups.items():
            self.lay.addWidget(section_label(f"{day_label(day, long=True)}  ·  {len(tasks)}"))
            card = Card()
            for t in tasks:
                note = self.store.note(t.note_id)
                restore = IconButton("undo", "#636366", 28, 15, "Restore to note (mark as not done)")
                restore.clicked.connect(lambda _=False, task=t: self.store.set_done(task, False))
                delete = IconButton("trash", "#636366", 28, 15, "Move to Recycle Bin")
                delete.clicked.connect(lambda _=False, task=t: self.store.delete_task(task))
                accent = theme.palette(note.color).accent if note else "#8E8E93"
                card.add_row(TaskLine(Dot("check", accent), t.text, note_pill(note), clock(t.done_dt),
                                      [restore, delete]))
            self.lay.addWidget(card)
        self.lay.addStretch(1)


# ---------------------------------------------------------------- reminders
class RemindersPage(Page):
    def __init__(self, hub):
        super().__init__(hub)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        area, self.lay = scroll_page(self)
        root.addWidget(area, 1)

    def refresh(self) -> None:
        clear(self.lay)
        now = datetime.now()
        items = sorted((t for t in self.store.tasks if t.remind_dt and not t.done), key=lambda t: t.remind_at)
        if not items:
            self.lay.addWidget(empty_message("No reminders",
                                             "End a task with @5pm, @tomorrow 9am or @30m - "
                                             "or use the bell on any task."))
            self.lay.addStretch(1)
            return
        groups: dict[str, list[Task]] = {}
        for t in items:
            key = "Overdue" if t.remind_dt < now else day_label(t.remind_dt.date(), long=True)
            groups.setdefault(key, []).append(t)
        for title, tasks in groups.items():
            self.lay.addWidget(section_label(f"{title}  ·  {len(tasks)}"))
            card = Card()
            for t in tasks:
                note = self.store.note(t.note_id)
                overdue = t.remind_dt < now
                done = IconButton("check", "#636366", 28, 15, "Mark done")
                done.clicked.connect(lambda _=False, task=t: self.store.set_done(task, True))
                remove = IconButton("x", "#636366", 28, 15, "Remove reminder")
                remove.clicked.connect(lambda _=False, task=t: self.store.set_reminder(task, None))
                color = theme.DANGER if overdue else (theme.palette(note.color).accent if note else theme.HUB_ACCENT)
                meta = friendly(t.remind_dt) if overdue else clock(t.remind_dt)
                if t.repeat:
                    meta += f"  ·  {repeat.short(t.repeat)}"
                card.add_row(TaskLine(Dot("repeat" if t.repeat else "bell", color), t.text, note_pill(note), meta,
                                      [done, remove], QColor(theme.DANGER) if overdue else SUB))
            self.lay.addWidget(card)
        self.lay.addStretch(1)


# ---------------------------------------------------------------- recycle bin
class BinPage(Page):
    """Deleted notes and deleted tasks, kept until they are restored or the bin is emptied."""

    def __init__(self, hub):
        super().__init__(hub)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        top = QHBoxLayout()
        self.section = Segmented([("notes", "Deleted notes"), ("tasks", "Deleted tasks")], "notes")
        self.section.changed.connect(lambda _: self.refresh())
        top.addWidget(self.section)
        top.addStretch(1)
        top.addWidget(label("Kept until you empty the bin", 9.5, color=SUB))
        self.empty_btn = PillButton("Empty bin", theme.DANGER, primary=True)
        self.empty_btn.clicked.connect(self._empty)
        top.addWidget(self.empty_btn)
        root.addLayout(top)
        area, self.lay = scroll_page(self)
        root.addWidget(area, 1)

    def refresh(self) -> None:
        clear(self.lay)
        notes = sorted(self.store.bin_notes, key=lambda n: n.deleted_at, reverse=True)
        tasks = self.store.deleted_tasks()
        self.section.buttons["notes"].setText(f"Deleted notes  ·  {len(notes)}")
        self.section.buttons["tasks"].setText(f"Deleted tasks  ·  {len(tasks)}")
        self.empty_btn.setEnabled(bool(notes or tasks))
        showing_notes = self.section.current == "notes"
        items = notes if showing_notes else tasks
        if not items:
            what = "notes" if showing_notes else "tasks"
            self.lay.addWidget(empty_message(f"No deleted {what}",
                                             f"{what.capitalize()} you delete are kept here until you restore "
                                             "them or empty the bin."))
            self.lay.addStretch(1)
            return
        groups: dict[date, list] = defaultdict(list)
        for item in items:
            groups[item.deleted_dt.date()].append(item)
        for day, group in groups.items():
            self.lay.addWidget(section_label(f"{day_label(day, long=True)}  ·  {len(group)}"))
            card = Card()
            for item in group:
                card.add_row(self._note_line(item) if showing_notes else self._task_line(item))
            self.lay.addWidget(card)
        self.lay.addStretch(1)

    def _note_line(self, note: Note) -> TaskLine:
        count = sum(1 for t in self.store.bin_tasks if t.note_id == note.id and not t.deleted_at)
        kind = "Daily to-do" if note.kind == "daily" else "Checklist"
        pill = Pill(f"{kind}  ·  {plural(count, 'task')}", QColor("#636366"), QColor(118, 118, 128, 30))
        restore = IconButton("undo", "#636366", 28, 15, "Restore note")
        restore.clicked.connect(lambda: self.store.restore_note(note))
        purge = IconButton("trash", "#636366", 28, 15, "Delete forever")
        purge.clicked.connect(lambda: self._purge_note(note, count))
        return TaskLine(Dot("dot", theme.palette(note.color).accent), note.title, pill,
                        clock(note.deleted_dt), [restore, purge])

    def _task_line(self, task: Task) -> TaskLine:
        note = self.store.note(task.note_id)
        restore = IconButton("undo", "#636366", 28, 15, "Restore to note")
        restore.clicked.connect(lambda: self.store.restore_task(task))
        purge = IconButton("trash", "#636366", 28, 15, "Delete forever")
        purge.clicked.connect(lambda: self.store.purge_task(task))
        accent = theme.palette(note.color).accent
        return TaskLine(Dot("check" if task.done else "dot", accent), task.text, note_pill(note),
                        clock(task.deleted_dt), [restore, purge])

    def _purge_note(self, note: Note, count: int) -> None:
        if confirm(self, "Delete forever",
                   f"Permanently delete “{note.title}” and its {plural(count, 'task')}?\nThis can't be undone."):
            self.store.purge_note(note)

    def _empty(self) -> None:
        notes, tasks = len(self.store.bin_notes), len(self.store.deleted_tasks())
        parts = [plural(n, word) for n, word in ((notes, "note"), (tasks, "task")) if n]
        if confirm(self, "Empty Recycle Bin",
                   f"Permanently delete {' and '.join(parts)}?\nThis can't be undone."):
            self.store.empty_bin()


# ---------------------------------------------------------------- settings
class SettingsPage(Page):
    def __init__(self, hub):
        super().__init__(hub)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        area, lay = scroll_page(self)
        root.addWidget(area, 1)
        s = self.store.settings

        lay.addWidget(section_label("General"))
        general = Card()
        self.autostart = Toggle(system.autostart_enabled())
        self.autostart.toggled.connect(self.ctl.set_autostart)
        general.add_row(self._row(system.AUTOSTART_LABEL, "Open your notes automatically when you sign in.",
                                  self.autostart))
        self.pin = Segmented([("desktop", "On desktop"), ("top", "Always on top")], s.pin)
        self.pin.changed.connect(self.ctl.set_pin_all)
        general.add_row(self._row("Where notes live",
                                  f"On desktop: other windows cover them and {system.SHOW_DESKTOP} shows them. "
                                  "Always on top: they float above everything.", self.pin))
        self.completed = Segmented([("strike", "Strike through"), ("hide", "Hide")], s.completed)
        self.completed.changed.connect(self.ctl.set_completed_all)
        general.add_row(self._row("Completed tasks on notes",
                                  "Strike through: kept on the note until the end of the day. "
                                  "Hide: they move straight to Completed.", self.completed))
        lay.addWidget(general)

        lay.addWidget(section_label("Appearance"))
        look = Card()
        self.style = Segmented([(key, name) for key, name, _ in theme.STYLES], s.style)
        self.style.changed.connect(lambda v: self.store.update_settings(style=v))
        apply_style = PillButton("Apply to all notes", theme.HUB_ACCENT)
        apply_style.setToolTip("Give every note this style now")
        apply_style.clicked.connect(lambda: self.ctl.set_style_all(self.style.current))
        style_box = QWidget()
        sl = QHBoxLayout(style_box)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(10)
        sl.addWidget(self.style)
        sl.addWidget(apply_style)
        look.add_row(self._row("Card style for new notes",
                               "Flat: a plain card. Elevated: flat, lifted by a soft shadow. 3D: glossy with a "
                               "deeper shadow. Each note can have its own under ⋯ → Style.", style_box))
        self.radius = Segmented([(str(r), name) for r, name in theme.RADII], str(s.radius))
        self.radius.changed.connect(lambda v: self.store.update_settings(radius=int(v)))
        look.add_row(self._row("Corners", "How rounded the corners of every note are.", self.radius))
        lay.addWidget(look)

        lay.addWidget(section_label("Reminder shortcuts"))
        tips = Card()
        for code, meaning in (("@5pm", "Today at 5:00 PM (tomorrow if already past)"),
                              ("@17:30", "24-hour time works too"),
                              ("@tomorrow 9am", "Tomorrow morning"),
                              ("@fri 10:30am", "Next Friday"),
                              ("@tonight", "Today at 8:00 PM"),
                              ("@30m  ·  @2h", "In 30 minutes / in 2 hours")):
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 10, 12, 10)
            rl.setSpacing(14)
            pill = Pill(code, QColor(theme.HUB_ACCENT), QColor(10, 132, 255, 26))
            pill.setFixedWidth(max(pill.width(), 120))
            rl.addWidget(pill)
            rl.addWidget(label(meaning, 9.5, color=SUB), 1)
            tips.add_row(row)
        lay.addWidget(tips)

        lay.addWidget(section_label("Data"))
        data = Card()
        path = data_dir() / "notes.db"
        open_btn = PillButton("Open folder", theme.HUB_ACCENT)
        open_btn.clicked.connect(lambda: system.open_folder(data_dir()))
        data.add_row(self._row("Stored locally in SQLite", str(path), open_btn, selectable=True))
        lay.addWidget(data)

        lay.addWidget(section_label("About"))
        about = Card()
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 14, 12, 14)
        rl.setSpacing(14)
        badge = QLabel()
        badge.setPixmap(self.ctl.icon.pixmap(44, 44))
        rl.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(APP_NAME, 12, QFont.Weight.DemiBold))
        col.addWidget(label(f"Version {__version__}", 9, color=SUB))
        col.addSpacing(6)
        col.addWidget(label(f"Developed by {DEVELOPER}", 10, QFont.Weight.Medium))
        rl.addLayout(col, 1)
        about.add_row(row)
        lay.addWidget(about)
        lay.addStretch(1)

    @staticmethod
    def _row(title: str, subtitle: str, control: QWidget, selectable: bool = False) -> QWidget:
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.setSpacing(16)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label(title, 10.5, QFont.Weight.Medium))
        sub = label(subtitle, 9, color=SUB, wrap=True)
        if selectable:
            sub.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(sub)
        rl.addLayout(col, 1)
        rl.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def refresh(self) -> None:
        s = self.store.settings
        self.pin.set_current(s.pin)
        self.completed.set_current(s.completed)
        self.style.set_current(s.style)
        self.radius.set_current(str(s.radius))
        self.autostart.blockSignals(True)
        self.autostart.setChecked(system.autostart_enabled())
        self.autostart.blockSignals(False)


# ---------------------------------------------------------------- window
class HubWindow(QWidget):
    PAGES = (("notes", "Notes"), ("completed", "Completed"), ("reminders", "Reminders"), ("bin", "Recycle Bin"),
             ("settings", "Settings"))

    def __init__(self, controller):
        super().__init__()
        self.ctl = controller
        self.setObjectName("hub")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(controller.icon)
        self.setStyleSheet(HUB_QSS)
        self.resize(900, 680)
        self.setMinimumSize(800, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 24, 12)
        root.setSpacing(18)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(label(APP_SHORT_NAME, 20, QFont.Weight.Bold, display=True))
        self.summary = label("", 9.5, color=SUB)
        titles.addWidget(self.summary)
        top.addLayout(titles)
        top.addStretch(1)
        self.tabs = Segmented(list(self.PAGES), "notes")
        self.tabs.changed.connect(self.show_page)
        top.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(top)

        self.stack = QStackedWidget()
        self.pages: dict[str, Page] = {
            "notes": NotesPage(self), "completed": CompletedPage(self),
            "reminders": RemindersPage(self), "bin": BinPage(self), "settings": SettingsPage(self),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        self._refresh_timer = QTimer(self, singleShot=True, interval=80)
        self._refresh_timer.timeout.connect(self.refresh)
        store = controller.store
        for signal in (store.note_changed, store.notes_changed, store.settings_changed, store.bin_changed):
            signal.connect(self._schedule_refresh)

    def _schedule_refresh(self, *_):
        if self.isVisible():
            self._refresh_timer.start()

    def show_page(self, key: str) -> None:
        self.tabs.set_current(key)
        self.stack.setCurrentWidget(self.pages[key])
        self.refresh()

    def refresh(self) -> None:
        store = self.ctl.store
        pending = sum(1 for t in store.tasks if not t.done)
        reminders = sum(1 for t in store.tasks if t.remind_dt and not t.done)
        today = sum(1 for t in store.tasks if t.done and t.done_dt and t.done_dt.date() == date.today())
        n = len(store.notes)
        self.summary.setText(f"{n} note{'s' if n != 1 else ''}  ·  {pending} pending  ·  "
                             f"{today} done today  ·  {reminders} reminder{'s' if reminders != 1 else ''}")
        self.stack.currentWidget().refresh()

    def showEvent(self, e):
        super().showEvent(e)
        system.set_caption_color(self, theme.HUB_BG)
        self.refresh()
