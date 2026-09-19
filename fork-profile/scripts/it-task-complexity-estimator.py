#!/usr/bin/python3
"""Information-theoretic task complexity estimator (Cover & Thomas AEP).

For each session's first user message, compute character-level Shannon entropy

    H(X) = -∑ p(x) log2 p(x)

where p is the empirical unigram over Unicode characters (Cover & Thomas 2nd ed,
eq. 2.1 / Ch 2). Under the AEP (Ch 3), a typical n-character string occupies a
set of size ≈ 2^{nH}: low H ⇒ stereotyped / compressible prompts (mechanical
extract/triage); high H ⇒ more uniform, novel, or cross-domain wording.

Routing tiers (bits/char):
  H < 3.5          low-entropy     mechanical/extract/triage → mistral-small aux
  3.5 ≤ H < 4.2    medium-entropy  standard research/coding  → sonnet-parent
  H ≥ 4.2          high-entropy    novel/cross-domain        → grok workers or deepseek

Usage:
  /usr/bin/python3 it-task-complexity-estimator.py
  /usr/bin/python3 it-task-complexity-estimator.py --last 20
  /usr/bin/python3 it-task-complexity-estimator.py --dry-run

Stdout: JSON list of {session_id, entropy, tier, recommended_route}.
Always emits one ALARM line. Requires numpy; stdlib otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

HOME = Path.home()
SESSIONS_DIR = HOME / ".hermes" / "sessions"
FORK_SESSIONS = HOME / ".hermes" / "profiles" / "fork" / "sessions"
HERMES_HOME = Path(
    os.environ.get("HERMES_HOME", str(HOME / ".hermes" / "profiles" / "fork"))
)
CACHE_DIR = HERMES_HOME / "cache" / "monitors"
OUT_FILE = CACHE_DIR / "it-task-complexity.json"

MIN_SESSIONS = 3
LOW_H = 3.5
HIGH_H = 4.2

TIER_LOW = "low-entropy"
TIER_MED = "medium-entropy"
TIER_HIGH = "high-entropy"
ROUTE_LOW = "mistral-small aux"
ROUTE_MED = "sonnet-parent"
ROUTE_HIGH = "grok workers or deepseek"


def _message_text(content: object) -> str:
    """Flatten a Hermes message content field to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in (None, "text"):
                    parts.append(str(block.get("text") or block.get("content") or ""))
        return "\n".join(parts)
    return str(content)


def first_user_message(path: Path) -> str | None:
    """Return the first role=user text in a session JSONL, or None."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        text = _message_text(msg.get("content")).strip()
        if text:
            return text
    return None


def char_entropy(text: str) -> float:
    """Empirical character unigram entropy H = -∑ p log2 p (bits/char).

    Empty string has no distribution; return 0.0 so it classifies as low-entropy.
    """
    if not text:
        return 0.0
    arr = np.array(list(text))
    _, counts = np.unique(arr, return_counts=True)
    p = counts.astype(np.float64) / float(counts.sum())
    # p_i > 0 by construction of unique counts; no 0-log issue.
    return float(-np.sum(p * np.log2(p)))


def classify(entropy: float) -> tuple[str, str]:
    """Map H (bits/char) to (tier, recommended_route)."""
    if entropy < LOW_H:
        return TIER_LOW, ROUTE_LOW
    if entropy < HIGH_H:
        return TIER_MED, ROUTE_MED
    return TIER_HIGH, ROUTE_HIGH


def list_session_files() -> list[Path]:
    """Session JSONL files from default and fork profiles, oldest first."""
    files: list[Path] = []
    for directory in (SESSIONS_DIR, FORK_SESSIONS):
        if directory.exists():
            files.extend(directory.glob("*.jsonl"))
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def estimate_sessions(files: list[Path]) -> list[dict]:
    """Build one report row per session that has a first user message."""
    report: list[dict] = []
    for path in files:
        text = first_user_message(path)
        if text is None:
            continue
        entropy = char_entropy(text)
        tier, route = classify(entropy)
        report.append(
            {
                "session_id": path.stem,
                "entropy": round(entropy, 6),
                "tier": tier,
                "recommended_route": route,
            }
        )
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate per-session task complexity from first-user-message entropy."
    )
    parser.add_argument(
        "--last",
        type=int,
        default=None,
        metavar="N",
        help="Analyze last N sessions by mtime (after the insufficient-data check).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output without writing cache files",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    files = list_session_files()

    if len(files) < MIN_SESSIONS:
        print("[]")
        print("ALARM: no -- insufficient data")
        return 0

    if args.last is not None:
        if args.last < 1:
            print("[]", file=sys.stderr)
            print("ALARM: no -- insufficient data")
            return 2
        files = files[-args.last :]

    report = estimate_sessions(files)
    payload = json.dumps(report, indent=2)
    print(payload)

    if not args.dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(payload + "\n", encoding="utf-8")

    print(f"ALARM: no -- {len(report)} session(s) classified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
