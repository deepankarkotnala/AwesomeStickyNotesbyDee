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

Each folder is a complete copy of the app and has its own README. The `stickynotes/` package inside them is identical; only the launchers and `requirements.txt` differ. The Mac folder also builds **`Awesome Sticky Notes.app`**, delivered as `Awesome Sticky Notes.zip`.

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
| Light or dark | **Settings → Appearance → Theme**: **System** (follows your computer's light or dark mode as it changes), **Light** or **Dark**, for the app's windows, dialogs, the calendar and menus. Notes keep their own colours |
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

Everything in this half happens in the **`AwesomeStickyNotes-Mac`** folder. It has the same features as the Windows edition, and runs as an app you double-click: **Awesome Sticky Notes.app**.

> [!NOTE]
> The macOS edition was built and tested on Windows: the app's launcher was run under bash with stand-ins for the macOS tools, and the app's code was run from inside the built app with its macOS code paths switched on. It has not yet been run on a real Mac. These parts still need confirming on one: double-clicking the app and its first-run setup, including the security prompt; the desktop window level, the menu-bar-only mode and the Reduce Motion check; and the LaunchAgent for Open at login.

### Requirements

- macOS 13 (Ventura) or later, because PySide6 6.11 needs it
- Python 3.10 to 3.14, from the [python.org installer](https://www.python.org/downloads/macos/) or `brew install python`

### Install

1. Copy **`Awesome Sticky Notes.zip`** from the `AwesomeStickyNotes-Mac` folder to the Mac (AirDrop, USB stick, cloud drive or email). Copy the zip, not an unzipped folder: the zip keeps the app's launcher marked as a program, and a folder copied from Windows loses that, so macOS would refuse to open it.
2. Double-click the zip to unzip it, and drag **Awesome Sticky Notes** into **Applications**.
3. Double-click the app. It isn't signed with an Apple developer certificate, so the first time macOS blocks it. On macOS 13 or 14, right-click the app, choose **Open**, then click **Open**. On macOS 15 and later, open **System Settings → Privacy & Security** and click **Open Anyway**. You only do this once.

The first start sets the app up. It finds Python 3.10–3.14 from python.org or Homebrew (if there is none, it offers to open python.org). It then builds its own Python environment in `~/Library/Application Support/AwesomeStickyNotes/python`, with the exact library versions in `requirements.txt`: PySide6 (Qt) and PyObjC's Cocoa bridge. That needs the internet and takes a minute or two; a notification says it's under way. After that the app starts at once.

### Run

Double-click **Awesome Sticky Notes** in Applications, or open it from Launchpad or Spotlight.

The app runs from the **menu bar**: look for the checklist icon at the top right. It has no Dock icon. Only one copy runs at a time; opening it again brings your notes forward.

The app always runs in its own Python environment, so installing or upgrading other Pythons or libraries can't break it. A newer version of the app that needs different libraries sets them up again the first time it opens. If setup fails, the app says so and keeps a log in `~/Library/Logs/AwesomeStickyNotes`, along with any start-up errors.

### Using it on macOS

| Action | How |
|---|---|
| New note in another colour | Hover over a note, click **+** in its header, then click a colour |
| Colour strength | **⋯** → Colour → **Saturation** slider (double-click it to reset) |
| Any colour | **⋯** → Colour → the rainbow dot at the end of the colours. Pick by eye, type a code such as `#FFD1DC` (or `#FD1` for short), or reuse a recent colour. The note shows it while you pick |
| Card style | **⋯** → Style: **Flat** (a plain card), **Elevated** (flat, lifted by a soft shadow) or **3D** (glossy with a deeper shadow). **Settings → Appearance** sets the style for new notes and can apply it to every note |
| Corners | **Settings → Appearance → Corners**: Square, Soft, Round or Extra round, for every note |
| Light or dark | **Settings → Appearance → Theme**: **System** (follows your computer's light or dark mode as it changes), **Light** or **Dark**, for the app's windows, dialogs, the calendar and menus. Notes keep their own colours |
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

Turn on **Settings → Open at login**. This adds a LaunchAgent at `~/Library/LaunchAgents/com.dee.awesomestickynotes.plist` that opens the app by its bundle identifier when you log in, so it keeps working if you move the app.

### Your data on macOS

Notes are stored in SQLite at **`~/Library/Application Support/AwesomeStickyNotes/notes.db`**, with a backup (`notes.bak.db`) made every time the app starts, never inside the app itself. Replacing the app with a newer version keeps them. Items in the Recycle Bin stay in the database, marked with a `deleted_at` time, until the bin is emptied. The folder also holds the same never-shrinking task log as on Windows: `notes-log.txt`, `notes-log.xlsx` (opens in Excel or Numbers) and `notes-log.json`. **Settings → Data → Open folder** shows it in Finder.

### Build the app

After changing the code, copy `stickynotes/` from the Windows edition into `AwesomeStickyNotes-Mac`, then run:

```bash
python build-app.py
```

Any Python 3 works, on Windows or a Mac, with no extra libraries. It assembles the app from `AwesomeStickyNotes.py`, `requirements.txt`, `stickynotes/` and `packaging/` (the launcher script and the icon) and writes `Awesome Sticky Notes.zip`. On a Mac it also leaves `Awesome Sticky Notes.app` next to it.

To run from source on a Mac instead: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `python3 AwesomeStickyNotes.py` (it hands over to `.venv`; notes then live in `StickyNotesDB/` in the folder).

---

## Moving notes between Windows and Mac

Both editions use the same database format. Close the app on both computers, then copy `notes.db` between `StickyNotesDB\notes.db` in the Windows app folder and `~/Library/Application Support/AwesomeStickyNotes/notes.db` on the Mac.

## Code layout

```
AwesomeStickyNotesDee/                 Windows edition
  AwesomeStickyNotes.pyw               entry point (hands over to .venv)
  setup.bat                            builds .venv from requirements.txt
  requirements.txt                     PySide6
AwesomeStickyNotes-Mac/                macOS edition
  AwesomeStickyNotes.py                entry point (the app runs it with its own Python)
  requirements.txt                     PySide6 and PyObjC's Cocoa bridge
  packaging/launcher.sh                what double-clicking the app runs: sets up Python, then starts
  packaging/AppIcon.icns               the app icon
  build-app.py                         builds Awesome Sticky Notes.app, zipped
  Awesome Sticky Notes.zip             the built app, to copy to a Mac

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

All platform differences live in `system.py`, `winutil.py` and `macutil.py`. When you change `stickynotes/` in one edition, copy it to the other so the two stay identical, then run `build-app.py` in the Mac folder.
