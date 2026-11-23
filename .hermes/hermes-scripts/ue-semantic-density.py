#!/usr/bin/env python3
"""ue-semantic-density.py — SemanticDensity (Qiu et al., 2024) blackbox adaptation.

Qiu et al. estimate confidence from how tightly sampled meanings cluster in
embedding space. Hermes is blackbox (no embeddings, typically one response),
so this script lifts the *density* idea onto a character-trigram Jaccard
overlap graph of sentences in a single response.

This is a heuristic adaptation: original embedding-space concentration
guarantees do NOT transfer (theory-to-implementation: label as belt).

Hard core (testable):
  semantic_density ∈ [0, 1]
  claim_count >= 0 (int)
  unique_claim_ratio ∈ [0, 1]
  high_density is bool (semantic_density > 0.5)
  never raises on empty / short / huge input (H-I7 for the scoring path)

Belt:
  sentence split on . ! ?
  edge if Jaccard > threshold (default 0.2)
  unique claim if Jaccard < 0.1 with every other sentence
  char-trigram features (not model embeddings)

Interpretation:
  High density = redundant/repetitive (low information; possibly looping)
  Low density  = diverse claims (high-quality OR scatter-shot)

Usage:
  python3 ue-semantic-density.py --response 'text' [--threshold 0.2]
  python3 ue-semantic-density.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

DEFAULT_THRESHOLD = 0.2
UNIQUE_JACCARD = 0.1
HIGH_DENSITY = 0.5
# ASCII .!? plus CJK fullwidth 。！？ (same role; spec belt, not a new invariant)
_SENT_SPLIT = re.compile(r"[.!?。！？]+")
_WS = re.compile(r"\s+")


def _clip01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def split_sentences(text: str) -> list[str]:
    """Split on . ! ? ; drop empty / punctuation-only fragments."""
    if text is None:
        return []
    raw = str(text).replace("\r\n", "\n").replace("\r", "\n")
    parts = _SENT_SPLIT.split(raw)
    out: list[str] = []
    for p in parts:
        s = _WS.sub(" ", p).strip()
        if s:
            out.append(s)
    return out


def char_trigrams(s: str) -> set[str]:
    """Character trigrams; fall back to the whole string if too short."""
    t = _WS.sub(" ", (s or "").lower()).strip()
    if not t:
        return set()
    if len(t) < 3:
        return {t}
    return {t[i : i + 3] for i in range(len(t) - 2)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 0.0
    return inter / union


def semantic_density_score(response: str, threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Compute SemanticDensity graph metrics. Never raises on bad input."""
    try:
        th = float(threshold)
    except (TypeError, ValueError):
        th = DEFAULT_THRESHOLD
    if not math.isfinite(th):
        th = DEFAULT_THRESHOLD
    th = _clip01(th)

    try:
        sentences = split_sentences(response if response is not None else "")
    except Exception:
        sentences = []

    n = len(sentences)
    grams = [char_trigrams(s) for s in sentences]

    edges = 0
    unique_flags: list[bool] = [True] * n
    max_edges = n * (n - 1) // 2

    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard(grams[i], grams[j])
            if sim > th:
                edges += 1
            if sim >= UNIQUE_JACCARD:
                unique_flags[i] = False
                unique_flags[j] = False

    if max_edges <= 0:
        density = 0.0
    else:
        density = _clip01(edges / max_edges)

    # Distinct sentences after whitespace-normalized lowercase.
    distinct = { _WS.sub(" ", s).strip().lower() for s in sentences }
    claim_count = len(distinct)

    if n == 0:
        unique_ratio = 0.0
    else:
        unique_ratio = _clip01(sum(1 for u in unique_flags if u) / n)

    return {
        "semantic_density": round(density, 6),
        "claim_count": int(claim_count),
        "unique_claim_ratio": round(unique_ratio, 6),
        "high_density": bool(density > HIGH_DENSITY),
        "sentence_count": int(n),
        "edge_count": int(edges),
        "threshold": th,
    }


def _emit(obj: dict) -> int:
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    return 0


def self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        if not cond:
            failures.append(f"{name}: {detail}" if detail else name)

    # 1. Empty string — no crash, ranges hold
    empty = semantic_density_score("")
    check("empty_density", empty["semantic_density"] == 0.0, str(empty))
    check("empty_count", empty["claim_count"] == 0, str(empty))
    check("empty_unique", empty["unique_claim_ratio"] == 0.0, str(empty))
    check("empty_high", empty["high_density"] is False, str(empty))
    check("empty_json", isinstance(json.loads(json.dumps(empty)), dict))

    none_out = semantic_density_score(None)  # type: ignore[arg-type]
    check("none_ok", none_out["claim_count"] == 0)

    # 2. Single-word / no terminator
    one = semantic_density_score("hello")
    check("one_density", one["semantic_density"] == 0.0, str(one))
    check("one_count", one["claim_count"] == 1, str(one))
    check("one_unique", one["unique_claim_ratio"] == 1.0, str(one))
    check("one_high", one["high_density"] is False)

    short = semantic_density_score("hi")
    check("short_count", short["claim_count"] == 1, str(short))
    check("short_range", 0.0 <= short["semantic_density"] <= 1.0)

    # 3. Diverse vs repetitive
    diverse = semantic_density_score(
        "The cat sat on the mat. Quantum chromodynamics confines quarks. "
        "Paris is the capital of France. Binary search runs in log n time."
    )
    check("diverse_lowish", diverse["semantic_density"] < 0.5, str(diverse))
    check("diverse_claims", diverse["claim_count"] >= 3, str(diverse))

    repetitive = semantic_density_score(
        "The cat sat on the mat. The cat sat on a mat. "
        "The cat sits on the mat. The cat sat on the mat again."
    )
    check(
        "repetitive_higher",
        repetitive["semantic_density"] > diverse["semantic_density"],
        f"rep={repetitive['semantic_density']} div={diverse['semantic_density']}",
    )

    identical = semantic_density_score("Same claim here. Same claim here. Same claim here.")
    check("identical_dense", identical["semantic_density"] >= 0.9, str(identical))
    check("identical_high", identical["high_density"] is True, str(identical))
    check("identical_distinct", identical["claim_count"] == 1, str(identical))

    # 4. Hard-core ranges
    samples = [
        "",
        "x",
        "A. B. C.",
        "Hello world! How are you? Fine.",
        "a" * 200,
        "Word " * 50,
        "Claim one. Claim two. Claim three.",
    ]
    for s in samples:
        r = semantic_density_score(s)
        check("density_range", 0.0 <= r["semantic_density"] <= 1.0, str(r))
        check("unique_range", 0.0 <= r["unique_claim_ratio"] <= 1.0, str(r))
        check("count_nonneg", r["claim_count"] >= 0, str(r))
        check("high_bool", isinstance(r["high_density"], bool), str(r))
        try:
            json.loads(json.dumps(r))
        except Exception as e:
            check("jsonable", False, str(e))

    # 5. Threshold clamp
    tneg = semantic_density_score("A. B.", threshold=-1)
    check("th_neg", tneg["threshold"] == 0.0, str(tneg))
    tbig = semantic_density_score("A. B.", threshold=9)
    check("th_big", tbig["threshold"] == 1.0, str(tbig))

    # 6. Long input (< 5s is checked by the caller; we just must finish)
    chunks = []
    acc = 0
    i = 0
    while acc < 10000:
        piece = f"Sentence {i} discusses item {i} in domain {i % 17}. "
        chunks.append(piece)
        acc += len(piece)
        i += 1
    long_out = semantic_density_score("".join(chunks))
    check("long_range", 0.0 <= long_out["semantic_density"] <= 1.0, str(long_out))
    check("long_count", long_out["claim_count"] > 1, str(long_out))

    # CJK terminators split into distinct claims
    cjk = semantic_density_score("東京は日本の首都です。Paris is not Tokyo.")
    check("cjk_split", cjk["sentence_count"] >= 2, str(cjk))
    check("cjk_claims", cjk["claim_count"] >= 2, str(cjk))

    # 7. JSON schema keys
    required = {"semantic_density", "claim_count", "unique_claim_ratio", "high_density"}
    check("keys", required <= set(empty.keys()), str(empty.keys()))

    if failures:
        print(json.dumps({"ok": False, "failures": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "tests": "pass", "n_failures": 0}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SemanticDensity (Qiu et al. 2024) blackbox proxy")
    p.add_argument("--response", default=None, help="Response text to score")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.response is None:
        p.print_usage(sys.stderr)
        print("error: --response is required unless --self-test", file=sys.stderr)
        return 2
    try:
        result = semantic_density_score(args.response, threshold=args.threshold)
        return _emit(result)
    except Exception as e:
        # Scoring path must not crash the caller (H-I7-shaped).
        fallback = {
            "semantic_density": 0.0,
            "claim_count": 0,
            "unique_claim_ratio": 0.0,
            "high_density": False,
            "error": type(e).__name__,
        }
        return _emit(fallback)


if __name__ == "__main__":
    sys.exit(main())
