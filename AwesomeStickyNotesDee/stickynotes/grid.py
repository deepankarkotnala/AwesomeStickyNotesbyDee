"""Keeps the notes tidy: every card sits on a grid laid over the screen it is on, and no two cards overlap.

The grid covers the screen's work area (the taskbar left out) with a line every STEP px, centred so the
margins on opposite sides match. A card starts on a grid line and ends GAP px before one, so cards in
neighbouring cells line up with an even gap between them.

The note the user has just moved, resized, expanded or opened is the one that makes room: it goes to the
nearest free spot that fits it, and the other notes stay where they are. After a resize the dragged edges
give way instead, so the note stops growing where it meets a neighbour. Only when every screen is full
does a note overlap others, at the nearby spot where it covers them least.

When the user lets go of a note, edges that end up within MAGNET cells of another note's edge (or of the
screen margin) are pulled into line with it, if the note still fits there, so neighbours form neat rows
and columns.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QGuiApplication

STEP = 20      # px between grid lines
GAP = 12       # px kept clear between cards, and between a card and the edge of the screen
MAGNET = 2     # cells: an edge this close to another note's edge lines up with it
MAX_TRIES = 20_000   # edge positions tried after a resize before falling back to moving the note

Span = tuple[int, int, int, int]      # first column, first row, columns, rows


def _nearest_line(offset: int) -> int:
    """offset / STEP rounded to the nearest whole number (halves round up)."""
    return (2 * offset + STEP) // (2 * STEP)


def _cells(length: int) -> int:
    """How many cells a card this long needs, its gap included."""
    return -(-(length + GAP) // STEP)


def _between(a: int, b: int) -> range:
    return range(a, b + 1) if a <= b else range(a, b - 1, -1)


class Grid:
    """The grid laid over one screen's work area."""

    def __init__(self, area: QRect):
        self.area = area
        self.cols = max(1, (area.width() - GAP) // STEP)
        self.rows = max(1, (area.height() - GAP) // STEP)
        self.x0 = area.x() + GAP + (area.width() - GAP - self.cols * STEP) // 2
        self.y0 = area.y() + GAP + (area.height() - GAP - self.rows * STEP) // 2

    def rect(self, span: Span) -> QRect:
        col, row, cols, rows = span
        return QRect(self.x0 + col * STEP, self.y0 + row * STEP, cols * STEP - GAP, rows * STEP - GAP)

    def snap(self, card: QRect, min_card: QSize, fixed_height: bool) -> Span:
        """The cells nearest to `card`: each edge goes to its closest grid line, then the span is kept
        on the grid. A `fixed_height` card (a collapsed note) keeps its height and only moves."""
        col = _nearest_line(card.x() - self.x0)
        cols = max(_nearest_line(card.x() + card.width() + GAP - self.x0) - col, _cells(min_card.width()))
        row = _nearest_line(card.y() - self.y0)
        if fixed_height:
            rows = _cells(card.height())
        else:
            rows = max(_nearest_line(card.y() + card.height() + GAP - self.y0) - row, _cells(min_card.height()))
        cols, rows = min(cols, self.cols), min(rows, self.rows)
        return max(0, min(col, self.cols - cols)), max(0, min(row, self.rows - rows)), cols, rows

    def coverage(self, others: list[QRect]) -> Callable[[Span], int]:
        """A function giving how much of a span the `others` cards claim (each card claims the cells it
        covers plus its gap). Built as a summed-area table, so each answer is four lookups."""
        counts = [[0] * self.cols for _ in range(self.rows)]
        for card in others:
            c0, r0 = (card.x() - self.x0) // STEP, (card.y() - self.y0) // STEP
            c1 = -(-(card.x() + card.width() + GAP - self.x0) // STEP)
            r1 = -(-(card.y() + card.height() + GAP - self.y0) // STEP)
            for r in range(max(r0, 0), min(r1, self.rows)):
                line = counts[r]
                for c in range(max(c0, 0), min(c1, self.cols)):
                    line[c] += 1
        table = [[0] * (self.cols + 1)]
        for line in counts:
            above, run, row = table[-1], 0, [0]
            for c, count in enumerate(line):
                run += count
                row.append(above[c + 1] + run)
            table.append(row)

        def covered(span: Span) -> int:
            col, row, cols, rows = span
            return table[row + rows][col + cols] - table[row][col + cols] - table[row + rows][col] + table[row][col]
        return covered


def _best_spot(grid: Grid, span: Span, covered: Callable[[Span], int]) -> tuple[Span, int]:
    """The spot nearest to `span` that no other card claims, or failing that the one claimed least;
    with how much of it is claimed."""
    col, row, cols, rows = span
    spots = [(c, r) for c in range(grid.cols - cols + 1) for r in range(grid.rows - rows + 1)]
    spots.sort(key=lambda s: ((s[0] - col) ** 2 + (s[1] - row) ** 2, abs(s[1] - row)))
    best, least = span, None
    for c, r in spots:
        claimed = covered((c, r, cols, rows))
        if least is None or claimed < least:
            best, least = (c, r, cols, rows), claimed
            if not claimed:
                break
    return best, least or 0


def _give_way(span: Span, before: Span, covered: Callable[[Span], int], min_cols: int,
              min_rows: int) -> Span | None:
    """After a resize: pull the dragged edges back towards where they started until the card is clear.
    The biggest card that fits wins; among equals, the one closest to what the user dragged."""
    col, row, cols, rows = span
    b_col, b_row, b_cols, b_rows = before
    lefts, rights = _between(col, b_col), _between(col + cols, b_col + b_cols)
    tops, bottoms = _between(row, b_row), _between(row + rows, b_row + b_rows)
    if len(lefts) * len(rights) * len(tops) * len(bottoms) > MAX_TRIES:
        return None
    best, best_key = None, None
    for left in lefts:
        for right in rights:
            for top in tops:
                for bottom in bottoms:
                    w, h = right - left, bottom - top
                    if w < min_cols or h < min_rows or covered((left, top, w, h)):
                        continue
                    moved = abs(left - col) + abs(right - col - cols) + abs(top - row) + abs(bottom - row - rows)
                    key = (w * h, -moved)
                    if best_key is None or key > best_key:
                        best, best_key = (left, top, w, h), key
    return best


def _lines(grid: Grid, others: list[QRect]) -> tuple[set[int], set[int]]:
    """The grid lines the other cards' edges (gap included) and the screen margins lie on: columns, rows."""
    cols, rows = {0, grid.cols}, {0, grid.rows}
    for card in others:
        cols.update((_nearest_line(card.x() - grid.x0), _nearest_line(card.x() + card.width() + GAP - grid.x0)))
        rows.update((_nearest_line(card.y() - grid.y0), _nearest_line(card.y() + card.height() + GAP - grid.y0)))
    return cols, rows


def _pull(edges: tuple[int, ...], lines: set[int]) -> int:
    """The smallest shift, at most MAGNET cells, that puts one of `edges` on one of `lines` (0 if none)."""
    return min((line - edge for edge in edges for line in lines if abs(line - edge) <= MAGNET), key=abs, default=0)


def _fits(grid: Grid, span: Span, min_cols: int, min_rows: int) -> bool:
    col, row, cols, rows = span
    return (0 <= col and col + cols <= grid.cols and 0 <= row and row + rows <= grid.rows
            and cols >= min_cols and rows >= min_rows)


def _line_up(grid: Grid, span: Span, lines: tuple[set[int], set[int]], covered: Callable[[Span], int]) -> Span:
    """Shift a dropped card so an edge lines up with a nearby edge, if it still fits there."""
    col, row, cols, rows = span
    dx, dy = _pull((col, col + cols), lines[0]), _pull((row, row + rows), lines[1])
    for sx, sy in ((dx, dy), (dx, 0), (0, dy)):
        moved = (col + sx, row + sy, cols, rows)
        if (sx or sy) and _fits(grid, moved, cols, rows) and not covered(moved):
            return moved
    return span


def _line_up_edges(grid: Grid, span: Span, before: Span, lines: tuple[set[int], set[int]],
                   covered: Callable[[Span], int], min_cols: int, min_rows: int) -> Span:
    """After a resize: pull just the dragged edges into line with nearby edges, if the card still fits."""
    col, row, cols, rows = span
    edges = [col, row, col + cols, row + rows]
    started = (before[0], before[1], before[0] + before[2], before[1] + before[3])
    for i, was in enumerate(started):
        if edges[i] != was:
            edges[i] += _pull((edges[i],), lines[i % 2])
    left, top, right, bottom = edges
    pulled = (left, top, right - left, bottom - top)
    return pulled if _fits(grid, pulled, min_cols, min_rows) and not covered(pulled) else span


def _distance(area: QRect, point: QPoint) -> int:
    dx = max(area.left() - point.x(), 0, point.x() - area.right())
    dy = max(area.top() - point.y(), 0, point.y() - area.bottom())
    return dx * dx + dy * dy


def settle(card: QRect, others: list[QRect], min_card: QSize, fixed_height: bool = False,
           before: QRect | None = None, align: bool = False) -> QRect:
    """Where `card` should go: on the grid of its screen, clear of the `others` cards.

    `before` is the card as it was when the user started resizing it, so the dragged edges can give way.
    `align` pulls edges into line with nearby ones (for a note the user has just let go of).
    """
    areas: list[QRect] = []
    for screen in QGuiApplication.screens():
        area = screen.availableGeometry()
        if area not in areas:          # mirrored displays share one area
            areas.append(area)
    areas.sort(key=lambda a: _distance(a, card.center()))     # its own screen first, then the nearest
    home = Grid(areas[0])
    home_span = home.snap(card, min_card, fixed_height)
    home_covered = home.coverage(others)
    lines = _lines(home, others) if align else None

    if before is not None and before.size() != card.size() and _distance(areas[0], before.center()) == 0:
        min_cols, min_rows = _cells(min_card.width()), home_span[3] if fixed_height else _cells(min_card.height())
        start = home.snap(before, min_card, fixed_height)
        spot = _give_way(home_span, start, home_covered, min_cols, min_rows)
        if spot is not None:
            if lines:
                spot = _line_up_edges(home, spot, start, lines, home_covered, min_cols, min_rows)
            return _place(home, spot, card, fixed_height)

    fallback = None
    for area in areas:
        grid, span, covered = home, home_span, home_covered
        if area != home.area:
            grid = Grid(area)
            span, covered = grid.snap(card, min_card, fixed_height), grid.coverage(others)
        spot, claimed = _best_spot(grid, span, covered)
        if not claimed:
            if lines and grid is home:
                spot = _line_up(home, spot, lines, home_covered)
            return _place(grid, spot, card, fixed_height)
        if fallback is None:
            fallback = _place(grid, spot, card, fixed_height)
    return fallback     # every screen is full: the spot on its own screen where it overlaps least


def _place(grid: Grid, span: Span, card: QRect, fixed_height: bool) -> QRect:
    rect = grid.rect(span)
    if fixed_height:
        rect.setHeight(card.height())
    return rect
