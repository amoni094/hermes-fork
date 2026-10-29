#!/usr/bin/env python3
"""Verify multi-agent process traces against invariants."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sys
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "process-verification-report.json"


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


DEFAULT_INVARIANTS = [
    "no_self_message_loop",
    "unique_step_ids",
    "actor_present",
    "action_present",
]


def verify_trace(trace: list, invariants: list | None = None) -> dict:
    inv = invariants or DEFAULT_INVARIANTS
    violations = []
    seen_ids = set()
    prev_actor = None
    for i, step in enumerate(trace or []):
        if not isinstance(step, dict):
            violations.append({"step": i, "invariant": "step_is_object", "detail": type(step).__name__})
            continue
        sid = step.get("id", i)
        actor = step.get("actor") or step.get("agent")
        action = step.get("action") or step.get("tool")
        if "unique_step_ids" in inv:
            if sid in seen_ids:
                violations.append({"step": i, "invariant": "unique_step_ids", "detail": sid})
            seen_ids.add(sid)
        if "actor_present" in inv and not actor:
            violations.append({"step": i, "invariant": "actor_present"})
        if "action_present" in inv and not action:
            violations.append({"step": i, "invariant": "action_present"})
        if "no_self_message_loop" in inv and actor and prev_actor == actor and action == "message":
            violations.append({"step": i, "invariant": "no_self_message_loop", "detail": actor})
        prev_actor = actor
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "step_count": len(trace or []),
        "invariants": inv,
        "violations": violations,
        "ok": len(violations) == 0,
    }


def self_test() -> dict:
    good = [{"id": 1, "actor": "a", "action": "plan"}, {"id": 2, "actor": "b", "action": "act"}]
    bad = [{"id": 1, "actor": "a", "action": "message"}, {"id": 1, "actor": "a", "action": "message"}]
    g = verify_trace(good)
    b = verify_trace(bad)
    assert g["ok"] is True, g
    assert b["ok"] is False, b
    assert verify_trace([])["ok"] is True
    return {"self_test": "PASS", "good": g, "bad": b}


def _load_trace(args) -> list:
    if args.json:
        try:
            obj = json.loads(args.json)
            return obj if isinstance(obj, list) else obj.get("trace") or obj.get("steps") or []
        except json.JSONDecodeError:
            return []
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                obj = json.loads(raw)
                return obj if isinstance(obj, list) else obj.get("trace") or []
            except json.JSONDecodeError:
                return []
    return [
        {"id": 1, "actor": "planner", "action": "plan"},
        {"id": 2, "actor": "worker", "action": "execute"},
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    out = verify_trace(_load_trace(args))
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
