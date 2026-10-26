#!/usr/bin/env python3
"""Start Awesome Sticky Notes on macOS.

"Awesome Sticky Notes.app" runs this file with the Python environment it sets up the first time it opens
(see packaging/launcher.sh). To run straight from this folder instead, while working on the code, create
`.venv` here (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`) and run
`python3 AwesomeStickyNotes.py`; it hands over to `.venv`.
"""
import os
import subprocess
import sys
import traceback
from pathlib import Path

TITLE = "Awesome Sticky Notes could not start"
HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
VENV_PYTHON = VENV / "bin" / "python3"
LOGS = Path.home() / "Library" / "Logs" / "AwesomeStickyNotes"


def fail(message: str) -> None:
    """Started from Finder there is no terminal to read, so also show an alert and keep a log file.
    Inside the app bundle the log goes to ~/Library/Logs, as the app itself may be read-only."""
    folder = LOGS if ".app/Contents/" in str(HERE) or not os.access(HERE, os.W_OK) else HERE
    log = folder / "startup-error.log"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        log.write_text(f"Python: {sys.executable}\n\n{message}", encoding="utf-8")
        where = f"\n\nDetails: {log}"
    except OSError:
        where = ""
    print(message, file=sys.stderr)
    short = message.strip().splitlines()[-1].replace('"', "'").replace("\\", "/")[:300]
    try:
        subprocess.run(["osascript", "-e", f'display alert "{TITLE}" message "{short}{where}" as critical'],
                       check=False, timeout=120)
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
             "Quit, then open Awesome Sticky Notes again: the app sets up its own Python environment.")
        sys.exit(1)
    try:
        from stickynotes.app import main
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        fail(traceback.format_exc())
        sys.exit(1)
