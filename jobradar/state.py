"""Remember which jobs were already processed so each one is reported once."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


def load(path: Path) -> dict[str, str]:
    """Return {job_key: first_seen_iso_date}. Missing or broken file means empty state."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def save(path: Path, seen: dict[str, str], today: date, keep_days: int = 90) -> None:
    """Write the state, dropping entries older than `keep_days` to keep the file small."""
    cutoff = (today - timedelta(days=keep_days)).isoformat()
    pruned = {k: v for k, v in seen.items() if v >= cutoff}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(pruned, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)  # atomic on the same filesystem
