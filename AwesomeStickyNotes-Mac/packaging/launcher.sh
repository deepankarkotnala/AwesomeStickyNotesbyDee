#!/bin/bash
# Awesome Sticky Notes for macOS: double-clicking the app runs this script (Contents/MacOS/AwesomeStickyNotes).
#
# The first time, it builds the app's own Python environment, with the exact libraries in requirements.txt
# (PySide6 and PyObjC), in ~/Library/Application Support/AwesomeStickyNotes/python. It uses Python 3.10-3.14
# from python.org or Homebrew, needs the internet, and takes a minute or two. After that the app starts at once.
# The app runs in the background from the menu bar; opening it again brings your notes forward.
# Written for the bash 3.2 that comes with macOS.

NAME="Awesome Sticky Notes"
CONTENTS="$(cd "$(dirname "$0")/.." && pwd)"
CODE="$CONTENTS/Resources/app"
SUPPORT="$HOME/Library/Application Support/AwesomeStickyNotes"
ENV="$SUPPORT/python"
LOGS="$HOME/Library/Logs/AwesomeStickyNotes"
LOCK="$SUPPORT/.setting-up"

notify() {   # a notification in the corner of the screen
    osascript -e "display notification \"$1\" with title \"$NAME\"" >/dev/null 2>&1
}

ask() {   # ask MESSAGE BUTTONS DEFAULT ICON: shows a dialog and prints the button clicked
    osascript -e "button returned of (display dialog \"$1\" buttons {$2} default button $3 with icon $4 with title \"$NAME\")" 2>/dev/null
}

find_python() {   # the newest Python 3.10-3.14 from python.org or Homebrew (never Apple's /usr/bin/python3)
    for v in 3.14 3.13 3.12 3.11 3.10; do
        for p in "/Library/Frameworks/Python.framework/Versions/$v/bin/python$v" \
                 "/opt/homebrew/bin/python$v" "/usr/local/bin/python$v"; do
            if [ -x "$p" ] && "$p" -c 'import venv' >/dev/null 2>&1; then
                echo "$p"
                return 0
            fi
        done
    done
    for p in /opt/homebrew/bin/python3 /usr/local/bin/python3; do
        if [ -x "$p" ] && "$p" -c 'import sys; sys.exit(not (3, 10) <= sys.version_info[:2] <= (3, 14))' >/dev/null 2>&1; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

ready() {   # the environment exists, still works, and was built for this version of the app
    [ -x "$ENV/bin/python3" ] &&
        "$ENV/bin/python3" -c 'import PySide6' >/dev/null 2>&1 &&
        cmp -s "$CODE/requirements.txt" "$ENV/app-requirements.txt"
}

running() {   # the app is already running, from this copy or an older one
    pgrep -f "Resources/app/AwesomeStickyNotes.py" >/dev/null 2>&1
}

take_lock() {   # only one setup at a time; a lock older than 20 minutes was left by an interrupted setup
    mkdir "$LOCK" 2>/dev/null && return 0
    if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +20 2>/dev/null)" ]; then
        rm -rf "$LOCK"
        mkdir "$LOCK" 2>/dev/null && return 0
    fi
    return 1
}

setup() {
    if ! take_lock; then
        notify "Still setting up. $NAME opens by itself when it is ready."
        exit 0
    fi
    trap 'rm -rf "$LOCK"' EXIT
    PY="$(find_python)"
    if [ -z "$PY" ]; then
        choice="$(ask "$NAME needs Python 3.10 or newer, which is free. Install it from python.org (the macOS installer), then open $NAME again." '"Cancel", "Get Python"' '"Get Python"' caution)"
        [ "$choice" = "Get Python" ] && open "https://www.python.org/downloads/macos/"
        exit 1
    fi
    notify "Setting up for the first time. This takes a minute or two."
    {
        echo "Setting up with $PY ($("$PY" --version 2>&1)) on $(date)"
        "$PY" -m venv --clear "$ENV" &&
            "$ENV/bin/python3" -m pip install --disable-pip-version-check -r "$CODE/requirements.txt" &&
            cp "$CODE/requirements.txt" "$ENV/app-requirements.txt"
    } >"$LOGS/setup.log" 2>&1
    if [ $? -ne 0 ]; then
        choice="$(ask "Setup could not finish. Check that the Mac is connected to the internet, then open $NAME again." '"Show details", "OK"' '"OK"' stop)"
        [ "$choice" = "Show details" ] && open -e "$LOGS/setup.log"
        exit 1
    fi
    rm -rf "$LOCK"
}

main() {
    mkdir -p "$SUPPORT" "$LOGS"
    major="$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)"
    if [ -n "$major" ] && [ "$major" -lt 13 ]; then
        ask "$NAME needs macOS 13 (Ventura) or later." '"OK"' '"OK"' stop >/dev/null
        exit 1
    fi
    # An update waits while an older copy is running: this start only brings its notes forward.
    if ! ready && ! running; then
        setup
    fi
    log="$LOGS/app.log"
    if [ -f "$log" ] && [ "$(stat -f%z "$log" 2>/dev/null || echo 0)" -gt 1048576 ]; then
        mv -f "$log" "$log.old"
    fi
    cd "$SUPPORT" || exit 1
    # Keep Python's compiled-code caches out of the app bundle.
    PYTHONPYCACHEPREFIX="$SUPPORT/pycache" nohup "$ENV/bin/python3" "$CODE/AwesomeStickyNotes.py" >>"$log" 2>&1 &
    exit 0
}

main "$@"
