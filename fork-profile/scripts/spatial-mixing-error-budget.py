#!/usr/bin/python3
"""
spatial-mixing-error-budget.py

Allows skill routing to trade approximation error for latency in spatial
or graph-structured decision contexts — allocates error budget across
skill invocations using mixing time bounds.

Math basis: Gibbs sampler mixing time + second-order perturbation bounds
  For a Markov chain with spectral gap δ, the ε-mixing time is:
    t_mix(ε) ≤ (1/δ) · ln(1/ε · 1/π_min)
  Under perturbation of transition matrix P → P + ΔP:
    ||π' - π||_TV ≤ ||ΔP||_∞ / (2δ)   (first-order bound)
  
  Operationally: model skill routing as a Markov chain over skill states.
  Spectral gap δ estimated from skill transition frequency matrix.
  Alarm when mixing time > LATENCY_BUDGET or perturbation bound > ERROR_BUDGET.

Usage:
  python3 spatial-mixing-error-budget.py          # scan recent sessions
  python3 spatial-mixing-error-budget.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "spatial-mixing-report.json"

LATENCY_BUDGET = 20    # alarm if mixing time > 20 transitions
ERROR_BUDGET   = 0.50  # alarm if perturbation bound > 0.50
PI_MIN_FLOOR   = 0.01  # minimum stationary probability (regulariser)
EPSILON        = 0.05  # target mixing accuracy


def _extract_tool_sequence(session_path: Path) -> list[str]:
    """Extract ordered tool call names from session."""
    tools = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools.append(block.get("name", "unknown"))
        except Exception:
            pass
    return tools


def _transition_matrix(seq: list[str]) -> tuple[np.ndarray, list[str]]:
    """Build row-stochastic transition matrix from tool sequence."""
    tools  = sorted(set(seq))
    idx    = {t: i for i, t in enumerate(tools)}
    n      = len(tools)
    counts = np.zeros((n, n)) + 1e-6  # Laplace smoothing

    for a, b in zip(seq[:-1], seq[1:]):
        counts[idx[a], idx[b]] += 1

    P = counts / counts.sum(axis=1, keepdims=True)
    return P, tools


def _spectral_gap(P: np.ndarray) -> float:
    """Estimate spectral gap from transition matrix eigenvalues."""
    try:
        eigs = np.linalg.eigvals(P)
        eigs_real = sorted(abs(eigs), reverse=True)  # use modulus, not real part (handles complex eigs)
        if len(eigs_real) < 2:
            return 1.0
        return float(max(1e-6, 1.0 - eigs_real[1]))
    except Exception:
        return 0.1


def analyse_session(session_path: Path) -> dict:
    seq = _extract_tool_sequence(session_path)
    if len(seq) < 4:
        return {
            "session": session_path.stem,
            "note":    f"only {len(seq)} tool calls",
            "alarm":   False,
        }

    P, tools = _transition_matrix(seq)
    delta    = _spectral_gap(P)
    pi_min   = max(PI_MIN_FLOOR, 1.0 / len(tools))
    t_mix    = math.ceil((1.0 / delta) * math.log(1.0 / (EPSILON * pi_min)))

    # Perturbation: simulate 10% random noise on P
    noise      = np.random.default_rng(42).uniform(-0.05, 0.05, P.shape)
    delta_P    = noise - noise.mean(axis=1, keepdims=True)  # row-sum-zero
    perturb_bd = float(np.max(np.abs(delta_P)) / (2 * max(delta, 1e-6)))

    alarm = t_mix > LATENCY_BUDGET or perturb_bd > ERROR_BUDGET

    return {
        "session":    session_path.stem,
        "tool_calls": len(seq),
        "unique":     len(tools),
        "delta":      round(delta, 4),
        "t_mix":      t_mix,
        "perturb_bd": round(perturb_bd, 4),
        "alarm":      alarm,
    }


def run(dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    if not paths:
        print("[mixing-budget] No sessions found")
        return 0

    results     = [analyse_session(p) for p in paths]
    alarm_cases = [r for r in results if r.get("alarm")]

    print(f"\n=== Spatial Mixing Error Budget — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["alarm"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"δ={r['delta']:.3f}  t_mix={r['t_mix']}  "
                  f"perturb={r['perturb_bd']:.3f}  "
                  f"tools={r['unique']}/{r['tool_calls']}")

    if alarm_cases:
        print(f"\nALARM: yes — {len(alarm_cases)} session(s) exceed mixing/error budget")
        rc = 1
    else:
        print(f"\nALARM: no — routing chain mixing within budget")
        rc = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "results": results, "alarm_count": len(alarm_cases),
        }, indent=2))

    return rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.dry_run))


if __name__ == "__main__":
    main()
