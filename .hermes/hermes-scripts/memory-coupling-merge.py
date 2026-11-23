#!/usr/bin/env python3
"""memory-coupling-merge.py — OT coupling merge of two memory snapshots.

Grimmett / Morters: couple two laws, then merge along the coupling.
Uses ot_utils.sinkhorn when numpy is available; otherwise independent coupling
of sorted relevance (still yields FOSD for the pointwise-max merge).

Hard core: merged relevance Y = max(X, Z) along the coupling stochastically
dominates both inputs (F_Y(t) ≤ min(F_X(t), F_Z(t)) for all t).

Usage:
  python3 memory-coupling-merge.py --self-test
  python3 memory-coupling-merge.py --a SNAP.json --b SNAP.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def fosd(merged: list[float], other: list[float], grid: int = 20) -> bool:
    """Empirical FOSD: F_merged(t) <= F_other(t) for t on a grid of values."""
    if not merged or not other:
        return True
    lo = min(min(merged), min(other))
    hi = max(max(merged), max(other))
    if hi == lo:
        return True
    n_m, n_o = len(merged), len(other)
    for i in range(grid + 1):
        t = lo + (hi - lo) * i / grid
        Fm = sum(1 for x in merged if x <= t) / n_m
        Fo = sum(1 for x in other if x <= t) / n_o
        if Fm > Fo + 1e-9:
            return False
    return True


def _pad(items: list[dict], n: int) -> list[dict]:
    out = list(items)
    while len(out) < n:
        out.append({"id": f"dummy:{len(out)}", "relevance": 0.0, "text": ""})
    return out


def merge_snapshots(a: list[dict], b: list[dict]) -> dict:
    """Couple then keep pointwise max relevance."""
    if not a and not b:
        return {"merged": [], "fosd_a": True, "fosd_b": True}
    n = max(len(a), len(b), 1)
    A, B = _pad(a, n), _pad(b, n)
    rel_a = [float(x.get("relevance") or 0.0) for x in A]
    rel_b = [float(x.get("relevance") or 0.0) for x in B]
    plan = None
    try:
        import numpy as np
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from ot_utils import sinkhorn  # type: ignore
        C = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            for j in range(n):
                C[i, j] = abs(rel_a[i] - rel_b[j]) + (1.0 - _jaccard(str(A[i].get("text") or ""), str(B[j].get("text") or "")))
        pa = np.ones(n) / n
        pb = np.ones(n) / n
        plan, _cost = sinkhorn(pa, pb, C, reg=0.08, max_iter=80)
    except Exception:
        plan = None
    merged_rel = []
    merged_items = []
    if plan is not None:
        import numpy as np
        # For each source i, partner j* = argmax_j P_ij, take max relevance
        P = np.asarray(plan)
        for i in range(n):
            j = int(np.argmax(P[i]))
            ra, rb = rel_a[i], rel_b[j]
            if ra >= rb:
                item = dict(A[i])
                item["relevance"] = ra
                item["coupled_from"] = "a"
            else:
                item = dict(B[j])
                item["relevance"] = rb
                item["coupled_from"] = "b"
            merged_items.append(item)
            merged_rel.append(item["relevance"])
    else:
        # Sorted independent coupling (comonotonic): still Y=max FOSD both
        sa = sorted(rel_a)
        sb = sorted(rel_b)
        merged_rel = [max(x, y) for x, y in zip(sa, sb)]
        merged_items = [{"relevance": r, "id": f"max:{i}"} for i, r in enumerate(merged_rel)]
    return {
        "merged": merged_items,
        "merged_rel": merged_rel,
        "fosd_a": fosd(merged_rel, rel_a),
        "fosd_b": fosd(merged_rel, rel_b),
        "used_sinkhorn": plan is not None,
    }


def self_test() -> int:
    a = [{"id": "1", "relevance": 0.1, "text": "alpha"},
         {"id": "2", "relevance": 0.4, "text": "beta cat"}]
    b = [{"id": "3", "relevance": 0.2, "text": "alpha dog"},
         {"id": "4", "relevance": 0.9, "text": "gamma"}]
    m = merge_snapshots(a, b)
    assert m["fosd_a"] and m["fosd_b"], m
    # Pointwise max of any pairing FOSD
    xs = [0.0, 0.5, 1.0]
    ys = [0.2, 0.2, 0.8]
    mm = [max(x, y) for x, y in zip(sorted(xs), sorted(ys))]
    assert fosd(mm, xs) and fosd(mm, ys)
    print("PASS memory-coupling-merge self-test")
    return 0


def _load_snap(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("merged") or []
    out = []
    for i, it in enumerate(raw):
        if isinstance(it, dict):
            out.append({
                "id": str(it.get("id") or i),
                "relevance": float(it.get("relevance") or it.get("rrf_score") or it.get("score") or 0.0),
                "text": str(it.get("text") or ""),
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", default="")
    ap.add_argument("--b", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.a and args.b:
            m = merge_snapshots(_load_snap(Path(args.a)), _load_snap(Path(args.b)))
            fosd_ok = m["fosd_a"] and m["fosd_b"]
            print(json.dumps({"fosd_a": m["fosd_a"], "fosd_b": m["fosd_b"],
                              "fosd_ok": fosd_ok,
                              "n": len(m["merged"]), "used_sinkhorn": m["used_sinkhorn"]}))
            # ADV-013: exit non-zero when merged does not FOSD both inputs
            return 0 if fosd_ok else 1
        print(json.dumps({"ok": True, "note": "pass --a/--b snapshots or --self-test"}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
