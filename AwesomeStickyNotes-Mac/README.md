# Awesome Sticky Notes — macOS

Desktop sticky notes for daily to-dos, checklists and reminders, on soft, shadowed cards that sit on your Mac's desktop. This is the macOS edition of the Windows app in `AwesomeStickyNotesDee`; both use the same code.

Developed by Deepankar Kotnala.

## Requirements

- macOS 13 (Ventura) or later, because PySide6 6.11 needs it
- Python 3.10 to 3.14. Use the [python.org installer](https://www.python.org/downloads/macos/) or `brew install python`

## Install

Double-click **setup.command** in Finder, or run `bash setup.command` in Terminal from this folder. It builds the app's own Python environment in `.venv`, using the newest Python 3.10–3.14 it finds, and installs the exact library versions in `requirements.txt`: PySide6 (Qt) and PyObjC's Cocoa bridge. Without PyObjC the app still runs, but notes behave like ordinary windows instead of sitting on the desktop layer, and the app shows a Dock icon.

The app always runs from `.venv`, so installing or upgrading other Pythons or libraries can't break it. If the Python that `.venv` was built from is removed, the app says so on start; run `setup.command` again.

## Run

Double-click **Start Awesome Sticky Notes.command** in Finder, or run `python3 AwesomeStickyNotes.py` (it hands over to `.venv`). Two things may need doing the first time, for both `.command` files:

- If Finder says the file isn't executable, run `chmod +x *.command` once in this folder.
- If macOS blocks it as coming from an unidentified developer, right-click it, choose **Open**, then confirm **Open**.

The app runs from the **menu bar**: look for the checklist icon at the top right. It has no Dock icon. Only one copy runs at a time; starting it again brings your notes forward.

## Using it

| Action | How |
|---|---|
| New note in another colour | Hover over a note, click **+**, then click a colour |
| Colour strength | **⋯** → Colour → **Saturation** slider (double-click it to reset) |
| Add a task | Type in **Add a task** and press Return |
| Add a reminder | End the task with `@5pm`, `@17:30`, `@tomorrow 9am`, `@fri 10am`, `@tonight`, `@30m`, `@2h`, or use the bell on a task |
| Complete a task | Click its circle |
| Edit a task | Double-click it. Clearing the text deletes the task (it goes to the Recycle Bin) |
| Pin a task to the top | Hover over it and click the **pin**. Pinned tasks stay in a **Pinned** section at the top of the note, above everything else. Click the pin again to unpin |
| Reorder tasks | Drag a task up or down within its section, so pinned tasks are reordered among themselves and always stay above the rest |
| Rename a note | Click its title |
| Text size | **⋯** → Text → Size, or ⌘ + scroll over the tasks, or ⌘ = / ⌘ − (⌘ 0 resets) |
| Font | **⋯** → Text → Font. Noteworthy and Marker Felt give a handwritten look |
| Move / resize | Drag the header / drag the dotted grip in the bottom-right corner |
| Hide a note | **×**. Click the menu-bar icon to show it again |
| Recover something you deleted | Menu-bar icon → **Recycle Bin…**. It has two sections, **Deleted notes** and **Deleted tasks**. Restore an item, delete it forever, or **Empty bin** |
| History, reminders, settings | Menu-bar icon → **All notes…**, **Completed history…**, **Recycle Bin…**, **Settings…** |

### Where notes sit

- **On desktop** (default): notes stay just above the desktop. Apps cover them, **Show Desktop** (F11 or the spread-fingers gesture) reveals them, and they appear on every Space.
- **Always on top**: notes float above all windows.

Change it per note under **⋯** → Position, or for all notes in Settings.

### Recycle Bin

Deleting a note, or a task with its **×** button, moves it to the Recycle Bin instead of erasing it. Items stay there until you restore them or empty the bin.

- **Restoring a note** puts it back on the desktop with all of its tasks.
- **Restoring a task** puts it back in its old place on its note.
- Tasks you deleted on their own before deleting their note stay in **Deleted tasks** after the note is restored.
- **Delete forever** and **Empty bin** can't be undone.

### Open at login

Turn on **Settings → Open at login**. This adds a LaunchAgent at `~/Library/LaunchAgents/com.dee.awesomestickynotes.plist`, which runs the app from this folder with the Python in `.venv`. If you move the folder, start the app once from its new location and the LaunchAgent is updated to match.

## Data

Notes are stored locally in SQLite in `StickyNotesDB/notes.db` inside this folder, with a backup (`notes.bak.db`) made on every start. Items in the Recycle Bin stay in the database, marked with a `deleted_at` time, until the bin is emptied. If the folder isn't writable, the database goes to `~/Library/Application Support/AwesomeStickyNotes` instead. `StickyNotesDB/` is git-ignored.

The same folder holds a readable log of every task: `notes-log.txt` (plain text) and `notes-log.xlsx` (opens in Excel or Numbers), oldest first by creation date with their status (Pending or Completed) and, once deleted, whether the task is in the Recycle Bin or deleted for good. They are rewritten about a second after each change, and rows are never removed; the history behind them is kept in `notes-log.json`.

To move notes between your Windows PC and your Mac, copy `notes.db` between the two `StickyNotesDB` folders while both apps are closed.

## Build a standalone .app (optional)

```bash
.venv/bin/python3 -m pip install pyinstaller
.venv/bin/pyinstaller --windowed --name "Awesome Sticky Notes" --osx-bundle-identifier com.dee.awesomestickynotes AwesomeStickyNotes.py
```

The app is created at `dist/Awesome Sticky Notes.app`. A packaged app keeps its notes in `~/Library/Application Support/AwesomeStickyNotes`, because writing inside an app bundle breaks its signature.

## Notes on this edition

This edition was written and checked on Windows by running its macOS code paths there. It has not yet been run on a real Mac, so the AppKit parts need confirming on one:

- the desktop window level
- the menu-bar-only mode
- the Reduce Motion check
- the LaunchAgent
- `setup.command` and the hand-over to `.venv`

Everything else is the same Qt code as the tested Windows app.
