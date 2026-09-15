#!/usr/bin/env python3
"""Lexical redundancy gate for MEMORY.md / USER.md (not Hindsight, not Shannon).

Checks a candidate fact against existing durable-memory files and returns
WRITE or SUPPRESS based on TF cosine overlap.

This does NOT query Hindsight and is not a Shannon channel-capacity result.
Shannon redundancy R = 1 − H/H_max is not computed. Cosine TF overlap is a
cheap lexical proxy: high overlap with an existing chunk → likely duplicate
prose, not a proof of zero information gain.

Usage:
    python3 memory-redundancy-gate.py "The user prefers concise responses"
    python3 memory-redundancy-gate.py --threshold 0.88 "fact text"

Output JSON:
    {"verdict": "WRITE"|"SUPPRESS", "redundancy": float, "nearest": str,
     "reason": str, "info_gain": float, "residual": float}

Exit codes: 0 = evaluated (read verdict in JSON), 2 = usage/IO error.
SUPPRESS is not a process failure.

Not wired into hindsight_retain. Callers that write MEMORY.md/USER.md may
consult the JSON before appending.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SUPPRESS_THRESHOLD = 0.88  # TF cosine above which we suppress


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _tf_vec(tokens: list[str]) -> dict[str, float]:
    """Normalised term frequency (not TF-IDF)."""
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * v for k, v in b.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))


def _hilbert_residual(x: dict[str, float], y: dict[str, float]) -> float:
    """Relative residual after projecting x onto y (Kreyszig inner-product space)."""
    dyy = _dot(y, y)
    proj_scale = _dot(x, y) / dyy if dyy > 0 else 0.0
    residual_vec = {k: x.get(k, 0.0) - proj_scale * y.get(k, 0.0) for k in set(x) | set(y)}
    norm_r = math.sqrt(sum(v * v for v in residual_vec.values()))
    norm_x = math.sqrt(sum(v * v for v in x.values()))
    return norm_r / norm_x if norm_x > 0 else 1.0


def _split_facts(text: str) -> list[str]:
    """Split durable memory the way learning_graph does: bare §, then paragraphs."""
    chunks: list[str] = []
    parts = re.split(r"\n?\s*§\s*\n?", text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        paras = [p.strip() for p in re.split(r"\n{2,}", part) if p.strip()]
        if len(paras) > 1:
            chunks.extend(paras)
        else:
            chunks.append(part)
    return chunks


def _load_memory_facts() -> list[str]:
    """Load fact chunks from MEMORY.md and USER.md (not Hindsight)."""
    facts: list[str] = []
    mem_dir = HERMES_HOME / "memories"
    for fname in ("MEMORY.md", "USER.md"):
        fpath = mem_dir / fname
        if not fpath.exists():
            continue
        try:
            fpath.resolve().relative_to(mem_dir.resolve())
        except (OSError, ValueError):
            continue
        try:
            facts.extend(_split_facts(fpath.read_text(encoding="utf-8")))
        except (OSError, UnicodeError):
            continue
    return facts


def check_redundancy(
    candidate: str, existing_facts: list[str], threshold: float = SUPPRESS_THRESHOLD
) -> dict:
    """Check lexical overlap of candidate against existing memory chunks."""
    if not candidate or not candidate.strip():
        return {
            "verdict": "SUPPRESS",
            "redundancy": 0.0,
            "info_gain": 0.0,
            "nearest": "",
            "residual": 1.0,
            "reason": "Empty candidate — refusing to write an empty fact",
        }

    if not existing_facts:
        return {
            "verdict": "WRITE",
            "redundancy": 0.0,
            "info_gain": 1.0,
            "nearest": "",
            "residual": 1.0,
            "reason": "No existing MEMORY.md/USER.md chunks to compare against",
        }

    cand_tokens = _tokenize(candidate)
    cand_vec = _tf_vec(cand_tokens)
    if not cand_vec:
        return {
            "verdict": "SUPPRESS",
            "redundancy": 0.0,
            "info_gain": 0.0,
            "nearest": "",
            "residual": 1.0,
            "reason": "Candidate has no lexical tokens — too short to evaluate; not writing",
        }
    cand_set = set(cand_tokens)

    best_sim = 0.0
    nearest = ""
    min_residual = 1.0
    for fact in existing_facts:
        if not isinstance(fact, str):
            continue
        fact_tokens = _tokenize(fact)
        fact_vec = _tf_vec(fact_tokens)
        if not fact_vec:
            continue
        cosine = _cosine(cand_vec, fact_vec)
        # Coverage: fraction of candidate types already present in this chunk.
        # Catches prefixes/subsets that TF cosine under-scores against a long fact.
        coverage = len(cand_set & set(fact_tokens)) / max(len(cand_set), 1)
        sim = max(cosine, coverage)
        residual = _hilbert_residual(cand_vec, fact_vec)
        if residual < min_residual:
            min_residual = residual
        if sim > best_sim:
            best_sim = sim
            nearest = fact[:120]

    # Proxy only: 1 - cosine is not Shannon information gain.
    info_gain = 1.0 - best_sim
    threshold = min(max(threshold, 0.0), 1.0)

    if best_sim >= threshold:
        return {
            "verdict": "SUPPRESS",
            "redundancy": round(best_sim, 4),
            "info_gain": round(info_gain, 4),
            "nearest": nearest,
            "residual": round(min_residual, 4),
            "reason": (
                f"TF cosine {best_sim:.3f} >= threshold {threshold:.3f}. "
                f"Lexical overlap with an existing MEMORY.md/USER.md chunk; "
                f"not a Shannon redundancy measurement."
            ),
        }
    return {
        "verdict": "WRITE",
        "redundancy": round(best_sim, 4),
        "info_gain": round(info_gain, 4),
        "nearest": nearest,
        "residual": round(min_residual, 4),
        "reason": (
            f"TF cosine {best_sim:.3f} < threshold {threshold:.3f}. "
            f"Lexical overlap is below the gate; this is not proof of novelty."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MEMORY.md/USER.md lexical redundancy gate")
    parser.add_argument("fact", help="Candidate memory fact to evaluate")
    parser.add_argument(
        "--threshold", type=float, default=SUPPRESS_THRESHOLD,
        help=f"TF cosine threshold for suppression (default {SUPPRESS_THRESHOLD})",
    )
    parser.add_argument(
        "--facts-json",
        help="Path to JSON array of existing fact strings (default: MEMORY.md + USER.md)",
    )
    args = parser.parse_args()

    if args.facts_json:
        try:
            existing = json.loads(Path(args.facts_json).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as e:
            print(json.dumps({"error": f"Could not read --facts-json: {e}"}))
            sys.exit(2)
        if not isinstance(existing, list):
            print(json.dumps({"error": "--facts-json must be a JSON array"}))
            sys.exit(2)
    else:
        existing = _load_memory_facts()

    result = check_redundancy(args.fact, existing, threshold=args.threshold)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
