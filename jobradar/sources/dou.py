"""DOU (jobs.dou.ua) vacancies via their public RSS feeds."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import requests

from ..models import Job
from ..text import html_to_text

SOURCE = "dou"
TIMEOUT = 20

# DOU item titles look like: "Junior DevOps Engineer в ACME, Київ, віддалено"
_TITLE = re.compile(r"^(?P<role>.+?) в (?P<company>[^,]+?)(?:, (?P<location>.+))?$")
_VACANCY_ID = re.compile(r"/vacancies/(\d+)")


def parse(xml_text: str) -> list[Job]:
    """Parse an RSS 2.0 document from DOU into jobs."""
    root = ET.fromstring(xml_text)
    jobs: list[Job] = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not raw_title or not link:
            continue

        m = _TITLE.match(raw_title)
        role, company, location = raw_title, "", ""
        if m:
            role = m.group("role").strip()
            company = m.group("company").strip()
            location = (m.group("location") or "").strip()

        id_match = _VACANCY_ID.search(link)
        jobs.append(
            Job(
                source=SOURCE,
                id=id_match.group(1) if id_match else link,
                title=role,
                company=company,
                location=location,
                url=link,
                description=html_to_text(item.findtext("description")),
                published=(item.findtext("pubDate") or "").strip() or None,
            )
        )
    return jobs


def fetch(session: requests.Session, feed_url: str) -> list[Job]:
    resp = session.get(feed_url, timeout=TIMEOUT)
    resp.raise_for_status()
    return parse(resp.text)
