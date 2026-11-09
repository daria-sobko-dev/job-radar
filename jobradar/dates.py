"""Parse the publication dates that different sources use."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime


def parse_published(value: str | None) -> datetime | None:
    """Parse RFC 822 (RSS) or ISO 8601 (APIs) into an aware UTC datetime. None if unknown."""
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def is_recent(value: str | None, max_age_hours: float, now: datetime) -> bool:
    """True if published within the window. Jobs without a date are kept: better one extra than one missed."""
    published = parse_published(value)
    if published is None:
        return True
    return published >= now - timedelta(hours=max_age_hours)
