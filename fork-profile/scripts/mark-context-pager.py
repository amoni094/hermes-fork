#!/usr/bin/env python3
"""Standalone MARK paging implementation. Imported by rd-compaction-advisor.py when available. May also be called directly.

MARK paging for context compaction (Motwani Ch 13).
Intersect MARK-drop with typicality drop in rd-compaction-advisor.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    return v


@dataclass
class MarkPager:
    k: int
    n: int
    p: float = field(init=False)
    r: int = field(init=False)

    def __post_init__(self) -> None:
        k = max(1, int(self.k or 1))
        n = max(k, int(self.n or k))
        self.k = k
        self.n = n
        self.p = k / n
        self.r = max(1, math.ceil(math.log(n)))


def mark_drop_set(items: list, pager: MarkPager, rng) -> set:
    """items ordered most-recent-first. Return ids to drop (unmarked).

    MARK: every request marks k uniform-random cache lines. Evict unmarked
    after r ≈ log n requests. Deterministic fallback: mark the k most recent.
    """
    if not items:
        return set()
    n = min(pager.n, len(items))
    k = min(pager.k, n)
    marked: set = set()
    if rng is not None:
        idx = list(range(n))
        rng.shuffle(idx)
        for i in idx[:k]:
            it = items[i]
            marked.add(it.get("id") if isinstance(it, dict) else it)
    else:
        for it in items[:k]:
            marked.add(it.get("id") if isinstance(it, dict) else it)
    drop = set()
    for it in items:
        iid = it.get("id") if isinstance(it, dict) else it
        if iid not in marked:
            drop.add(iid)
    return drop


def _self_test() -> int:
    import random
    items = [{"id": i} for i in range(16)]
    pager = MarkPager(k=4, n=16)
    assert pager.r >= 1
    rng = random.Random(0)
    drop = mark_drop_set(items, pager, rng)
    assert len(drop) == 12
    det = mark_drop_set(items, pager, None)
    assert 0 not in det and 3 not in det
    assert 15 in det
    print(json.dumps({"ok": True, "p": pager.p, "r": pager.r, "n_drop": len(drop)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MARK context pager")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
