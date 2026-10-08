#!/usr/bin/env python3
"""memory-signature-rerank.py — rough-path signature re-ranking.

Hairer rough paths / Kidger CDEs. Existing memory-rough-signature.py stores
order-2 signatures; this module uses them to re-rank recall candidates.

Query path: token embeddings as a piecewise-linear path in R^2.
Candidate path: access-time sequence (t_norm, hash) in R^2.
Signature: level-1 increment + level-2 iterated integral (Chen).
Similarity: inner product of flattened, l2-normalised signatures.
Blend: 0.3 * signature_sim + 0.7 * bm25_score.

Chen identity (linear path X_t = a + t b): S^2 = 0.5 S^1 ⊗ S^1.

Usage:
  python3 memory-signature-rerank.py --query "..." --candidates candidates.json
  python3 memory-signature-rerank.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
BLEND_SIG = 0.3
BLEND_BM25 = 0.7
K1 = 1.2
B = 0.75


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


def _hash01(text: str) -> float:
    h = 2166136261
    for ch in (text or ""):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def order2_signature(path: list[list[float]]) -> list[float]:
    """Flattened (S^1, vec(S^2))."""
    if not path:
        return []
    d = len(path[0])
    s1 = [0.0] * d
    s2 = [0.0] * (d * d)
    running = [0.0] * d
    for i in range(1, len(path)):
        dx = [path[i][j] - path[i - 1][j] for j in range(d)]
        for a in range(d):
            for b in range(d):
                s2[a * d + b] += running[a] * dx[b] + 0.5 * dx[a] * dx[b]
        for j in range(d):
            running[j] += dx[j]
            s1[j] += dx[j]
    return s1 + s2


def chen_linear_ok(b: list[float], T: float = 1.0) -> bool:
    """S^2 = 0.5 S^1 ⊗ S^1 for a linear path of increment b*T."""
    path = [[0.0] * len(b), [bj * T for bj in b]]
    sig = order2_signature(path)
    d = len(b)
    s1 = sig[:d]
    s2 = sig[d:]
    for a in range(d):
        for c in range(d):
            expected = 0.5 * s1[a] * s1[c]
            if abs(s2[a * d + c] - expected) > 1e-9:
                return False
    return True


def text_path(text: str) -> list[list[float]]:
    toks = TOKEN_RE.findall((text or "").lower())
    if not toks:
        return [[0.0, 0.0]]
    n = max(len(toks) - 1, 1)
    path = []
    for i, tok in enumerate(toks):
        path.append([i / n, _hash01(tok) * 2.0 - 1.0])
    return path


def access_path(times: list[float], labels: list[str] | None = None) -> list[list[float]]:
    if not times:
        return [[0.0, 0.0]]
    t0, t1 = min(times), max(times)
    span = (t1 - t0) or 1.0
    labels = labels or [""] * len(times)
    path = []
    for t, lab in zip(times, labels):
        path.append([(t - t0) / span, _hash01(str(lab)) * 2.0 - 1.0])
    return path


def l2_normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def sig_sim(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    ua, ub = l2_normalize(a[:n]), l2_normalize(b[:n])
    return sum(x * y for x, y in zip(ua, ub))


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def bm25_scores(query: str, docs: list[str]) -> list[float]:
    q = tokenize(query)
    if not q or not docs:
        return [0.0] * len(docs)
    N = len(docs)
    toks = [tokenize(d) for d in docs]
    lens = [len(t) or 1 for t in toks]
    avgdl = sum(lens) / N
    df: dict[str, int] = {}
    for tlist in toks:
        for tok in set(tlist):
            df[tok] = df.get(tok, 0) + 1
    scores = []
    for tlist, dl in zip(toks, lens):
        tf: dict[str, int] = {}
        for tok in tlist:
            tf[tok] = tf.get(tok, 0) + 1
        s = 0.0
        for term in q:
            n_q = df.get(term, 0)
            idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
            f = tf.get(term, 0)
            denom = f + K1 * (1.0 - B + B * dl / avgdl)
            s += idf * (f * (K1 + 1.0) / denom) if denom else 0.0
        scores.append(s)
    mx = max(scores) if scores else 1.0
    mx = mx if mx > 0 else 1.0
    return [x / mx for x in scores]


def rerank(query: str, candidates: list[dict]) -> list[dict]:
    qsig = order2_signature(text_path(query))
    docs = [str(c.get("text") or c.get("content") or "") for c in candidates]
    bm = bm25_scores(query, docs)
    out = []
    for c, bscore in zip(candidates, bm):
        times = c.get("access_times") or c.get("times") or []
        labels = c.get("access_labels") or []
        if times:
            try:
                tpath = access_path([float(t) for t in times], [str(x) for x in labels] if labels else None)
            except Exception:
                tpath = text_path(str(c.get("text") or ""))
        else:
            tpath = text_path(str(c.get("text") or c.get("content") or ""))
        csig = order2_signature(tpath)
        ssim = sig_sim(qsig, csig)
        # map cosine [-1,1] → [0,1]
        s01 = 0.5 * (ssim + 1.0)
        blended = BLEND_SIG * s01 + BLEND_BM25 * float(bscore)
        out.append({
            "entry_id": str(c.get("entry_id") or c.get("id") or ""),
            "blended_score": round(blended, 6),
            "signature_sim": round(s01, 6),
            "bm25_score": round(float(bscore), 6),
        })
    out.sort(key=lambda r: -r["blended_score"])
    return out


def compute(query: str, candidates: list[dict]) -> dict:
    try:
        ranked = rerank(query, candidates)
        chen_ok = chen_linear_ok([1.0, -0.5]) and chen_linear_ok([0.3, 0.7])
        rec = {
            "query": query[:200],
            "n": len(ranked),
            "results": ranked,
            "chen_ok": chen_ok,
            "alarm": (not chen_ok),
            "reason": "chen_identity_fail" if not chen_ok else "ok",
        }
        _atomic_write(_cache_dir() / "memory-signature-rerank.json", rec)
        return rec
    except Exception as exc:
        return {"query": query[:200], "n": 0, "results": [], "fail_open": str(exc)}


def self_test() -> int:
    assert chen_linear_ok([1.0, -0.5])
    assert chen_linear_ok([0.0, 0.0])
    q = "markov mixing conductance ttl"
    cands = [
        {"entry_id": "rel", "text": "markov mixing time conductance cheeger ttl floor",
         "access_times": [1.0, 2.0, 3.0]},
        {"entry_id": "irrel", "text": "banana pancake recipe with maple syrup",
         "access_times": [1.0, 1.1]},
        {"entry_id": "mid", "text": "ttl cache expiry for memory entries",
         "access_times": [0.0, 5.0, 9.0, 12.0]},
    ]
    ranked = rerank(q, cands)
    assert len(ranked) == 3
    ids = [r["entry_id"] for r in ranked]
    assert ids[0] == "rel", ranked
    for r in ranked:
        assert 0.0 <= r["blended_score"] <= 1.0 + 1e-6
        assert 0.0 <= r["signature_sim"] <= 1.0 + 1e-6
        assert 0.0 <= r["bm25_score"] <= 1.0 + 1e-6
    empty = rerank("", [])
    assert empty == []
    print("PASS memory-signature-rerank self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--query", default="")
    ap.add_argument("--candidates", default="", help="JSON file of candidate objects")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        cands: list[dict] = []
        if args.candidates:
            raw = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = raw.get("candidates") or raw.get("results") or raw.get("entries") or []
            cands = [x for x in raw if isinstance(x, dict)]
        rec = compute(args.query, cands)
        print(json.dumps(rec, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"results": [], "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
