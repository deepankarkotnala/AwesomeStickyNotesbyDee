"""Custom note colours: any of the 16 million, picked by eye or typed as a #RRGGBB code."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from . import icons, theme
from .widgets import Dialog

INSET = 7   # room around the shade field and hue track so their knobs never get cut off


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


class ShadeField(QWidget):
    """Saturation from left to right and brightness from bottom to top, for the current hue."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hue, self.sat, self.val = 0.0, 0.0, 1.0
        self.setFixedHeight(156)
        self.setMinimumWidth(300)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _area(self) -> QRectF:
        return QRectF(self.rect()).adjusted(INSET, INSET, -INSET, -INSET)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self._area()
        path = QPainterPath()
        path.addRoundedRect(r, 10, 10)
        across = QLinearGradient(r.topLeft(), r.topRight())
        across.setColorAt(0, QColor("#FFFFFF"))
        across.setColorAt(1, QColor.fromHsvF(self.hue, 1, 1))
        p.fillPath(path, across)
        down = QLinearGradient(r.topLeft(), r.bottomLeft())
        down.setColorAt(0, QColor(0, 0, 0, 0))
        down.setColorAt(1, QColor(0, 0, 0, 255))
        p.fillPath(path, down)
        knob = QPointF(r.left() + self.sat * r.width(), r.top() + (1 - self.val) * r.height())
        p.setPen(QPen(QColor(0, 0, 0, 80), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(knob, 8.5, 8.5)
        p.setPen(QPen(QColor("#FFFFFF"), 2.5))
        p.setBrush(QColor.fromHsvF(self.hue, self.sat, self.val))
        p.drawEllipse(knob, 7, 7)

    def _pick(self, pos) -> None:
        r = self._area()
        self.sat = _clamp((pos.x() - r.left()) / r.width())
        self.val = 1 - _clamp((pos.y() - r.top()) / r.height())
        self.update()
        self.changed.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pick(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._pick(e.position())


class HueSlider(QWidget):
    """The rainbow of hues; drag along it to change the hue."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hue = 0.0
        self.setFixedHeight(12 + 2 * INSET)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _track(self) -> QRectF:
        return QRectF(INSET, INSET, self.width() - 2 * INSET, 12)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._track()
        rainbow = QLinearGradient(t.topLeft(), t.topRight())
        for i in range(7):
            rainbow.setColorAt(i / 6, QColor.fromHsvF(min(i / 6, 0.9999), 1, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(rainbow)
        p.drawRoundedRect(t, 6, 6)
        knob = QPointF(t.left() + self.hue * t.width(), t.center().y())
        p.setPen(QPen(QColor(0, 0, 0, 80), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(knob, 9.5, 9.5)
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(QColor.fromHsvF(min(self.hue, 0.9999), 1, 1))
        p.drawEllipse(knob, 8, 8)

    def _pick(self, x: float) -> None:
        t = self._track()
        self.hue = _clamp((x - t.left()) / t.width())
        self.update()
        self.changed.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._pick(e.position().x())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._pick(e.position().x())


class NotePreview(QWidget):
    """A small note in the chosen colour, with the text and accent colours it will get."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pal = theme.palette("lemon")
        self.setFixedSize(138, 96)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.pal
        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(255, 255, 255, 30) if pal.dark else QColor(0, 0, 0, 26), 1))
        p.setBrush(QColor(pal.bg))
        p.drawRoundedRect(card, 12, 12)
        p.setPen(pal.text)
        p.setFont(theme.font(10.5, QFont.Weight.DemiBold))
        p.drawText(QRectF(14, 10, 120, 20), Qt.AlignmentFlag.AlignVCenter, "Preview")
        p.setPen(Qt.PenStyle.NoPen)                       # a progress bar, a ticked task, an accent pill
        p.setBrush(pal.wash(0.08))
        p.drawRoundedRect(QRectF(14, 35, 110, 4), 2, 2)
        p.setBrush(QColor(pal.accent))
        p.drawRoundedRect(QRectF(14, 35, 46, 4), 2, 2)
        p.drawEllipse(QRectF(14, 50, 14, 14))
        icons.paint(p, "check", QRectF(16.5, 52.6, 9, 9), "#FFFFFF", 3.2)
        p.setPen(pal.text)
        p.setFont(theme.font(9))
        p.drawText(QRectF(34, 48, 96, 18), Qt.AlignmentFlag.AlignVCenter, "Buy milk")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(pal.accent))
        p.drawRoundedRect(QRectF(14, 72, 56, 14), 7, 7)
        p.setPen(QColor(pal.bg))
        p.setFont(theme.font(7.5, QFont.Weight.DemiBold))
        p.drawText(QRectF(14, 72, 56, 14), Qt.AlignmentFlag.AlignCenter, "Accent")


class Dot(QAbstractButton):
    """One recent colour."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(color)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        p.setBrush(QColor(self.color))
        p.drawEllipse(QRectF(self.rect()).adjusted(2.5, 2.5, -2.5, -2.5))


class ColorDialog(Dialog):
    """Pick a colour with the shade field and hue slider, type a #RRGGBB code, or reuse a recent one."""
    previewed = Signal(str)   # "#RRGGBB" as it changes, for showing it on the note straight away

    def __init__(self, initial: QColor, recent: list[str], parent=None):
        super().__init__("Custom colour", parent)
        self.heading("Custom colour")
        self.field = ShadeField()
        self.hue = HueSlider()
        self.lay.addWidget(self.field)
        self.lay.addWidget(self.hue)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        bottom.setContentsMargins(INSET, 4, INSET, 0)
        self.preview = NotePreview()
        bottom.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignTop)
        side = QVBoxLayout()
        side.setSpacing(6)
        code = QLabel("Colour code")
        code.setFont(theme.font(9, QFont.Weight.DemiBold))
        side.addWidget(code)
        self.hex = QLineEdit()
        self.hex.setFont(theme.font(10.5))
        self.hex.setMaxLength(7)
        self.hex.setPlaceholderText("#RRGGBB")
        self.hex.setValidator(QRegularExpressionValidator(QRegularExpression("#?[0-9A-Fa-f]{0,6}"), self.hex))
        self.hex.textEdited.connect(self._typed)
        self.hex.editingFinished.connect(self._typed_done)
        side.addWidget(self.hex)
        recent = [c for c in recent if theme.is_custom(c)]
        if recent:
            side.addSpacing(4)
            label = QLabel("Recent")
            label.setFont(theme.font(9, QFont.Weight.DemiBold))
            side.addWidget(label)
            dots = QHBoxLayout()
            dots.setSpacing(0)
            for color in recent[:6]:
                dot = Dot(color)
                dot.clicked.connect(lambda _=False, c=color: self.set_color(QColor(c)))
                dots.addWidget(dot)
            dots.addStretch(1)
            side.addLayout(dots)
        side.addStretch(1)
        bottom.addLayout(side, 1)
        self.lay.addLayout(bottom)
        self.add_buttons("Use colour")

        self._quiet = False
        self.field.changed.connect(self._from_field)
        self.hue.changed.connect(self._from_hue)
        self.set_color(initial)

    def color(self) -> QColor:
        return QColor.fromHsvF(min(self.hue.hue, 0.9999), self.field.sat, self.field.val)

    def value(self) -> str:
        return self.color().name().upper()

    def set_color(self, color: QColor, keep_text: bool = False) -> None:
        h, s, v, _ = color.getHsvF()
        if h >= 0:   # greys have no hue: keep the one already chosen
            self.hue.hue = self.field.hue = h
        self.field.sat, self.field.val = s, v
        self.hue.update()
        self.field.update()
        self._changed(keep_text)

    def _from_field(self) -> None:
        self._changed()

    def _from_hue(self) -> None:
        self.field.hue = self.hue.hue
        self.field.update()
        self._changed()

    def _changed(self, keep_text: bool = False) -> None:
        code = self.value()
        if not keep_text:
            self.hex.setText(code)
        self.preview.pal = theme.palette(code)
        self.preview.update()
        self.previewed.emit(code)

    def _typed(self, text: str) -> None:
        digits = text.lstrip("#")
        if len(digits) == 6:
            self.set_color(QColor("#" + digits), keep_text=True)

    def _typed_done(self) -> None:
        digits = self.hex.text().lstrip("#")
        if len(digits) == 3:   # #abc is shorthand for #aabbcc
            self.set_color(QColor("#" + "".join(c * 2 for c in digits)))
        else:
            self.hex.setText(self.value())


def pick_color(parent, initial: QColor, recent: list[str], on_preview=None) -> str | None:
    """Ask for a colour; "#RRGGBB", or None if cancelled. `on_preview` gets each colour as it is tried,
    at most every 60 ms, so a note can show it straight away."""
    dlg = ColorDialog(initial, recent, parent)
    if on_preview is not None:
        latest = [""]
        timer = QTimer(dlg, singleShot=True, interval=60)
        timer.timeout.connect(lambda: on_preview(latest[0]))
        dlg.previewed.connect(lambda code: (latest.__setitem__(0, code), timer.isActive() or timer.start()))
    accepted = dlg.exec() == Dialog.DialogCode.Accepted
    return dlg.value() if accepted else None
