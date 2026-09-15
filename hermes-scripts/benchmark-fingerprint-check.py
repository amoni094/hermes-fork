#!/usr/bin/env python3
"""benchmark-fingerprint-check.py — Pre-eval contamination check for Hermes paper sweeps.

arXiv: math OPTIMIZATION finding (benchmark fingerprinting hardening, 2026-09-08 sweep).

Checks whether evaluation examples in a paper interpretation queue appear verbatim (or near-
verbatim) in the Hermes skills/cache corpus, which would indicate benchmark contamination
and invalidate LLM-scored quality metrics for those papers.

Usage:
    python3 benchmark-fingerprint-check.py --queue <path-to-json>
    python3 benchmark-fingerprint-check.py --queue ~/.hermes/cache/research/cs-spike-queue.json

Exit codes:
    0 — clean (no contamination detected)
    1 — contamination detected (flagged items printed to stdout as JSON)
    2 — error

Output (JSON to stdout):
    {
        "clean": true/false,
        "checked": N,
        "flagged": [{"item_id": ..., "reason": ..., "matched_fragment": ...}],
        "corpus_size_chars": N
    }
"""
from __future__ import annotations

import json
import sys
import hashlib
import re
from pathlib import Path
from typing import Any, Optional

HERMES_DIR = Path(__import__("os").environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
SKILLS_DIR = HERMES_DIR / "skills"
CACHE_DIR = HERMES_DIR / "cache"

# Minimum fragment length to consider a match significant (avoids common short phrases).
MIN_FRAGMENT_LEN = 60
# Fraction of title/abstract words that must appear in corpus to flag contamination.
CONTAMINATION_THRESHOLD = 0.75


def _build_corpus(exclude_path: Optional[Path] = None) -> str:
    """Concatenate all SKILL.md files and cache JSON files into one searchable string.

    exclude_path: if set, skip any file whose resolved path starts with this directory.
    This prevents the queue file itself (and its siblings) from being included in the
    corpus, which would cause every queue item to self-match.
    """
    parts = []
    _exclude = exclude_path.resolve() if exclude_path else None
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        try:
            if _exclude and skill_md.resolve().is_relative_to(_exclude):
                continue
            parts.append(skill_md.read_text(errors="replace"))
        except Exception:
            pass
    for cache_json in CACHE_DIR.rglob("*.json"):
        try:
            if _exclude and cache_json.resolve().is_relative_to(_exclude):
                continue
            parts.append(cache_json.read_text(errors="replace"))
        except Exception:
            pass
    return "\n".join(parts)


def _ngrams(text: str, n: int = 6) -> set[str]:
    """Extract word n-grams from text for overlap scoring."""
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < n:
        return set(words)
    return {" ".join(words[i:i+n]) for i in range(len(words) - n + 1)}


def _check_item(item: dict[str, Any], corpus: str, corpus_lower: str) -> dict[str, Any] | None:
    """Return a contamination flag dict if the item looks contaminated, else None."""
    # Collect searchable text from the item
    fragments = []
    for field in ("title", "abstract", "rationale", "paper_title"):
        val = item.get(field)
        if isinstance(val, str) and len(val) >= MIN_FRAGMENT_LEN:
            fragments.append(val)

    if not fragments:
        return None

    for fragment in fragments:
        # Direct substring check (verbatim contamination)
        if len(fragment) >= MIN_FRAGMENT_LEN and fragment.lower() in corpus_lower:
            return {
                "item_id": item.get("arxiv_id") or item.get("id") or str(item)[:40],
                "reason": "verbatim_match",
                "matched_fragment": fragment[:120] + ("..." if len(fragment) > 120 else ""),
            }

        # N-gram overlap check (near-verbatim contamination)
        item_ngrams = _ngrams(fragment)
        if not item_ngrams:
            continue
        corpus_ngrams = _ngrams(corpus[:500_000])  # cap corpus scan for speed
        overlap = len(item_ngrams & corpus_ngrams) / len(item_ngrams)
        if overlap >= CONTAMINATION_THRESHOLD:
            return {
                "item_id": item.get("arxiv_id") or item.get("id") or str(item)[:40],
                "reason": f"ngram_overlap_{overlap:.2f}",
                "matched_fragment": fragment[:120] + ("..." if len(fragment) > 120 else ""),
            }

    return None


def check_routing_query_contamination(
    query: str,
    skills_dir: Optional[Path] = None,
    min_len: int = 40,
) -> dict[str, Any]:
    """Check whether a skill routing query matches skill-library text verbatim.

    A verbatim hit means the eval query was copied from SKILL.md content
    (contamination), which inflates routing-eval scores.
    """
    q = (query or "").strip()
    if len(q) < min_len:
        return {
            "contaminated": False,
            "reason": "query_too_short",
            "query": q,
            "matches": [],
            "match_count": 0,
        }

    root = skills_dir or SKILLS_DIR
    q_lower = q.lower()
    matches: list[str] = []
    for skill_md in root.rglob("SKILL.md"):
        try:
            text = skill_md.read_text(errors="replace")
        except Exception:
            continue
        if q_lower in text.lower():
            try:
                matches.append(str(skill_md.relative_to(root)))
            except ValueError:
                matches.append(str(skill_md))

    return {
        "contaminated": bool(matches),
        "reason": "verbatim_skill_library_match" if matches else "clean",
        "query": q[:200],
        "matches": matches[:20],
        "match_count": len(matches),
    }


def run(queue_path: Path) -> dict[str, Any]:
    queue = json.loads(queue_path.read_text())
    if isinstance(queue, dict):
        items = queue.get("items") or list(queue.values())
    elif isinstance(queue, list):
        items = queue
    else:
        return {"error": f"Unrecognised queue format: {type(queue)}"}

    corpus = _build_corpus(exclude_path=queue_path.parent)
    corpus_lower = corpus.lower()

    flagged = []
    for item in items:
        if not isinstance(item, dict):
            continue
        flag = _check_item(item, corpus, corpus_lower)
        if flag:
            flagged.append(flag)

    return {
        "clean": len(flagged) == 0,
        "checked": len(items),
        "flagged": flagged,
        "corpus_size_chars": len(corpus),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark fingerprint contamination check")
    parser.add_argument("--queue", help="Path to spike/interpretation queue JSON")
    parser.add_argument(
        "--routing-query",
        default=None,
        help="Check a skill-routing query for verbatim skill-library contamination",
    )
    args = parser.parse_args()

    if args.routing_query:
        result = check_routing_query_contamination(args.routing_query)
        print(json.dumps(result, indent=2))
        if result.get("contaminated"):
            return 1
        return 0

    if not args.queue:
        parser.error("either --queue or --routing-query is required")

    queue_path = Path(args.queue).expanduser()
    if not queue_path.exists():
        print(json.dumps({"error": f"Queue file not found: {queue_path}"}))
        return 2

    result = run(queue_path)
    print(json.dumps(result, indent=2))
    if "error" in result:
        return 2
    return 0 if result.get("clean") else 1


if __name__ == "__main__":
    sys.exit(main())
