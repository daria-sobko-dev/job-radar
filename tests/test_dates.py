from datetime import UTC, datetime

from jobradar.dates import is_recent, parse_published

NOW = datetime(2026, 11, 9, 7, 0, tzinfo=UTC)


def test_parses_rss_and_iso_formats():
    assert parse_published("Mon, 09 Nov 2026 08:00:00 +0200") == datetime(2026, 11, 9, 6, 0, tzinfo=UTC)
    assert parse_published("2026-11-05T10:00:00-05:00") == datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
    assert parse_published("2026-11-09T06:00:00Z") == datetime(2026, 11, 9, 6, 0, tzinfo=UTC)
    assert parse_published("not a date") is None
    assert parse_published(None) is None


def test_recent_window():
    assert is_recent("2026-11-08T08:00:00Z", 24, NOW)  # 23h ago
    assert not is_recent("2026-11-08T06:00:00Z", 24, NOW)  # 25h ago
    assert is_recent("2026-11-08T06:00:00Z", 26, NOW)


def test_undated_jobs_are_kept():
    assert is_recent(None, 24, NOW)
    assert is_recent("garbage", 24, NOW)
