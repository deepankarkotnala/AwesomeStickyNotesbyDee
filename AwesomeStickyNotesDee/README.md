# Awesome Sticky Notes

Desktop sticky notes for Windows: daily to-dos, checklists and reminders, on soft, shadowed cards that live on your desktop.

Developed by Deepankar Kotnala. A macOS edition lives in the sibling folder `AwesomeStickyNotes-Mac`.

## Run

1. Run **`setup.bat`** once. It builds the app's own Python environment in `.venv` (Python 3.14 plus the exact library versions in `requirements.txt`).
2. Double-click **`AwesomeStickyNotes.pyw`**.

The app always runs from `.venv`, whichever Python Windows uses to open the `.pyw`, so installing or upgrading other Pythons or libraries can't break it. **Start with Windows** launches it from `.venv` too. If Python 3.14 itself is ever uninstalled, the app says so on start; reinstall it and run `setup.bat` again.

For a console with error output, run `.venv\Scripts\python AwesomeStickyNotes.pyw`. Only one copy runs at a time. Launching it again just brings your notes forward.

## Using it

| Action | How |
|---|---|
| New note in another colour | Hover over a note, click **+** in its header, then click a colour |
| Colour strength | **⋯** → Colour → **Saturation** slider, from a faint tint to the full colour (double-click it to reset) |
| Add a task | Type in **Add a task** at the bottom of a note and press Enter |
| Add a reminder | End the task with `@5pm`, `@17:30`, `@tomorrow 9am`, `@fri 10am`, `@tonight`, `@30m`, `@2h`, or use the bell on a task |
| Complete a task | Click its circle |
| Edit a task | Double-click it. Clearing the text deletes the task (it goes to the Recycle Bin) |
| Pin a task to the top | Hover over it and click the **pin**. Pinned tasks stay in a **Pinned** section at the top of the note, above everything else. Click the pin again to unpin |
| Reorder tasks | Drag a task up or down (a grip appears on its left on hover). Works within its section, so pinned tasks are reordered among themselves and always stay above the rest. Completed tasks stay in the order you finished them |
| Move a note | Drag its header |
| Resize a note | Drag the dotted grip in the bottom-right corner |
| Rename a note | Click its title |
| Text size | **⋯** → Text → Size, or Ctrl + mouse wheel over the tasks, or Ctrl + = / Ctrl + − (Ctrl + 0 resets) |
| Font | **⋯** → Text → Font. **Use this font & size on all notes** copies it to every note |
| Colour, type, position, completed style | The **⋯** button in the note header (shown on hover). The colour row stays open so you can try several |
| Collapse a note | The chevron in the header |
| Hide a note | The **×** button. Click the tray icon to show it again |
| Recover something you deleted | Tray menu → **Recycle Bin…**. It has two sections, **Deleted notes** and **Deleted tasks**. Restore an item, delete it forever, or **Empty bin** |
| History, reminders, Recycle Bin, settings | Double-click the tray icon, or right-click it for the menu |

### Daily to-do notes vs checklists
- **Daily to-do**: unfinished tasks from earlier days stay on the note under **Carried over**, with a "Since Tue" badge. Tasks you finish today are either struck through until midnight or hidden straight away (your choice). Older finished tasks leave the note but stay in **Completed** history.
- **Checklist**: a plain list. Checked items stay struck through until you choose **Clear completed**.

### Where notes sit
- **On desktop** (default): the note sits on the desktop layer. Other windows cover it, and **Win+D / Show desktop** reveals it instead of minimising it.
- **Always on top**: the note floats above every window.

### Recycle Bin
Deleting a note, or a task with its **×** button, moves it to the Recycle Bin instead of erasing it. Items stay there until you restore them or empty the bin.
- **Restoring a note** puts it back on the desktop with all of its tasks.
- **Restoring a task** puts it back in its old place on its note.
- Tasks you deleted on their own before deleting their note stay in **Deleted tasks** after the note is restored.
- **Delete forever** and **Empty bin** can't be undone.

### Reminders
When a reminder is due, a card slides in at the bottom-right with **Mark done** and **Snooze**. Reminders that came due while the app was closed show up the next time it starts.

## Data

Everything is stored locally in SQLite in the **`StickyNotesDB`** folder next to the app (`StickyNotesDB\notes.db`), which has three tables: `notes`, `tasks` and `settings`. Each change is written immediately. Items in the Recycle Bin stay in the database, marked with a `deleted_at` time, until the bin is emptied. A copy is saved to `notes.bak.db` every time the app starts, and if the main database is ever damaged, the app restores from that copy. To back up or move your notes, copy that folder while the app is closed.

The same folder holds a readable log of every task: **`notes-log.txt`** (plain text) and **`notes-log.xlsx`** (an Excel sheet with filters). Both list tasks oldest first by creation date, with their status (Pending or Completed) and, once deleted, whether the task is in the Recycle Bin or deleted for good. They are rewritten about a second after each change, and rows are never removed, even after a task is deleted for good: the history behind them is kept in `notes-log.json`. If the workbook is open in Excel when something changes, it catches up within 30 seconds of being closed. The app never reads these files back, so editing them changes nothing.

If the app folder isn't writable (for example under `Program Files`), the database goes to `%APPDATA%\AwesomeStickyNotes` instead. The first versions kept it in `%APPDATA%\StickyNotesDee`; if a database is still there, the app moves it into `StickyNotesDB` on start and leaves the old file renamed to `notes.moved-to-app-folder.db` as a safety copy.

`StickyNotesDB/` is listed in `.gitignore`, so your notes stay out of version control.

## Build a standalone .exe (optional)

```powershell
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --noconsole --onefile --name AwesomeStickyNotes AwesomeStickyNotes.pyw
```

The result is `dist\AwesomeStickyNotes.exe`. **Start with Windows** registers whichever version you launched it from, so turn that setting on from the .exe if you use one.

## Project layout

```
AwesomeStickyNotes.pyw  entry point (hands over to .venv)
setup.bat               builds .venv from requirements.txt
stickynotes/
  app.py               tray icon, note windows, single instance, day roll-over
  note.py              the desktop sticky note window
  widgets.py           check circle, task row, menus, toggles, pills
  hub.py               notes overview, completed history, reminders, Recycle Bin, settings
  reminders.py         reminder scheduler and toast pop-ups
  store.py             SQLite data model
  notelog.py           plain-text and Excel log of every task
  timeparse.py         "@5pm"-style reminder parsing
  shadow.py            layered soft drop shadows
  icons.py             vector line icons
  theme.py             colours and fonts
  system.py            platform layer (picks winutil or macutil)
  winutil.py           Windows: desktop pinning, always-on-top, autostart
  macutil.py           macOS: desktop window level, menu-bar mode, login item
```
