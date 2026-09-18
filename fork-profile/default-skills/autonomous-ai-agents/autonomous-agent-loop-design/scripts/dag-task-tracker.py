#!/usr/bin/env python3
"""dag-task-tracker.py - DAG Task Completion Tracker (arXiv:2608.00267 LoopsBench).
Tasks have deps[] and regression_obligations[]. A task is DONE only when it
passes AND all its regression_obligations still pass.

Usage:
  python dag-task-tracker.py init --file dag-tasks.json
  Do NOT point --file at cache/loop-harness/feature_list.json (capability inventory).
  python dag-task-tracker.py add --id T1 --description TEXT [--deps T0] [--regress T0]
  python dag-task-tracker.py pass --id T1
  python dag-task-tracker.py fail --id T1 --reason TEXT
  python dag-task-tracker.py status
  python dag-task-tracker.py regress-check --id T2
Exit codes: 0=OK/all-pass, 1=failures, 2=usage error
"""
import argparse, json, pathlib, sys, datetime

def load(path):
    p = pathlib.Path(path).expanduser()
    if not p.exists():
        return {"tasks": []}
    data = json.loads(p.read_text())
    if isinstance(data, list):
        raise SystemExit(
            f"[dag] ERROR: {p} is a capability inventory (JSON list), not a DAG task file. "
            "Use dag-tasks.json. feature_list.json is read by reasoning-hooks.py inventory only."
        )
    if not isinstance(data, dict):
        raise SystemExit(f"[dag] ERROR: {p} is not a DAG task object")
    data.setdefault("tasks", [])
    return data

def save(data, path):
    p = pathlib.Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")

def get(data, tid): return next((t for t in data["tasks"] if t["id"] == tid), None)

def main():
    p = argparse.ArgumentParser(description="DAG Task Tracker")
    p.add_argument("command", choices=["init", "add", "pass", "fail", "status", "regress-check"])
    p.add_argument("--file", default="dag-tasks.json")
    p.add_argument("--id"); p.add_argument("--description")
    p.add_argument("--deps", default=""); p.add_argument("--regress", default="")
    p.add_argument("--reason", default="unspecified")
    a = p.parse_args()

    if a.command == "init":
        save({"tasks": []}, a.file); print(f"[dag] Initialized {a.file}"); return 0

    data = load(a.file)

    if a.command == "add":
        if get(data, a.id): print(f"[dag] ERROR: {a.id} exists", file=sys.stderr); return 2
        deps = [d.strip() for d in a.deps.split(",") if d.strip()]
        regs = [r.strip() for r in a.regress.split(",") if r.strip()]
        data["tasks"].append({"id": a.id, "description": a.description, "deps": deps,
            "regression_obligations": regs, "passed": False, "failed": False,
            "failure_reason": None, "updated_at": datetime.datetime.utcnow().isoformat() + "Z"})
        save(data, a.file); print(f"[dag] Added {a.id} deps={deps} regress={regs}"); return 0

    if a.command in ("pass", "fail"):
        t = get(data, a.id)
        if not t: print(f"[dag] ERROR: {a.id} not found", file=sys.stderr); return 2
        t["passed"] = a.command == "pass"; t["failed"] = a.command == "fail"
        t["failure_reason"] = None if a.command == "pass" else a.reason
        t["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        save(data, a.file); print(f"[dag] {a.id} marked {a.command.upper()}")
        if a.command == "pass":
            deps = [x for x in data["tasks"] if a.id in x.get("regression_obligations", [])]
            if deps: print(f"  NOTE: regression check needed: {[x['id'] for x in deps]}")
        return 0

    if a.command == "status":
        tasks = data["tasks"]; total = len(tasks)
        passed = sum(1 for t in tasks if t["passed"])
        failed = sum(1 for t in tasks if t["failed"])
        print(f"[dag] {passed}/{total} passed, {failed} failed, {total-passed-failed} pending")
        for t in tasks:
            s = "PASS" if t["passed"] else ("FAIL" if t["failed"] else "PEND")
            print(f"  [{s}] {t['id']}: {t['description'][:60]}")
            if t["failed"]: print(f"        reason: {t['failure_reason']}")
        stale = [(t["id"], r) for t in tasks if t["passed"]
                 for r in t.get("regression_obligations", [])
                 if not (get(data, r) or {}).get("passed")]
        if stale: print(f"  REGRESSION RISK: {stale}")
        return 0 if failed == 0 else 1

    if a.command == "regress-check":
        t = get(data, a.id)
        if not t: print(f"[dag] ERROR: {a.id} not found", file=sys.stderr); return 2
        obs = t.get("regression_obligations", [])
        if not obs: print(f"[dag] No obligations for {a.id}"); return 0
        fail = [o for o in obs if not (get(data, o) or {}).get("passed")]
        if fail: print(f"[dag] REGRESSION FAIL {a.id}: {fail}"); return 1
        print(f"[dag] Obligations satisfied for {a.id}: {obs}"); return 0

if __name__ == "__main__": sys.exit(main())
