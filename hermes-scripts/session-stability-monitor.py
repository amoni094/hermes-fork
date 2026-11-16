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
    <profile>/memory-facts/stability.db  (session_stability table)
    <profile>/cache/stability-alarm.json (if alarm triggered)

H-I6: stdlib only — no numpy (cron / sandbox python often has none).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# ── Paths (profile-aware) ──────────────────────────────────────────────────────
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

SESSIONS_DIR = _hermes_base / "sessions"
FORK_SESSIONS = _hermes_root / "sessions"
CIRCUIT_SCORES = _hermes_root / "cache" / "circuit-scores.json"
STABILITY_DB = _hermes_root / "memory-facts" / "stability.db"
ALARM_PATH = _hermes_root / "cache" / "stability-alarm.json"


def get_db() -> sqlite3.Connection:
    STABILITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STABILITY_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_stability (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_idx INTEGER NOT NULL,
            v_t      REAL NOT NULL,
            delta_v  REAL,
            alarm    INTEGER DEFAULT 0,
            ts       TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def load_session_turns(session_id: str | None, window: int) -> tuple[str, list[list[str]]]:
    """Load last `window` turns from the most recent (or specified) session.
    Returns (session_id, list_of_tool_name_lists) — one list per turn.
    """
    jsonl_files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")]
    )
    if not jsonl_files:
        return ("none", [])

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
        for line in target_file.read_text(encoding="utf-8").splitlines():
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
                    name = fn.get("name", "") if isinstance(fn, dict) else ""
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
        data = json.loads(CIRCUIT_SCORES.read_text(encoding="utf-8"))
        freq: Counter = Counter()
        for circuit in data.get("top_circuits", []):
            for tool in circuit.get("circuit", []):
                freq[tool] += circuit.get("frequency", 1)
        total = sum(freq.values()) or 1
        return {k: v / total for k, v in freq.items()}
    except Exception:
        return {}


def _l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def turn_to_vector(names: list[str], vocab: list[str]) -> list[float]:
    """TF bag-of-words embedding, L2-normalised. Stdlib only."""
    count = Counter(names)
    total = len(names) or 1
    vec = [count.get(term, 0) / total for term in vocab]
    nrm = _l2_norm(vec)
    if nrm > 0:
        return [x / nrm for x in vec]
    return vec


def kl_divergence(p: list[float], q: list[float]) -> float:
    """KL(p || q) with add-epsilon smoothing to handle zeros."""
    eps = 1e-10
    p2 = [max(x, eps) for x in p]
    q2 = [max(x, eps) for x in q]
    ps = sum(p2) or 1.0
    qs = sum(q2) or 1.0
    p2 = [x / ps for x in p2]
    q2 = [x / qs for x in q2]
    return float(sum(pi * math.log(pi / qi) for pi, qi in zip(p2, q2)))


def compute_potential(
    turns: list[list[str]], steady_state: dict[str, float]
) -> tuple[float, float, list[float]]:
    """Compute V_t given the last window of turns.
    Returns (v_t, mean_delta, deltas).
    """
    if not turns:
        return (0.0, 0.0, [])

    all_names: set[str] = set(steady_state.keys())
    for turn in turns:
        all_names.update(turn)
    vocab = sorted(all_names)

    vecs = [turn_to_vector(t, vocab) for t in turns]

    deltas: list[float] = []
    for i in range(1, len(vecs)):
        deltas.append(
            math.sqrt(sum((a - b) ** 2 for a, b in zip(vecs[i], vecs[i - 1])))
        )

    mean_delta = (sum(deltas) / len(deltas)) if deltas else 0.0

    if turns:
        all_tools = [t for turn in turns for t in turn]
        count = Counter(all_tools)
        total = len(all_tools) or 1
        current_probs = [count.get(t, 0) / total for t in vocab]
        steady_probs = [steady_state.get(t, 0.0) for t in vocab]
        kl = kl_divergence(current_probs, steady_probs) if sum(steady_probs) > 0 else 0.0
    else:
        kl = 0.0

    v_t = mean_delta + kl
    return (v_t, mean_delta, deltas)


def check_alarm(
    conn: sqlite3.Connection, session_id: str, v_t: float, threshold: float, dry_run: bool
) -> bool:
    """Check last 3 delta_v rows for monotone increase; write alarm if triggered."""
    rows = conn.execute(
        "SELECT v_t, delta_v FROM session_stability WHERE session_id=? ORDER BY id DESC LIMIT 5",
        (session_id,),
    ).fetchall()

    if len(rows) < 2:
        return False

    delta_vs = [r[1] for r in rows[:3] if r[1] is not None]
    increasing = all(d > 0 for d in delta_vs) and len(delta_vs) >= 3
    alarm = increasing or (v_t > threshold)

    if alarm and not dry_run:
        try:
            ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "alarm": True,
                "session_id": session_id,
                "v_t": round(v_t, 4),
                "recent_delta_vs": [round(d, 4) for d in delta_vs],
                "reason": "monotone_increase" if increasing else "threshold_breach",
                "threshold": threshold,
                "ts": datetime.now(UTC).isoformat(),
            }
            tmp = ALARM_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(ALARM_PATH))
            print(f"[stability] ALARM written to {ALARM_PATH}", file=sys.stderr)
        except Exception as e:
            print(f"[stability] alarm write failed: {e}", file=sys.stderr)

    return alarm


def main() -> None:
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

    v_t, mean_delta, _deltas = compute_potential(turns, steady_state)

    conn = get_db()
    last_row = conn.execute(
        "SELECT v_t FROM session_stability WHERE session_id=? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    delta_v = v_t - last_row[0] if last_row else None
    turn_idx = conn.execute(
        "SELECT COUNT(*) FROM session_stability WHERE session_id=?", (session_id,)
    ).fetchone()[0]

    alarm = check_alarm(conn, session_id, v_t, args.threshold, args.dry_run)

    if not args.dry_run:
        conn.execute(
            "INSERT INTO session_stability (session_id, turn_idx, v_t, delta_v, alarm, ts) VALUES (?,?,?,?,?,?)",
            (
                session_id,
                turn_idx,
                v_t,
                delta_v,
                int(alarm),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()

    conn.close()

    print(f"\n=== Session Stability Monitor — {datetime.now(UTC).isoformat()[:19]} ===")
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
