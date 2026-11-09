"""Format the daily digest and deliver it through the Telegram Bot API."""

from __future__ import annotations

import html
from datetime import date

import requests

from .models import Match

API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 4000  # Telegram allows 4096 characters per message; keep a margin


def _item(m: Match) -> str:
    j = m.job
    title = html.escape(j.title)
    link = f'<a href="{html.escape(j.url, quote=True)}">{title}</a>' if j.url else title
    where = " · ".join(html.escape(p) for p in (j.company, j.location) if p)
    lines = [f"<b>{m.score}</b> · {link}"]
    if where:
        lines.append(where)
    if m.skills:
        lines.append("Skills: " + html.escape(", ".join(m.skills)))
    if m.notes:
        lines.append("Notes: " + html.escape(", ".join(m.notes)))
    return "\n".join(lines)


def build_messages(
    matches: list[Match], today: date, failures: list[str] | None = None, total_new: int = 0
) -> list[str]:
    """Return one or more HTML messages, each under Telegram's size limit."""
    header = f"<b>Job Radar · {today.isoformat()}</b>\n"
    if matches:
        header += f"{len(matches)} match(es) out of {total_new} new vacancies\n"
    else:
        header += f"No new matches today ({total_new} new vacancies checked)\n"

    blocks = [_item(m) for m in matches]
    if failures:
        blocks.append("<i>Sources with errors: " + html.escape(", ".join(failures)) + "</i>")

    messages, current = [], header
    for block in blocks:
        if len(current) + len(block) + 2 > LIMIT:
            messages.append(current.rstrip())
            current = ""
        current += "\n" + block + "\n"
    messages.append(current.rstrip())
    return messages


def send(session: requests.Session, token: str, chat_id: str, text: str) -> None:
    resp = session.post(
        API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    if not resp.ok:
        # Never echo the URL: it contains the bot token.
        raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text[:300]}")
