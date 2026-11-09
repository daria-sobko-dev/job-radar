"""Entry point: fetch all sources, keep new jobs, score them and send the digest."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import requests
import yaml

from . import state, telegram
from .models import Job
from .scoring import Profile, rank, rejection_reason
from .sources import dou, greenhouse, lever

log = logging.getLogger("jobradar")
USER_AGENT = "Mozilla/5.0 (compatible; job-radar/1.0; +https://github.com/daria-sobko-dev/job-radar)"


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def source_tasks(cfg: dict[str, Any], session: requests.Session) -> list[tuple[str, Callable[[], list[Job]]]]:
    """Turn the `sources` config block into named fetch callables."""
    src = cfg.get("sources") or {}
    tasks: list[tuple[str, Callable[[], list[Job]]]] = []
    for url in src.get("dou") or []:
        tasks.append((f"dou:{url}", lambda u=url: dou.fetch(session, u)))
    for entry in src.get("greenhouse") or []:
        board, name = entry["board"], entry.get("name")
        tasks.append((f"greenhouse:{board}", lambda b=board, n=name: greenhouse.fetch(session, b, n)))
    for entry in src.get("lever") or []:
        slug, name = entry["company"], entry.get("name")
        tasks.append((f"lever:{slug}", lambda s=slug, n=name: lever.fetch(session, s, n)))
    return tasks


def collect(tasks: list[tuple[str, Callable[[], list[Job]]]]) -> tuple[list[Job], list[str]]:
    """Run every source; one failing source must not stop the others."""
    jobs: list[Job] = []
    failures: list[str] = []
    for name, fetch in tasks:
        try:
            found = fetch()
            log.info("%s: %d jobs", name, len(found))
            jobs.extend(found)
        except Exception as exc:  # noqa: BLE001 - report and continue
            log.warning("%s failed: %s", name, type(exc).__name__)
            failures.append(name if len(name) <= 60 else name[:57] + "...")
    # The same vacancy can come from several feeds: keep the first copy per URL.
    unique: dict[str, Job] = {}
    for job in jobs:
        unique.setdefault(job.url or job.key, job)
    return list(unique.values()), failures


def run(args: argparse.Namespace) -> int:
    cfg = load_config(Path(args.config))
    profile = Profile.from_config(cfg.get("profile") or {})
    digest_cfg = cfg.get("digest") or {}
    state_path = Path(cfg.get("state_file", "data/seen.json"))
    today = date.today()

    session = make_session()
    tasks = source_tasks(cfg, session)
    if not tasks:
        log.error("No sources configured in %s", args.config)
        return 2

    jobs, failures = collect(tasks)
    seen = {} if args.ignore_state else state.load(state_path)
    new_jobs = [j for j in jobs if j.key not in seen]
    matches = rank(new_jobs, profile)[: int(digest_cfg.get("max_items", 15))]
    log.info("%d fetched, %d new, %d matched", len(jobs), len(new_jobs), len(matches))

    if args.explain:
        for job in new_jobs:
            reason = rejection_reason(job, profile) or "passed filters"
            print(f"- {job.title} | {job.company} | {job.location} -> {reason}")

    messages = telegram.build_messages(matches, today, failures, total_new=len(new_jobs))
    send_empty = bool(digest_cfg.get("send_when_empty", True))

    if args.dry_run:
        for msg in messages:
            print(msg, end="\n\n")
    elif matches or send_empty:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            log.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set (or use --dry-run)")
            return 2
        try:
            for msg in messages:
                telegram.send(session, token, chat_id, msg)
        except Exception as exc:  # noqa: BLE001 - hide details that could contain the token URL
            log.error("Sending to Telegram failed: %s", type(exc).__name__)
            return 1

    if not args.dry_run and not args.ignore_state:
        for job in new_jobs:
            seen[job.key] = today.isoformat()
        state.save(state_path, seen, today, keep_days=int(cfg.get("keep_days", 90)))

    # Fail the run only when nothing could be fetched at all, so a broken feed is visible.
    return 1 if failures and len(failures) == len(tasks) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="jobradar", description="Daily vacancy digest to Telegram")
    p.add_argument("--config", default="config.yaml", help="path to config.yaml")
    p.add_argument("--dry-run", action="store_true", help="print the digest, do not send or save state")
    p.add_argument("--ignore-state", action="store_true", help="treat every job as new, do not save state")
    p.add_argument("--explain", action="store_true", help="print why each new job passed or failed the filters")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
