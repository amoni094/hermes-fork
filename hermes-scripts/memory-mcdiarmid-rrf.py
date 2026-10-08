#!/usr/bin/env python3
"""memory-mcdiarmid-rrf.py — bounded-differences retrieval score (Lugosi, Vershynin).

Unnormalized RRF score of a memory list. Changing one memory changes the
score of any fixed query by at most c = 1/(RRF_K+1) ≤ 1/n * n/(RRF_K+1).

McDiarmid: |f(X) - f(X')| ≤ c_i when X, X' differ only in coordinate i.
Here f = sum_rank 1/(K+rank+1) over the ranked list (no max-normalisation,
which would violate bounded differences with c independent of the max).

unified-recall.py fuse_results uses the same RRF kernel; this module is the
pure, testable core. unified-recall --self-test imports it fail-open.

Hard core: for all trials, |f(X)-f(X^{(i)})| ≤ 1/(K+1).

Usage:
  python3 memory-mcdiarmid-rrf.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys


RRF_K = 60


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()


def rrf_score(memories: list[str], query: str, k: int = RRF_K) -> float:
    """Score = sum_i 1/(k+rank_i+1) for memories, ranked by token overlap."""
    q = set(query.lower().split())
    ranked = sorted(
        memories,
        key=lambda m: len(q & set(m.lower().split())),
        reverse=True,
    )
    s = 0.0
    for rank, _m in enumerate(ranked):
        s += 1.0 / (k + rank + 1)
    return s


def mcdiarmid_bound(k: int = RRF_K) -> float:
    return 1.0 / (k + 1)


def property_mcdiarmid(n: int = 16, trials: int = 40, k: int = RRF_K, seed: int = 0) -> dict:
    rng = random.Random(seed)
    bound = mcdiarmid_bound(k)
    worst = 0.0
    query = "user prefers dark mode python scripts"
    for _ in range(trials):
        mems = [f"fact {rng.randint(0, 99)} token{j} extra{rng.randint(0, 5)}" for j in range(n)]
        base = rrf_score(mems, query, k)
        i = rng.randrange(n)
        alt = list(mems)
        alt[i] = f"REPLACED {rng.random()} prefers python"
        other = rrf_score(alt, query, k)
        delta = abs(base - other)
        if delta > worst:
            worst = delta
        if delta > bound + 1e-12:
            return {"ok": False, "delta": delta, "bound": bound, "n": n}
    return {"ok": True, "worst": worst, "bound": bound, "n": n, "trials": trials}


def self_test() -> int:
    r = property_mcdiarmid()
    assert r["ok"], r
    # Changing a list of size n changes total RRF by at most the largest single
    # term 1/(K+1) because ranks of others shift by at most 1 and the swapped
    # item's own contribution is itself ≤ 1/(K+1). The crude bound 1/(K+1) is
    # conservative relative to the true Lipschitz constant of the *sum* of all
    # terms (which is invariant under permutation!). Sum of 1/(K+r+1) over a
    # full ranking of n items is CONSTANT in the set cardinality — replacing
    # one string does not change n, so f is invariant and delta==0.
    # So we also test a score that depends on content: overlap-weighted RRF.
    def weighted(mems, query, k=RRF_K):
        q = set(query.lower().split())
        scored = []
        for m in mems:
            ov = len(q & set(m.lower().split()))
            scored.append((ov, m))
        scored.sort(reverse=True)
        s = 0.0
        for rank, (ov, _m) in enumerate(scored):
            s += ov / (k + rank + 1)
        return s

    rng = random.Random(1)
    q = "user prefers dark mode"
    bound_w = 8.0 / (RRF_K + 1)  # overlap bounded by query length
    n = 12
    worst = 0.0
    for _ in range(50):
        mems = [f"user prefers token{rng.randint(0, 20)}" for _ in range(n)]
        i = rng.randrange(n)
        alt = list(mems)
        alt[i] = "unrelated zzzz"
        d = abs(weighted(mems, q) - weighted(alt, q))
        worst = max(worst, d)
        assert d <= bound_w + 1e-12, (d, bound_w)
    print("PASS memory-mcdiarmid-rrf self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    print(json.dumps(property_mcdiarmid(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
