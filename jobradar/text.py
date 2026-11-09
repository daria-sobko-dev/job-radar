"""Small text helpers: HTML to plain text and keyword matching."""

from __future__ import annotations

import html
import re
from functools import lru_cache

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)\b[^>]*>", re.IGNORECASE)
_SPACES = re.compile(r"[ \t\r\f\v]+")
_NEWLINES = re.compile(r"\n{3,}")


def html_to_text(raw: str | None) -> str:
    """Convert an HTML fragment (possibly entity-encoded twice) to readable text."""
    if not raw:
        return ""
    text = html.unescape(raw)
    if "&lt;" in text or "&amp;" in text:  # Greenhouse double-encodes its content
        text = html.unescape(text)
    text = _BLOCK.sub("\n", text)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NEWLINES.sub("\n\n", text).strip()


@lru_cache(maxsize=1024)
def _pattern(term: str) -> re.Pattern[str]:
    # Word boundaries that also work for terms like "ci/cd", "c++" or Cyrillic words.
    return re.compile(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)")


def contains(text: str, term: str) -> bool:
    """Case-insensitive whole-term match. `text` is expected to be lowercased."""
    return bool(_pattern(term).search(text))


def count_term(text: str, term: str) -> int:
    """How many times `term` occurs as a whole term in lowercased `text`."""
    return len(_pattern(term).findall(text))


def find_terms(text: str, terms: list[str]) -> list[str]:
    """Return the terms from `terms` that occur in `text`, preserving order."""
    return [t for t in terms if contains(text, t)]
