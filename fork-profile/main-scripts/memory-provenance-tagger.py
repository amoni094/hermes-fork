#!/usr/bin/env python3
"""
memory-provenance-tagger.py — Provenance attestation for Hindsight staging facts
arXiv:2609.21088 — Origin Is All You Need: Provenance-Aware Transformers

Reads ~/.hermes/memory-facts/staging.md.
For each fact line (starting with - or *) without a [source=...] tag:
  Infers source type from content keywords.
  Appends [source=TYPE] [trust=LEVEL] to the line.
Writes back to staging.md. Logs changes.

Trust tiers:
  user     = high   (direct user statement)
  internal = high   (agent reasoning, session-derived)
  cron     = medium (automated job output)
  external = low    (web, papers, third-party)
"""
import sys
import re
import json
import os
import datetime
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
STAGING_PATH = _HERMES_HOME / "memory-facts/staging.md"
PROV_LOG = _HERMES_HOME / "profiles/fork/logs/provenance-tagging.jsonl"
PROV_LOG.parent.mkdir(parents=True, exist_ok=True)

# Source inference rules (checked in order — first match wins)
SOURCE_RULES = [
    ("user",     ["user said", "user prefers", "user reported", "user asked",
                  "user confirmed", "user wants", "user noted", "user chose"]),
    ("cron",     ["cron", "scheduled", "sweep", "nightly", "automated", "monitor",
                  "watchdog", "daily", "hourly"]),
    ("external", ["arxiv:", "arxiv.org", "paper", "study", "research", "github.com",
                  "2609.", "2608.", "2607.", "web_extract", "web_search", "published"]),
]
DEFAULT_SOURCE = "internal"

TRUST_MAP = {
    "user": "high",
    "internal": "high",
    "cron": "medium",
    "external": "low",
}

TAG_PATTERN = re.compile(r'\[source=[^\]]+\]')
FACT_LINE_PATTERN = re.compile(r'^(\s*[-*]\s+)')


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _infer_source(text: str) -> str:
    lower = text.lower()
    for source_type, signals in SOURCE_RULES:
        for signal in signals:
            if signal.lower() in lower:
                return source_type
    return DEFAULT_SOURCE


# Quality signal from information partition theory: finer partitions (more specific tags) -> higher utility
def _compute_partition_quality(fact_text: str, tags: list) -> float:
    """Return 0.0–1.0 quality from provenance tags (arXiv:2609.12210)."""
    del fact_text  # signature required; quality is a function of the tag partition
    if not tags:
        return 0.0
    norm = [str(t).strip().lower() for t in tags if t is not None and str(t).strip()]
    if not norm or all(t == "unknown" for t in norm):
        return 0.0
    unique = {t for t in norm if t != "unknown"}
    if len(unique) >= 2:
        return 1.0  # corroboration: multiple sources agree
    tag = next(iter(unique), "unknown")
    if tag in ("cron", "session", "internal", "user"):
        return 0.6
    return 0.3  # external (or other) with no corroboration


def _persist_quality_score(label: str, quality: float) -> None:
    """Store quality in lifecycle.db when quality_score exists. Fail silently otherwise."""
    try:
        import sqlite3

        db = _HERMES_HOME / "memory-facts" / "lifecycle.db"
        if not db.exists():
            return
        con = sqlite3.connect(str(db))
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(fact_lifecycle)").fetchall()}
            if "quality_score" not in cols:
                return
            con.execute(
                "UPDATE fact_lifecycle SET quality_score=? WHERE label=?",
                (quality, label),
            )
            con.commit()
        finally:
            con.close()
    except Exception:
        pass


def main() -> None:
    if not STAGING_PATH.exists():
        print("memory-provenance-tagger: staging.md not found, skipping")
        sys.exit(0)

    try:
        original = STAGING_PATH.read_text()
    except OSError as e:
        print(f"memory-provenance-tagger: cannot read staging.md: {e}", file=sys.stderr)
        return

    lines = original.splitlines(keepends=True)
    new_lines = []
    changes: list[dict] = []

    for i, line in enumerate(lines):
        # Only process fact lines (- or *)
        match = FACT_LINE_PATTERN.match(line)
        if match and not TAG_PATTERN.search(line):
            source_type = _infer_source(line)
            trust = TRUST_MAP[source_type]
            tag = f" [source={source_type}] [trust={trust}]"
            # Insert before the newline
            stripped = line.rstrip("\n")
            new_line = stripped + tag + "\n"
            new_lines.append(new_line)
            matched_tags = []
            lower = line.lower()
            for stype, signals in SOURCE_RULES:
                if any(sig.lower() in lower for sig in signals):
                    matched_tags.append(stype)
            if not matched_tags:
                matched_tags = [source_type]
            quality = _compute_partition_quality(stripped, matched_tags)
            _persist_quality_score(stripped, quality)
            changes.append({
                "line": i + 1,
                "source": source_type,
                "trust": trust,
                "quality": quality,
                "preview": stripped[:60],
            })
        else:
            new_lines.append(line)

    if changes:
        try:
            # Atomic write via tmp+rename (prevents corrupt staging.md on crash)
            _tmp = STAGING_PATH.with_suffix(".tmp")
            _tmp.write_text("".join(new_lines))
            _tmp.rename(STAGING_PATH)
        except OSError as e:
            print(f"memory-provenance-tagger: cannot write staging.md: {e}", file=sys.stderr)
            return

        log_entry = {
            "ts": _now_iso(),
            "tagged_facts": len(changes),
            "changes": changes[:50],  # cap
        }
        try:
            with PROV_LOG.open("a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except OSError:
            pass

        print(f"memory-provenance-tagger: tagged {len(changes)} facts with provenance")
    else:
        print("memory-provenance-tagger: all facts already tagged, no changes")


if __name__ == "__main__":
    main()
