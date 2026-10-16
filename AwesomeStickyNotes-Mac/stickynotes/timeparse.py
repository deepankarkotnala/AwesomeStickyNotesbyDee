"""Tiny parser for reminder suffixes such as "@5pm", "@tomorrow 9am", "@fri 10:30" or "@30m"."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_WORDS = "|".join(["today", "tonight", "tomorrow", "tmrw", "tom"] + [d + "[a-z]*" for d in _DAYS])

_RELATIVE = re.compile(r"^(?:in\s*)?(?P<n>\d+)\s*(?P<unit>m|min|mins|minutes?|h|hr|hrs|hours?)$")
_ABSOLUTE = re.compile(
    rf"^(?P<day>{_DAY_WORDS})?\s*(?:at\s*)?"
    r"(?:(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm|a|p)?)?$"
)
_SUFFIX = re.compile(r"(?:^|\s)@\s*([^@]+?)\s*$")


def parse_when(spec: str, ref: datetime | None = None) -> datetime | None:
    ref = (ref or datetime.now()).replace(second=0, microsecond=0)
    s = " ".join(spec.lower().split())
    if not s:
        return None

    m = _RELATIVE.match(s)
    if m:
        n = int(m["n"])
        if n <= 0:
            return None
        return ref + (timedelta(hours=n) if m["unit"].startswith("h") else timedelta(minutes=n))

    m = _ABSOLUTE.match(s)
    if not m or not (m["day"] or m["h"]):
        return None
    day = m["day"]

    if day in (None, "today", "tonight"):
        base = ref.date()
    elif day in ("tomorrow", "tmrw", "tom"):
        base = ref.date() + timedelta(days=1)
    else:
        ahead = (_DAYS.index(day[:3]) - ref.weekday()) % 7 or 7
        base = ref.date() + timedelta(days=ahead)

    if m["h"] is None:
        if day == "today":
            return None
        hour, minute = (20, 0) if day == "tonight" else (9, 0)
    else:
        hour, minute = int(m["h"]), int(m["m"] or 0)
        if hour > 23 or minute > 59:
            return None
        if m["ap"]:
            if not 1 <= hour <= 12:
                return None
            hour = hour % 12 + (12 if m["ap"].startswith("p") else 0)
        elif 1 <= hour <= 6 or (day == "tonight" and hour < 12):
            hour += 12  # "@5" almost always means 5 PM

    when = datetime.combine(base, time(hour, minute))
    if m["h"] and not m["ap"] and 7 <= hour <= 11 and base == ref.date() and when <= ref:
        when += timedelta(hours=12)  # "@9" at 2 PM means 9 PM
    if day is None and when <= ref:
        when += timedelta(days=1)
    return when


def extract_reminder(text: str, ref: datetime | None = None) -> tuple[str, datetime | None]:
    """Split "Call Sam @5pm" into ("Call Sam", <today 17:00>). Unparseable suffixes stay in the text."""
    m = _SUFFIX.search(text)
    if not m:
        return text.strip(), None
    when = parse_when(m.group(1), ref)
    if when is None:
        return text.strip(), None
    return text[:m.start()].strip(), when


def clock(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    return f"{hour}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def day_label(d: date, today: date | None = None, long: bool = False) -> str:
    today = today or date.today()
    delta = (d - today).days
    if delta == 0:
        return "Today"
    if delta == -1:
        return "Yesterday"
    if delta == 1:
        return "Tomorrow"
    if -6 <= delta <= 6:
        return f"{d:%A}" if long else f"{d:%a}"
    if long:
        return f"{d:%A}, {d.day} {d:%B}" + ("" if d.year == today.year else f" {d.year}")
    return f"{d.day} {d:%b}" + ("" if d.year == today.year else f" {d.year}")


def friendly(dt: datetime, ref: datetime | None = None) -> str:
    ref = ref or datetime.now()
    return f"{day_label(dt.date(), ref.date())} {clock(dt)}"
