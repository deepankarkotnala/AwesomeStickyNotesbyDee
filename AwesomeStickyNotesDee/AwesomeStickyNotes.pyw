"""Launch Awesome Sticky Notes. Double-click this file (runs with pythonw, no console window).

The app runs in its own Python environment, `.venv` next to this file (setup.bat creates it).
Whichever Python opens this file only hands over to that environment, so the system's
default Python and its libraries don't matter.
"""
import subprocess
import sys
import traceback
from pathlib import Path

TITLE = "Awesome Sticky Notes could not start"
VENV = Path(__file__).resolve().with_name(".venv")
VENV_PYTHONW = VENV / "Scripts" / "pythonw.exe"


def fail(message: str) -> None:
    """pythonw has no console, so surface startup errors in a dialog and a log file."""
    log = Path(__file__).with_name("startup-error.log")
    log.write_text(f"Python: {sys.executable}\n\n{message}", encoding="utf-8")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f"{message}\n\nDetails saved to:\n{log}", TITLE, 0x10)
    except Exception:
        pass


def venv_base() -> Path:
    """The Python install `.venv` was built from. The environment stops working if it is uninstalled."""
    for line in (VENV / "pyvenv.cfg").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "home":
            return Path(value.strip())
    return VENV


if __name__ == "__main__":
    if VENV_PYTHONW.exists() and Path(sys.prefix).resolve() != VENV:
        base = venv_base()
        if not (base / "pythonw.exe").exists():
            fail(f"The Python this app's environment was built from is missing:\n{base}\n\n"
                 "Close this message and run setup.bat in the app folder to rebuild it.")
            sys.exit(1)
        subprocess.Popen([str(VENV_PYTHONW), str(Path(__file__).resolve()), *sys.argv[1:]])
        sys.exit(0)
    try:
        import PySide6  # noqa: F401
    except ImportError:
        fail(f"PySide6 is not installed for this Python:\n{sys.executable}\n\n"
             "Run setup.bat in the app folder to create the app's own Python environment.")
        sys.exit(1)
    try:
        from stickynotes.app import main
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        fail(traceback.format_exc())
        sys.exit(1)
