import json
from datetime import date

from jobradar import state, telegram
from jobradar.models import Job, Match


def test_state_roundtrip_and_pruning(tmp_path):
    path = tmp_path / "data" / "seen.json"
    today = date(2026, 11, 9)
    state.save(path, {"dou:1": "2026-11-09", "dou:old": "2026-01-01"}, today, keep_days=90)
    assert state.load(path) == {"dou:1": "2026-11-09"}


def test_state_tolerates_missing_or_broken_file(tmp_path):
    assert state.load(tmp_path / "nope.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert state.load(broken) == {}
    broken.write_text(json.dumps(["a", "list"]), encoding="utf-8")
    assert state.load(broken) == {}


def _match(i: int, title: str = "DevOps Engineer") -> Match:
    job = Job("t", str(i), title, "Acme & Co", "Valencia, Spain", f"https://example.com/{i}?a=1&b=2")
    return Match(job=job, score=7, skills=["aws", "terraform"], notes=["junior +3"])


def test_message_escapes_html():
    msg = telegram.build_messages([_match(1, "SRE <Cloud>")], date(2026, 11, 9), total_new=3)[0]
    assert "SRE &lt;Cloud&gt;" in msg
    assert "Acme &amp; Co" in msg
    assert 'href="https://example.com/1?a=1&amp;b=2"' in msg
    assert "1 match(es) out of 3 new vacancies" in msg


def test_empty_digest_and_failures_are_reported():
    msg = telegram.build_messages([], date(2026, 11, 9), failures=["dou:feed"], total_new=0)[0]
    assert "No new matches today" in msg
    assert "Sources with errors: dou:feed" in msg


def test_long_digest_is_split_under_limit():
    matches = [_match(i, "DevOps Engineer " + "x" * 150) for i in range(60)]
    messages = telegram.build_messages(matches, date(2026, 11, 9), total_new=60)
    assert len(messages) > 1
    assert all(len(m) <= telegram.LIMIT for m in messages)
    assert sum(m.count("<b>7</b>") for m in messages) == 60
