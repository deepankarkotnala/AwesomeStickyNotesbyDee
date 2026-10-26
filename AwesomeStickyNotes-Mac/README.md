# Awesome Sticky Notes — macOS

Desktop sticky notes for daily to-dos, checklists and reminders, on soft, shadowed cards that sit on your Mac's desktop. This is the macOS edition of the Windows app in `AwesomeStickyNotesDee`. Both use the same code, so they have the same features.

Developed by Deepankar Kotnala.

## Install on a Mac

You need macOS 13 (Ventura) or later, and Python 3.10 to 3.14.

1. **Get Python** if the Mac doesn't have it: the free installer from [python.org](https://www.python.org/downloads/macos/), or `brew install python` if you use Homebrew. (The app tells you if it can't find one.)
2. **Copy `Awesome Sticky Notes.zip` to the Mac**, by AirDrop, a USB stick, a cloud drive or email. Copy the zip itself, not an unzipped folder: the zip keeps the app's launcher marked as a program, and a folder copied from Windows loses that, so macOS would refuse to open it.
3. **Double-click the zip** to unzip it, then drag **Awesome Sticky Notes** into your **Applications** folder.
4. **Double-click the app.** The app isn't signed with an Apple developer certificate, so the first time macOS blocks it:
   - macOS 13 or 14: right-click the app, choose **Open**, then click **Open**.
   - macOS 15 or later: close the message, open **System Settings → Privacy & Security**, scroll down, click **Open Anyway** next to Awesome Sticky Notes, and confirm.

   You only do this once.
5. **The first start sets up the app.** A notification says it's setting up: the app builds its own Python environment with the libraries it needs (PySide6 and PyObjC). This needs the internet and takes a minute or two. Your notes then appear, and the app's checklist icon shows in the **menu bar** at the top right.

From then on, double-click the app (or open it from Launchpad or Spotlight) and it starts at once. It runs from the menu bar and has no Dock icon. Only one copy runs at a time: opening it again brings your notes forward.

## Using it

| Action | How |
|---|---|
| New note in another colour | Hover over a note, click **+** in its header, then click a colour |
| Colour strength | **⋯** → Colour → **Saturation** slider (double-click it to reset) |
| Any colour | **⋯** → Colour → the rainbow dot at the end of the colours. Pick by eye, type a code such as `#FFD1DC` (or `#FD1` for short), or reuse a recent colour. The note shows it while you pick |
| Card style | **⋯** → Style: **Flat** (a plain card), **Elevated** (flat, lifted by a soft shadow) or **3D** (glossy with a deeper shadow). **Settings → Appearance** sets the style for new notes and can apply it to every note |
| Corners | **Settings → Appearance → Corners**: Square, Soft, Round or Extra round, for every note |
| Same look on every note | **⋯** → **Apply to all notes** → this colour, this style, these fonts & size, or the whole look |
| Customise everything | **⋯** → **Customise look…**: colour, card style, paper (lined, grid, dotted or a two-colour gradient), header (plain, tinted or solid), an emoji before the title, title font, text font, size, text colour, line spacing, checkbox shape (circle, square or heart) and how done tasks look (struck through or faded). Changes show on the note straight away |
| Paper look | **⋯** → Style → **Paper**: paper grain, nearly square corners and lifted ends, in any colour |
| Copy a look to other notes | **⋯** → **Copy style**, then click **Paste style** on each note you want to look the same. **Done copying** or Esc stops. Like Format Painter in Word |
| Restyle several notes | Hub → Notes: hover a note and tick its circle, tick more, then **Customise…** or **Paste style** for all of them |
| Add a task | Type in **Add a task** at the bottom of a note and press Return |
| Add a reminder | End the task with `@5pm`, `@tomorrow 9am`, `@30m` and so on, or use the bell on a task |
| Repeat a reminder | Bell on a task → **Repeat**: every 10, 15 or 30 minutes, every 1, 2 or 3 hours, daily, weekdays, weekly, monthly, or **Custom…** |
| Complete a task | Click its circle |
| Edit a task | Double-click it. Clearing the text deletes the task (it goes to the Recycle Bin) |
| Pin a task to the top | Hover over it and click the **pin**. Click the pin again to unpin |
| Reorder tasks | Drag a task up or down within its section |
| Move a note | Drag the dotted handle at the top, or anywhere on the header (the pointer turns into a hand) |
| Resize a note | Drag any edge or corner |
| Rename a note | Click its title |
| Text size | **⋯** → Text → Size, or ⌘ + scroll over the tasks, or ⌘ = / ⌘ − (⌘ 0 resets) |
| Font | **⋯** → Text → Font, or **Customise look…** for a separate title font. 21 fonts come with the app: clean (Inter, Roboto, Open Sans, Poppins, Montserrat, Lato, Nunito, DM Sans), handwritten (Caveat, Shantell Sans, Kalam, Patrick Hand, Indie Flower, Shadows Into Light, Gochi Hand, Architects Daughter, Permanent Marker), classic (Merriweather, Lora, Playfair Display) and code (JetBrains Mono) |
| Colour, type, position, completed style | The **⋯** button in the note header (shown on hover) |
| Collapse a note | The chevron in the header |
| Hide a note | The **×** button. Menu-bar icon → **Show all notes** brings it back |
| Recover something you deleted | Menu-bar icon → **Recycle Bin…**, which lists **Deleted notes** and **Deleted tasks** |
| History, reminders, settings | Menu-bar icon → **All notes…**, **Completed history…**, **Reminders…**, **Settings…** |

### Where notes sit

- **On desktop** (default): notes stay just above the desktop. Apps cover them, **Show Desktop** (F11 or the spread-fingers gesture) reveals them, and they appear on every Space.
- **Always on top**: notes float above all windows.
- **Tidy grid**: notes never overlap. When you let go of a note after moving or resizing it, it slides onto an invisible grid on its monitor, with an even gap between neighbouring notes. If it lands on another note, it moves to the nearest free spot. If you drag an edge into a neighbour, that edge stops at the neighbour. New, reopened and expanded notes find a free spot the same way. Only when every monitor is full do notes overlap.

Change this for one note under **⋯** → Position, or for all notes under **Settings → Where notes live**.

### Open at login

Turn on **Settings → Open at login**. This adds a LaunchAgent at `~/Library/LaunchAgents/com.dee.awesomestickynotes.plist` that opens the app when you log in, wherever the app is kept.

## Your data

Everything stays on your Mac, in your user folder:

| What | Where |
|---|---|
| Notes (SQLite), with a backup made on every start | `~/Library/Application Support/AwesomeStickyNotes/notes.db` and `notes.bak.db` |
| Readable log of every task (rows are never removed) | the same folder: `notes-log.txt`, `notes-log.xlsx` (opens in Excel or Numbers), `notes-log.json` |
| The app's own Python environment | `~/Library/Application Support/AwesomeStickyNotes/python` |
| Logs (setup, start-up errors) | `~/Library/Logs/AwesomeStickyNotes` |

**Settings → Data → Open folder** shows the notes folder in Finder. Items in the Recycle Bin stay in the database until you empty the bin.

Replacing the app with a newer version keeps your notes. If a newer version needs different libraries, it sets them up again the first time it opens.

To set up the Python environment again (for example after removing the Python it was built from), quit the app, delete the `python` folder above, and open the app.

## Moving notes between Windows and Mac

Both editions use the same database. Close the app on both computers, then copy `notes.db` between `StickyNotesDB\notes.db` in the Windows app folder and `~/Library/Application Support/AwesomeStickyNotes/notes.db` on the Mac. (In Finder, **Go → Go to Folder…** and paste the path.)

## Uninstall

1. Turn off **Settings → Open at login** if it's on, then quit from the menu-bar icon (**Quit**).
2. Drag the app from Applications to the Bin.
3. To remove your notes and the app's Python environment too, delete `~/Library/Application Support/AwesomeStickyNotes` and `~/Library/Logs/AwesomeStickyNotes`.

## For whoever maintains the app

This folder holds the source of the Mac app:

```
AwesomeStickyNotes.py        entry point; the app runs it with its own Python
requirements.txt             PySide6 and PyObjC's Cocoa bridge, exact versions
stickynotes/                 the app itself, identical to the Windows edition's
packaging/launcher.sh        what double-clicking the app runs: sets up Python the first time, then starts
packaging/AppIcon.icns       the app icon
build-app.py                 builds the app and Awesome Sticky Notes.zip
Awesome Sticky Notes.zip     the built app, ready to copy to a Mac
```

**After changing the code:** copy `stickynotes/` from the Windows edition (the two must stay identical), then run `python build-app.py` with any Python 3. It needs no extra libraries and works on Windows or a Mac. It writes a fresh `Awesome Sticky Notes.zip`; on a Mac it also leaves `Awesome Sticky Notes.app` here, ready to open.

**Running from source on a Mac**, without building the app: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `python3 AwesomeStickyNotes.py` (it hands over to `.venv`). Notes then live in `StickyNotesDB/` in this folder.

## Not yet confirmed on a real Mac

This edition was built and tested on Windows. The launcher's every path was run under bash, with stand-ins for macOS tools and Python: first-run setup, normal start, update, already running, no Python, failed setup, double-click during setup, and old macOS. The app's code was run from inside the built app with the macOS code paths switched on. These still need confirming on a Mac:

- double-clicking the app and the first-run setup, including the security prompt
- the desktop window level, the menu-bar-only mode and the Reduce Motion check
- the LaunchAgent for Open at login
