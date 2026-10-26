"""Repeating reminders: how a repeat is written down, how it reads, and when it comes round next.

A task's `repeat` column holds a short code:
    "15min", "2h", "3d", "1w"   every N minutes / hours / days / weeks
    "1mo"                       every month on the same day (the month's last day when it is shorter)
    "weekdays"                  every Monday to Friday
    ""                          no repeat
The series runs from the task's `repeat_from` time (its first reminder), so snoozing one alert never
shifts the times of the ones after it.
"""
from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta

# unit -> (singular, plural, short, most allowed in a custom repeat)
UNITS = {
    "min": ("minute", "minutes", "m", 60),
    "h": ("hour", "hours", "h", 24),
    "d": ("day", "days", "d", 365),
    "w": ("week", "weeks", "w", 52),
}
PRESETS = ("10min", "15min", "30min", "1h", "2h", "3h", "1d", "weekdays", "1w", "1mo")
_CODE = re.compile(r"^(\d+)(min|h|d|w|mo)$")
_NAMED = {"1h": ("Every hour", "hourly"), "1d": ("Every day", "daily"), "1w": ("Every week", "weekly"),
          "1mo": ("Every month", "monthly"), "weekdays": ("Every weekday (Mon–Fri)", "weekdays")}


def code(n: int, unit: str) -> str:
    return f"{n}{unit}"


def parse(spec: str) -> tuple[int, str] | None:
    """(n, unit) for an every-N code, or None for "weekdays", "" and anything unknown."""
    m = _CODE.match(spec or "")
    return (int(m[1]), m[2]) if m and int(m[1]) > 0 else None


def valid(spec: str) -> bool:
    return spec == "weekdays" or parse(spec) is not None


def describe(spec: str) -> str:
    """"Every 15 minutes", "Every day", "Every weekday (Mon–Fri)"."""
    if spec in _NAMED:
        return _NAMED[spec][0]
    n, unit = parse(spec) or (0, "")
    if unit == "mo":
        return f"Every {n} months"
    one, many = UNITS[unit][:2] if unit else ("", "")
    return f"Every {one}" if n == 1 else f"Every {n} {many}"


def short(spec: str) -> str:
    """For tight spots such as the reminder chip on a task: "every 15m", "daily", "weekdays"."""
    if spec in _NAMED:
        return _NAMED[spec][1]
    n, unit = parse(spec) or (0, "")
    return f"every {n}mo" if unit == "mo" else f"every {n}{UNITS[unit][2]}" if unit else ""


def by_the_day(spec: str) -> bool:
    """True for repeats that come round at a time of day (daily, weekdays, weekly, monthly...)."""
    parsed = parse(spec)
    return spec == "weekdays" or (parsed is not None and parsed[1] in ("d", "w", "mo"))


def step(spec: str) -> timedelta | None:
    """The fixed gap between reminders, for every-N-minutes/hours/days/weeks repeats."""
    parsed = parse(spec)
    if parsed is None or parsed[1] == "mo":
        return None
    n, unit = parsed
    return {"min": timedelta(minutes=n), "h": timedelta(hours=n), "d": timedelta(days=n),
            "w": timedelta(weeks=n)}[unit]


def next_after(spec: str, start: datetime, after: datetime) -> datetime | None:
    """The first time in the series that begins at `start` which is later than `after`."""
    if spec == "weekdays":
        day = max(start.date(), after.date())
        while True:
            when = datetime.combine(day, start.time())
            if when > after and when >= start and day.weekday() < 5:
                return when
            day += timedelta(days=1)
    parsed = parse(spec)
    if parsed is None:
        return None
    if after < start:
        return start
    n, unit = parsed
    if unit == "mo":
        k = max(0, ((after.year - start.year) * 12 + after.month - start.month) // n - 1)
        while True:
            when = _add_months(start, k * n)
            if when > after:
                return when
            k += 1
    gap = step(spec)
    return start + ((after - start) // gap + 1) * gap


def _add_months(when: datetime, months: int) -> datetime:
    years, month = divmod(when.month - 1 + months, 12)
    year = when.year + years
    return when.replace(year=year, month=month + 1, day=min(when.day, calendar.monthrange(year, month + 1)[1]))
