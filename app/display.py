"""Format values for templates."""

from datetime import datetime, timezone

STATUS_LABELS = {
    "new": "New",
    "action": "Action",
    "revisit": "Revisit",
    "keep": "Keep",
    "let_go": "Let Go",
    "resolved": "Resolved",
}

CATEGORY_LABELS = {
    "work": "Work",
    "family": "Family",
    "personal": "Personal",
    "money": "Money",
    "health": "Health",
    "ideas": "Ideas",
    "other": "Other",
}


def format_revisit_date(iso_date: str) -> str:
    """Show a stored YYYY-MM-DD revisit date in a friendly way."""
    moment = datetime.fromisoformat(iso_date)
    return moment.strftime("%b %-d, %Y")


def format_created_at(iso_utc: str) -> str:
    """Show a stored UTC timestamp in this machine's local time."""
    normalized = iso_utc.replace("Z", "+00:00")
    moment = datetime.fromisoformat(normalized)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone()
    return local.strftime("%b %-d, %Y · %-I:%M %p")
