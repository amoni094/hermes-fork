#!/usr/bin/env python3
"""
uncertainty-calibration-monitor.py

Monitors Hermes skill calibration: are high-confidence tool calls actually
more reliable than low-confidence ones?

Math basis (generalization_theory / robust_stats wave-3):
  Calibration as a monotone operator: uncertainty estimates should form a
  consistent ordering with prediction error. Empirical calibration error =
  L2 distance between sorted confidence quantiles and sorted error quantiles
  (a discrete transport metric). A well-calibrated skill has near-zero score;
  an overconfident skill has high score.

Usage:
    python3 uncertainty-calibration-monitor.py [--ingest] [--report] [--alarm]
    [--dry-run] [--threshold F]

    Default (no flags): runs ingest → report → alarm check.

Output:
    ~/.hermes/memory-facts/calibration.db  (skill_calibration table)
    ~/.hermes/cache/calibration-alarm.json (if alarm triggered)
"""

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
CALIBRATION_DB = HOME / ".hermes/memory-facts/calibration.db"
ALARM_PATH = HOME / ".hermes/cache/calibration-alarm.json"

# ── DB setup ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    CALIBRATION_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CALIBRATION_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_calibration (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id         TEXT NOT NULL,
            input_hash       TEXT NOT NULL,
            model_confidence REAL NOT NULL,
            actual_error     REAL NOT NULL,
            ts               TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ── Ingestion ──────────────────────────────────────────────────────────────────

def ingest(conn: sqlite3.Connection, dry_run: bool, max_files: int = 50):
    """Read recent session JSONL files and populate skill_calibration."""
    files = sorted(SESSIONS_DIR.glob("*.jsonl"))[-max_files:]
    inserted = 0
    existing_hashes = {r[0] for r in conn.execute("SELECT input_hash FROM skill_calibration").fetchall()}

    for f in files:
        try:
            lines = [l.strip() for l in f.read_text().splitlines() if l.strip()]
        except Exception:
            continue

        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        for i, record in enumerate(records):
            if record.get("role") != "assistant":
                continue
            tool_calls = record.get("tool_calls") or []
            if not tool_calls:
                continue

            # Extract skill_id (first tool name)
            skill_id = None
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    if name:
                        skill_id = name.lower()
                        break
            if not skill_id:
                continue

            # Model confidence from finish_reason
            finish = record.get("finish_reason", "")
            if finish == "end_turn":
                confidence = 0.9
            elif finish in ("error", "max_tokens"):
                confidence = 0.3
            else:
                confidence = 0.6  # null/unknown

            # Actual error: check next record for error indicators
            actual_error = 0.0
            if i + 1 < len(records):
                next_rec = records[i + 1]
                content = str(next_rec.get("content", ""))
                if "error" in content.lower() or "Error" in content or "exception" in content.lower():
                    actual_error = 1.0

            # Dedup by input_hash
            input_hash = hashlib.sha256(json.dumps(tool_calls, sort_keys=True).encode()).hexdigest()[:16]
            if input_hash in existing_hashes:
                continue

            existing_hashes.add(input_hash)
            if not dry_run:
                conn.execute(
                    "INSERT INTO skill_calibration (skill_id, input_hash, model_confidence, actual_error, ts) VALUES (?,?,?,?,?)",
                    (skill_id, input_hash, confidence, actual_error, datetime.now(timezone.utc).isoformat())
                )
                inserted += 1

    if not dry_run:
        conn.commit()
    print(f"[calibration] Ingested {inserted} new records from {len(files)} session files")


# ── Calibration scoring ────────────────────────────────────────────────────────

def calibration_error(confidences: np.ndarray, errors: np.ndarray) -> float:
    """L2 distance between argsort(confidence)/N and argsort(error)/N.

    This measures whether confidence rank-ordering matches error rank-ordering.
    A perfectly calibrated skill has score = 0.
    """
    n = len(confidences)
    if n < 2:
        return 0.0
    conf_rank = np.argsort(confidences).argsort() / n
    err_rank = np.argsort(errors).argsort() / n
    return float(np.linalg.norm(conf_rank - err_rank))


def report(conn: sqlite3.Connection, threshold: float) -> list[dict]:
    """Compute and print per-skill calibration errors. Returns flagged skills."""
    skills = [r[0] for r in conn.execute("SELECT DISTINCT skill_id FROM skill_calibration").fetchall()]
    flagged = []
    rows_printed = 0

    print(f"\n{'Skill':<35} {'N':>4} {'Cal.Err':>8} {'AvgConf':>8} {'AvgErr':>8} {'Flag'}")
    print("-" * 75)

    for skill in sorted(skills):
        rows = conn.execute(
            "SELECT model_confidence, actual_error FROM skill_calibration WHERE skill_id=?", (skill,)
        ).fetchall()
        if len(rows) < 5:
            continue
        confs = np.array([r[0] for r in rows])
        errs = np.array([r[1] for r in rows])
        cal_err = calibration_error(confs, errs)
        flag = "OVERCONFIDENT" if cal_err > threshold else ""
        print(f"{skill:<35} {len(rows):>4} {cal_err:>8.3f} {confs.mean():>8.3f} {errs.mean():>8.3f} {flag}")
        rows_printed += 1
        if flag:
            flagged.append({"skill_id": skill, "calibration_error": round(cal_err, 4),
                           "avg_confidence": round(float(confs.mean()), 3),
                           "avg_error": round(float(errs.mean()), 3), "n": len(rows)})

    if rows_printed == 0:
        print("  No skills with >= 5 records yet. Run --ingest first.")

    return flagged


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Skill uncertainty calibration monitor")
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--alarm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.3)
    args = parser.parse_args()

    # Default: all three
    run_all = not (args.ingest or args.report or args.alarm)

    conn = get_db()

    if args.ingest or run_all:
        ingest(conn, args.dry_run)

    flagged = []
    if args.report or run_all:
        flagged = report(conn, args.threshold)

    if args.alarm or run_all:
        if flagged and not args.dry_run:
            ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
            ALARM_PATH.write_text(json.dumps({
                "alarm": True,
                "flagged_skills": flagged,
                "threshold": args.threshold,
                "ts": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            print(f"\nALARM: yes — {len(flagged)} overconfident skill(s) — written to {ALARM_PATH}")
        elif not flagged:
            print("\nALARM: no — no overconfident skills detected.")

    conn.close()
    if args.dry_run:
        print("  (dry-run: no writes)")


if __name__ == "__main__":
    main()
