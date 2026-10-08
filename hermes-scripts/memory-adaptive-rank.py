#!/usr/bin/env python3
"""memory-adaptive-rank.py — concentration-bound adaptive SVD rank.

Vershynin HDP / Wainwright–Jordan: choose the smallest k such that
  ||X - X_k||_F^2 / ||X||_F^2 <= delta
with delta=0.1 (retain 90% of Frobenius energy).

Truncation error e_k = sum_{i>k} sigma_i^2 concentrates around its mean
with deviation O(sqrt(n) * sigma_{k+1}) (matrix concentration / operator
norm of the tail). Report [e_k - c*dev, e_k + c*dev].

Stdlib-only: singular values from cache, or power-iteration+deflation on
a hashed document-term matrix.

Usage:
  python3 memory-adaptive-rank.py
  python3 memory-adaptive-rank.py --singular 10,5,2,1,0.4,0.1
  python3 memory-adaptive-rank.py --self-test
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

DELTA = 0.1
CONC_C = 1.0
TOKEN_RE = re.compile(r"[a-z]{3,}")
HASH_DIM = 32


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


def select_rank(sigmas: list[float], delta: float = DELTA, n_rows: int | None = None) -> dict:
    sigmas = [max(0.0, float(s)) for s in (sigmas or []) if math.isfinite(float(s) if s is not None else 0)]
    sigmas = sorted((s for s in sigmas if s >= 0.0), reverse=True)
    if not sigmas:
        return {
            "selected_rank": 0,
            "variance_explained": 0.0,
            "truncation_error": 0.0,
            "concentration_interval": [0.0, 0.0],
        }
    energy = [s * s for s in sigmas]
    total = sum(energy) or 1.0
    k_star = len(sigmas)
    explained = 1.0
    trunc = 0.0
    for k in range(1, len(sigmas) + 1):
        tail = sum(energy[k:])
        ratio = tail / total
        if ratio <= delta:
            k_star = k
            explained = 1.0 - ratio
            trunc = tail
            break
    else:
        k_star = len(sigmas)
        explained = 1.0
        trunc = 0.0
    sigma_next = sigmas[k_star] if k_star < len(sigmas) else 0.0
    n = int(n_rows) if n_rows else len(sigmas)
    dev = CONC_C * math.sqrt(max(n, 1)) * sigma_next
    lo = max(0.0, trunc - dev)
    hi = trunc + dev
    return {
        "selected_rank": int(k_star),
        "variance_explained": round(explained, 6),
        "truncation_error": round(trunc, 6),
        "concentration_interval": [round(lo, 6), round(hi, 6)],
        "delta": delta,
        "sigma_next": round(sigma_next, 6),
        "n": n,
    }


def _hash_embed(text: str, dim: int = HASH_DIM) -> list[float]:
    vec = [0.0] * dim
    for tok in TOKEN_RE.findall((text or "").lower()):
        h = 2166136261
        for ch in tok:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        vec[h % dim] += 1.0
    nrm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / nrm for x in vec]


def _matvec(A: list[list[float]], x: list[float]) -> list[float]:
    return [sum(row[j] * x[j] for j in range(len(x))) for row in A]


def _transpose(A: list[list[float]]) -> list[list[float]]:
    if not A:
        return []
    m, n = len(A), len(A[0])
    return [[A[i][j] for i in range(m)] for j in range(n)]


def power_singular_values(rows: list[list[float]], k: int = 12, iters: int = 40) -> list[float]:
    """Top-k singular values of row-matrix via power iteration + deflation (XtX)."""
    if not rows or not rows[0]:
        return []
    m, n = len(rows), len(rows[0])
    # Gram G = X^T X  (n x n), n is HASH_DIM so small
    G = [[0.0] * n for _ in range(n)]
    for row in rows:
        for i in range(n):
            ri = row[i]
            if ri == 0.0:
                continue
            Gi = G[i]
            for j in range(n):
                Gi[j] += ri * row[j]
    sigmas: list[float] = []
    k = min(k, n, m)
    # Working copy of G for deflation
    for _ in range(k):
        v = [1.0] * n
        v[_ % n] = 1.0
        nrm = math.sqrt(sum(x * x for x in v)) or 1.0
        v = [x / nrm for x in v]
        lam = 0.0
        for _it in range(iters):
            w = _matvec(G, v)
            lam = sum(w[i] * v[i] for i in range(n))
            nrm = math.sqrt(sum(x * x for x in w)) or 1.0
            v = [x / nrm for x in w]
        lam = max(lam, 0.0)
        sigmas.append(math.sqrt(lam))
        # Hotelling deflation: G <- G - lam v v^T
        for i in range(n):
            for j in range(n):
                G[i][j] -= lam * v[i] * v[j]
    return sigmas


def load_texts() -> list[str]:
    texts: list[str] = []
    staging = _hermes_base / "memory-facts" / "staging.md"
    try:
        if staging.exists():
            for line in staging.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s.startswith("-") and len(s) > 12:
                    texts.append(s)
    except Exception:
        pass
    return texts[-80:]


def load_cached_sigmas() -> list[float]:
    for name in ("memory-svd-singular.json", "memory-eckart-young.json"):
        p = _cache_dir() / name
        try:
            if not p.exists():
                continue
            obj = json.loads(p.read_text(encoding="utf-8"))
            for key in ("singular_values", "singular_all", "S"):
                xs = obj.get(key)
                if isinstance(xs, list) and xs:
                    return [float(x) for x in xs]
        except Exception:
            continue
    return []


def compute(sigmas: list[float] | None = None) -> dict:
    try:
        if sigmas is not None:
            rec = select_rank(sigmas)
        else:
            cached = load_cached_sigmas()
            if cached:
                rec = select_rank(cached)
            else:
                texts = load_texts()
                if len(texts) < 2:
                    rec = select_rank([])
                    rec["reason"] = "insufficient_memory"
                else:
                    rows = [_hash_embed(t) for t in texts]
                    sv = power_singular_values(rows, k=min(12, len(rows)))
                    rec = select_rank(sv, n_rows=len(rows))
        rec["ts"] = time.time()
        _atomic_write(_cache_dir() / "memory-adaptive-rank.json", rec)
        return rec
    except Exception as exc:
        return {
            "selected_rank": 0,
            "variance_explained": 0.0,
            "truncation_error": 0.0,
            "concentration_interval": [0.0, 0.0],
            "fail_open": str(exc),
        }


def self_test() -> int:
    # Geometric spectrum: energy concentrates in first few
    sig = [10.0, 5.0, 2.0, 1.0, 0.4, 0.1, 0.05]
    rec = select_rank(sig, delta=0.1)
    total = sum(s * s for s in sig)
    k = rec["selected_rank"]
    tail = sum(s * s for s in sig[k:])
    assert tail / total <= 0.1 + 1e-9, rec
    assert rec["variance_explained"] >= 0.9
    assert rec["truncation_error"] >= 0
    lo, hi = rec["concentration_interval"]
    assert lo <= rec["truncation_error"] <= hi
    # Empty
    empty = select_rank([])
    assert empty["selected_rank"] == 0
    # Power iteration on orthogonal-ish rows
    rows = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.5, 0.0],
        [0.0, 0.0, 0.0, 0.1],
    ]
    sv = power_singular_values(rows, k=4, iters=60)
    assert sv[0] >= sv[-1]
    rec2 = select_rank(sv)
    assert 1 <= rec2["selected_rank"] <= 4
    print("PASS memory-adaptive-rank self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--singular", default="", help="Comma-separated singular values")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        xs = None
        if args.singular.strip():
            xs = [float(t) for t in args.singular.split(",") if t.strip()]
        print(json.dumps(compute(xs), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "selected_rank": 0,
            "variance_explained": 0.0,
            "truncation_error": 0.0,
            "concentration_interval": [0.0, 0.0],
            "fail_open": str(exc),
        }))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
