#!/usr/bin/env python3
"""context-channel-capacity.py — mutual-information proxy at compaction.

Cover–Thomas / Shannon 1948: each compaction is a lossy channel X→Y.
Entropy proxies via zlib compressed length (bits).

  H(X) ≈ 8 * |zlib(pre)|
  H(Y) ≈ 8 * |zlib(post)|
  H(X,Y) ≈ 8 * |zlib(pre||post)|
  I(X;Y) = H(X)+H(Y)-H(X,Y)     (Shannon identity)
  Spec estimator H(both)-H(post) is H(X|Y); stored as h_x_given_y.

Channel efficiency = I(X;Y) / H(X). Alarm if efficiency < 0.6
(DPI: compaction discarded >40% of information).

Also checks the DPI inequality I(intent; Y) <= I(intent; X) when an
intent string is supplied.

Usage:
  python3 context-channel-capacity.py --pre PATH --post PATH
  python3 context-channel-capacity.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zlib
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EFFICIENCY_ALARM = 0.6


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


def _atomic_append_jsonl(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        tmp = path.with_suffix(".tmp")
        tmp.write_text(existing + line, encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def zlib_bits(data: bytes) -> float:
    if not data:
        return 0.0
    try:
        n = len(zlib.compress(data, 9))
    except Exception:
        n = len(data)
    return float(max(n, 1) * 8)


def channel_stats(pre: str, post: str, intent: str = "") -> dict:
    xb = (pre or "").encode("utf-8", errors="replace")
    yb = (post or "").encode("utf-8", errors="replace")
    h_pre = zlib_bits(xb)
    h_post = zlib_bits(yb)
    h_both = zlib_bits(xb + b"\n\x1e\n" + yb)
    mi = max(0.0, h_pre + h_post - h_both)
    h_x_given_y = max(0.0, h_both - h_post)  # spec formula
    efficiency = (mi / h_pre) if h_pre > 0 else 0.0
    if efficiency > 1.0:
        efficiency = 1.0
    alarm = bool(efficiency < EFFICIENCY_ALARM) if h_pre > 0 else False
    rec = {
        "channel_efficiency": round(efficiency, 6),
        "h_pre": round(h_pre, 4),
        "h_post": round(h_post, 4),
        "mutual_info_proxy": round(mi, 4),
        "h_x_given_y": round(h_x_given_y, 4),
        "alarm": alarm,
        "dpi_ok": True,
        "n_pre_bytes": len(pre.encode("utf-8", errors="replace") if isinstance(pre, str) else pre),
    }
    if intent:
        ib = intent.encode("utf-8", errors="replace")
        h_i = zlib_bits(ib)
        h_ix = zlib_bits(ib + b"\n\x1e\n" + xb)
        h_iy = zlib_bits(ib + b"\n\x1e\n" + yb)
        i_ix = max(0.0, h_i + h_pre - h_ix)
        i_iy = max(0.0, h_i + h_post - h_iy)
        rec["i_intent_pre"] = round(i_ix, 4)
        rec["i_intent_post"] = round(i_iy, 4)
        rec["dpi_ok"] = bool(i_iy <= i_ix + 1e-6)
        if not rec["dpi_ok"]:
            rec["alarm"] = True
            rec["dpi_violation"] = True
    return rec


def _read_text(path: Path) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


def load_default_pair() -> tuple[str, str]:
    cache = _cache_dir()
    pre = ""
    post = ""
    for name in ("pre-compact-annotate.txt", "pre-compact-context.txt", "context-pre-compact.txt"):
        pre = _read_text(cache / name)
        if pre:
            break
    for name in ("post-compact-context.txt", "context-post-compact.txt", "compacted-context.txt"):
        post = _read_text(cache / name)
        if post:
            break
    # Fallback: last rd advisory + annotation snippets
    if not pre:
        try:
            adv = cache / "rd-compaction-advisory.json"
            if adv.exists():
                pre = adv.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if not post:
        # ADV21-014: do not synthesize a fake channel from half the pre-text
        return pre, None
    return pre, post


def compute(pre: str | None = None, post: str | None = None, intent: str = "") -> dict:
    try:
        if pre is None or post is None:
            p, q = load_default_pair()
            pre = p if pre is None else pre
            post = q if post is None else post
        # ADV21-014: if post is still None (missing), write no-data record
        if post is None:
            rec = {"channel_efficiency": 1.0, "h_pre": 0.0, "h_post": 0.0,
                   "mutual_info_proxy": 0.0, "alarm": False, "reason": "missing_post",
                   "n_pre_bytes": len((pre or "").encode("utf-8", errors="replace"))}
            _atomic_write(_cache_dir() / "context-channel-capacity.json", rec)
            return rec
        rec = channel_stats(pre or "", post or "", intent=intent)
        rec["ts"] = time.time()
        _atomic_write(_cache_dir() / "context-channel-capacity.json", rec)
        _atomic_append_jsonl(_cache_dir() / "context-channel-capacity.jsonl", rec)
        return rec
    except Exception as exc:
        return {
            "channel_efficiency": 0.0,
            "h_pre": 0.0,
            "h_post": 0.0,
            "mutual_info_proxy": 0.0,
            "alarm": False,
            "fail_open": str(exc),
        }


def self_test() -> int:
    # Near-lossless: post ≈ pre → high efficiency, no alarm
    src = ("the mixing time of a reversible Markov chain is controlled by "
           "the spectral gap and the Cheeger conductance. " * 8)
    lossless = channel_stats(src, src)
    assert lossless["h_pre"] > 0
    assert lossless["channel_efficiency"] >= 0.6, lossless
    assert lossless["alarm"] is False
    # Heavy loss: post is a stub
    lossy = channel_stats(src, "ok")
    assert lossy["h_post"] < lossy["h_pre"]
    assert lossy["alarm"] is True, lossy
    assert 0.0 <= lossy["channel_efficiency"] <= 1.0
    # Empty
    empty = channel_stats("", "")
    assert empty["h_pre"] == 0.0
    assert empty["alarm"] is False
    # DPI: intent more related to pre than to an unrelated post
    dpi = channel_stats(src, "unrelated banana flux", intent="Markov mixing conductance")
    assert "dpi_ok" in dpi
    # JSON validity
    json.loads(json.dumps(lossless))
    print("PASS context-channel-capacity self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--pre", default="")
    ap.add_argument("--post", default="")
    ap.add_argument("--intent", default="")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        pre = Path(args.pre).read_text(encoding="utf-8", errors="replace") if args.pre else None
        post = Path(args.post).read_text(encoding="utf-8", errors="replace") if args.post else None
        rec = compute(pre, post, intent=args.intent)
        print(json.dumps(rec, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "channel_efficiency": 0.0,
            "h_pre": 0.0,
            "h_post": 0.0,
            "mutual_info_proxy": 0.0,
            "alarm": False,
            "fail_open": str(exc),
        }))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
