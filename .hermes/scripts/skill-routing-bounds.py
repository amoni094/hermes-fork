#!/usr/bin/env python3
"""skill-routing-bounds.py — ROY-9: tail-bounds for skill routing stability.

Implements Royden-Fitzpatrick-inspired tail-probability diagnostics for the skill
routing subsystem.

Subcommands
-----------
  tail-bounds   Reads skill invocation counts from skill-state sessions or
                lifecycle.db (if present), computes empirical probabilities,
                checks the Borel-Cantelli heuristic for anomalous tails, and
                computes Chebyshev bounds on routing score deviations.

Usage
-----
  python3 skill-routing-bounds.py tail-bounds [--n-window N] [--anomaly-z Z]
                                               [--chebyshev-t T]

Options
-------
  --n-window N     Number of most-recent routing steps to analyse (default: 50)
  --anomaly-z Z    Z-score threshold above which a skill is flagged as anomalous
                   (default: 2.0)
  --chebyshev-t T  Deviation threshold t for Chebyshev P(|X-mu| >= t) (default: 0.1)

Output
------
JSON to stdout with:
  empirical_probs        per-skill empirical p_k = count_k / total
  anomalous_skills       skills with |p_k - mean| / std >= Z
  borel_cantelli         sum of tail p_k for anomalous skills, convergence judgement
  chebyshev_bound        sigma^2 / t^2 upper bound on routing score deviation probability
  routing_score_stats    mean, variance, std of empirical p distribution

Data sources (in order of preference)
--------------------------------------
1. lifecycle.db (SQLite, table 'skill_lifecycle') — if present and readable
2. skill-state JSON files in ~/.hermes/cache/skill-state/ — skill_name field
3. loop-pid session history — action field as proxy (fallback to empty)

Reference: Royden & Fitzpatrick, Real Analysis 4e §7 (Borel-Cantelli lemma) and
           Chebyshev's inequality (§6).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from collections import Counter
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
# Skill-state and PID files live in the *base* ~/.hermes hierarchy regardless of
# which profile is active.  Fall back to the base path when the profile path is absent.
_HERMES_BASE = Path.home() / ".hermes"


def _resolve_cache_path(rel: str) -> Path:
    """Return HERMES_HOME/rel when it exists, else fall back to ~/.hermes/rel."""
    p = HERMES_HOME / rel
    if p.exists():
        return p
    return _HERMES_BASE / rel


SKILL_STATE_DIR = _resolve_cache_path("cache/skill-state")
LIFECYCLE_DB = _resolve_cache_path("cache/lifecycle.db")
LOOP_PID_STATE = _resolve_cache_path("cache/loop-pid-state.json")
LOOP_PID_SESSIONS = _resolve_cache_path("cache/loop-pid-sessions")


# ---------------------------------------------------------------------------
# Data source readers
# ---------------------------------------------------------------------------

def _read_lifecycle_db(n_window: int) -> list[str] | None:
    """Read last n_window skill invocations from lifecycle.db if present.

    Table schema heuristic: tries common column names (skill, skill_name,
    name) and a 'ts' or 'created_at' for ordering.
    """
    if not LIFECYCLE_DB.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{LIFECYCLE_DB}?mode=ro", uri=True)
        try:
            # Probe table names
            tables = [
                r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
        except sqlite3.Error:
            conn.close()
            return None

        target_table = None
        for t in tables:
            if "skill" in t.lower() or "lifecycle" in t.lower():
                target_table = t
                break
        if target_table is None and tables:
            target_table = tables[0]
        if target_table is None:
            conn.close()
            return None

        # Probe column names
        try:
            cols = [
                r[1] for r in conn.execute(
                    f"PRAGMA table_info({target_table})"
                ).fetchall()
            ]
        except sqlite3.Error:
            conn.close()
            return None

        skill_col = next(
            (c for c in cols if c.lower() in ("skill_name", "skill", "name")), None
        )
        if skill_col is None:
            conn.close()
            return None

        ts_col = next(
            (c for c in cols if c.lower() in ("ts", "created_at", "timestamp", "updated_at")),
            None,
        )
        order_clause = f"ORDER BY {ts_col} DESC" if ts_col else ""
        limit_clause = f"LIMIT {int(n_window)}"
        try:
            rows = conn.execute(
                f"SELECT {skill_col} FROM {target_table} {order_clause} {limit_clause}"
            ).fetchall()
        except sqlite3.Error:
            conn.close()
            return None
        conn.close()
        return [str(r[0]) for r in rows if r[0] is not None]
    except (OSError, sqlite3.Error, ValueError):
        return None


def _read_skill_state_files(n_window: int) -> list[str]:
    """Collect skill_name from skill-state JSON files, newest-first up to n_window."""
    if not SKILL_STATE_DIR.is_dir():
        return []
    items: list[tuple[float, str]] = []
    for p in SKILL_STATE_DIR.glob("*.json"):
        try:
            doc = json.loads(p.read_text())
            name = doc.get("skill_name") or doc.get("skill") or doc.get("name")
            if not name:
                continue
            # Use mtime as ordering proxy
            mtime = p.stat().st_mtime
            items.append((mtime, str(name)))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    items.sort(key=lambda x: -x[0])  # newest first
    return [name for _, name in items[:n_window]]


def _read_pid_history(n_window: int) -> list[str]:
    """Fallback: read action strings from loop-pid action_log as a proxy for skill invocations."""
    invocations: list[tuple[str, str]] = []  # (ts, action)
    files: list[Path] = []
    if LOOP_PID_STATE.exists():
        files.append(LOOP_PID_STATE)
    if LOOP_PID_SESSIONS.is_dir():
        files.extend(sorted(LOOP_PID_SESSIONS.glob("*.json")))
    for p in files:
        try:
            data = json.loads(p.read_text())
            log = data.get("action_log") or []
            for entry in log:
                if isinstance(entry, dict):
                    ts = entry.get("ts", "")
                    action = entry.get("action", "UNKNOWN")
                    invocations.append((ts, f"pid_action:{action}"))
        except (OSError, json.JSONDecodeError):
            continue
    invocations.sort(key=lambda x: x[0], reverse=True)
    return [name for _, name in invocations[:n_window]]


def _collect_invocations(n_window: int) -> tuple[list[str], str]:
    """Return (invocation_list, source_description)."""
    result = _read_lifecycle_db(n_window)
    if result is not None:
        return result, "lifecycle.db"
    result = _read_skill_state_files(n_window)
    if result:
        return result, "skill-state-files"
    result = _read_pid_history(n_window)
    if result:
        return result, "loop-pid-action-log"
    return [], "no_data"


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mu = _mean(xs)
    return sum((x - mu) ** 2 for x in xs) / len(xs)  # population variance


def _chebyshev_bound(sigma2: float, t: float) -> float | None:
    """P(|X - mu| >= t) <= sigma^2 / t^2.  Returns None when t == 0."""
    if t <= 0.0:
        return None
    return sigma2 / (t ** 2)


def _borel_cantelli_sum(probs: list[float]) -> float:
    """Sum of tail probabilities (Borel-Cantelli Series: sum p_k for anomalous k)."""
    return sum(probs)


def _converging(tail_probs: list[float], n_recent: int = 10) -> bool:
    """Heuristic convergence: recent partial sum < half of total sum, OR total < 1.0."""
    total = _borel_cantelli_sum(tail_probs)
    if total < 1.0:
        return True
    recent = sum(tail_probs[-n_recent:]) if len(tail_probs) > n_recent else total
    return recent < 0.5 * total


# ---------------------------------------------------------------------------
# Main subcommand
# ---------------------------------------------------------------------------

def cmd_tail_bounds(args: argparse.Namespace) -> None:
    """ROY-9 implementation."""
    n_window = int(args.n_window)
    anomaly_z = float(args.anomaly_z)
    chebyshev_t = float(args.chebyshev_t)

    invocations, source = _collect_invocations(n_window)
    total = len(invocations)

    if total == 0:
        print(json.dumps({
            "error": "no_invocation_data",
            "source_tried": ["lifecycle.db", "skill-state-files", "loop-pid-action-log"],
            "note": (
                "No skill invocation history found. Populate by running skills "
                "or seeding lifecycle.db / skill-state files."
            ),
        }, indent=2))
        return

    counts: Counter[str] = Counter(invocations)
    n_skills = len(counts)

    # Empirical probabilities
    empirical_probs: dict[str, float] = {
        skill: count / total for skill, count in counts.most_common()
    }

    # Routing score distribution statistics
    probs_list = list(empirical_probs.values())
    mu = _mean(probs_list)
    sigma2 = _variance(probs_list)
    sigma = math.sqrt(sigma2)

    # Anomaly detection: skills where |p_k - mu| >= anomaly_z * sigma
    anomalous: list[dict] = []
    for skill, p_k in empirical_probs.items():
        if sigma > 0:
            z = abs(p_k - mu) / sigma
        else:
            z = 0.0
        if z >= anomaly_z:
            anomalous.append({
                "skill": skill,
                "p_k": round(p_k, 6),
                "z_score": round(z, 4),
                "count": counts[skill],
            })
    anomalous.sort(key=lambda x: -x["z_score"])

    # Borel-Cantelli: sum of tail probabilities for anomalous skills
    tail_probs = [a["p_k"] for a in anomalous]
    bc_sum = _borel_cantelli_sum(tail_probs)
    bc_converging = _converging(tail_probs)

    # Chebyshev bound on routing score deviations
    cb = _chebyshev_bound(sigma2, chebyshev_t)
    cb_str = f"P(|p_k - mu| >= {chebyshev_t}) <= {round(cb, 6)}" if cb is not None else "N/A (t=0)"

    # Top-k empirical probabilities for display
    top_skills = [
        {"skill": sk, "p_k": round(p, 6), "count": counts[sk]}
        for sk, p in list(empirical_probs.items())[:20]
    ]

    out = {
        "source": source,
        "total_invocations": total,
        "n_skills": n_skills,
        "n_window": n_window,
        "routing_score_stats": {
            "mean_p": round(mu, 6),
            "variance_p": round(sigma2, 6),
            "std_p": round(sigma, 6),
        },
        "empirical_probs": top_skills,
        "anomaly_detection": {
            "z_threshold": anomaly_z,
            "n_anomalous": len(anomalous),
            "anomalous_skills": anomalous,
        },
        "borel_cantelli": {
            "sum_tail_probs": round(bc_sum, 6),
            "converging": bc_converging,
            "interpretation": (
                "sum(p_k for anomalous k) < 1 — tail converges, routing appears stable"
                if bc_converging else
                "sum(p_k for anomalous k) >= 1 — tail may diverge, routing concentration risk"
            ),
            "note": (
                "Borel-Cantelli heuristic (Royden & Fitzpatrick §7.3): "
                "if sum p_k < inf then tail events occur finitely often almost surely. "
                "Convergence is assessed as sum < 1.0 OR recent partial sum < 50% of total."
            ),
        },
        "chebyshev_bound": {
            "t": chebyshev_t,
            "sigma2": round(sigma2, 6),
            "upper_bound_probability": round(cb, 6) if cb is not None else None,
            "formula": cb_str,
            "note": (
                "Chebyshev's inequality (Royden & Fitzpatrick §6.4): "
                "P(|X - mu| >= t) <= sigma^2 / t^2. "
                "Applied to the empirical routing probability distribution."
            ),
        },
        "interpretation": (
            "Routing appears statistically stable: tail probabilities converge "
            "and Chebyshev bound is tight."
            if (bc_converging and cb is not None and cb < 0.5)
            else "Routing shows concentration or heavy-tail anomalies — review anomalous skills."
        ),
    }
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ROY-9: tail-bounds for skill routing stability (Royden-Fitzpatrick)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    tb = sub.add_parser(
        "tail-bounds",
        help="Compute tail-probability diagnostics for skill routing (ROY-9)",
    )
    tb.add_argument(
        "--n-window", type=int, default=50, dest="n_window",
        help="Number of most-recent skill invocations to analyse (default: 50)",
    )
    tb.add_argument(
        "--anomaly-z", type=float, default=2.0, dest="anomaly_z",
        help="Z-score threshold for flagging anomalous skills (default: 2.0)",
    )
    tb.add_argument(
        "--chebyshev-t", type=float, default=0.1, dest="chebyshev_t",
        help="Deviation threshold t for Chebyshev bound (default: 0.1)",
    )
    tb.set_defaults(func=cmd_tail_bounds)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
