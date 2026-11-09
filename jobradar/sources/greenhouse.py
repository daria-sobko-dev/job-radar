"""Company career boards hosted on Greenhouse (public Job Board API, no key needed)."""

from __future__ import annotations

from typing import Any

import requests

from ..models import Job
from ..text import html_to_text

SOURCE = "greenhouse"
TIMEOUT = 30
API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


def parse(data: dict[str, Any], company: str) -> list[Job]:
    jobs: list[Job] = []
    for item in data.get("jobs", []):
        jobs.append(
            Job(
                source=SOURCE,
                id=str(item["id"]),
                title=(item.get("title") or "").strip(),
                company=company,
                location=((item.get("location") or {}).get("name") or "").strip(),
                url=item.get("absolute_url") or "",
                description=html_to_text(item.get("content")),
                published=item.get("first_published") or item.get("updated_at"),
            )
        )
    return jobs


def fetch(session: requests.Session, board: str, company: str | None = None) -> list[Job]:
    resp = session.get(API.format(board=board), timeout=TIMEOUT)
    resp.raise_for_status()
    return parse(resp.json(), company or board)
