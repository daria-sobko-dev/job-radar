import json
from pathlib import Path

import pytest
import yaml

from jobradar.scoring import Profile

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).parent.parent


@pytest.fixture
def dou_xml() -> str:
    return (FIXTURES / "dou.xml").read_text(encoding="utf-8")


@pytest.fixture
def greenhouse_data() -> dict:
    return json.loads((FIXTURES / "greenhouse.json").read_text(encoding="utf-8"))


@pytest.fixture
def lever_data() -> list:
    return json.loads((FIXTURES / "lever.json").read_text(encoding="utf-8"))


@pytest.fixture
def profile() -> Profile:
    """The real profile from config.yaml, so tests also guard the shipped config."""
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    return Profile.from_config(cfg["profile"])
