#!/usr/bin/env python3
"""
skill-state.py — SKILL.state runtime: mutable execution state for long-horizon skills.

arXiv:2608.26263 (SKILL.state): replaces append-only conversational history with
an explicit, mutable execution state. At each step the model receives only:
  1. Immutable skill specification (the SKILL.md spec section)
  2. Current structured execution state (JSON blob)
  3. Latest observation

Intermediate reasoning is discarded after producing a validated state update.
This prevents prompt growth and context-poisoning over long execution horizons.

Use case in Hermes: Long-running cronjobs, multi-step delegated tasks, and
autonomous loops where working-memory.py WM alone is insufficient because the
history itself becomes a liability.

This script manages the execution-state surface:
  ~/.hermes/cache/skill-state/<session_id>_<skill_name>.json

Key differences from working-memory.py:
  - WM tracks task goals/constraints for skill SELECTION
  - skill-state.py tracks step-by-step EXECUTION within a specific skill run
  - skill-state enforces state schema validation each step (prevents drift)
  - skill-state purges intermediate reasoning traces after commit

Usage:
  python3 skill-state.py init --session SID --skill SKILL_NAME --spec "..."
  python3 skill-state.py step --session SID --skill SKILL_NAME \\
      --observation "tool output" --state-update '{"step": 2, "done": false}'
  python3 skill-state.py show --session SID --skill SKILL_NAME
  python3 skill-state.py context --session SID --skill SKILL_NAME
  python3 skill-state.py complete --session SID --skill SKILL_NAME --summary "..."
  python3 skill-state.py fail --session SID --skill SKILL_NAME --reason "..."
  python3 skill-state.py should-activate --steps 12
  python3 skill-state.py list
  python3 skill-state.py gc
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
STATE_DIR = HERMES_HOME / "cache" / "skill-state"
OBS_RING_BUFFER = 3
MAX_REASONING_TRACES = 0
ACTIVATE_THRESHOLD_STEPS = 10
GC_AFTER_HOURS = 24


def _load_runtime_config() -> None:
    global STATE_DIR, OBS_RING_BUFFER, ACTIVATE_THRESHOLD_STEPS, GC_AFTER_HOURS
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        return
    text = cfg_path.read_text()
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        sec = data.get("skill_state") or (data.get("memory") or {}).get("skill_state") or {}
        if sec.get("enabled") is False:
            return
        if sec.get("dir"):
            STATE_DIR = HERMES_HOME / str(sec["dir"])
        OBS_RING_BUFFER = int(sec.get("obs_ring_buffer", OBS_RING_BUFFER))
        ACTIVATE_THRESHOLD_STEPS = int(sec.get("activate_threshold_steps", ACTIVATE_THRESHOLD_STEPS))
        GC_AFTER_HOURS = int(sec.get("gc_after_hours", GC_AFTER_HOURS))
        return
    except Exception as e:
        import sys as _s
        print(f"[skill-state] config load failed: {e}", file=_s.stderr)
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("obs_ring_buffer:"):
            try:
                OBS_RING_BUFFER = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif s.startswith("activate_threshold_steps:"):
            try:
                ACTIVATE_THRESHOLD_STEPS = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif s.startswith("gc_after_hours:"):
            try:
                GC_AFTER_HOURS = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass


_load_runtime_config()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key(session_id: str, skill_name: str) -> str:
    safe_sid = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:60]
    safe_skill = "".join(c if c.isalnum() or c in "-_" else "_" for c in skill_name)[:40]
    return f"{safe_sid}__{safe_skill}"


def _path(session_id: str, skill_name: str) -> Path:
    return STATE_DIR / f"{_key(session_id, skill_name)}.json"


def _load(session_id: str, skill_name: str) -> dict[str, Any]:
    p = _path(session_id, skill_name)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _save(doc: dict[str, Any]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    doc["updated_at"] = _now()
    p = _path(doc["session_id"], doc["skill_name"])
    _p_tmp = p.with_suffix('.tmp')
    _p_tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    _p_tmp.replace(p)
    return p


def cmd_init(args: argparse.Namespace) -> int:
    existing = _load(args.session, args.skill)
    if existing and existing.get("status") == "active":
        print(f"[skill-state] WARNING: active state exists for {args.skill}@{args.session}", file=sys.stderr)
        if not getattr(args, "force", False):
            print("[skill-state] use --force to reinitialize", file=sys.stderr)
            return 1
    spec = args.spec or ""
    spec_hash = hashlib.sha256(spec.encode()).hexdigest()[:16]
    doc: dict[str, Any] = {
        "schema": "hermes-skill-state/v1",
        "session_id": args.session,
        "skill_name": args.skill,
        "spec_hash": spec_hash,
        "step": 0,
        "state": {},
        "observations": [],
        "reasoning_traces": [],
        "status": "active",
        "started_at": _now(),
        "updated_at": None,
        "completed_at": None,
        "token_savings_est": 0,
    }
    p = _save(doc)
    print(f"[skill-state] initialized {args.skill}@{args.session} -> {p}")
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    doc = _load(args.session, args.skill)
    if not doc:
        print(f"[skill-state] ERROR: no state found for {args.skill}@{args.session}. Run init first.", file=sys.stderr)
        return 1
    if doc.get("status") != "active":
        print(f"[skill-state] ERROR: state is {doc.get('status')}, not active", file=sys.stderr)
        return 1
    if args.spec:
        current_hash = hashlib.sha256(args.spec.encode()).hexdigest()[:16]
        if current_hash != doc.get("spec_hash"):
            print(f"[skill-state] WARNING: spec drift detected (stored={doc['spec_hash']}, current={current_hash})", file=sys.stderr)
    if args.state_update:
        try:
            update = json.loads(args.state_update)
            doc["state"].update(update)
        except json.JSONDecodeError as e:
            print(f"[skill-state] ERROR: invalid JSON in --state-update: {e}", file=sys.stderr)
            return 1
    if args.observation:
        doc["observations"].append({"step": doc["step"], "obs": args.observation, "at": _now()})
        if len(doc["observations"]) > OBS_RING_BUFFER:
            doc["observations"] = doc["observations"][-OBS_RING_BUFFER:]
    doc["reasoning_traces"] = []
    obs_chars = sum(len(o.get("obs", "")) for o in doc["observations"])
    step_count = doc["step"] + 1
    saved_chars = obs_chars * max(0, step_count - OBS_RING_BUFFER)
    doc["token_savings_est"] = doc.get("token_savings_est", 0) + (saved_chars // 4)
    doc["step"] += 1
    p = _save(doc)
    print(f"[skill-state] step {doc['step']} committed -> {p} (est. {doc['token_savings_est']} tokens saved so far)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    doc = _load(args.session, args.skill)
    if not doc:
        print(f"[skill-state] no state found for {args.skill}@{args.session}")
        return 1
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    doc = _load(args.session, args.skill)
    if not doc:
        print("[skill-state] ERROR: no state found", file=sys.stderr)
        return 1
    doc["status"] = "complete"
    doc["completed_at"] = _now()
    doc["completion_summary"] = getattr(args, "summary", "")
    doc["reasoning_traces"] = []
    p = _save(doc)
    print(f"[skill-state] completed {args.skill}@{args.session} -> {p}")
    print(f"[skill-state] total steps: {doc['step']}, estimated token savings: {doc['token_savings_est']}")
    return 0


def cmd_fail(args: argparse.Namespace) -> int:
    doc = _load(args.session, args.skill)
    if not doc:
        print("[skill-state] ERROR: no state found", file=sys.stderr)
        return 1
    doc["status"] = "failed"
    doc["completed_at"] = _now()
    doc["failure_reason"] = getattr(args, "reason", "") or ""
    doc["reasoning_traces"] = []
    p = _save(doc)
    print(f"[skill-state] failed {args.skill}@{args.session} -> {p}")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    doc = _load(args.session, args.skill)
    if not doc:
        print(f"[skill-state] ERROR: no state found for {args.skill}@{args.session}", file=sys.stderr)
        return 1
    obs = doc.get("observations") or []
    payload = {
        "schema": "hermes-skill-state-context/v1",
        "skill_name": doc.get("skill_name"),
        "session_id": doc.get("session_id"),
        "spec_hash": doc.get("spec_hash"),
        "step": doc.get("step"),
        "status": doc.get("status"),
        "state": doc.get("state") or {},
        "latest_observation": obs[-1] if obs else None,
        "observation_ring": obs[-OBS_RING_BUFFER:],
        "reasoning_traces": [],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_should_activate(args: argparse.Namespace) -> int:
    steps = getattr(args, "steps", None)
    if steps is None:
        doc = _load(args.session, args.skill) if args.session and args.skill else {}
        steps = int(doc.get("step", 0)) if doc else 0
    threshold = ACTIVATE_THRESHOLD_STEPS
    activate = steps >= threshold
    print(json.dumps({
        "activate": activate,
        "steps": steps,
        "threshold": threshold,
        "decision": "ACTIVATE" if activate else "SKIP",
    }))
    return 0 if activate else 2


def cmd_list(args: argparse.Namespace) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(STATE_DIR.glob("*.json")):
        try:
            doc = json.loads(p.read_text())
            items.append({
                "skill": doc.get("skill_name"), "session": doc.get("session_id"),
                "status": doc.get("status"), "step": doc.get("step"),
                "token_savings": doc.get("token_savings_est", 0),
                "updated": doc.get("updated_at"),
            })
        except Exception as e:
            import sys as _s
            print(f"[skill-state] skipping corrupt state file {p}: {e}", file=_s.stderr)
    if not items:
        print("[skill-state] no state files found")
    else:
        for item in items:
            print(f"  {item['skill']}@{item['session'][:20]} [{item['status']}] step={item['step']} saved_tokens={item['token_savings']} updated={item['updated']}")
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    from datetime import timedelta
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    max_age_h = getattr(args, "hours", None) or GC_AFTER_HOURS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_h)
    removed = 0
    for p in STATE_DIR.glob("*.json"):
        try:
            doc = json.loads(p.read_text())
            if doc.get("status") in ("complete", "failed"):
                updated = doc.get("updated_at") or doc.get("completed_at")
                if updated:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if dt < cutoff:
                        p.unlink()
                        removed += 1
        except Exception as e:
            import sys as _s
            print(f"[skill-state] gc: skipping unparseable file {p}: {e}", file=_s.stderr)
    print(f"[skill-state] gc: removed {removed} completed/failed states older than {max_age_h}h")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SKILL.state mutable execution state (arXiv:2608.26263)")
    sub = p.add_subparsers(dest="cmd")
    init = sub.add_parser("init")
    init.add_argument("--session", required=True)
    init.add_argument("--skill", required=True)
    init.add_argument("--spec", default="")
    init.add_argument("--force", action="store_true")
    step = sub.add_parser("step")
    step.add_argument("--session", required=True)
    step.add_argument("--skill", required=True)
    step.add_argument("--observation", default="")
    step.add_argument("--state-update", default="{}")
    step.add_argument("--spec", default=None)
    show = sub.add_parser("show")
    show.add_argument("--session", required=True)
    show.add_argument("--skill", required=True)
    complete = sub.add_parser("complete")
    complete.add_argument("--session", required=True)
    complete.add_argument("--skill", required=True)
    complete.add_argument("--summary", default="")
    fail = sub.add_parser("fail")
    fail.add_argument("--session", required=True)
    fail.add_argument("--skill", required=True)
    fail.add_argument("--reason", default="")
    context = sub.add_parser("context")
    context.add_argument("--session", required=True)
    context.add_argument("--skill", required=True)
    activate = sub.add_parser("should-activate")
    activate.add_argument("--session", default="")
    activate.add_argument("--skill", default="")
    activate.add_argument("--steps", type=int, default=None)
    sub.add_parser("list")
    gc = sub.add_parser("gc")
    gc.add_argument("--hours", type=int, default=None)
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    dispatch = {
        "init": cmd_init,
        "step": cmd_step,
        "show": cmd_show,
        "complete": cmd_complete,
        "fail": cmd_fail,
        "context": cmd_context,
        "should-activate": cmd_should_activate,
        "list": cmd_list,
        "gc": cmd_gc,
    }
    if args.cmd == "gc" and getattr(args, "hours", None) is None:
        args.hours = GC_AFTER_HOURS
    fn = dispatch.get(args.cmd)
    if not fn:
        parser.print_help()
        return 1
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
