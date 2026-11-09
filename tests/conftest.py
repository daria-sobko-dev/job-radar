import json
from pathlib import Path

import pytest
import yaml

from jobradar.scoring import Profile, load_profiles

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


def _config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def profiles() -> list[Profile]:
    """The real profiles from config.yaml, so tests also guard the shipped config."""
    return load_profiles(_config())


@pytest.fixture
def profile(profiles) -> Profile:
    return next(p for p in profiles if p.name == "devops")


@pytest.fixture
def web_profile(profiles) -> Profile:
    return next(p for p in profiles if p.name == "web")
