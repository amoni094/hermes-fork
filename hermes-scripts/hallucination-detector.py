#!/usr/bin/env python3
"""Blackbox UE hallucination detector (zlib CCR, hedge, trigram Jaccard)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import zlib

LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")
HEDGE_WORDS = (
    "might", "could", "possibly", "perhaps", "unclear",
    "uncertain", "estimated", "approximately",
)
_HEDGE_RE = re.compile(r"\b(" + "|".join(HEDGE_WORDS) + r")\b", re.IGNORECASE)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _read_text(args) -> str:
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def sentences(text: str) -> list:
    t = (text or "").strip()
    if not t:
        return []
    parts = _SENT_SPLIT.split(t)
    return [p.strip() for p in parts if p.strip()]


def hedge_score(text: str) -> float:
    sents = sentences(text)
    if not sents:
        return 0.0
    hit = sum(1 for s in sents if _HEDGE_RE.search(s))
    return hit / float(len(sents))


def ccr(text: str) -> float:
    raw = (text or "").encode("utf-8")
    if not raw:
        return 1.0
    try:
        compressed = zlib.compress(raw)
        return len(compressed) / float(len(raw))
    except Exception:
        return 1.0


def _trigrams(tokens: list) -> set:
    if len(tokens) < 3:
        return set()
    return set(tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2))


def trigram_jaccard(text: str) -> float:
    tokens = re.findall(r"[A-Za-z0-9_]+", (text or "").lower())
    if len(tokens) < 6:
        return 1.0
    mid = max(3, len(tokens) // 2)
    a = _trigrams(tokens[:mid])
    b = _trigrams(tokens[mid:])
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / float(union)


def detect(text: str) -> dict:
    hs = hedge_score(text)
    c = ccr(text)
    tj = trigram_jaccard(text)
    composite = 0.4 * hs + 0.3 * (1.0 - c) + 0.3 * (1.0 - tj)
    composite = max(composite, 0.0)
    composite = min(composite, 1.0)
    flagged = composite > 0.75
    return {
        "composite_ue": round(composite, 6),
        "hedge_score": round(hs, 6),
        "ccr": round(c, 6),
        "trigram_jaccard": round(tj, 6),
        "flagged": bool(flagged),
    }


def _log_event(text: str, result: dict) -> None:
    if not result.get("flagged"):
        return
    qh = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    conn = sqlite3.connect(str(LIFECYCLE_DB))
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS hallucination_events(
            id INTEGER PRIMARY KEY,
            ts TEXT,
            query_hash TEXT,
            composite_ue REAL,
            hedge_score REAL,
            ccr REAL,
            flagged INTEGER)"""
        )
        conn.execute(
            """INSERT INTO hallucination_events
            (ts, query_hash, composite_ue, hedge_score, ccr, flagged)
            VALUES (datetime('now'), ?, ?, ?, ?, ?)""",
            (
                qh,
                float(result["composite_ue"]),
                float(result["hedge_score"]),
                float(result["ccr"]),
                1 if result["flagged"] else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def self_test() -> dict:
    hedged = "This might be true. It could possibly fail. Perhaps the answer is unclear."
    r = detect(hedged)
    assert r["hedge_score"] > 0.3, r
    empty = detect("")
    assert empty["hedge_score"] == 0.0
    long_txt = ("alpha beta gamma delta epsilon zeta eta theta. " * 200)
    detect(long_txt)
    return {"self_test": "PASS", "hedge_score": r["hedge_score"], "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--text", default=None)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    try:
        text = _read_text(args)
        result = detect(text)
        try:
            _log_event(text, result)
        except Exception:
            pass
        print(json.dumps(result))
    except Exception:
        pass


if __name__ == "__main__":
    main()
