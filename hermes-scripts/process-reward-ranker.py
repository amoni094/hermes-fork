#!/usr/bin/env python3
"""Rank candidate process steps by a lightweight process reward model (SWE-TRACE)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "process-reward-rankings.json"


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def score_candidate(c: dict) -> dict:
    name = str(c.get("action") or c.get("step") or c.get("name") or "step")
    blob = json.dumps(c, default=str).lower()
    correctness = 0.5
    if c.get("tests_pass") or "correct" in blob:
        correctness = 0.9
    if c.get("error") or "fail" in blob:
        correctness = 0.1
    if c.get("correctness_proxy") is not None:
        try:
            correctness = float(c["correctness_proxy"])
        except (TypeError, ValueError):
            pass
    efficiency = 0.5
    cost = c.get("cost") or c.get("tool_calls") or 1
    try:
        efficiency = 1.0 / (1.0 + float(cost))
    except (TypeError, ValueError):
        efficiency = 0.5
    if c.get("efficiency_proxy") is not None:
        try:
            efficiency = float(c["efficiency_proxy"])
        except (TypeError, ValueError):
            pass
    correctness = min(1.0, max(0.0, correctness))
    efficiency = min(1.0, max(0.0, efficiency))
    reward = 0.6 * correctness + 0.4 * efficiency
    return {
        "action": name,
        "correctness_proxy": round(correctness, 6),
        "efficiency_proxy": round(efficiency, 6),
        "reward": round(reward, 6),
    }


def rank(candidates: list) -> dict:
    scored = [score_candidate(c if isinstance(c, dict) else {"action": str(c)}) for c in (candidates or [])]
    scored.sort(key=lambda r: -r["reward"])
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(scored),
        "ranked": scored,
    }


def self_test() -> dict:
    cs = [
        {"action": "patch", "correctness_proxy": 0.9, "efficiency_proxy": 0.8},
        {"action": "rewrite", "correctness_proxy": 0.4, "efficiency_proxy": 0.2},
        {"action": "noop", "correctness_proxy": 0.1, "efficiency_proxy": 1.0},
    ]
    r = rank(cs)
    assert r["ranked"][0]["action"] == "patch", r
    assert rank([])["n"] == 0
    return {"self_test": "PASS", "sample": r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    raw = args.json
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    cands = []
    if raw:
        try:
            obj = json.loads(raw)
            cands = obj if isinstance(obj, list) else obj.get("candidates") or []
        except json.JSONDecodeError:
            cands = []
    out = rank(cands)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
