#!/usr/bin/env python3
"""compaction-aep-typical-set.py — AEP typical-set guard for compaction.

Cover–Thomas Asymptotic Equipartition Property: for i.i.d. source,
  P(x^n in A_ε^(n)) → 1  where
  A_ε^(n) = { x^n : |-(1/n) log p(x^n) - H| < ε }

Scores the SEQUENCE self-information rate -(1/n) log p(x^n), not per-token
surprisal. A sequence is typical iff |rate - H| < ε (Cover–Thomas A_ε^(n)).
Post-compact text is scored under the pre (source) unigram. Alarm if the
pre-sequence is typical and the post-sequence is not (typical set dropped).

Usage:
  python3 compaction-aep-typical-set.py --pre FILE --post FILE
  python3 compaction-aep-typical-set.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}")
EPS = 1.0  # nats/bits of typicality slack (bits)
ALARM_POST_FRAC = 0.5
ALARM_PRE_FRAC = 0.7


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


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text or "")


def unigram_entropy(counts: Counter) -> float:
    n = sum(counts.values()) or 1
    h = 0.0
    for c in counts.values():
        p = c / n
        if p > 0:
            h -= p * math.log2(p)
    return h


def sequence_self_info_rate(tokens: list[str], counts: Counter) -> float:
    """AEP: -(1/n) log p(x^n) under the source unigram, not per-token surprisal."""
    z = sum(counts.values()) or 1
    if not tokens:
        return 0.0
    s = 0.0
    for t in tokens:
        p = (counts[t] / z) if counts[t] else 1e-12
        s += -math.log2(max(p, 1e-12))
    return s / len(tokens)


def typical_stats(pre: str, post: str, eps: float = EPS) -> dict:
    pre_toks = tokenize(pre)
    post_toks = tokenize(post)
    counts = Counter(pre_toks)
    h = unigram_entropy(counts)
    pre_rate = sequence_self_info_rate(pre_toks, counts)
    # Post scored under the PRE source measure (compaction as a channel on X^n).
    post_rate = sequence_self_info_rate(post_toks, counts)
    pre_typical = bool(pre_toks) and abs(pre_rate - h) < eps
    post_typical = bool(post_toks) and abs(post_rate - h) < eps
    alarm = bool(pre_toks and post_toks and pre_typical and not post_typical)
    return {
        "entropy_unigram": round(h, 6),
        "eps": eps,
        "pre_self_info_rate": round(pre_rate, 6),
        "post_self_info_rate": round(post_rate, 6),
        "pre_typical": pre_typical,
        "post_typical": post_typical,
        "pre_typical_fraction": 1.0 if pre_typical else 0.0,
        "post_typical_fraction": 1.0 if post_typical else 0.0,
        "n_pre": len(pre_toks),
        "n_post": len(post_toks),
        "alarm": alarm,
        "scope": "sequence_aep",
    }


def compute(pre: str = "", post: str = "") -> dict:
    try:
        if not pre and not post:
            cache = _cache_dir()
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
        rec = typical_stats(pre, post)
        rec["ts"] = time.time()
        _atomic_write(_cache_dir() / "compaction-aep-typical-set.json", rec)
        return rec
    except Exception as exc:
        return {
            "entropy_unigram": 0.0,
            "pre_typical_fraction": 0.0,
            "post_typical_fraction": 0.0,
            "alarm": False,
            "fail_open": str(exc),
        }


def self_test() -> int:
    # Repeated natural-ish text: most tokens typical
    words = (["the", "mixing", "time", "of", "the", "chain", "is", "bounded"] * 20)
    pre = " ".join(words)
    rec = typical_stats(pre, pre)
    assert rec["n_pre"] > 0
    assert rec["pre_typical"] is True  # empirical measure: rate == H
    assert rec["alarm"] is False
    # Drop typical sequence, keep only a rare nonce → post not in A_ε
    post = "xyzzyplugh xyzzyplugh xyzzyplugh"
    rec2 = typical_stats(pre + " xyzzyplugh", post)
    assert rec2["post_typical"] is False
    assert rec2["alarm"] is True
    empty = typical_stats("", "")
    assert empty["n_pre"] == 0
    print("PASS compaction-aep-typical-set self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pre", default="")
    ap.add_argument("--post", default="")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        pre = Path(args.pre).read_text(encoding="utf-8", errors="replace") if args.pre else ""
        post = Path(args.post).read_text(encoding="utf-8", errors="replace") if args.post else ""
        print(json.dumps(compute(pre, post), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"alarm": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
