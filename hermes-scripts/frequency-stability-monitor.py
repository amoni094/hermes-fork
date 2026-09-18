#!/usr/bin/env python3
"""
frequency-stability-monitor.py

Monitors Hermes skill-routing stability using a discrete Lyapunov energy function.

Math basis (convex_analysis wave-3):
  Lyapunov stability criterion: a continuously decreasing energy function V(x) bounds
  system convergence to equilibrium. Here:
    V_t = ||routing_scores_t - routing_scores_{t-1}||_2 + H(retention_scores)
  where H is Shannon entropy over normalised memory retention scores.
  If delta_V oscillates (sign alternates 3+ times) or grows for 3+ steps: instability alarm.

Usage:
    python3 frequency-stability-monitor.py [--dry-run] [--window N]

Output:
    ~/.hermes/memory-facts/stability.db  (freq_stability table)
    ~/.hermes/cache/freq-stability-alarm.json (if alarm triggered)
"""

import argparse
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
CIRCUIT_SCORES = HOME / ".hermes/cache/circuit-scores.json"
LIFECYCLE_DB = HOME / ".hermes/memory-facts/lifecycle.db"
STABILITY_DB = HOME / ".hermes/memory-facts/stability.db"
ALARM_PATH = HOME / ".hermes/cache/freq-stability-alarm.json"


# ── DB setup ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    STABILITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STABILITY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS freq_stability (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_ts       TEXT NOT NULL,
            v_t          REAL NOT NULL,
            delta_v      REAL,
            routing_norm REAL NOT NULL,
            entropy      REAL NOT NULL,
            alarm        INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


# ── Data loading ───────────────────────────────────────────────────────────────

def load_routing_scores() -> np.ndarray:
    """Load circuit_score vector from circuit-scores.json."""
    if not CIRCUIT_SCORES.exists():
        return np.array([])
    try:
        data = json.loads(CIRCUIT_SCORES.read_text())
        scores = [c.get("circuit_score", 0.0) for c in data.get("top_circuits", [])]
        return np.array(scores[:50])  # cap at 50 for stability
    except Exception:
        return np.array([])


def load_retention_entropy() -> float:
    """Compute Shannon entropy over memory retention_score distribution from lifecycle.db."""
    if not LIFECYCLE_DB.exists():
        return 0.0
    try:
        conn = sqlite3.connect(str(LIFECYCLE_DB))
        rows = conn.execute(
            "SELECT retention_score FROM fact_lifecycle WHERE retention_score IS NOT NULL"
        ).fetchall()
        conn.close()
        if not rows:
            return 0.0
        scores = np.array([r[0] for r in rows], dtype=float)
        scores = np.clip(scores, 1e-10, None)
        scores = scores / scores.sum()
        return float(-np.sum(scores * np.log(scores)))
    except Exception as e:
        print(f"[freq-stability] lifecycle.db error: {e}", file=sys.stderr)
        return 0.0


def load_history(conn: sqlite3.Connection, window: int) -> list[dict]:
    """Load last `window` rows from freq_stability."""
    rows = conn.execute(
        "SELECT run_ts, v_t, delta_v, routing_norm, entropy, alarm FROM freq_stability "
        "ORDER BY id DESC LIMIT ?", (window,)
    ).fetchall()
    return [{"run_ts": r[0], "v_t": r[1], "delta_v": r[2],
             "routing_norm": r[3], "entropy": r[4], "alarm": r[5]}
            for r in reversed(rows)]


# ── Stability computation ──────────────────────────────────────────────────────

def compute_routing_norm(scores_t: np.ndarray, conn: sqlite3.Connection) -> float:
    """L2 norm of delta between current and previous routing scores."""
    last = conn.execute(
        "SELECT routing_norm, v_t FROM freq_stability ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if last is None or len(scores_t) == 0:
        return 0.0
    # Approximate: use current norm vs last recorded routing_norm
    current_norm = float(np.linalg.norm(scores_t))
    prev_norm = last[0]
    return abs(current_norm - prev_norm)


def detect_instability(history: list[dict], current_delta_v: float | None) -> tuple[bool, str]:
    """Detect oscillation or monotone growth in delta_v history."""
    if current_delta_v is None:
        return False, ""
    delta_vs = [h["delta_v"] for h in history if h["delta_v"] is not None]
    delta_vs.append(current_delta_v)

    if len(delta_vs) < 3:
        return False, ""

    recent = delta_vs[-3:]

    # Oscillation: alternating sign
    signs = [1 if d > 0 else -1 for d in recent]
    if signs[0] != signs[1] and signs[1] != signs[2]:
        return True, "oscillation"

    # Monotone growth: all positive
    if all(d > 0 for d in recent):
        return True, "monotone_growth"

    return False, ""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Frequency (Lyapunov) stability monitor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--window", type=int, default=5, help="History rows to check (default 5)")
    args = parser.parse_args()

    scores_t = load_routing_scores()
    entropy = load_retention_entropy()

    conn = get_db()
    history = load_history(conn, args.window)

    routing_norm = compute_routing_norm(scores_t, conn)
    v_t = routing_norm + entropy

    # delta_v from previous run
    last_v = history[-1]["v_t"] if history else None
    delta_v = v_t - last_v if last_v is not None else None

    alarm, alarm_type = detect_instability(history, delta_v)

    if not args.dry_run:
        conn.execute(
            "INSERT INTO freq_stability (run_ts, v_t, delta_v, routing_norm, entropy, alarm) "
            "VALUES (?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), v_t, delta_v, routing_norm, entropy, int(alarm))
        )
        conn.commit()

        if alarm:
            ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
            ALARM_PATH.write_text(json.dumps({
                "alarm": True,
                "alarm_type": alarm_type,
                "v_t": round(v_t, 4),
                "delta_v": round(delta_v, 4) if delta_v is not None else None,
                "routing_norm": round(routing_norm, 4),
                "entropy": round(entropy, 4),
                "ts": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            print(f"[freq-stability] ALARM ({alarm_type}) written to {ALARM_PATH}", file=sys.stderr)

    conn.close()

    print(f"\n=== Frequency Stability Monitor — {datetime.now(timezone.utc).isoformat()[:19]} ===")
    print(f"V_t:          {v_t:.4f}")
    print(f"delta_V:      {delta_v:.4f}" if delta_v is not None else "delta_V:      (first run)")
    print(f"routing_norm: {routing_norm:.4f}")
    print(f"entropy:      {entropy:.4f}")
    print(f"ALARM:        {'YES (' + alarm_type + ')' if alarm else 'no'}")
    if args.dry_run:
        print("  (dry-run: no writes)")


if __name__ == "__main__":
    main()
