"""Application controller: tray icon, note windows, single instance, day roll-over."""
from __future__ import annotations

import getpass
import sys
from datetime import date

from PySide6.QtCore import QObject, QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from . import APP_NAME, SLUG, screens, system, theme
from .hub import HubWindow
from .note import MARGINS, NoteWindow
from .notelog import NotesLog
from .reminders import ReminderService
from .store import Note, Store
from .widgets import add_action, make_menu

SERVER_NAME = f"{SLUG}-{getpass.getuser()}"
NEW_NOTE_COLORS = ("lemon", "mint", "sky", "peach", "lavender", "rose")


def app_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFD54A"))
        p.drawRoundedRect(QRectF(s * 0.06, s * 0.06, s * 0.88, s * 0.88), s * 0.22, s * 0.22)
        pen = QPen(QColor("#5C4300"), max(1.3, s * 0.085))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([QPoint(round(s * 0.25), round(s * 0.37)), QPoint(round(s * 0.32), round(s * 0.44)),
                        QPoint(round(s * 0.45), round(s * 0.29))])
        p.drawLine(QPoint(round(s * 0.55), round(s * 0.37)), QPoint(round(s * 0.75), round(s * 0.37)))
        p.drawLine(QPoint(round(s * 0.27), round(s * 0.57)), QPoint(round(s * 0.75), round(s * 0.57)))
        p.drawLine(QPoint(round(s * 0.27), round(s * 0.75)), QPoint(round(s * 0.60), round(s * 0.75)))
        p.end()
        icon.addPixmap(pm)
    return icon


def tray_icon(icon: QIcon) -> QIcon:
    """macOS menu-bar icons are monochrome templates that adapt to light/dark menu bars."""
    if not system.IS_MAC:
        return icon
    template = QIcon()
    for s in (16, 18, 22, 32, 36, 44):
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0, 0, 0), max(1.2, s * 0.08))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawRoundedRect(QRectF(s * 0.14, s * 0.14, s * 0.72, s * 0.72), s * 0.16, s * 0.16)
        p.drawPolyline([QPoint(round(s * 0.3), round(s * 0.5)), QPoint(round(s * 0.44), round(s * 0.63)),
                        QPoint(round(s * 0.7), round(s * 0.36))])
        p.end()
        template.addPixmap(pm)
    template.setIsMask(True)
    return template


class Controller(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.icon = app_icon()
        app.setWindowIcon(self.icon)
        self.store = Store()
        self.log = NotesLog(self.store)
        self.windows: dict[str, NoteWindow] = {}
        self.hub: HubWindow | None = None
        self._today = date.today()
        self._desktop = system.shell_token()
        self._hide_tip_shown = False
        self.layout_key = screens.current_key()   # the monitor arrangement note positions are saved under
        self.settling = False                     # monitors are changing: positions aren't the user's doing

        self._build_tray()
        self.reminders = ReminderService(self)
        self.store.notes_changed.connect(self.sync_windows)
        self.sync_windows()

        self._clock = QTimer(self, interval=30_000)        # day roll-over
        self._clock.timeout.connect(self._tick)
        self._clock.start()
        self._shell = QTimer(self, interval=3_000)         # Explorer restarts
        self._shell.timeout.connect(self._check_shell)
        self._shell.start()

        # Monitor plugged in or out, resolution or scaling changed: wait for Windows to finish moving
        # windows around, then put every note where it belongs for the new arrangement.
        self._relayout = QTimer(self, singleShot=True, interval=1500)
        self._relayout.timeout.connect(self._apply_layout)
        app.screenAdded.connect(self._watch_screen)
        app.screenRemoved.connect(self._screens_changed)
        app.primaryScreenChanged.connect(self._screens_changed)
        for screen in app.screens():
            self._watch_screen(screen, changed=False)

        if self.store.settings.autostart:
            try:
                system.set_autostart(True)  # keep the launch path current if the folder moved
            except OSError:
                pass

    # ------------------------------------------------------------------ tray
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(tray_icon(self.icon), self)
        self.tray.setToolTip(APP_NAME)
        menu = self.tray_menu = make_menu()
        add_action(menu, "New daily note", lambda: self.new_note("daily"), icon="plus")
        add_action(menu, "New checklist", lambda: self.new_note("checklist"), icon="note")
        menu.addSeparator()
        add_action(menu, "Show all notes", self.show_all, icon="eye")
        add_action(menu, "Bring notes to front", self.bring_to_front, icon="pin")
        menu.addSeparator()
        add_action(menu, "All notes…", lambda: self.open_hub("notes"), icon="note")
        add_action(menu, "Completed history…", lambda: self.open_hub("completed"), icon="clock")
        add_action(menu, "Reminders…", lambda: self.open_hub("reminders"), icon="bell")
        add_action(menu, "Recycle Bin…", lambda: self.open_hub("bin"), icon="trash")
        add_action(menu, "Settings…", lambda: self.open_hub("settings"), icon="gear")
        menu.addSeparator()
        add_action(menu, "Quit", self.quit, icon="x")
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_all()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_hub("notes")

    # ------------------------------------------------------------------ windows
    def sync_windows(self) -> None:
        visible = {n.id: n for n in self.store.notes if n.visible}
        for note_id in list(self.windows):
            if note_id not in visible:
                window = self.windows.pop(note_id)
                window.hide()
                window.deleteLater()
        for note_id, note in visible.items():
            if note_id not in self.windows:
                window = self.windows[note_id] = NoteWindow(self, note)
                window.show()

    def recreate_windows(self) -> None:
        for window in self.windows.values():
            window.hide()
            window.deleteLater()
        self.windows.clear()
        self.sync_windows()

    def cards(self, exclude: NoteWindow | None = None) -> list[QRect]:
        """Where the cards of the open notes are (or are sliding to), so a note can keep clear of them."""
        return [w.card_target() for w in self.windows.values() if w is not exclude and w.isVisible()]

    def default_position(self, size: QSize) -> QPoint:
        area = QGuiApplication.primaryScreen().availableGeometry()
        step = 36 * len(self.windows)
        return QPoint(area.right() - size.width() - 12 - step, area.top() + 12 + step)

    def new_note(self, kind: str = "daily", near: NoteWindow | None = None, color: str | None = None) -> None:
        used = [n.color for n in self.store.notes]
        props: dict = {"color": color or min(NEW_NOTE_COLORS, key=used.count)}
        if near is not None:
            props.update(font_family=near.note.font_family, font_size=near.note.font_size,
                         saturation=near.note.saturation)
            g = near.geometry()
            overlap = MARGINS.left() + MARGINS.right() - 8   # let the shadows overlap
            x = g.x() - g.width() + overlap
            area = near.screen().availableGeometry()
            if x < area.left():
                x = g.x() + 36
            props.update(x=x, y=g.y() + (0 if x < g.x() else 36), w=g.width(), h=g.height())
        note = self.store.add_note(kind, **props)
        QTimer.singleShot(60, self, lambda: self.windows.get(note.id) and self.windows[note.id].focus_input())

    def hide_note(self, note: Note) -> None:
        self.store.set_note_visible(note, False)
        if not self._hide_tip_shown:
            self._hide_tip_shown = True
            self.tray.showMessage("Note hidden", f"Click the {system.TRAY} to show your notes again.", self.icon, 4000)

    def focus_note(self, note_id: str) -> None:
        note = self.store.note(note_id)
        if note is None:
            return
        system.activate_app()
        if not note.visible:
            self.store.set_note_visible(note, True)
        QTimer.singleShot(30, self, lambda: self.windows.get(note_id) and self.windows[note_id].focus_input())

    def show_all(self) -> None:
        hidden = [n for n in self.store.notes if not n.visible]
        for note in hidden:
            self.store.update_note(note, emit=False, visible=True)
        if hidden:
            self.store.notes_changed.emit()
        self.bring_to_front()

    def bring_to_front(self) -> None:
        system.activate_app()
        for window in self.windows.values():
            window.show()
            window.raise_()
        if self.windows:
            next(iter(self.windows.values())).activateWindow()

    def open_hub(self, page: str = "notes") -> None:
        system.activate_app()
        if self.hub is None:
            self.hub = HubWindow(self)
        self.hub.show_page(page)
        self.hub.showNormal()
        self.hub.raise_()
        self.hub.activateWindow()

    # ------------------------------------------------------------------ settings
    def set_autostart(self, enabled: bool) -> None:
        try:
            system.set_autostart(enabled)
        except OSError as exc:
            QMessageBox.warning(self.hub, system.AUTOSTART_LABEL, f"Couldn't update the startup setting:\n{exc}")
            return
        self.store.update_settings(autostart=enabled)

    def set_pin_all(self, mode: str) -> None:
        self.store.update_settings(pin=mode)
        for note in self.store.notes:
            self.store.update_note(note, emit=False, pin=mode)
        for window in self.windows.values():
            window.apply_pin()

    def apply_font_all(self, family: str, size: float) -> None:
        for note in self.store.notes:
            self.store.update_note(note, font_family=family, font_size=size)

    def set_completed_all(self, mode: str) -> None:
        self.store.update_settings(completed=mode)
        for note in self.store.notes:
            self.store.update_note(note, completed=mode)

    # ------------------------------------------------------------------ timers
    def _tick(self) -> None:
        if date.today() != self._today:
            self._today = date.today()
            for window in self.windows.values():
                window.rebuild()
            if self.hub and self.hub.isVisible():
                self.hub.refresh()

    def _check_shell(self) -> None:
        # Desktop-pinned notes are owned by Explorer's desktop window; if Explorer restarts they must be rebuilt.
        current = system.shell_token()
        if current and current != self._desktop:
            self._desktop = current
            self.recreate_windows()

    # ------------------------------------------------------------------ monitors
    def _watch_screen(self, screen, changed: bool = True) -> None:
        screen.geometryChanged.connect(self._screens_changed)
        if changed:
            self._screens_changed()

    def _screens_changed(self, *_) -> None:
        self.settling = True
        self._relayout.start()

    def _apply_layout(self) -> None:
        self.layout_key = screens.current_key()
        self._fit_all()
        QTimer.singleShot(1000, self, self._settled)

    def _settled(self) -> None:
        if self._relayout.isActive():   # the monitors changed again meanwhile
            return
        # Windows sometimes moves windows once more shortly after a display change; undo that too.
        self._fit_all()
        self.settling = False

    def _fit_all(self) -> None:
        """Put every note where it belongs for the monitors connected now, one after another so each
        keeps clear of those already placed."""
        placed: list[QRect] = []
        for window in self.windows.values():
            placed.append(window.fit_to_screens(placed))

    def quit(self) -> None:
        for window in self.windows.values():
            window._save_geometry()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    system.configure_app(app)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(theme.font(9.5))
    app.setStyleSheet(theme.tooltip_qss())

    # Single instance: if already running, ask that copy to show its notes and exit.
    probe = QLocalSocket()
    probe.connectToServer(SERVER_NAME)
    if probe.waitForConnected(400):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(400)
        probe.disconnectFromServer()
        return 0
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)

    controller = Controller(app)

    def on_connection():
        while server.hasPendingConnections():
            server.nextPendingConnection().deleteLater()
        controller.show_all()

    server.newConnection.connect(on_connection)
    code = app.exec()
    controller.log.flush()
    controller.store.close()
    return code
