#!/bin/bash
# Double-click in Finder to start Awesome Sticky Notes in the background, from the app's own .venv.
cd "$(dirname "$0")" || exit 1
PY=.venv/bin/python3
[ -x "$PY" ] || PY=python3   # no .venv yet: the app explains how to run setup.command
nohup "$PY" AwesomeStickyNotes.py >/dev/null 2>&1 &
# Close the Terminal window that Finder opened for this script.
osascript -e 'tell application "Terminal" to close (every window whose name contains "Start Awesome Sticky Notes")' >/dev/null 2>&1 &
exit 0
