#!/usr/bin/env python3
"""loop-contract-init.py - Hash-locked Loop Contract (arXiv:2608.28281 LoopArena).
Write before any worker is dispatched; re-hash at end to detect scope drift.

Usage:
  python loop-contract-init.py --objective TEXT --verify TEXT --output PATH
  python loop-contract-init.py --verify-hash PATH
Exit codes: 0=OK, 1=hash mismatch, 2=usage error
"""
import argparse, hashlib, json, pathlib, sys, datetime

def _hash(obj, ver, stop):
    return hashlib.sha256(f"{obj}\x00{ver}\x00{stop}".encode()).hexdigest()

def cmd_init(a):
    c = {"objective": a.objective, "verify": a.verify, "stop_if": a.stop_if,
         "budget_turns": a.budget_turns, "budget_delegations": a.budget_delegations,
         "created_at": datetime.datetime.utcnow().isoformat() + "Z",
         "hash": _hash(a.objective, a.verify, a.stop_if)}
    out = pathlib.Path(a.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(c, indent=2) + "\n")
    print(f"[loop-contract] Written: {out}  hash={c['hash'][:16]}...")
    return 0

def cmd_verify(a):
    c = json.loads(pathlib.Path(a.verify_hash).expanduser().read_text())
    exp = _hash(c["objective"], c["verify"], c["stop_if"])
    stored = c.get("hash", "")
    if exp == stored:
        print(f"[loop-contract] Hash OK ({exp[:16]}...)"); return 0
    print(f"[loop-contract] SCOPE DRIFT: stored={stored[:16]} computed={exp[:16]}",
          file=sys.stderr); return 1

def main():
    p = argparse.ArgumentParser(description="Hash-locked Loop Contract")
    p.add_argument("--objective"); p.add_argument("--verify"); p.add_argument("--output")
    p.add_argument("--stop_if", default="3 consecutive same-tool failures")
    p.add_argument("--budget_turns", type=int, default=50)
    p.add_argument("--budget_delegations", type=int, default=8)
    p.add_argument("--verify-hash")
    a = p.parse_args()
    if a.verify_hash: return cmd_verify(a)
    missing = [f for f, v in [("--objective", a.objective), ("--verify", a.verify),
                               ("--output", a.output)] if not v]
    if missing: print(f"Missing: {missing}", file=sys.stderr); return 2
    return cmd_init(a)

if __name__ == "__main__": sys.exit(main())
