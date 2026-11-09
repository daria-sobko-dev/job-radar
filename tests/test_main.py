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
