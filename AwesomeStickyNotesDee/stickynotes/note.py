"""The desktop sticky note: a frameless, softly shadowed card holding a to-do list."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QEvent, QMargins, QMarginsF, QPoint, QPointF,
                            QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer)
from PySide6.QtGui import (QColor, QFont, QKeySequence, QLinearGradient, QPainter,
                           QPainterPath, QPalette, QPen, QPixmap, QRegion, QShortcut)
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout,
                               QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
                               QWidget)

from . import icons, screens, shadow, system, theme
from .store import DEFAULT_FONT_SIZE, Note, Task, to_iso
from .timeparse import day_label, extract_reminder, friendly
from .widgets import (IconButton, InlineEdit, ProgressLine, ResizeEdge, ResizeGrip, TaskRow, add_action, add_font_list,
                      add_menu_label, add_saturation, add_stepper,
                      add_submenu, add_swatches, animate, animation, make_menu, pick_datetime, EXIT_MS, MOTION,
                      reminder_presets)

MARGINS = QMargins(22, 16, 22, 30)      # transparent room around the card for the shadow
CARD_PADDING = QMargins(8, 0, 12, 12)        # task rows add their own 12px grip gutter
HANDLE_BAND = 14                             # strip above the title holding the move handle (part of the header)
EDGE_OUT, EDGE_IN, EDGE_CORNER = 6, 4, 12    # resize zones: px outside / inside the card, corner reach
RADIUS = 16.0
MIN_SIZE = QSize(280, 250)
QWIDGETSIZE_MAX = 16777215


class ElidedLabel(QLabel):
    """Single-line label that ends with an ellipsis instead of clipping."""

    def __init__(self, parent=None, inset: int = 0):
        super().__init__(parent)
        self.color = QColor("#1C1C1E")
        self.inset = inset                 # left padding inside the (optional) highlight
        self.reserve = 0                   # room kept free on the right (e.g. for buttons floating over it)
        self.highlight: QColor | None = None
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def text_rect(self) -> QRect:
        width = min(self.fontMetrics().horizontalAdvance(self.text()) + 2 * self.inset,
                    self.width() - self.reserve)
        return QRect(0, 0, max(0, width), self.height())

    def paintEvent(self, e):
        p = QPainter(self)
        if self.highlight is not None:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.highlight)
            p.drawRoundedRect(QRectF(self.text_rect()).adjusted(0, 1, 0, -1), 6, 6)
        p.setFont(self.font())
        p.setPen(self.color)
        width = self.width() - self.reserve - 2 * self.inset
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, width)
        p.drawText(self.rect().adjusted(self.inset, 0, -self.reserve, 0),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)


class Header(QWidget):
    """Drag to move the note (a dotted handle at the top shows where); click the title to rename it.
    Its buttons float over the top-right corner."""

    def __init__(self, note_window: "NoteWindow"):
        super().__init__(note_window.card)
        self.win = note_window
        self._press: QPoint | None = None
        self._manual: tuple[QPoint, QPoint] | None = None   # (press, window pos) when moving by hand
        self.actions: QWidget | None = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def resizeEvent(self, e):
        if self.actions:
            self.actions.adjustSize()
            self.actions.move(self.width() - self.actions.width(), HANDLE_BAND)

    def paintEvent(self, e):
        # Six-dot handle centred on the card, like the grip on task rows; stronger while hovered.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.win.pal.ink(0.30 + 0.20 * self.win._hover_t))
        cx = self.win.card.width() / 2 - self.x()
        for dx in (-5.5, 0.0, 5.5):
            for dy in (-2.75, 2.75):
                p.drawEllipse(QPointF(cx + dx, HANDLE_BAND / 2 + 1 + dy), 1.4, 1.4)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        pos = e.globalPosition().toPoint()
        if self._manual:
            press, origin = self._manual
            self.window().move(origin + pos - press)
        elif self._press and (pos - self._press).manhattanLength() > 3:
            press, self._press = self._press, None
            self.win.set_title_hover(False)
            handle = self.window().windowHandle()
            if not (handle and handle.startSystemMove()):
                self._manual = (press, self.window().pos())   # no system move: follow the mouse ourselves
        elif not e.buttons():
            self.win.set_title_hover(self.win.over_title(e.position().toPoint()))

    def mouseReleaseEvent(self, e):
        self._manual = None
        pressed, self._press = self._press, None
        # A click (not a drag) on the title text starts renaming.
        if pressed is not None and e.button() == Qt.MouseButton.LeftButton \
                and self.win.over_title(e.position().toPoint()):
            self.win.begin_rename()

    def leaveEvent(self, e):
        self.win.set_title_hover(False)

    def mouseDoubleClickEvent(self, e):
        self.win.begin_rename()


class EmptyState(QWidget):
    def __init__(self, pal: theme.Palette, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.pal = pal
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 66, 0, 16)
        lay.setSpacing(2)
        for text, size, weight, color in ((title, 11, QFont.Weight.DemiBold, pal.ink(0.75)),
                                          (subtitle, 9, QFont.Weight.Normal, pal.sub)):
            label = QLabel(text)
            label.setFont(theme.font(size, weight))
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {theme.rgba(color)};")
            lay.addWidget(label)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.pal.accent)
        bg.setAlphaF(0.14)
        centre = QPointF(self.width() / 2, 36)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawEllipse(centre, 22, 22)
        icons.paint(p, "check", QRectF(centre.x() - 11, centre.y() - 11, 22, 22), self.pal.accent, 2.4)


class DragGhost(QWidget):
    """The 'lifted' copy of a task that follows the cursor while dragging."""

    def __init__(self, pixmap: QPixmap, pal: theme.Palette, parent: QWidget):
        super().__init__(parent)
        self.pixmap, self.pal = pixmap, pal
        self.setFixedSize(pixmap.deviceIndependentSize().toSize())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(22)
        effect.setOffset(0, 6)
        effect.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(effect)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 9, 9)
        p.fillPath(path, QColor(self.pal.bg))
        p.setClipPath(path)
        p.drawPixmap(0, 0, self.pixmap)


class RowDrag:
    """Drag-to-reorder for one task row, kept inside its own section of the list.

    The row stays in the layout as an empty slot; the other rows slide around it as the ghost moves,
    and the new order is saved when the ghost settles into the slot.
    """
    EDGE = 28          # px from the list's top/bottom edge where auto-scroll kicks in
    SLIDE_MS = 140

    def __init__(self, win: "NoteWindow", row: TaskRow, press: QPoint):
        self.win, self.row = win, row
        lay = win.list_lay
        index = lay.indexOf(row)
        lo = hi = index
        while lo > 0 and self._movable(lay.itemAt(lo - 1).widget()):
            lo -= 1
        while hi + 1 < lay.count() and self._movable(lay.itemAt(hi + 1).widget()):
            hi += 1
        self.lo, self.hi = lo, hi
        self.slides: dict[QWidget, QPropertyAnimation] = {}
        self.final_y: dict[QWidget, int] = {}

        row.actions.hide()
        self.ghost = DragGhost(self._snapshot(row), win.pal, win.card)
        self.offset_y = row.mapFromGlobal(press).y()
        self.ghost.move(row.mapTo(win.card, QPoint(0, 0)))
        self.ghost.show()
        self.ghost.raise_()
        row.set_slot(True)
        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)

        self.cursor = press
        self.scroller = QTimer(win, interval=16)
        self.scroller.timeout.connect(self._autoscroll)

    @staticmethod
    def _snapshot(row: TaskRow) -> QPixmap:
        """Render the row onto a transparent pixmap (QWidget.grab would fill it with the system's
        window colour, which is dark grey in Windows dark mode)."""
        dpr = row.devicePixelRatioF()
        pixmap = QPixmap(round(row.width() * dpr), round(row.height() * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        row.render(pixmap, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        return pixmap

    @staticmethod
    def _movable(widget) -> bool:
        return isinstance(widget, TaskRow) and widget.draggable

    def _viewport_span(self) -> tuple[int, int]:
        vp = self.win.scroll.viewport()
        top = vp.mapTo(self.win.card, QPoint(0, 0)).y()
        return top, top + vp.height()

    def move(self, cursor: QPoint) -> None:
        self.cursor = cursor
        top, bottom = self._viewport_span()
        y = self.win.card.mapFromGlobal(cursor).y()
        half = self.ghost.height() // 2
        ghost_y = max(top - half, min(y - self.offset_y, bottom - half))
        self.ghost.move(self.ghost.x(), ghost_y)
        self._retarget()
        near_edge = y < top + self.EDGE or y > bottom - self.EDGE
        if near_edge and not self.scroller.isActive():
            self.scroller.start()
        elif not near_edge:
            self.scroller.stop()

    def _autoscroll(self) -> None:
        top, bottom = self._viewport_span()
        y = self.win.card.mapFromGlobal(self.cursor).y()
        if y < top + self.EDGE:
            step = -max(2, (top + self.EDGE - y) // 3)
        elif y > bottom - self.EDGE:
            step = max(2, (y - bottom + self.EDGE) // 3)
        else:
            self.scroller.stop()
            return
        bar = self.win.scroll.verticalScrollBar()
        bar.setValue(bar.value() + step)
        self._retarget()

    def _retarget(self) -> None:
        """Move the slot to wherever the ghost's centre now sits, sliding the other rows aside."""
        lay = self.win.list_lay
        centre = self.win.list.mapFrom(self.win.card, self.ghost.geometry().center()).y()
        others = [lay.itemAt(i).widget() for i in range(self.lo, self.hi + 1)]
        others = [w for w in others if w is not self.row]
        target = self.lo + sum(1 for w in others
                               if self.final_y.get(w, w.y()) + w.height() / 2 < centre)
        if target == lay.indexOf(self.row):
            return
        moving = others + [self.row]
        before = {w: w.pos() for w in moving}
        lay.removeWidget(self.row)
        lay.insertWidget(target, self.row)
        lay.activate()  # apply the new geometry now, then animate from the old spots
        for w in moving:
            after = w.pos()
            self.final_y[w] = after.y()
            if before[w] == after:
                continue
            if w in self.slides:
                self.slides[w].stop()
            if not MOTION:
                continue
            w.move(before[w])
            slide = QPropertyAnimation(w, b"pos", w)
            slide.setDuration(self.SLIDE_MS)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            slide.setStartValue(before[w])
            slide.setEndValue(after)
            slide.start()
            self.slides[w] = slide

    def drop(self) -> None:
        self.scroller.stop()
        QApplication.restoreOverrideCursor()
        lay = self.win.list_lay
        order = [lay.itemAt(i).widget().task for i in range(self.lo, self.hi + 1)]
        slot = self.row.mapTo(self.win.card, QPoint(0, 0))
        slot.setY(self.win.list.mapTo(self.win.card, QPoint(0, self.final_y.get(self.row, self.row.y()))).y())
        settle = QPropertyAnimation(self.ghost, b"pos", self.ghost)
        settle.setDuration(self.SLIDE_MS if MOTION else 0)
        settle.setEasingCurve(QEasingCurve.Type.OutCubic)
        settle.setStartValue(self.ghost.pos())
        settle.setEndValue(slot)
        settle.finished.connect(lambda: self.win._finish_drag(self, order))
        settle.start()
        self._settle = settle


class NoteWindow(QWidget):
    def __init__(self, controller, note: Note):
        super().__init__(None, system.window_flags("note"))
        system.prepare(self)
        self.ctl, self.store, self.note = controller, controller.store, note
        self.pal = theme.palette(note.color, note.saturation)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(note.title)
        self.setMinimumSize(MIN_SIZE)
        if MOTION:
            self.setWindowOpacity(0.0)  # faded in on first show

        self._hover_t = 0.0
        self._hover_anim = animation(self, 220, self._set_hover)
        self._exact_shadow: tuple | None = None   # only needed for small (collapsed) cards
        self._geo_timer = QTimer(self, singleShot=True, interval=400)
        self._geo_timer.timeout.connect(self._save_geometry)
        self._collapse_anim = None
        self._fade_anim = None
        self._faded_in = False

        self._optimistic: dict[str, bool] = {}   # checkbox state shown before it is committed
        self._animate_in: set[str] = set()       # task ids whose rows should grow in on the next rebuild
        self._quiet = False                      # skip the store's rebuild while we trigger our own
        self._editing = 0
        self._rebuild_pending = False
        self._title_edit: InlineEdit | None = None
        self._drag: RowDrag | None = None
        self._scroll_to: str | None = None
        self._themed = None                      # (colour, saturation) the widgets were styled for

        self._build()
        self.apply_theme()
        self.rebuild()
        self._restore_geometry()
        self.store.note_changed.connect(self._on_note_changed)

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(MARGINS)
        # Sizes are managed explicitly (MIN_SIZE / collapsed height), so the window may animate
        # below its content's minimum while collapsing.
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.card = QWidget(self)
        root.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(CARD_PADDING)
        lay.setSpacing(0)

        # header -----------------------------------------------------------
        self.header = Header(self)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(6, HANDLE_BAND, 0, 0)
        hl.setSpacing(2)
        self.titles = QVBoxLayout()
        self.titles.setSpacing(0)
        self.title_lbl = ElidedLabel(inset=4)
        self.title_lbl.setFont(theme.font(13.5, QFont.Weight.DemiBold, display=True))
        self.title_lbl.setFixedHeight(26)
        self.sub_lbl = ElidedLabel(inset=4)
        self.sub_lbl.setFont(theme.font(8.8))
        self.sub_lbl.setFixedHeight(self.sub_lbl.fontMetrics().height() + 2)
        for label in (self.title_lbl, self.sub_lbl):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.titles.addWidget(label)
        hl.addLayout(self.titles, 1)
        self.header.actions = actions = QWidget(self.header)
        al = QHBoxLayout(actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(2)
        self.btn_new = IconButton("plus", QColor(), 28, 16, "New note")
        self.btn_collapse = IconButton("chevron_up", QColor(), 28, 16, "Collapse")
        self.btn_more = IconButton("more", QColor(), 28, 16, "Colour & options")
        self.btn_close = IconButton("x", QColor(), 28, 16, f"Hide note (reopen from the {system.TRAY})")
        self.btn_new.clicked.connect(self._new_menu)
        self.btn_collapse.clicked.connect(self.toggle_collapsed)
        self.btn_more.clicked.connect(self._more_menu)
        self.btn_close.clicked.connect(self.hide_note)
        self.header_buttons = (self.btn_new, self.btn_collapse, self.btn_more, self.btn_close)
        for b in self.header_buttons:
            b.set_revealed(False, animated=False)
            al.addWidget(b)
        lay.addWidget(self.header)

        # progress ---------------------------------------------------------
        self.progress_wrap = QWidget()
        pl = QVBoxLayout(self.progress_wrap)
        pl.setContentsMargins(10, 10, 6, 6)
        self.progress = ProgressLine()
        pl.addWidget(self.progress)
        lay.addWidget(self.progress_wrap)

        # task list --------------------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.viewport().installEventFilter(self)  # Ctrl + wheel = text size
        self.list = QWidget()
        self.list.setObjectName("list")
        self.list_lay = QVBoxLayout(self.list)
        self.list_lay.setContentsMargins(0, 0, 4, 4)
        self.list_lay.setSpacing(1)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.list)
        lay.addWidget(self.scroll, 1)

        # add-task footer --------------------------------------------------
        self.footer = QWidget()
        fl = QVBoxLayout(self.footer)
        fl.setContentsMargins(6, 8, 2, 0)
        fl.setSpacing(4)
        self.input = QLineEdit()
        self.input.setObjectName("addInput")
        self.input.setPlaceholderText("Add a task")
        self.input.setFont(theme.font(10))
        self.input.setToolTip("Press Enter to add. End with @5pm, @tomorrow 9am or @30m to set a reminder.")
        self.input_icon = self.input.addAction(icons.icon("plus", "#000"), QLineEdit.ActionPosition.LeadingPosition)
        self.input_icon.triggered.connect(self._add_task)
        self.input.returnPressed.connect(self._add_task)
        self.input.textChanged.connect(self._update_hint)
        fl.addWidget(self.input)
        self.hint = QLabel()
        self.hint.setFont(theme.font(8.5, QFont.Weight.DemiBold))
        self.hint.setContentsMargins(8, 0, 0, 0)
        self.hint.hide()
        fl.addWidget(self.hint)
        lay.addWidget(self.footer)

        self.grip = ResizeGrip(self.card)
        # Invisible zones along every side and corner of the card: drag any of them to resize.
        E = Qt.Edge
        self.resize_edges = {edges: ResizeEdge(edges, self) for edges in (
            E.LeftEdge, E.RightEdge, E.TopEdge, E.BottomEdge, E.TopEdge | E.LeftEdge,
            E.TopEdge | E.RightEdge, E.BottomEdge | E.LeftEdge, E.BottomEdge | E.RightEdge)}

        # Ctrl + = / Ctrl + - change the text size, Ctrl + 0 resets it (while the note has focus).
        for keys, delta in (("Ctrl+=", 1), ("Ctrl++", 1), ("Ctrl+-", -1)):
            QShortcut(QKeySequence(keys), self, lambda d=delta: self.step_font_size(d))
        QShortcut(QKeySequence("Ctrl+0"), self,
                  lambda: self.step_font_size(DEFAULT_FONT_SIZE - self.note.font_size))

    # ------------------------------------------------------------------ theme
    def apply_theme(self) -> None:
        pal = self.pal = theme.palette(self.note.color, self.note.saturation)
        self._themed = (self.note.color, self.note.saturation)
        rgba = theme.rgba
        focus_bg = pal.wash(0.10) if pal.dark else QColor(255, 255, 255, 190)
        self.setStyleSheet(f"""
            QWidget {{ color: {rgba(pal.text)}; }}
            QScrollArea, QWidget#list {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0; }}
            QScrollBar::handle:vertical {{
                background: {rgba(pal.wash(0.16))}; border-radius: 3px; min-height: 30px; margin: 0 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {rgba(pal.wash(0.30))}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            QLineEdit#addInput {{
                background: {rgba(pal.wash(0.05))}; border: 1px solid transparent; border-radius: 10px;
                padding: 7px 8px 7px 2px; selection-background-color: {pal.accent};
            }}
            QLineEdit#addInput:focus {{ background: {rgba(focus_bg)}; border: 1px solid {rgba(pal.accent, 0.5)}; }}
            QLineEdit#inlineEdit, QLineEdit#titleEdit {{
                background: transparent; border: none; border-bottom: 2px solid {pal.accent};
                border-radius: 0; padding: 0 0 1px 0; selection-background-color: {pal.accent};
            }}
            QPushButton#link {{
                background: transparent; border: none; color: {rgba(pal.sub)}; text-align: left; padding: 10px 8px 10px 14px;
            }}
            QPushButton#link:hover {{ color: {pal.accent}; }}
        """ + theme.tooltip_qss())
        placeholder = self.input.palette()
        placeholder.setColor(QPalette.ColorRole.PlaceholderText, pal.ink(0.42))
        self.input.setPalette(placeholder)
        self.input_icon.setIcon(icons.icon("plus", pal.ink(0.45)))
        self.title_lbl.color = pal.text
        self.sub_lbl.color = pal.sub
        self.sub_lbl.update()
        self.hint.setStyleSheet(f"color: {pal.accent};")
        for b in self.header_buttons:
            b.set_colors(pal.ink(0.55), pal.wash(0.07))
        self.progress.set_colors(pal.wash(0.07), QColor(pal.accent))
        self.grip.color = pal.ink(0.22)
        self.update()

    # ------------------------------------------------------------------ list
    def rebuild(self) -> None:
        if self._editing or self._drag is not None:
            self._rebuild_pending = True
            return
        self._rebuild_pending = False
        note, today = self.note, date.today()
        daily = note.kind == "daily"
        self._task_font = theme.note_font(note.font_family, note.font_size)
        if self.input.font() != self._task_font:
            self.input.setFont(self._task_font)
        tasks = self.store.tasks_for(note.id)
        pending = [t for t in tasks if not t.done]
        pinned = [t for t in pending if t.pinned]
        unpinned = [t for t in pending if not t.pinned]
        if daily:
            done = [t for t in tasks if t.done and not t.archived and t.done_dt and t.done_dt.date() == today]
            carried = [t for t in unpinned if t.created_date < today]
            fresh = [t for t in unpinned if t.created_date >= today]
        else:
            done = [t for t in tasks if t.done and not t.archived]
            carried, fresh = [], unpinned
        done.sort(key=lambda t: t.done_at or "")

        self.title_lbl.setText(note.title)
        self.title_lbl.update()
        self.setWindowTitle(note.title)
        total = len(pending) + len(done)
        counts = f"{len(done)} of {total} done" if total else ""
        if daily:
            heading = f"{today:%A}, {today.day} {today:%B}"
            self.sub_lbl.setText(f"{heading}  ·  {counts}" if counts else heading)
        else:
            self.sub_lbl.setText(counts or "Checklist")
        self.progress.set_value(len(done) / total if total else 0.0)

        self.list.setUpdatesEnabled(False)
        while self.list_lay.count() > 1:
            item = self.list_lay.takeAt(0)
            if w := item.widget():
                w.hide()
                w.deleteLater()

        rows: dict[str, TaskRow] = {}

        def add(widget):
            self.list_lay.insertWidget(self.list_lay.count() - 1, widget)

        def add_rows(items, carried_over=False):
            for t in items:
                since = self._since(t.created_date, today) if carried_over and t.created_date < today else None
                rows[t.id] = row = self._row(t, since)
                add(row)

        # Each section is its own drag range, so pinned tasks stay above the rest.
        if pinned:
            add(self._section("Pinned", len(pinned)))
            add_rows(pinned, carried_over=daily)
        if carried:
            add(self._section("Carried over", len(carried)))
            add_rows(carried, carried_over=True)
        if fresh and (carried or pinned):
            add(self._section("Today" if daily else "Tasks", len(fresh)))
        add_rows(fresh)
        if not pending:
            if done:
                title = "All done for today" if daily else "Everything's checked"
                add(EmptyState(self.pal, title, "Nice work. Enjoy the rest of your day." if daily else "Clear completed items from the menu."))
            else:
                add(EmptyState(self.pal, "All clear", "Add your first task below."))
        if done:
            if note.completed == "strike":
                add(self._section("Completed", len(done)))
                add_rows(done)
            else:
                link = QPushButton(f"{len(done)} completed{' today' if daily else ''}  ·  View history")
                link.setObjectName("link")
                link.setFont(theme.font(8.8))
                link.setCursor(Qt.CursorShape.PointingHandCursor)
                link.clicked.connect(lambda: self.ctl.open_hub("completed"))
                add(link)
        entering, self._animate_in = self._animate_in, set()
        if not note.collapsed:
            m = self.list_lay.contentsMargins()
            width = self.list.width() - m.left() - m.right()
            for task_id in entering & rows.keys():
                rows[task_id].play_enter(width)
        self.list.setUpdatesEnabled(True)

        if self._scroll_to and self._scroll_to in rows:
            row = rows[self._scroll_to]
            # wait for the row to finish growing so it scrolls fully into view
            QTimer.singleShot(280 if MOTION else 0, row, lambda: self.scroll.ensureWidgetVisible(row, 0, 8))
        self._scroll_to = None

    def _section(self, title: str, count: int) -> QLabel:
        label = QLabel(f"{title.upper()}   {count}")
        f = theme.font(7.8, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
        label.setFont(f)
        label.setContentsMargins(14, 12, 0, 4)
        label.setStyleSheet(f"color: {theme.rgba(self.pal.ink(0.45))};")
        return label

    @staticmethod
    def _since(created: date, today: date) -> str:
        if (today - created).days == 1:
            return "Since yesterday"
        return f"Since {day_label(created, today)}"

    def _row(self, task: Task, since: str | None) -> TaskRow:
        row = TaskRow(task, self.pal, self._task_font, done=self._optimistic.get(task.id, task.done), since=since)
        row.toggled.connect(self._on_toggle)
        row.edited.connect(self._on_edit)
        row.deleted.connect(lambda t, r=row: self._remove_task(r, t))
        row.pin_toggled.connect(lambda t, r=row: self._toggle_pin(r, t))
        row.remind.connect(self._reminder_menu)
        row.editing.connect(self._on_editing)
        row.drag_started.connect(self._drag_start)
        row.drag_moved.connect(lambda pos: self._drag and self._drag.move(pos))
        row.drag_finished.connect(lambda: self._drag and self._drag.drop())
        return row

    # ------------------------------------------------------------------ task actions
    def _add_task(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        body, when = extract_reminder(text)
        self.input.clear()
        self._quiet = True
        try:
            task = self.store.add_task(self.note.id, body or "Reminder", when)
        finally:
            self._quiet = False
        self._animate_in.add(task.id)
        self._scroll_to = task.id
        self.rebuild()

    def _drag_start(self, row: TaskRow, press: QPoint) -> None:
        if self._drag is None and not self.note.collapsed:
            self._drag = RowDrag(self, row, press)

    def _finish_drag(self, drag: RowDrag, order: list[Task]) -> None:
        drag.ghost.hide()
        drag.ghost.deleteLater()
        self._drag = None
        current = [t.id for t in sorted(order, key=lambda t: t.order)]
        if [t.id for t in order] != current:
            self.store.reorder(order)   # saves and triggers a rebuild in the new order
        else:
            self.rebuild()

    def _remove_task(self, row: TaskRow, task: Task) -> None:
        row.play_exit()
        # The commit doesn't depend on the row surviving (a rebuild may replace it meanwhile).
        QTimer.singleShot(EXIT_MS if MOTION else 0, self,
                          lambda: self.store.task(task.id) and self.store.delete_task(task))

    def _toggle_pin(self, row: TaskRow, task: Task) -> None:
        """Slide the task out, then back in at the end of the pinned tasks (or at the top of the rest)."""
        row.play_exit()
        QTimer.singleShot(EXIT_MS if MOTION else 0, self, lambda: self._commit_pin(task.id))

    def _commit_pin(self, task_id: str) -> None:
        if task := self.store.task(task_id):
            self._animate_in.add(task_id)
            self._scroll_to = task_id
            self.store.set_pinned(task, not task.pinned)

    def _update_hint(self, text: str) -> None:
        _, when = extract_reminder(text)
        self.hint.setText(f"Reminder  ·  {friendly(when)}" if when else "")
        self.hint.setVisible(bool(when))

    def _on_toggle(self, row: TaskRow, task: Task, checked: bool) -> None:
        """Tick → strike through → pause → slide out → reappear in its new section."""
        self._optimistic[task.id] = checked
        row.set_done_visual(checked)
        hold = (600 if checked else 300) if MOTION else 0
        QTimer.singleShot(hold, row, row.play_exit)
        QTimer.singleShot(hold + (EXIT_MS if MOTION else 0), self, lambda: self._commit_toggle(task.id))

    def _commit_toggle(self, task_id: str) -> None:
        checked = self._optimistic.pop(task_id, None)
        task = self.store.task(task_id)
        if checked is None or task is None:
            return
        self._animate_in.add(task_id)
        if task.done != checked:
            self.store.set_done(task, checked)
        else:
            self.rebuild()

    def _on_edit(self, task: Task, text: str) -> None:
        body, when = extract_reminder(text)
        if not body:
            self.store.delete_task(task)
        elif when:
            self.store.update_task(task, text=body, remind_at=to_iso(when), reminded=False)
        else:
            self.store.update_task(task, text=body)

    def _on_editing(self, on: bool) -> None:
        self._editing = max(0, self._editing + (1 if on else -1))
        if not self._editing and self._rebuild_pending:
            QTimer.singleShot(0, self, self.rebuild)

    def _set_reminder(self, task: Task, when: datetime | None) -> None:
        self.store.update_task(task, remind_at=to_iso(when), reminded=False)

    def _pick_reminder(self, task: Task) -> None:
        start = task.remind_dt or (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        when = pick_datetime(self, start)
        if when:
            self._set_reminder(task, when)

    def _reminder_menu(self, task: Task, anchor: QWidget) -> None:
        menu = make_menu(self, self.pal.dark)
        for label, when in reminder_presets():
            add_action(menu, label, lambda _=False, w=when: self._set_reminder(task, w), icon="clock")
        add_action(menu, "Pick date && time…", lambda: self._pick_reminder(task), icon="bell")
        if task.remind_at:
            menu.addSeparator()
            add_action(menu, "Remove reminder", lambda: self._set_reminder(task, None), icon="x", danger=True)
        menu.exec(anchor.mapToGlobal(QPoint(0, anchor.height() + 4)))

    # ------------------------------------------------------------------ note actions
    def _new_menu(self) -> None:
        menu = make_menu(self, self.pal.dark)
        add_menu_label(menu, "New note in colour")
        add_swatches(menu, "", lambda key: self.ctl.new_note("daily", near=self, color=key))
        menu.addSeparator()
        add_action(menu, "New daily note", lambda: self.ctl.new_note("daily", near=self), icon="plus")
        add_action(menu, "New checklist", lambda: self.ctl.new_note("checklist", near=self), icon="note")
        menu.exec(self.btn_new.mapToGlobal(QPoint(0, self.btn_new.height() + 4)))

    def _more_menu(self) -> None:
        n, store = self.note, self.store
        menu = make_menu(self, self.pal.dark)
        add_menu_label(menu, "Colour")
        add_swatches(menu, n.color, lambda key: (store.update_note(n, color=key), slider.set_key(key)),
                     keep_open=True)
        slider = add_saturation(menu, n.color, n.saturation, self._preview_saturation,
                                lambda v: store.update_note(n, saturation=v))
        add_menu_label(menu, "Text")
        add_stepper(menu, "Size", self._size_label(), self.step_font_size)
        fonts = add_submenu(menu, "Font")
        add_font_list(fonts, n.font_family, lambda family: store.update_note(n, font_family=family))
        fonts.addSeparator()
        add_action(fonts, "Use this font && size on all notes",
                   lambda: self.ctl.apply_font_all(n.font_family, n.font_size), icon="blank")
        menu.addSeparator()
        add_action(menu, "New daily note", lambda: self.ctl.new_note("daily", near=self), icon="plus")
        add_action(menu, "New checklist", lambda: self.ctl.new_note("checklist", near=self), icon="note")
        menu.addSeparator()
        pos = add_submenu(menu, "Position")
        add_action(pos, "Stick to desktop", lambda: self.set_pin("desktop"), checked=n.pin == "desktop")
        add_action(pos, "Always on top", lambda: self.set_pin("top"), checked=n.pin == "top")
        comp = add_submenu(menu, "Completed tasks")
        add_action(comp, "Show with strikethrough", lambda: store.update_note(n, completed="strike"),
                   checked=n.completed == "strike")
        add_action(comp, "Hide from note", lambda: store.update_note(n, completed="hide"),
                   checked=n.completed == "hide")
        kind = add_submenu(menu, "Note type")
        add_action(kind, "Daily to-do (unfinished tasks carry over)", lambda: store.update_note(n, kind="daily"),
                   checked=n.kind == "daily")
        add_action(kind, "Checklist", lambda: store.update_note(n, kind="checklist"), checked=n.kind == "checklist")
        has_done = any(t.done and not t.archived for t in store.tasks_for(n.id))
        add_action(menu, "Clear completed", lambda: store.clear_completed(n.id), icon="check", enabled=has_done)
        add_action(menu, "Rename", self.begin_rename, icon="blank")
        menu.addSeparator()
        add_action(menu, "History && settings…", lambda: self.ctl.open_hub("completed"), icon="clock")
        add_action(menu, "Hide note", self.hide_note, icon="eye_off")
        add_action(menu, "Delete note…", self._delete, icon="trash", danger=True)
        menu.exec(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height() + 4)))

    def _preview_saturation(self, value: float) -> None:
        """While the slider is dragged only the card background changes - a cheap repaint, no rebuild."""
        self.note.saturation = value          # saved when the slider is released
        self.pal = theme.palette(self.note.color, value)
        self.update()

    def _size_label(self) -> str:
        return f"{self.note.font_size:g} pt"

    def step_font_size(self, delta: float) -> str:
        """Grow or shrink the note's text; returns the new size for the menu's readout."""
        low, high = theme.FONT_SIZES
        size = min(high, max(low, self.note.font_size + delta))
        if size != self.note.font_size:
            self.store.update_note(self.note, font_size=size)
        return self._size_label()

    def eventFilter(self, obj, e):
        # Ctrl + mouse wheel over the task list changes the text size.
        if e.type() == QEvent.Type.Wheel and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if e.angleDelta().y():
                self.step_font_size(1 if e.angleDelta().y() > 0 else -1)
            return True
        return super().eventFilter(obj, e)

    # title renaming affordance
    def over_title(self, pos: QPoint) -> bool:
        lbl = self.title_lbl
        return lbl.isVisible() and lbl.text_rect().translated(lbl.pos()).contains(pos)

    def set_title_hover(self, on: bool) -> None:
        highlight = self.pal.wash(0.06) if on else None
        if (self.title_lbl.highlight is None) == (highlight is None):
            return
        self.title_lbl.highlight = highlight
        self.title_lbl.update()
        self.header.setCursor(Qt.CursorShape.IBeamCursor if on else Qt.CursorShape.OpenHandCursor)
        self.header.setToolTip("Click to rename" if on else "")

    def set_pin(self, mode: str) -> None:
        self.store.update_note(self.note, emit=False, pin=mode)
        self.apply_pin()

    def apply_pin(self) -> None:
        system.remove_frame(self)
        if self.note.pin == "top":
            system.set_topmost(self)
        else:
            system.pin_to_desktop(self)

    def hide_note(self) -> None:
        self._fade(self.windowOpacity(), 0.0, then=lambda: self.ctl.hide_note(self.note))

    def _fade(self, start: float, end: float, then=None) -> None:
        if self._fade_anim:
            self._fade_anim.stop()
        self._fade_anim = animation(self, 180, self.setWindowOpacity)
        if then:
            self._fade_anim.finished.connect(then)
        animate(self._fade_anim, start, end)

    def _delete(self) -> None:
        count = len(self.store.tasks_for(self.note.id))
        box = QMessageBox(QMessageBox.Icon.NoIcon, "Delete note",
                          f"Move “{self.note.title}” and its {count} task{'s' if count != 1 else ''} "
                          "to the Recycle Bin?\nYou can restore it from there.",
                          QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes, self)
        box.button(QMessageBox.StandardButton.Yes).setText("Delete")
        box.setStyleSheet("QMessageBox { background: #FFFFFF; } QLabel { color: #1C1C1E; }")
        if box.exec() == QMessageBox.StandardButton.Yes:
            self._fade(self.windowOpacity(), 0.0, then=lambda: self.store.delete_note(self.note))

    def begin_rename(self) -> None:
        if self._title_edit:
            return
        ed = InlineEdit(self.note.title, self.header)
        ed.setObjectName("titleEdit")
        ed.setFont(self.title_lbl.font())
        ed.setFixedHeight(self.title_lbl.height())
        self.set_title_hover(False)
        ed.committed.connect(self._finish_rename)
        ed.cancelled.connect(lambda: self._finish_rename(None))
        self.title_lbl.hide()
        self.titles.insertWidget(0, ed)
        self._title_edit = ed
        self.activateWindow()
        ed.setFocus()
        ed.selectAll()

    def _finish_rename(self, text: str | None) -> None:
        ed, self._title_edit = self._title_edit, None
        if ed is None:
            return
        ed.hide()
        ed.deleteLater()
        self.title_lbl.show()
        if text and text.strip() and text.strip() != self.note.title:
            self.store.update_note(self.note, title=text.strip())

    def _collapsing(self) -> bool:
        return bool(self._collapse_anim and self._collapse_anim.state() == QAbstractAnimation.State.Running)

    def toggle_collapsed(self) -> None:
        if self._collapsing():
            return
        self.store.update_note(self.note, emit=False, collapsed=not self.note.collapsed)
        self._apply_collapsed(animated=True)

    def _apply_collapsed(self, animated: bool = False) -> None:
        collapsed = self.note.collapsed
        content = (self.progress_wrap, self.scroll, self.footer)
        self.btn_collapse.name = "chevron_down" if collapsed else "chevron_up"
        self.btn_collapse.setToolTip("Expand" if collapsed else "Collapse")
        self.btn_collapse.update()
        target = self._collapsed_height() if collapsed else max(self.note.h, MIN_SIZE.height())
        start = self.height()

        if not (animated and MOTION) or start == target:
            for w in content:
                w.setVisible(not collapsed)
            self._show_resizers(not collapsed)
            self._lock_height(collapsed, target)
            self.resize(self.width(), target)
            return

        # Roll the card up/down: freeze the content where it is and let the moving bottom edge clip it.
        card_lay = self.card.layout()
        self._show_resizers(False)
        if not collapsed:
            for w in content:
                w.show()
            inner = target - MARGINS.top() - MARGINS.bottom()
            card_lay.setGeometry(QRect(0, 0, self.card.width(), inner))  # lay out at the final size first
        card_lay.setEnabled(False)
        self.setMinimumHeight(min(start, target))
        self.setMaximumHeight(QWIDGETSIZE_MAX)

        def step(v):
            self.resize(self.width(), round(start + (target - start) * v))

        def done():
            if collapsed:
                for w in content:
                    w.hide()
            card_lay.setEnabled(True)
            self._lock_height(collapsed, target)
            self.resize(self.width(), target)
            card_lay.activate()
            self._show_resizers(not collapsed)
            self.update()

        self._collapse_anim = animation(self, 280, step, QEasingCurve.Type.OutCubic)
        self._collapse_anim.finished.connect(done)
        animate(self._collapse_anim, 0.0, 1.0)

    def _show_resizers(self, on: bool) -> None:
        """A collapsed note can only get wider or narrower, so only its left and right edges stay active."""
        self.grip.setVisible(on)
        for edges, zone in self.resize_edges.items():
            zone.setVisible(on or edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge))
        self._place_resizers()

    def _place_resizers(self) -> None:
        c = self.card_rect().toRect()
        out, inside, corner = EDGE_OUT, EDGE_IN, EDGE_CORNER
        band, reach = out + inside, out + corner
        left, top = c.left() - out, c.top() - out
        right, bottom = c.left() + c.width() - inside, c.top() + c.height() - inside
        far_x, far_y = c.left() + c.width() - corner, c.top() + c.height() - corner
        side_y, side_h = c.top() + corner, max(0, c.height() - 2 * corner)
        if self.resize_edges[Qt.Edge.TopEdge].isHidden():   # collapsed: the sides run the full height
            side_y, side_h = c.top(), c.height()
        E = Qt.Edge
        for edges, rect in (
                (E.LeftEdge, (left, side_y, band, side_h)),
                (E.RightEdge, (right, side_y, band, side_h)),
                (E.TopEdge, (c.left() + corner, top, max(0, c.width() - 2 * corner), band)),
                (E.BottomEdge, (c.left() + corner, bottom, max(0, c.width() - 2 * corner), band)),
                (E.TopEdge | E.LeftEdge, (left, top, reach, reach)),
                (E.TopEdge | E.RightEdge, (far_x, top, reach, reach)),
                (E.BottomEdge | E.LeftEdge, (left, far_y, reach, reach)),
                (E.BottomEdge | E.RightEdge, (far_x, far_y, reach, reach))):
            self.resize_edges[edges].setGeometry(*rect)

    def _collapsed_height(self) -> int:
        return (MARGINS.top() + MARGINS.bottom() + CARD_PADDING.top() + CARD_PADDING.bottom()
                + self.header.sizeHint().height())

    def _lock_height(self, collapsed: bool, height: int) -> None:
        if collapsed:
            self.setMinimumHeight(height)
            self.setMaximumHeight(height)
        else:
            self.setMaximumHeight(QWIDGETSIZE_MAX)
            self.setMinimumHeight(MIN_SIZE.height())

    def focus_input(self) -> None:
        self.raise_()
        self.activateWindow()
        if self.note.collapsed:
            self.toggle_collapsed()
        self.input.setFocus()

    # ------------------------------------------------------------------ store events
    def _on_note_changed(self, note_id: str) -> None:
        if note_id != self.note.id or self._quiet:
            return
        if (self.note.color, self.note.saturation) != self._themed:
            self.apply_theme()
        self.rebuild()

    # ------------------------------------------------------------------ geometry
    def _restore_geometry(self) -> None:
        n = self.note
        if n.x is None or n.y is None:
            pos = self.ctl.default_position(QSize(n.w, n.h))
            n.x, n.y = pos.x(), pos.y()
            self.store.update_note(n, emit=False)
        self.setGeometry(screens.place(n, self.ctl.layout_key, MARGINS, MIN_SIZE))
        self._apply_collapsed()

    def fit_to_screens(self) -> None:
        """Put the note back where it belongs for the monitors connected now."""
        if self._collapsing():
            return
        rect = screens.place(self.note, self.ctl.layout_key, MARGINS, MIN_SIZE)
        if self.note.collapsed:
            rect.setHeight(self.height())
        if rect != self.geometry():
            self.setGeometry(rect)

    def _save_geometry(self) -> None:
        if self.ctl.settling or screens.current_key() != self.ctl.layout_key:
            return   # the monitors are changing: Windows is moving the note, not the user
        g = self.geometry()
        h = self.note.h if self.note.collapsed else g.height()
        self.store.update_note(self.note, emit=False, x=g.x(), y=g.y(), w=g.width(), h=h,
                               layouts=screens.remember(self.note, self.ctl.layout_key,
                                                        QRect(g.x(), g.y(), g.width(), h)))

    def moveEvent(self, e):
        self._geo_timer.start()

    def resizeEvent(self, e):
        cw = self.width() - MARGINS.left() - MARGINS.right()
        ch = self.height() - MARGINS.top() - MARGINS.bottom()
        self.grip.move(cw - self.grip.width() - 3, ch - self.grip.height() - 3)
        self._place_resizers()
        self._geo_timer.start()

    def showEvent(self, e):
        super().showEvent(e)
        if not self._faded_in:
            self._faded_in = True
            if MOTION:
                self._fade(0.0, 1.0)
        QTimer.singleShot(0, self, self.apply_pin)

    # ------------------------------------------------------------------ painting
    def card_rect(self) -> QRectF:
        return QRectF(self.rect()).marginsRemoved(QMarginsF(MARGINS))

    def _set_hover(self, value) -> None:
        self._hover_t = float(value)
        self.update()
        self.header.update()

    def enterEvent(self, e):
        animate(self._hover_anim, self._hover_t, 1.0)
        for b in self.header_buttons:
            b.set_revealed(True)
        self.title_lbl.reserve = self.header.actions.width() + 6   # keep the title clear of the buttons
        self.title_lbl.update()

    def leaveEvent(self, e):
        animate(self._hover_anim, self._hover_t, 0.0)
        for b in self.header_buttons:
            b.set_revealed(False)
        self.title_lbl.reserve = 0
        self.title_lbl.update()

    def _paint_shadow(self, p: QPainter) -> None:
        dpr, card = self.devicePixelRatioF(), self.card_rect()
        weights = ((shadow.REST, 1.0 - self._hover_t), (shadow.HOVER, self._hover_t))
        patches = [(shadow.nine_patch(MARGINS, RADIUS, layers, dpr), w) for layers, w in weights]
        if self._collapsing() or all(patch.fits(card.size()) for patch, _ in patches):
            # Stretchable shadow: no re-blurring while resizing or animating.
            for patch, weight in patches:
                if weight > 0.001:
                    p.setOpacity(weight)
                    patch.draw(p, self.width(), self.height())
        else:
            # A collapsed card is too small to stretch from - render it exactly, once per size.
            key = (self.size().toTuple(), dpr)
            if not self._exact_shadow or self._exact_shadow[0] != key:
                self._exact_shadow = (key, shadow.render(self.size(), card, RADIUS, shadow.REST, dpr),
                                      shadow.render(self.size(), card, RADIUS, shadow.HOVER, dpr))
            for pixmap, (_, weight) in zip(self._exact_shadow[1:], weights):
                if weight > 0.001:
                    p.setOpacity(weight)
                    p.drawPixmap(0, 0, pixmap)
        p.setOpacity(1.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._paint_shadow(p)

        r = self.card_rect()
        path = QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        p.fillPath(path, QColor(self.pal.bg))
        if not self.pal.dark:
            sheen = QLinearGradient(r.topLeft(), QPointF(r.left(), r.top() + 110))
            sheen.setColorAt(0, QColor(255, 255, 255, 110))
            sheen.setColorAt(1, QColor(255, 255, 255, 0))
            p.fillPath(path, sheen)
        border = QColor(255, 255, 255, 24) if self.pal.dark else QColor(0, 0, 0, 20)
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS - 0.5, RADIUS - 0.5)
