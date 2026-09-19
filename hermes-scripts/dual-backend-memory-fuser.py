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
import sys, math, json, subprocess
from pathlib import Path

ALPHA = 0.60   # relevance weight (1-alpha = novelty weight)
TOP_K = 5

_SCRIPTS_DIR = Path(__file__).resolve().parent

# Backend A: real call to unified-recall.py (positional query arg, --json output)
def _backend_a(query: str) -> list[dict]:
    """Skill/local memory backend via unified-recall.py."""
    try:
        _proc = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "unified-recall.py"), query, "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if _proc.returncode not in (0, 1) or not _proc.stdout.strip():
            return []
        raw = json.loads(_proc.stdout)
        results = []
        for item in raw if isinstance(raw, list) else []:
            _id = item.get("id") or item.get("_md5") or item.get("memory_id") or ""
            _text = item.get("text", "")
            _score = float(item.get("rrf_score") or item.get("enriched_weight") or item.get("score", 0.0))
            if _text:
                results.append({"id": str(_id), "text": _text, "score": _score})
        return results
    except Exception:
        return []

# Backend B: real call to skill-router-index.py (--query TEXT --json)
def _backend_b(query: str) -> list[dict]:
    """Skill routing backend via skill-router-index.py."""
    try:
        _proc = subprocess.run(
            [sys.executable, str(_SCRIPTS_DIR / "skill-router-index.py"),
             "--query", query, "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if _proc.returncode != 0 or not _proc.stdout.strip():
            return []
        raw = json.loads(_proc.stdout)
        results = []
        for item in raw if isinstance(raw, list) else []:
            _id = "skill:" + item.get("name", "")
            _text = (item.get("name", "") + " " + item.get("description", "")).strip()
            _score = float(item.get("score", 0.0))
            if _text:
                results.append({"id": _id, "text": _text, "score": _score})
        return results
    except Exception:
        return []

def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    inter  = len(sa & sb)
    union  = len(sa | sb)
    return inter / max(union, 1)

def fuse(query: str) -> list[dict]:
    pool_a = _backend_a(query)
    pool_b = _backend_b(query)
    all_results = list({r["id"]: r for r in pool_a + pool_b}.values())

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
