"""Build the `skills` block of config.yaml from a resume.

Usage:
    python -m jobradar.resume path/to/resume.pdf            # preview
    python -m jobradar.resume path/to/resume.pdf --write    # update config.yaml

Only infrastructure-related terms from a fixed vocabulary are picked up, so the
profile stays focused on DevOps / Cloud roles. A skill mentioned several times in
the resume is treated as a core skill and gets a higher weight.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .text import count_term
from .vocabulary import VOCABULARY

CORE_MENTIONS = 3  # mentioned at least this many times -> core skill
CORE_WEIGHT = 2
BASE_WEIGHT = 1

BEGIN = "  # BEGIN skills"
END = "  # END skills"


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # only needed for this local tool

        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return path.read_text(encoding="utf-8")


def count_skills(text: str) -> dict[str, int]:
    """Return {canonical_skill: mentions} for every vocabulary skill found in `text`."""
    lowered = text.lower()
    counts: dict[str, int] = {}
    for skill, aliases in VOCABULARY.items():
        n = sum(count_term(lowered, alias) for alias in aliases)
        if n:
            counts[skill] = n
    return counts


def to_weights(counts: dict[str, int]) -> dict[str, int]:
    weights = {s: CORE_WEIGHT if n >= CORE_MENTIONS else BASE_WEIGHT for s, n in counts.items()}
    # Core skills first, then alphabetical: easier to review in config.yaml.
    return dict(sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])))


def render_block(weights: dict[str, int], source: str) -> str:
    lines = [
        f"{BEGIN} (generated from {source} by: python -m jobradar.resume)",
        "  skills:",
    ]
    for skill, weight in weights.items():
        key = f'"{skill}"' if any(c in skill for c in "/:#") else skill
        lines.append(f"    {key}: {weight}")
    lines.append(END)
    return "\n".join(lines)


def replace_block(config_text: str, block: str) -> str:
    """Swap the generated skills block in config.yaml, keeping every comment elsewhere."""
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(config_text):
        raise ValueError(f"config has no '{BEGIN.strip()}' ... '{END.strip()}' markers")
    return pattern.sub(lambda _: block, config_text, count=1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jobradar.resume", description=__doc__.split("\n\n")[0])
    p.add_argument("resume", type=Path, help="resume as .pdf, .txt or .md")
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--write", action="store_true", help="update the skills block in the config")
    args = p.parse_args(argv)

    counts = count_skills(extract_text(args.resume))
    if not counts:
        print("No known skills found in the resume.", file=sys.stderr)
        return 1

    weights = to_weights(counts)
    block = render_block(weights, args.resume.name)
    print("Mentions: " + ", ".join(f"{s}={n}" for s, n in sorted(counts.items(), key=lambda kv: -kv[1])))
    print(block)

    if args.write:
        args.config.write_text(replace_block(args.config.read_text(encoding="utf-8"), block), encoding="utf-8")
        print(f"Updated {args.config}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
