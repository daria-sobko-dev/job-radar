"""Company career pages hosted on Lever (public postings API, no key needed)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from ..models import Job
from ..text import html_to_text

SOURCE = "lever"
TIMEOUT = 30
API = "https://api.lever.co/v0/postings/{company}?mode=json"


def _description(item: dict[str, Any]) -> str:
    parts = [item.get("descriptionPlain") or ""]
    for block in item.get("lists") or []:
        parts.append(block.get("text") or "")
        parts.append(block.get("content") or "")
    parts.append(item.get("additionalPlain") or "")
    # lists[].content is HTML, the *Plain fields are already text
    return html_to_text("\n".join(p for p in parts if p))


def parse(data: list[dict[str, Any]], company: str) -> list[Job]:
    jobs: list[Job] = []
    for item in data:
        created = item.get("createdAt")
        published = datetime.fromtimestamp(created / 1000, tz=UTC).isoformat() if created else None
        categories = item.get("categories") or {}
        jobs.append(
            Job(
                source=SOURCE,
                id=str(item["id"]),
                title=(item.get("text") or "").strip(),
                company=company,
                location=(categories.get("location") or "").strip(),
                url=item.get("hostedUrl") or "",
                description=_description(item),
                published=published,
            )
        )
    return jobs


def fetch(session: requests.Session, company_slug: str, company: str | None = None) -> list[Job]:
    resp = session.get(API.format(company=company_slug), timeout=TIMEOUT)
    resp.raise_for_status()
    return parse(resp.json(), company or company_slug)
