"""Match jobs against a candidate profile defined in config.yaml.

Rules, in order:
1. Hard filters on the title: it must name a relevant role and must not be a senior/lead role.
   Red flags anywhere in the vacancy (industry, unpaid work, ...) reject it outright.
2. Location filter on title + location: remote or an allowed city/region.
3. Score = weighted skills found in the full text + title bonuses + text penalties.
4. Keep the job if score >= min_score.

Several profiles (directions) can be configured. Each job is scored against all of
them and kept once, under the profile where it scores best.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Job, Match
from .text import contains, find_terms, norm
from .vocabulary import aliases

_COMMON = ("red_flags", "allowed_locations", "location_bonus", "penalties")


@dataclass
class Profile:
    name: str = "default"
    label: str = ""
    min_score: int = 4
    title_keywords: list[str] = field(default_factory=list)
    exclude_title: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    allowed_locations: list[str] = field(default_factory=list)
    skills: dict[str, int] = field(default_factory=dict)
    title_bonus: dict[str, int] = field(default_factory=dict)
    penalties: dict[str, int] = field(default_factory=dict)
    location_bonus: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_config(cls, cfg: dict[str, Any], common: dict[str, Any] | None = None, name: str = "default") -> Profile:
        """Build a profile; shared `filters` apply unless the profile overrides them."""
        cfg = {**{k: v for k, v in (common or {}).items() if k in _COMMON}, **cfg}
        return cls(
            name=name,
            label=str(cfg.get("label") or name),
            min_score=int(cfg.get("min_score", 4)),
            title_keywords=[t.lower() for t in cfg.get("title_keywords", [])],
            exclude_title=[t.lower() for t in cfg.get("exclude_title", [])],
            red_flags=[t.lower() for t in cfg.get("red_flags", [])],
            allowed_locations=[t.lower() for t in cfg.get("allowed_locations", [])],
            skills={k.lower(): int(v) for k, v in (cfg.get("skills") or {}).items()},
            title_bonus={k.lower(): int(v) for k, v in (cfg.get("title_bonus") or {}).items()},
            penalties={k.lower(): int(v) for k, v in (cfg.get("penalties") or {}).items()},
            location_bonus={k.lower(): int(v) for k, v in (cfg.get("location_bonus") or {}).items()},
        )


def rejection_reason(job: Job, profile: Profile) -> str | None:
    """Return why a job fails the hard filters, or None if it passes them."""
    title = norm(job.title)
    if profile.title_keywords and not find_terms(title, profile.title_keywords):
        return "title does not name a target role"
    excluded = find_terms(title, profile.exclude_title)
    if excluded:
        return f"title excluded: {', '.join(excluded)}"
    flags = find_terms(norm(f"{title}\n{job.company}\n{job.description}"), profile.red_flags)
    if flags:
        return f"red flag: {', '.join(flags)}"
    if profile.allowed_locations:
        where = norm(f"{job.title} {job.location}")
        if not find_terms(where, profile.allowed_locations):
            return f"location not allowed: {job.location or 'unknown'}"
    return None


def score(job: Job, profile: Profile) -> Match | None:
    """Score a job. Returns None when it fails a hard filter or scores too low."""
    if rejection_reason(job, profile):
        return None

    title = norm(job.title)
    where = norm(f"{job.title} {job.location}")
    text = norm(f"{job.title}\n{job.location}\n{job.description}")

    skills = [s for s in profile.skills if any(contains(text, a) for a in aliases(s))]
    total = sum(profile.skills[s] for s in skills)
    notes: list[str] = []

    for term in find_terms(title, list(profile.title_bonus)):
        total += profile.title_bonus[term]
        notes.append(f"{term} {profile.title_bonus[term]:+d}")

    for term in find_terms(where, list(profile.location_bonus)):
        total += profile.location_bonus[term]
        notes.append(f"{term} {profile.location_bonus[term]:+d}")

    for term in find_terms(text, list(profile.penalties)):
        total += profile.penalties[term]
        notes.append(f"'{term}' {profile.penalties[term]:+d}")

    if total < profile.min_score:
        return None
    return Match(job=job, score=total, skills=skills, notes=notes, profile=profile.name)


def load_profiles(cfg: dict[str, Any]) -> list[Profile]:
    """Read `profiles` (several directions) or the older single `profile` block."""
    if cfg.get("profiles"):
        common = cfg.get("filters") or {}
        return [Profile.from_config(p or {}, common, name) for name, p in cfg["profiles"].items()]
    return [Profile.from_config(cfg.get("profile") or {})]


def best_match(job: Job, profiles: list[Profile]) -> Match | None:
    matches = [m for p in profiles if (m := score(job, p))]
    return max(matches, key=lambda m: m.score) if matches else None


def rank(jobs: list[Job], profiles: Profile | list[Profile]) -> list[Match]:
    if isinstance(profiles, Profile):
        profiles = [profiles]
    matches = [m for j in jobs if (m := best_match(j, profiles))]
    return sorted(matches, key=lambda m: m.score, reverse=True)
