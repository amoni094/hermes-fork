#!/usr/bin/env python3
"""
research-pipeline-weekly.py — Consolidated Hermes research pipeline.

Runs research stages in sequence. A failed sweep does not abort downstream
interpretation of cached results from a prior run. Skipped stages (missing
script/input) are non-fatal and do not cause exit 1.

  Stage 1 — CS primers refresh       cs-primers-overnight.py  (stale-check, quarterly cadence)
  Stage 2 — Math sub-sweep           hermes-math-sweep.py
  Stage 3 — CS/systems sweep         cs-research-sweep.py
  Stage 4 — Math interpretation      math-paper-interpreter.py
  Stage 5 — CS paper interpretation  cs-paper-interpreter.py
  Stage 6 — Improvements review      pending-improvements-review.py
  Stage 7 — Spike actuator           spike-actuator.py  (builds stubs from IMPLEMENT items)

Stage 7 runs recursively: after building stubs, it re-invokes Stages 4–6 on any
newly generated spikes until no new IMPLEMENT items appear (saturation). Each
recursive pass is capped at --max-passes (default 1; budget: base 6120s + 1*2820s = 8940s < 10800s)
to bound runtime. Use --max-passes 0 to skip recursion entirely.

Stage 1 replaces the standalone cs-primers-quarterly cron. It runs cs-primers-
overnight.py without --force so it only generates missing/stale primers. The
original cron is removed to avoid duplication.

The old hermes-research-sweep (69 cats) is intentionally omitted: its output
is not consumed by any interpreter and would exhaust the budget alone.

Per-stage timeouts sized so all stages + 3 recursive passes fit within the
10800s (3h) cron budget. Schedule: Sunday 03:00 UTC (14:00 AEDT) to avoid the
01:00 UTC slot that can be missed when the job is created on the same Sunday.

Usage:
  python3 research-pipeline-weekly.py [--dry-run] [--stages 1,2,3,4,5,6,7] [--limit N]
  python3 research-pipeline-weekly.py --stages 4,5,6,7   # interpret + review + actuate
  python3 research-pipeline-weekly.py --stages 7          # actuate only (re-read last report)
  python3 research-pipeline-weekly.py --max-passes 1      # single pass, no recursion
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

HERMES_PROFILE = os.environ.get("HERMES_PROFILE", "fork")

# A003-fix: use name-based unwrap (same as pending-improvements-review._resolve_paths)
# to avoid exists() accepting ghost doubled dirs like .../profiles/fork/profiles/fork/.
_hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
if _hh.name == HERMES_PROFILE or str(_hh).endswith(f"profiles/{HERMES_PROFILE}"):
    _CHILD_HOME  = str(_hh.parent.parent)   # strip profiles/<profile> → hermes base
    _profile_root = _hh
else:
    _CHILD_HOME  = str(_hh)                 # hh is already the hermes base
    _profile_root = _hh / "profiles" / HERMES_PROFILE

HERMES_HOME = Path(_CHILD_HOME)  # canonical base (used only for logging)

# SWEEP-003: resolve scripts from this file's directory, not HERMES_HOME
SCRIPTS   = Path(__file__).resolve().parent
CACHE_DIR = _profile_root / "cache" / "research"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PYTHON = sys.executable

# Per-stage timeouts (seconds).
# Budget: 3h (10800s) to accommodate recursive passes.
# Base pass sum: 300+2400+1500+1200+1200+300+120 = 7020s.
# Each recursive pass (stages 4+5+6+7) adds: 1200+1200+300+120 = 2820s.
# max_passes=1 (default): 7020+2820=9840s — fits 10800s with 960s slack.
# max_passes=2: 7020+2*2820=12660s > 10800s — NOT safe.
#
# Stage 2 raised from 1500→2400s: 52 math cats × 14 requests × ~1s min + 17.5s sleep/cat
# = ~1638s minimum even with instant fetches, so 1500s was structurally too tight.
_STAGE_TIMEOUT = {
    1:  300,   # cs-primers stale-check (fast, only generates missing)
    2: 2400,   # math sweep (52 cats × ~17.5s sleep + fetch; 1638s min, 2400s gives 33% headroom)
    3: 1500,   # cs sweep (17 cats, ~535s min — fits comfortably)
    4: 1200,   # math interpret (LLM calls)
    5: 1200,   # cs interpret
    6:  300,   # review
    7:  120,   # spike actuator (stdlib only, fast)
}
_LIMIT_STAGES   = {2, 3, 4, 5}   # stages that accept --limit; others do not

# Stages that form the recursive inner loop (re-run until saturation)
_RECURSIVE_STAGES = [4, 5, 6, 7]

# CS primers: only regenerate if INDEX.txt is older than 90 days
_PRIMERS_MAX_AGE_DAYS = 90

STAGES: dict = {
    1: dict(name="cs-primers",
            label="CS primers stale-check (cs-primers-overnight)",
            script=SCRIPTS / "cs-primers-overnight.py",
            output=CACHE_DIR / "cs-primers" / "INDEX.txt"),
    2: dict(name="math-sweep",
            label="Math sub-sweep (hermes-math-sweep)",
            script=SCRIPTS / "hermes-math-sweep.py",
            output=CACHE_DIR / "hermes-math-sweep-latest.json"),
    3: dict(name="cs-sweep",
            label="CS/systems sweep (cs-research-sweep)",
            script=SCRIPTS / "cs-research-sweep.py",
            output=CACHE_DIR / "hermes-cs-sweep-latest.json"),
    4: dict(name="math-interpret",
            label="Math interpretation + theory-to-impl bridge",
            script=SCRIPTS / "math-paper-interpreter.py",
            output=CACHE_DIR / "math-spike-queue.json",
            requires=CACHE_DIR / "hermes-math-sweep-latest.json"),
    5: dict(name="cs-interpret",
            label="CS paper interpretation",
            script=SCRIPTS / "cs-paper-interpreter.py",
            output=CACHE_DIR / "cs-spike-queue.json",
            requires=CACHE_DIR / "hermes-cs-sweep-latest.json"),
    6: dict(name="review",
            label="Improvements review + IMPLEMENT shortlist",
            script=SCRIPTS / "pending-improvements-review.py",
            output=_profile_root / "cache" / "pending-improvements-report.json",
            requires_any=[
                CACHE_DIR / "math-spike-queue.json",
                CACHE_DIR / "cs-spike-queue.json",
            ]),
    7: dict(name="spike-actuator",
            label="Spike actuator — build stubs from IMPLEMENT items",
            script=SCRIPTS / "spike-actuator.py",
            output=_profile_root / "cache" / "spike-actuator-log.json",
            requires=_profile_root / "cache" / "pending-improvements-report.json"),
}

def _count_implement(report_path: Path) -> int:
    """Return number of IMPLEMENT items in the improvements report, or 0 if missing/invalid."""
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        # Support both schema variants
        if "ranked" in data:
            return sum(1 for item in data["ranked"]
                       if item.get("recommendation") == "IMPLEMENT")
        elif "implement" in data:
            return len(data["implement"])
        return 0
    except Exception:
        return 0


def _count_viable_stubs(log_path: Path) -> int:
    """Return viable_stubs_created from spike-actuator log, or 0 if missing/invalid.

    SA-001: saturation requires BOTH unchanged IMPLEMENT count AND no new viable stubs.
    A pass that created new viable stubs may unlock new interpretation paths, so it
    must recurse even when the IMPLEMENT count is unchanged.
    """
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
        return int(data.get("viable_stubs_created", 0))
    except Exception:
        return 0


# Tri-state: "ok" | "skip" | "fail"
def run_stage(n: int, stage: dict, run_start: float,
              dry_run: bool, extra: list, recursive_pass: int = 0) -> str:
    script = stage["script"]

    # — Guard: script missing
    if not script.exists():
        print(f"[pipeline] Stage {n} SKIP — not found: {script}", flush=True)
        return "skip"

    # — Stage 1 special: only run if INDEX.txt is missing or >90 days old
    if n == 1:
        idx = stage["output"]
        if idx.exists():
            age_days = (time.time() - idx.stat().st_mtime) / 86400
            if age_days < _PRIMERS_MAX_AGE_DAYS:
                print(f"[pipeline] Stage 1 SKIP — primers fresh ({age_days:.0f}d < {_PRIMERS_MAX_AGE_DAYS}d)", flush=True)
                return "skip"
        # Fall through to run cs-primers-overnight.py (generates missing primers only)

    # — Guard: required input missing (skip only on pass 0; recursive passes use stale cache)
    if "requires" in stage:
        req = stage["requires"]
        if not req.exists():
            print(f"[pipeline] Stage {n} SKIP — missing input: {req}", flush=True)
            return "skip"
        # On the base pass, warn if input is stale but still run — sweep failures shouldn't
        # block interpretation of the last good cache. Hard-skip only if file is truly absent.
        if recursive_pass == 0 and req.stat().st_mtime < run_start:
            print(f"[pipeline] Stage {n} WARN — input is stale (from prior run): {req}", flush=True)
            # Fall through: run the interpreter on cached data

    if "requires_any" in stage:
        fresh = [p for p in stage["requires_any"]
                 if p.exists() and p.stat().st_mtime >= run_start]
        if not fresh:
            existing = [p for p in stage["requires_any"] if p.exists()]
            if not existing:
                print(f"[pipeline] Stage {n} SKIP — no inputs found", flush=True)
                return "skip"
            # Stale cache exists: allow review to run on it with a warning
            print(f"[pipeline] Stage {n} WARN — inputs are stale; using prior cache", flush=True)

    # — Build command; RP-003: pass --input to interpret stages so they read
    #   the file the orchestrator validated, not a hardcoded path in the child.
    cmd = [PYTHON, str(script)]
    if n in _LIMIT_STAGES:
        cmd += extra
    # Stage 1 (cs-primers) does not accept --dry-run; skip forwarding it.
    if dry_run and n != 1:
        cmd += ["--dry-run"]
    if n == 4 and "requires" in stage:
        cmd += ["--input", str(stage["requires"])]
    if n == 5 and "requires" in stage:
        cmd += ["--input", str(stage["requires"])]

    print(f"\n[pipeline] Stage {n}: {stage['label']}", flush=True)
    print(f"[pipeline]   {' '.join(str(a) for a in cmd)}", flush=True)

    t0      = time.monotonic()
    timeout = _STAGE_TIMEOUT.get(n, 1800)
    env     = {**os.environ, "HERMES_HOME": _CHILD_HOME, "HERMES_PROFILE": HERMES_PROFILE}
    # Stages 4+5 (interpreter scripts) import anthropic from ~/.local/lib which the
    # landlock policy cannot grant recursively. They are already isolated inside the
    # outer pipeline sandbox, so running them on the host subprocess is safe.
    if n in (4, 5):
        env["HERMES_NO_SANDBOX"] = "1"
    try:
        rc = subprocess.run(cmd, env=env, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"[pipeline] Stage {n} TIMEOUT after {timeout}s", flush=True)
        return "fail"
    except Exception as exc:
        print(f"[pipeline] Stage {n} ERROR: {exc}", flush=True)
        return "fail"

    ok = rc == 0
    print(f"[pipeline] Stage {n} {'OK' if ok else f'FAILED (exit {rc})'} "
          f"in {time.monotonic()-t0:.1f}s", flush=True)
    return "ok" if ok else "fail"


def _save_json_atomic(path: Path, data: dict) -> None:
    """Atomic JSON write: tmp then os.replace. Loops os.write for short writes."""
    payload = json.dumps(data, indent=2).encode()
    tmp = path.with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        view = memoryview(payload)
        written = 0
        while written < len(payload):
            n = os.write(fd, view[written:])
            if n <= 0:
                raise OSError("os.write returned 0")
            written += n
    finally:
        os.close(fd)
    os.replace(str(tmp), str(path))


def main() -> None:
    pa = argparse.ArgumentParser(description="Weekly Hermes research pipeline")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--stages", default="1,2,3,4,5,6,7")
    pa.add_argument("--limit", type=int, default=None)
    pa.add_argument("--max-passes",                    type=int, default=1,
                    help="Max recursive re-passes of stages 4-7 after new stubs are built (default: 1; budget: 6120+N*2820 < 10800s)")
    args = pa.parse_args()

    requested = [int(s.strip()) for s in args.stages.split(",") if s.strip()]
    bad = [n for n in requested if n not in STAGES]
    if bad:
        print(f"[pipeline] Unknown stages: {bad}. Valid: {sorted(STAGES)}", file=sys.stderr)
        sys.exit(1)

    extra = ["--limit", str(args.limit)] if args.limit else []
    run_start = time.time()

    print(f"[pipeline] research-pipeline-weekly {datetime.now(UTC).isoformat()}")
    print(f"[pipeline] HOME={_CHILD_HOME}  profile={HERMES_PROFILE}  scripts={SCRIPTS}")
    print(f"[pipeline] stages={requested}  max_passes={args.max_passes}  dry_run={args.dry_run}")

    report_path = STAGES[6]["output"]
    all_results: list[dict] = []

    # ── Base pass: run all requested stages ───────────────────────────────────
    results: dict = {}
    for n in requested:
        results[n] = run_stage(n, STAGES[n], run_start, args.dry_run, extra, recursive_pass=0)
    all_results.append({"pass": 0, "stages": dict(results)})

    # ── Recursive passes: re-run inner loop until saturation ──────────────────
    # Only enter recursion if: Stage 7 is in scope, spike-actuator script exists,
    # and there are IMPLEMENT items to act on.
    inner = [n for n in _RECURSIVE_STAGES if n in requested]
    implement_before = _count_implement(report_path)
    spike_log_path   = STAGES[7]["output"] if 7 in STAGES else None

    for pass_num in range(1, args.max_passes + 1):
        if 7 not in inner or not STAGES[7]["script"].exists():
            print("[pipeline] Recursion skipped — Stage 7 not in scope or script missing", flush=True)
            break
        if implement_before == 0:
            print(f"[pipeline] Recursion pass {pass_num}: no IMPLEMENT items to act on, stopping.", flush=True)
            break

        print(f"\n[pipeline] ── Recursive pass {pass_num}/{args.max_passes} (inner stages {inner}) ──", flush=True)
        pass_results: dict = {}
        for n in inner:
            pass_results[n] = run_stage(n, STAGES[n], run_start, args.dry_run, extra,
                                        recursive_pass=pass_num)
        all_results.append({"pass": pass_num, "stages": dict(pass_results)})

        implement_after = _count_implement(report_path)
        viable_stubs    = _count_viable_stubs(spike_log_path) if spike_log_path else 0
        print(f"[pipeline] Pass {pass_num}: IMPLEMENT count {implement_before} → {implement_after}, "
              f"viable stubs created this pass: {viable_stubs}", flush=True)

        # SA-001: saturation requires BOTH conditions:
        #   1. IMPLEMENT count unchanged (no new items surfaced)
        #   2. No new viable stubs created (new stubs may unlock new interpretation paths)
        if implement_after == implement_before and viable_stubs == 0:
            print(f"[pipeline] Saturation reached at pass {pass_num} — "
                  f"no new IMPLEMENT items and no new viable stubs.", flush=True)
            break
        implement_before = implement_after

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed  = round(time.monotonic() - (run_start - time.monotonic() + time.monotonic()), 1)
    # (use wall clock delta properly)
    elapsed  = round(time.time() - run_start, 1)
    failures = [n for n, s in results.items() if s == "fail"]
    skips    = [n for n, s in results.items() if s == "skip"]
    # A009-fix: also count failures from recursive passes
    for pr in all_results[1:]:  # all_results[0] is base pass (already in results)
        for n, s in pr.get("stages", {}).items():
            if s == "fail" and n not in failures:
                failures.append(n)

    if not args.dry_run:
        summary = {
            "run_at":      datetime.now(UTC).isoformat(),
            "dry_run":     False,
            "elapsed_s":   elapsed,
            "all_ok":      not failures,
            "failures":    failures,
            "skips":       skips,
            "passes":      len(all_results),
            "pass_results": all_results,
            "stages": {
                str(n): {"name":          STAGES[n]["name"],
                         "status":        s,
                         "output_exists": STAGES[n]["output"].exists()}
                for n, s in results.items()
            },
        }
        summary_path = _profile_root / "cache" / "research-pipeline-last-run.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        _save_json_atomic(summary_path, summary)
        print(f"\n[pipeline] Summary: {summary_path}")

    print("\n[pipeline] Results:")
    for n, s in results.items():
        print(f"  {s.upper():4s} Stage {n}: {STAGES[n]['label']}")
    print(f"  Total {elapsed:.1f}s  passes={len(all_results)}  dry_run={args.dry_run}")
    if skips:
        print(f"  Skipped (non-fatal): {skips}")

    # Exit 1 only if a non-skipped stage actually failed
    if failures:
        print(f"[pipeline] {len(failures)} stage(s) failed: {failures}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
