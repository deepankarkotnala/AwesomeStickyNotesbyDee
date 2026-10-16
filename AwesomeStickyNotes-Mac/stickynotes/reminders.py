"""Reminder scheduler and the toast cards it pops up in the corner of the screen."""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import (QEasingCurve, QMargins, QMarginsF, QObject, QPoint,
                            QPropertyAnimation, QRectF, Qt, QTimer)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from . import icons, shadow, system, theme
from .store import Note, Task, to_iso
from .timeparse import friendly
from .widgets import IconButton, PillButton

MAX_TOASTS = 4
MARGINS = QMargins(18, 12, 18, 26)
RADIUS = 14.0
SHADOW = ((3, 1, 0.12), (30, 12, 0.22))


class BellBadge(QWidget):
    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self.setFixedSize(38, 38)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.accent)
        p.drawEllipse(QRectF(1, 1, 36, 36))
        icons.paint(p, "bell", QRectF(10, 10, 18, 18), "#FFFFFF", 2.2)


class Toast(QWidget):
    def __init__(self, service: "ReminderService", task: Task, note: Note | None):
        super().__init__(None, system.window_flags("toast"))
        system.prepare(self)
        self.service, self.task_id = service, task.id
        self.note_id = note.id if note else None
        self.pal = theme.palette(note.color, note.saturation) if note else theme.palette("cloud")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(400)
        self._shadow = None
        pal, rgba = self.pal, theme.rgba

        root = QVBoxLayout(self)
        root.setContentsMargins(MARGINS)
        card = QWidget()
        root.addWidget(card)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 14, 10, 14)
        lay.setSpacing(12)
        lay.addWidget(BellBadge(pal.accent), 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        caption = QLabel("REMINDER" + (f"  ·  {note.title.upper()}" if note else ""))
        f = theme.font(7.6, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
        caption.setFont(f)
        caption.setStyleSheet(f"color: {rgba(pal.ink(0.5))};")
        text = QLabel(task.text)
        text.setWordWrap(True)
        text.setFont(theme.font(11.5, QFont.Weight.DemiBold))
        text.setStyleSheet(f"color: {rgba(pal.text)};")
        when = QLabel(friendly(task.remind_dt) if task.remind_dt else "")
        when.setFont(theme.font(9))
        when.setStyleSheet(f"color: {rgba(pal.sub)};")
        col.addWidget(caption)
        col.addSpacing(2)
        col.addWidget(text)
        col.addWidget(when)
        col.addSpacing(8)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        done = PillButton("Mark done", pal.accent, primary=True)
        snooze = PillButton(f"Snooze {service.store.settings.snooze_minutes} min", pal.accent, dark=pal.dark)
        done.clicked.connect(lambda: service.complete(self))
        snooze.clicked.connect(lambda: service.snooze(self))
        buttons.addWidget(done)
        buttons.addWidget(snooze)
        buttons.addStretch(1)
        col.addLayout(buttons)
        lay.addLayout(col, 1)

        close = IconButton("x", pal.ink(0.5), 26, 14, "Dismiss", pal.wash(0.07))
        close.clicked.connect(lambda: service.dismiss(self))
        lay.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        self._move_anim = QPropertyAnimation(self, b"pos", self)
        self._move_anim.setDuration(320)
        self._move_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(240)

    def slide_to(self, target: QPoint) -> None:
        self._move_anim.stop()
        self._move_anim.setStartValue(self.pos())
        self._move_anim.setEndValue(target)
        self._move_anim.start()

    def fade(self, start: float, end: float, then=None) -> None:
        self._fade_anim.stop()
        self._fade_anim.setStartValue(start)
        self._fade_anim.setEndValue(end)
        if then:
            self._fade_anim.finished.connect(then)
        self._fade_anim.start()

    def showEvent(self, e):
        super().showEvent(e)
        system.remove_frame(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.note_id:
            self.service.ctl.focus_note(self.note_id)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).marginsRemoved(QMarginsF(MARGINS))
        if self._shadow is None or self._shadow.deviceIndependentSize().toSize() != self.size():
            self._shadow = shadow.render(self.size(), card, RADIUS, SHADOW, self.devicePixelRatioF())
        p.drawPixmap(0, 0, self._shadow)
        path = QPainterPath()
        path.addRoundedRect(card, RADIUS, RADIUS)
        p.fillPath(path, QColor(self.pal.bg))
        border = QColor(255, 255, 255, 24) if self.pal.dark else QColor(0, 0, 0, 22)
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(card.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS - 0.5, RADIUS - 0.5)


class ReminderService(QObject):
    def __init__(self, controller):
        super().__init__(controller)
        self.ctl, self.store = controller, controller.store
        self.toasts: list[Toast] = []
        self.timer = QTimer(self, interval=15_000)
        self.timer.timeout.connect(self.check)
        self.timer.start()
        QTimer.singleShot(1500, self, self.check)  # catch reminders missed while the app was closed

    def due(self) -> list[Task]:
        now = datetime.now()
        return sorted((t for t in self.store.tasks
                       if t.remind_dt and not t.reminded and not t.done and t.remind_dt <= now),
                      key=lambda t: t.remind_at)

    def check(self) -> None:
        shown = 0
        for task in self.due():
            if len(self.toasts) >= MAX_TOASTS:
                break  # the rest stay queued until a toast is dismissed
            self.store.update_task(task, reminded=True)
            self._show(task)
            shown += 1
        if shown:
            self._chime()

    @staticmethod
    def _chime() -> None:
        system.chime()

    def _show(self, task: Task) -> None:
        toast = Toast(self, task, self.store.note(task.note_id))
        toast.adjustSize()
        self.toasts.append(toast)
        toast.setWindowOpacity(0.0)
        self._layout(new=toast)
        toast.show()
        toast.fade(0.0, 1.0)

    def _layout(self, new: Toast | None = None) -> None:
        area = QGuiApplication.primaryScreen().availableGeometry()
        y = area.bottom() + 1
        for toast in reversed(self.toasts):  # newest at the bottom
            y -= toast.height()
            target = QPoint(area.right() + 1 - toast.width(), y)
            if toast is new:
                toast.move(target + QPoint(0, 30))
            toast.slide_to(target)
            y += MARGINS.top() + MARGINS.bottom() - 10  # overlap the transparent shadow margins

    def dismiss(self, toast: Toast) -> None:
        if toast not in self.toasts:
            return
        self.toasts.remove(toast)
        toast.fade(toast.windowOpacity(), 0.0, then=lambda: (toast.close(), toast.deleteLater()))
        self._layout()
        QTimer.singleShot(400, self, self.check)

    def complete(self, toast: Toast) -> None:
        if task := self.store.task(toast.task_id):
            self.store.set_done(task, True)
        self.dismiss(toast)

    def snooze(self, toast: Toast) -> None:
        if task := self.store.task(toast.task_id):
            minutes = self.store.settings.snooze_minutes
            when = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=minutes)
            self.store.update_task(task, remind_at=to_iso(when), reminded=False)
        self.dismiss(toast)
