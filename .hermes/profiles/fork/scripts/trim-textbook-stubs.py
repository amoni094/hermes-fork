#!/usr/bin/env python3
"""Trim generic textbook-stub boilerplate suffixes from hybrid SKILL.md files."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SKILLS_ROOT = Path("/var/home/rainbow/.hermes/profiles/fork/skills")
STUB_LINE = "<!-- textbook-stub: see source PDF -->"

BOILERPLATE_MARKERS = [
    "## Hermes Relevance",
    "- Core definitions, theorems, and proofs in the domain",
    "- Applying asymptotic results outside their regime",
    "Source: ",
    "<!-- textbook-stub",
]

OPERATIONAL_MARKERS = [
    "## Procedure",
    "## Pitfalls",
    "## When to Use",
    "## Commands",
    "## Causal Claim Detection Gate",
    "## Routing Rules",
    "## Operational Summary",
    "## Algorithm",
    "## Lessons",
    "## Decision rules",
    "## Script",
    "## Steps",
    "## Usage",
]


def line_has_boilerplate(line: str) -> bool:
    for marker in BOILERPLATE_MARKERS:
        if marker not in line:
            continue
        # Operational skills cite arXiv/papers with "Source: " at the top.
        # Textbook stubs use "Source: <file>.pdf (N lines)" as a suffix.
        if marker == "Source: " and ".pdf" not in line:
            continue
        return True
    return False


def first_boilerplate_index(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if line_has_boilerplate(line):
            return i
    return None


def has_operational_after(lines: list[str], idx: int) -> bool:
    for line in lines[idx + 1 :]:
        for marker in OPERATIONAL_MARKERS:
            if marker in line:
                return True
    return False


def planned_content(text: str) -> tuple[str | None, str | None, int]:
    """Return (new_text, skip_reason, lines_removed). new_text is None if skip."""
    lines = text.splitlines(keepends=True)
    idx = first_boilerplate_index(lines)
    if idx is None:
        return None, "no boilerplate marker", 0
    if has_operational_after(lines, idx):
        return None, "operational content after boilerplate marker", 0
    kept = "".join(lines[:idx])
    if kept and not kept.endswith("\n"):
        kept += "\n"
    new_text = kept + STUB_LINE + "\n"
    if new_text == text:
        return None, "already trimmed", 0
    removed = len(lines) - idx
    # If original lacked a trailing newline, splitlines may undercount the stub swap.
    return new_text, None, removed


def iter_skill_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("SKILL.md") if p.is_file())


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default is dry-run)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=SKILLS_ROOT,
        help="Skills root to walk",
    )
    args = parser.parse_args(argv)

    root = args.root
    if not root.is_dir():
        print(f"ERROR: skills root missing: {root}", file=sys.stderr)
        return 2

    to_modify: list[tuple[Path, str, int]] = []
    skipped_operational = 0
    skipped_none = 0
    skipped_already = 0

    for path in iter_skill_files(root):
        text = path.read_text(encoding="utf-8")
        new_text, reason, removed = planned_content(text)
        if new_text is None:
            if reason == "operational content after boilerplate marker":
                skipped_operational += 1
                print(f"WARN: skip {path} ({reason})", file=sys.stderr)
            elif reason == "already trimmed":
                skipped_already += 1
            else:
                skipped_none += 1
            continue
        to_modify.append((path, new_text, removed))

    mode = "APPLY" if args.apply else "DRY-RUN"
    for path, new_text, removed in to_modify:
        rel = path
        if args.apply:
            atomic_write(path, new_text)
            print(f"TRIMMED: {rel} (removed {removed} lines)")
        else:
            print(f"WOULD TRIM: {rel} (removed {removed} lines)")

    total_removed = sum(r for _, _, r in to_modify)
    print(
        f"{mode}: files to modify: {len(to_modify)}; "
        f"total lines removed: {total_removed}; "
        f"skipped_no_marker: {skipped_none}; "
        f"skipped_operational_after: {skipped_operational}; "
        f"skipped_already: {skipped_already}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
