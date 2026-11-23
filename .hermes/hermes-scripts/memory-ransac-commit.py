#!/usr/bin/env python3
"""memory-ransac-commit.py — RANSAC-style outlier gate before memory commit.

Szeliski: fit a simple location model (coordinate-wise median of hashed TF
vectors) and reject geometric outliers. Inlier iff residual ≤ INLIER_K * MAD
(or residual ≤ ABS_FLOOR when MAD is 0).

Hard core: INLIER_K = 2.5 and ABS_FLOOR = 0.15 are named, testable constants.

Usable standalone or as a post_tool_call plugin (fail-open, never raises).

Usage:
  python3 memory-ransac-commit.py --check "candidate fact"
  python3 memory-ransac-commit.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path


INLIER_K = 2.5
ABS_FLOOR = 0.15
TOKEN_RE = re.compile(r"[a-z]{3,}")
DIM = 16


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def hash_embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    toks = TOKEN_RE.findall((text or "").lower())
    if not toks:
        return vec
    for tok in toks:
        h = 2166136261
        for ch in tok:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        vec[h % dim] += 1.0
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    m = len(ys) // 2
    if len(ys) % 2:
        return ys[m]
    return 0.5 * (ys[m - 1] + ys[m])


def mad(xs: list[float], med: float) -> float:
    return median([abs(x - med) for x in xs])


def residual(vec: list[float], center: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec, center)))


def fit_center(corpus: list[str]) -> list[float]:
    if not corpus:
        return [0.0] * DIM
    embs = [hash_embed(t) for t in corpus]
    return [median([e[j] for e in embs]) for j in range(DIM)]


def inlier_threshold(corpus: list[str], center: list[float]) -> float:
    embs = [hash_embed(t) for t in corpus] if corpus else []
    res = [residual(e, center) for e in embs]
    m = mad(res, median(res)) if res else 0.0
    return max(ABS_FLOOR, INLIER_K * (1.4826 * m if m > 0 else 0.0) or ABS_FLOOR)


def is_inlier(text: str, corpus: list[str]) -> dict:
    center = fit_center(corpus)
    thr = inlier_threshold(corpus, center)
    r = residual(hash_embed(text), center)
    near_dup = False
    try:
        import importlib.util as _ilu
        _ep = hermes_home() / "hermes-scripts" / "memory-eckart-young.py"
        if _ep.exists():
            _es = _ilu.spec_from_file_location("memory_eckart_young", str(_ep))
            if _es and _es.loader:
                _em = _ilu.module_from_spec(_es)
                _es.loader.exec_module(_em)
                _pr = _em.project(text)
                near_dup = bool(_pr.get("near_duplicate"))
    except Exception:
        near_dup = False
    return {
        "inlier": bool(r <= thr),
        "residual": round(r, 6),
        "threshold": round(thr, 6),
        "INLIER_K": INLIER_K,
        "ABS_FLOOR": ABS_FLOOR,
        "n_corpus": len(corpus),
        "svd_near_duplicate": near_dup,
    }


def load_corpus() -> list[str]:
    texts: list[str] = []
    staging = hermes_home() / "memory-facts" / "staging.md"
    try:
        if staging.exists():
            for line in staging.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("-"):
                    texts.append(line.strip())
    except Exception:
        pass
    return texts[-200:]


def self_test() -> int:
    # Tight cluster: identical facts → residual 0 is an inlier.
    corpus = ["user prefers dark mode in the editor"] * 5
    assert INLIER_K == 2.5 and ABS_FLOOR == 0.15
    ok = is_inlier(corpus[0], corpus)
    assert ok["inlier"] is True, ok
    assert ok["residual"] <= 1e-12
    assert ok["threshold"] >= ABS_FLOOR
    far = is_inlier("xyzzy quantum banana flux 99999 qqq", corpus)
    assert far["threshold"] == ABS_FLOOR or far["threshold"] >= ABS_FLOOR
    assert far["INLIER_K"] == 2.5
    assert far["residual"] > ok["residual"]
    print("PASS memory-ransac-commit self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", default="", help="Candidate fact text")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        if not args.check:
            print(json.dumps({"ok": True, "INLIER_K": INLIER_K, "ABS_FLOOR": ABS_FLOOR}))
            return 0
        print(json.dumps(is_inlier(args.check, load_corpus()), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"inlier": True, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
