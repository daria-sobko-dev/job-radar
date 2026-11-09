"""DOU (jobs.dou.ua) vacancies via their public RSS feeds."""

from __future__ import annotations

import html
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
_SALARY = re.compile(r"[$€₴]|грн|\buah\b|\busd\b|\beur\b", re.IGNORECASE)


def split_salary(rest: str) -> tuple[str, str]:
    """'$1100–1500, Краків (Польща), віддалено' -> ('$1100–1500', 'Краків (Польща), віддалено')."""
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    salary = [p for p in parts if _SALARY.search(p)]
    location = [p for p in parts if not _SALARY.search(p)]
    return ", ".join(salary), ", ".join(location)


def parse(xml_text: str) -> list[Job]:
    """Parse an RSS 2.0 document from DOU into jobs."""
    root = ET.fromstring(xml_text)
    jobs: list[Job] = []
    for item in root.iter("item"):
        # DOU titles carry HTML entities (&amp;, &nbsp;) on top of the XML escaping.
        raw_title = html.unescape(item.findtext("title") or "").replace("\xa0", " ").strip()
        link = (item.findtext("link") or "").strip()
        if not raw_title or not link:
            continue

        m = _TITLE.match(raw_title)
        role, company, location, salary = raw_title, "", "", ""
        if m:
            role = m.group("role").strip()
            company = m.group("company").strip()
            salary, location = split_salary(m.group("location") or "")

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
                salary=salary,
            )
        )
    return jobs


def fetch(session: requests.Session, feed_url: str) -> list[Job]:
    resp = session.get(feed_url, timeout=TIMEOUT)
    resp.raise_for_status()
    return parse(resp.text)
