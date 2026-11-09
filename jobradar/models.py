"""Core data types shared by sources, scoring and notifications."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Job:
    """A vacancy normalised from any source."""

    source: str
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    published: str | None = None
    salary: str = ""

    @property
    def key(self) -> str:
        """Stable identifier used for de-duplication across runs."""
        return f"{self.source}:{self.id}"


@dataclass
class Match:
    """A job that passed the profile filters, with its score and the reasons."""

    job: Job
    score: int
    skills: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
