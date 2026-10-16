#!/usr/bin/env python3
"""Launch Awesome Sticky Notes on macOS.

Run it with `python3 AwesomeStickyNotes.py`, or double-click "Start Awesome Sticky Notes.command" in Finder.
The app runs in its own Python environment, `.venv` next to this file (setup.command creates it).
Whichever Python starts this file only hands over to that environment.
"""
import os
import subprocess
import sys
import traceback
from pathlib import Path

TITLE = "Awesome Sticky Notes could not start"
VENV = Path(__file__).resolve().with_name(".venv")
VENV_PYTHON = VENV / "bin" / "python3"


def fail(message: str) -> None:
    """Started from Finder there is no terminal to read, so also show an alert and keep a log file."""
    log = Path(__file__).with_name("startup-error.log")
    log.write_text(f"Python: {sys.executable}\n\n{message}", encoding="utf-8")
    print(message, file=sys.stderr)
    short = message.strip().splitlines()[-1].replace('"', "'")[:300]
    try:
        subprocess.run(["osascript", "-e",
                        f'display alert "{TITLE}" message "{short}\n\nDetails: {log}" as critical'],
                       check=False, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pass


if __name__ == "__main__":
    # exists() follows the symlink, so a .venv whose base Python was removed falls through to the message below.
    if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != VENV:
        os.execv(VENV_PYTHON, [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
    try:
        import PySide6  # noqa: F401
    except ImportError:
        fail(f"PySide6 is not installed for this Python ({sys.executable}).\n"
             "Double-click setup.command in the app folder to create the app's own Python environment.")
        sys.exit(1)
    try:
        from stickynotes.app import main
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        fail(traceback.format_exc())
        sys.exit(1)
