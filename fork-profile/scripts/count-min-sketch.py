#!/usr/bin/env python3
"""Count-Min sketch (Motwani streaming / Cormode-Muthukrishnan)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    return v


class CountMinSketch:
    def __init__(self, width=2000, depth=5):
        try:
            width = int(width or 2000)
        except (TypeError, ValueError):
            width = 2000
        try:
            depth = int(depth or 5)
        except (TypeError, ValueError):
            depth = 5
        self.width = max(8, width)
        self.depth = max(1, depth)
        self.table = [[0] * self.width for _ in range(self.depth)]

    def _idx(self, key: str, row: int) -> int:
        h = hashlib.sha256(f"{row}:{key}".encode("utf-8", errors="replace")).digest()
        return int.from_bytes(h[:8], "little") % self.width

    def add(self, key, c=1) -> None:
        try:
            c = int(c or 1)
        except (TypeError, ValueError):
            c = 1
        s = str(key)
        for d in range(self.depth):
            self.table[d][self._idx(s, d)] += c

    def query(self, key) -> int:
        s = str(key)
        return min(self.table[d][self._idx(s, d)] for d in range(self.depth))


def _self_test() -> int:
    cm = CountMinSketch(width=64, depth=3)
    for _ in range(10):
        cm.add("hot")
    cm.add("cold")
    assert cm.query("hot") >= 10
    assert cm.query("cold") >= 1
    assert cm.query("absent") == 0
    print(json.dumps({"ok": True, "hot": cm.query("hot"), "cold": cm.query("cold")}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Count-Min sketch")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
