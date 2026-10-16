#!/bin/bash
# Builds the app's own Python environment (.venv) with the exact libraries in requirements.txt.
# Double-click it in Finder once, and again if the app says its environment is missing or broken.
cd "$(dirname "$0")" || exit 1

# PySide6 6.11 supports Python 3.10 to 3.14; use the newest one installed.
PY=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 14))' 2>/dev/null; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3.10 to 3.14 is needed. Install it from https://www.python.org/downloads/macos/ and run this again."
    read -r -p "Press Return to close. " _
    exit 1
fi

echo "Close Awesome Sticky Notes before continuing."
read -r -p "Press Return to build .venv with $("$PY" --version)... " _
if "$PY" -m venv --clear .venv && .venv/bin/python3 -m pip install --disable-pip-version-check -r requirements.txt; then
    echo
    echo "Done. Double-click \"Start Awesome Sticky Notes.command\" to start the app."
else
    echo
    echo "Setup failed - see the messages above."
fi
read -r -p "Press Return to close. " _
