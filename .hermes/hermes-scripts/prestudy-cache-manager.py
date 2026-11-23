#!/usr/bin/env python3
"""
prestudy-cache-manager.py

Scans ~/.hermes/cache/prestudy/ and deletes files older than --ttl-hours (default 24).
Pruned files are logged to ~/.hermes/logs/prestudy-prune.jsonl with ts, filename, age_hours.

Usage:
    python3 prestudy-cache-manager.py [--dry-run] [--ttl-hours N]
"""

import os
import json
import time
import argparse
import math
import statistics
from pathlib import Path
from datetime import datetime, timezone


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prune stale files from the Hermes prestudy cache."
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        default=None,
        help="Optional subcommand: 'renewal-stats' to read prune log",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would be deleted without actually deleting them.",
    )
    parser.add_argument(
        "--ttl-hours",
        type=float,
        default=24.0,
        metavar="N",
        help="Delete files older than N hours (default: 24).",
    )
    return parser.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


PRUNE_LOG_PATH = Path.home() / ".hermes" / "logs" / "prestudy-prune-log.jsonl"


def _log_prune_event(file: str, ttl_hours: float, age_hours: float) -> None:
    """GS-7: Append a prune event to prestudy-prune-log.jsonl."""
    record = {
        "timestamp": now_utc_iso(),
        "file": file,
        "ttl_hours": round(ttl_hours, 4),
        "age_hours": round(age_hours, 4),
    }
    try:
        PRUNE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PRUNE_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as exc:
        print(f"[WARN] Could not write prune log: {exc}")


def cmd_renewal_stats() -> None:
    """GS-7: Read prestudy-prune-log.jsonl and compute renewal statistics."""
    if not PRUNE_LOG_PATH.exists():
        print(json.dumps({
            "error": "Prune log not found",
            "path": str(PRUNE_LOG_PATH),
            "renewal_stats": None,
        }, indent=2))
        return

    records = []
    try:
        for line in PRUNE_LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if isinstance(rec, dict):
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    except OSError as exc:
        print(json.dumps({"error": str(exc)}))
        return

    if not records:
        print(json.dumps({
            "n_events": 0,
            "renewal_stats": None,
            "note": "No prune events recorded yet.",
        }, indent=2))
        return

    # Inter-renewal times: consecutive events for the same file
    from collections import defaultdict
    file_times: dict = defaultdict(list)
    for rec in records:
        ts_str = rec.get("timestamp", "")
        fname = rec.get("file", "")
        if not ts_str or not fname:
            continue
        try:
            # Parse ISO timestamp
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").timestamp()
            file_times[fname].append(ts)
        except ValueError:
            continue

    inter_renewal_hours: list[float] = []
    for fname, times in file_times.items():
        if len(times) < 2:
            continue
        sorted_ts = sorted(times)
        for a, b in zip(sorted_ts, sorted_ts[1:]):
            inter_renewal_hours.append((b - a) / 3600.0)

    ttl_vals = [rec["ttl_hours"] for rec in records if isinstance(rec.get("ttl_hours"), (int, float))]
    age_vals = [rec["age_hours"] for rec in records if isinstance(rec.get("age_hours"), (int, float))]

    mean_inter = statistics.mean(inter_renewal_hours) if inter_renewal_hours else None
    mean_age = statistics.mean(age_vals) if age_vals else None
    mean_ttl = statistics.mean(ttl_vals) if ttl_vals else None

    # Recommended TTL: mean_age * 0.9 to catch files just before they expire naturally
    if mean_age is not None and mean_age > 0:
        recommended_ttl = round(mean_age * 0.9, 1)
    elif mean_ttl is not None:
        recommended_ttl = round(mean_ttl, 1)
    else:
        recommended_ttl = None

    print(json.dumps({
        "n_events": len(records),
        "n_files_tracked": len(file_times),
        "n_files_with_renewals": sum(1 for times in file_times.values() if len(times) >= 2),
        "mean_inter_renewal_hours": round(mean_inter, 2) if mean_inter is not None else None,
        "estimated_cache_lifetime_hours": round(mean_age, 2) if mean_age is not None else None,
        "mean_ttl_hours_used": round(mean_ttl, 2) if mean_ttl is not None else None,
        "recommended_ttl_adjustment_hours": recommended_ttl,
        "note": (
            "inter_renewal = average time between successive prune events for the same file. "
            "recommended_ttl = 0.9 * mean_age_at_prune (catches files before natural expiry)."
        ),
        "log_path": str(PRUNE_LOG_PATH),
    }, indent=2))


def main():
    args = parse_args()

    # GS-7: renewal-stats subcommand
    if args.subcommand == "renewal-stats":
        cmd_renewal_stats()
        return

    cache_dir = Path.home() / ".hermes" / "cache" / "prestudy"
    log_path = Path.home() / ".hermes" / "logs" / "prestudy-prune.jsonl"

    # Create cache dir if missing
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    ttl_seconds = args.ttl_hours * 3600.0
    now_ts = time.time()

    pruned = []

    for entry in cache_dir.iterdir():
        if not entry.is_file():
            continue

        try:
            mtime = entry.stat().st_mtime
        except OSError as exc:
            print(f"[WARN] Cannot stat {entry.name}: {exc}")
            continue

        age_seconds = now_ts - mtime
        age_hours = age_seconds / 3600.0

        if age_seconds >= ttl_seconds:
            record = {
                "ts": now_utc_iso(),
                "filename": entry.name,
                "age_hours": round(age_hours, 4),
            }
            if args.dry_run:
                print(f"[DRY-RUN] Would delete: {entry.name} (age={age_hours:.2f}h)")
            else:
                try:
                    os.remove(entry)
                    pruned.append(record)
                    print(f"[DELETED] {entry.name} (age={age_hours:.2f}h)")
                    # GS-7: log TTL expiry to prestudy-prune-log.jsonl
                    _log_prune_event(entry.name, args.ttl_hours, age_hours)
                except OSError as exc:
                    print(f"[ERROR] Failed to delete {entry.name}: {exc}")
            if args.dry_run:
                pruned.append(record)

    if pruned and not args.dry_run:
        with log_path.open("a") as f:
            for record in pruned:
                f.write(json.dumps(record) + "\n")
        print(f"Logged {len(pruned)} pruned file(s) to {log_path}")
    elif pruned and args.dry_run:
        print(f"[DRY-RUN] {len(pruned)} file(s) would be pruned (nothing written to log).")
    else:
        print("No files exceeded the TTL. Nothing pruned.")


if __name__ == "__main__":
    main()
