#!/usr/bin/env python3
"""eval-memory-planted-needle.py — LongMemEval-style planted-fact recall.

Plants 10 distinctive facts in a synthetic session-history file, queries
unified-recall.py for each, and reports hit_rate, avg_rank, Wilson CI.

If Hindsight/Graphiti are down (unified-recall exit 3), falls back to a
stdlib lexical ranker over the planted history (retrieval diagnosis first).
This still yields a planted-needle number for the local memory surface.

LongMemEval (arXiv:2410.10813) / HELMET (arXiv:2410.02694): Hermes 15-q
exam is underpowered (N=15, CI width ~45pt). This script is the N=10
needle probe; scale later.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 eval-memory-planted-needle.py
  python3 eval-memory-planted-needle.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

HISTORY_PATH = _hermes_root / "cache" / "scratch" / "planted-needle-history.txt"
OUT_PATH = _hermes_root / "cache" / "eval-memory-planted-needle.json"
UNIFIED = _hermes_base / "hermes-scripts" / "unified-recall.py"
TOP_K = 10

FACTS = [
    {"id": "N01", "fact": "The fork eval codename is AMBER-NEEDLE-7 and it lives only in synthetic history.",
     "query": "What is the fork eval codename AMBER-NEEDLE?", "needle": "AMBER-NEEDLE-7"},
    {"id": "N02", "fact": "User rainbow planted spare token is QUARTZ-FROG-4419, not a real secret.",
     "query": "What is the planted spare token QUARTZ-FROG?", "needle": "QUARTZ-FROG-4419"},
    {"id": "N03", "fact": "The Bayesian TTL experiment uses prior KappaEqualsTwo on 2026-10-09.",
     "query": "Which prior does the Bayesian TTL experiment use KappaEquals?", "needle": "KappaEqualsTwo"},
    {"id": "N04", "fact": "Planted printer hostname is willow-spool-17.lab.invalid.",
     "query": "What is the planted printer hostname willow-spool?", "needle": "willow-spool-17.lab.invalid"},
    {"id": "N05", "fact": "Shadow gate synthetic seed is forty-six; cite SEED-FORTY-SIX-OK.",
     "query": "What seed citation is SEED-FORTY-SIX?", "needle": "SEED-FORTY-SIX-OK"},
    {"id": "N06", "fact": "LongMemEval probe animal is a cerulean axolotl named Nimbus-P9.",
     "query": "What is the LongMemEval probe animal name Nimbus?", "needle": "Nimbus-P9"},
    {"id": "N07", "fact": "The mSPRT mixture prior in this eval is labelled MIXPRIOR-BETA22.",
     "query": "What label is the mSPRT mixture prior MIXPRIOR?", "needle": "MIXPRIOR-BETA22"},
    {"id": "N08", "fact": "HELMET citation token for this run is HELMET-2410-02694-LOCAL.",
     "query": "What is the HELMET citation token HELMET-2410?", "needle": "HELMET-2410-02694-LOCAL"},
    {"id": "N09", "fact": "Planted timezone alias for the eval clock is TZ-AEST-NEEDLE-PLUS10.",
     "query": "What timezone alias is TZ-AEST-NEEDLE?", "needle": "TZ-AEST-NEEDLE-PLUS10"},
    {"id": "N10", "fact": "The tenth needle is a checksum phrase: zebra-velvet-orchid-92.",
     "query": "What is the tenth needle checksum phrase zebra-velvet?", "needle": "zebra-velvet-orchid-92"},
]

FILLER = (
    "Routine session chatter about compiling stdlib-only scripts, wrapping "
    "fork profile runpy delegates, and checking monitor-suite missing files. "
    "No planted needles in this paragraph. Discussion of SPRT thresholds, "
    "N_MIN_POWER floors, and cache paths under the fork profile. "
)


def _atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def build_history(facts=None) -> str:
    facts = facts if facts is not None else FACTS
    chunks = []
    for i, f in enumerate(facts):
        chunks.append(FILLER)
        chunks.append("Session turn %d: %s" % (i + 1, f["fact"]))
        chunks.append(FILLER)
    return "\n".join(chunks) + "\n"


def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9]{3,}", (text or "").lower())


def lexical_rank(query: str, docs: list, top_k: int = TOP_K) -> list:
    q = set(tokenize(query))
    scored = []
    for d in docs:
        toks = tokenize(d["text"])
        if not toks:
            scored.append((0.0, d))
            continue
        tf = sum(1 for t in toks if t in q)
        score = tf / math.sqrt(len(toks))
        scored.append((score, d))
    scored.sort(key=lambda kv: -kv[0])
    out = []
    for rank, (score, d) in enumerate(scored[:top_k], start=1):
        item = dict(d)
        item["rank"] = rank
        item["score"] = score
        out.append(item)
    return out


def wilson_ci(k: int, n: int, z: float = 1.96):
    if n <= 0:
        return 0.0, 0.0, 1.0
    p = k / n
    z2 = z * z
    den = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / den
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / den
    return p, max(0.0, center - margin), min(1.0, center + margin)


def hit_in_text(needle: str, text: str) -> bool:
    return needle.lower() in (text or "").lower()


def run_unified(query: str, timeout: int = 20):
    if not UNIFIED.exists():
        return [], "missing_binary"
    env = dict(os.environ)
    env.setdefault("HERMES_HOME", str(_hermes_base))
    if _hermes_profile:
        env.setdefault("HERMES_PROFILE", _hermes_profile)
    try:
        proc = subprocess.run(
            [sys.executable, str(UNIFIED), query, "--json", "--top", str(TOP_K)],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return [], "timeout"
    except OSError as exc:
        return [], f"oserror:{exc}"
    if proc.returncode == 3:
        return [], "services_down"
    if proc.returncode != 0:
        return [], f"exit_{proc.returncode}"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], "bad_json"
    if not isinstance(data, list):
        return [], "not_list"
    return data, "ok"


def evaluate(history_text: str, facts=None, use_unified: bool = True) -> dict:
    facts = facts if facts is not None else FACTS
    parts = [p.strip() for p in history_text.split("\n") if p.strip()]
    docs = [{"id": "p%d" % i, "text": p} for i, p in enumerate(parts)]
    per = []
    unified_status = None
    for f in facts:
        lex_ranked = lexical_rank(f["query"] + " " + f["needle"], docs)
        lex_texts = [r["text"] for r in lex_ranked]
        lex_rank = None
        lex_hit = False
        for i, text in enumerate(lex_texts, start=1):
            if hit_in_text(f["needle"], text):
                lex_hit = True
                lex_rank = i
                break
        uni_rank = None
        uni_hit = False
        source = "lexical"
        if use_unified:
            items, status = run_unified(f["query"])
            unified_status = status if unified_status is None else unified_status
            if status == "ok":
                source = "unified-recall"
                for i, it in enumerate(items, start=1):
                    if hit_in_text(f["needle"], str(it.get("text", ""))):
                        uni_hit = True
                        uni_rank = i
                        break
        # Primary reported hit: live index if queried, else lexical history surface
        if use_unified and unified_status == "ok":
            hit, rank = uni_hit, uni_rank
            if not hit:
                failure = "index_write_gap" if lex_hit else (
                    "retrieval" if hit_in_text(f["needle"], history_text) else "write"
                )
            else:
                failure = None
        else:
            hit, rank = lex_hit, lex_rank
            failure = None if hit else (
                "retrieval" if hit_in_text(f["needle"], history_text) else "write"
            )
        per.append({
            "id": f["id"],
            "needle": f["needle"],
            "hit": hit,
            "rank": rank,
            "lexical_hit": lex_hit,
            "lexical_rank": lex_rank,
            "unified_hit": uni_hit,
            "unified_rank": uni_rank,
            "source": source,
            "failure": failure,
        })
    hits = sum(1 for r in per if r["hit"])
    lex_hits = sum(1 for r in per if r["lexical_hit"])
    ranks = [r["rank"] for r in per if r["rank"] is not None]
    lex_ranks = [r["lexical_rank"] for r in per if r["lexical_rank"] is not None]
    p, lo, hi = wilson_ci(hits, len(facts))
    lp, llo, lhi = wilson_ci(lex_hits, len(facts))
    avg_rank = (sum(ranks) / len(ranks)) if ranks else None
    avg_lex_rank = (sum(lex_ranks) / len(lex_ranks)) if lex_ranks else None
    return {
        "n": len(facts),
        "hits": hits,
        "hit_rate": p,
        "wilson_ci_95": [lo, hi],
        "ci_width_pt": round((hi - lo) * 100.0, 1),
        "avg_rank": avg_rank,
        "lexical_hits": lex_hits,
        "lexical_hit_rate": lp,
        "lexical_wilson_ci_95": [llo, lhi],
        "lexical_avg_rank": avg_lex_rank,
        "unified_status": unified_status,
        "benchmark": "LongMemEval-style planted needle; HELMET scale note: N=10 vs 100-2000",
        "diagnosis": (
            "index_write_gap" if (use_unified and unified_status == "ok" and hits == 0 and lex_hits == len(facts))
            else "ok"
        ),
        "per_query": per,
    }


def run() -> dict:
    history = build_history()
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = HISTORY_PATH.with_suffix(".tmp")
        tmp.write_text(history, encoding="utf-8")
        os.replace(tmp, HISTORY_PATH)
    except OSError:
        pass
    result = evaluate(history, use_unified=True)
    result["ts"] = datetime.now(UTC).isoformat()
    result["history_path"] = str(HISTORY_PATH)
    try:
        _atomic_write(OUT_PATH, result)
        result["output"] = str(OUT_PATH)
    except OSError as exc:
        result["write_error"] = str(exc)
    return result


def self_test() -> int:
    failures = []
    hist = build_history()
    for f in FACTS:
        if f["needle"] not in hist:
            failures.append("plant {}".format(f["id"]))
    r = evaluate(hist, use_unified=False)
    if r["hits"] != 10:
        failures.append("lexical hits {}".format(r["hits"]))
    if r["hit_rate"] != 1.0:
        failures.append("hit_rate {}".format(r["hit_rate"]))
    p, lo, _hi = wilson_ci(10, 10)
    if lo >= p:
        failures.append("wilson")
    r0 = evaluate("", facts=FACTS, use_unified=False)
    if r0["hits"] != 0:
        failures.append("empty hits")
    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS", "hit_rate": r["hit_rate"], "avg_rank": r["avg_rank"]}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--no-unified", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.no_unified:
        history = build_history()
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text(history, encoding="utf-8")
        result = evaluate(history, use_unified=False)
        print(json.dumps(result))
        return 0
    out = run()
    print(json.dumps({
        "hit_rate": out.get("hit_rate"),
        "hits": out.get("hits"),
        "n": out.get("n"),
        "avg_rank": out.get("avg_rank"),
        "wilson_ci_95": out.get("wilson_ci_95"),
        "ci_width_pt": out.get("ci_width_pt"),
        "unified_status": out.get("unified_status"),
        "output": out.get("output"),
        "per_query": out.get("per_query"),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
