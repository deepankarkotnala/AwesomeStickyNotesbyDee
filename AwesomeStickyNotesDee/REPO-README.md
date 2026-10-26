# Awesome Sticky Notes

Desktop sticky notes for daily to-dos, checklists and reminders, on soft, shadowed cards that sit on your desktop. The app comes in a Windows edition and a macOS edition. Both run the same Python code, built with [PySide6](https://doc.qt.io/qtforpython-6/) (Qt).

Developed by Deepankar Kotnala.

**Jump to:** [Windows edition](#windows-edition) · [macOS edition](#macos-edition) · [Moving notes between Windows and Mac](#moving-notes-between-windows-and-mac) · [Code layout](#code-layout)

## What it does

- **Daily to-do notes.** Unfinished tasks from earlier days stay on the note under **Carried over**, with a "Since Tue" badge. Tasks you finish today are either struck through until midnight or hidden straight away, as you choose in Settings. Older finished tasks leave the note but stay in **Completed history**.
- **Checklists.** A plain list. Checked items stay struck through until you choose **Clear completed**.
- **Reminders typed into the task.** End a task with `@5pm`, `@17:30`, `@tomorrow 9am`, `@fri 10am`, `@tonight`, `@30m` or `@2h`, or use the bell on a task. Reminders can repeat: every few minutes or hours, daily, on weekdays, weekly, monthly, or a custom gap (bell → **Repeat**). When a reminder is due, a card slides in at the bottom-right with **Mark done** and **Snooze** pills for 10, 20 or 30 minutes, an hour, or a custom time. Reminders that came due while the app was closed show up the next time it starts.
- **Pinned tasks and drag-to-reorder.** Pinned tasks stay in a **Pinned** section at the top of the note. You can drag tasks up and down within their section.
- **Recycle Bin.** Deleting a note, or a task with its **×** button, moves it to the bin instead of erasing it. Restoring a note brings it back with all its tasks, and restoring a task puts it back where it was. **Delete forever** and **Empty bin** can't be undone.
- **A look for each note.** Each note has its own colour: 15 ready-made pastels and darks, or any colour from a picker or a `#RRGGBB` code, with a saturation slider from a faint tint to the full colour. Each also has its own card style (flat, elevated with a soft shadow, or glossy 3D), font and text size, a paper look, lined, grid, dotted or gradient paper, a header band and emoji, 21 bundled fonts, and heart or square checkboxes. A note's look can be copied to others like Format Painter, applied to several notes at once, or to every note. Each note can also sit on the desktop or stay on top of other windows.
- **Your notes stay on your computer.** They are kept in a local SQLite database next to the app, with a backup made every time it starts.

## Repository layout

```
AwesomeStickyNotesDee/      Windows edition
AwesomeStickyNotes-Mac/     macOS edition
```

Each folder is a complete copy of the app and has its own README. The `stickynotes/` package inside them is identical; only the launcher, the setup script and `requirements.txt` differ.

---

## Windows edition

Everything in this half happens in the **`AwesomeStickyNotesDee`** folder.

### Requirements

- Windows 10 or 11
- Python 3.14 from [python.org](https://www.python.org/downloads/windows/). `setup.bat` finds it with the `py` launcher (`py -3.14`), which the python.org installer adds.

### Install

1. Clone or download this repository.
2. Open the `AwesomeStickyNotesDee` folder and run **`setup.bat`** once. It builds the app's own Python environment in `.venv` and installs the exact library versions in `requirements.txt` (PySide6 6.11.0).

### Run

Double-click **`AwesomeStickyNotes.pyw`**. Your notes appear on the desktop, and the app's icon appears in the system tray at the bottom-right of the taskbar (it may be hidden behind the **^** arrow). Only one copy runs at a time. Launching it again brings your notes forward.

The app always runs from `.venv`, whichever Python Windows uses to open the `.pyw`, so installing or upgrading other Pythons or libraries can't break it. If Python 3.14 itself is uninstalled, the app says so when it starts; reinstall Python 3.14 and run `setup.bat` again.

If the app doesn't start, the error appears in a dialog and is saved to `startup-error.log` in the app folder. To see error output in a console, run:

```powershell
.venv\Scripts\python AwesomeStickyNotes.pyw
```

### Using it on Windows

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
| Add a task | Type in **Add a task** at the bottom of a note and press Enter |
| Add a reminder | End the task with `@5pm`, `@tomorrow 9am`, `@30m` and so on, or use the bell on a task |
| Repeat a reminder | Bell on a task → **Repeat**: every 10, 15 or 30 minutes, every 1, 2 or 3 hours, daily, weekdays, weekly, monthly, or **Custom…** |
| Complete a task | Click its circle |
| Edit a task | Double-click it. Clearing the text deletes the task (it goes to the Recycle Bin) |
| Pin a task to the top | Hover over it and click the **pin**. Click the pin again to unpin |
| Reorder tasks | Drag a task up or down (a grip appears on its left when you hover). Completed tasks stay in the order you finished them |
| Move a note | Drag the dotted handle at the top, or anywhere on the header (the pointer turns into a hand) |
| Resize a note | Drag any edge or corner |
| Rename a note | Click its title |
| Text size | **⋯** → Text → Size, or Ctrl + mouse wheel over the tasks, or Ctrl + = / Ctrl + − (Ctrl + 0 resets) |
| Font | **⋯** → Text → Font, or **Customise look…** for a separate title font. 21 fonts come with the app: clean (Inter, Roboto, Open Sans, Poppins, Montserrat, Lato, Nunito, DM Sans), handwritten (Caveat, Shantell Sans, Kalam, Patrick Hand, Indie Flower, Shadows Into Light, Gochi Hand, Architects Daughter, Permanent Marker), classic (Merriweather, Lora, Playfair Display) and code (JetBrains Mono) |
| Colour, type, position, completed style | The **⋯** button in the note header (shown on hover) |
| Collapse a note | The chevron in the header |
| Hide a note | The **×** button. Click the tray icon to show it again |
| Recover something you deleted | Tray menu → **Recycle Bin…**, which lists **Deleted notes** and **Deleted tasks** |
| History, reminders, settings | Double-click the tray icon, or right-click it for the menu |

### Where notes sit on Windows

- **On desktop** (default): the note sits on the desktop layer. Other windows cover it, and **Win+D** / **Show desktop** reveals it instead of minimising it.
- **Always on top**: the note floats above every window.
- **Changing monitors**: each note remembers where it was for every monitor setup (laptop screen alone, docked to an external monitor, and so on). When you plug in or unplug a monitor, notes go back to where you left them in that setup. In a setup a note hasn't been in before, it stays on the same monitor if that monitor is still connected, otherwise it moves to the same spot on the main monitor.
- **Tidy grid**: notes never overlap. When you let go of a note after moving or resizing it, it slides onto an invisible grid on its monitor, with an even gap between neighbouring notes. If it lands on another note, it moves to the nearest free spot. If you drag an edge into a neighbour, that edge stops at the neighbour. New, reopened and expanded notes find a free spot the same way. Only when every monitor is full do notes overlap.

Change this for one note under **⋯** → Position, or for all notes under **Settings → Where notes live**.

### Start with Windows

Turn on **Settings → Start with Windows**. This adds an `AwesomeStickyNotes` entry under `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` that starts the app from `.venv`. If you move the app folder, start the app once from its new location and the entry is updated to match.

### Your data on Windows

Notes are stored in SQLite at **`StickyNotesDB\notes.db`** inside the app folder, in three tables: `notes`, `tasks` and `settings`. Every change is written immediately. A copy is saved to `notes.bak.db` each time the app starts, and if the main database is ever damaged, the app restores it from that copy. Items in the Recycle Bin stay in the database, marked with a `deleted_at` time, until the bin is emptied.

If the app folder isn't writable (for example under `Program Files`), the database goes to `%APPDATA%\AwesomeStickyNotes` instead.

The same folder holds a readable log of every task: **`notes-log.txt`** (plain text) and **`notes-log.xlsx`** (an Excel sheet with filters), listed oldest first by creation date with their status (Pending or Completed) and, once deleted, whether the task is in the Recycle Bin or deleted for good. They are rewritten about a second after each change, and rows are never removed; the history behind them is kept in `notes-log.json`. If the workbook is open in Excel, it catches up within 30 seconds of being closed.

To back up or move your notes, copy the `StickyNotesDB` folder while the app is closed. `StickyNotesDB/` is listed in `.gitignore`, so your notes never end up in the repository.

### Build a standalone .exe (optional)

```powershell
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --noconsole --onefile --name AwesomeStickyNotes AwesomeStickyNotes.pyw
```

The result is `dist\AwesomeStickyNotes.exe`. **Start with Windows** registers whichever copy of the app you turned it on from, so if you use the .exe, turn the setting on from the .exe.

---

## macOS edition

Everything in this half happens in the **`AwesomeStickyNotes-Mac`** folder.

> [!NOTE]
> The macOS edition was written and checked on Windows by running its macOS code paths there. It has not yet been run on a real Mac. These parts still need confirming on one: the desktop window level, the menu-bar-only mode, the Reduce Motion check, the LaunchAgent, and `setup.command` with the hand-over to `.venv`. Everything else is the same Qt code as the tested Windows app.

### Requirements

- macOS 13 (Ventura) or later, because PySide6 6.11 needs it
- Python 3.10 to 3.14, from the [python.org installer](https://www.python.org/downloads/macos/) or `brew install python`

### Install

1. Clone or download this repository.
2. Open the `AwesomeStickyNotes-Mac` folder and double-click **`setup.command`** in Finder, or run `bash setup.command` in Terminal from that folder.

`setup.command` builds the app's own Python environment in `.venv` using the newest Python 3.10–3.14 it finds. It installs the exact library versions in `requirements.txt`: PySide6 (Qt) and PyObjC's Cocoa bridge. Without PyObjC the app still runs, but notes behave like ordinary windows instead of sitting on the desktop layer, and the app shows a Dock icon.

The first time you open either `.command` file, you may need to do two things:

- If Finder says the file isn't executable (common after downloading a ZIP), run `chmod +x *.command` once in the folder.
- If macOS blocks the file as coming from an unidentified developer, right-click it, choose **Open**, then confirm **Open**. On macOS 15 and later, go to **System Settings → Privacy & Security** and click **Open Anyway** instead.

### Run

Double-click **`Start Awesome Sticky Notes.command`** in Finder, or run `python3 AwesomeStickyNotes.py` in Terminal (it hands over to `.venv`).

The app runs from the **menu bar**: look for the checklist icon at the top right. It has no Dock icon. Only one copy runs at a time. Starting it again brings your notes forward.

The app always runs from `.venv`, so installing or upgrading other Pythons or libraries can't break it. If the Python that `.venv` was built from is removed, the app says so when it starts; run `setup.command` again. Startup errors appear in an alert and are saved to `startup-error.log` in the app folder.

### Using it on macOS

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

### Where notes sit on macOS

- **On desktop** (default): notes stay just above the desktop. Apps cover them, **Show Desktop** (F11 or the spread-fingers gesture) reveals them, and they appear on every Space.
- **Always on top**: notes float above all windows.
- **Tidy grid**: notes never overlap. When you let go of a note after moving or resizing it, it slides onto an invisible grid on its monitor, with an even gap between neighbouring notes. If it lands on another note, it moves to the nearest free spot. If you drag an edge into a neighbour, that edge stops at the neighbour. New, reopened and expanded notes find a free spot the same way. Only when every monitor is full do notes overlap.

Change this for one note under **⋯** → Position, or for all notes under **Settings → Where notes live**.

### Open at login

Turn on **Settings → Open at login**. This adds a LaunchAgent at `~/Library/LaunchAgents/com.dee.awesomestickynotes.plist`, which runs the app from its folder with the Python in `.venv`. If you move the folder, start the app once from its new location and the LaunchAgent is updated to match.

### Your data on macOS

Notes are stored in SQLite at **`StickyNotesDB/notes.db`** inside the app folder, with a backup (`notes.bak.db`) made every time the app starts. Items in the Recycle Bin stay in the database, marked with a `deleted_at` time, until the bin is emptied. The folder also holds the same never-shrinking task log as on Windows: `notes-log.txt`, `notes-log.xlsx` (opens in Excel or Numbers) and `notes-log.json`.

If the folder isn't writable, the database goes to `~/Library/Application Support/AwesomeStickyNotes` instead. `StickyNotesDB/` is listed in `.gitignore`, so your notes never end up in the repository.

### Build a standalone .app (optional)

```bash
.venv/bin/python3 -m pip install pyinstaller
.venv/bin/pyinstaller --windowed --name "Awesome Sticky Notes" --osx-bundle-identifier com.dee.awesomestickynotes AwesomeStickyNotes.py
```

The app is created at `dist/Awesome Sticky Notes.app`. A packaged app keeps its notes in `~/Library/Application Support/AwesomeStickyNotes`, because writing inside an app bundle breaks its signature.

---

## Moving notes between Windows and Mac

Both editions use the same database format. Close the app on both computers, then copy `notes.db` from one `StickyNotesDB` folder to the other.

## Code layout

```
AwesomeStickyNotesDee/                 Windows edition
  AwesomeStickyNotes.pyw               entry point (hands over to .venv)
  setup.bat                            builds .venv from requirements.txt
  requirements.txt                     PySide6
AwesomeStickyNotes-Mac/                macOS edition
  AwesomeStickyNotes.py                entry point (hands over to .venv)
  Start Awesome Sticky Notes.command   Finder launcher
  setup.command                        builds .venv from requirements.txt
  requirements.txt                     PySide6 and PyObjC's Cocoa bridge

stickynotes/                           identical in both folders
  app.py         tray / menu-bar icon, note windows, single instance, day roll-over
  note.py        the desktop sticky note window
  screens.py     note positions remembered per monitor setup
  grid.py        snapping notes to a grid, keeping them from overlapping
  widgets.py     check circle, task row, menus, toggles, pills
  hub.py         notes overview, completed history, reminders, Recycle Bin, settings
  reminders.py   reminder scheduler and pop-up cards
  repeat.py      repeating reminders: every N minutes/hours, daily, weekly...
  store.py       SQLite data model and schema migrations
  notelog.py     plain-text and Excel log of every task
  timeparse.py   "@5pm"-style reminder parsing
  shadow.py      layered soft drop shadows
  icons.py       vector line icons
  theme.py       colours, card styles and fonts
  colorpicker.py the custom colour picker
  decor.py       paints a note's card: fill, paper, header band
  stylepanel.py  the Customise look window
  fonts/         bundled Google Fonts and their licences
  system.py      platform layer: picks winutil.py or macutil.py
  winutil.py     Windows: desktop pinning, always-on-top, Start with Windows
  macutil.py     macOS: desktop window level, menu-bar-only mode, Open at login
```

All platform differences live in `system.py`, `winutil.py` and `macutil.py`. When you change `stickynotes/` in one edition, copy it to the other so the two stay identical.
