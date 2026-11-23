#!/usr/bin/env python3
"""routing-thompson-sampling.py — Beta-Bernoulli Thompson ranking.

KL-UCB (Cappé/Garivier) assumes Bernoulli rewards and saturates at index 1.0
on unused arms. Skill-beta-state is continuous-ish Beta with median n≈1, so
KL-UCB vs mean disagreement is structural. Thompson sampling draws from
Beta(alpha, beta) (Lattimore & Szepesvári Ch 36) and is the correct
exploration policy for this posterior.

Writes cache/routing-thompson-sampling.json. Deterministic seed for cron replay.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

EPS = 1e-15
TS_SEED = 0x74686F6D


def _cache_dir() -> Path:
    override = os.environ.get("HERMES_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2) + "\n")
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default


def compute(beta: dict) -> dict:
    names = sorted(beta.keys()) if isinstance(beta, dict) else []
    rng = random.Random(TS_SEED)
    rows = []
    for nm in names:
        e = beta.get(nm)
        if not isinstance(e, dict):
            e = {}
        try:
            a = float(e.get("alpha", 1.0))
            b = float(e.get("beta", 1.0))
        except (TypeError, ValueError):
            a, b = 1.0, 1.0
        a = max(a, EPS)
        b = max(b, EPS)
        n = max(0.0, a + b - 2.0)
        mu = a / (a + b)
        try:
            draw = rng.betavariate(a, b)
        except ValueError:
            draw = mu
        rows.append({"skill": nm, "n": n, "mu": mu, "thompson": draw})
    if not rows:
        return {"n_skills": 0, "alarm": False, "reason": "empty"}
    by_ts = sorted(rows, key=lambda r: -r["thompson"])
    by_mu = sorted(rows, key=lambda r: -r["mu"])
    n_median = sorted(r["n"] for r in rows)[len(rows) // 2]
    return {
        "ts": time.time(),
        "n_skills": len(rows),
        "thompson_top1": by_ts[0]["skill"],
        "mean_top1": by_mu[0]["skill"],
        "n_median": round(n_median, 6),
        "alarm": False,
        "reason": "ok",
        "policy": "thompson_beta",
        "top": [
            {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}
            for r in by_ts[:8]
        ],
    }


def run(cache=None):
    cache = cache or _cache_dir()
    beta = _load_json(cache / "skill-beta-state.json", {})
    result = compute(beta if isinstance(beta, dict) else {})
    try:
        _atomic_write_json(cache / "routing-thompson-sampling.json", result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        r = compute(
            {
                "star": {"alpha": 20.0, "beta": 2.0},
                "dud": {"alpha": 2.0, "beta": 20.0},
            }
        )
        assert r["n_skills"] == 2
        json.dumps(r)
    except Exception as e:
        failures.append(f"rank: {e}")
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            run(cache=d)
            assert (d / "routing-thompson-sampling.json").exists()
    except Exception as e:
        failures.append(f"io: {e}")
    return {
        "self_test": "PASS" if not failures else "FAIL",
        "n_failures": len(failures),
        "failures": failures,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r["self_test"] == "PASS" else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({"error": "shadow_path_failed"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
