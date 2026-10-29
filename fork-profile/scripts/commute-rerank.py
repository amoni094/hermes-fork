#!/usr/bin/env python3
"""Commute-time / effective-resistance rerank (standalone, Motwani / Doyle-Snell).

Not wired into unified-recall yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    return v


def effective_resistance_undirected(adj, u, v, tol=1e-8, max_iter=500) -> float:
    """R_uv via Laplacian solve. numpy if present, else Gauss-Seidel."""
    nodes = list(adj.keys())
    if u not in adj or v not in adj:
        return float("inf")
    if u == v:
        return 0.0
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    # Laplacian
    L = [[0.0] * n for _ in range(n)]
    for a, nbrs in adj.items():
        i = idx[a]
        deg = 0.0
        for b, w in nbrs.items() if isinstance(nbrs, dict) else [(x, 1.0) for x in nbrs]:
            if b not in idx:
                continue
            ww = _f(w, 1.0)
            j = idx[b]
            L[i][j] -= ww
            deg += ww
        L[i][i] = deg
    # Ground v: solve L_red x = e_u - e_v with x_v = 0
    gi = idx[v]
    keep = [i for i in range(n) if i != gi]
    m = len(keep)
    if m == 0:
        return 0.0
    A = [[L[keep[r]][keep[c]] for c in range(m)] for r in range(m)]
    b = [0.0] * m
    if idx[u] != gi:
        b[keep.index(idx[u])] = 1.0
    try:
        import numpy as np  # type: ignore

        x = np.linalg.lstsq(np.array(A, dtype=float), np.array(b, dtype=float), rcond=None)[0]
        xu = float(x[keep.index(idx[u])]) if idx[u] != gi else 0.0
        return max(0.0, xu)
    except Exception:
        x = [0.0] * m
        for _ in range(max_iter):
            delta = 0.0
            for r in range(m):
                diag = A[r][r]
                if abs(diag) < 1e-18:
                    continue
                s = b[r] - sum(A[r][c] * x[c] for c in range(m) if c != r)
                nx = s / diag
                delta = max(delta, abs(nx - x[r]))
                x[r] = nx
            if delta < tol:
                break
        xu = x[keep.index(idx[u])] if idx[u] != gi else 0.0
        return max(0.0, xu)


def rerank(graphiti_results, query_node, adj, k=10):
    scored = []
    for item in graphiti_results:
        nid = item.get("id") if isinstance(item, dict) else item
        r = effective_resistance_undirected(adj, query_node, nid)
        scored.append((r, item))
    scored.sort(key=lambda t: t[0])
    return [it for _, it in scored[:k]]


def _self_test() -> int:
    # Path a-b-c-d: R(a,d) > R(a,b)
    adj = {
        "a": {"b": 1.0},
        "b": {"a": 1.0, "c": 1.0},
        "c": {"b": 1.0, "d": 1.0},
        "d": {"c": 1.0},
    }
    rab = effective_resistance_undirected(adj, "a", "b")
    rad = effective_resistance_undirected(adj, "a", "d")
    assert rad > rab, (rab, rad)
    results = [{"id": "d"}, {"id": "b"}, {"id": "c"}]
    out = rerank(results, "a", adj, k=2)
    assert out[0]["id"] == "b"
    print(json.dumps({"ok": True, "R_ab": rab, "R_ad": rad, "top": [x["id"] for x in out]}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Commute-time rerank")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    print(json.dumps({"ok": True, "usage": "--self-test"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
