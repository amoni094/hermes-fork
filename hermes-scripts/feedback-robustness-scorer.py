#!/usr/bin/env python3
"""Huber-loss robust regression on skill feedback (delta=1.35)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, UTC

DELTA = 1.35
ROUTING_EVENTS = _hermes_root / "cache" / "routing-events.jsonl"
OUT_PATH = _hermes_root / "cache" / "skill-robustness-scores.json"
LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")


def huber(r: float, delta: float = DELTA) -> float:
    ar = abs(r)
    if ar <= delta:
        return (r * r) / 2.0
    return delta * (ar - delta / 2.0)


def robust_mean(scores: list, delta: float = DELTA) -> float:
    if not scores:
        return 0.0
    mu = sum(scores) / float(len(scores))
    weights = []
    for s in scores:
        L = huber(s - mu, delta)
        weights.append(1.0 / max(L, 0.001))
    wsum = sum(weights) or 1.0
    return sum(w * s for w, s in zip(weights, scores)) / wsum


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def _load_routing_events(path: Path) -> dict:
    by_skill = defaultdict(list)
    if not path.exists():
        return by_skill
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            skill = rec.get("top_skill") or rec.get("skill") or rec.get("skill_name")
            score = rec.get("top_score", rec.get("score", rec.get("reward")))
            if skill is None or score is None:
                continue
            try:
                by_skill[str(skill)].append(float(score))
            except (TypeError, ValueError):
                continue
    except OSError:
        return defaultdict(list)
    return by_skill


def _load_lifecycle_episodes() -> dict:
    by_skill = defaultdict(list)
    try:
        if not LIFECYCLE_DB.exists():
            return by_skill
        conn = sqlite3.connect(str(LIFECYCLE_DB))
        try:
            names = [
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            if "episodes" not in names:
                return by_skill
            cols = [r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()]
            skill_col = "skill_name" if "skill_name" in cols else None
            score_col = "score" if "score" in cols else None
            if not skill_col or not score_col:
                return by_skill
            for skill, score in conn.execute(
                "SELECT %s, %s FROM episodes" % (skill_col, score_col)
            ):
                if skill is None or score is None:
                    continue
                try:
                    by_skill[str(skill)].append(float(score))
                except (TypeError, ValueError):
                    continue
        finally:
            conn.close()
    except Exception:
        return defaultdict(list)
    return by_skill


def synthetic_scores() -> dict:
    return {
        "skill_a": [0.8, 0.82, 0.79, 0.81, 0.83],
        "skill_b": [0.5, 0.52, 0.48, 0.51, 0.9],
    }


def score_groups(by_skill: dict, delta: float = DELTA) -> dict:
    rows = []
    for skill, scores in sorted(by_skill.items()):
        if not scores:
            continue
        rows.append(
            {
                "skill": skill,
                "robustness_score": round(robust_mean(scores, delta), 6),
                "n": len(scores),
            }
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "delta": delta,
        "scores": rows,
    }


def run() -> dict:
    by_skill = _load_routing_events(ROUTING_EVENTS)
    source = "routing-events"
    if not by_skill:
        by_skill = _load_lifecycle_episodes()
        source = "lifecycle.episodes"
    if not by_skill:
        by_skill = synthetic_scores()
        source = "synthetic"
    out = score_groups(by_skill)
    out["source"] = source
    try:
        _atomic_write_json(OUT_PATH, out)
    except Exception:
        pass
    return out


def self_test() -> dict:
    scores = [0.8, 0.81, 0.79, 0.82, 0.80, 5.0]
    naive = sum(scores) / len(scores)
    rob = robust_mean(scores)
    assert rob < naive, (rob, naive)
    assert abs(rob - 0.8) < 0.15, rob
    empty = robust_mean([])
    assert empty == 0.0
    return {
        "self_test": "PASS",
        "naive": round(naive, 6),
        "robust": round(rob, 6),
        "outlier_downweighted": rob < naive,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
