#!/usr/bin/env python3
"""Score each tool-use step with a lightweight process reward (ToolPRMBench)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "prm-step-scores.json"


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def score_step(step: dict, seen: set) -> dict:
    completes = bool(step.get("completes_subgoal") or step.get("success") or step.get("achieved"))
    backtracks = bool(step.get("backtracks") or step.get("undo") or (str(step.get("action") or "").lower() in ("undo", "retry", "revert")))
    sig = json.dumps({"tool": step.get("tool") or step.get("action"), "args": step.get("args")}, sort_keys=True, default=str)
    redundant = bool(step.get("redundant")) or sig in seen
    seen.add(sig)
    prm = 0.5 * float(completes) - 0.3 * float(backtracks) - 0.2 * float(redundant)
    return {
        "completes_subgoal": completes,
        "backtracks": backtracks,
        "redundant": redundant,
        "prm_score": round(prm, 6),
        "tool": step.get("tool") or step.get("action") or "",
    }


def score_steps(steps: list) -> dict:
    seen = set()
    rows = []
    for i, st in enumerate(steps or []):
        if not isinstance(st, dict):
            st = {"action": str(st)}
        row = score_step(st, seen)
        row["step"] = i
        rows.append(row)
    mean = sum(r["prm_score"] for r in rows) / float(len(rows) or 1)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(rows),
        "mean_prm": round(mean, 6),
        "steps": rows,
    }


def self_test() -> dict:
    steps = [
        {"tool": "t", "args": {"a": 1}, "completes_subgoal": True},
        {"tool": "t", "args": {"a": 1}, "completes_subgoal": False},
        {"tool": "undo", "backtracks": True},
    ]
    r = score_steps(steps)
    assert r["steps"][0]["prm_score"] == 0.5, r
    assert r["steps"][1]["redundant"] is True
    assert r["steps"][2]["backtracks"] is True
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
    steps = []
    if raw:
        try:
            obj = json.loads(raw)
            steps = obj if isinstance(obj, list) else obj.get("steps") or []
        except json.JSONDecodeError:
            steps = []
    out = score_steps(steps)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
