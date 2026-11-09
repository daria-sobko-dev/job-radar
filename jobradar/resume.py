"""Build a profile's `skills` block in config.yaml from a resume.

Usage:
    python -m jobradar.resume resume.pdf                          # preview, devops profile
    python -m jobradar.resume resume.pdf --profile web            # preview, web profile
    python -m jobradar.resume resume.pdf --profile devops --write # update config.yaml

Each profile has its own vocabulary (see jobradar/vocabulary.py), so a DevOps
profile picks up only infrastructure skills and a web profile only web skills.
A skill mentioned several times in the resume is treated as a core skill and
gets a higher weight.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .text import count_term
from .vocabulary import VOCABULARIES

CORE_MENTIONS = 3  # mentioned at least this many times -> core skill
CORE_WEIGHT = 2
BASE_WEIGHT = 1


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # only needed for this local tool

        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    return path.read_text(encoding="utf-8")


def count_skills(text: str, vocabulary: dict[str, list[str]] | None = None) -> dict[str, int]:
    """Return {canonical_skill: mentions} for every vocabulary skill found in `text`."""
    vocabulary = vocabulary or VOCABULARIES["devops"]
    lowered = text.lower()
    counts: dict[str, int] = {}
    for skill, aliases in vocabulary.items():
        n = sum(count_term(lowered, alias) for alias in aliases)
        if n:
            counts[skill] = n
    return counts


def to_weights(counts: dict[str, int]) -> dict[str, int]:
    weights = {s: CORE_WEIGHT if n >= CORE_MENTIONS else BASE_WEIGHT for s, n in counts.items()}
    # Core skills first, then alphabetical: easier to review in config.yaml.
    return dict(sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])))


def _markers(profile: str) -> re.Pattern[str]:
    return re.compile(
        rf"^(?P<indent>[ \t]*)# BEGIN skills {re.escape(profile)}\b.*?^[ \t]*# END skills {re.escape(profile)}\b[^\n]*",
        re.DOTALL | re.MULTILINE,
    )


def render_block(weights: dict[str, int], source: str, profile: str = "devops", indent: str = "    ") -> str:
    lines = [
        f"{indent}# BEGIN skills {profile} (generated from {source} by: python -m jobradar.resume)",
        f"{indent}skills:",
    ]
    for skill, weight in weights.items():
        key = f'"{skill}"' if any(c in skill for c in "/:#") else skill
        lines.append(f"{indent}  {key}: {weight}")
    lines.append(f"{indent}# END skills {profile}")
    return "\n".join(lines)


def replace_block(config_text: str, weights: dict[str, int], source: str, profile: str = "devops") -> str:
    """Swap one profile's generated skills block, keeping every comment elsewhere."""
    match = _markers(profile).search(config_text)
    if not match:
        raise ValueError(f"config has no '# BEGIN skills {profile}' ... '# END skills {profile}' markers")
    block = render_block(weights, source, profile, match.group("indent"))
    return config_text[: match.start()] + block + config_text[match.end() :]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jobradar.resume", description=__doc__.split("\n\n")[0])
    p.add_argument("resume", type=Path, help="resume as .pdf, .txt or .md")
    p.add_argument("--profile", default="devops", choices=sorted(VOCABULARIES), help="which profile to update")
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--write", action="store_true", help="update the skills block in the config")
    args = p.parse_args(argv)

    counts = count_skills(extract_text(args.resume), VOCABULARIES[args.profile])
    if not counts:
        print("No known skills found in the resume.", file=sys.stderr)
        return 1

    weights = to_weights(counts)
    print("Mentions: " + ", ".join(f"{s}={n}" for s, n in sorted(counts.items(), key=lambda kv: -kv[1])))
    print(render_block(weights, args.resume.name, args.profile))

    if args.write:
        text = args.config.read_text(encoding="utf-8")
        args.config.write_text(replace_block(text, weights, args.resume.name, args.profile), encoding="utf-8")
        print(f"Updated profile '{args.profile}' in {args.config}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
