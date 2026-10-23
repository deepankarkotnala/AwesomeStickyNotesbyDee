"""macOS backend for `system`: desktop-level windows, menu-bar-only app, login item, sounds.

Desktop pinning, hiding the Dock icon and the Reduce Motion check use AppKit through PyObjC
(`pip install pyobjc-framework-Cocoa`). Without it everything still works; notes then behave like
ordinary windows and the app keeps a Dock icon.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt

from . import SLUG

LAUNCHER = "AwesomeStickyNotes.py"
AGENT_LABEL = "com.dee.awesomestickynotes"
AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{AGENT_LABEL}.plist"

# kCGDesktopIconWindowLevel + 1: above the desktop and its icons, below every app window.
DESKTOP_LEVEL = -2147483603 + 1
FLOATING_LEVEL = 3                      # NSFloatingWindowLevel
# NSWindowCollectionBehavior: CanJoinAllSpaces | Stationary | IgnoresCycle
DESKTOP_BEHAVIOR = (1 << 0) | (1 << 4) | (1 << 6)
TOP_BEHAVIOR = (1 << 0) | (1 << 6)

try:
    import objc
    from AppKit import NSApplication, NSWorkspace
    HAVE_APPKIT = True
except ImportError:          # PyObjC not installed: fall back to plain Qt behaviour
    HAVE_APPKIT = False


def _ns_window(widget):
    if not HAVE_APPKIT:
        return None
    try:
        view = objc.objc_object(c_void_p=int(widget.winId()))   # Qt's winId() is the NSView
        return view.window()
    except Exception:
        return None


# ---------------------------------------------------------------- windows
def window_flags(kind: str) -> Qt.WindowType:
    # Notes are regular windows: on macOS, Qt "tool" windows (NSPanels) vanish whenever the app is
    # in the background. No native shadow - the card paints its own.
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
    if kind == "toast":
        return flags | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
    return flags | Qt.WindowType.Window


def prepare(widget) -> None:
    widget.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)


def move_phase(event_type, message) -> str | None:
    return None   # not reported on macOS: notes tidy up once they have stopped moving instead


def click_through(widget, event_type, message, solid) -> int | None:
    return None   # not done on macOS yet: the faint edge of a shadow still catches clicks there


def shell_token() -> int:
    return 0   # nothing like an Explorer restart to watch for on macOS


def pin_to_desktop(widget) -> None:
    """Keep the note just above the desktop: apps cover it, and 'Show Desktop' (F11 / spread gesture)
    leaves it in place. It also appears on every Space."""
    window = _ns_window(widget)
    if window is not None:
        window.setLevel_(DESKTOP_LEVEL)
        window.setCollectionBehavior_(DESKTOP_BEHAVIOR)


def set_topmost(widget) -> None:
    window = _ns_window(widget)
    if window is not None:
        window.setLevel_(FLOATING_LEVEL)
        window.setCollectionBehavior_(TOP_BEHAVIOR)
    elif not widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
        widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        widget.show()


def remove_frame(widget) -> None:
    """Frameless windows have no system border on macOS."""


def set_caption_color(widget, hex_color: str) -> None:
    """The macOS title bar follows the system appearance."""


def animations_enabled() -> bool:
    """System Settings > Accessibility > Display > Reduce motion."""
    if HAVE_APPKIT:
        try:
            return not NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion()
        except Exception:
            pass
    return True


# ---------------------------------------------------------------- app
def configure_app(app) -> None:
    """Run as a menu-bar app: no Dock icon, no app menu (the menu-bar icon is the way in)."""
    if HAVE_APPKIT:
        NSApplication.sharedApplication().setActivationPolicy_(1)   # NSApplicationActivationPolicyAccessory


def activate_app() -> None:
    """Menu-bar apps aren't brought forward automatically; do it before showing a window."""
    if HAVE_APPKIT:
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)


def chime() -> None:
    sound = "/System/Library/Sounds/Glass.aiff"
    try:
        subprocess.Popen(["afplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        from PySide6.QtWidgets import QApplication
        QApplication.beep()


def open_folder(path: Path) -> None:
    subprocess.Popen(["open", str(path)])


def fallback_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / SLUG


# ---------------------------------------------------------------- start at login
def launch_arguments() -> list[str]:
    if getattr(sys, "frozen", False):        # packaged as an .app
        return [sys.executable]
    script = Path(__file__).resolve().parent.parent / LAUNCHER
    return [sys.executable, str(script)]


def set_autostart(enabled: bool) -> None:
    """A per-user LaunchAgent that starts the app when you log in."""
    if enabled:
        AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AGENT_PATH, "wb") as fh:
            plistlib.dump({
                "Label": AGENT_LABEL,
                "ProgramArguments": launch_arguments(),
                "RunAtLoad": True,
                "ProcessType": "Interactive",
            }, fh)
    else:
        try:
            os.remove(AGENT_PATH)
        except FileNotFoundError:
            pass


def autostart_enabled() -> bool:
    return AGENT_PATH.exists()
