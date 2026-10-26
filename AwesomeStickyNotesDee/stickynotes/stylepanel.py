"""The "Customise look" window: every part of a note's look in one place, for one note or several at once.

Each change applies straight away to all the notes the panel was opened for (see Controller.restyle).
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget, QWidgetAction)

from . import decor, icons, theme
from .colorpicker import pick_color
from .store import Note
from .widgets import (DIALOG_QSS, ComboBox, CustomSwatch, PillButton, SaturationSlider, Segmented, Swatch,
                      check_shape, make_menu)

RING = QColor("#3A3A3C")
SUB = QColor(60, 60, 67, 150)

PANEL_QSS = DIALOG_QSS + f"""
    QWidget#panel {{ background: #FFFFFF; }}
    QScrollArea, QWidget#content {{ background: transparent; border: none; }}
    QFrame#rule {{ background: rgba(0, 0, 0, 16); border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px 0; }}
    QScrollBar::handle:vertical {{ background: rgba(0, 0, 0, 40); border-radius: 4px; min-height: 30px; margin: 0 2px; }}
    QScrollBar::handle:vertical:hover {{ background: rgba(0, 0, 0, 70); }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QPushButton#emoji {{ background: #F2F2F7; border: none; border-radius: 8px; padding: 4px 12px;
                         color: {theme.HUB_TEXT}; }}
    QPushButton#emoji:hover {{ background: #E5E5EA; }}
"""


def _label(text: str, pt: float = 10, weight=QFont.Weight.Normal, color: QColor | str = theme.HUB_TEXT) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(theme.font(pt, weight))
    lbl.setStyleSheet(f"color: {theme.rgba(color)};")
    return lbl


class LookPreview(QWidget):
    """A small note drawn with the look being edited."""

    def __init__(self, panel: "StylePanel"):
        super().__init__()
        self.panel = panel
        self.setFixedSize(236, 178)

    def paintEvent(self, e):
        note = self.panel.notes[0]
        pal = theme.note_palette(note)
        head = theme.header_palette(pal, note.header)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(10, 6, self.width() - 20, self.height() - 18)
        radius = min(3.0, self.panel.radius) if note.style == "paper" else self.panel.radius * 0.8
        if note.style != "flat":   # a hint of the shadow
            for spread, alpha in ((6, 10), (3, 16)):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 0, 0, alpha))
                p.drawRoundedRect(r.adjusted(-spread / 3, spread / 2, spread / 3, spread), radius + 2, radius + 2)
        title_bottom = r.top() + 40
        decor.paint_card(p, r, note, pal, radius, 0.0, title_bottom, scale=0.85)

        title = theme.title_font(note.title_font)
        title.setPointSizeF(title.pointSizeF() * 0.82)
        p.setFont(title)
        p.setPen(head.text)
        name = note.title if len(self.panel.notes) == 1 else "Your note"
        p.drawText(QRectF(r.left() + 12, r.top() + 8, r.width() - 24, 26), Qt.AlignmentFlag.AlignVCenter,
                   f"{note.emoji}  {name}" if note.emoji else name)

        body = theme.note_font(note.font_family, min(note.font_size, 12.0) * 0.92)
        p.setFont(body)
        step = {"compact": 21, "normal": 25, "roomy": 31}.get(note.spacing, 25)
        for i, (text, done) in enumerate((("Call Sam about the quote", False), ("Buy milk", True),
                                          ("Book the dentist", False))):
            y = title_bottom + 10 + i * step
            box = QRectF(r.left() + 13, y + 2, 13, 13)
            path = check_shape(note.checkbox, box)
            if done:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(pal.accent))
                p.drawPath(path)
                mark = box.adjusted(3.4, 2.4, -3.4, -4.2) if note.checkbox == "heart" else box.adjusted(2.8, 3, -2.8, -2.6)
                icons.paint(p, "check", mark, "#FFFFFF", 3.2)
            else:
                p.setPen(QPen(pal.faint, 1.4))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
            p.setPen(pal.ink(0.38) if done else pal.text)
            line = QRectF(r.left() + 34, y, r.width() - 46, 18)
            p.drawText(line, Qt.AlignmentFlag.AlignVCenter, text)
            if done and note.done_look != "fade":
                width = p.fontMetrics().horizontalAdvance(text)
                p.setPen(QPen(pal.ink(0.38), 1.2))
                y_mid = line.center().y() + 1
                p.drawLine(QPointF(line.left(), y_mid), QPointF(line.left() + width, y_mid))


class StylePanel(QWidget):
    def __init__(self, ctl, notes: list[Note]):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.ctl, self.notes = ctl, notes
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(PANEL_QSS)
        first = notes[0]
        self.setWindowTitle(f"Customise “{first.title}”" if len(notes) == 1 else f"Customise {len(notes)} notes")
        self.setWindowIcon(ctl.icon)
        self.radius = float(ctl.store.settings.radius)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        top = QHBoxLayout()
        top.setContentsMargins(22, 18, 22, 10)
        top.setSpacing(16)
        heading = QVBoxLayout()
        heading.setSpacing(4)
        heading.addWidget(_label("Customise look", 15, QFont.Weight.DemiBold))
        what = f"“{first.title}”" if len(notes) == 1 else f"{len(notes)} notes"
        sub = _label(f"Changes apply to {what} as you make them.", 9.5, color=SUB)
        sub.setWordWrap(True)
        heading.addWidget(sub)
        heading.addStretch(1)
        top.addLayout(heading, 1)
        self.preview = LookPreview(self)
        top.addWidget(self.preview)
        root.addLayout(top)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("content")
        self.form = QGridLayout(content)
        self.form.setContentsMargins(22, 4, 22, 16)
        self.form.setHorizontalSpacing(16)
        self.form.setVerticalSpacing(10)
        self.form.setColumnStretch(1, 1)
        area.setWidget(content)
        root.addWidget(area, 1)
        self._build(first)

        rule = QFrame()
        rule.setObjectName("rule")
        rule.setFixedHeight(1)
        root.addWidget(rule)
        foot = QHBoxLayout()
        foot.setContentsMargins(22, 12, 22, 14)
        foot.setSpacing(8)
        copy = PillButton("Copy style", theme.HUB_ACCENT)
        copy.setToolTip("Copy this look, then click “Paste style” on any note")
        copy.clicked.connect(lambda: (self.ctl.copy_style(self.notes[0]), self.close()))
        paste = PillButton("Paste style", theme.HUB_ACCENT)
        paste.setEnabled(ctl.copied_style is not None)
        paste.setToolTip("Give these notes the look you copied")
        paste.clicked.connect(self._paste)
        everyone = PillButton("Apply to all notes", theme.HUB_ACCENT)
        everyone.setToolTip("Give every note this look")
        everyone.clicked.connect(lambda: self.ctl.apply_to_all(self.notes[0]))
        done = PillButton("Done", theme.HUB_ACCENT, primary=True)
        done.clicked.connect(self.close)
        for b in (copy, paste, everyone):
            foot.addWidget(b)
        foot.addStretch(1)
        foot.addWidget(done)
        root.addLayout(foot)
        self.resize(600, 820)

    # ------------------------------------------------------------------ building blocks
    def _section(self, title: str) -> None:
        row = self.form.rowCount()
        lbl = _label(title.upper(), 8, QFont.Weight.Bold, SUB)
        f = lbl.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.7)
        lbl.setFont(f)
        lbl.setContentsMargins(0, 12 if row else 2, 0, 0)
        self.form.addWidget(lbl, row, 0, 1, 2)

    def _row(self, title: str, control: QWidget | QHBoxLayout) -> QWidget:
        row = self.form.rowCount()
        name = _label(title, 10)
        self.form.addWidget(name, row, 0, Qt.AlignmentFlag.AlignVCenter)
        if isinstance(control, QHBoxLayout):
            holder = QWidget()
            control.setContentsMargins(0, 0, 0, 0)
            holder.setLayout(control)
            control = holder
        self.form.addWidget(control, row, 1)
        return control

    def _segments(self, title: str, options, current: str, field: str) -> Segmented:
        seg = Segmented([(key, label) for key, label, *_ in options], current)
        seg.changed.connect(lambda key: self._set(**{field: key}))
        box = QHBoxLayout()
        box.addWidget(seg)
        box.addStretch(1)
        self._row(title, box)
        return seg

    def _swatches(self, current: str, on_pick, on_custom, extra: list[QWidget] = ()) -> QWidget:
        holder = QWidget()
        grid = QVBoxLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)
        dots = list(extra)
        swatches = [Swatch(pal, pal.key == current, RING) for pal in theme.PALETTES.values()]
        custom = CustomSwatch(current, RING)

        def pick(key: str) -> None:
            for sw in swatches:
                sw.selected = sw.pal.key == key
                sw.update()
            custom.selected = False
            custom.update()
            on_pick(key)

        for sw in swatches:
            sw.clicked.connect(lambda _=False, k=sw.pal.key: pick(k))
        custom.clicked.connect(on_custom)
        dots += swatches + [custom]
        for start in range(0, len(dots), 9):
            row = QHBoxLayout()
            row.setSpacing(2)
            for dot in dots[start:start + 9]:
                row.addWidget(dot)
            row.addStretch(1)
            grid.addLayout(row)
        return holder

    def _font_combo(self, current: str, field: str, system_label: str) -> ComboBox:
        combo = ComboBox()
        combo.setFont(theme.font(10.5))
        group = None
        for family, label, kind in theme.available_fonts(current):
            if kind and kind != group:
                if group is not None:
                    combo.insertSeparator(combo.count())
                group = kind
            combo.addItem(system_label if not family else label, family)
            combo.setItemData(combo.count() - 1, theme.note_font(family, 10.5), Qt.ItemDataRole.FontRole)
        combo.setCurrentIndex(max(0, combo.findData(current)))
        combo.setMaxVisibleItems(18)
        combo.currentIndexChanged.connect(lambda _: self._set(**{field: combo.currentData()}))
        return combo

    # ------------------------------------------------------------------ the form
    def _build(self, n: Note) -> None:
        self._section("Colour")
        self.saturation = SaturationSlider(n.color, n.saturation, False)
        self._row("Colour", self._swatches(n.color, self._pick_color, self._custom_color))
        self.saturation.moved.connect(self._preview_saturation)
        self.saturation.committed.connect(lambda v: self._set(saturation=v))
        self._row("Strength", self.saturation)

        self._section("Card")
        self._segments("Style", theme.STYLES, n.style, "style")
        self._segments("Paper", theme.BACKGROUNDS, n.background, "background")
        auto = PillButton("Auto", theme.HUB_ACCENT, small=True)
        auto.setToolTip("A deeper shade of the note's own colour")
        auto.clicked.connect(lambda: self._set(color2=""))
        self.gradient_row = self._row("Gradient to", self._swatches(
            n.color2, lambda key: self._set(color2=key), lambda: self._custom_into("color2"), [auto]))
        self.gradient_row.setEnabled(n.background == "gradient")

        self._section("Title")
        self._segments("Header", theme.HEADERS, n.header, "header")
        self.emoji_btn = QPushButton()
        self.emoji_btn.setObjectName("emoji")
        self.emoji_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.emoji_btn.clicked.connect(self._emoji_menu)
        self._show_emoji(n.emoji)
        box = QHBoxLayout()
        box.addWidget(self.emoji_btn)
        box.addStretch(1)
        self._row("Emoji", box)
        self._row("Title font", self._font_combo(n.title_font, "title_font", "System font (Segoe UI)"))

        self._section("Text")
        self._row("Font", self._font_combo(n.font_family, "font_family", "System font (Segoe UI)"))
        self.size_label = _label(f"{n.font_size:g} pt", 10.5, QFont.Weight.DemiBold)
        self.size_label.setMinimumWidth(52)
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box = QHBoxLayout()
        box.setSpacing(4)
        for text, delta in (("−", -1), ("+", 1)):
            b = QPushButton(text)
            b.setObjectName("step")
            b.setFixedSize(32, 30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(theme.font(11, QFont.Weight.DemiBold))
            b.clicked.connect(lambda _=False, d=delta: self._step_size(d))
            box.addWidget(b)
            if delta < 0:
                box.addWidget(self.size_label)
        box.addStretch(1)
        self._row("Size", box)
        auto = PillButton("Auto", theme.HUB_ACCENT, small=True)
        auto.setToolTip("Dark or light text, whichever reads best on the colour")
        auto.clicked.connect(lambda: self._set(text_color=""))
        inks = QHBoxLayout()
        inks.setSpacing(2)
        inks.addWidget(auto)
        for code, name in theme.INKS:
            sw = Swatch(theme.Palette(code, name, code, code, code), n.text_color.upper() == code, RING)
            sw.clicked.connect(lambda _=False, c=code: self._set(text_color=c))
            inks.addWidget(sw)
        custom = CustomSwatch(n.text_color if n.text_color not in dict(theme.INKS) else "", RING)
        custom.setToolTip("Any text colour…")
        custom.clicked.connect(lambda: self._custom_into("text_color"))
        inks.addWidget(custom)
        inks.addStretch(1)
        self._row("Colour", inks)
        self._segments("Spacing", theme.SPACINGS, n.spacing, "spacing")

        self._section("Tasks")
        self._segments("Checkboxes", theme.CHECKBOXES, n.checkbox, "checkbox")
        self._segments("Done tasks", theme.DONE_LOOKS, n.done_look, "done_look")

    # ------------------------------------------------------------------ changes
    def _set(self, **changes) -> None:
        self.ctl.restyle(self.notes, **changes)
        if "background" in changes:
            self.gradient_row.setEnabled(changes["background"] == "gradient")
        self.preview.update()

    def _windows(self):
        return [w for w in (self.ctl.windows.get(n.id) for n in self.notes) if w is not None]

    def _pick_color(self, key: str) -> None:
        self.saturation.set_key(key)
        self._set(color=key)

    def _preview_saturation(self, value: float) -> None:
        for n in self.notes:
            n.saturation = value          # saved when the slider is let go
        for w in self._windows():
            w._preview_saturation(value)
        self.preview.update()

    def _custom_color(self) -> None:
        first = self.notes[0]
        picked = pick_color(self, QColor(theme.note_palette(first).bg), self.ctl.recent_colors(),
                            lambda code: [w.apply_theme(theme.palette(code)) for w in self._windows()])
        if picked:
            self.ctl.remember_color(picked)
            self.saturation.set_key(picked)
            self._set(color=picked, saturation=0.5)
        else:
            for w in self._windows():
                w.apply_theme()

    def _custom_into(self, field: str) -> None:
        """Any colour for a gradient's far end or for the text."""
        current = getattr(self.notes[0], field) or ("#1C1C1E" if field == "text_color" else self.notes[0].color)
        start = QColor(current) if theme.is_custom(current) else QColor(theme.palette(current).bg)
        picked = pick_color(self, start, self.ctl.recent_colors())
        if picked:
            self.ctl.remember_color(picked)
            self._set(**{field: picked})

    def _step_size(self, delta: int) -> None:
        low, high = theme.FONT_SIZES
        size = min(high, max(low, self.notes[0].font_size + delta))
        self.size_label.setText(f"{size:g} pt")
        self._set(font_size=size)

    def _show_emoji(self, emoji: str) -> None:
        self.emoji_btn.setText(emoji or "None")
        self.emoji_btn.setFont(theme.font(14 if emoji else 10))

    def _emoji_menu(self) -> None:
        menu = make_menu(self)
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)
        grid = QGridLayout()
        grid.setSpacing(2)

        def pick(emoji: str) -> None:
            menu.close()
            self._show_emoji(emoji)
            self._set(emoji=emoji)

        for i, emoji in enumerate(theme.EMOJIS):
            b = QPushButton(emoji)
            b.setFixedSize(QSize(34, 34))
            b.setFont(theme.font(14))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 8px; }"
                            "QPushButton:hover { background: rgba(0, 0, 0, 14); }")
            b.clicked.connect(lambda _=False, e=emoji: pick(e))
            grid.addWidget(b, i // 8, i % 8)
        lay.addLayout(grid)
        own = QLineEdit()
        own.setPlaceholderText("Or type any emoji (Win + .) and press Enter")
        own.setFont(theme.font(9.5))
        own.setStyleSheet("QLineEdit { background: #F2F2F7; border: none; border-radius: 7px; padding: 6px 8px; }")
        own.setMaxLength(8)
        own.returnPressed.connect(lambda: pick(own.text().strip()))
        lay.addWidget(own)
        clear = PillButton("No emoji", theme.HUB_ACCENT, small=True)
        clear.clicked.connect(lambda: pick(""))
        row = QHBoxLayout()
        row.addWidget(clear)
        row.addStretch(1)
        lay.addLayout(row)
        action = QWidgetAction(menu)
        action.setDefaultWidget(holder)
        menu.addAction(action)
        menu.exec(self.emoji_btn.mapToGlobal(self.emoji_btn.rect().bottomLeft()))

    def _paste(self) -> None:
        self.ctl.paste_style(self.notes)
        notes = self.notes
        self.close()
        self.ctl.customise(notes)   # reopen, showing the pasted look
