#!/usr/bin/python3
"""
relevance-scorer.py

Replaces heuristic similarity scoring in skill lookup and memory retrieval
with a principled relevance score combining lexical overlap, semantic
proximity (via keyword co-occurrence), and recency weighting.

Math basis: BM25-inspired relevance with temporal decay
  score(q, d) = Σ_t IDF(t) · tf_norm(t,d) · recency(d)
  tf_norm(t,d) = tf(t,d) · (k+1) / (tf(t,d) + k·(1-b+b·|d|/avgdl))
  IDF(t)       = ln((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
  recency(d)   = exp(-λ · age_days(d))   (decay favours recent skills)

Usage:
  python3 relevance-scorer.py --query QUERY [--top 10]
  python3 relevance-scorer.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME       = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SKILLS_DIR = _RT / "skills"
ALT_SKILLS = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = CACHE_DIR / "relevance-scores.json"

# BM25 parameters
K1 = 1.5
B  = 0.75
RECENCY_LAMBDA = 0.02   # decay per day; half-life ≈ 35 days


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]{3,}", text.lower())


def _load_corpus() -> list[dict]:
    """Load all skills as documents."""
    docs = []
    now  = datetime.now(timezone.utc)
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in base.rglob("SKILL.md"):
            try:
                text  = md.read_text()[:800]
                mtime = md.stat().st_mtime
                age_d = (now.timestamp() - mtime) / 86400
                docs.append({
                    "name":    md.parent.name,
                    "tokens":  _tokenize(text),
                    "age_days": age_d,
                    "path":    str(md),
                })
            except Exception:
                pass
    return docs


def _bm25(query_tokens: list[str], docs: list[dict]) -> list[tuple[float, str]]:
    N    = len(docs)
    avgdl = sum(len(d["tokens"]) for d in docs) / max(N, 1)

    # Document frequencies
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d["tokens"]):
            df[t] = df.get(t, 0) + 1

    scores = []
    for d in docs:
        tf_map = {}
        for t in d["tokens"]:
            tf_map[t] = tf_map.get(t, 0) + 1

        dl      = len(d["tokens"])
        score   = 0.0
        for t in query_tokens:
            if t not in tf_map:
                continue
            tf  = tf_map[t]
            idf = math.log((N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1)
            tfn = tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / max(avgdl, 1)))
            score += idf * tfn

        # Recency decay
        recency = math.exp(-RECENCY_LAMBDA * d["age_days"])
        scores.append((score * recency, d["name"]))

    return sorted(scores, reverse=True)


def run(query: str, top: int, dry_run: bool) -> int:
    now  = datetime.now(timezone.utc).isoformat()
    docs = _load_corpus()

    if not docs:
        print("[relevance-scorer] No skills found")
        return 1

    q_tokens = _tokenize(query)
    ranked   = _bm25(q_tokens, docs)

    print(f"\n=== Relevance Scorer — {now[:10]} ===")
    print(f"Query:  \"{query}\"")
    print(f"Corpus: {len(docs)} skills\n")
    print(f"  {'Rank':<5} {'Score':>7}  Skill")
    print("  " + "-" * 55)

    results = []
    for rank, (score, name) in enumerate(ranked[:top], 1):
        print(f"  {rank:<5} {score:>7.3f}  {name}")
        results.append({"rank": rank, "score": round(score, 4), "name": name})

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "query": query, "results": results,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query", default="agent memory compression context")
    p.add_argument("--top",   type=int, default=10)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.query, args.top, args.dry_run))


if __name__ == "__main__":
    main()
