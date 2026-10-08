#!/usr/bin/env python3
"""memory-fano-bound.py — Fano lower bound on retrieval error after compaction.

Cover–Thomas Thm 2.10.1 (Fano):
  H(X|Y) <= h_2(Pe) + Pe log(|X|-1)
hence
  Pe >= (H(X|Y) - 1) / log(|X|)     (standard weak form)

Consumes context-channel-capacity.json (h_pre, mutual_info_proxy → H(X|Y)).
Alphabet size |X| estimated from unique bytes of pre-context, or --alphabet.

If Pe lower bound > 0.4, emit alarm: compaction is information-theoretically
lossy beyond a usable retrieval error.

Usage:
  python3 memory-fano-bound.py
  python3 memory-fano-bound.py --h-xy 12 --alphabet 256
  python3 memory-fano-bound.py --self-test
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

PE_ALARM = 0.4


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
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def fano_pe_lower(h_x_given_y_bits: float, alphabet: int) -> dict:
    A = max(int(alphabet), 2)
    hxy = max(0.0, float(h_x_given_y_bits))
    logA = math.log2(A)
    # Weak form
    weak = max(0.0, (hxy - 1.0) / logA) if logA > 0 else 0.0
    weak = min(1.0, weak)
    # Tight-ish: invert H(X|Y) <= h2(Pe) + Pe log2(|X|-1) by grid search
    logAm1 = math.log2(max(A - 1, 2))
    pe_tight = 0.0
    for i in range(0, 501):
        pe = i / 500.0
        rhs = binary_entropy(pe) + pe * logAm1
        if rhs + 1e-12 >= hxy:
            pe_tight = pe
            break
    else:
        pe_tight = 1.0
    return {
        "pe_lower_weak": round(weak, 6),
        "pe_lower_tight": round(pe_tight, 6),
        "h_x_given_y_bits": round(hxy, 4),
        "alphabet": A,
        "alarm": bool(max(weak, pe_tight) > PE_ALARM),
    }


def load_channel() -> dict:
    p = _cache_dir() / "context-channel-capacity.json"
    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def compute(h_xy: float | None = None, alphabet: int | None = None) -> dict:
    try:
        ch = load_channel()
        if h_xy is None:
            if "h_x_given_y" in ch:
                h_xy = float(ch["h_x_given_y"])
            else:
                h_pre_total = float(ch.get("h_pre") or 0.0)
                mi = float(ch.get("mutual_info_proxy") or 0.0)
                h_xy_total = max(0.0, h_pre_total - mi)
                # ADV21-001: normalize to bits/byte so Fano with |A|=256 is well-formed
                n_bytes = max(1, int(ch.get("n_pre_bytes") or (h_pre_total / 8.0) or 1))
                h_xy = h_xy_total / n_bytes
        if alphabet is None:
            alphabet = 256
        rec = fano_pe_lower(float(h_xy), int(alphabet))
        rec["ts"] = time.time()
        rec["source"] = "context-channel-capacity" if ch else "cli"
        _atomic_write(_cache_dir() / "memory-fano-bound.json", rec)
        return rec
    except Exception as exc:
        return {
            "pe_lower_weak": 0.0,
            "pe_lower_tight": 0.0,
            "h_x_given_y_bits": 0.0,
            "alphabet": 2,
            "alarm": False,
            "fail_open": str(exc),
        }


def self_test() -> int:
    # Perfect channel: H(X|Y)=0 → Pe bound 0, no alarm
    z = fano_pe_lower(0.0, 256)
    assert z["pe_lower_weak"] == 0.0
    assert z["alarm"] is False
    # High residual entropy → alarm
    hi = fano_pe_lower(40.0, 16)
    assert hi["pe_lower_weak"] > 0.4
    assert hi["alarm"] is True
    # Tight bound is in [0,1] and >= 0
    assert 0.0 <= hi["pe_lower_tight"] <= 1.0
    # Binary entropy sanity: h2(0.5)=1
    assert abs(binary_entropy(0.5) - 1.0) < 1e-9
    print("PASS memory-fano-bound self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--h-xy", type=float, default=None)
    ap.add_argument("--alphabet", type=int, default=None)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        rec = compute(args.h_xy, args.alphabet)
        print(json.dumps(rec, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"pe_lower_weak": 0.0, "alarm": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
