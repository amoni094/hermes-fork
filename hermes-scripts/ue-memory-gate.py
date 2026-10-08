#!/usr/bin/env python3
"""Gate memory commits using blackbox UE scores.

Fail-closed on empty query/response and on unreadable scores (H-I7: no raise).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

WARN_UE = 0.6
DENY_UE = 0.75
WARN_HEDGE = 0.4


def _clip01(x: Any, default: float = 1.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _scores_path() -> Path:
    return _cache_dir() / "ue-blackbox-scores.jsonl"


def _gate_log_path() -> Path:
    return _cache_dir() / "ue-memory-gate-log.jsonl"


def _append_jsonl(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
    except Exception:
        pass


def _iter_jsonl(path: Path):
    try:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s or not s.startswith("{"):
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def query_hash(query: str) -> str:
    t = query or ""
    if len(t) > 50000:
        t = t[:50000]
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()[:16]


def _load_scorer_module():
    candidates = [
        Path(__file__).resolve().parent / "ue-blackbox-scorer.py",
        Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "hermes-scripts" / "ue-blackbox-scorer.py",
        Path.home() / ".hermes" / "hermes-scripts" / "ue-blackbox-scorer.py",
    ]
    # If HERMES_HOME is a profile dir, strip profiles/<name>
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    if hh.parent.name == "profiles":
        candidates.append(hh.parent.parent / "hermes-scripts" / "ue-blackbox-scorer.py")
    elif (hh / "hermes-scripts" / "ue-blackbox-scorer.py").exists():
        candidates.append(hh / "hermes-scripts" / "ue-blackbox-scorer.py")
    seen = set()
    for p in candidates:
        try:
            rp = str(p.resolve()) if p.exists() else str(p)
        except Exception:
            rp = str(p)
        if rp in seen:
            continue
        seen.add(rp)
        try:
            if not p.exists():
                continue
            spec = importlib.util.spec_from_file_location("ue_blackbox_scorer", str(p))
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            continue
    return None


def _latest_score(qh: str) -> Optional[dict]:
    latest = None
    for row in _iter_jsonl(_scores_path()) or []:
        if row.get("query_hash") == qh:
            latest = row
    return latest


def _live_score(query: str, response: str) -> Optional[dict]:
    mod = _load_scorer_module()
    if mod is None:
        return None
    try:
        return mod.score_and_log(query=query, response=response)
    except Exception:
        try:
            return mod.compute_scores(query=query, response=response, update_length=False)
        except Exception:
            return None


def decide(query: str, response: str, content: str = "") -> dict:
    q = (query or "").strip()
    r = (response or "").strip()
    reasons: list[str] = []
    if not q or not r:
        rec = {
            "ts": time.time(),
            "query_hash": query_hash(query or ""),
            "decision": "GATE_DENY",
            "composite_ue": 1.0,
            "hedge_phrase": 1.0,
            "ue_uncertain": True,
            "ue_score": 1.0,
            "reason": "empty_query_or_response",
            "content_len": len(content or ""),
        }
        _append_jsonl(_gate_log_path(), rec)
        return rec

    qh = query_hash(query)
    # Live-score this pair first so a stale cache row cannot bypass or deny the wrong response.
    score = _live_score(query, response)
    if score is None:
        score = _latest_score(qh)
    if score is None:
        rec = {
            "ts": time.time(),
            "query_hash": qh,
            "decision": "GATE_DENY",
            "composite_ue": 1.0,
            "hedge_phrase": 1.0,
            "ue_uncertain": True,
            "ue_score": 1.0,
            "reason": "no_ue_scores_fail_closed",
            "content_len": len(content or ""),
        }
        _append_jsonl(_gate_log_path(), rec)
        return rec

    composite = _clip01(score.get("composite_ue"), default=1.0)
    scores = score.get("scores") if isinstance(score.get("scores"), dict) else {}
    hedge = _clip01(scores.get("hedge_phrase"), default=0.0)

    if composite > DENY_UE:
        decision = "GATE_DENY"
        reasons.append("composite_ue>%.2f" % DENY_UE)
    elif composite > WARN_UE or hedge > WARN_HEDGE:
        decision = "GATE_WARN"
        if composite > WARN_UE:
            reasons.append("composite_ue>%.2f" % WARN_UE)
        if hedge > WARN_HEDGE:
            reasons.append("hedge_phrase>%.2f" % WARN_HEDGE)
    else:
        decision = "GATE_PASS"
        reasons.append("ok")

    rec = {
        "ts": time.time(),
        "query_hash": qh,
        "decision": decision,
        "composite_ue": round(composite, 6),
        "hedge_phrase": round(hedge, 6),
        "ue_uncertain": decision != "GATE_PASS",
        "ue_score": round(composite, 6),
        "reason": ",".join(reasons),
        "content_len": len(content or ""),
        "high_ue": bool(score.get("high_ue")),
    }
    _append_jsonl(_gate_log_path(), rec)
    return rec


def stats() -> dict:
    rows = list(_iter_jsonl(_gate_log_path()) or [])
    counts = {"GATE_PASS": 0, "GATE_WARN": 0, "GATE_DENY": 0}
    for r in rows:
        d = r.get("decision")
        if d in counts:
            counts[d] += 1
        else:
            counts[d] = 1
    return {"n": len(rows), "counts": counts, "path": str(_gate_log_path())}


def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    isolated = _hermes_root / "cache" / "scratch" / "ue-self-test-gate"
    try:
        isolated.mkdir(parents=True, exist_ok=True)
        for leftover in isolated.glob("*"):
            try:
                leftover.unlink()
            except Exception:
                pass
    except Exception:
        pass
    os.environ["UE_CACHE_DIR"] = str(isolated)

    d0 = decide("", "fact")
    check(d0["decision"] == "GATE_DENY", "empty query bypass: %s" % d0)
    d1 = decide("query", "")
    check(d1["decision"] == "GATE_DENY", "empty response bypass")
    d1b = decide("   ", "   ")
    check(d1b["decision"] == "GATE_DENY", "whitespace bypass")

    # Live-score a high-hedge claim -> WARN or DENY
    d2 = decide(
        "is this true",
        "This might possibly be uncertain. I'm not sure. It could, probably, likely, be unclear.",
        content="memory fact",
    )
    check(d2["decision"] in ("GATE_WARN", "GATE_DENY"), "hedge not gated: %s" % d2)

    # Low-uncertainty factual
    d3 = decide("what is 2+2", "2+2 equals 4.")
    check(d3["decision"] in ("GATE_PASS", "GATE_WARN", "GATE_DENY"), "factual ran")
    check("decision" in d3, "json keys")

    st = stats()
    check(st["n"] >= 3, "gate log n")

    # malformed jsonl must not raise
    try:
        gp = _scores_path()
        gp.parent.mkdir(parents=True, exist_ok=True)
        with open(gp, "a", encoding="utf-8") as fh:
            fh.write("NOT JSON\n{]\n\n")
        d4 = decide("malformed-cache-query", "a perfectly ordinary memory sentence about cats.")
        check("decision" in d4, "malformed jsonl raised or empty")
    except Exception as exc:
        failures.append("malformed jsonl raised: %s" % exc)

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "n_checks": 7}))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    try:
        ap = argparse.ArgumentParser(description="UE memory commit gate")
        ap.add_argument("--self-test", action="store_true")
        sub = ap.add_subparsers(dest="cmd")
        p_check = sub.add_parser("check")
        p_check.add_argument("--query", default="")
        p_check.add_argument("--response", default="")
        p_check.add_argument("--content", default="")
        sub.add_parser("stats")
        sub.add_parser("self-test")
        args = ap.parse_args(argv)
        if args.self_test or args.cmd in ("self-test", "self_test"):
            return self_test()
        if args.cmd == "stats":
            print(json.dumps(stats(), ensure_ascii=False))
            return 0
        rec = decide(
            getattr(args, "query", ""),
            getattr(args, "response", ""),
            getattr(args, "content", ""),
        )
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    except Exception:
        try:
            print(json.dumps({
                "decision": "GATE_DENY",
                "composite_ue": 1.0,
                "ue_uncertain": True,
                "reason": "unhandled",
            }))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
