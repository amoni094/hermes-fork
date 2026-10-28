#!/usr/bin/env python3
"""Rubric-based verifier for subgoals in tool-use chains (SCRIBE)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "subgoal-verification.json"


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def score_subgoal(sg: dict) -> dict:
    expected_tool = str(sg.get("expected_tool") or sg.get("tool") or "")
    used_tool = str(sg.get("used_tool") or sg.get("tool_used") or expected_tool)
    expected_args = sg.get("expected_args") if isinstance(sg.get("expected_args"), dict) else {}
    used_args = sg.get("used_args") if isinstance(sg.get("used_args"), dict) else expected_args
    achieved = bool(sg.get("achieved", sg.get("success", True)))
    correct_tool = (used_tool == expected_tool) if expected_tool else bool(used_tool)
    correct_args = used_args == expected_args if expected_args else True
    step_score = (0.4 * float(achieved) + 0.3 * float(correct_tool) + 0.3 * float(correct_args))
    return {
        "name": sg.get("name") or sg.get("subgoal") or "subgoal",
        "achieved": achieved,
        "correct_tool": correct_tool,
        "correct_args": correct_args,
        "step_score": round(step_score, 6),
    }


def verify(subgoals: list) -> dict:
    scored = [score_subgoal(s if isinstance(s, dict) else {"name": str(s)}) for s in (subgoals or [])]
    agg = sum(s["step_score"] for s in scored) / float(len(scored) or 1)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(scored),
        "aggregate_score": round(agg, 6),
        "subgoals": scored,
    }


def self_test() -> dict:
    sgs = [
        {"name": "read", "expected_tool": "read_file", "used_tool": "read_file", "expected_args": {"p": "a"}, "used_args": {"p": "a"}, "achieved": True},
        {"name": "bad", "expected_tool": "write_file", "used_tool": "terminal", "achieved": False, "expected_args": {"p": "b"}, "used_args": {}},
    ]
    r = verify(sgs)
    assert r["n"] == 2
    assert r["subgoals"][0]["step_score"] == 1.0
    assert r["subgoals"][1]["step_score"] < 0.5
    assert verify([])["n"] == 0
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
    subgoals = []
    raw = args.json
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    if raw:
        try:
            obj = json.loads(raw)
            subgoals = obj if isinstance(obj, list) else obj.get("subgoals") or []
        except json.JSONDecodeError:
            subgoals = []
    out = verify(subgoals)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
