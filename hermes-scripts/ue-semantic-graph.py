#!/usr/bin/env python3
"""Graph-based blackbox UE metrics (EigValLaplacian / DegMat / Eccentricity).

Stdlib only. Power-iteration + exact trace. Never raises through shadow paths.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

SAMPLE_CAP = 32
TEXT_CAP = 50000
ECC_THRESHOLD = 0.3
COMP_THRESHOLD = 0.5
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _clip01(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _append_jsonl(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
    except Exception:
        pass


def _cap_text(s: Any) -> str:
    if s is None:
        return ""
    t = str(s)
    return t[:TEXT_CAP]


def _trigrams(text: str) -> set:
    words = _WORD_RE.findall((text or "").lower())
    if len(words) >= 3:
        return {tuple(words[k : k + 3]) for k in range(len(words) - 2)}
    s = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if len(s) >= 3:
        return {s[k : k + 3] for k in range(len(s) - 2)}
    if s:
        return {s}
    return set()


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    union = len(a | b)
    if union <= 0:
        return 0.0
    return len(a & b) / union


def parse_samples(raw: str) -> list[str]:
    if raw is None:
        return []
    parts = [_cap_text(p.strip()) for p in str(raw).split("|")]
    return [p for p in parts if p][:SAMPLE_CAP]


def similarity_matrix(samples: list[str]) -> list[list[float]]:
    n = len(samples)
    grams = [_trigrams(s) for s in samples]
    w = [[0.0] * n for _ in range(n)]
    for i in range(n):
        # No self-loops: standard combinatorial Laplacian L = D - W
        # has W_ii = 0, so trace(L) = sum(degrees).
        w[i][i] = 0.0
        for j in range(i + 1, n):
            s = jaccard(grams[i], grams[j])
            w[i][j] = s
            w[j][i] = s
    return w


def degree_vector(w: list[list[float]]) -> list[float]:
    return [sum(row) for row in w]


def laplacian(w: list[list[float]], deg: list[float]) -> list[list[float]]:
    n = len(w)
    l = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            l[i][j] = (deg[i] if i == j else 0.0) - w[i][j]
    return l


def _matvec(a: list[list[float]], v: list[float]) -> list[float]:
    n = len(a)
    out = [0.0] * n
    for i in range(n):
        s = 0.0
        row = a[i]
        for j in range(n):
            s += row[j] * v[j]
        out[i] = s
    return out


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    n = math.sqrt(sum(x * x for x in v))
    return n if n > 1e-15 and math.isfinite(n) else 0.0


def power_eigenvalue(a: list[list[float]], iters: int = 80) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(iters):
        w = _matvec(a, v)
        nw = _norm(w)
        if nw <= 0.0:
            return 0.0
        lam = _dot(v, w)
        if not math.isfinite(lam):
            return 0.0
        v = [x / nw for x in w]
    return lam if math.isfinite(lam) else 0.0


def trace(a: list[list[float]]) -> float:
    return sum(a[i][i] for i in range(len(a)))


def connected_components(w: list[list[float]], threshold: float) -> list[list[int]]:
    n = len(w)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        for j in range(i + 1, n):
            if w[i][j] >= threshold:
                union(i, j)
    buckets: dict[int, list[int]] = {}
    for i in range(n):
        r = find(i)
        buckets.setdefault(r, []).append(i)
    return list(buckets.values())


def eccentricity_mean(w: list[list[float]], threshold: float) -> float:
    n = len(w)
    if n == 0:
        return 0.0
    if n == 1:
        return 0.0
    eccs: list[float] = []
    for src in range(n):
        dist = [-1] * n
        dist[src] = 0
        q = [src]
        qi = 0
        while qi < len(q):
            u = q[qi]
            qi += 1
            for v in range(n):
                if v == u:
                    continue
                if w[u][v] >= threshold and dist[v] < 0:
                    dist[v] = dist[u] + 1
                    q.append(v)
        reachable = [d for d in dist if d >= 0]
        # unreachable nodes: treat distance as n (disconnected => eccentric)
        for d in dist:
            if d < 0:
                reachable.append(n)
        eccs.append(float(max(reachable) if reachable else 0))
    return sum(eccs) / len(eccs)


def analyze(samples: list[str]) -> dict:
    n = len(samples)
    if n == 0:
        return {
            "eigval_laplacian": 0.0,
            "eigval_max_power": 0.0,
            "deg_mat_mean": 0.0,
            "eccentricity_mean": 0.0,
            "num_sem_sets": 0,
            "high_diversity": False,
            "n_samples": 0,
        }
    w = similarity_matrix(samples)
    deg = degree_vector(w)
    lap = laplacian(w, deg)
    # Exact sum of Laplacian eigenvalues = trace(L) = sum(deg)
    eig_sum = trace(lap)
    eig_max = power_eigenvalue(lap)
    deg_mean = (sum(deg) / n) if n else 0.0
    ecc = eccentricity_mean(w, ECC_THRESHOLD)
    comps = connected_components(w, COMP_THRESHOLD)
    nsets = len(comps)
    high_div = bool(n >= 2 and nsets >= 2)
    return {
        "eigval_laplacian": round(eig_sum, 6) if math.isfinite(eig_sum) else 0.0,
        "eigval_max_power": round(eig_max, 6) if math.isfinite(eig_max) else 0.0,
        "deg_mat_mean": round(deg_mean, 6) if math.isfinite(deg_mean) else 0.0,
        "eccentricity_mean": round(ecc, 6) if math.isfinite(ecc) else 0.0,
        "num_sem_sets": nsets,
        "high_diversity": high_div,
        "n_samples": n,
        "trace_equals_degree_sum": abs(eig_sum - sum(deg)) < 1e-9,
    }


def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    isolated = _hermes_root / "cache" / "scratch" / "ue-self-test-graph"
    try:
        isolated.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    os.environ["UE_CACHE_DIR"] = str(isolated)

    z = analyze([])
    check(z["num_sem_sets"] == 0 and z["high_diversity"] is False, "empty samples")

    one = analyze(["only one sample here"])
    check(one["num_sem_sets"] == 1 and one["high_diversity"] is False, "single sample")

    ident = "the cat sat on the mat today"
    same = analyze([ident, ident, ident])
    check(same["num_sem_sets"] == 1, "identical num_sem_sets")
    check(same["high_diversity"] is False, "identical high_diversity")
    check(same["trace_equals_degree_sum"] is True, "trace identity")
    check(same["eigval_laplacian"] >= 0.0, "eigval negative identical")

    diverse = analyze(
        [
            "the cat sat on the mat today",
            "quantum banana flux xylophone 999",
            "completely unrelated zebra economy report",
        ]
    )
    check(diverse["num_sem_sets"] >= 2, "diverse num_sem_sets=%s" % diverse["num_sem_sets"])
    check(diverse["high_diversity"] is True, "diverse high_diversity")
    # identical texts form a tighter (higher-degree) graph than unrelated texts
    check(same["deg_mat_mean"] >= diverse["deg_mat_mean"], "degree mean inverted")

    long_s = "token " * 20000
    long_r = analyze([long_s, "short", long_s[:100]])
    check(long_r["n_samples"] == 3, "long text n")

    none_like = analyze(["None", "null", ""])  # empty dropped by parse; here explicit
    check(none_like["n_samples"] == 3, "none-like n")

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "n_checks": 8}))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        ap = argparse.ArgumentParser(description="Graph-based UE (EigValLaplacian/DegMat/Eccentricity)")
        ap.add_argument("--samples", default="")
        ap.add_argument("--self-test", action="store_true")
        args = ap.parse_args(argv)
        if args.self_test:
            return self_test()
        samples = parse_samples(args.samples)
        rec = analyze(samples)
        rec["ts"] = __import__("time").time()
        _append_jsonl(_cache_dir() / "ue-semantic-graph.jsonl", rec)
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    except Exception:
        try:
            print(json.dumps({
                "eigval_laplacian": 0.0,
                "deg_mat_mean": 0.0,
                "eccentricity_mean": 0.0,
                "num_sem_sets": 0,
                "high_diversity": False,
                "error": "unhandled",
            }))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
