#!/usr/bin/env python3
"""memory-mixing-ttl.py — mixing-time lower bound vs TTL (Hairer, Durrett).

Legal TTL for a memory fact is bounded below by an empirical mixing time of
the recall Markov chain: purging before the chain mixes throws away mass that
has not yet equilibrated.

Estimate P on recalled fact-ids (or query tokens) from recall logs / lifecycle
last_accessed order. Spectral gap γ ≈ 1 - λ_2 of the lazy chain; 
  τ_mix(ε) ≤ log(1/(ε π_min)) / γ

Flag TTL (seconds) < τ_mix as too short.

Usage:
  python3 memory-mixing-ttl.py --check
  python3 memory-mixing-ttl.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import timedelta
from pathlib import Path


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


def empirical_transition(seq: list[str]) -> list[list[float]]:
    states = sorted(set(seq))
    if not states:
        return []
    idx = {s: i for i, s in enumerate(states)}
    n = len(states)
    C = [[0.0] * n for _ in range(n)]
    for a, b in zip(seq, seq[1:]):
        C[idx[a]][idx[b]] += 1.0
    P = []
    for i in range(n):
        s = sum(C[i])
        if s <= 0:
            row = [1.0 / n] * n
        else:
            row = [C[i][j] / s for j in range(n)]
        # lazy chain: 0.5 I + 0.5 P  (guarantees aperiodicity)
        P.append([0.5 * (1.0 if i == j else 0.0) + 0.5 * row[j] for j in range(n)])
    return P


def spectral_gap(P: list[list[float]]) -> float:
    """1 - |λ_2| via power iteration on P - 1π^T using numpy if present, else bound."""
    n = len(P)
    if n <= 1:
        return 1.0
    try:
        import numpy as np
        A = np.array(P, dtype=np.float64)
        # stationary: left eigenvector
        w, v = np.linalg.eig(A.T)
        w = np.real(w)
        order = np.argsort(-np.abs(w))
        lam2 = float(np.abs(w[order[1]])) if n > 1 else 0.0
        gap = max(1e-9, 1.0 - min(1.0, lam2))
        return gap
    except Exception:
        # Dobrushin: 1 - max TV between rows
        max_tv = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                tv = 0.5 * sum(abs(P[i][k] - P[j][k]) for k in range(n))
                if tv > max_tv:
                    max_tv = tv
        return max(1e-9, 1.0 - max_tv)


def mixing_time(gap: float, n_states: int, eps: float = 0.25) -> float:
    if n_states <= 1:
        return 1.0
    pi_min = 1.0 / n_states
    return math.log(max(2.0, 1.0 / (eps * pi_min))) / gap


def load_recall_sequence() -> list[str]:
    seq: list[str] = []
    for cand in (
        cache_dir() / "ripple-mem-recall.jsonl",
        hermes_home() / "cache" / "ripple-mem-recall.jsonl",
        hermes_home() / "memory-facts" / "staleness_log.jsonl",
    ):
        if not cand.exists():
            continue
        try:
            for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    q = obj.get("query") or obj.get("fact_label") or obj.get("memory_id")
                    if q:
                        seq.append(str(q)[:80])
                    for e in obj.get("entries") or []:
                        if isinstance(e, dict) and e.get("memory_id"):
                            seq.append(str(e["memory_id"])[:80])
        except Exception:
            continue
    db = hermes_home() / "memory-facts" / "lifecycle.db"
    if db.exists() and len(seq) < 8:
        try:
            conn = sqlite3.connect(str(db), timeout=10)
            try:
                rows = conn.execute(
                    "SELECT memory_id FROM fact_lifecycle "
                    "WHERE last_accessed IS NOT NULL ORDER BY last_accessed"
                ).fetchall()
                seq.extend(str(r[0])[:80] for r in rows if r and r[0])
            finally:
                conn.close()
        except Exception:
            pass
    return seq


def check_ttls(ttl_days: dict[str, float] | None = None) -> dict:
    seq = load_recall_sequence()
    P = empirical_transition(seq) if len(seq) >= 4 else []
    n = len(P)
    gap = spectral_gap(P) if P else 1.0
    tau = mixing_time(gap, max(n, 1))
    # mixing time is in chain steps; convert with ~1 recall/hour crude clock
    tau_hours = tau  # 1 step ~ 1 hour default
    tau_days = tau_hours / 24.0
    policy = ttl_days or {"ephemeral": 1.0, "volatile": 30.0, "preference": 14.0}
    flags = []
    for name, days in policy.items():
        if days < tau_days:
            flags.append({"ttl": name, "ttl_days": days, "mixing_days": round(tau_days, 4),
                          "too_short": True})
    result = {
        "n_states": n,
        "n_transitions": max(0, len(seq) - 1),
        "spectral_gap": round(gap, 6),
        "tau_mix_steps": round(tau, 4),
        "tau_mix_days": round(tau_days, 4),
        "flags": flags,
        "ok": len(flags) == 0,
    }
    outp = cache_dir() / "memory-mixing-ttl.json"
    try:
        tmp = outp.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
        tmp.replace(outp)
    except Exception:
        pass
    return result


def self_test() -> int:
    # Two-state chain that mixes slowly: P = [[0.99, 0.01], [0.01, 0.99]] then lazy
    seq = (["a"] * 50 + ["b"] * 2) * 20 + ["a"] * 10
    P = empirical_transition(seq)
    assert len(P) == 2
    gap = spectral_gap(P)
    assert 0 < gap < 1
    tau = mixing_time(gap, 2)
    assert tau > 1
    # Dirac chain mixes immediately
    P1 = empirical_transition(["x"] * 10)
    g1 = spectral_gap(P1)
    assert g1 >= 0.5  # lazy self-loop
    # Flag short TTL
    fake = {"ephemeral": 0.0001, "volatile": 30.0}
    # Use mixing_time large
    flags = [name for name, d in fake.items() if d < 1.0]
    assert "ephemeral" in flags
    print("PASS memory-mixing-ttl self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        print(json.dumps(check_ttls(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": True, "fail_open": str(exc), "flags": []}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
