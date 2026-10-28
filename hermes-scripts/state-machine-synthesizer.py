#!/usr/bin/env python3
"""Synthesize a finite state machine from observed action sequences."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base


import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone, UTC

OUT = _hermes_root / "cache" / "synthesized-fsm.json"
ACTION_LOG = _hermes_root / "cache" / "action-log.json"
LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def load_actions() -> list:
    if ACTION_LOG.exists():
        try:
            obj = json.loads(ACTION_LOG.read_text())
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                return obj.get("actions") or obj.get("log") or []
        except (OSError, json.JSONDecodeError):
            pass
    try:
        if LIFECYCLE_DB.exists():
            conn = sqlite3.connect(str(LIFECYCLE_DB))
            try:
                names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                if "action_log" in names:
                    cols = [r[1] for r in conn.execute("PRAGMA table_info(action_log)").fetchall()]
                    rows = conn.execute("SELECT * FROM action_log").fetchall()
                    out = []
                    for row in rows:
                        rec = dict(zip(cols, row))
                        out.append(rec)
                    return out
            finally:
                conn.close()
    except Exception:
        pass
    return []


def synthesize(actions: list) -> dict:
    trans = defaultdict(int)
    states = []
    seen = set()
    seq = []
    for a in actions or []:
        if isinstance(a, dict):
            st = str(a.get("state") or a.get("from") or "s")
            act = str(a.get("action") or a.get("tool") or "act")
            nxt = str(a.get("next_state") or a.get("to") or st)
        else:
            st = "s"
            act = str(a)
            nxt = "s"
        seq.append((st, act, nxt))
        for x in (st, nxt):
            if x not in seen:
                seen.add(x)
                states.append(x)
        trans[(st, act, nxt)] += 1
    transitions = [
        {"from": f, "action": a, "to": t, "count": c}
        for (f, a, t), c in sorted(trans.items(), key=lambda kv: -kv[1])
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "states": states,
        "transitions": transitions,
        "n_observations": len(seq),
    }


def self_test() -> dict:
    acts = [
        {"state": "idle", "action": "plan", "next_state": "planned"},
        {"state": "planned", "action": "act", "next_state": "done"},
        {"state": "idle", "action": "plan", "next_state": "planned"},
        {"state": "done", "action": "reset", "next_state": "idle"},
    ]
    r = synthesize(acts)
    assert "idle" in r["states"] and "done" in r["states"], r
    counts = {(t["from"], t["action"], t["to"]): t["count"] for t in r["transitions"]}
    assert counts[("idle", "plan", "planned")] == 2
    assert synthesize([])["states"] == []
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
    actions = []
    raw = args.json
    if raw:
        try:
            obj = json.loads(raw)
            actions = obj if isinstance(obj, list) else obj.get("actions") or []
        except json.JSONDecodeError:
            actions = []
    if not actions:
        actions = load_actions()
    out = synthesize(actions)
    try:
        _atomic_write_json(OUT, out)
    except Exception:
        pass
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
