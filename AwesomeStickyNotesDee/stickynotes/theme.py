"""Colours, fonts and shared style sheets."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

IS_MAC = sys.platform == "darwin"

DANGER = "#E5484D"


@dataclass(frozen=True)
class Chrome:
    """Colours for everything that isn't a note: the hub, dialogs, panels, the calendar and the tray menu.
    Colours with transparency are written #AARRGGBB; use rgba() to put them in a style sheet."""
    dark: bool
    bg: str            # window background
    surface: str       # cards, dialogs, panels, pop-ups
    text: str
    sub: str           # secondary text
    accent: str        # buttons, selection, links
    field: str         # input fields and small buttons
    field_hover: str
    line: str          # hairlines and borders
    icon: str          # grey icons
    track: str         # behind a segmented control
    thumb: str         # its selected segment
    scroll: str        # scrollbar handle
    scroll_hover: str


# Apple's system greys, light and dark. Text and secondary text are at least 4.5:1 on every background,
# and white text on the accent at least 3.6:1 (4.6:1 in light mode).
LIGHT_UI = Chrome(False, "#F5F5F7", "#FFFFFF", "#1C1C1E", "#BF3C3C43", "#0071E3", "#F2F2F7", "#E5E5EA", "#14000000",
                  "#636366", "#1E767680", "#FFFFFF", "#28000000", "#46000000")
DARK_UI = Chrome(True, "#1C1C1E", "#2C2C2E", "#F2F2F7", "#A6EBEBF5", "#0A84FF", "#3A3A3C", "#48484A", "#24FFFFFF",
                 "#AEAEB2", "#3D767680", "#636366", "#32FFFFFF", "#5AFFFFFF")
APPEARANCES = (("system", "System"), ("light", "Light"), ("dark", "Dark"))
_ui = LIGHT_UI


def ui() -> Chrome:
    """The colours of the app's own windows right now (see Controller.apply_appearance)."""
    return _ui


def set_dark(dark: bool) -> None:
    global _ui
    _ui = DARK_UI if dark else LIGHT_UI

# macOS draws 1 pt as 1 px, Windows as 1.33 px; scale on the Mac so notes look the same size on both.
FONT_SCALE = 96 / 72 if IS_MAC else 1.0
FONT_SIZES = (8.0, 22.0)        # allowed range for note text, in points

# Fonts offered for notes, by group. They ship in stickynotes/fonts (Google Fonts, open licences), so every
# computer has them; "" is the system's own UI font (Segoe UI on Windows, San Francisco on the Mac).
FONT_GROUPS = (
    ("Clean", ("Inter", "Roboto", "Open Sans", "Poppins", "Montserrat", "Lato", "Nunito", "DM Sans")),
    ("Handwritten", ("Caveat", "Shantell Sans", "Kalam", "Patrick Hand", "Indie Flower", "Shadows Into Light",
                     "Gochi Hand", "Architects Daughter", "Permanent Marker")),
    ("Classic", ("Merriweather", "Lora", "Playfair Display")),
    ("Code", ("JetBrains Mono",)),
)
FONTS_DIR = Path(__file__).resolve().parent / "fonts"


def load_bundled_fonts() -> None:
    """Make the fonts in stickynotes/fonts available to the app (call once, after the QApplication)."""
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))


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


def available_fonts(current: str = "") -> list[tuple[str, str, str]]:
    """(family, label, group) for every font on offer, the system font first. A font a note already uses
    stays on the list even if it is no longer offered, so it can be seen and changed."""
    installed = set(QFontDatabase.families())
    fonts = [("", "System font", "")]
    for group, families in FONT_GROUPS:
        fonts += [(family, family, group) for family in families if family in installed]
    if current and all(current != family for family, _, _ in fonts):
        fonts.append((current, current, "In use"))
    return fonts


def note_font(family: str, size: float) -> QFont:
    f = font(size)
    if family:
        f.setFamilies([family] + list(_families(False)))
    return f


def title_font(family: str) -> QFont:
    """A note's title: its own title font if one is chosen, else the system's display font."""
    f = note_font(family, 13.5) if family else font(13.5, display=True)
    f.setWeight(QFont.Weight.DemiBold)
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
    ink_color: str = ""   # text colour chosen for the note; "" = dark or light to suit the background

    @property
    def text(self) -> QColor:
        if self.ink_color:
            return QColor(self.ink_color)
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


# Shown in pickers in this order, eight to a row (the custom-colour button ends the second row).
PALETTES: dict[str, Palette] = {p.key: p for p in (
    Palette("lemon", "Lemon", "#FFF7D1", "#FFE27A", "#E0A100"),
    Palette("apricot", "Apricot", "#FFF0D9", "#FFC97A", "#D98200"),
    Palette("peach", "Peach", "#FFEDE3", "#FFB899", "#EE6A3C"),
    Palette("rose", "Rose", "#FFE9F0", "#FFAAC4", "#E0457A"),
    Palette("lavender", "Lavender", "#F0EBFF", "#C4B5FF", "#7357EE"),
    Palette("sky", "Sky", "#E6F0FF", "#9DC0FF", "#2F6FED"),
    Palette("aqua", "Aqua", "#E0F6F6", "#86D9D9", "#0E949A"),
    Palette("mint", "Mint", "#E5F6EC", "#8FD9AE", "#1E9E62"),
    Palette("sage", "Sage", "#EEF2E6", "#C2D1A8", "#5F8432"),
    Palette("sand", "Sand", "#F6EFE4", "#DCC7A5", "#A06E2E"),
    Palette("cloud", "Cloud", "#FFFFFF", "#FFFFFF", "#0A84FF"),
    Palette("fog", "Fog", "#EEF0F3", "#C9CED6", "#4F6280"),
    Palette("graphite", "Graphite", "#232428", "#3A3B40", "#8E9BFF", dark=True),
    Palette("midnight", "Midnight", "#1B2333", "#2D3A55", "#7FB2FF", dark=True),
    Palette("plum", "Plum", "#2A1F33", "#4A3558", "#D39CFF", dark=True),
)}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_custom(key: str) -> bool:
    """True for a colour the user mixed themselves, stored as "#RRGGBB" instead of a palette name."""
    return bool(_HEX.match(key or ""))


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor.fromRgbF(*(a.getRgbF()[i] * (1 - t) + b.getRgbF()[i] * t for i in range(3)))


def luminance(color: QColor) -> float:
    """Relative luminance (WCAG), 0 = black, 1 = white."""
    def channel(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in color.getRgbF()[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _wants_light_text(bg: QColor) -> bool:
    """True when light text contrasts better with `bg` than dark text does (WCAG ratios; the two
    cross at a luminance of about 0.19, nudged slightly towards dark text)."""
    return luminance(bg) < 0.18


def _from_color(key: str, bg: QColor) -> Palette:
    """A palette for any background colour: light or dark text to suit it, and an accent in its hue that
    stands out against it (blue for greys)."""
    dark = _wants_light_text(bg)
    h, s, l, _ = bg.getHslF()
    if s < 0.12 or h < 0:
        accent = QColor("#8E9BFF") if dark else QColor("#0A84FF")
    else:   # the card's own hue, lightened or darkened until checkboxes stand out (3:1 or better)
        light, step = (0.62, 0.04) if dark else (0.48, -0.04)
        accent = QColor.fromHslF(h, max(0.70, s), light)
        while contrast(accent, bg) < 3.0 and 0.08 < light < 0.92:
            light += step
            accent = QColor.fromHslF(h, max(0.70, s), light)
    return Palette(key, key.upper(), bg.name(), bg.name(), accent.name(), dark)


def contrast(a: QColor, b: QColor) -> float:
    """WCAG contrast ratio, 1 (none) to 21 (black on white)."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


@lru_cache(maxsize=256)
def _saturated(base: Palette, saturation: float) -> Palette:
    """0 = barely tinted, 0.5 = the classic pastel (base.bg), 1 = the full swatch colour."""
    if base.dark:
        low, high = _mix(QColor("#000000"), QColor(base.bg), 0.6), QColor(base.swatch)
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


@lru_cache(maxsize=256)
def _custom(key: str, saturation: float) -> Palette:
    """A custom colour: exact at 0.5, softer and lighter below, deeper and more vivid above."""
    base = QColor(key)
    h, s, l, _ = base.getHslF()
    if _wants_light_text(base):
        low, high = _mix(QColor("#000000"), base, 0.6), _mix(base, QColor("#FFFFFF"), 0.18)
    elif s < 0.08 or h < 0:   # a grey or white deepens to a darker grey, never to a hue
        low, high = _mix(QColor("#FFFFFF"), base, 0.25), _mix(base, QColor("#000000"), 0.15)
    else:
        low = _mix(QColor("#FFFFFF"), base, 0.25)
        high = QColor.fromHslF(h, min(1.0, s + (1 - s) * 0.5), l * 0.82)
    if saturation < 0.5:
        bg = _mix(low, base, saturation / 0.5)
    elif saturation > 0.5:
        bg = _mix(base, high, (saturation - 0.5) / 0.5)
    else:
        bg = base
    return _from_color(key, bg)


def palette(key: str, saturation: float = 0.5) -> Palette:
    saturation = round(max(0.0, min(1.0, saturation)), 2)
    if is_custom(key):
        return _custom(key.upper(), saturation)
    base = PALETTES.get(key, PALETTES["lemon"])
    return base if saturation == 0.5 else _saturated(base, saturation)


def note_palette(note) -> Palette:
    """The palette a note is drawn with: its colour and saturation, and its own text colour if it has one."""
    pal = palette(note.color, note.saturation)
    return replace(pal, ink_color=note.text_color) if getattr(note, "text_color", "") else pal


def header_palette(pal: Palette, header: str) -> Palette:
    """Colours for the title area: the note's own, or for a solid header, ones that read on the accent."""
    if header != "solid":
        return pal
    return _from_color(pal.key, QColor(pal.accent))


def header_fill(pal: Palette, header: str) -> QColor | None:
    if header == "tinted":
        return _mix(QColor(pal.bg), QColor(pal.accent), 0.16)
    if header == "solid":
        return QColor(pal.accent)
    return None


def second_color(pal: Palette, color2: str) -> QColor:
    """Where a gradient background ends: the chosen colour, or a deeper shade of the note's own."""
    if color2:
        return QColor(palette(color2).bg)
    return _mix(QColor(pal.bg), QColor(pal.accent), 0.30)


# Card styles: how a note sits on the desktop.
STYLES = (("flat", "Flat", "A plain card, no shadow"),
          ("soft", "Elevated", "Flat, lifted by a soft shadow, like a modern web card"),
          ("3d", "3D", "Glossy, with a deeper shadow"),
          ("paper", "Paper", "Like a real sticky note: paper grain, square corners and lifted ends"))
BACKGROUNDS = (("plain", "Plain"), ("lined", "Lined"), ("grid", "Grid"), ("dots", "Dotted"), ("gradient", "Gradient"))
HEADERS = (("plain", "Plain"), ("tinted", "Tinted"), ("solid", "Solid"))
CHECKBOXES = (("circle", "Circle"), ("square", "Square"), ("heart", "Heart"))
DONE_LOOKS = (("strike", "Struck through"), ("fade", "Faded"))
SPACINGS = (("compact", "Compact"), ("normal", "Comfortable"), ("roomy", "Roomy"))
ROW_PADDING = {"compact": 2, "normal": 5, "roomy": 9}          # px above and below each task
# Text colours offered besides "automatic" (and any custom colour).
INKS = (("#1C1C1E", "Charcoal"), ("#4A4A4F", "Slate"), ("#1F3A5F", "Navy"), ("#1E4D2B", "Forest"),
        ("#5B3A1E", "Brown"), ("#7A1F3D", "Wine"), ("#4B2A6B", "Plum"), ("#FFFFFF", "White"))
EMOJIS = ("📌", "⭐", "🔥", "✅", "📝", "💡", "🎯", "📅", "⏰", "🛒", "💼", "🏠",
          "❤️", "🎉", "📚", "✈️", "💰", "🏋️", "🍎", "☕", "🎵", "🌱", "🚀", "⚡",
          "🧠", "📞", "✉️", "🔧", "🎨", "🐾", "🌙", "☀️")
RADII = ((4, "Square"), (10, "Soft"), (16, "Round"), (22, "Extra round"))   # corner radius, name


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
