#!/usr/bin/python3
"""
hierarchy-coherence-monitor.py

Auto-structures multi-agent delegation hierarchies to detect and reduce
contradictions between parallel sub-agents or layered skill delegations.

Math basis (categorical coherence from algebraic topology):
  A delegation hierarchy is coherent if the composition of delegation
  morphisms is consistent: for any pair of paths P1, P2 from orchestrator
  to the same leaf, the composed outputs commute.

  Alarm condition: max off-diagonal JS-divergence in the delegation
  agreement matrix exceeds coherence threshold.

  Algorithm:
  1. Load recent multi-agent delegation traces from stability.db
  2. For each (orchestrator, task_id) group, collect all sub-agent outputs
  3. Build pairwise JS divergence matrix over tool-use distributions
  4. Flag hierarchy as incoherent if any pair diverges > threshold
  5. Recommend merge strategy (majority vote / weighted reconciliation)

Usage:
  python3 hierarchy-coherence-monitor.py [--dry-run]
"""

from __future__ import annotations
import os

import argparse
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
STABILITY_DB = HOME / ".hermes/cache/monitors/stability.db"
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

JS_ALARM_THRESHOLD  = 0.50   # nats — matches consensus-convergence-monitor
MIN_AGENTS_FOR_CHECK = 2
EPSILON              = 1e-9


def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    m = 0.5 * (p + q)
    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > EPSILON
        return float(np.sum(a[mask] * np.log((a[mask]) / (b[mask] + EPSILON))))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def _tool_distribution(tool_seq: list[str], vocab: list[str]) -> np.ndarray:
    counts = np.zeros(len(vocab))
    for t in tool_seq:
        if t in vocab:
            counts[vocab.index(t)] += 1
    s = counts.sum()
    return (counts + EPSILON) / (s + len(vocab) * EPSILON)


def _load_session_tools(sessions_dir: Path) -> dict[str, list[str]]:
    """Load tool sequences per session from JSONL files."""
    sessions: dict[str, list[str]] = {}
    try:
        for p in sorted(sessions_dir.glob("*.jsonl"))[-20:]:
            tools = []
            sid = p.stem
            for line in p.read_text().splitlines():
                try:
                    ev = json.loads(line)
                    role = ev.get("role", "")
                    if role == "assistant":
                        content = ev.get("content", ev.get("api_content", ""))
                        if isinstance(content, str) and "tool_use" in content:
                            import re
                            for m in re.finditer(r'"name"\s*:\s*"([^"]+)"', content):
                                tools.append(m.group(1))
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool_use":
                                    tools.append(block.get("name", "unknown"))
                except Exception:
                    pass
            if tools:
                sessions[sid] = tools
    except Exception:
        pass
    return sessions


def _group_by_prefix(sessions: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    """
    Group sessions into delegation clusters by timestamp prefix (YYYYMMDD_HHMM).
    Sessions launched within the same minute are likely parallel sub-agents.
    """
    groups: dict[str, dict[str, list[str]]] = {}
    for sid, tools in sessions.items():
        # Extract date+hour prefix: YYYYMMDD_HH
        prefix = sid[:11] if len(sid) >= 11 else sid[:8]
        groups.setdefault(prefix, {})[sid] = tools
    return groups


def run_monitor(dry_run: bool = False) -> int:
    now = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    results: list[dict] = []

    sessions = _load_session_tools(SESSIONS_DIR)
    print(f"[hierarchy-coherence] Loaded {len(sessions)} sessions with tool calls")

    if not sessions:
        print("[hierarchy-coherence] No sessions with tool call data found")
        print("\nALARM: no — insufficient data")
        return 0

    groups = _group_by_prefix(sessions)
    print(f"[hierarchy-coherence] Delegation clusters (by hour-prefix): {len(groups)}")

    # Build vocab from all tools observed
    vocab = sorted({t for tools in sessions.values() for t in tools})
    if not vocab:
        print("[hierarchy-coherence] Empty tool vocab")
        return 0

    for cluster_id, cluster_sessions in groups.items():
        if len(cluster_sessions) < MIN_AGENTS_FOR_CHECK:
            continue

        sids = list(cluster_sessions.keys())
        dists = [
            _tool_distribution(cluster_sessions[sid], vocab)
            for sid in sids
        ]

        # Pairwise JS matrix
        n = len(dists)
        js_mat = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                v = _js_divergence(dists[i], dists[j])
                js_mat[i, j] = v
                js_mat[j, i] = v

        max_js   = float(np.max(js_mat))
        mean_js  = float(js_mat[js_mat > 0].mean()) if (js_mat > 0).any() else 0.0

        worst_pair = None
        if n >= 2:
            idx = np.unravel_index(js_mat.argmax(), js_mat.shape)
            worst_pair = (sids[idx[0]][:12], sids[idx[1]][:12])

        alarm = max_js > JS_ALARM_THRESHOLD
        if alarm:
            alarms.append(
                f"INCOHERENT cluster {cluster_id}: max JS={max_js:.3f} > {JS_ALARM_THRESHOLD} "
                f"between {worst_pair} — recommend merge-reconciler"
            )

        results.append({
            "cluster_id": cluster_id,
            "n_agents": n,
            "max_js": round(max_js, 4),
            "mean_js": round(mean_js, 4),
            "alarm": alarm,
            "worst_pair": worst_pair,
            "recommendation": "merge-reconciler.py or majority-vote" if alarm else "coherent",
        })

    print(f"\n=== Hierarchy Coherence Monitor — {now[:10]} ===")
    for r in results:
        flag = "  ALARM" if r["alarm"] else "OK"
        print(f"  [{flag}] cluster={r['cluster_id']} agents={r['n_agents']} "
              f"max_JS={r['max_js']:.3f} mean_JS={r['mean_js']:.3f}  → {r['recommendation']}")

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} incoherent delegation cluster(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — all delegation clusters coherent")
        alarm_exit = 0

    if not dry_run:
        out = CACHE_DIR / "hierarchy-coherence-report.json"
        out.write_text(json.dumps({
            "ts": now, "clusters": results, "alarms": alarms,
        }, indent=2))
        print(f"\nWritten: {out}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import sys
    sys.exit(run_monitor(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
