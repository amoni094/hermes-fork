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

import json
import math
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

MEMORY_PATH = os.path.expanduser("~/.hermes/memories/MEMORY.md")
STALE_DAYS = 30
REF_FREQUENT_MIN = 2
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / "cache"
STOPWORDS = {
    "that", "this", "with", "from", "have", "been", "were", "they", "them",
    "then", "than", "also", "into", "over", "only", "some", "such", "when",
    "what", "which", "while", "where", "your", "about", "after", "before",
    "using", "used", "must", "should", "would", "could", "there", "their",
    "hermes", "none", "true", "false", "null", "path", "file", "files",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{3,}")

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


def key_terms(section: str, n: int = 10) -> list:
    counts = {}
    for tok in TOKEN_RE.findall(section or ""):
        low = tok.lower()
        if low in STOPWORDS or low.isdigit():
            continue
        counts[low] = counts.get(low, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:n]]


def load_reference_corpus() -> str:
    """Session-history proxy: top-level JSON files under profile cache."""
    cache_dir = _hermes_root / "cache"
    parts = []
    try:
        for p in sorted(cache_dir.glob("*.json")):
            try:
                parts.append(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    except OSError:
        return ""
    return "\n".join(parts).lower()


def count_references(section: str, corpus: str) -> int:
    if not corpus:
        return 0
    total = 0
    for t in key_terms(section):
        total += corpus.count(t)
    return total


def classify_section(idx: int, section: str, corpus: str = "") -> dict:
    """Return a dict describing staleness status for one section."""
    tag_match = RE_TAG.match(section)
    tag = tag_match.group(1) if tag_match else None

    today = date.today()
    status = "UNKNOWN"
    reasons: list[str] = []
    ref_freq = count_references(section, corpus)
    recommended_ttl = int(STALE_DAYS * (1.0 + math.log(1.0 + ref_freq)))

    # ── Date staleness check ──────────────────────────────────────────────
    dates = extract_dates(section)
    if dates:
        oldest = min(dates)
        newest = max(dates)
        age_days = (today - newest).days
        if age_days > recommended_ttl:
            status = "STALE"
            reasons.append(
                f"newest date {newest} is {age_days}d old (>Bayesian TTL {recommended_ttl}d, refs={ref_freq})"
            )
        else:
            status = "ACTIVE"
            reasons.append(
                f"newest date {newest} is {age_days}d old (Bayesian TTL {recommended_ttl}d, refs={ref_freq})"
            )
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

    # Berger: a frequently referenced undated fact is stable, not unknown.
    if status == "UNKNOWN" and ref_freq >= REF_FREQUENT_MIN:
        status = "ACTIVE"
        reasons.append(
            "no dates but reference_frequency=%d (>=%d) => ACTIVE"
            % (ref_freq, REF_FREQUENT_MIN)
        )

    first = (section.splitlines()[0].strip() if section else "")[:120]
    return {
        "section": idx + 1,
        "tag": tag or "(none)",
        "status": status,
        "reasons": reasons,
        "preview": section[:80].replace("\n", " "),
        "reference_frequency": ref_freq,
        "recommended_ttl_days": recommended_ttl,
        "key": first or f"section-{idx + 1}",
        "title": first or f"section-{idx + 1}",
        "name": tag or first or f"section-{idx + 1}",
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

    corpus = load_reference_corpus()
    today = date.today()
    print(f"Hermes memory staleness report — {today}  (threshold: {STALE_DAYS} days)")
    print(f"File: {MEMORY_PATH}")
    print(f"Sections found: {len(sections)}")
    print("─" * 70)

    classified = [classify_section(i, sec, corpus) for i, sec in enumerate(sections)]
    for result in classified:
        tag_col = f"[{result['tag']}]" if result["tag"] != "(none)" else "(untagged)"
        reason_str = "; ".join(result["reasons"])
        status_icon = {"STALE": "⚠ STALE", "ACTIVE": "✓ ACTIVE", "UNKNOWN": "? UNKNOWN"}[
            result["status"]
        ]
        print(
            f"§{result['section']:02d}  {tag_col:<14}  {status_icon:<12}  refs={result['reference_frequency']:<4}  ttl={result['recommended_ttl_days']}d  {reason_str}"
        )
        print(f"     preview: {result['preview']!r}")
        print()

    stale_count = sum(1 for r in classified if r["status"] == "STALE")
    active_count = sum(1 for r in classified if r["status"] == "ACTIVE")
    unknown_count = len(sections) - stale_count - active_count
    print("─" * 70)
    print(f"Summary: {active_count} ACTIVE  |  {stale_count} STALE  |  {unknown_count} UNKNOWN")
    if stale_count:
        print("Action: review STALE sections — update facts, correct paths, or evict.")

    CACHE.mkdir(parents=True, exist_ok=True)
    out_path = CACHE / "memory-staleness.json"
    out_path.write_text(json.dumps({
        "sections": classified,
        "ts": datetime.now(timezone.utc).isoformat(),
    }, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
