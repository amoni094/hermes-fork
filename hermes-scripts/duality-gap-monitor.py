#!/usr/bin/env python3
"""
duality-gap-monitor.py

Monitors Hermes skill-routing optimality via a duality gap certificate.

Math basis (convex_analysis wave-3):
  In convex decision problems, the duality gap = dual_bound - primal_objective >= 0.
  A gap of 0 certifies optimality. Large relative gap means the current routing
  leaves significant improvement on the table and should be re-optimised.

  Primal: sum of achieved circuit_score for top-K circuits (the routing we got).
  Dual:   relaxation upper bound — assign each tool the max circuit_score it appears
          in, then sum over unique tools (ignores sequencing constraints = valid UB).
  Gap = dual - primal. Relative gap = gap / dual.

Usage:
    python3 duality-gap-monitor.py [--dry-run] [--threshold F] [--top-k N]

Output:
    ~/.hermes/memory-facts/stability.db  (duality_gaps table)
    ~/.hermes/cache/duality-alarm.json   (if alarm triggered)
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
CIRCUIT_SCORES = HOME / ".hermes/cache/circuit-scores.json"
STABILITY_DB = HOME / ".hermes/memory-facts/stability.db"
ALARM_PATH = HOME / ".hermes/cache/duality-alarm.json"


# ── DB setup ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    STABILITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STABILITY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS duality_gaps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_ts       TEXT NOT NULL,
            primal       REAL NOT NULL,
            dual         REAL NOT NULL,
            gap          REAL NOT NULL,
            relative_gap REAL NOT NULL,
            alarm        INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


# ── Gap computation ────────────────────────────────────────────────────────────

def compute_gap(circuits: list[dict], top_k: int) -> tuple[float, float, float, float]:
    """Compute primal objective, dual bound, gap and relative gap.

    Returns (primal, dual, gap, relative_gap).
    """
    if not circuits:
        return (0.0, 0.0, 0.0, 0.0)

    top = circuits[:top_k]

    # Primal: sum of circuit_score for top-K circuits
    primal = sum(c.get("circuit_score", 0.0) for c in top)

    # Dual: relaxation UB — each tool independently contributes its best circuit_score.
    # For a valid upper bound, we must count the contribution per circuit:
    # dual = sum over top-K circuits of max(circuit_score) for each tool position.
    # Simpler valid UB: for each circuit in top-K, replace it with its best single-tool score.
    # Since circuit_score <= sum of individual tool max scores, dual >= primal always.
    tool_max: dict[str, float] = {}
    for c in circuits:  # use all circuits to build tool score table
        score = c.get("circuit_score", 0.0)
        for tool in c.get("circuit", []):
            tool_max[tool] = max(tool_max.get(tool, 0.0), score)

    # Dual for top-K circuits: replace each circuit's score with sum of its tools' max scores
    dual = 0.0
    for c in top:
        circuit_tools = c.get("circuit", [])
        dual += sum(tool_max.get(t, 0.0) for t in circuit_tools)

    gap = max(0.0, dual - primal)
    relative_gap = gap / dual if dual > 0 else 0.0

    return (primal, dual, gap, relative_gap)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Duality gap monitor for skill routing")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.2,
                        help="Relative gap alarm threshold (default 0.2 = 20%%)")
    parser.add_argument("--top-k", type=int, default=10, help="Top-K circuits (default 10)")
    args = parser.parse_args()

    if not CIRCUIT_SCORES.exists():
        print(f"[duality-gap] {CIRCUIT_SCORES} not found. Run circuit-trajectory-scorer.py first.")
        sys.exit(1)

    data = json.loads(CIRCUIT_SCORES.read_text())
    circuits = data.get("top_circuits", [])

    if not circuits:
        print("[duality-gap] No circuits in circuit-scores.json. Nothing to analyse.")
        return

    primal, dual, gap, relative_gap = compute_gap(circuits, args.top_k)
    alarm = relative_gap > args.threshold

    conn = get_db()
    if not args.dry_run:
        conn.execute(
            "INSERT INTO duality_gaps (run_ts, primal, dual, gap, relative_gap, alarm) VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), primal, dual, gap, relative_gap, int(alarm))
        )
        conn.commit()

        if alarm:
            ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
            ALARM_PATH.write_text(json.dumps({
                "alarm": True,
                "primal": round(primal, 4),
                "dual": round(dual, 4),
                "gap": round(gap, 4),
                "relative_gap": round(relative_gap, 4),
                "threshold": args.threshold,
                "recommendation": "Re-run circuit-trajectory-scorer.py and review top-K routing paths.",
                "ts": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            print(f"[duality-gap] ALARM written to {ALARM_PATH}", file=sys.stderr)

    conn.close()

    print(f"\n=== Duality Gap Monitor — {datetime.now(timezone.utc).isoformat()[:19]} ===")
    print(f"Circuits analysed: {len(circuits)} (top-K={args.top_k})")
    print(f"Primal objective:  {primal:.4f}")
    print(f"Dual bound (UB):   {dual:.4f}")
    print(f"Gap:               {gap:.4f}")
    print(f"Relative gap:      {relative_gap:.4f}  (threshold={args.threshold})")
    print(f"ALARM:             {'YES — routing is suboptimal, consider re-optimisation' if alarm else 'no'}")
    if args.dry_run:
        print("  (dry-run: no writes)")


if __name__ == "__main__":
    main()
