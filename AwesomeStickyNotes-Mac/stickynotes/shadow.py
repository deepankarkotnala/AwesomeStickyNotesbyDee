"""Soft, layered drop shadows (think CSS `box-shadow: 0 1px 3px ..., 0 12px 32px ...`)."""
from __future__ import annotations

from PySide6.QtCore import QMargins, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene

# (blur radius, y offset, opacity)
REST = ((3, 1, 0.10), (26, 10, 0.16))
HOVER = ((4, 2, 0.12), (36, 16, 0.24))

_FORMAT = QImage.Format.Format_ARGB32_Premultiplied


def _blur(image: QImage, radius: float) -> QImage:
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(image))
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    out = QImage(image.size(), _FORMAT)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    area = QRectF(0, 0, image.width(), image.height())
    scene.render(p, area, area)
    p.end()
    return out


class NinePatch:
    """A shadow rendered once for a small card, then stretched to any size without re-blurring.

    The corners are drawn as-is and only the flat middle strips are stretched, so it looks identical
    to a full render while costing a few pixmap blits per frame - which keeps resizing and the
    collapse/expand animation smooth.
    """

    def __init__(self, margins: QMargins, radius: float, layers, dpr: float):
        self.margins, self.dpr = margins, dpr
        reach = max(blur for blur, _, _ in layers) + max(dy for _, dy, _ in layers)
        self.corner = int(radius + reach) + 1           # card-space size of each corner slice
        core = 2 * self.corner + 2
        self.size = QSize(margins.left() + margins.right() + core, margins.top() + margins.bottom() + core)
        card = QRectF(margins.left(), margins.top(), core, core)
        self.pixmap = render(self.size, card, radius, layers, dpr)

    def fits(self, card: QSizeF) -> bool:
        """True when the card is big enough for an exact result."""
        return card.width() >= 2 * self.corner and card.height() >= 2 * self.corner

    def draw(self, p: QPainter, width: float, height: float) -> None:
        m, c, d = self.margins, self.corner, self.dpr
        card_w = width - m.left() - m.right()
        card_h = height - m.top() - m.bottom()
        cx, cy = min(c, card_w / 2), min(c, card_h / 2)
        sw, sh = self.size.width(), self.size.height()
        src_x = (0, m.left() + c, sw - m.right() - c, sw)
        src_y = (0, m.top() + c, sh - m.bottom() - c, sh)
        dst_x = (0, m.left() + cx, width - m.right() - cx, width)
        dst_y = (0, m.top() + cy, height - m.bottom() - cy, height)
        for i in range(3):
            for j in range(3):
                target = QRectF(dst_x[i], dst_y[j], dst_x[i + 1] - dst_x[i], dst_y[j + 1] - dst_y[j])
                if target.width() <= 0 or target.height() <= 0:
                    continue
                source = QRectF(src_x[i] * d, src_y[j] * d,
                                (src_x[i + 1] - src_x[i]) * d, (src_y[j + 1] - src_y[j]) * d)
                p.drawPixmap(target, self.pixmap, source)


_patches: dict = {}


def nine_patch(margins: QMargins, radius: float, layers, dpr: float) -> NinePatch:
    key = (margins.left(), margins.top(), margins.right(), margins.bottom(), radius, layers, dpr)
    if key not in _patches:
        _patches[key] = NinePatch(margins, radius, layers, dpr)
    return _patches[key]


def render(size: QSize, card: QRectF, radius: float, layers, dpr: float = 1.0) -> QPixmap:
    """Return a window-sized pixmap containing the blurred shadow of `card`."""
    w, h = max(1, round(size.width() * dpr)), max(1, round(size.height() * dpr))
    out = QImage(w, h, _FORMAT)
    out.fill(Qt.GlobalColor.transparent)
    painter = QPainter(out)
    for blur, dy, alpha in layers:
        layer = QImage(w, h, _FORMAT)
        layer.fill(Qt.GlobalColor.transparent)
        p = QPainter(layer)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(dpr, dpr)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, round(255 * alpha)))
        inset = min(blur / 6, 4)
        p.drawRoundedRect(card.translated(0, dy).adjusted(inset, inset, -inset, 0), radius, radius)
        p.end()
        painter.drawImage(0, 0, _blur(layer, blur * dpr))
    painter.end()
    pixmap = QPixmap.fromImage(out)
    pixmap.setDevicePixelRatio(dpr)
    return pixmap
