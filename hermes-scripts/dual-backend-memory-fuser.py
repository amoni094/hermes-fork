#!/usr/bin/python3
"""
dual-backend-memory-fuser.py

Prevents single-backend failure from starving agent context.
Fuses memory results from two backends (e.g. Obsidian + session-search,
or local skills + remote vector store) with diversity weighting —
so even if one backend returns nothing, the fused result is still useful.

Math basis: Diversity-weighted fusion (information-theoretic).
  Fused result maximises sum of relevance scores minus redundancy penalty:
    score(d) = alpha * relevance(d) + (1-alpha) * novelty(d)
  where novelty(d) = min Jaccard distance to already-selected items.

Run on-demand: /usr/bin/python3 dual-backend-memory-fuser.py <query>
"""
from __future__ import annotations
import sys, math

ALPHA = 0.60   # relevance weight (1-alpha = novelty weight)
TOP_K = 5

# Simulated backends — replace with real calls in production
def _backend_a(query: str) -> list[dict]:
    """Skill/local memory backend."""
    keywords = query.lower().split()
    pool = [
        {"id": "skill:python-debugpy",    "text": "debug python breakpoint remote",  "score": 0.88},
        {"id": "skill:systematic-debug",  "text": "root cause analysis bug trace",   "score": 0.82},
        {"id": "skill:hermes-research",   "text": "research paper sweep math ideas", "score": 0.75},
        {"id": "skill:coding-conventions","text": "code style lint review format",   "score": 0.65},
    ]
    for r in pool:
        hits = sum(1 for k in keywords if k in r["text"])
        r["score"] *= (0.7 + 0.3 * hits / max(len(keywords), 1))
    return pool

def _backend_b(query: str) -> list[dict]:
    """Session-search / episodic memory backend."""
    keywords = query.lower().split()
    pool = [
        {"id": "session:debug-2026-09-10", "text": "python debugpy error fix session",  "score": 0.80},
        {"id": "session:research-09-15",   "text": "math sweep research ideas wave",    "score": 0.78},
        {"id": "session:pr-review-09-12",  "text": "pr review github issue fix commit", "score": 0.70},
        {"id": "session:monitor-09-15",    "text": "monitor suite alarm runner fix",    "score": 0.72},
    ]
    for r in pool:
        hits = sum(1 for k in keywords if k in r["text"])
        r["score"] *= (0.7 + 0.3 * hits / max(len(keywords), 1))
    return pool

def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    inter  = len(sa & sb)
    union  = len(sa | sb)
    return inter / max(union, 1)

def fuse(query: str) -> list[dict]:
    pool_a = _backend_a(query)
    pool_b = _backend_b(query)
    all_results = {r["id"]: r for r in pool_a + pool_b}.values()

    selected: list[dict] = []
    remaining = list(all_results)

    print(f"\n=== Dual-Backend Memory Fuser ===")
    print(f"Query: {query[:60]}")
    print(f"Backend A: {len(pool_a)} results, Backend B: {len(pool_b)} results\n")
    print(f"  {'Rank':<5} {'ID':<35} {'Rel':>6} {'Nov':>6} {'Fused':>7}")
    print("  " + "-"*60)

    for rank in range(min(TOP_K, len(remaining))):
        best_id   = None
        best_fuse = -math.inf
        best_rel  = best_nov = 0.0
        for r in remaining:
            rel = r["score"]
            if not selected:
                nov = 1.0
            else:
                sims = [_jaccard(r["text"], s["text"]) for s in selected]
                nov  = 1.0 - max(sims)
            fused = ALPHA * rel + (1 - ALPHA) * nov
            if fused > best_fuse:
                best_fuse, best_id = fused, r["id"]
                best_rel, best_nov = rel, nov

        chosen = next(r for r in remaining if r["id"] == best_id)
        selected.append(chosen)
        remaining = [r for r in remaining if r["id"] != best_id]
        print(f"  {rank+1:<5} {best_id:<35} {best_rel:>6.3f} {best_nov:>6.3f} {best_fuse:>7.3f}")

    print(f"\nFused top-{len(selected)} results returned")
    return selected

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "debug python error"
    fuse(query)
