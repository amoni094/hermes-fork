#!/usr/bin/env python3
"""eval-compaction-distortion-gate.py — character-level Jaccard distortion gate.

Rate-distortion (Cover–Thomas Ch 10): compaction is a channel X → Y with
rate R = |Y| / |X| (token or char ratio) and distortion d(x, y).

This gate uses a stdlib-only character-level Jaccard:
    J = |shingles(x) ∩ shingles(y)| / |shingles(x) ∪ shingles(y)|
    d  = 1 - J
Default shingle size is 1 (character set). --ngram N uses character n-grams.

Alarm if d > threshold (default 0.50). Compaction may add no information
(DPI); this gate only flags excessive *loss*.

Usage:
  python3 eval-compaction-distortion-gate.py --pre FILE --post FILE
  python3 eval-compaction-distortion-gate.py --pre-text '...' --post-text '...'
  python3 eval-compaction-distortion-gate.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_THRESHOLD = 0.50


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def shingles(text: str, n: int = 1) -> set:
    s = text or ""
    if n <= 1:
        return set(s)
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def distortion(pre: str, post: str, ngram: int = 1) -> dict:
    pre = pre or ""
    post = post or ""
    ja = jaccard(shingles(pre, 1), shingles(post, 1))
    jn = jaccard(shingles(pre, ngram), shingles(post, ngram)) if ngram != 1 else ja
    d_char = 1.0 - ja
    d_ngram = 1.0 - jn
    rate = (len(post) / len(pre)) if pre else (1.0 if not post else 0.0)
    return {
        "char_jaccard": round(ja, 6),
        "ngram_jaccard": round(jn, 6),
        "ngram": ngram,
        "distortion": round(d_char, 6),
        "distortion_ngram": round(d_ngram, 6),
        "rate_char": round(rate, 6),
        "n_pre_chars": len(pre),
        "n_post_chars": len(post),
    }


def gate(pre: str, post: str, threshold: float = DEFAULT_THRESHOLD, ngram: int = 1) -> dict:
    rec = distortion(pre, post, ngram=ngram)
    rec["threshold"] = threshold
    rec["alarm"] = rec["distortion"] > threshold
    rec["alarm_ngram"] = rec["distortion_ngram"] > threshold
    rec["reason"] = (
        "distortion_exceeds_threshold" if rec["alarm"] else "ok"
    )
    return rec


def self_test() -> int:
    identical = gate("abcabc", "abcabc", threshold=0.1)
    assert identical["distortion"] == 0.0
    assert identical["alarm"] is False
    empty = gate("", "", threshold=0.1)
    assert empty["char_jaccard"] == 1.0
    dropped = gate("the deploy code for region 0 is Z6305", "ok", threshold=0.5)
    assert dropped["distortion"] > 0.5
    assert dropped["alarm"] is True
    # Alphabet overlap can stay high while n-grams collapse — ngram gate is stricter.
    shuffled = gate("abcd" * 20, "dcba" * 20, threshold=0.2, ngram=3)
    assert shuffled["distortion"] == 0.0  # same charset
    assert shuffled["distortion_ngram"] > 0.0
    print("PASS eval-compaction-distortion-gate self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pre", default="")
    ap.add_argument("--post", default="")
    ap.add_argument("--pre-text", default="")
    ap.add_argument("--post-text", default="")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--ngram", type=int, default=1)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    pre = args.pre_text
    post = args.post_text
    if args.pre:
        pre = Path(args.pre).read_text(encoding="utf-8", errors="replace")
    if args.post:
        post = Path(args.post).read_text(encoding="utf-8", errors="replace")
    if not pre and not post:
        cache = _profile_root() / "cache"
        for name in ("pre-compact-context.txt", "pre-compact-annotate.txt"):
            p = cache / name
            if p.exists():
                pre = p.read_text(encoding="utf-8", errors="replace")
                break
        for name in ("post-compact-context.txt", "compacted-context.txt"):
            p = cache / name
            if p.exists():
                post = p.read_text(encoding="utf-8", errors="replace")
                break
    rec = gate(pre, post, threshold=args.threshold, ngram=args.ngram)
    print(json.dumps(rec, indent=2))
    return 1 if rec.get("alarm") else 0


if __name__ == "__main__":
    raise SystemExit(main())
