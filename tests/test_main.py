"""End-to-end run with the network replaced by fixtures."""

import json
from pathlib import Path

import pytest
import yaml

from jobradar import main as app
from jobradar.sources import dou, greenhouse, lever


@pytest.fixture
def workdir(tmp_path, monkeypatch, dou_xml, greenhouse_data, lever_data):
    cfg = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))
    cfg["state_file"] = str(tmp_path / "seen.json")
    cfg.pop("max_age_hours", None)  # fixtures have fixed dates; the age filter is tested separately
    cfg["sources"] = {
        "dou": ["https://feed.example/dou"],
        "greenhouse": [{"board": "dkbcodefactory", "name": "DKB Code Factory"}],
        "lever": [{"company": "example", "name": "Example"}],
    }
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")

    monkeypatch.setattr(dou, "fetch", lambda s, u: dou.parse(dou_xml))
    monkeypatch.setattr(greenhouse, "fetch", lambda s, b, n=None: greenhouse.parse(greenhouse_data, n or b))
    monkeypatch.setattr(lever, "fetch", lambda s, c, n=None: lever.parse(lever_data, n or c))
    return tmp_path


def test_first_run_sends_matches_and_saves_state(workdir, monkeypatch):
    sent = []
    monkeypatch.setattr(app.telegram, "send", lambda s, t, c, text: sent.append(text))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    assert app.main(["--config", str(workdir / "config.yaml")]) == 0
    text = "\n".join(sent)
    assert "Junior DevOps Engineer" in text
    assert "DevOps Engineer - Credit Cards" in text
    assert "Cloud Engineer" in text
    assert "Senior" not in text
    assert len(json.loads((workdir / "seen.json").read_text())) == 6


def test_second_run_reports_nothing_new(workdir, monkeypatch):
    sent = []
    monkeypatch.setattr(app.telegram, "send", lambda s, t, c, text: sent.append(text))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    config = str(workdir / "config.yaml")

    app.main(["--config", config])
    sent.clear()
    app.main(["--config", config])
    assert len(sent) == 1 and "No new matches today" in sent[0]


def test_dry_run_prints_and_does_not_save(workdir, capsys):
    assert app.main(["--config", str(workdir / "config.yaml"), "--dry-run"]) == 0
    assert "Job Radar" in capsys.readouterr().out
    assert not (workdir / "seen.json").exists()


def test_one_failing_source_does_not_stop_the_run(workdir, monkeypatch, capsys):
    def boom(*_args, **_kwargs):
        raise ConnectionError("down")

    monkeypatch.setattr(dou, "fetch", boom)
    assert app.main(["--config", str(workdir / "config.yaml"), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Sources with errors: dou:" in out
    assert "DevOps Engineer - Credit Cards" in out


def test_all_sources_failing_returns_error(workdir, monkeypatch):
    def boom(*_args, **_kwargs):
        raise ConnectionError("down")

    for mod in (dou, greenhouse, lever):
        monkeypatch.setattr(mod, "fetch", boom)
    assert app.main(["--config", str(workdir / "config.yaml"), "--dry-run"]) == 1


def test_missing_secrets_is_an_error(workdir, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert app.main(["--config", str(workdir / "config.yaml")]) == 2


def test_age_filter_drops_old_jobs(workdir, monkeypatch, capsys):
    from datetime import UTC, datetime

    cfg_path = workdir / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["max_age_hours"] = 26
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    fresh = greenhouse.parse(
        {
            "jobs": [
                {
                    "id": 1,
                    "title": "Junior DevOps Engineer",
                    "location": {"name": "Valencia, Spain"},
                    "absolute_url": "https://example.com/fresh",
                    "first_published": datetime.now(UTC).isoformat(),
                    "content": "AWS Terraform Linux Docker",
                }
            ]
        },
        "Fresh Co",
    )
    monkeypatch.setattr(greenhouse, "fetch", lambda s, b, n=None: fresh)
    # DOU and Lever fixtures are dated 2026-11-09 08:00 and 2025-11-09: old relative to the run time
    monkeypatch.setattr(dou, "fetch", lambda s, u: dou.parse(_old_dou()))

    assert app.main(["--config", str(cfg_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Junior DevOps Engineer" in out and "Fresh Co" in out
    assert "Acme Cloud" not in out
    assert "from the last 26h" in out


def _old_dou() -> str:
    return (
        "<rss><channel><item><title>Junior DevOps Engineer в Acme Cloud, віддалено</title>"
        "<link>https://jobs.dou.ua/companies/acme/vacancies/1/</link>"
        "<description>AWS Terraform Linux Docker</description>"
        "<pubDate>Mon, 01 Jan 2024 08:00:00 +0200</pubDate></item></channel></rss>"
    )
