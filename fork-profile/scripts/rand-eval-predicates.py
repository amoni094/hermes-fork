#!/usr/bin/env python3
"""Randomized predicate evaluation (Motwani Ch 1).

rand_or / rand_and for cheap pre-screens (backend health probes).
"""
from __future__ import annotations

import argparse
import json
import random
import sys


def rand_or(preds, rng=None) -> bool:
    """Shuffle then short-circuit OR. Expected probes 1/(1-Π(1-p_i))."""
    rng = rng or random.Random()
    order = list(preds)
    rng.shuffle(order)
    for p in order:
        if p():
            return True
    return False


def rand_and(preds, rng=None) -> bool:
    rng = rng or random.Random()
    order = list(preds)
    rng.shuffle(order)
    for p in order:
        if not p():
            return False
    return True


def _self_test() -> int:
    rng = random.Random(0)
    calls = []

    def t():
        calls.append("t")
        return True

    def f():
        calls.append("f")
        return False

    assert rand_or([f, f, t], rng) is True
    assert rand_and([t, t], random.Random(1)) is True
    assert rand_and([t, f], random.Random(2)) is False
    assert rand_or([f, f], random.Random(3)) is False
    print(json.dumps({"ok": True, "calls": calls}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Randomized predicate eval")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
