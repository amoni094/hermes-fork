#!/usr/bin/env python3
"""compaction-rd-converse.py — Shannon rate-distortion converse for compaction.

Cover–Thomas Thm 10.4 (Hamming distortion, finite alphabet):
  R(D) >= H(X) - h2(D) - D log2(|A|-1)     for 0 <= D <= 1-1/|A|
          0                                 for D >= 1-1/|A|

Empirical rate R_hat = H(Y)/n_symbols (zlib bits of post / |pre|).
Empirical distortion D_hat = 1 - channel_efficiency  (fraction of H(X) lost).

If R_hat < R(D_hat) - slack, the compressor is claiming an impossible
(rate, distortion) pair → alarm (estimator bug or over-aggressive compact).

Usage:
  python3 compaction-rd-converse.py
  python3 compaction-rd-converse.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

SLACK = 0.05
ALPHABET = 256


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


def binary_entropy(p: float) -> float:
    p = min(max(float(p), 1e-12), 1.0 - 1e-12)
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def rd_hamming_lower(h_x_per_sym: float, D: float, alphabet: int = ALPHABET) -> float:
    A = max(int(alphabet), 2)
    D = min(max(float(D), 0.0), 1.0)
    dmax = 1.0 - 1.0 / A
    if D >= dmax:
        return 0.0
    bound = h_x_per_sym - binary_entropy(D) - D * math.log2(A - 1)
    return max(0.0, bound)


def converse(h_pre_bits: float, h_post_bits: float, n_symbols: int, efficiency: float,
             alphabet: int = ALPHABET) -> dict:
    n = max(int(n_symbols), 1)
    h_x = max(0.0, float(h_pre_bits)) / n
    r_hat = max(0.0, float(h_post_bits)) / n
    D = min(max(1.0 - float(efficiency), 0.0), 1.0)
    r_star = rd_hamming_lower(h_x, D, alphabet)
    impossible = bool(r_hat + SLACK < r_star)
    return {
        "r_hat": round(r_hat, 6),
        "r_star": round(r_star, 6),
        "distortion": round(D, 6),
        "h_x_per_symbol": round(h_x, 6),
        "n_symbols": n,
        "alphabet": alphabet,
        "impossible": impossible,
        "alarm": impossible,
        "slack": SLACK,
    }


def load_channel() -> dict:
    try:
        p = _cache_dir() / "context-channel-capacity.json"
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def compute() -> dict:
    try:
        ch = load_channel()
        h_pre = float(ch.get("h_pre") or 0.0)
        h_post = float(ch.get("h_post") or 0.0)
        eff = float(ch.get("channel_efficiency") or 0.0)
        n = int(ch.get("n_pre_bytes") or ch.get("n_symbols") or 0)
        if n <= 0:
            n = max(1, int(h_pre / 8.0) if h_pre else 1)
        rec = converse(h_pre, h_post, n, eff)
        rec["ts"] = time.time()
        _atomic_write(_cache_dir() / "compaction-rd-converse.json", rec)
        return rec
    except Exception as exc:
        return {"r_hat": 0.0, "r_star": 0.0, "distortion": 0.0, "alarm": False, "fail_open": str(exc)}


def self_test() -> int:
    # Lossless: D=0, R(D)=H(X), R_hat=H(X) → possible
    rec = converse(h_pre_bits=800.0, h_post_bits=800.0, n_symbols=100, efficiency=1.0)
    assert rec["distortion"] == 0.0
    assert rec["impossible"] is False
    # Claim huge compression at D≈0 → impossible
    bad = converse(h_pre_bits=800.0, h_post_bits=8.0, n_symbols=100, efficiency=0.99)
    assert bad["r_star"] > 0
    assert bad["impossible"] is True
    # D=1 (max) → R*=0, always possible
    mx = converse(800.0, 8.0, 100, efficiency=0.0)
    assert mx["r_star"] == 0.0
    assert mx["impossible"] is False
    print("PASS compaction-rd-converse self-test")
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
        print(json.dumps({"alarm": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
