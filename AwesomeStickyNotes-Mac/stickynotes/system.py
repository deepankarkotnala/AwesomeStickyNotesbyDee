"""Platform layer: the same functions on every OS, implemented by `winutil` (Windows) or `macutil` (macOS).

window_flags(kind)          Qt flags for "note" and "toast" windows
prepare(widget)             platform tweaks before such a window is shown
pin_to_desktop(widget)      keep a note on the desktop layer (survives Show Desktop)
set_topmost(widget)         keep a note above all windows
remove_frame(widget)        drop any border the OS adds to frameless windows
move_phase(type, message)   "start"/"end" of the user dragging a window (from nativeEvent), else None
click_through(w, type, message, solid)   nativeEvent reply that lets clicks outside `solid` fall through
set_caption_color(w, hex)   tint a normal window's title bar where supported
shell_token()               changes when the desktop shell restarts (0 if not applicable)
animations_enabled()        the OS "reduce motion"/"animation effects" setting
configure_app(app)          app identity / menu-bar-only mode
activate_app()              bring the app to the front before showing a window
chime()                     reminder sound
open_folder(path)           reveal a folder in Explorer / Finder
fallback_data_dir()         per-user data folder used if the app folder is read-only
app_bundle()                the macOS .app the code runs from, else None
set_autostart(on), autostart_enabled()   start with Windows / at macOS login
"""
import sys

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# Wording that differs between platforms.
TRAY = "menu-bar icon" if IS_MAC else "tray icon"
AUTOSTART_LABEL = "Open at login" if IS_MAC else "Start with Windows"
SHOW_DESKTOP = "Show Desktop (F11)" if IS_MAC else "Win+D"

if IS_MAC:
    from .macutil import (LAUNCHER, activate_app, animations_enabled, app_bundle, autostart_enabled, chime,
                          click_through, configure_app, fallback_data_dir, move_phase, open_folder,
                          pin_to_desktop, prepare, remove_frame, set_autostart, set_caption_color, set_topmost,
                          shell_token, window_flags)
else:
    from .winutil import (LAUNCHER, activate_app, animations_enabled, app_bundle, autostart_enabled, chime,
                          click_through, configure_app, fallback_data_dir, move_phase, open_folder,
                          pin_to_desktop, prepare, remove_frame, set_autostart, set_caption_color, set_topmost,
                          shell_token, window_flags)

__all__ = ["AUTOSTART_LABEL", "IS_MAC", "IS_WINDOWS", "SHOW_DESKTOP", "TRAY", "LAUNCHER", "activate_app",
           "animations_enabled", "app_bundle", "autostart_enabled", "chime", "click_through",
           "configure_app", "fallback_data_dir", "move_phase", "open_folder", "pin_to_desktop", "prepare", "remove_frame",
           "set_autostart", "set_caption_color", "set_topmost", "shell_token", "window_flags"]
