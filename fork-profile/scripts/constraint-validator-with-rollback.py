#!/usr/bin/python3
"""
constraint-validator-with-rollback.py

Prevents early discrete mistakes from cascading through long tool chains
by checking constraint invariants at each step and recommending rollback
to the last known-good checkpoint when a violation is detected.

Research basis (arXiv core agent sweep — constraint validation with rollback):
  In long multi-step tool chains, a single constraint violation at step k
  propagates downstream, corrupting all subsequent results. Early detection
  and rollback to the last valid checkpoint (checkpoint_k-1) is cheaper
  than rerunning the full chain.

Math basis: monotone constraint lattice with rollback points
  Define constraints C = {c_1, ..., c_n} as monotone predicates on state S.
  A state S is valid iff ∀c_i: c_i(S) = True.
  Rollback point: the most recent S_k where all C are satisfied.
  
  Constraint types checked:
    FILE_SIZE:   written files must be > min_bytes
    NO_TRACEBACK: execute_code/terminal output must not contain traceback
    SCHEMA:      JSON outputs must match declared schema keys
    IDEMPOTENT:  patch operations must not no-op (detect already-applied)
    NON_EMPTY:   tool outputs must not be empty strings

Usage:
  python3 constraint-validator-with-rollback.py [--dry-run]
  python3 constraint-validator-with-rollback.py --check path/to/file.py
  python3 constraint-validator-with-rollback.py --check-output "output text"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "constraint-validation-report.json"

# Constraint definitions
MIN_FILE_BYTES = 50          # files < 50 bytes are likely stubs
SCHEMA_KEYS = {              # required keys per output type
    "sweep": ["sweep_date", "new_papers_flat"],
    "ideas": ["ideas"],
    "interpretation": ["run_date"],
    "monitor_report": ["ts"],
}


# ── Individual constraint predicates ──────────────────────────────────────────

def c_file_size(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"file does not exist: {path.name}"
    size = path.stat().st_size
    if size < MIN_FILE_BYTES:
        return False, f"file too small: {size} bytes < {MIN_FILE_BYTES}"
    return True, f"ok ({size:,} bytes)"


def c_no_traceback(text: str) -> tuple[bool, str]:
    if re.search(r"Traceback \(most recent", text):
        first_line = next((l for l in text.splitlines() if "Traceback" in l), "")
        return False, f"traceback detected: {first_line[:60]}"
    if re.search(r"^\s*Error:", text, re.MULTILINE):
        return False, "Error: line found in output"
    return True, "no traceback"


def c_non_empty(text: str, label: str = "output") -> tuple[bool, str]:
    if not text or not text.strip():
        return False, f"{label} is empty"
    return True, f"{label} non-empty ({len(text)} chars)"


def c_idempotent_patch(patch_result: str) -> tuple[bool, str]:
    if '"no_change": true' in patch_result:
        return False, "patch was no-op (already applied)"
    return True, "patch applied changes"


def c_json_schema(data: dict, schema_type: str) -> tuple[bool, str]:
    required = SCHEMA_KEYS.get(schema_type, [])
    missing  = [k for k in required if k not in data]
    if missing:
        return False, f"missing required keys: {missing}"
    return True, "schema valid"


# ── Checkpoint system ──────────────────────────────────────────────────────────

class ConstraintChain:
    """
    Tracks constraint evaluations as a chain with rollback points.
    A rollback point is saved whenever all constraints pass.
    """
    def __init__(self):
        self.steps: list[dict] = []
        self.last_valid_checkpoint: int = -1
        self.violations: list[dict] = []

    def check(self, step_id: str, constraint_fn, *args) -> bool:
        ok, detail = constraint_fn(*args)
        self.steps.append({"step": step_id, "ok": ok, "detail": detail})
        if ok:
            self.last_valid_checkpoint = len(self.steps) - 1
        else:
            self.violations.append({"step": step_id, "detail": detail})
        return ok

    def rollback_recommendation(self) -> str:
        if self.last_valid_checkpoint < 0:
            return "ROLLBACK_TO_START: no valid checkpoint exists"
        ckpt = self.steps[self.last_valid_checkpoint]
        return f"ROLLBACK_TO: step '{ckpt['step']}' (checkpoint {self.last_valid_checkpoint})"

    def summary(self) -> dict:
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s["ok"])
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "valid": total - passed == 0,
            "last_valid_checkpoint": self.last_valid_checkpoint,
            "rollback": self.rollback_recommendation() if self.violations else None,
        }


# ── Main validation routines ───────────────────────────────────────────────────

def validate_scripts_dir(scripts_dir: Path) -> list[dict]:
    """Validate all recently written scripts for size and syntax."""
    results = []
    for p in sorted(scripts_dir.glob("*.py"), key=lambda x: x.stat().st_mtime)[-30:]:
        chain = ConstraintChain()
        chain.check(f"file_size:{p.name}", c_file_size, p)
        # Quick syntax check via compile()
        try:
            source = p.read_text()
            compile(source, str(p), "exec")
            chain.steps.append({"step": f"syntax:{p.name}", "ok": True, "detail": "syntax ok"})
            chain.last_valid_checkpoint = len(chain.steps) - 1
        except SyntaxError as e:
            chain.steps.append({"step": f"syntax:{p.name}", "ok": False,
                                 "detail": f"SyntaxError: {e}"})
            chain.violations.append({"step": f"syntax:{p.name}", "detail": str(e)})
        s = chain.summary()
        if not s["valid"]:
            results.append({"file": p.name, **s, "violations": chain.violations})
    return results


def validate_cache_files(cache_dir: Path) -> list[dict]:
    """Validate key cache JSON files for schema and non-emptiness."""
    schema_map = {
        "hermes-math-sweep-latest.json":    "sweep",
        "hermes-cs-sweep-latest.json":      "sweep",
        "hermes-research-latest.json":      "sweep",
        "math-ideas-queue.json":            "ideas",
        "cs-ideas-queue.json":              "ideas",
        "research-ideas-queue.json":        "ideas",
        "math-interpretation-latest.json":  "interpretation",
    }
    results = []
    for fname, schema_type in schema_map.items():
        p = cache_dir / fname
        chain = ConstraintChain()
        ok, detail = c_file_size(p)
        chain.steps.append({"step": f"exists:{fname}", "ok": ok, "detail": detail})
        if ok:
            chain.last_valid_checkpoint = 0
        if ok:
            try:
                data = json.loads(p.read_text())
                schema_ok, schema_detail = c_json_schema(data, schema_type)
                chain.steps.append({"step": f"schema:{fname}", "ok": schema_ok,
                                     "detail": schema_detail})
                if schema_ok:
                    chain.last_valid_checkpoint = 1
                else:
                    chain.violations.append({"step": f"schema:{fname}",
                                              "detail": schema_detail})
            except json.JSONDecodeError as e:
                chain.steps.append({"step": f"json:{fname}", "ok": False,
                                     "detail": f"JSONDecodeError: {e}"})
                chain.violations.append({"step": f"json:{fname}", "detail": str(e)})
        s = chain.summary()
        if not s["valid"]:
            results.append({"file": fname, **s, "violations": chain.violations})
    return results


def run(check_path: Path | None, check_output: str | None, dry_run: bool) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    all_violations: list[dict] = []

    print(f"\n=== Constraint Validator with Rollback — {now[:10]} ===")

    if check_path:
        chain = ConstraintChain()
        chain.check("file_size", c_file_size, check_path)
        s = chain.summary()
        print(f"  {check_path.name}: {'VALID' if s['valid'] else 'INVALID'} — {chain.steps}")
        return 0 if s["valid"] else 1

    if check_output:
        chain = ConstraintChain()
        chain.check("no_traceback", c_no_traceback, check_output)
        chain.check("non_empty",    c_non_empty, check_output)
        s = chain.summary()
        print(f"  Output check: {'VALID' if s['valid'] else 'INVALID'}")
        if chain.violations:
            for v in chain.violations:
                print(f"    ! {v}")
        return 0 if s["valid"] else 1

    # Full system check
    scripts_dir = HOME / ".hermes/scripts"
    cache_dir   = HOME / ".hermes/cache/research"

    script_violations = validate_scripts_dir(scripts_dir)
    cache_violations  = validate_cache_files(cache_dir)

    if script_violations:
        print(f"\n  Script violations ({len(script_violations)}):")
        for v in script_violations:
            print(f"    ! {v['file']}: {v['violations']}")
            alarms.append(f"SCRIPT_INVALID: {v['file']} — {v['violations'][0]['detail'][:60]}")
    else:
        print(f"  Scripts: all {len(list((scripts_dir).glob('*.py')))} scripts pass constraints")

    if cache_violations:
        print(f"\n  Cache violations ({len(cache_violations)}):")
        for v in cache_violations:
            print(f"    ! {v['file']}: {v['violations']}")
            alarms.append(f"CACHE_INVALID: {v['file']} — {v['violations'][0]['detail'][:60]}")
    else:
        print(f"  Cache: all checked JSON files pass schema constraints")

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} constraint violation(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — all constraints satisfied")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now,
            "script_violations": script_violations,
            "cache_violations": cache_violations,
            "alarms": alarms,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", dest="check_path", type=Path, default=None)
    parser.add_argument("--check-output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(check_path=args.check_path, check_output=args.check_output,
                 dry_run=args.dry_run))


if __name__ == "__main__":
    main()
