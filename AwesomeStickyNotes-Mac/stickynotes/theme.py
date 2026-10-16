"""Colours, fonts and shared style sheets."""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from functools import lru_cache

from PySide6.QtGui import QColor, QFont, QFontDatabase

IS_MAC = sys.platform == "darwin"

DANGER = "#E5484D"
HUB_BG = "#F5F5F7"
HUB_TEXT = "#1C1C1E"
HUB_ACCENT = "#0A84FF"

# macOS draws 1 pt as 1 px, Windows as 1.33 px; scale on the Mac so notes look the same size on both.
FONT_SCALE = 96 / 72 if IS_MAC else 1.0
FONT_SIZES = (8.0, 22.0)        # allowed range for note text, in points

if IS_MAC:
    # Fonts offered for note text; only those installed are shown. "" = the default UI font.
    FONT_CHOICES = (
        ("", "Default"),
        ("Helvetica Neue", "Helvetica Neue"),
        ("Avenir Next", "Avenir Next"),
        ("Noteworthy", "Noteworthy"),
        ("Marker Felt", "Marker Felt"),
        ("Chalkboard SE", "Chalkboard SE"),
        ("Bradley Hand", "Bradley Hand"),
        ("Futura", "Futura"),
        ("Georgia", "Georgia"),
        ("Baskerville", "Baskerville"),
        ("Menlo", "Menlo"),
        ("SF Mono", "SF Mono"),
    )
else:
    FONT_CHOICES = (
        ("", "Default"),
        ("Segoe UI", "Segoe UI"),
        ("Segoe Print", "Segoe Print"),
        ("Ink Free", "Ink Free"),
        ("Segoe Script", "Segoe Script"),
        ("Comic Sans MS", "Comic Sans MS"),
        ("Calibri", "Calibri"),
        ("Bahnschrift", "Bahnschrift"),
        ("Georgia", "Georgia"),
        ("Cambria", "Cambria"),
        ("Cascadia Code", "Cascadia Code"),
        ("Consolas", "Consolas"),
    )


@lru_cache(maxsize=2)
def _families(display: bool) -> tuple[str, ...]:
    if IS_MAC:  # San Francisco is only reachable through the system font
        system = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
        return (system, "Helvetica Neue", "Arial")
    if display:
        return ("Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI", "Arial")
    return ("Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Arial")


def font(pt: float, weight: QFont.Weight = QFont.Weight.Normal, display: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(list(_families(display)))
    f.setPointSizeF(pt * FONT_SCALE)
    f.setWeight(weight)
    return f


def available_fonts() -> list[tuple[str, str]]:
    installed = set(QFontDatabase.families())
    return [(family, label) for family, label in FONT_CHOICES if not family or family in installed]


def note_font(family: str, size: float) -> QFont:
    f = font(size)
    if family:
        f.setFamilies([family] + list(_families(False)))
    return f


def rgba(color: QColor | str, alpha: float | None = None) -> str:
    """Qt style sheets want 0-255 integer alpha."""
    c = QColor(color)
    if alpha is not None:
        c.setAlphaF(alpha)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {c.alpha()})"


@dataclass(frozen=True)
class Palette:
    key: str
    name: str
    bg: str        # card background
    swatch: str    # colour shown in pickers
    accent: str    # checkboxes, progress bar, highlights
    dark: bool = False

    @property
    def text(self) -> QColor:
        return QColor("#F2F2F5") if self.dark else QColor("#1C1C1E")

    def ink(self, alpha: float) -> QColor:
        c = self.text
        c.setAlphaF(alpha)
        return c

    @property
    def sub(self) -> QColor:
        return self.ink(0.55)

    @property
    def faint(self) -> QColor:
        return self.ink(0.30)

    def wash(self, alpha: float) -> QColor:
        """Neutral overlay used for hover states and input fields."""
        c = QColor(255, 255, 255) if self.dark else QColor(0, 0, 0)
        c.setAlphaF(alpha)
        return c


PALETTES: dict[str, Palette] = {p.key: p for p in (
    Palette("lemon", "Lemon", "#FFF7D1", "#FFE27A", "#E0A100"),
    Palette("peach", "Peach", "#FFEDE3", "#FFB899", "#EE6A3C"),
    Palette("mint", "Mint", "#E5F6EC", "#8FD9AE", "#1E9E62"),
    Palette("sky", "Sky", "#E6F0FF", "#9DC0FF", "#2F6FED"),
    Palette("lavender", "Lavender", "#F0EBFF", "#C4B5FF", "#7357EE"),
    Palette("rose", "Rose", "#FFE9F0", "#FFAAC4", "#E0457A"),
    Palette("cloud", "Cloud", "#FFFFFF", "#FFFFFF", "#0A84FF"),
    Palette("graphite", "Graphite", "#232428", "#3A3B40", "#8E9BFF", dark=True),
)}


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(*(a.getRgbF()[i] * (1 - t) + b.getRgbF()[i] * t for i in range(3)))


@lru_cache(maxsize=256)
def _saturated(base: Palette, saturation: float) -> Palette:
    """0 = barely tinted, 0.5 = the classic pastel (base.bg), 1 = the full swatch colour."""
    if base.dark:
        low, high = QColor("#141518"), QColor("#3C3E46")
    elif base.key == "cloud":
        low, high = QColor("#FFFFFF"), QColor("#E2E8F1")
    else:  # keep a hint of the colour even at the lightest setting
        low, high = _mix(QColor("#FFFFFF"), QColor(base.bg), 0.25), QColor(base.swatch)
    bg = QColor(base.bg)
    if saturation < 0.5:
        bg = _mix(low, bg, saturation / 0.5)
    else:
        bg = _mix(bg, high, (saturation - 0.5) / 0.5)
    accent = QColor(base.accent)
    if saturation > 0.5 and not base.dark:  # keep checkboxes readable on stronger colours
        accent = accent.darker(100 + round(40 * (saturation - 0.5)))
    return replace(base, bg=bg.name(), accent=accent.name())


def palette(key: str, saturation: float = 0.5) -> Palette:
    base = PALETTES.get(key, PALETTES["lemon"])
    saturation = round(max(0.0, min(1.0, saturation)), 2)
    return base if saturation == 0.5 else _saturated(base, saturation)


def menu_qss(dark: bool = False) -> str:
    bg, fg = ("#2C2D31", "#F2F2F5") if dark else ("#FFFFFF", "#1C1C1E")
    border = rgba("#FFFFFF", 0.10) if dark else rgba("#000000", 0.09)
    hover = rgba("#FFFFFF", 0.08) if dark else rgba("#000000", 0.055)
    muted = rgba(fg, 0.38)
    return f"""
    QMenu {{
        background: {bg}; color: {fg};
        border: 1px solid {border}; border-radius: 12px; padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 26px 7px 10px; border-radius: 7px; background: transparent;
    }}
    QMenu::item:selected {{ background: {hover}; }}
    QMenu::item:disabled {{ color: {muted}; }}
    QMenu::icon {{ padding-left: 10px; }}
    QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}
    """


def tooltip_qss() -> str:
    return """
    QToolTip {
        background: #1C1C1E; color: #FFFFFF; border: none;
        border-radius: 6px; padding: 5px 8px;
    }
    """
