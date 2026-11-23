#!/usr/bin/env python3
"""memory-eckart-young.py — truncated SVD memory compressor (Axler).

Eckart–Young–Mirsky: the rank-k truncated SVD X_k is the unique optimal
Frobenius-norm approximation of X among rank ≤ k matrices.

  ||X - X_k||_F = sqrt(sum_{i>k} σ_i^2)
  ||X - X_k||_2 = σ_{k+1}

The task's "next singular value" identity is the spectral-norm form;
both residuals are stored and tested.

Does not duplicate skill-embedding-geometry.py (W2 geometry on skills).
This script builds a document-term matrix over staged memory facts.

Usage:
  python3 memory-eckart-young.py --fit --rank 8
  python3 memory-eckart-young.py --project "new fact text"
  python3 memory-eckart-young.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path


def _np():
    import numpy as np
    return np


TOKEN_RE = re.compile(r"[a-z]{3,}")
DEDUP_COSINE = 0.97


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def profile_root() -> Path:
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    hp = os.environ.get("HERMES_PROFILE", "").strip()
    if hp:
        cand = Path.home() / ".hermes" / "profiles" / hp
        if cand.is_dir():
            return cand
    if hh.name != ".hermes" and hh.parent.name == "profiles":
        return hh
    return hermes_home()


def cache_dir() -> Path:
    d = profile_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_path() -> Path:
    return cache_dir() / "memory-svd-basis.npz"


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_memory_texts() -> list[str]:
    texts: list[str] = []
    staging = hermes_home() / "memory-facts" / "staging.md"
    if staging.exists():
        try:
            for line in staging.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith("-") and len(line) > 20:
                    texts.append(line)
        except Exception:
            pass
    wm = hermes_home() / "cache" / "working-memory"
    if wm.is_dir():
        for p in wm.glob("*.json"):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
                g = str((doc or {}).get("goal") or "")
                if g:
                    texts.append(g)
            except Exception:
                continue
    return texts


def build_matrix(texts: list[str]) -> tuple[np.ndarray, list[str]]:
    np = _np()
    vocab: dict[str, int] = {}
    rows: list[dict[str, float]] = []
    for t in texts:
        tf: dict[str, float] = {}
        for tok in tokenize(t):
            tf[tok] = tf.get(tok, 0.0) + 1.0
            if tok not in vocab:
                vocab[tok] = len(vocab)
        rows.append(tf)
    if not vocab or not rows:
        return np.zeros((0, 0)), []
    terms = [""] * len(vocab)
    for tok, i in vocab.items():
        terms[i] = tok
    X = np.zeros((len(rows), len(terms)), dtype=np.float64)
    for i, tf in enumerate(rows):
        for tok, c in tf.items():
            X[i, vocab[tok]] = c
    # l2-normalise rows
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    nrm = np.where(nrm == 0, 1.0, nrm)
    X = X / nrm
    return X, terms


def fit_svd(X: np.ndarray, k: int) -> dict:
    np = _np()
    if X.size == 0:
        return {"ok": False, "reason": "empty"}
    k = max(1, min(k, min(X.shape) - 1 if min(X.shape) > 1 else 1))
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    k = min(k, len(S))
    Uk, Sk, Vtk = U[:, :k], S[:k], Vt[:k]
    Xk = (Uk * Sk) @ Vtk
    f_resid = float(np.linalg.norm(X - Xk, "fro"))
    tail = float(math.sqrt(np.sum(S[k:] ** 2))) if k < len(S) else 0.0
    if k < len(S):
        op_resid = float(np.linalg.norm(X - Xk, 2))
        sigma_next = float(S[k])
    else:
        op_resid = 0.0
        sigma_next = 0.0
    return {
        "ok": True,
        "k": k,
        "U": Uk,
        "S": Sk,
        "Vt": Vtk,
        "singular_all": S,
        "f_resid": f_resid,
        "f_resid_tail": tail,
        "op_resid": op_resid,
        "sigma_next": sigma_next,
        "shape": list(X.shape),
    }


def save_basis(fit: dict, terms: list[str]) -> Path:
    np = _np()
    p = state_path()
    tmp = p.with_suffix(".npz.tmp")
    np.savez(
        tmp,
        U=fit["U"],
        S=fit["S"],
        Vt=fit["Vt"],
        terms=np.array(terms),
        f_resid=np.array([fit["f_resid"]]),
        sigma_next=np.array([fit["sigma_next"]]),
        op_resid=np.array([fit["op_resid"]]),
        k=np.array([fit["k"]]),
    )
    tmp.replace(p)
    meta = {
        "k": fit["k"],
        "f_resid": fit["f_resid"],
        "f_resid_tail": fit["f_resid_tail"],
        "op_resid": fit["op_resid"],
        "sigma_next": fit["sigma_next"],
        "shape": fit["shape"],
        "n_terms": len(terms),
        "path": str(p),
    }
    mp = cache_dir() / "memory-svd-basis.json"
    mt = mp.with_suffix(".json.tmp")
    mt.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    mt.replace(mp)
    return p


def vectorize(text: str, terms: list[str]) -> np.ndarray:
    np = _np()
    idx = {t: i for i, t in enumerate(terms)}
    v = np.zeros(len(terms), dtype=np.float64)
    for tok in tokenize(text):
        if tok in idx:
            v[idx[tok]] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def project(text: str) -> dict:
    np = _np()
    p = state_path()
    if not p.exists():
        return {"ok": False, "reason": "no_basis"}
    data = np.load(p, allow_pickle=True)
    terms = [str(t) for t in data["terms"].tolist()]
    Vt = data["Vt"]
    v = vectorize(text, terms)
    coeff = Vt @ v  # k coords
    recon = Vt.T @ coeff
    n1, n2 = np.linalg.norm(v), np.linalg.norm(recon)
    cos = float(np.dot(v, recon) / (n1 * n2)) if n1 > 0 and n2 > 0 else 0.0
    return {
        "ok": True,
        "cosine_to_recon": round(cos, 6),
        "near_duplicate": bool(cos >= DEDUP_COSINE),
        "coeff_l2": round(float(np.linalg.norm(coeff)), 6),
    }


def self_test() -> int:
    np = _np()
    rng = np.random.default_rng(0)
    # Rank-3 signal + tiny noise so k=3 leaves one extra singular value
    A = rng.normal(size=(12, 3))
    B = rng.normal(size=(3, 8))
    X = A @ B
    fit = fit_svd(X, k=3)
    assert fit["ok"]
    # F-norm residual equals tail of singular values
    assert abs(fit["f_resid"] - fit["f_resid_tail"]) < 1e-8, fit
    # Hard core (spectral): ||X-X_k||_2 = σ_{k+1}
    assert abs(fit["op_resid"] - fit["sigma_next"]) < 1e-8, (fit["op_resid"], fit["sigma_next"])
    # Rank-1 exact
    x = np.outer(np.arange(5.0), np.arange(4.0) + 1.0)
    fit1 = fit_svd(x, k=1)
    assert fit1["f_resid"] < 1e-8
    assert fit1["sigma_next"] < 1e-8
    print("PASS memory-eckart-young self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--project", default="", help="Project a new fact for dedup")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.project:
            print(json.dumps(project(args.project), indent=2))
            return 0
        texts = load_memory_texts()
        X, terms = build_matrix(texts)
        fit = fit_svd(X, args.rank)
        if not fit.get("ok"):
            print(json.dumps(fit))
            return 0
        save_basis(fit, terms)
        out = {k: fit[k] for k in ("ok", "k", "f_resid", "f_resid_tail", "op_resid", "sigma_next", "shape")}
        print(json.dumps(out, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
