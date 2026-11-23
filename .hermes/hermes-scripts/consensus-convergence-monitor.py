#!/usr/bin/env python3
"""
consensus-convergence-monitor.py

Detects multi-agent opinion fragmentation or deadlock before results are merged.

Math basis (multi-agent systems / distributed consensus ideas queue):
  A consensus operator on agent belief states converges to a collective invariant
  through iterative averaging (DeGroot / gossip). Convergence rate is controlled
  by the spectral gap of the influence graph. If belief states fail to converge
  after D rounds (spectral gap near 0 or negative), fragmentation is detected.

  Applied to Hermes: agent "belief states" are approximated by the distribution
  over tool-call types in each delegated subagent's session. Two agents that
  both use terminal/execute_code heavily are in consensus; two agents where one
  uses search_files and the other uses web_search are diverging.

  Convergence metric: mean pairwise JS divergence between agent tool distributions.
  Threshold: JS > 0.5 nats = fragmentation alarm.

Usage:
    python3 consensus-convergence-monitor.py [--dry-run] [--threshold F]
    [--sessions DIR [DIR ...]]

Output:
    ~/.hermes/cache/consensus-state.json   — per-agent distributions + divergence
    ~/.hermes/cache/consensus-alarm.json   — if fragmentation alarm triggered
"""

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import os

HOME = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"
OUTPUT = HOME / ".hermes/cache/consensus-state.json"
ALARM = HOME / ".hermes/cache/consensus-alarm.json"


# ── Tool distribution per session ─────────────────────────────────────────────

def session_tool_distribution(session_file: Path) -> dict[str, float]:
    """Return normalised tool-call frequency distribution for a session."""
    counts: Counter = Counter()
    try:
        for line in session_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            for tc in (rec.get("tool_calls") or []):
                if isinstance(tc, dict):
                    name = tc.get("function", {}).get("name", "")
                    if name:
                        counts[name.lower()] += 1
    except Exception:
        pass
    total = sum(counts.values()) or 1
    return {k: v / total for k, v in counts.items()}


# ── Jensen-Shannon divergence ─────────────────────────────────────────────────

def js_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """Jensen-Shannon divergence between two tool distributions (in nats)."""
    vocab = sorted(set(p) | set(q))
    eps = 1e-10
    pv = np.array([p.get(v, eps) for v in vocab])
    qv = np.array([q.get(v, eps) for v in vocab])
    pv /= pv.sum()
    qv /= qv.sum()
    m = 0.5 * (pv + qv)
    # KL(p||m) + KL(q||m)
    def kl(a, b):
        return float(np.sum(a * np.log(np.clip(a / b, 1e-10, None))))
    return 0.5 * kl(pv, m) + 0.5 * kl(qv, m)


# ── Consensus check ───────────────────────────────────────────────────────────

def check_consensus(session_dirs: list[Path], threshold: float) -> dict:
    """Load all recent sessions, compute pairwise JS divergence, detect fragmentation."""
    sessions = {}
    for d in session_dirs:
        for f in sorted(d.glob("*.jsonl"))[-20:]:
            dist = session_tool_distribution(f)
            if dist:
                sessions[f.stem] = dist

    if len(sessions) < 2:
        return {
            "n_sessions": len(sessions),
            "mean_js": 0.0,
            "max_js": 0.0,
            "fragmented": False,
            "agents": list(sessions.keys()),
            "pairwise": [],
        }

    agents = list(sessions.keys())
    pairwise = []
    js_values = []
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            js = js_divergence(sessions[agents[i]], sessions[agents[j]])
            pairwise.append({
                "agent_a": agents[i],
                "agent_b": agents[j],
                "js_divergence": round(js, 4),
            })
            js_values.append(js)

    mean_js = float(np.mean(js_values)) if js_values else 0.0
    max_js = float(np.max(js_values)) if js_values else 0.0
    fragmented = mean_js > threshold

    # Top diverging pairs
    pairwise.sort(key=lambda x: x["js_divergence"], reverse=True)

    return {
        "n_sessions": len(sessions),
        "mean_js": round(mean_js, 4),
        "max_js": round(max_js, 4),
        "threshold": threshold,
        "fragmented": fragmented,
        "agents": agents,
        "top_diverging_pairs": pairwise[:5],
        "all_pairs": len(pairwise),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-agent consensus convergence monitor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Mean JS divergence alarm threshold in nats (default 0.5)")
    args = parser.parse_args()

    session_dirs = [d for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists()]
    result = check_consensus(session_dirs, args.threshold)

    now = datetime.now(timezone.utc).isoformat()
    result["checked_at"] = now

    if not args.dry_run:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _tmp = OUTPUT.with_suffix('.tmp'); _tmp.write_text(json.dumps(result, indent=2)); _tmp.replace(OUTPUT)
        if result["fragmented"]:
            _alarm_payload = json.dumps({"alarm": True, "mean_js": result["mean_js"], "max_js": result["max_js"], "threshold": result["threshold"], "top_diverging": result.get("top_diverging_pairs", [])[:3], "ts": now}, indent=2)
            _tmp = ALARM.with_suffix('.tmp'); _tmp.write_text(_alarm_payload); _tmp.replace(ALARM)
            print(f"[consensus] FRAGMENTATION alarm — {ALARM}", file=sys.stderr)

    print(f"\n=== Consensus Convergence Monitor — {now[:10]} ===")
    print(f"Sessions analysed: {result['n_sessions']}")
    print(f"Pairwise pairs:    {result.get('all_pairs', 0)}")
    print(f"Mean JS div:       {result['mean_js']:.4f} nats  (threshold={result['threshold']})")
    print(f"Max JS div:        {result['max_js']:.4f} nats")
    print(f"FRAGMENTED:        {'YES' if result['fragmented'] else 'no'}")
    if result.get("top_diverging_pairs"):
        print("\nTop diverging pairs:")
        for p in result["top_diverging_pairs"][:5]:
            print(f"  JS={p['js_divergence']:.4f}  {p['agent_a'][:25]} ↔ {p['agent_b'][:25]}")
    if args.dry_run:
        print("  (dry-run)")


if __name__ == "__main__":
    main()
