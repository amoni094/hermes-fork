#!/usr/bin/env python3
"""
session-stability-monitor.py

Monitors Hermes session stability using a discrete Lyapunov potential function.

Math basis (arXiv game_theory/stochastic_causal wave-3):
  A Lyapunov potential V(state) monotonically decreases under stable dynamics.
  Here, V_t = mean(||emb_curr - emb_prev||_2 over window) + KL(skill_probs || steady_state)
  where embeddings are TF-IDF bag-of-words over tool-call name sequences.
  If V_t fails to decrease for 3+ consecutive turns: session is drifting or looping.

Usage:
    python3 session-stability-monitor.py [--session ID] [--window N] [--threshold F] [--dry-run]

Output:
    ~/.hermes/memory-facts/stability.db  (session_stability table)
    ~/.hermes/cache/stability-alarm.json (if alarm triggered)
"""

import argparse
import json
import math
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
CIRCUIT_SCORES = HOME / ".hermes/cache/circuit-scores.json"
STABILITY_DB = HOME / ".hermes/memory-facts/stability.db"
ALARM_PATH = HOME / ".hermes/cache/stability-alarm.json"

# ── DB setup ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    STABILITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STABILITY_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_stability (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_idx INTEGER NOT NULL,
            v_t      REAL NOT NULL,
            delta_v  REAL,
            alarm    INTEGER DEFAULT 0,
            ts       TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


# ── Data loading ───────────────────────────────────────────────────────────────

def load_session_turns(session_id: str | None, window: int) -> tuple[str, list[list[str]]]:
    """Load last `window` turns from the most recent (or specified) session.
    Returns (session_id, list_of_tool_name_lists) — one list per turn.
    """
    jsonl_files = sorted(SESSIONS_DIR.glob("*.jsonl"))
    if not jsonl_files:
        return ("none", [])

    # If session_id specified, find that file; else use most recent
    target_file = None
    if session_id:
        for f in jsonl_files:
            if session_id in f.stem:
                target_file = f
                break
    if target_file is None:
        target_file = jsonl_files[-1]

    sid = target_file.stem
    turns: list[list[str]] = []
    try:
        for line in target_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            tool_calls = record.get("tool_calls") or []
            names = []
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    if name:
                        names.append(name.lower())
            if names:
                turns.append(names)
    except Exception as e:
        print(f"[stability] Error reading {target_file}: {e}", file=sys.stderr)

    return (sid, turns[-window:])


def load_steady_state() -> dict[str, float]:
    """Load steady-state tool frequency from circuit-scores.json."""
    if not CIRCUIT_SCORES.exists():
        return {}
    try:
        data = json.loads(CIRCUIT_SCORES.read_text())
        freq: Counter = Counter()
        for circuit in data.get("top_circuits", []):
            for tool in circuit.get("circuit", []):
                freq[tool] += circuit.get("frequency", 1)
        total = sum(freq.values()) or 1
        return {k: v / total for k, v in freq.items()}
    except Exception:
        return {}


# ── Embeddings and potential ───────────────────────────────────────────────────

def turn_to_vector(names: list[str], vocab: list[str]) -> np.ndarray:
    """TF-IDF bag-of-words embedding (TF only, normalised to unit L2)."""
    vec = np.zeros(len(vocab))
    count = Counter(names)
    total = len(names) or 1
    for i, term in enumerate(vocab):
        vec[i] = count.get(term, 0) / total
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """KL(p || q) with add-epsilon smoothing to handle zeros."""
    eps = 1e-10
    p = np.clip(p, eps, None)
    q = np.clip(q, eps, None)
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))


def compute_potential(turns: list[list[str]], steady_state: dict[str, float]) -> tuple[float, float, list[float]]:
    """Compute V_t and delta_V given the last window of turns.
    Returns (v_t, delta_v, deltas) where delta_v = v_t - v_prev (from embedding deltas only).
    """
    if not turns:
        return (0.0, 0.0, [])

    # Build vocab from all tool names seen + steady state
    all_names: set[str] = set(steady_state.keys())
    for turn in turns:
        all_names.update(turn)
    vocab = sorted(all_names)

    # Compute per-turn embeddings
    vecs = [turn_to_vector(t, vocab) for t in turns]

    # Embedding deltas (L2 norm of consecutive differences)
    deltas = []
    for i in range(1, len(vecs)):
        deltas.append(float(np.linalg.norm(vecs[i] - vecs[i - 1])))

    mean_delta = float(np.mean(deltas)) if deltas else 0.0

    # KL divergence of current skill distribution from steady state
    if turns:
        all_tools = [t for turn in turns for t in turn]
        count = Counter(all_tools)
        total = len(all_tools) or 1
        current_probs = np.array([count.get(t, 0) / total for t in vocab])
        steady_probs = np.array([steady_state.get(t, 0.0) for t in vocab])
        kl = kl_divergence(current_probs, steady_probs) if steady_probs.sum() > 0 else 0.0
    else:
        kl = 0.0

    v_t = mean_delta + kl
    # delta_v against last stored v (returned separately, caller stores)
    return (v_t, mean_delta, deltas)


# ── Alarm detection ────────────────────────────────────────────────────────────

def check_alarm(conn: sqlite3.Connection, session_id: str, v_t: float,
                threshold: float, dry_run: bool) -> bool:
    """Check last 3 delta_v rows for monotone increase; write alarm if triggered."""
    rows = conn.execute(
        "SELECT v_t, delta_v FROM session_stability WHERE session_id=? ORDER BY id DESC LIMIT 5",
        (session_id,)
    ).fetchall()

    if len(rows) < 2:
        return False

    # Get last 3 delta_v values (newest first)
    delta_vs = [r[1] for r in rows[:3] if r[1] is not None]
    increasing = all(d > 0 for d in delta_vs) and len(delta_vs) >= 3
    alarm = increasing or (v_t > threshold)

    if alarm and not dry_run:
        ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
        ALARM_PATH.write_text(json.dumps({
            "alarm": True,
            "session_id": session_id,
            "v_t": round(v_t, 4),
            "recent_delta_vs": [round(d, 4) for d in delta_vs],
            "reason": "monotone_increase" if increasing else "threshold_breach",
            "threshold": threshold,
            "ts": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
        print(f"[stability] ALARM written to {ALARM_PATH}", file=sys.stderr)

    return alarm


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Session Lyapunov stability monitor")
    parser.add_argument("--session", type=str, default=None, help="Session ID substring to target")
    parser.add_argument("--window", type=int, default=20, help="Turn window size (default 20)")
    parser.add_argument("--threshold", type=float, default=0.5, help="V_t alarm threshold (default 0.5)")
    parser.add_argument("--dry-run", action="store_true", help="Skip all writes")
    args = parser.parse_args()

    session_id, turns = load_session_turns(args.session, args.window)
    steady_state = load_steady_state()

    if not turns:
        print(f"[stability] No tool-call turns found for session={session_id}. No data to analyse.")
        return

    v_t, mean_delta, deltas = compute_potential(turns, steady_state)

    conn = get_db()
    # Compute delta_v against last stored v_t
    last_row = conn.execute(
        "SELECT v_t FROM session_stability WHERE session_id=? ORDER BY id DESC LIMIT 1",
        (session_id,)
    ).fetchone()
    delta_v = v_t - last_row[0] if last_row else None
    turn_idx = conn.execute(
        "SELECT COUNT(*) FROM session_stability WHERE session_id=?", (session_id,)
    ).fetchone()[0]

    alarm = check_alarm(conn, session_id, v_t, args.threshold, args.dry_run)

    if not args.dry_run:
        conn.execute(
            "INSERT INTO session_stability (session_id, turn_idx, v_t, delta_v, alarm, ts) VALUES (?,?,?,?,?,?)",
            (session_id, turn_idx, v_t, delta_v, int(alarm),
             datetime.now(timezone.utc).isoformat())
        )
        conn.commit()

    conn.close()

    print(f"\n=== Session Stability Monitor — {datetime.now(timezone.utc).isoformat()[:19]} ===")
    print(f"Session:    {session_id}")
    print(f"Turns used: {len(turns)} (window={args.window})")
    print(f"V_t:        {v_t:.4f}  (threshold={args.threshold})")
    print(f"delta_V:    {delta_v:.4f}" if delta_v is not None else "delta_V:    (first run)")
    print(f"Mean emb delta: {mean_delta:.4f}")
    print(f"ALARM:      {'YES' if alarm else 'no'}")
    if alarm:
        print(f"  -> Alarm written to {ALARM_PATH}")
    if args.dry_run:
        print("  (dry-run: no writes)")


if __name__ == "__main__":
    main()
