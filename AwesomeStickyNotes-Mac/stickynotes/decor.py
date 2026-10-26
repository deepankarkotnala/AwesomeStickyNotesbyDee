"""How a note's card is painted: fill or gradient, header band, paper pattern, paper grain, gloss and edge.

Shared by the notes on the desktop, the hub's note tiles and the preview in the style panel, so all three
look alike. Shadows are drawn by the caller, outside the card.
"""
from __future__ import annotations

import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from . import theme

GRAIN_SIZE = 160
_grain: QPixmap | None = None


def grain() -> QPixmap:
    """A tile of faint light and dark specks, laid over paper-style notes so they look like paper."""
    global _grain
    if _grain is None:
        rng = random.Random(7)
        data = bytearray()
        for _ in range(GRAIN_SIZE * GRAIN_SIZE):
            roll = rng.random()
            if roll < 0.22:                       # a dark speck (premultiplied BGRA)
                data += bytes((0, 0, 0, rng.randint(5, 13)))
            elif roll < 0.40:                     # a light speck
                a = rng.randint(10, 26)
                data += bytes((a, a, a, a))
            else:
                data += bytes(4)
        image = QImage(bytes(data), GRAIN_SIZE, GRAIN_SIZE, QImage.Format.Format_ARGB32_Premultiplied).copy()
        _grain = QPixmap.fromImage(image)
    return _grain


def paint_card(p: QPainter, rect: QRectF, note, pal: theme.Palette, radius: float, hover: float = 0.0,
               header_bottom: float | None = None, scale: float = 1.0) -> None:
    """Paint the card for `note` into `rect`. `header_bottom` is where its title area ends (for the header
    band and to start the paper pattern below the title); `scale` shrinks patterns for small previews."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if note.background == "gradient":
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0, QColor(pal.bg))
        fill.setColorAt(1, theme.second_color(pal, note.color2))
        p.fillPath(path, fill)
    else:
        p.fillPath(path, QColor(pal.bg))

    p.setClipPath(path)
    head = header_bottom if header_bottom is not None else rect.top() + 52 * scale
    band = theme.header_fill(pal, note.header)
    if band is not None:
        p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), head - rect.top()), band)
    _pattern(p, rect, note.background, pal, head, scale)

    if note.style == "paper":
        brush = QBrush(grain())
        brush.setTransform(brush.transform().translate(rect.left(), rect.top()))
        p.fillRect(rect, brush)
        light = QLinearGradient(rect.topLeft(), rect.bottomLeft())    # flat at the top, curling at the bottom
        light.setColorAt(0, QColor(255, 255, 255, 40))
        light.setColorAt(0.35, QColor(255, 255, 255, 0))
        light.setColorAt(0.85, QColor(0, 0, 0, 0))
        light.setColorAt(1, QColor(0, 0, 0, 16))
        p.fillRect(rect, light)
    elif note.style == "3d" and not pal.dark:   # the glossy top
        sheen = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + 110 * scale))
        sheen.setColorAt(0, QColor(255, 255, 255, 110))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(rect, sheen)
    p.setClipping(False)

    # A hairline edge. With no shadow to deepen, a flat card shows the hover on its edge instead.
    alpha = {"flat": 26 + 24 * hover, "soft": 10, "paper": 14}.get(note.style, 20) + (4 if pal.dark else 0)
    ink = 255 if pal.dark else 0
    p.setPen(QPen(QColor(ink, ink, ink, round(alpha)), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), max(0.0, radius - 0.5), max(0.0, radius - 0.5))
    p.restore()


def _pattern(p: QPainter, rect: QRectF, kind: str, pal: theme.Palette, top: float, scale: float) -> None:
    """Lined, grid or dotted paper, starting just below the title area."""
    if kind == "lined":
        step = 24 * scale
        p.setPen(QPen(pal.ink(0.10), 1))
        y = top + step
        while y < rect.bottom():
            p.drawLine(QPointF(rect.left(), round(y) + 0.5), QPointF(rect.right(), round(y) + 0.5))
            y += step
    elif kind == "grid":
        step = 18 * scale
        p.setPen(QPen(pal.ink(0.07), 1))
        y = top + step
        while y < rect.bottom():
            p.drawLine(QPointF(rect.left(), round(y) + 0.5), QPointF(rect.right(), round(y) + 0.5))
            y += step
        x = rect.left() + step
        while x < rect.right():
            p.drawLine(QPointF(round(x) + 0.5, top), QPointF(round(x) + 0.5, rect.bottom()))
            x += step
    elif kind == "dots":
        step = 16 * scale
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.ink(0.18))
        y = top + step
        while y < rect.bottom():
            x = rect.left() + step
            while x < rect.right():
                p.drawEllipse(QPointF(x, y), 1.1 * max(scale, 0.8), 1.1 * max(scale, 0.8))
                x += step
            y += step
