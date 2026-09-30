"""Local calendar dates for revisit choices and weekly reflection."""

from datetime import date, datetime, time, timedelta, timezone


def tomorrow() -> date:
    return date.today() + timedelta(days=1)


def this_weekend_saturday() -> date:
    """The next Saturday on the calendar (not today if today is Saturday)."""
    today = date.today()
    days_ahead = 5 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def next_week() -> date:
    return date.today() + timedelta(days=7)


def parse_iso_date(text: str) -> date:
    """Parse YYYY-MM-DD. Raises ValueError if the format is wrong."""
    return date.fromisoformat(text.strip())


def revisit_date_from_form(preset: str, custom_date: str) -> date:
    """Turn a revisit form choice into a calendar date."""
    choice = preset.strip().lower()
    if choice == "tomorrow":
        return tomorrow()
    if choice == "weekend":
        return this_weekend_saturday()
    if choice == "next_week":
        return next_week()
    if choice == "custom":
        if not custom_date.strip():
            raise ValueError("Pick a date.")
        return parse_iso_date(custom_date)
    raise ValueError("Pick when to revisit.")


def _local_timezone():
    return datetime.now().astimezone().tzinfo


def current_week_bounds_utc() -> tuple[str, str]:
    """Monday 00:00 through Sunday 23:59:59 local time, as UTC ISO strings."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    tz = _local_timezone()
    start = datetime.combine(monday, time.min, tzinfo=tz)
    end = datetime.combine(sunday, time(23, 59, 59), tzinfo=tz)
    return _to_utc_z(start), _to_utc_z(end)


def current_week_label() -> str:
    """Human-readable range for the reflection page header."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    if monday.year == sunday.year:
        return f"{monday.strftime('%b %-d')} – {sunday.strftime('%b %-d, %Y')}"
    return f"{monday.strftime('%b %-d, %Y')} – {sunday.strftime('%b %-d, %Y')}"


def _to_utc_z(moment: datetime) -> str:
    return (
        moment.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
