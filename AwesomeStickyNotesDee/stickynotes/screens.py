"""Where each note sits, remembered separately for every monitor arrangement.

When a monitor is plugged in or unplugged (docking, undocking, closing the laptop lid), Windows moves
windows on its own and the notes end up piled on top of each other. So every note keeps its place per
arrangement ("layout") and goes back there when that arrangement returns. In an arrangement it has not
been in before, a note keeps its spot on the same monitor if that monitor is still connected, or moves to
the same relative spot on the main monitor.
"""
from __future__ import annotations

import json

from PySide6.QtCore import QMargins, QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication

MAX_LAYOUTS = 8          # arrangements remembered per note; the oldest is forgotten first


def _ident(screen) -> str:
    """A name for the monitor itself that stays the same across reconnects (the EDID when available)."""
    parts = (screen.manufacturer(), screen.model(), screen.serialNumber())
    ident = " ".join(p for p in parts if p).strip() or screen.name()
    return ident.replace("|", "/").replace("@", "/")


def current_key() -> str:
    """Identifies the arrangement: which monitors are connected, and where each sits on the desktop."""
    entries = []
    for screen in QGuiApplication.screens():
        g = screen.geometry()
        entries.append(f"{_ident(screen)}@{g.x()},{g.y()},{g.width()},{g.height()}")
    return "|".join(sorted(entries))


def parse_key(key: str) -> list[tuple[str, QRect]]:
    screens = []
    for entry in key.split("|"):
        ident, _, geometry = entry.rpartition("@")
        try:
            x, y, w, h = (int(v) for v in geometry.split(","))
        except ValueError:
            continue
        screens.append((ident, QRect(x, y, w, h)))
    return screens


def saved(note) -> dict[str, list[int]]:
    """{layout key: [x, y, w, h]}, the most recently used arrangement last."""
    try:
        data = json.loads(note.layouts or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def remember(note, key: str, rect: QRect) -> str:
    """The note's `layouts` value with `rect` recorded for arrangement `key`."""
    data = saved(note)
    data.pop(key, None)                   # re-inserted at the end: the most recent arrangement
    data[key] = [rect.x(), rect.y(), rect.width(), rect.height()]
    while len(data) > MAX_LAYOUTS:
        data.pop(next(iter(data)))
    return json.dumps(data)


def place(note, key: str, margins: QMargins, min_size: QSize) -> QRect:
    """The window geometry the note should have in arrangement `key`."""
    data = saved(note)
    if key in data:
        rect = QRect(*data[key])
    elif data:
        last = next(reversed(data))
        rect = carry_over(QRect(*data[last]), parse_key(last), margins)
        return fit(_at_least(rect, min_size), margins, min_size)
    else:
        rect = QRect(note.x, note.y, note.w, note.h)
    rect = _at_least(rect, min_size)
    return rect if visible(rect.marginsRemoved(margins)) else fit(rect, margins, min_size)


def carry_over(rect: QRect, old: list[tuple[str, QRect]], margins: QMargins) -> QRect:
    """Move a window saved under an earlier arrangement onto the current monitors."""
    if not old:
        return rect
    card = rect.marginsRemoved(margins)
    ident, source = max(old, key=lambda s: _overlap(s[1], card))
    now = [(_ident(s), s.geometry()) for s in QGuiApplication.screens()]
    same = [g for i, g in now if i == ident]
    if same:     # the same monitor, perhaps now elsewhere on the desktop or at another resolution
        target = min(same, key=lambda g: (g.topLeft() - source.topLeft()).manhattanLength())
    else:
        target = QGuiApplication.primaryScreen().geometry()
    if target.size() == source.size():
        return rect.translated(target.topLeft() - source.topLeft())
    # Keep the card's centre at the same relative spot on the monitor.
    fx =(card.center().x() - source.x()) / max(1, source.width())
    fy = (card.center().y() - source.y()) / max(1, source.height())
    centre = QPoint(target.x() + round(fx * target.width()), target.y() + round(fy * target.height()))
    card.moveCenter(centre)
    return card.marginsAdded(margins)


def visible(card: QRect) -> bool:
    """True when the note's header is on a screen, so it can still be grabbed and moved."""
    header = QRect(card.x(), card.y(), card.width(), 40)
    for screen in QGuiApplication.screens():
        part = screen.availableGeometry().intersected(header)
        if part.width() >= 100 and part.height() >= 20:
            return True
    return False


def fit(rect: QRect, margins: QMargins, min_size: QSize) -> QRect:
    """Shift (and if needed shrink) the window so its card lies wholly on the nearest screen."""
    card = rect.marginsRemoved(margins)
    area = _nearest_area(card.center())
    min_w = min_size.width() - margins.left() - margins.right()
    min_h = min_size.height() - margins.top() - margins.bottom()
    card.setWidth(max(min_w, min(card.width(), area.width())))
    card.setHeight(max(min_h, min(card.height(), area.height())))
    card.moveLeft(max(area.left(), min(card.left(), area.left() + area.width() - card.width())))
    card.moveTop(max(area.top(), min(card.top(), area.top() + area.height() - card.height())))
    return card.marginsAdded(margins)


def _at_least(rect: QRect, min_size: QSize) -> QRect:
    return QRect(rect.topLeft(), rect.size().expandedTo(min_size))


def _overlap(a: QRect, b: QRect) -> int:
    part = a.intersected(b)
    return part.width() * part.height() if part.isValid() else 0


def _nearest_area(point: QPoint) -> QRect:
    screen = QGuiApplication.screenAt(point)
    if screen is None:
        def distance(s):
            g = s.geometry()
            dx = max(g.left() - point.x(), 0, point.x() - g.right())
            dy = max(g.top() - point.y(), 0, point.y() - g.bottom())
            return dx * dx + dy * dy
        screen = min(QGuiApplication.screens(), key=distance)
    return screen.availableGeometry()
