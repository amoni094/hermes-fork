#!/usr/bin/env python3
"""Per-model / per-skill affinity tracker with abstention.

Updates routing-affinity.json: model_name, skill_tag, success_rate, n_trials,
abstain_flag. Computes assignment entropy and re-ranks affinities from
historical outcomes. Does not invent extra models when logs lack model labels.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import random
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / "cache"
CALIB_LOG = CACHE / "calibration-log.jsonl"
TURN_LOG = CACHE / "turn-behavior.jsonl"
OUT_PATH = CACHE / "routing-affinity.json"
ABSTAIN_THRESHOLD = 0.45
MAX_ROWS = 30000
N_MIN = 8


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _clip01(v, default=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(x):
        return default
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock") if path.suffix else path.with_name(path.name + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _tail_jsonl(path: Path, max_rows: int) -> list:
    if not path.exists():
        return []
    rows = []
    try:
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            if path.stat().st_size > 8_000_000:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 6_000_000))
                fh.readline()
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    rows.append(rec)
    except OSError:
        return []
    if max_rows and len(rows) > max_rows:
        return rows[-max_rows:]
    return rows


def parse_trial(rec: dict) -> dict | None:
    if not isinstance(rec, dict):
        return None
    if rec.get("scope") == "ue_blackbox":
        return None
    skill = rec.get("tool_name") or rec.get("skill_tag") or rec.get("skill") or rec.get("skill_id")
    if skill is None or str(skill).strip() == "":
        return None
    model = rec.get("model_name") or rec.get("model") or rec.get("backend") or rec.get("role")
    if model is None or str(model).strip() == "":
        model = "default"
    success = rec.get("success")
    if success is None:
        ao = rec.get("actual_outcome")
        if ao is None:
            return None
        success = ao in (1, "1", True, "true", "True")
    else:
        success = bool(success)
    conf = _clip01(rec.get("predicted_confidence"), default=None)
    return {
        "model_name": str(model).strip(),
        "skill_tag": str(skill).strip(),
        "success": bool(success),
        "confidence": conf,
    }


def accumulate_trials(trials: list) -> list:
    buckets = defaultdict(lambda: {"n": 0, "wins": 0, "conf_sum": 0.0, "conf_n": 0, "abstain_n": 0})
    for t in trials:
        key = (t["model_name"], t["skill_tag"])
        b = buckets[key]
        b["n"] += 1
        if t["success"]:
            b["wins"] += 1
        c = t.get("confidence")
        if c is not None:
            b["conf_sum"] += c
            b["conf_n"] += 1
            if c < ABSTAIN_THRESHOLD:
                b["abstain_n"] += 1
    rows = []
    for (model, skill), b in buckets.items():
        n = b["n"]
        rate = b["wins"] / n if n else 0.0
        mean_conf = (b["conf_sum"] / b["conf_n"]) if b["conf_n"] else None
        abstain_rate = b["abstain_n"] / b["conf_n"] if b["conf_n"] else 0.0
        rows.append({
            "model_name": model,
            "skill_tag": skill,
            "success_rate": round(rate, 6),
            "n_trials": n,
            "abstain_flag": bool(mean_conf is not None and mean_conf < ABSTAIN_THRESHOLD),
            "abstain_rate": round(abstain_rate, 6),
            "mean_confidence": None if mean_conf is None else round(mean_conf, 6),
        })
    rows.sort(key=lambda r: (r["success_rate"], r["n_trials"]), reverse=True)
    return rows


def assignment_entropy(rows: list) -> float:
    totals = defaultdict(float)
    for r in rows:
        totals[r["model_name"]] += float(r["n_trials"])
    s = sum(totals.values())
    if s <= 0:
        return 0.0
    h = 0.0
    for v in totals.values():
        p = v / s
        if p > 0:
            h -= p * math.log2(p)
    return h


def skill_entropy(rows: list) -> float:
    totals = defaultdict(float)
    for r in rows:
        totals[r["skill_tag"]] += float(r["n_trials"])
    s = sum(totals.values())
    if s <= 0:
        return 0.0
    h = 0.0
    for v in totals.values():
        p = v / s
        if p > 0:
            h -= p * math.log2(p)
    return h


def adaptive_vs_round_robin(tasks: list, affinities: list) -> dict:
    """tasks: list of {skill_tag, model_outcomes: {model: success_bool}}.
    Adaptive: pick highest success_rate model that does not abstain; else skip.
    Round-robin: cycle models regardless of affinity.
    """
    by_skill = defaultdict(list)
    for r in affinities:
        by_skill[r["skill_tag"]].append(r)
    for sk in by_skill:
        by_skill[sk].sort(key=lambda r: r["success_rate"], reverse=True)
    models = sorted({r["model_name"] for r in affinities})
    if not models:
        return {"adaptive": 0.0, "round_robin": 0.0, "n": 0, "adaptive_n": 0, "rr_n": 0}

    ad_ok = 0
    ad_n = 0
    for t in tasks:
        ranked = by_skill.get(t["skill_tag"]) or []
        chosen = None
        for r in ranked:
            if r.get("abstain_flag"):
                continue
            chosen = r["model_name"]
            break
        if chosen is None:
            continue
        ad_n += 1
        outcomes = t.get("model_outcomes") or {}
        if outcomes.get(chosen):
            ad_ok += 1

    rr_ok = 0
    rr_n = len(tasks)
    for i, t in enumerate(tasks):
        m = models[i % len(models)]
        outcomes = t.get("model_outcomes") or {}
        if outcomes.get(m):
            rr_ok += 1
    return {
        "adaptive": (ad_ok / ad_n) if ad_n else 0.0,
        "round_robin": (rr_ok / rr_n) if rr_n else 0.0,
        "n": len(tasks),
        "adaptive_n": ad_n,
        "rr_n": rr_n,
        "adaptive_ok": ad_ok,
        "rr_ok": rr_ok,
    }


def layer1_demo(seed: int = 7) -> dict:
    rng = random.Random(seed)
    models = ["mA", "mB", "mC"]
    skills = ["search", "write", "math", "review"]
    # mA strong on search/math, mB strong on write/review, mC weak everywhere
    strength = {
        ("mA", "search"): 0.90, ("mA", "write"): 0.35, ("mA", "math"): 0.88, ("mA", "review"): 0.30,
        ("mB", "search"): 0.32, ("mB", "write"): 0.87, ("mB", "math"): 0.30, ("mB", "review"): 0.85,
        ("mC", "search"): 0.40, ("mC", "write"): 0.38, ("mC", "math"): 0.42, ("mC", "review"): 0.36,
    }
    trials = []
    for _ in range(400):
        sk = rng.choice(skills)
        m = rng.choice(models)
        p = strength[(m, sk)]
        conf = p
        trials.append({
            "model_name": m,
            "skill_tag": sk,
            "success": rng.random() < p,
            "confidence": conf,
        })
    affinities = accumulate_trials(trials)
    tasks = []
    for i in range(100):
        sk = rng.choice(skills)
        tasks.append({
            "skill_tag": sk,
            "model_outcomes": {
                m: (rng.random() < strength[(m, sk)]) for m in models
            },
        })
    cmp = adaptive_vs_round_robin(tasks, affinities)
    return {"affinities": affinities, "cmp": cmp, "entropy": assignment_entropy(affinities)}


def run_live() -> dict:
    trials = []
    for path in (CALIB_LOG, TURN_LOG):
        for rec in _tail_jsonl(path, MAX_ROWS):
            t = parse_trial(rec)
            if t is not None:
                trials.append(t)
    if len(trials) < N_MIN:
        return {
            "status": "insufficient_data",
            "n": len(trials),
            "ts": _now(),
            "reason": "fewer than %d parsed trials" % N_MIN,
        }
    rows = accumulate_trials(trials)
    payload = {
        "status": "ok",
        "ts": _now(),
        "n_trials": len(trials),
        "n_rows": len(rows),
        "assignment_entropy": round(assignment_entropy(rows), 6),
        "skill_entropy": round(skill_entropy(rows), 6),
        "abstain_threshold": ABSTAIN_THRESHOLD,
        "rows": rows,
    }
    _atomic_write(OUT_PATH, payload)
    return payload


def _self_test() -> int:
    demo = layer1_demo(7)
    cmp = demo["cmp"]
    assert cmp["adaptive"] - cmp["round_robin"] >= 0.08, cmp
    rows = demo["affinities"]
    assert rows, "empty affinities"
    assert all("model_name" in r and "skill_tag" in r and "success_rate" in r for r in rows)
    assert all("n_trials" in r and "abstain_flag" in r for r in rows)
    # missing file
    missing = parse_trial({})
    assert missing is None
    empty = accumulate_trials([])
    assert empty == []
    # malformed json handled by tail
    tmp = OUT_PATH.with_name(OUT_PATH.stem + "_test_" + uuid.uuid4().hex + OUT_PATH.suffix)
    try:
        _atomic_write(tmp, {"status": "ok", "rows": rows[:2]})
        loaded = json.loads(tmp.read_text(encoding="utf-8"))
        assert loaded["status"] == "ok"
    finally:
        tmp.unlink(missing_ok=True)
        Path(str(tmp) + ".lock").unlink(missing_ok=True)
        tmp.with_suffix(".lock").unlink(missing_ok=True)
        tmp.with_name(tmp.name + ".tmp").unlink(missing_ok=True)
    print(json.dumps({
        "status": "ok",
        "self_test": True,
        "adaptive": cmp["adaptive"],
        "round_robin": cmp["round_robin"],
        "delta": cmp["adaptive"] - cmp["round_robin"],
    }))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Skill/model affinity state")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[skill-affinity-state] --self-test FAIL: {exc}")
            return 1
    try:
        rec = run_live()
        slim = {k: rec[k] for k in rec if k != "rows"}
        slim["n_rows"] = rec.get("n_rows") or len(rec.get("rows") or [])
        print(json.dumps(slim))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
