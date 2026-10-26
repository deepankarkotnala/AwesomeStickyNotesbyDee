"""Crisp vector line icons (Lucide-style, 24x24 grid) drawn with QPainter - no icon font needed."""
from __future__ import annotations

import math
from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _lines(*polylines) -> QPainterPath:
    path = QPainterPath()
    for pts in polylines:
        path.moveTo(*pts[0])
        for pt in pts[1:]:
            path.lineTo(*pt)
    return path


def _dots(*centres, r: float = 1.4) -> QPainterPath:
    path = QPainterPath()
    for x, y in centres:
        path.addEllipse(QRectF(x - r, y - r, 2 * r, 2 * r))
    return path


def _bell() -> QPainterPath:
    p = QPainterPath()
    p.moveTo(6, 8.5)
    p.arcTo(QRectF(6, 2.5, 12, 12), 180, -180)
    p.cubicTo(18, 15, 20.5, 17, 20.5, 17)
    p.lineTo(3.5, 17)
    p.cubicTo(3.5, 17, 6, 15, 6, 8.5)
    p.moveTo(10.2, 20.5)
    p.quadTo(12, 22.4, 13.8, 20.5)
    return p


def _clock() -> QPainterPath:
    p = QPainterPath()
    p.addEllipse(QRectF(3, 3, 18, 18))
    p.moveTo(12, 7.5)
    p.lineTo(12, 12)
    p.lineTo(15, 14)
    return p


def _repeat() -> QPainterPath:
    p = _lines([(17, 2.5), (20.5, 6), (17, 9.5)], [(7, 21.5), (3.5, 18), (7, 14.5)])
    p.moveTo(3.5, 11.5)
    p.lineTo(3.5, 10)
    p.arcTo(QRectF(3.5, 6, 8, 8), 180, -90)
    p.lineTo(20.5, 6)
    p.moveTo(20.5, 12.5)
    p.lineTo(20.5, 14)
    p.arcTo(QRectF(12.5, 10, 8, 8), 0, -90)
    p.lineTo(3.5, 18)
    return p


def _brush() -> QPainterPath:
    p = _lines([(10.5, 13.5), (18.8, 5.2)])
    p.addEllipse(QRectF(17.6, 3.0, 3.6, 3.6))
    p.moveTo(9.2, 14.2)
    p.cubicTo(6.2, 13.6, 4.4, 15.8, 4.6, 18.2)
    p.cubicTo(4.7, 19.6, 3.8, 20.4, 3.2, 20.8)
    p.cubicTo(6.4, 21.6, 10.4, 20.6, 10.9, 17.0)
    p.cubicTo(11.1, 15.6, 10.4, 14.6, 9.2, 14.2)
    return p


def _copy() -> QPainterPath:
    p = QPainterPath()
    p.addRoundedRect(QRectF(8.5, 8.5, 12, 12), 2.5, 2.5)
    p.moveTo(15.5, 8.5)
    p.lineTo(15.5, 6)
    p.quadTo(15.5, 3.5, 13, 3.5)
    p.lineTo(6, 3.5)
    p.quadTo(3.5, 3.5, 3.5, 6)
    p.lineTo(3.5, 13)
    p.quadTo(3.5, 15.5, 6, 15.5)
    p.lineTo(8.5, 15.5)
    return p


def _paste() -> QPainterPath:
    p = QPainterPath()
    p.addRoundedRect(QRectF(5, 4.5, 14, 17), 2.5, 2.5)
    p.addRoundedRect(QRectF(9, 2.5, 6, 4), 1.5, 1.5)
    p.moveTo(9, 12)
    p.lineTo(15, 12)
    p.moveTo(9, 16)
    p.lineTo(13, 16)
    return p


def _trash() -> QPainterPath:
    p = _lines([(4, 6.5), (20, 6.5)], [(9.5, 6.5), (9.5, 4), (14.5, 4), (14.5, 6.5)])
    p.moveTo(6, 6.5)
    p.lineTo(7, 19)
    p.quadTo(7.1, 20.5, 8.6, 20.5)
    p.lineTo(15.4, 20.5)
    p.quadTo(16.9, 20.5, 17, 19)
    p.lineTo(18, 6.5)
    return p


def _eye() -> QPainterPath:
    p = QPainterPath()
    p.moveTo(2.5, 12)
    p.cubicTo(5.5, 6, 18.5, 6, 21.5, 12)
    p.cubicTo(18.5, 18, 5.5, 18, 2.5, 12)
    p.addEllipse(QRectF(9, 9, 6, 6))
    return p


def _eye_off() -> QPainterPath:
    p = _eye()
    p.moveTo(4, 4)
    p.lineTo(20, 20)
    return p


def _undo() -> QPainterPath:
    p = _lines([(8.5, 13.5), (4, 9), (8.5, 4.5)])
    p.moveTo(4, 9)
    p.lineTo(14.5, 9)
    p.cubicTo(18, 9, 20.5, 11.5, 20.5, 15)
    p.cubicTo(20.5, 18.5, 18, 20.5, 14.5, 20.5)
    p.lineTo(11, 20.5)
    return p


def _pin() -> QPainterPath:
    return _lines([(12, 16), (12, 21.5)],
                  [(9, 3), (15, 3)],
                  [(10, 3), (10, 9.5), (6, 13.5), (6, 16), (18, 16), (18, 13.5), (14, 9.5), (14, 3)])


def _note() -> QPainterPath:
    p = QPainterPath()
    p.addRoundedRect(QRectF(4, 4, 16, 16), 3, 3)
    p.moveTo(8, 9.5)
    p.lineTo(16, 9.5)
    p.moveTo(8, 14)
    p.lineTo(13, 14)
    return p


def _gear() -> QPainterPath:
    p = QPainterPath()
    p.addEllipse(QRectF(9, 9, 6, 6))
    for i in range(8):
        a = math.radians(i * 45)
        p.moveTo(12 + 6.2 * math.cos(a), 12 + 6.2 * math.sin(a))
        p.lineTo(12 + 9 * math.cos(a), 12 + 9 * math.sin(a))
    return p


# name -> (stroke path, fill path)
_DEFS = {
    "plus": lambda: (_lines([(12, 5), (12, 19)], [(5, 12), (19, 12)]), None),
    "x": lambda: (_lines([(17.5, 6.5), (6.5, 17.5)], [(6.5, 6.5), (17.5, 17.5)]), None),
    "check": lambda: (_lines([(20, 6.5), (9.5, 17), (4.5, 12)]), None),
    "more": lambda: (None, _dots((5.5, 12), (12, 12), (18.5, 12), r=1.7)),
    "chevron_up": lambda: (_lines([(6, 14.5), (12, 8.5), (18, 14.5)]), None),
    "chevron_down": lambda: (_lines([(6, 9.5), (12, 15.5), (18, 9.5)]), None),
    "bell": lambda: (_bell(), None),
    "clock": lambda: (_clock(), None),
    "repeat": lambda: (_repeat(), None),
    "brush": lambda: (_brush(), None),
    "copy": lambda: (_copy(), None),
    "paste": lambda: (_paste(), None),
    "trash": lambda: (_trash(), None),
    "eye": lambda: (_eye(), None),
    "eye_off": lambda: (_eye_off(), None),
    "undo": lambda: (_undo(), None),
    "pin": lambda: (_pin(), None),
    "note": lambda: (_note(), None),
    "gear": lambda: (_gear(), None),
    "grip": lambda: (None, _dots((19, 19), (14, 19), (19, 14), (9, 19), (14, 14), (19, 9), r=1.25)),
    "blank": lambda: (None, None),
}


@lru_cache(maxsize=None)
def _paths(name: str):
    return _DEFS[name]()


def paint(p: QPainter, name: str, rect: QRectF, color: QColor | str, width: float = 2.0) -> None:
    stroke, fill = _paths(name)
    side = min(rect.width(), rect.height())
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.x() + (rect.width() - side) / 2, rect.y() + (rect.height() - side) / 2)
    p.scale(side / 24, side / 24)
    color = QColor(color)
    if stroke is not None:
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(stroke)
    if fill is not None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(fill)
    p.restore()


def icon(name: str, color: QColor | str, size: int = 16, width: float = 2.0) -> QIcon:
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(2)
    p = QPainter(pm)
    paint(p, name, QRectF(0, 0, size, size), color, width)
    p.end()
    return QIcon(pm)
