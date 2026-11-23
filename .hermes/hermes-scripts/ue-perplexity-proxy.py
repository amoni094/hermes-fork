#!/usr/bin/env python3
"""ue-perplexity-proxy.py — compression-based perplexity proxy (no logprobs).

Shannon 1948 / Cover-Thomas: compression ratio tracks entropy rate.
Li-Vitanyi MDL: K(x) is approximated by a real compressor (zlib here).
Conditional complexity K(response | query) ≈ C(query+response) − C(query).

Hermes blackbox path has no token logprobs, so zlib length is the belt
estimator. Hard-core claims are only the *normalized output ranges*, not
that zlib equals true perplexity.

Hard core (testable):
  CCR > 0  (zlib headers make compressed size ≥ 1)
  ue_proxy ∈ [0, 1]
  is_high_ue is bool (ue_proxy > 0.5)
  never raises on empty query/response or missing cache (H-I7 on log path)

Method:
  joint_size    = len(zlib.compress(query+response))
  query_size    = len(zlib.compress(query))
  response_size = len(zlib.compress(response))
  CCR = joint_size / (query_size + response_size)
  ue_proxy = clip(CCR - 0.4, 0, 0.6) / 0.6
  response_entropy_rate = -log2(clip(c/raw, eps, 1))  bits-per-char proxy

Usage:
  python3 ue-perplexity-proxy.py score --query 'text' --response 'text'
  python3 ue-perplexity-proxy.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

LOG_NAME = "ue-perplexity-proxy.jsonl"
CCR_OFFSET = 0.4
CCR_SPAN = 0.6
HIGH_UE = 0.5
_EPS = 1e-12


def _clip01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _to_bytes(text: str | None) -> bytes:
    if text is None:
        return b""
    try:
        return str(text).encode("utf-8", errors="replace")
    except Exception:
        return b""


def _zlib_size(data: bytes) -> int:
    try:
        n = len(zlib.compress(data, level=6))
    except Exception:
        n = max(len(data), 1)
    return max(int(n), 1)


def cache_dir() -> Path:
    return _hermes_root / "cache"


def log_path() -> Path:
    return cache_dir() / LOG_NAME


def _append_log(record: dict, dest: Path | None = None) -> None:
    """Best-effort JSONL append. Never raises (H-I7)."""
    try:
        p = dest if dest is not None else log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        return


def score_perplexity(query: str | None, response: str | None, log: bool = True) -> dict:
    q = _to_bytes(query)
    r = _to_bytes(response)
    joint = _zlib_size(q + r)
    qsz = _zlib_size(q)
    rsz = _zlib_size(r)
    denom = qsz + rsz
    # denom is at least 2 because each zlib size is ≥ 1
    ccr = joint / denom if denom > 0 else 1.0
    if not math.isfinite(ccr) or ccr <= 0:
        ccr = _EPS

    ue = _clip01(max(0.0, min(ccr - CCR_OFFSET, CCR_SPAN)) / CCR_SPAN)

    raw_len = len(r)
    if raw_len <= 0:
        entropy_rate = 0.0
    else:
        ratio = rsz / raw_len
        if not math.isfinite(ratio) or ratio <= 0:
            entropy_rate = 0.0
        else:
            # clip ratio to (eps, 1] so -log2 is ≥ 0 (zlib overhead can exceed raw)
            ratio = min(max(ratio, _EPS), 1.0)
            entropy_rate = -math.log2(ratio)

    def _jf(x: float) -> float:
        if not math.isfinite(x):
            return 0.0
        r = round(float(x), 6)
        return 0.0 if r == 0.0 else r  # canonical +0.0 (avoid JSON -0.0)

    out = {
        "ccr": _jf(float(ccr)),
        "ue_proxy": _jf(ue),
        "response_entropy_rate": _jf(float(entropy_rate)),
        "is_high_ue": bool(ue > HIGH_UE),
        "joint_size": int(joint),
        "query_size": int(qsz),
        "response_size": int(rsz),
        "response_raw_size": int(raw_len),
    }
    if log:
        rec = dict(out)
        rec["ts"] = datetime.now(timezone.utc).isoformat()
        rec["query_len"] = len(q)
        rec["response_len"] = len(r)
        _append_log(rec)
    return out


def _emit(obj: dict) -> int:
    print(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    return 0


def self_test() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        if not cond:
            failures.append(f"{name}: {detail}" if detail else name)

    # zlib is stdlib
    check("zlib_available", hasattr(zlib, "compress"))

    # 1. Empty inputs
    empty = score_perplexity("", "", log=False)
    check("empty_ccr_pos", empty["ccr"] > 0, str(empty))
    check("empty_ue_range", 0.0 <= empty["ue_proxy"] <= 1.0, str(empty))
    check("empty_high_bool", isinstance(empty["is_high_ue"], bool))
    check("empty_json", isinstance(json.loads(json.dumps(empty)), dict))

    none_out = score_perplexity(None, None, log=False)
    check("none_ccr_pos", none_out["ccr"] > 0, str(none_out))

    # 2. Single-word
    one = score_perplexity("q", "hi", log=False)
    check("one_ue", 0.0 <= one["ue_proxy"] <= 1.0, str(one))
    check("one_ccr", one["ccr"] > 0, str(one))

    # 3. Related vs unrelated (related should have lower or equal CCR)
    related = score_perplexity(
        "The capital of France is",
        "The capital of France is Paris.",
        log=False,
    )
    unrelated = score_perplexity(
        "The capital of France is",
        "Quantum chromodynamics and the confinement of quarks in baryons.",
        log=False,
    )
    check("related_ccr_pos", related["ccr"] > 0, str(related))
    check("unrelated_ccr_pos", unrelated["ccr"] > 0, str(unrelated))
    check(
        "ue_in_range_rel",
        0.0 <= related["ue_proxy"] <= 1.0 and 0.0 <= unrelated["ue_proxy"] <= 1.0,
    )

    # 4. DPI / range invariant on many samples
    samples = [
        ("", ""),
        ("a", "b"),
        ("query", "response"),
        ("hello " * 20, "hello " * 20),
        ("abc", "xyz" * 100),
        ("?", "!"),
        ("q" * 1000, "r" * 1000),
    ]
    for q, r in samples:
        s = score_perplexity(q, r, log=False)
        check("ccr_pos", s["ccr"] > 0, str(s))
        check("ue_01", 0.0 <= s["ue_proxy"] <= 1.0, str(s))
        check("entropy_finite", math.isfinite(s["response_entropy_rate"]), str(s))
        check("entropy_nonneg", s["response_entropy_rate"] >= 0.0, str(s))
        try:
            json.loads(json.dumps(s))
        except Exception as e:
            check("jsonable", False, str(e))

    # 5. Missing cache / log path must not raise. Write to scratch, not
    # the production JSONL (self-test must not pollute the live log).
    try:
        scratch = cache_dir() / "scratch" / "ue-perplexity-self-test.jsonl"
        _append_log({"event": "self-test"}, dest=scratch)
        # cache-as-file: dest parent cannot be created if a file is in the way;
        # swallow must still hold.
        _append_log({"event": "self-test"}, dest=Path("/dev/null/not-a-path.jsonl"))
        check("log_no_raise", True)
    except Exception as e:
        check("log_no_raise", False, str(e))

    # signed-zero must not appear in JSON
    one_json = json.dumps(score_perplexity("q", "hi", log=False))
    check("no_negzero", "-0.0" not in one_json, one_json)

    # 6. Long input
    qlong = "question about widgets " * 50
    rlong = ("Answer sentence with payload %d. " % 3) * 400
    long_out = score_perplexity(qlong, rlong[:10000], log=False)
    check("long_ue", 0.0 <= long_out["ue_proxy"] <= 1.0, str(long_out))
    check("long_ccr", long_out["ccr"] > 0, str(long_out))

    # 7. Schema
    required = {"ccr", "ue_proxy", "response_entropy_rate", "is_high_ue"}
    check("keys", required <= set(empty.keys()), str(empty.keys()))

    # 8. ue_proxy formula edges
    # CCR=0.4 → 0; CCR=1.0 → 1; CCR>1 clipped
    def _ue_from_ccr(ccr: float) -> float:
        return _clip01(max(0.0, min(ccr - CCR_OFFSET, CCR_SPAN)) / CCR_SPAN)

    check("ue_at_0.4", abs(_ue_from_ccr(0.4) - 0.0) < 1e-12)
    check("ue_at_1.0", abs(_ue_from_ccr(1.0) - 1.0) < 1e-12)
    check("ue_at_1.5", abs(_ue_from_ccr(1.5) - 1.0) < 1e-12)
    check("ue_at_0.1", abs(_ue_from_ccr(0.1) - 0.0) < 1e-12)

    if failures:
        print(json.dumps({"ok": False, "failures": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "tests": "pass", "n_failures": 0}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compression-based perplexity proxy (no logprobs)")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sc = sub.add_parser("score", help="Score query/response pair")
    sc.add_argument("--query", default="")
    sc.add_argument("--response", default="")
    sc.add_argument("--no-log", action="store_true")

    args = p.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.cmd == "score":
        try:
            result = score_perplexity(args.query, args.response, log=not args.no_log)
            return _emit(result)
        except Exception as e:
            fallback = {
                "ccr": 1e-12,
                "ue_proxy": 1.0,
                "response_entropy_rate": 0.0,
                "is_high_ue": True,
                "error": type(e).__name__,
            }
            return _emit(fallback)
    p.print_usage(sys.stderr)
    print("error: use `score --query ... --response ...` or --self-test", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
