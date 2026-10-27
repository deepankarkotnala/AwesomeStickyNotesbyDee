"""Reusable, custom-painted widgets shared by notes, toasts and the hub."""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import (QDate, QEasingCurve, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation,
                            Signal)
from PySide6.QtGui import (QColor, QConicalGradient, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen, QTextCharFormat, QTextLayout, QTextOption)
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QCalendarWidget, QComboBox,
                               QDateTimeEdit, QDialog, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget, QWidgetAction)

from . import icons, repeat, system, theme
from .store import Task
from .theme import Palette
from .timeparse import friendly

# Follow Windows' "Animation effects" accessibility setting: when it's off, every animation jumps to its end.
MOTION = system.animations_enabled()
QWIDGETSIZE_MAX = 16777215
ENTER_MS, EXIT_MS, STRIKE_MS = 260, 200, 320


def animation(owner, ms: int, on_value, curve=QEasingCurve.Type.OutCubic) -> QVariantAnimation:
    """A short-lived animation: it only ticks while running, then costs nothing."""
    a = QVariantAnimation(owner)
    a.setDuration(ms if MOTION else 0)
    a.setEasingCurve(curve)
    a.valueChanged.connect(on_value)
    return a


def animate(anim: QVariantAnimation, start: float, end: float) -> None:
    anim.stop()
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.start()


def mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(*(a.getRgbF()[i] * (1 - t) + b.getRgbF()[i] * t for i in range(4)))


# ------------------------------------------------------------------ buttons
class IconButton(QAbstractButton):
    """Flat square icon button with a soft rounded hover background; can fade in/out."""

    def __init__(self, name: str, color: QColor, size: int = 26, icon_size: int = 16,
                 tooltip: str = "", hover_bg: QColor | None = None, parent=None):
        super().__init__(parent)
        self.name, self.color = name, QColor(color)
        self.icon_px = icon_size
        self.hover_bg = hover_bg or (QColor(255, 255, 255, 26) if theme.ui().dark else QColor(0, 0, 0, 16))
        self._hover = False
        self._opacity = 1.0
        self._fade = animation(self, 140, self._set_opacity)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)

    def set_colors(self, color: QColor, hover_bg: QColor) -> None:
        self.color, self.hover_bg = QColor(color), QColor(hover_bg)
        self.update()

    def set_revealed(self, revealed: bool, animated: bool = True) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not revealed)
        target = 1.0 if revealed else 0.0
        if animated:
            animate(self._fade, self._opacity, target)
        else:
            self._set_opacity(target)

    def _set_opacity(self, v) -> None:
        self._opacity = float(v)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        if self._opacity <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)
        if self._hover or self.isDown():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.hover_bg)
            p.drawRoundedRect(QRectF(self.rect()), 7, 7)
        s = self.icon_px
        icons.paint(p, self.name, QRectF((self.width() - s) / 2, (self.height() - s) / 2, s, s), self.color)


def heart_path(r: QRectF) -> QPainterPath:
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    p = QPainterPath()
    p.moveTo(x + w / 2, y + h * 0.95)
    p.cubicTo(x + w * 0.02, y + h * 0.62, x - w * 0.04, y + h * 0.18, x + w * 0.27, y + h * 0.08)
    p.cubicTo(x + w * 0.39, y + h * 0.04, x + w * 0.48, y + h * 0.12, x + w / 2, y + h * 0.22)
    p.cubicTo(x + w * 0.52, y + h * 0.12, x + w * 0.61, y + h * 0.04, x + w * 0.73, y + h * 0.08)
    p.cubicTo(x + w * 1.04, y + h * 0.18, x + w * 0.98, y + h * 0.62, x + w / 2, y + h * 0.95)
    p.closeSubpath()
    return p


def check_shape(shape: str, r: QRectF) -> QPainterPath:
    """The outline of a checkbox: "circle", "square" (rounded) or "heart"."""
    if shape == "heart":
        return heart_path(r.adjusted(-1.2, -1.2, 1.2, 1.2))
    path = QPainterPath()
    if shape == "square":
        path.addRoundedRect(r, 4.5, 4.5)
    else:
        path.addEllipse(r)
    return path


class CheckCircle(QAbstractButton):
    """Animated checkbox in the style of Apple Reminders: a circle, a rounded square or a heart."""

    def __init__(self, accent: QColor, ring: QColor, parent=None, shape: str = "circle"):
        super().__init__(parent)
        self.accent, self.ring, self.shape = QColor(accent), QColor(ring), shape
        self.setCheckable(True)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._t = 0.0
        self._hover = False
        self._anim = animation(self, 260, self._set_t, QEasingCurve.Type.OutBack)
        self.toggled.connect(lambda on: animate(self._anim, self._t, 1.0 if on else 0.0))

    def set_checked_silently(self, on: bool) -> None:
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._t = 1.0 if on else 0.0
        self.update()

    def _set_t(self, v) -> None:
        self._t = float(v)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(2, 2, 16, 16)
        t = max(0.0, min(self._t, 1.15))
        mark = r.adjusted(4.4, 3.4, -4.4, -5.0) if self.shape == "heart" else r.adjusted(3.6, 3.8, -3.6, -3.4)
        if t < 1.0:
            ring = self.accent if self._hover else self.ring
            p.setPen(QPen(ring, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(check_shape(self.shape, r))
            if self._hover and t < 0.05:  # preview of the check mark
                c = QColor(self.accent)
                c.setAlphaF(0.55)
                icons.paint(p, "check", mark.adjusted(-0.4, -0.4, 0.4, 0.4), c, 3.0)
        if t > 0.0:
            scale = 0.55 + 0.45 * t
            fill = QRectF(0, 0, r.width() * scale, r.height() * scale)
            fill.moveCenter(r.center())
            p.setOpacity(min(1.0, t))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.accent)
            p.drawPath(check_shape(self.shape, fill))
            icons.paint(p, "check", mark, QColor("#FFFFFF"), 3.2)


class Pill(QAbstractButton):
    """Small rounded label, optionally with an icon - used for reminder times and 'since' badges."""

    def __init__(self, text: str, fg: QColor, bg: QColor, icon: str | None = None, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.fg, self.bg, self.icon_name = QColor(fg), QColor(bg), icon
        self.setFont(theme.font(8.2, QFont.Weight.DemiBold))
        fm = QFontMetrics(self.font())
        self.setFixedSize(fm.horizontalAdvance(text) + (30 if icon else 16), 20)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.bg)
        p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        x = 8
        if self.icon_name:
            icons.paint(p, self.icon_name, QRectF(7, 4, 12, 12), self.fg, 2.4)
            x = 22
        p.setPen(self.fg)
        p.setFont(self.font())
        p.drawText(QRectF(x, 0, self.width() - x - 8, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text())


class PillButton(QPushButton):
    """A rounded button: filled with `accent` when primary, else a soft grey that suits a light or dark
    background (`dark`; by default the app's own light or dark windows)."""

    def __init__(self, text: str, accent: str, primary: bool = False, dark: bool | None = None, small: bool = False,
                 parent=None):
        super().__init__(text, parent)
        dark = theme.ui().dark if dark is None else dark
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(theme.font(8.4 if small else 9, QFont.Weight.DemiBold))
        shape = "border-radius: 11px; padding: 0 9px;" if small else "border-radius: 8px; padding: 6px 12px;"
        if small:
            self.setFixedHeight(23)   # Qt drops the rounding when the radius is over half the height
        if primary:
            bg, fg, hover = accent, "#FFFFFF", theme.rgba(QColor(accent).darker(112))
        else:
            ink = "#FFFFFF" if dark else "#000000"
            bg, fg, hover = theme.rgba(ink, 0.07), ("#F2F2F5" if dark else "#1C1C1E"), theme.rgba(ink, 0.12)
        self.setStyleSheet(f"""
            QPushButton {{ background: {bg}; color: {fg}; border: none; {shape} }}
            QPushButton:hover {{ background: {hover}; }}
        """)


# ------------------------------------------------------------------ note bits
class ProgressLine(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self.track, self.fill = QColor(0, 0, 0, 20), QColor("#0A84FF")
        self._shown = 0.0
        self._anim = animation(self, 420, self._set)

    def set_colors(self, track: QColor, fill: QColor) -> None:
        self.track, self.fill = QColor(track), QColor(fill)
        self.update()

    def set_value(self, value: float) -> None:
        animate(self._anim, self._shown, max(0.0, min(1.0, value)))

    def _set(self, v) -> None:
        self._shown = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        r = QRectF(self.rect())
        p.setBrush(self.track)
        p.drawRoundedRect(r, 2, 2)
        if self._shown > 0.001:
            p.setBrush(self.fill)
            p.drawRoundedRect(QRectF(0, 0, max(4.0, r.width() * self._shown), r.height()), 2, 2)


class ResizeEdge(QWidget):
    """An invisible zone along a side or corner of a frameless window; dragging it resizes from there."""
    released = Signal(QRect)    # after a resize we drove ourselves: the window's geometry when it began

    def __init__(self, edges: Qt.Edge, parent=None):
        super().__init__(parent)
        self.edges = edges
        self._manual: tuple[QPoint, QRect] | None = None
        E, C = Qt.Edge, Qt.CursorShape
        if edges in (E.LeftEdge, E.RightEdge):
            cursor = C.SizeHorCursor
        elif edges in (E.TopEdge, E.BottomEdge):
            cursor = C.SizeVerCursor
        elif edges in (E.TopEdge | E.LeftEdge, E.BottomEdge | E.RightEdge):
            cursor = C.SizeFDiagCursor
        else:
            cursor = C.SizeBDiagCursor
        self.setCursor(cursor)

    def paintEvent(self, e):
        # Not quite transparent: fully transparent pixels of a translucent window let clicks fall through.
        QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 1))

    def mousePressEvent(self, e):
        self._manual = None
        if e.button() != Qt.MouseButton.LeftButton:
            return
        handle = self.window().windowHandle()
        if handle and handle.startSystemResize(self.edges):
            return
        # macOS has no system resize for frameless windows: follow the mouse ourselves.
        self._manual = (e.globalPosition().toPoint(), self.window().geometry())

    def mouseMoveEvent(self, e):
        if not self._manual:
            return
        origin, r = self._manual
        delta = e.globalPosition().toPoint() - origin
        low = self.window().minimumSize()
        g = QRect(r)
        E = Qt.Edge
        if self.edges & E.LeftEdge:
            g.setLeft(min(r.left() + delta.x(), r.right() - low.width() + 1))
        if self.edges & E.RightEdge:
            g.setRight(max(r.right() + delta.x(), r.left() + low.width() - 1))
        if self.edges & E.TopEdge:
            g.setTop(min(r.top() + delta.y(), r.bottom() - low.height() + 1))
        if self.edges & E.BottomEdge:
            g.setBottom(max(r.bottom() + delta.y(), r.top() + low.height() - 1))
        self.window().setGeometry(g)

    def mouseReleaseEvent(self, e):
        manual, self._manual = self._manual, None
        if manual:
            self.released.emit(manual[1])


class ResizeGrip(ResizeEdge):
    """The visible dotted grip in the bottom-right corner."""

    def __init__(self, parent=None):
        super().__init__(Qt.Edge.RightEdge | Qt.Edge.BottomEdge, parent)
        self.color = QColor(0, 0, 0, 60)
        self.setFixedSize(14, 14)

    def paintEvent(self, e):
        p = QPainter(self)
        icons.paint(p, "grip", QRectF(1, 1, 12, 12), self.color)


class InlineEdit(QLineEdit):
    committed = Signal(str)
    cancelled = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("inlineEdit")
        self._finished = False
        self.returnPressed.connect(self._commit)

    def _commit(self):
        if not self._finished:
            self._finished = True
            self.committed.emit(self.text())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            if not self._finished:
                self._finished = True
                self.cancelled.emit()
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self._commit()


class RowActions(QWidget):
    """Small button strip that fades the text underneath into the row's hover colour."""

    def __init__(self, bg: QColor, parent=None):
        super().__init__(parent)
        self.bg = bg
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(18, 0, 0, 0)
        self.lay.setSpacing(0)

    def add(self, *buttons: QWidget) -> None:
        for b in buttons:
            self.lay.addWidget(b)

    def paintEvent(self, e):
        p = QPainter(self)
        clear = QColor(self.bg)
        clear.setAlpha(0)
        fade = QLinearGradient(0, 0, 18, 0)
        fade.setColorAt(0, clear)
        fade.setColorAt(1, self.bg)
        p.fillRect(QRectF(0, 0, 18, self.height()), fade)
        p.fillRect(QRectF(18, 0, self.width() - 18, self.height()), self.bg)


class TaskText(QWidget):
    """Word-wrapped task text that can draw an animated strike-through, line by line."""

    def __init__(self, text: str, font: QFont, color: QColor, done_color: QColor, done: bool, parent=None,
                 strike: bool = True):
        super().__init__(parent)
        self.color, self.done_color, self.strike = QColor(color), QColor(done_color), strike
        self._text = text
        self._font = QFont(font)
        self._strike_pos = QFontMetrics(self._font).strikeOutPos()
        self._cache: tuple[int, QTextLayout, int] | None = None
        self._t = 1.0 if done else 0.0
        self._anim = animation(self, STRIKE_MS, self._set_t)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_done(self, done: bool, animated: bool = True) -> None:
        if animated:
            animate(self._anim, self._t, 1.0 if done else 0.0)
        else:
            self._set_t(1.0 if done else 0.0)

    def _set_t(self, v) -> None:
        self._t = float(v)
        self.update()

    def _layout(self, width: int) -> tuple[QTextLayout, int]:
        width = max(width, 20)
        if self._cache and self._cache[0] == width:
            return self._cache[1], self._cache[2]
        layout = QTextLayout(self._text, self._font)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)
        layout.beginLayout()
        y = 0.0
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            line.setPosition(QPointF(0, y))
            y += line.height()
        layout.endLayout()
        height = max(1, round(y))
        self._cache = (width, layout, height)
        return layout, height

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._layout(width)[1]

    def sizeHint(self) -> QSize:
        natural = QFontMetrics(self._font).horizontalAdvance(self._text) + 2
        width = min(natural, 260)
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:
        return QSize(40, QFontMetrics(self._font).height())

    def resizeEvent(self, e):
        self._cache = None

    def paintEvent(self, e):
        layout, _ = self._layout(self.width())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = mix(self.color, self.done_color, self._t)
        p.setPen(color)
        layout.draw(p, QPointF(0, 0))
        if self._t <= 0.001 or not self.strike:
            return
        p.setPen(QPen(color, 1.3))
        lines = layout.lineCount()
        for i in range(lines):
            progress = max(0.0, min(1.0, self._t * lines - i))  # lines strike one after another
            if progress <= 0:
                break
            line = layout.lineAt(i)
            y = line.y() + line.ascent() - self._strike_pos + 0.5
            p.drawLine(QPointF(line.x(), y), QPointF(line.x() + line.naturalTextWidth() * progress, y))


class TaskRow(QWidget):
    toggled = Signal(object, object, bool)   # row, task, checked
    edited = Signal(object, str)
    deleted = Signal(object)
    pin_toggled = Signal(object)             # task
    remind = Signal(object, object)          # task, anchor widget
    editing = Signal(bool)
    drag_started = Signal(object, QPoint)    # row, global press position
    drag_moved = Signal(QPoint)              # global cursor position
    drag_finished = Signal()

    GUTTER = 12                              # left margin that holds the drag grip

    def __init__(self, task: Task, pal: Palette, font: QFont, *, done: bool, since: str | None = None,
                 checkbox: str = "circle", strike: bool = True, pad: int = 5, parent=None):
        super().__init__(parent)
        self.task, self.pal, self.text_font = task, pal, QFont(font)
        self.done = done
        self._hover = False
        self._editor: InlineEdit | None = None
        self._press: QPoint | None = None
        self._dragging = False
        self._slot = False
        self.setMouseTracking(True)  # show the grab cursor over the grip

        lay = QHBoxLayout(self)
        lay.setContentsMargins(self.GUTTER, pad, 8, pad)
        lay.setSpacing(9)

        # Centre the check circle on the first line of text, whatever the font size.
        line = QFontMetrics(self.text_font).height()
        self._grip_y = pad + max(line, 20) / 2
        self.check = CheckCircle(QColor(pal.accent), pal.faint, self, checkbox)
        self.check.set_checked_silently(done)
        self.check.clicked.connect(lambda on: self.toggled.emit(self, self.task, on))
        check_col = QVBoxLayout()
        check_col.setContentsMargins(0, max(0, (line - self.check.height()) // 2), 0, 0)
        check_col.addWidget(self.check)
        check_col.addStretch(1)
        lay.addLayout(check_col)

        self.col = QVBoxLayout()
        self.col.setContentsMargins(0, max(0, (self.check.height() - line) // 2), 0, 0)
        self.col.setSpacing(4)
        self.label = TaskText(task.text, self.text_font, pal.text, pal.ink(0.38), done, strike=strike)
        self.col.addWidget(self.label)

        meta = []
        when = task.remind_dt
        if when:
            overdue = when < datetime.now() and not done
            fg = QColor(theme.DANGER) if overdue else (pal.faint if done else QColor(pal.accent))
            bg = QColor(fg)
            bg.setAlphaF(0.13)
            text = f"{friendly(when)}  ·  {repeat.short(task.repeat)}" if task.repeat else friendly(when)
            chip = Pill(text, fg, bg, "repeat" if task.repeat else "bell")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip("Change reminder")
            chip.clicked.connect(lambda: self.remind.emit(self.task, chip))
            meta.append(chip)
        if since:
            meta.append(Pill(since, pal.sub, pal.wash(0.06)))
        if meta:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 1)
            row.setSpacing(6)
            for w in meta:
                row.addWidget(w)
            row.addStretch(1)
            self.col.addLayout(row)
        lay.addLayout(self.col, 1)

        # Hover actions float over the end of the row so the text can use the full width.
        self.actions = RowActions(self._hover_color(), self)
        if not done:
            self.btn_pin = IconButton("pin", pal.accent if task.pinned else pal.sub, 24, 14,
                                      "Unpin" if task.pinned else "Pin to top", pal.wash(0.07))
            self.btn_pin.clicked.connect(lambda: self.pin_toggled.emit(self.task))
            self.actions.add(self.btn_pin)
        self.btn_bell = IconButton("bell", pal.sub, 24, 14, "Remind me", pal.wash(0.07))
        self.btn_bell.clicked.connect(lambda: self.remind.emit(self.task, self.btn_bell))
        self.btn_del = IconButton("x", pal.sub, 24, 14, "Delete task", pal.wash(0.07))
        self.btn_del.clicked.connect(lambda: self.deleted.emit(self.task))
        self.actions.add(self.btn_bell, self.btn_del)
        self.actions.hide()
        self._motion: QVariantAnimation | None = None

    # enter / exit animations: grow or shrink the row's height while fading it
    def play_enter(self, width: int) -> None:
        if not MOTION:
            return
        target = self.heightForWidth(width) if self.hasHeightForWidth() else -1
        target = max(target, self.sizeHint().height())
        self._play(0.0, 1.0, lambda v: self.setMaximumHeight(round(target * v)), ENTER_MS,
                   QEasingCurve.Type.OutCubic, then=lambda: self.setMaximumHeight(QWIDGETSIZE_MAX))

    def play_exit(self) -> None:
        if not MOTION:
            return
        start = self.height()
        self.actions.hide()
        self._play(1.0, 0.0, lambda v: self.setMaximumHeight(round(start * v)), EXIT_MS,
                   QEasingCurve.Type.InCubic)

    def _play(self, start: float, end: float, apply_height, ms: int, curve, then=None) -> None:
        if self._motion:
            self._motion.stop()
        effect = QGraphicsOpacityEffect(self)  # only attached while animating
        effect.setOpacity(start)
        self.setGraphicsEffect(effect)
        apply_height(start)

        def step(v):
            apply_height(v)
            effect.setOpacity(v)

        def done():
            self.setGraphicsEffect(None)
            if then:
                then()

        self._motion = animation(self, ms, step, curve)
        self._motion.finished.connect(done)
        animate(self._motion, start, end)

    def _hover_color(self) -> QColor:
        overlay = QColor(255, 255, 255) if self.pal.dark else QColor(0, 0, 0)
        return mix(QColor(self.pal.bg), overlay, 0.045)

    def resizeEvent(self, e):
        self.actions.adjustSize()
        self.actions.move(self.width() - self.actions.width() - 4, 3)

    def set_done_visual(self, done: bool, animated: bool = True) -> None:
        self.done = done
        self.label.set_done(done, animated)

    @property
    def draggable(self) -> bool:
        return not self.done and not self._editor

    # hover
    def enterEvent(self, e):
        self._hover = True
        if not self._editor and not self._slot:
            self.actions.show()
            self.actions.raise_()
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.actions.hide()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        if self._slot:  # the empty spot a dragged task will drop into
            p.setBrush(self.pal.wash(0.05))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 9, 9)
            return
        if self._hover or self._editor:
            p.setBrush(self._hover_color())
            p.drawRoundedRect(QRectF(self.rect()), 9, 9)
        if self._hover and self.draggable:  # six-dot grip in the left gutter
            p.setBrush(self.pal.ink(0.28))
            for dx in (4.0, 8.0):
                for dy in (-4.0, 0.0, 4.0):
                    p.drawEllipse(QPointF(dx, self._grip_y + dy), 1.1, 1.1)

    # drag to reorder (the note window does the actual moving)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.draggable:
            self._press = e.globalPosition().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pos = e.globalPosition().toPoint()
        if self._press is not None and not self._dragging \
                and (pos - self._press).manhattanLength() >= QApplication.startDragDistance():
            self._dragging = True
            self.actions.hide()
            self.drag_started.emit(self, self._press)
        if self._dragging:
            self.drag_moved.emit(pos)
        elif self._press is None and e.position().x() < self.GUTTER and self.draggable:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self.drag_finished.emit()
        self._press = None
        self._dragging = False
        super().mouseReleaseEvent(e)

    def set_slot(self, on: bool) -> None:
        """Turn the row into an empty placeholder (same height) while it is being dragged."""
        self._slot = on
        if on:
            self.setFixedHeight(self.height())
            for child in self.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                child.hide()
        self.update()

    # inline editing
    def mouseDoubleClickEvent(self, e):
        self.begin_edit()

    @property
    def is_editing(self) -> bool:
        return self._editor is not None

    def begin_edit(self) -> None:
        if self._editor:
            return
        self._editor = InlineEdit(self.task.text, self)
        self._editor.setFont(self.text_font)
        self._editor.committed.connect(self._finish)
        self._editor.cancelled.connect(lambda: self._finish(None))
        self.label.hide()
        self.actions.hide()
        self.col.insertWidget(0, self._editor)
        self._editor.setFocus()
        self._editor.selectAll()
        self.editing.emit(True)
        self.update()

    def _finish(self, text: str | None) -> None:
        editor, self._editor = self._editor, None
        if editor is None:
            return
        editor.hide()
        editor.deleteLater()
        self.label.show()
        if text is not None and text.strip() != self.task.text:
            self.edited.emit(self.task, text.strip())
        self.editing.emit(False)


class Swatch(QAbstractButton):
    def __init__(self, pal: Palette, selected: bool, ring: QColor, parent=None):
        super().__init__(parent)
        self.pal, self.selected, self.ring = pal, selected, QColor(ring)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(pal.name)
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QRectF(self.rect()).center()
        if self.selected:
            p.setPen(QPen(self.ring, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 11.5, 11.5)
        r = 8.5 if not self._hover else 9.5
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        p.setBrush(QColor(self.pal.swatch))
        p.drawEllipse(c, r, r)


class CustomSwatch(Swatch):
    """The last dot in the colour rows: a rainbow ring that opens the custom colour picker. While the
    note has a custom colour, the dot shows it."""

    def __init__(self, current: str, ring: QColor, parent=None):
        custom = theme.is_custom(current)
        super().__init__(theme.palette(current if custom else "cloud"), custom, ring, parent)
        self.custom = custom
        self.setToolTip(f"Custom colour ({current.upper()})…" if custom else "Custom colour…")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QRectF(self.rect()).center()
        if self.selected:
            p.setPen(QPen(self.ring, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 11.5, 11.5)
        r = 8.5 if not self._hover else 9.5
        rainbow = QConicalGradient(c, 90)
        for i in range(7):
            rainbow.setColorAt(i / 6, QColor.fromHsvF(min(i / 6, 0.9999), 0.75, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(rainbow)
        p.drawEllipse(c, r, r)
        p.setBrush(QColor(self.pal.bg) if self.custom else QColor("#FFFFFF"))
        p.drawEllipse(c, r - 3, r - 3)
        if not self.custom:
            icons.paint(p, "plus", QRectF(c.x() - 5, c.y() - 5, 10, 10), "#3A3A3C", 2.6)


# ------------------------------------------------------------------ menus
def make_menu(parent=None, dark: bool = False, title: str = "") -> QMenu:
    menu = QMenu(title, parent)
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    menu.setStyleSheet(theme.menu_qss(dark))
    menu.setFont(theme.font(9.5))
    menu.setProperty("dark", dark)
    menu.aboutToShow.connect(lambda: system.remove_frame(menu))
    return menu


def add_action(menu: QMenu, text: str, slot=None, *, checked: bool | None = None,
               icon: str | None = None, enabled: bool = True, danger: bool = False):
    dark = bool(menu.property("dark"))
    color = QColor(theme.DANGER) if danger else QColor("#F2F2F5" if dark else "#3A3A3C")
    act = menu.addAction(text)
    if checked is not None:
        act.setIcon(icons.icon("check" if checked else "blank", color, 14, 2.4))
    elif icon:
        act.setIcon(icons.icon(icon, color, 14))
    if slot:
        act.triggered.connect(slot)
    act.setEnabled(enabled)
    return act


def add_submenu(menu: QMenu, title: str, icon: str | None = None) -> QMenu:
    dark = bool(menu.property("dark"))
    sub = make_menu(menu, dark, title)
    action = menu.addMenu(sub)
    if icon:
        action.setIcon(icons.icon(icon, QColor("#F2F2F5" if dark else "#3A3A3C"), 14))
    return sub


def add_menu_label(menu: QMenu, text: str) -> None:
    lbl = QLabel(text.upper())
    f = theme.font(7.6, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
    lbl.setFont(f)
    color = QColor("#F2F2F5" if menu.property("dark") else "#1C1C1E")
    lbl.setStyleSheet(f"color: {theme.rgba(color, 0.45)}; background: transparent; padding: 6px 12px 0 12px;")
    action = QWidgetAction(menu)
    action.setDefaultWidget(lbl)
    action.setEnabled(False)
    menu.addAction(action)


def _add_widget(menu: QMenu, widget: QWidget) -> None:
    action = QWidgetAction(menu)
    action.setDefaultWidget(widget)
    menu.addAction(action)


SWATCHES_PER_ROW = 8


def add_swatches(menu: QMenu, current: str, on_pick, keep_open: bool = False, on_custom=None) -> None:
    """Rows of colour dots. With keep_open the menu stays up so colours can be tried one after another;
    it closes like any menu when you click outside it. With on_custom, a last rainbow dot closes the menu
    and calls on_custom to pick any colour."""
    holder = QWidget()
    grid = QVBoxLayout(holder)
    grid.setContentsMargins(8, 4, 8, 4)
    grid.setSpacing(2)
    ring = QColor("#F2F2F5" if menu.property("dark") else "#3A3A3C")
    swatches = [Swatch(pal, pal.key == current, ring) for pal in theme.PALETTES.values()]
    custom = CustomSwatch(current, ring) if on_custom else None

    def pick(key: str) -> None:
        if keep_open:
            for sw in swatches:
                sw.selected = sw.pal.key == key
                sw.update()
            if custom:
                custom.selected = custom.custom and key == current
                custom.update()
        else:
            menu.close()
        on_pick(key)

    def pick_custom() -> None:
        menu.close()
        QTimer.singleShot(0, on_custom)   # once the menu has gone

    for sw in swatches:
        sw.clicked.connect(lambda _=False, key=sw.pal.key: pick(key))
    dots: list[QWidget] = list(swatches)
    if custom:
        custom.clicked.connect(pick_custom)
        dots.append(custom)
    for start in range(0, len(dots), SWATCHES_PER_ROW):
        row = QHBoxLayout()
        row.setSpacing(2)
        for dot in dots[start:start + SWATCHES_PER_ROW]:
            row.addWidget(dot)
        row.addStretch(1)
        grid.addLayout(row)
    _add_widget(menu, holder)


class MenuSegments(QWidget):
    """A row of choices inside a menu, like "Flat | Elevated | 3D", that applies at once and keeps
    the menu open."""

    def __init__(self, options: list[tuple[str, str, str]], current: str, on_pick, dark: bool):
        super().__init__()
        fg = "#F2F2F5" if dark else "#1C1C1E"
        ink = "#FFFFFF" if dark else "#000000"
        on = theme.rgba("#FFFFFF", 0.16) if dark else "#FFFFFF"
        edge = theme.rgba("#FFFFFF", 0.10) if dark else theme.rgba("#000000", 0.10)
        self.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {fg}; border: 1px solid transparent;
                           border-radius: 7px; padding: 5px 4px; }}
            QPushButton:hover:!checked {{ background: {theme.rgba(ink, 0.06)}; }}
            QPushButton:checked {{ background: {on}; border: 1px solid {edge}; }}
            QWidget#track {{ background: {theme.rgba(ink, 0.06)}; border-radius: 9px; }}
        """)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 2, 10, 4)
        track = QWidget()
        track.setObjectName("track")
        track.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        lay = QHBoxLayout(track)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.buttons: dict[str, QPushButton] = {}
        for key, label, tip in options:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(key == current)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(theme.font(9, QFont.Weight.Medium))
            b.clicked.connect(lambda _=False, k=key: self._pick(k, on_pick))
            lay.addWidget(b, 1)
            self.buttons[key] = b
        outer.addWidget(track)

    def _pick(self, key: str, on_pick) -> None:
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        on_pick(key)


def add_segments(menu: QMenu, options: list[tuple[str, str, str]], current: str, on_pick) -> None:
    _add_widget(menu, MenuSegments(options, current, on_pick, bool(menu.property("dark"))))


class SaturationSlider(QWidget):
    """Gradient track from the lightest to the most vivid version of a colour.

    `moved` fires continuously while dragging (for a live preview), `committed` once on release.
    Double-click resets to the classic pastel.
    """
    moved = Signal(float)
    committed = Signal(float)

    def __init__(self, key: str, value: float, dark_menu: bool):
        super().__init__()
        self.key, self.value, self.dark_menu = key, value, dark_menu
        self.setFixedHeight(26)
        self.setMinimumWidth(150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Drag to change how strong the colour is. Double-click to reset.")
        self._dragging = False

    def set_key(self, key: str) -> None:
        self.key = key
        self.update()

    def _track(self) -> QRectF:
        return QRectF(10, self.height() / 2 - 5, self.width() - 20, 10)

    def _value_at(self, x: float) -> float:
        track = self._track()
        return max(0.0, min(1.0, (x - track.left()) / track.width()))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._set(self._value_at(e.position().x()))

    def mouseMoveEvent(self, e):
        if self._dragging:
            self._set(self._value_at(e.position().x()))

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False
            self.committed.emit(self.value)

    def mouseDoubleClickEvent(self, e):
        self._set(0.5)
        self.committed.emit(self.value)

    def _set(self, value: float) -> None:
        value = round(value, 2)
        if value != self.value:
            self.value = value
            self.update()
            self.moved.emit(value)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = self._track()
        gradient = QLinearGradient(track.topLeft(), track.topRight())
        for stop in (0.0, 0.25, 0.5, 0.75, 1.0):
            gradient.setColorAt(stop, QColor(theme.palette(self.key, stop).bg))
        p.setPen(QPen(QColor(255, 255, 255, 40) if self.dark_menu else QColor(0, 0, 0, 30), 1))
        p.setBrush(gradient)
        p.drawRoundedRect(track, 5, 5)
        # notch marking the classic pastel
        p.setPen(QPen(QColor(0, 0, 0, 45), 1))
        mid = track.left() + track.width() / 2
        p.drawLine(QPointF(mid, track.top() + 2.5), QPointF(mid, track.bottom() - 2.5))
        # knob, filled with the selected colour
        centre = QPointF(track.left() + track.width() * self.value, track.center().y())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(centre + QPointF(0, 1), 9, 9)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(centre, 9, 9)
        p.setBrush(QColor(theme.palette(self.key, self.value).bg))
        p.setPen(QPen(QColor(0, 0, 0, 35), 1))
        p.drawEllipse(centre, 6, 6)


def add_saturation(menu: QMenu, key: str, value: float, on_move, on_commit) -> SaturationSlider:
    holder = QWidget()
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(12, 0, 8, 4)
    lay.setSpacing(8)
    dark = bool(menu.property("dark"))
    name = QLabel("Saturation")
    name.setFont(theme.font(9.5))
    name.setStyleSheet(f"color: {'#F2F2F5' if dark else '#1C1C1E'}; background: transparent;")
    slider = SaturationSlider(key, value, dark)
    slider.moved.connect(on_move)
    slider.committed.connect(on_commit)
    lay.addWidget(name)
    lay.addWidget(slider, 1)
    _add_widget(menu, holder)
    return slider


class Stepper(QWidget):
    """Menu row like "Text size   −  10.5  +" that stays open while you click."""

    def __init__(self, label: str, value: str, on_step, dark: bool):
        super().__init__()
        fg = QColor("#F2F2F5" if dark else "#1C1C1E")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 2, 8, 2)
        lay.setSpacing(4)
        name = QLabel(label)
        name.setFont(theme.font(9.5))
        name.setStyleSheet(f"color: {theme.rgba(fg)}; background: transparent;")
        lay.addWidget(name)
        lay.addStretch(1)
        self.value = QLabel(value)
        self.value.setFont(theme.font(9.5, QFont.Weight.DemiBold))
        self.value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value.setMinimumWidth(40)
        self.value.setStyleSheet(f"color: {theme.rgba(fg)}; background: transparent;")
        wash = theme.rgba("#FFFFFF" if dark else "#000000", 0.07)
        hover = theme.rgba("#FFFFFF" if dark else "#000000", 0.13)
        for text, delta in (("−", -1), ("+", +1)):
            b = QPushButton(text)
            b.setFixedSize(30, 26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(theme.font(11, QFont.Weight.DemiBold))
            b.setStyleSheet(f"QPushButton {{ background: {wash}; color: {theme.rgba(fg)}; border: none; "
                            f"border-radius: 7px; }} QPushButton:hover {{ background: {hover}; }}")
            b.clicked.connect(lambda _=False, d=delta: self.value.setText(on_step(d)))
            if delta < 0:
                lay.addWidget(b)
                lay.addWidget(self.value)
            else:
                lay.addWidget(b)


def add_stepper(menu: QMenu, label: str, value: str, on_step) -> None:
    _add_widget(menu, Stepper(label, value, on_step, bool(menu.property("dark"))))


class FontOption(QAbstractButton):
    """A font choice, previewed in its own typeface."""

    def __init__(self, family: str, label: str, selected: bool, dark: bool):
        super().__init__()
        self.family, self.selected, self.dark = family, selected, dark
        self.setText(label)
        self.setFont(theme.note_font(family, 11))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False
        self.setFixedHeight(max(32, QFontMetrics(self.font()).height() + 12))
        self.setMinimumWidth(QFontMetrics(self.font()).horizontalAdvance(label) + 56)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fg = QColor("#F2F2F5" if self.dark else "#1C1C1E")
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 20) if self.dark else QColor(0, 0, 0, 14))
            p.drawRoundedRect(QRectF(self.rect()), 7, 7)
        if self.selected:
            icons.paint(p, "check", QRectF(10, (self.height() - 14) / 2, 14, 14), fg, 2.4)
        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(QRectF(34, 0, self.width() - 40, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text())


def add_font_list(menu: QMenu, current: str, on_pick) -> None:
    """Font choices that apply instantly and keep the menu open."""
    holder = QWidget()
    lay = QVBoxLayout(holder)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    dark = bool(menu.property("dark"))
    options: list[FontOption] = []
    group = None

    def pick(family: str) -> None:
        for opt in options:
            opt.selected = opt.family == family
            opt.update()
        on_pick(family)

    for family, label, kind in theme.available_fonts(current):
        if kind and kind != group:
            group = kind
            heading = QLabel(kind.upper())
            f = theme.font(7.6, QFont.Weight.Bold)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
            heading.setFont(f)
            color = QColor("#F2F2F5" if dark else "#1C1C1E")
            heading.setStyleSheet(f"color: {theme.rgba(color, 0.45)}; background: transparent; padding: 8px 12px 2px 12px;")
            lay.addWidget(heading)
        opt = FontOption(family, label, family == current, dark)
        opt.clicked.connect(lambda _=False, f=family: pick(f))
        options.append(opt)
        lay.addWidget(opt)
    _add_widget(menu, holder)


def reminder_presets(ref: datetime | None = None) -> list[tuple[str, datetime]]:
    ref = (ref or datetime.now()).replace(second=0, microsecond=0)
    presets = [("In 15 minutes", ref + timedelta(minutes=15)),
               ("In 1 hour", ref + timedelta(hours=1)),
               ("In 3 hours", ref + timedelta(hours=3))]
    if ref.hour < 17:
        presets.append(("This evening · 6:00 PM", ref.replace(hour=18, minute=0)))
    tomorrow = (ref + timedelta(days=1)).replace(hour=9, minute=0)
    presets.append(("Tomorrow morning · 9:00 AM", tomorrow))
    return presets


# ------------------------------------------------------------------ dialogs
def dialog_qss() -> str:
    """Dialogs, fields and drop-down lists in the app's light or dark colours."""
    ui, css = theme.ui(), theme.rgba
    return f"""
    QDialog {{ background: {ui.surface}; }}
    QLabel {{ color: {ui.text}; }}
    QDateTimeEdit, QComboBox, QSpinBox, QLineEdit {{
        background: {ui.field}; border: 1px solid transparent; border-radius: 8px;
        padding: 7px 10px; color: {ui.text}; selection-background-color: {ui.accent}; selection-color: #FFFFFF;
    }}
    QDateTimeEdit:focus, QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border: 1px solid {ui.accent}; }}
    QDateTimeEdit::drop-down, QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {ui.surface}; color: {ui.text}; border: 1px solid {css(ui.line)}; outline: none;
        selection-background-color: {ui.accent}; selection-color: #FFFFFF; padding: 4px;
    }}
    QPushButton#step {{ background: {ui.field}; color: {ui.text}; border: none; border-radius: 8px; }}
    QPushButton#step:hover {{ background: {ui.field_hover}; }}
    """


def calendar() -> QCalendarWidget:
    """The month that drops down from a date field, readable in the app's light and dark colours: no red
    weekends, today in the accent colour, other months' days greyed."""
    ui, css = theme.ui(), theme.rgba
    cal = QCalendarWidget()
    cal.setGridVisible(False)
    cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
    cal.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
    pal = cal.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        for role, color in ((QPalette.ColorRole.Window, ui.surface), (QPalette.ColorRole.Base, ui.surface),
                            (QPalette.ColorRole.AlternateBase, ui.surface), (QPalette.ColorRole.Button, ui.surface),
                            (QPalette.ColorRole.WindowText, ui.text), (QPalette.ColorRole.Text, ui.text),
                            (QPalette.ColorRole.ButtonText, ui.text), (QPalette.ColorRole.Highlight, ui.accent),
                            (QPalette.ColorRole.HighlightedText, "#FFFFFF")):
            pal.setColor(group, role, QColor(color))
    faded = QColor(ui.sub)
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, faded)   # days of the months either side
    cal.setPalette(pal)
    plain = QTextCharFormat()
    plain.setForeground(QColor(ui.text))
    for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
        cal.setWeekdayTextFormat(day, plain)
    header = QTextCharFormat()
    header.setForeground(faded)
    header.setFontWeight(QFont.Weight.DemiBold)
    cal.setHeaderTextFormat(header)
    today = QTextCharFormat()
    today.setForeground(QColor(ui.accent))
    today.setFontWeight(QFont.Weight.Bold)
    cal.setDateTextFormat(QDate.currentDate(), today)
    cal.setStyleSheet(f"""
        QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {ui.surface};
            border-bottom: 1px solid {css(ui.line)}; }}
        QCalendarWidget QToolButton {{ color: {ui.text}; background: transparent; border: none; border-radius: 7px;
            padding: 5px 8px; font-weight: 600; }}
        QCalendarWidget QToolButton:hover {{ background: {ui.field}; }}
        QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0; }}
        QCalendarWidget QMenu {{ background: {ui.surface}; color: {ui.text}; border: 1px solid {css(ui.line)}; }}
        QCalendarWidget QMenu::item:selected {{ background: {ui.accent}; color: #FFFFFF; }}
        QCalendarWidget QSpinBox {{ background: {ui.field}; color: {ui.text}; border: none; border-radius: 6px;
            padding: 2px 6px; selection-background-color: {ui.accent}; selection-color: #FFFFFF; }}
        QCalendarWidget QAbstractItemView {{ background: {ui.surface}; color: {ui.text}; outline: none; border: none;
            selection-background-color: {ui.accent}; selection-color: #FFFFFF; }}
    """)
    for name, icon in (("qt_calendar_prevmonth", "chevron_left"), ("qt_calendar_nextmonth", "chevron_right")):
        button = cal.findChild(QToolButton, name)
        if button is not None:
            button.setIcon(icons.icon(icon, ui.text, 16, 2.4))
            button.setIconSize(QSize(16, 16))
    return cal


def _paint_chevron(widget: QWidget) -> None:
    """The drop-down arrow, which the dialog style sheet would otherwise hide."""
    p = QPainter(widget)
    icons.paint(p, "chevron_down", QRectF(widget.width() - 26, (widget.height() - 14) / 2, 14, 14),
                theme.ui().icon, 2.2)


class ComboBox(QComboBox):
    def paintEvent(self, e):
        super().paintEvent(e)
        _paint_chevron(self)


class DateTimeEdit(QDateTimeEdit):
    def paintEvent(self, e):
        super().paintEvent(e)
        _paint_chevron(self)


class Dialog(QDialog):
    """A small dialog, light or dark like the rest of the app, that stays above the notes, with Cancel and
    a main button at the bottom."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setStyleSheet(dialog_qss())
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 16)
        self.lay.setSpacing(8)
        self.setMinimumWidth(340)

    def heading(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(theme.font(11.5, QFont.Weight.DemiBold))
        self.lay.addWidget(label)
        return label

    def add_buttons(self, ok_text: str) -> None:
        self.lay.addSpacing(8)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = PillButton("Cancel", theme.ui().accent)
        ok = PillButton(ok_text, theme.ui().accent, primary=True)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        self.lay.addLayout(buttons)


class DurationField(QWidget):
    """A number with − / + buttons (or type it), and its unit: "−  45  +   minutes | hours"."""

    def __init__(self, n: int, unit: str, units: tuple[str, ...], parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.spin = QSpinBox()
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setFont(theme.font(10.5, QFont.Weight.DemiBold))
        self.spin.setFixedWidth(58)
        for text, delta in (("−", -1), ("+", 1)):
            b = QPushButton(text)
            b.setObjectName("step")
            b.setFixedSize(30, 32)
            b.setAutoRepeat(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(theme.font(11, QFont.Weight.DemiBold))
            b.clicked.connect(lambda _=False, d=delta: self.spin.stepBy(d))
            lay.addWidget(b)
            if delta < 0:
                lay.addWidget(self.spin)
        lay.addSpacing(8)
        self.unit = Segmented([(u, repeat.UNITS[u][1]) for u in units], unit if unit in units else units[0])
        self.unit.changed.connect(self._limit)
        lay.addWidget(self.unit)
        lay.addStretch(1)
        self._limit(self.unit.current)
        self.spin.setValue(n)

    def _limit(self, unit: str) -> None:
        self.spin.setRange(1, repeat.UNITS[unit][3])

    def value(self) -> tuple[int, str]:
        return self.spin.value(), self.unit.current


class ReminderDialog(Dialog):
    """When to be reminded, and whether to be reminded again: never, every 15 minutes, daily, or a custom gap."""
    CUSTOM = "custom"

    def __init__(self, initial: datetime, repeat_code: str = "", custom: bool = False, parent=None):
        super().__init__("Set reminder", parent)
        self.when_title = self.heading("Remind me at")
        self.edit = DateTimeEdit(initial)
        self.edit.setCalendarPopup(True)
        self.edit.setCalendarWidget(calendar())
        self.edit.setDisplayFormat("ddd d MMM yyyy   h:mm AP")
        self.edit.setFont(theme.font(10.5))
        self.lay.addWidget(self.edit)
        self.lay.addSpacing(8)
        self.heading("Repeat")
        self.repeat = ComboBox()
        self.repeat.setFont(theme.font(10.5))
        self.repeat.addItem("Never", "")
        for code in repeat.PRESETS:
            self.repeat.addItem(repeat.describe(code), code)
        self.repeat.addItem("Custom…", self.CUSTOM)
        self.repeat.setMaxVisibleItems(self.repeat.count())
        self.lay.addWidget(self.repeat)
        n, unit = repeat.parse(repeat_code) or (30, "min")
        self.custom = DurationField(n, unit, ("min", "h", "d", "w"))
        self.custom_row = QWidget()
        row = QHBoxLayout(self.custom_row)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(10)
        every = QLabel("Every")
        every.setFont(theme.font(10.5))
        row.addWidget(every)
        row.addWidget(self.custom, 1)
        self.lay.addWidget(self.custom_row)
        self.add_buttons("Set reminder")

        preset = repeat_code if (repeat_code in repeat.PRESETS or not repeat_code) and not custom else self.CUSTOM
        self.repeat.setCurrentIndex(max(0, self.repeat.findData(preset)))
        self.repeat.currentIndexChanged.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        code = self.repeat.currentData()
        self.custom_row.setVisible(code == self.CUSTOM)
        self.when_title.setText("First reminder at" if code else "Remind me at")
        self.adjustSize()

    def value(self) -> tuple[datetime, str]:
        when = self.edit.dateTime().toPython().replace(second=0, microsecond=0)
        code = self.repeat.currentData()
        return when, repeat.code(*self.custom.value()) if code == self.CUSTOM else code


def pick_reminder(parent, initial: datetime, repeat_code: str = "", custom: bool = False
                  ) -> tuple[datetime, str] | None:
    """Ask when to remind and how to repeat: (first time, repeat code), or None if cancelled."""
    dlg = ReminderDialog(initial, repeat_code, custom, parent)
    return dlg.value() if dlg.exec() == QDialog.DialogCode.Accepted else None


_last_snooze = (45, "min")   # the custom snooze offered next time


def pick_snooze(parent) -> int | None:
    """Ask how long to snooze for; minutes, or None if cancelled."""
    global _last_snooze
    dlg = Dialog("Snooze", parent)
    dlg.heading("Snooze for")
    field = DurationField(*_last_snooze, ("min", "h"))
    dlg.lay.addWidget(field)
    dlg.add_buttons("Snooze")
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    _last_snooze = n, unit = field.value()
    return n * 60 if unit == "h" else n


# ------------------------------------------------------------------ hub controls
class Toggle(QAbstractButton):
    """iOS-style switch."""

    def __init__(self, on: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(on)
        self.setFixedSize(42, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._t = 1.0 if on else 0.0
        self._anim = animation(self, 180, self._set)
        self.toggled.connect(lambda v: animate(self._anim, self._t, 1.0 if v else 0.0))

    def _set(self, v):
        self._t = float(v)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mix(QColor(120, 120, 128, 70), QColor("#34C759"), self._t))
        p.drawRoundedRect(QRectF(self.rect()), 13, 13)
        x = 2 + self._t * (self.width() - 24)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawEllipse(QRectF(x, 3, 22, 22))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 2, 22, 22))


class Segmented(QWidget):
    """macOS-style segmented control."""
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current: str, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self.buttons: dict[str, QPushButton] = {}
        for key, label in options:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(theme.font(9, QFont.Weight.Medium))
            b.clicked.connect(lambda _=False, k=key: self.set_current(k, emit=True))
            lay.addWidget(b)
            self.buttons[key] = b
        ui, css = theme.ui(), theme.rgba
        self.setStyleSheet(f"""
            QWidget#segmented {{ background: {css(ui.track)}; border-radius: 9px; }}
            QPushButton {{ background: transparent; border: none; border-radius: 7px;
                           padding: 5px 14px; color: {ui.text}; }}
            QPushButton:hover:!checked {{ background: {css(ui.line)}; }}
            QPushButton:checked {{ background: {ui.thumb}; border: 1px solid {css(ui.line)}; }}
        """)
        self.current = ""
        self.set_current(current)

    def set_current(self, key: str, emit: bool = False) -> None:
        self.current = key
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        if emit:
            self.changed.emit(key)
