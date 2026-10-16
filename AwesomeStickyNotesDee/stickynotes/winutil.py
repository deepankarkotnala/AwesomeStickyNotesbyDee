"""Windows backend for `system`: desktop pinning, always-on-top, autostart, frame and app identity.

Every function takes the Qt widget it acts on; `system.py` exposes the same names on every platform.
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt

from . import APP_ID, SLUG

LAUNCHER = "AwesomeStickyNotes.pyw"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = SLUG
LEGACY_RUN_VALUES = ("StickyNotesDee", "AwesomeStickyNotesDee")   # earlier names; cleaned up automatically

HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_NOOWNERZORDER = 0x0001, 0x0002, 0x0010, 0x0200
GWLP_HWNDPARENT = -8

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
_set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
_set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
_set_long.restype = ctypes.c_void_p


def _hwnd(value: int) -> wintypes.HWND:
    return wintypes.HWND(value % (1 << (8 * ctypes.sizeof(ctypes.c_void_p))))


def _handle(widget) -> int:
    return int(widget.winId())


def _dwm_set(widget, attribute: int, value: ctypes._SimpleCData) -> None:
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(_hwnd(_handle(widget)), attribute, ctypes.byref(value),
                                                   ctypes.sizeof(value))
    except (AttributeError, OSError):
        pass  # attribute unknown on this Windows version


# ---------------------------------------------------------------- windows
def window_flags(kind: str) -> Qt.WindowType:
    """Frameless tool windows: no taskbar button, no Alt+Tab entry."""
    flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
    if kind == "toast":
        flags |= Qt.WindowType.WindowStaysOnTopHint
    return flags


def prepare(widget) -> None:
    """Platform tweaks before a note/toast window is shown (nothing needed on Windows)."""


def shell_token() -> int:
    """Changes when Explorer restarts, so pinned notes know to re-attach to the new desktop."""
    return user32.FindWindowW("Progman", None) or 0


def _set_owner(widget, owner: int) -> None:
    _set_long(_hwnd(_handle(widget)), GWLP_HWNDPARENT, owner or None)


def _set_z(widget, after: int) -> None:
    user32.SetWindowPos(_hwnd(_handle(widget)), _hwnd(after), 0, 0, 0, 0,
                        SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_NOOWNERZORDER)


def pin_to_desktop(widget) -> None:
    """Let the window live on the desktop: other apps cover it, and Win+D / "Show desktop" keeps it visible.

    Owning the window by the shell's desktop window ties it to the desktop layer, so Show Desktop
    reveals it together with the desktop instead of minimising it.
    """
    _set_z(widget, HWND_NOTOPMOST)
    _set_owner(widget, shell_token())


def set_topmost(widget) -> None:
    _set_owner(widget, 0)
    _set_z(widget, HWND_TOPMOST)


def remove_frame(widget) -> None:
    """Stop Windows 11 from drawing its rounded corners and 1px border around a frameless window.

    Our windows are bigger than the card they paint (the extra room holds the soft shadow), so the
    system border would otherwise outline that invisible area as a grey box.
    """
    _dwm_set(widget, 33, ctypes.c_int(1))              # DWMWA_WINDOW_CORNER_PREFERENCE = DONOTROUND
    _dwm_set(widget, 34, ctypes.c_uint(0xFFFFFFFE))    # DWMWA_BORDER_COLOR = COLOR_NONE


def set_caption_color(widget, hex_color: str) -> None:
    """Tint the Windows 11 title bar to match the window background (ignored on older Windows)."""
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    _dwm_set(widget, 35, ctypes.c_uint32(r | (g << 8) | (b << 16)))   # DWMWA_CAPTION_COLOR


def animations_enabled() -> bool:
    """Windows Settings > Accessibility > Visual effects > Animation effects."""
    enabled = wintypes.BOOL(True)
    try:
        ok = user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)  # SPI_GETCLIENTAREAANIMATION
    except (AttributeError, OSError):
        return True
    return bool(enabled.value) if ok else True


# ---------------------------------------------------------------- app
def configure_app(app) -> None:
    """Group the app's windows and notifications under its own identity instead of python.exe."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        pass


def activate_app() -> None:
    """Bring the app forward before showing a window (Windows does this per window already)."""


def chime() -> None:
    import winsound
    try:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except RuntimeError:
        pass


def open_folder(path: Path) -> None:
    os.startfile(path)


def fallback_data_dir() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home()) / SLUG


# ---------------------------------------------------------------- autostart
def launch_command() -> str:
    if getattr(sys, "frozen", False):  # packaged with PyInstaller
        return f'"{sys.executable}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    script = Path(__file__).resolve().parent.parent / LAUNCHER
    return f'"{pythonw if pythonw.exists() else exe}" "{script}"'


def set_autostart(enabled: bool) -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        for old in LEGACY_RUN_VALUES:
            try:
                winreg.DeleteValue(key, old)
            except FileNotFoundError:
                pass
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass


def autostart_enabled() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            for name in (RUN_VALUE, *LEGACY_RUN_VALUES):
                try:
                    winreg.QueryValueEx(key, name)
                    return True
                except FileNotFoundError:
                    continue
    except FileNotFoundError:
        pass
    return False
