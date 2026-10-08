#!/usr/bin/env python3
"""
jev-gate-nightly.py — Nightly promotion gate for jev-turn-evaluator.

Reads cache/jev-turn-scores.jsonl, computes mean_score and error_rate over a
rolling window, and prints a verdict. Does NOT auto-mutate config.yaml —
promotion is manual.

Usage:
    python3 jev-gate-nightly.py [--window N] [--min-turns M]

Output (stdout):
    PROMOTE   — criteria met; manual step: add jev-turn-evaluator to plugins.enabled
    HOLD      — insufficient data or criteria not met
    DEGRADED  — error_rate too high; consider disabling

Exit codes:
    0 = PROMOTE
    1 = HOLD
    2 = DEGRADED
    3 = read error

Promotion criteria:
    - >= MIN_TURNS scored turns in window (default 20)
    - mean_score  >= 3.5  (0-5 scale; avg of factual_coherence, task_progress, efficiency)
    - error_rate  <  0.10 (fraction of scorer-errored turns)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes" / "profiles" / "fork")))
SCORES_FILE  = HERMES_HOME / "cache" / "jev-turn-scores.jsonl"
WINDOW_DAYS  = 7
MIN_TURNS    = 20
MIN_SCORE    = 3.5
MAX_ERROR    = 0.10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scores-file", type=Path, default=SCORES_FILE)
    p.add_argument("--window",    type=int,   default=WINDOW_DAYS, metavar="DAYS")
    p.add_argument("--min-turns", type=int,   default=MIN_TURNS)
    p.add_argument("--min-score", type=float, default=MIN_SCORE)
    p.add_argument("--max-error", type=float, default=MAX_ERROR)
    p.add_argument("--json",      dest="as_json", action="store_true")
    return p.parse_args()


def load_window(path: Path, window_days: int) -> list[dict]:
    if not path.exists():
        return []
    cutoff = datetime.now(tz=timezone.utc).timestamp() - window_days * 86400
    out = []
    with path.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"WARN  line {lineno}: {e}", file=sys.stderr)
                continue
            ts = obj.get("timestamp", 0)
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts).timestamp()
                except ValueError:
                    ts = 0
            if ts >= cutoff:
                out.append(obj)
    return out


def metrics(entries: list[dict]) -> dict:
    total  = len(entries)
    errors = 0
    scored = 0
    dims: dict[str, list[float]] = {d: [] for d in ("factual_coherence", "task_progress", "efficiency", "tool_alignment")}

    for e in entries:
        if e.get("errors"):
            errors += 1
            continue
        s = e.get("scores") or {}
        got = False
        for d in ("factual_coherence", "task_progress", "efficiency"):
            v = s.get(d)
            if v is not None:
                try:
                    dims[d].append(float(v)); got = True
                except (TypeError, ValueError):
                    pass
        ta = s.get("tool_alignment")
        if ta is not None:
            dims["tool_alignment"].append(1.0 if ta else 0.0); got = True
        if got:
            scored += 1

    dim_means = {d: (statistics.mean(vs) if vs else None) for d, vs in dims.items()}
    ordinal = [dim_means[d] for d in ("factual_coherence", "task_progress", "efficiency") if dim_means[d] is not None]  # type: ignore[misc]
    mean_score = statistics.mean(ordinal) if ordinal else None

    return {
        "total_turns":  total,
        "error_turns":  errors,
        "error_rate":   errors / total if total else 0.0,
        "scored_turns": scored,
        "mean_score":   mean_score,
        "dim_means":    dim_means,
    }


def verdict(m: dict, args: argparse.Namespace) -> tuple[str, int, str]:
    if m["error_rate"] >= args.max_error and m["total_turns"] >= 5:
        return "DEGRADED", 2, f"error_rate={m['error_rate']:.2%} >= {args.max_error:.2%}"
    if m["scored_turns"] < args.min_turns:
        return "HOLD", 1, f"scored_turns={m['scored_turns']} < min_turns={args.min_turns}"
    if m["mean_score"] is None:
        return "HOLD", 1, "mean_score=None (all turns errored?)"
    if m["mean_score"] < args.min_score:
        return "HOLD", 1, f"mean_score={m['mean_score']:.3f} < {args.min_score}"
    return "PROMOTE", 0, (
        f"mean_score={m['mean_score']:.3f} >= {args.min_score}, "
        f"error_rate={m['error_rate']:.2%} < {args.max_error:.2%}, "
        f"scored_turns={m['scored_turns']}"
    )


def main() -> int:
    args = parse_args()
    try:
        entries = load_window(args.scores_file, args.window)
    except OSError as e:
        msg = f"Cannot read {args.scores_file}: {e}"
        if args.as_json:
            print(json.dumps({"verdict": "ERROR", "reason": msg}))
        else:
            print(f"ERROR  {msg}", file=sys.stderr)
        return 3

    m = metrics(entries)
    v, code, reason = verdict(m, args)

    if args.as_json:
        print(json.dumps({
            "verdict": v, "reason": reason, "metrics": m,
            "window_days": args.window, "scores_file": str(args.scores_file),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }, indent=2, default=str))
    else:
        sep = "=" * 60
        ms = m["mean_score"]
        print(f"\n{sep}")
        print(f"  jev-gate-nightly — jev-turn-evaluator promotion gate")
        print(f"  Window {args.window}d | {args.scores_file.name}")
        print(f"{sep}")
        print(f"  Total turns  : {m['total_turns']}")
        print(f"  Scored turns : {m['scored_turns']}")
        print(f"  Error turns  : {m['error_turns']}  ({m['error_rate']:.1%})")
        print(f"  Mean score   : {ms:.3f}" if ms is not None else "  Mean score   : N/A")
        print("  Dim means    :")
        for d, val in m["dim_means"].items():
            print(f"    {d:<22} {f'{val:.3f}' if val is not None else 'N/A'}")
        print()
        print(f"  VERDICT : {v}")
        print(f"  Reason  : {reason}")
        if v == "PROMOTE":
            print()
            print("  Manual promotion steps:")
            print("    1. Add 'jev-turn-evaluator' to plugins.enabled in config.yaml")
            print("    2. Set shadow_jev_evaluator: true in config.yaml plugin config")
            print("    3. Monitor jev-turn-scores.jsonl for one more week")
        print(f"{sep}\n")

    return code


if __name__ == "__main__":
    sys.exit(main())
