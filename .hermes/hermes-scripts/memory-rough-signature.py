#!/usr/bin/env python3
"""memory-rough-signature.py — order-2 rough-path signature of irregular events.

Hairer / Kidger: the level-2 signature of a path X:[0,T]→R^d is
  S^1 = ∫ dX          (increments)
  S^2 = ∫∫ dX ⊗ dX    (Lévy area + squares)

ripple-mem-expander.py does Jaccard/BFS associative expansion, not signatures.
This module stores a bounded order-2 signature as a memory feature.

Discrete Chen/Young increment formula (stdlib math + optional numpy).

Hard core: signature of a linear path X_t = a + t b is
  S^1 = b * T,  S^2 = 0.5 (S^1) ⊗ (S^1)   (shuffle / Chen identity)

Usage:
  python3 memory-rough-signature.py --from-jsonl PATH
  python3 memory-rough-signature.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Iterable


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def profile_root() -> Path:
    hp = os.environ.get("HERMES_PROFILE", "").strip()
    if hp:
        cand = Path.home() / ".hermes" / "profiles" / hp
        if cand.is_dir():
            return cand
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    if hh.name != ".hermes" and hh.parent.name == "profiles":
        return hh
    return hermes_home()


def cache_dir() -> Path:
    d = profile_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _zeros(d: int) -> list[float]:
    return [0.0] * d


def _outer(a: list[float], b: list[float]) -> list[list[float]]:
    return [[ai * bj for bj in b] for ai in a]


def _add_mat(A: list[list[float]], B: list[list[float]]) -> list[list[float]]:
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _scale_mat(A: list[list[float]], s: float) -> list[list[float]]:
    return [[A[i][j] * s for j in range(len(A[0]))] for i in range(len(A))]


def order2_signature(path: list[list[float]]) -> dict:
    """Bounded order-2 signature. path: list of R^d points, length >= 1."""
    if not path:
        return {"level1": [], "level2": [], "d": 0, "n": 0}
    d = len(path[0])
    s1 = _zeros(d)
    s2 = [[0.0] * d for _ in range(d)]
    running = _zeros(d)
    for i in range(1, len(path)):
        dx = [path[i][j] - path[i - 1][j] for j in range(d)]
        # S^2 += running ⊗ dx + 0.5 dx ⊗ dx
        s2 = _add_mat(s2, _outer(running, dx))
        s2 = _add_mat(s2, _scale_mat(_outer(dx, dx), 0.5))
        for j in range(d):
            running[j] += dx[j]
            s1[j] += dx[j]
    return {"level1": s1, "level2": s2, "d": d, "n": len(path)}


def events_to_path(events: Iterable[dict], dim: int = 3) -> list[list[float]]:
    """Map irregular tool events to a path in R^d: [t_norm, hash0, hash1]."""
    evs = list(events)
    if not evs:
        return [[0.0] * dim]
    times = []
    for e in evs:
        t = e.get("ts") or e.get("t") or e.get("time") or 0.0
        try:
            times.append(float(t))
        except (TypeError, ValueError):
            times.append(0.0)
    t0, t1 = min(times), max(times)
    span = (t1 - t0) or 1.0
    path = []
    for e, t in zip(evs, times):
        name = str(e.get("tool") or e.get("name") or e.get("text") or "")
        h = 0
        for ch in name:
            h = (h * 131 + ord(ch)) & 0xFFFFFFFF
        x1 = ((h & 0xFFFF) / 65535.0) * 2.0 - 1.0
        x2 = (((h >> 16) & 0xFFFF) / 65535.0) * 2.0 - 1.0
        pt = [(t - t0) / span, x1, x2][:dim]
        while len(pt) < dim:
            pt.append(0.0)
        path.append(pt)
    return path


def flatten_sig(sig: dict) -> list[float]:
    out = list(sig["level1"])
    for row in sig["level2"]:
        out.extend(row)
    return out


def self_test() -> int:
    # Linear path in R^2: (0,0) -> (1,2)  T=1, b=(1,2)
    path = [[0.0, 0.0], [1.0, 2.0]]
    sig = order2_signature(path)
    s1 = sig["level1"]
    assert abs(s1[0] - 1.0) < 1e-12 and abs(s1[1] - 2.0) < 1e-12
    # Chen: S^2 = 0.5 S^1 ⊗ S^1
    expected = [[0.5 * s1[i] * s1[j] for j in range(2)] for i in range(2)]
    for i in range(2):
        for j in range(2):
            assert abs(sig["level2"][i][j] - expected[i][j]) < 1e-12, (i, j, sig["level2"], expected)
    # Time-reparametrisation invariance of signature (weak): same increments
    path2 = [[0.0, 0.0], [0.3, 0.6], [1.0, 2.0]]  # not linear in time but colinear in space
    # For a genuinely linear geometric path split in two, Chen identity still holds globally
    sig2 = order2_signature([[0.0, 0.0], [1.0, 2.0], [1.0, 2.0]])
    assert abs(sig2["level1"][0] - 1.0) < 1e-12
    print("PASS memory-rough-signature self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-jsonl", default="", help="JSONL of {ts, tool} events")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        events = []
        src = Path(args.from_jsonl) if args.from_jsonl else cache_dir() / "ripple-mem-recall.jsonl"
        if src.exists():
            for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        path = events_to_path(events)
        sig = order2_signature(path)
        outp = cache_dir() / "memory-rough-signature.json"
        payload = {"n_events": len(events), "d": sig["d"], "level1": sig["level1"],
                   "level2": sig["level2"], "feature": flatten_sig(sig)}
        tmp = outp.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(outp)
        print(json.dumps({"ok": True, "n_events": len(events), "path": str(outp), "level1": sig["level1"]}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
