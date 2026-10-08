#!/usr/bin/env python3
"""memory-conductance-ttl.py — Cheeger conductance TTL floor.

Levin–Peres–Wilmer / Cheeger: mixing time of a reversible chain satisfies
  t_mix >= 1/(2 Phi) - 1
where Phi is the bottleneck conductance
  Phi = min_S cut(S,S^c) / min(vol(S), vol(S^c)).

Also records the Cheeger upper bound
  t_mix <= log(1/(eps * pi_min)) / (Phi^2 / 2)
so TTL is an interval, not only a floor.

Graph: memory entries; edge weight = Jaccard of content-word sets.
TTL floor = max(existing_ttl, t_mix_lower * BASE_UNIT_SECONDS).

Usage:
  python3 memory-conductance-ttl.py
  python3 memory-conductance-ttl.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
BASE_UNIT_SECONDS = 3600
DEFAULT_EXISTING_TTL = 86400
EPS_MIX = 0.25


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall((text or "").lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0


def load_memory_entries() -> list[dict]:
    entries: list[dict] = []
    staging = _hermes_base / "memory-facts" / "staging.md"
    try:
        if staging.exists():
            for i, line in enumerate(staging.read_text(encoding="utf-8", errors="replace").splitlines()):
                s = line.strip()
                if s.startswith("-") and len(s) > 12:
                    entries.append({"entry_id": f"staging:{i}", "text": s})
    except Exception:
        pass
    try:
        wm = _hermes_root / "cache" / "working-memory"
        if wm.is_dir():
            for p in list(wm.glob("*.json"))[:80]:
                try:
                    doc = json.loads(p.read_text(encoding="utf-8"))
                    g = str((doc or {}).get("goal") or "")
                    if g:
                        entries.append({"entry_id": p.stem, "text": g})
                except Exception:
                    continue
    except Exception:
        pass
    return entries[-120:]


def build_graph(entries: list[dict]) -> tuple[list[list[float]], list[float]]:
    n = len(entries)
    toks = [tokenize(str(e.get("text") or e.get("content") or "")) for e in entries]
    W = [[0.0] * n for _ in range(n)]
    deg = [0.0] * n
    for i in range(n):
        for j in range(i + 1, n):
            w = jaccard(toks[i], toks[j])
            if w <= 0.0:
                continue
            W[i][j] = W[j][i] = w
            deg[i] += w
            deg[j] += w
    return W, deg


def cut_conductance(S: set[int], W: list[list[float]], deg: list[float]) -> float:
    n = len(deg)
    if not S or len(S) >= n:
        return 1.0
    vol_s = sum(deg[i] for i in S)
    vol_bar = sum(deg) - vol_s
    denom = min(vol_s, vol_bar)
    if denom <= 1e-12:
        return 1.0
    cut = 0.0
    bar = set(range(n)) - S
    for i in S:
        row = W[i]
        for j in bar:
            cut += row[j]
    return cut / denom


def min_conductance(W: list[list[float]], deg: list[float]) -> float:
    n = len(deg)
    if n <= 1:
        return 1.0
    # Sweep cuts on degree order and on a hash-of-index order.
    orders = [
        sorted(range(n), key=lambda i: deg[i]),
        sorted(range(n), key=lambda i: -deg[i]),
        list(range(n)),
    ]
    best = 1.0
    for order in orders:
        S: set[int] = set()
        for k in range(1, n):
            S.add(order[k - 1])
            phi = cut_conductance(S, W, deg)
            if phi < best:
                best = phi
    return max(best, 0.0)


def mixing_bounds(phi: float, n: int, deg: list[float] | None = None, eps: float = EPS_MIX) -> tuple[float, float, float]:
    phi = max(float(phi), 1e-9)
    t_lo = max(0.0, 1.0 / (2.0 * phi) - 1.0)
    # Stationary mass of a reversible chain: pi_i = deg_i / vol, not 1/n.
    if deg:
        vol = sum(deg) or 1.0
        pos = [d / vol for d in deg if d > 0]
        pi_min = min(pos) if pos else 1.0 / max(n, 1)
    else:
        pi_min = 1.0 / max(n, 1)
    gap_lo = (phi * phi) / 2.0
    t_hi = math.log(max(2.0, 1.0 / (eps * max(pi_min, 1e-12)))) / max(gap_lo, 1e-12)
    return t_lo, t_hi, pi_min


def existing_ttl_seconds() -> int:
    try:
        p = _cache_dir() / "memory-mixing-ttl.json"
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            for k in ("ttl_seconds", "ttl", "recommended_ttl"):
                if k in obj:
                    return max(0, int(float(obj[k])))
    except Exception:
        pass
    return DEFAULT_EXISTING_TTL


def compute(entries: list[dict] | None = None) -> dict:
    try:
        ents = list(entries) if entries is not None else load_memory_entries()
        n = len(ents)
        if n == 0:
            rec = {
                "conductance": 1.0,
                "mixing_time_lower_bound": 0.0,
                "mixing_time_upper_bound": 0.0,
                "ttl_floor_seconds": DEFAULT_EXISTING_TTL,
                "n_nodes": 0,
                "existing_ttl": DEFAULT_EXISTING_TTL,
            }
            _atomic_write(_cache_dir() / "memory-conductance-ttl.json", rec)
            return rec
        W, deg = build_graph(ents)
        phi = min_conductance(W, deg)
        t_lo, t_hi, pi_min = mixing_bounds(phi, n, deg)
        existing = existing_ttl_seconds()
        ttl_floor = max(existing, int(math.ceil(t_lo * BASE_UNIT_SECONDS)))
        rec = {
            "conductance": round(phi, 6),
            "mixing_time_lower_bound": round(t_lo, 6),
            "mixing_time_upper_bound": round(t_hi, 6),
            "ttl_floor_seconds": int(ttl_floor),
            "n_nodes": n,
            "existing_ttl": existing,
            "base_unit_seconds": BASE_UNIT_SECONDS,
            "pi_min": round(pi_min, 8),
            "advisory_only": True,
            "ts": time.time(),
        }
        _atomic_write(_cache_dir() / "memory-conductance-ttl.json", rec)
        return rec
    except Exception as exc:
        return {
            "conductance": 1.0,
            "mixing_time_lower_bound": 0.0,
            "ttl_floor_seconds": DEFAULT_EXISTING_TTL,
            "n_nodes": 0,
            "fail_open": str(exc),
        }


def self_test() -> int:
    # Two disjoint cliques → conductance near 0, mixing lower bound large
    clique_a = [{"entry_id": f"a{i}", "text": "alpha beta gamma delta " * 3} for i in range(4)]
    clique_b = [{"entry_id": f"b{i}", "text": "quantum banana flux zed " * 3} for i in range(4)]
    rec = compute(clique_a + clique_b)
    assert rec["n_nodes"] == 8
    assert rec["conductance"] < 0.15, rec
    assert rec["mixing_time_lower_bound"] > 1.0, rec
    assert rec["ttl_floor_seconds"] >= DEFAULT_EXISTING_TTL
    # Complete similar graph → high conductance
    similar = [{"entry_id": f"s{i}", "text": "shared topic memory entry number %d" % i} for i in range(6)]
    rec2 = compute(similar)
    assert rec2["conductance"] > rec["conductance"]
    # Empty
    empty = compute([])
    assert empty["n_nodes"] == 0
    assert empty["ttl_floor_seconds"] > 0
    # Cheeger: upper >= lower
    assert rec["mixing_time_upper_bound"] >= rec["mixing_time_lower_bound"]
    assert rec.get("advisory_only") is True
    _, t_hi_u, pi_u = mixing_bounds(0.1, 4)
    assert abs(pi_u - 0.25) < 1e-9  # uniform fallback 1/n
    _, t_hi_d, pi_d = mixing_bounds(0.1, 4, [1.0, 1.0, 1.0, 7.0])
    assert abs(pi_d - 0.1) < 1e-9  # min deg/vol = 1/10
    assert t_hi_d > t_hi_u  # smaller pi_min => larger mixing upper bound
    print("PASS memory-conductance-ttl self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        print(json.dumps(compute(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "conductance": 1.0,
            "mixing_time_lower_bound": 0.0,
            "ttl_floor_seconds": DEFAULT_EXISTING_TTL,
            "n_nodes": 0,
            "fail_open": str(exc),
        }))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
