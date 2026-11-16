#!/usr/bin/env python3
"""score-compaction-rouge.py — stdlib-only ROUGE-1 / ROUGE-L compaction scorer.

Coverage vs fabrication for compaction (X → Y):
    rouge1_r  = clipped unigram overlap / |X|   (source n-grams kept)
    rouge1_p  = clipped unigram overlap / |Y|   (summary n-grams from source)
    rougeL_*  = LCS(token seq X, token seq Y) ratios (same P/R split)

Tokenize by whitespace split. No rouge-score pip package.

Alarms:
    alarm_fabrication  if rouge1_p < 0.3
    alarm_coverage     if rouge1_r < 0.2

LCS is O(|X|·|Y|). If either side has >10000 tokens, sample to 5000
(2500 from each end) and set lcs_sampled=true.

Usage:
  python3 score-compaction-rouge.py --pre FILE --post FILE
  python3 score-compaction-rouge.py --pre-text '...' --post-text '...'
  python3 score-compaction-rouge.py --batch < records.jsonl
  python3 score-compaction-rouge.py --self-test
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path

LCS_LIMIT = 10000
LCS_KEEP_EACH_END = 2500  # 2500+2500 = 5000
FABRICATION_P = 0.3
COVERAGE_R = 0.2

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)


def _profile_root() -> Path:
    base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    profile = os.environ.get("HERMES_PROFILE", "")
    if profile and "profiles" not in str(base):
        return base / "profiles" / profile
    return base


def tokenize(text: str) -> list:
    return (text or "").lower().split()


def _f1(p: float, r: float) -> float:
    s = p + r
    if s <= 0.0:
        return 0.0
    return 2.0 * p * r / s


def rouge1_pr(pre_toks: list, post_toks: list) -> tuple:
    ref = Counter(pre_toks)
    hyp = Counter(post_toks)
    overlap = sum((ref & hyp).values())
    n_ref = len(pre_toks)
    n_hyp = len(post_toks)
    if n_ref == 0 and n_hyp == 0:
        return 1.0, 1.0, 0
    if n_ref == 0:
        return 0.0, 1.0, 0
    if n_hyp == 0:
        return 1.0, 0.0, 0
    r = overlap / n_ref
    p = overlap / n_hyp
    return p, r, overlap


def _sample_ends(toks: list) -> tuple:
    n = len(toks)
    if n <= LCS_LIMIT:
        return toks, False
    k = LCS_KEEP_EACH_END
    if 2 * k >= n:
        return toks, False
    return toks[:k] + toks[-k:], True


def lcs_length(a: list, b: list) -> tuple:
    a, sa = _sample_ends(a)
    b, sb = _sample_ends(b)
    sampled = sa or sb
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0, sampled, len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n
    prev = [0] * (n + 1)
    cur = [0] * (n + 1)
    for i in range(1, m + 1):
        bi = b[i - 1]
        for j in range(1, n + 1):
            if bi == a[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                x = prev[j]
                y = cur[j - 1]
                cur[j] = max(x, y)
        prev, cur = cur, prev
    return prev[n], sampled, len(a), len(b)


def rougeL_pr(pre_toks: list, post_toks: list) -> tuple:
    n_ref_orig = len(pre_toks)
    n_hyp_orig = len(post_toks)
    L, sampled, n_ref_eff, n_hyp_eff = lcs_length(pre_toks, post_toks)
    # Use effective (post-sample) lengths as denominators so P+R are consistent
    # with the LCS computation. n_ref_eff <= n_ref_orig, n_hyp_eff <= n_hyp_orig.
    n_ref = n_ref_eff if sampled else n_ref_orig
    n_hyp = n_hyp_eff if sampled else n_hyp_orig
    if n_ref == 0 and n_hyp == 0:
        return 1.0, 1.0, L, sampled
    if n_ref == 0 and n_hyp > 0:
        return 0.0, 1.0, L, sampled
    if n_ref > 0 and n_hyp == 0:
        return 1.0, 0.0, L, sampled
    p = L / n_hyp
    r = L / n_ref
    return p, r, L, sampled


def score(pre: str, post: str) -> dict:
    pre = pre or ""
    post = post or ""
    pre_toks = tokenize(pre)
    post_toks = tokenize(post)
    p1, r1, _ov = rouge1_pr(pre_toks, post_toks)
    pL, rL, _L, sampled = rougeL_pr(pre_toks, post_toks)
    rec = {
        "rouge1_r": round(r1, 6),
        "rouge1_p": round(p1, 6),
        "rouge1_f1": round(_f1(p1, r1), 6),
        "rougeL_r": round(rL, 6),
        "rougeL_p": round(pL, 6),
        "rougeL_f1": round(_f1(pL, rL), 6),
        "n_pre_tokens": len(pre_toks),
        "n_post_tokens": len(post_toks),
        "lcs_sampled": bool(sampled),
    }
    rec["alarm_fabrication"] = rec["rouge1_p"] < FABRICATION_P
    rec["alarm_coverage"] = rec["rouge1_r"] < COVERAGE_R
    return rec


def _latest_named(cache: Path, filename: str):
    found = [p for p in cache.rglob(filename) if p.is_file()]
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def _load_cache_pair() -> tuple:
    cache = _profile_root() / "cache"
    pre = post = ""
    pre_p = post_p = None
    for name in ("pre-compact-context.txt", "pre-compact-annotate.txt"):
        p = _latest_named(cache, name)
        if p is not None:
            pre = p.read_text(encoding="utf-8", errors="replace")
            pre_p = p
            break
    for name in ("post-compact-context.txt", "compacted-context.txt"):
        p = _latest_named(cache, name)
        if p is not None:
            post = p.read_text(encoding="utf-8", errors="replace")
            post_p = p
            break
    return pre, post, pre_p, post_p


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    payload = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(lock_path, "w", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        with open(path, "a", encoding="utf-8") as f:
            f.write(payload)


def _nightly_append(rec: dict, pre_p, post_p) -> dict:
    out = dict(rec)
    now = datetime.now(UTC)
    out["ts"] = now.isoformat()
    out["instance_id"] = now.date().isoformat()
    if pre_p is not None:
        out["pre_path"] = str(pre_p)
    if post_p is not None:
        out["post_path"] = str(post_p)
    dest = _profile_root() / "cache" / "compaction-rouge-scores.jsonl"
    _append_jsonl(dest, out)
    out["out_path"] = str(dest)
    return out


def _batch() -> int:
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"error": "invalid_json"}))
            continue
        if not isinstance(obj, dict):
            print(json.dumps({"error": "not_object"}))
            continue
        rec = score(str(obj.get("pre") or ""), str(obj.get("post") or ""))
        if "instance_id" in obj:
            rec["instance_id"] = obj.get("instance_id")
        if "summarizer_id" in obj:
            rec["summarizer_id"] = obj.get("summarizer_id")
        print(json.dumps(rec))
    return 0


def self_test() -> int:
    empty = score("", "")
    assert empty["rouge1_r"] == 1.0
    assert empty["rouge1_p"] == 1.0
    assert empty["rouge1_f1"] == 1.0
    assert empty["rougeL_r"] == 1.0
    assert empty["rougeL_p"] == 1.0
    assert empty["n_pre_tokens"] == 0
    assert empty["alarm_fabrication"] is False
    assert empty["alarm_coverage"] is False
    assert empty["lcs_sampled"] is False

    identical = score("the cat sat on the mat", "the cat sat on the mat")
    assert identical["rouge1_r"] == 1.0
    assert identical["rouge1_p"] == 1.0
    assert identical["rouge1_f1"] == 1.0
    assert identical["rougeL_r"] == 1.0
    assert identical["rougeL_p"] == 1.0
    assert identical["rougeL_f1"] == 1.0
    assert identical["alarm_fabrication"] is False
    assert identical["alarm_coverage"] is False

    fab = score("alpha beta gamma delta", "zzzz yyyy xxxx wwww")
    assert fab["rouge1_r"] == 0.0
    assert fab["rouge1_p"] == 0.0
    assert fab["rouge1_f1"] == 0.0
    assert fab["rougeL_r"] == 0.0
    assert fab["rougeL_p"] == 0.0
    assert fab["alarm_fabrication"] is True
    assert fab["alarm_coverage"] is True

    # Full coverage: every source unigram appears in the summary.
    cov = score("alpha beta gamma", "alpha beta gamma extra")
    assert cov["rouge1_r"] == 1.0
    assert cov["alarm_coverage"] is False
    assert cov["rouge1_p"] == 0.75
    assert cov["rougeL_r"] == 1.0
    assert cov["rougeL_p"] == 0.75

    # Empty summary of nonempty source: coverage alarm, no fabrication n-grams.
    drop = score("keep these facts please", "")
    assert drop["rouge1_r"] == 0.0
    assert drop["rouge1_p"] == 1.0
    assert drop["alarm_coverage"] is True
    assert drop["alarm_fabrication"] is False

    # Empty source, nonempty summary: all fabricated.
    inv = score("", "totally invented tokens here")
    assert inv["rouge1_r"] == 1.0
    assert inv["rouge1_p"] == 0.0
    assert inv["alarm_fabrication"] is True
    assert inv["alarm_coverage"] is False

    # Clipped unigram overlap (ROUGE-1 counts, not sets).
    clip = score("a b a", "a a a")
    assert clip["n_pre_tokens"] == 3
    assert clip["n_post_tokens"] == 3
    assert clip["rouge1_r"] == round(2 / 3, 6)
    assert clip["rouge1_p"] == round(2 / 3, 6)

    # ROUGE-L: subsequence, not bag.
    lcs = score("a b c d", "a c d")
    assert lcs["rougeL_r"] == 0.75
    assert lcs["rougeL_p"] == 1.0

    sampled_in, flag = _sample_ends(["t"] * (LCS_LIMIT + 1))
    assert flag is True
    assert len(sampled_in) == 2 * LCS_KEEP_EACH_END
    small, flag2 = _sample_ends(["t"] * 10)
    assert flag2 is False
    assert small == ["t"] * 10

    # LCS sampled: identical 10001-token strings — rougeL P=R=F=1.0 on sampled lengths.
    big_toks = ["word"] * (LCS_LIMIT + 1)
    big_s = " ".join(big_toks)
    big = score(big_s, big_s)
    assert big["lcs_sampled"] is True
    assert big["rougeL_r"] == 1.0, f"expected 1.0 got {big['rougeL_r']}"
    assert big["rougeL_p"] == 1.0, f"expected 1.0 got {big['rougeL_p']}"
    assert big["rougeL_f1"] == 1.0

    for rec in (empty, identical, fab, cov, drop, inv, clip, lcs):
        for k in (
            "rouge1_r",
            "rouge1_p",
            "rouge1_f1",
            "rougeL_r",
            "rougeL_p",
            "rougeL_f1",
        ):
            v = rec[k]
            assert 0.0 <= v <= 1.0, (k, v)
        json.loads(json.dumps(rec))

    print("PASS score-compaction-rouge self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pre", default="")
    ap.add_argument("--post", default="")
    ap.add_argument("--pre-text", default="")
    ap.add_argument("--post-text", default="")
    ap.add_argument("--batch", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.batch:
        return _batch()
    pre = args.pre_text
    post = args.post_text
    explicit = bool(args.pre or args.post or args.pre_text or args.post_text)
    pre_p = post_p = None
    if args.pre:
        pre_p = Path(args.pre)
        pre = pre_p.read_text(encoding="utf-8", errors="replace")
    if args.post:
        post_p = Path(args.post)
        post = post_p.read_text(encoding="utf-8", errors="replace")
    if not explicit:
        pre, post, pre_p, post_p = _load_cache_pair()
        if pre_p is None and post_p is None:
            rec = {"status": "insufficient_data", "reason": "no_pre_post_context"}
            print(json.dumps(rec, indent=2))
            return 0
    rec = score(pre, post)
    if not explicit:
        rec = _nightly_append(rec, pre_p, post_p)
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
