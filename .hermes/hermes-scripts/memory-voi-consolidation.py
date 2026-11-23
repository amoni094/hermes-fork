#!/usr/bin/env python3
"""memory-voi-consolidation.py — VOI-gated G-Memory consolidation trigger.

DeGroot (Optimal Statistical Decisions) / Williams optional sampling:
fire a costly experiment (consolidation) iff E[loss-drop] > cost.

memory-buffer-flush.py implements ARM decay + topic clustering, NOT VOI.
This script does not re-derive that flush path; it only gates
l1-gmemory-consolidation.py.

Proxy for expected loss: Shannon entropy of fact-type (or retention) mass.
E[loss-drop] ≈ (H_now - H_after_hat) * n_facts * LOSS_PER_NAT
H_after_hat uses a conservative fractional drop (DEFAULT_DROP).

Hard core: never spawn consolidation when voi <= cost.

Usage:
  python3 memory-voi-consolidation.py --check
  python3 memory-voi-consolidation.py --maybe-run [--dry-run]
  python3 memory-voi-consolidation.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


LOSS_PER_NAT = 1.0
DEFAULT_DROP = 0.15          # conservative expected entropy fraction drop
CONSOLIDATION_COST = 8.0     # haiku distill * clusters, in loss units
MIN_FACTS = 8


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def profile_root() -> Path:
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    hp = os.environ.get("HERMES_PROFILE", "").strip()
    if hp and (Path.home() / ".hermes" / "profiles" / hp).is_dir():
        return Path.home() / ".hermes" / "profiles" / hp
    if hh.name != ".hermes" and hh.parent.name == "profiles":
        return hh
    return hermes_home()


def cache_dir() -> Path:
    d = profile_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lifecycle_db() -> Path:
    return hermes_home() / "memory-facts" / "lifecycle.db"


def consolidation_script() -> Path:
    return hermes_home() / "hermes-scripts" / "l1-gmemory-consolidation.py"


def shannon_entropy(counts: dict[str, float]) -> float:
    total = sum(max(0.0, float(v)) for v in counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for v in counts.values():
        p = float(v) / total
        if p > 0:
            h -= p * math.log(p)
    return h


def load_type_counts(db: Path | None = None) -> dict[str, float]:
    path = db or lifecycle_db()
    if not path.exists():
        return {}
    try:
        conn = sqlite3.connect(str(path), timeout=10)
        try:
            cur = conn.execute(
                "SELECT COALESCE(fact_type, 'unknown'), COUNT(*) "
                "FROM fact_lifecycle GROUP BY 1"
            )
            return {str(k): float(v) for k, v in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return {}


def voi_decision(counts: dict[str, float], cost: float = CONSOLIDATION_COST,
                 drop: float = DEFAULT_DROP, loss_per_nat: float = LOSS_PER_NAT) -> dict:
    n = sum(counts.values())
    h = shannon_entropy(counts)
    expected_drop = h * drop
    voi = expected_drop * n * loss_per_nat
    fire = bool(n >= MIN_FACTS and voi > cost)
    return {
        "n_facts": n,
        "entropy": round(h, 6),
        "expected_drop": round(expected_drop, 6),
        "voi": round(voi, 6),
        "cost": cost,
        "fire": fire,
        "reason": "voi>cost" if fire else ("too_few_facts" if n < MIN_FACTS else "voi<=cost"),
    }


def maybe_run(dry_run: bool = True) -> dict:
    decision = voi_decision(load_type_counts())
    decision["ts"] = datetime.now(timezone.utc).isoformat()
    decision["dry_run"] = dry_run
    decision["spawned"] = False
    logp = cache_dir() / "memory-voi-log.jsonl"
    if decision["fire"] and not dry_run:
        script = consolidation_script()
        if script.exists():
            try:
                subprocess.run(
                    [sys.executable, str(script), "--dry-run"],
                    timeout=120,
                    check=False,
                )
                decision["spawned"] = True
            except Exception as exc:
                decision["spawn_error"] = str(exc)
        else:
            decision["spawn_error"] = f"missing {script}"
    try:
        with logp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision) + "\n")
    except Exception:
        pass
    return decision


def self_test() -> int:
    # Uniform types → high entropy → fire
    counts = {str(i): 10.0 for i in range(10)}  # n=100, H=log(10)
    d = voi_decision(counts, cost=1.0, drop=0.15)
    assert d["fire"] is True, d
    # Tiny n → no fire
    d2 = voi_decision({"a": 2.0}, cost=1.0)
    assert d2["fire"] is False and d2["reason"] == "too_few_facts"
    # Dirac → H=0 → voi=0 → no fire
    d3 = voi_decision({"a": 100.0}, cost=0.1, drop=0.15)
    assert d3["entropy"] == 0.0
    assert d3["fire"] is False
    # Monotone: more entropy, more VOI
    d4 = voi_decision({"a": 50.0, "b": 50.0}, cost=999, drop=0.2)
    d5 = voi_decision({"a": 99.0, "b": 1.0}, cost=999, drop=0.2)
    assert d4["voi"] > d5["voi"]
    print("PASS memory-voi-consolidation self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--maybe-run", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", action="store_true", help="Allow spawning consolidation")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        dry = not args.live
        if args.maybe_run:
            d = maybe_run(dry_run=dry)
        else:
            d = voi_decision(load_type_counts())
        print(json.dumps(d, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"fire": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
