#!/usr/bin/env python3
"""memory-ot-decay.py — Wasserstein-1 geodesic forgetting.

Villani / Peyré–Cuturi: decay along an OT geodesic, not exponential.
Memory is a discrete law over importance scores (UE-based). Target law
is uniform on the top-K entries. 1-D monotone coupling is optimal for W1.

  W1 = sum_i |rank_current(i) - rank_target(i)| / n
  ot_decay_factor(i) = displacement(i) / max_disp   (far from target → faster decay)

Stdlib only (no scipy). Pinsker companion: TV <= sqrt(KL/2) between
current and target measures is reported as a sanity bound.

Usage:
  python3 memory-ot-decay.py
  python3 memory-ot-decay.py --k 5
  python3 memory-ot-decay.py --self-test
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

DEFAULT_K = 8


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return max(0.0, min(1.0, v))


def load_entries() -> list[dict]:
    entries: list[dict] = []
    cache = _cache_dir()
    for name in ("ue-memory-gate-log.jsonl", "ue-blackbox-scores.jsonl", "ue-memory-gate-scores.jsonl"):
        p = cache / name
        try:
            if not p.exists():
                continue
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh):
                    s = line.strip()
                    if not s.startswith("{"):
                        continue
                    try:
                        row = json.loads(s)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue
                    imp = row.get("composite_ue")
                    if imp is None:
                        imp = row.get("ue_score", row.get("ue", 0.0))
                    # invert UE: low uncertainty = high importance
                    ue = _clip01(imp)
                    importance = 1.0 - ue
                    eid = str(row.get("query_hash") or row.get("entry_id") or f"{name}:{i}")
                    entries.append({"entry_id": eid, "importance": importance, "ue": ue})
        except Exception:
            continue
        if entries:
            break
    # de-dup by entry_id keeping last
    seen = {}
    for e in entries:
        seen[e["entry_id"]] = e
    return list(seen.values())[-200:]


def ot_decay(entries: list[dict], k: int = DEFAULT_K) -> dict:
    n = len(entries)
    if n == 0:
        return {"w1_distance": 0.0, "k": k, "n": 0, "entries": []}
    k = max(1, min(int(k), n))
    ranked = sorted(entries, key=lambda e: -float(e.get("importance") or 0.0))
    # current ranks: 0 = most important
    current_rank = {e["entry_id"]: i for i, e in enumerate(ranked)}
    top = ranked[:k]
    top_ids = {e["entry_id"] for e in top}
    # Target: stay in top-K. Displacement = 0 on the support; below cutoff,
    # displacement = rank - (k-1) (how far the item is from the kept set).
    target_rank = {}
    cutoff = k - 1
    for i, e in enumerate(ranked):
        if i < k:
            target_rank[e["entry_id"]] = i
        else:
            target_rank[e["entry_id"]] = cutoff
    displacements = []
    for e in ranked:
        cr = current_rank[e["entry_id"]]
        d = abs(cr - target_rank[e["entry_id"]])
        displacements.append(d)
    w1 = (sum(displacements) / n) if n else 0.0
    max_d = max(displacements) if displacements else 1
    max_d = max(max_d, 1)
    out_entries = []
    for e, d in zip(ranked, displacements):
        factor = d / max_d  # 0 = stay, 1 = fastest decay
        out_entries.append({
            "entry_id": e["entry_id"],
            "ot_decay_factor": round(factor, 6),
            "w1_distance": round(w1, 6),
            "displacement": int(d),
            "importance": round(float(e.get("importance") or 0.0), 6),
        })
    # Pinsker: TV and KL between current softmax and target uniform-on-top-K
    imps = [max(1e-9, float(e.get("importance") or 0.0)) for e in ranked]
    z = sum(imps) or 1.0
    p = [x / z for x in imps]
    q = [(1.0 / k if e["entry_id"] in top_ids else 1e-12) for e in ranked]
    qz = sum(q) or 1.0
    q = [x / qz for x in q]
    tv = 0.5 * sum(abs(a - b) for a, b in zip(p, q))
    kl = 0.0
    for a, b in zip(p, q):
        if a > 0 and b > 0:
            kl += a * math.log(a / b)
    pinsker = math.sqrt(max(kl, 0.0) / 2.0)
    # ADV21-016: alarm on W1 displacement / decay_needed, not pinsker_ok
    # (Pinsker is a sanity bound on TV vs KL; it is not a forgetting trigger.)
    W1_ALARM = 0.25
    decay_needed = bool(w1 > W1_ALARM)
    return {
        "w1_distance": round(w1, 6),
        "k": k,
        "n": n,
        "tv_distance": round(tv, 6),
        "kl_pq": round(kl, 6),
        "pinsker_tv_upper": round(pinsker, 6),
        "pinsker_ok": bool(tv <= pinsker + 1e-6 or kl < 1e-12),
        "decay_needed": decay_needed,
        "alarm": decay_needed,
        "reason": "w1_geodesic_displacement" if decay_needed else "ok",
        "entries": out_entries,
        "ts": time.time(),
    }


def compute(entries: list[dict] | None = None, k: int = DEFAULT_K) -> dict:
    try:
        ents = list(entries) if entries is not None else load_entries()
        rec = ot_decay(ents, k=k)
        _atomic_write(_cache_dir() / "memory-ot-decay.json", rec)
        return rec
    except Exception as exc:
        return {"w1_distance": 0.0, "k": k, "n": 0, "entries": [], "fail_open": str(exc)}


def self_test() -> int:
    ents = [
        {"entry_id": "a", "importance": 0.9},
        {"entry_id": "b", "importance": 0.8},
        {"entry_id": "c", "importance": 0.1},
        {"entry_id": "d", "importance": 0.05},
    ]
    rec = ot_decay(ents, k=2)
    assert rec["n"] == 4
    assert rec["w1_distance"] >= 0
    by_id = {e["entry_id"]: e for e in rec["entries"]}
    # top-2 already at target ranks 0,1 → decay factor 0
    assert by_id["a"]["ot_decay_factor"] == 0.0
    assert by_id["b"]["ot_decay_factor"] == 0.0
    # tail should decay faster
    assert by_id["c"]["ot_decay_factor"] > 0.0
    assert by_id["d"]["ot_decay_factor"] >= by_id["c"]["ot_decay_factor"]
    empty = ot_decay([], k=3)
    assert empty["n"] == 0 and empty["w1_distance"] == 0.0
    # Pinsker direction TV <= sqrt(KL/2) (or both ~0)
    assert rec["tv_distance"] >= 0
    assert rec["pinsker_tv_upper"] >= 0
    # Tail mass displaced from top-K => W1 alarm, independent of pinsker_ok
    assert rec["w1_distance"] > 0.25
    assert rec["alarm"] is True
    assert rec["decay_needed"] is True
    tight = ot_decay(ents[:2], k=2)
    assert tight["w1_distance"] == 0.0
    assert tight["alarm"] is False
    print("PASS memory-ot-decay self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        rec = compute(k=args.k)
        slim = {kk: rec[kk] for kk in rec if kk != "entries"}
        slim["n_entries"] = len(rec.get("entries") or [])
        print(json.dumps(slim, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"w1_distance": 0.0, "entries": [], "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
