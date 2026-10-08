#!/usr/bin/env python3
"""
memory-staleness.py — Typed memory staleness detector for Hermes MEMORY.md.

Based on:
  arXiv:2606.24775 — agent-native memory taxonomy (typed memory tags)
  arXiv:2608.07440 — Blast Radius reversible eviction (staleness + STALE flag)

Usage:
    python ~/.hermes/scripts/memory-staleness.py

Output: compact per-section report with section number, type tag, status
        (STALE / ACTIVE / UNKNOWN), and reason.
"""

import os
import re
import sys
from datetime import date, datetime

MEMORY_PATH = os.path.expanduser("~/.hermes/memories/MEMORY.md")
STALE_DAYS = 30

# Month name → number (for "Month YYYY" pattern)
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Patterns for dates
RE_ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RE_MONTH_YYYY = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+(\d{4})\b",
    re.IGNORECASE,
)

# Patterns for file paths
RE_FILE_PATH = re.compile(r"(~[^\s,;:)\"']+|/var/home/[^\s,;:)\"']+)")

# Typed tag pattern
RE_TAG = re.compile(r"^\[(factual|procedural|preference|correction|reference)\]")


def parse_sections(text: str) -> list[str]:
    """Split MEMORY.md on lines that contain only '§'."""
    sections = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "§":
            sections.append("\n".join(current).strip())
            current = []
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]  # drop empty


def extract_dates(text: str) -> list[date]:
    """Extract all recognisable dates from a section."""
    found: list[date] = []

    for m in RE_ISO.finditer(text):
        try:
            found.append(datetime.strptime(m.group(1), "%Y-%m-%d").date())
        except ValueError:
            pass

    for m in RE_MONTH_YYYY.finditer(text):
        month_str = m.group(1)[:3].lower()
        year = int(m.group(2))
        month = MONTH_MAP.get(month_str)
        if month:
            try:
                found.append(date(year, month, 1))
            except ValueError:
                pass

    return found


def extract_paths(text: str) -> list[str]:
    """Extract file/directory paths from a section."""
    paths = []
    for m in RE_FILE_PATH.finditer(text):
        raw = m.group(1).rstrip(".,;:)'\"")
        expanded = os.path.expanduser(raw)
        paths.append(expanded)
    return paths


def classify_section(idx: int, section: str) -> dict:
    """Return a dict describing staleness status for one section."""
    tag_match = RE_TAG.match(section)
    tag = tag_match.group(1) if tag_match else None

    today = date.today()
    status = "UNKNOWN"
    reasons: list[str] = []

    # ── Date staleness check ──────────────────────────────────────────────
    dates = extract_dates(section)
    if dates:
        oldest = min(dates)
        newest = max(dates)
        age_days = (today - newest).days
        if age_days > STALE_DAYS:
            status = "STALE"
            reasons.append(
                f"newest date {newest} is {age_days}d old (>{STALE_DAYS}d threshold)"
            )
        else:
            status = "ACTIVE"
            reasons.append(f"newest date {newest} is {age_days}d old")
    else:
        reasons.append("no dates found")

    # ── File path existence check ─────────────────────────────────────────
    paths = extract_paths(section)
    missing: list[str] = []
    present: list[str] = []
    for p in paths:
        # Skip URLs, GitHub refs, bare filenames without slashes
        if not p.startswith("/"):
            continue
        if os.path.exists(p):
            present.append(p)
        else:
            missing.append(p)

    if missing:
        status = "STALE"
        reasons.append(f"missing path(s): {', '.join(missing)}")
    if present:
        reasons.append(f"path(s) exist: {', '.join(present)}")

    # If no dates and no paths, leave UNKNOWN
    if status == "UNKNOWN" and not paths and not dates:
        pass  # UNKNOWN stays

    return {
        "section": idx + 1,
        "tag": tag or "(none)",
        "status": status,
        "reasons": reasons,
        "preview": section[:80].replace("\n", " "),
    }


def main():
    if not os.path.exists(MEMORY_PATH):
        print(f"ERROR: {MEMORY_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    with open(MEMORY_PATH, "r", encoding="utf-8") as fh:
        text = fh.read()

    sections = parse_sections(text)
    if not sections:
        print("No sections found in MEMORY.md.")
        return

    today = date.today()
    print(f"Hermes memory staleness report — {today}  (threshold: {STALE_DAYS} days)")
    print(f"File: {MEMORY_PATH}")
    print(f"Sections found: {len(sections)}")
    print("─" * 70)

    for sec in sections:
        result = classify_section(sections.index(sec), sec)
        tag_col = f"[{result['tag']}]" if result["tag"] != "(none)" else "(untagged)"
        reason_str = "; ".join(result["reasons"])
        status_icon = {"STALE": "⚠ STALE", "ACTIVE": "✓ ACTIVE", "UNKNOWN": "? UNKNOWN"}[
            result["status"]
        ]
        print(
            f"§{result['section']:02d}  {tag_col:<14}  {status_icon:<12}  {reason_str}"
        )
        print(f"     preview: {result['preview']!r}")
        print()

    stale_count = sum(1 for s in sections if classify_section(sections.index(s), s)["status"] == "STALE")
    active_count = sum(1 for s in sections if classify_section(sections.index(s), s)["status"] == "ACTIVE")
    unknown_count = len(sections) - stale_count - active_count
    print("─" * 70)
    print(f"Summary: {active_count} ACTIVE  |  {stale_count} STALE  |  {unknown_count} UNKNOWN")
    if stale_count:
        print("Action: review STALE sections — update facts, correct paths, or evict.")


if __name__ == "__main__":
    main()
