#!/usr/bin/python3
"""
redundancy-stability-monitor.py

Prevents Hermes from overcommitting to parallel skill execution (delegation
thrash) by tracking the marginal utility of additional parallel agents.

Math basis (redundancy from coding theory / Singleton bound):
  In a system with k parallel agents and r redundant agents, the effective
  information rate is R = (k - r) / k.
  When R < R_min (too many redundant agents), delegation is wasteful.
  When d_H(agent_i, agent_j) < δ (Hamming distance on tool vectors too small),
  agents are producing near-identical outputs — redundancy alarm.

  Algorithm:
  1. Load parallel session tool traces from same timestamp cluster
  2. Compute pairwise Hamming distance on binary tool-use vectors
  3. Alarm when redundancy rate r/k > R_max_redundancy
  4. Also flag when any cluster has zero variance (perfect echo chambers)

Usage:
  python3 redundancy-stability-monitor.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_REDUNDANCY_RATE = 0.60   # If > 60% of agents produce near-identical output → alarm
HAMMING_CLOSE       = 0.20   # Normalized hamming distance < 0.20 → agent pair is redundant
EPSILON             = 1e-9
MIN_CLUSTER_SIZE    = 2


def _load_session_tools(sessions_dir: Path) -> dict[str, list[str]]:
    sessions: dict[str, list[str]] = {}
    import re
    try:
        for p in sorted(sessions_dir.glob("*.jsonl"))[-30:]:
            tools = []
            sid = p.stem
            for line in p.read_text().splitlines():
                try:
                    ev = json.loads(line)
                    if ev.get("role", "") == "assistant":
                        content = ev.get("content", ev.get("api_content", ""))
                        if isinstance(content, str):
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


def _binary_vector(tools: list[str], vocab: list[str]) -> np.ndarray:
    v = np.zeros(len(vocab), dtype=int)
    for t in tools:
        if t in vocab:
            v[vocab.index(t)] = 1
    return v


def _hamming_norm(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sum(a != b)) / max(len(a), 1)


def _group_by_prefix(sessions: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    groups: dict[str, dict[str, list[str]]] = {}
    for sid, tools in sessions.items():
        prefix = sid[:11] if len(sid) >= 11 else sid[:8]
        groups.setdefault(prefix, {})[sid] = tools
    return groups


def run_monitor(dry_run: bool = False) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    results: list[dict] = []

    sessions = _load_session_tools(SESSIONS_DIR)
    print(f"[redundancy-monitor] Loaded {len(sessions)} sessions")

    if not sessions:
        print("[redundancy-monitor] No session tool data — cannot assess redundancy")
        print("\nALARM: no — insufficient data")
        return 0

    vocab  = sorted({t for tools in sessions.values() for t in tools})
    groups = _group_by_prefix(sessions)

    for cluster_id, cluster_sessions in groups.items():
        if len(cluster_sessions) < MIN_CLUSTER_SIZE:
            continue

        sids   = list(cluster_sessions.keys())
        vecs   = [_binary_vector(cluster_sessions[sid], vocab) for sid in sids]
        k      = len(vecs)

        # Pairwise Hamming distances
        close_pairs = 0
        pair_count  = 0
        worst_pair  = None
        worst_d     = 1.0
        for i in range(k):
            for j in range(i+1, k):
                d = _hamming_norm(vecs[i], vecs[j])
                pair_count += 1
                if d < HAMMING_CLOSE:
                    close_pairs += 1
                    if d < worst_d:
                        worst_d = d
                        worst_pair = (sids[i][:12], sids[j][:12])

        redundancy_rate = close_pairs / max(pair_count, 1)

        # Zero-variance check (all agents used identical tool sets)
        stacked  = np.stack(vecs)
        variance = float(stacked.var(axis=0).mean())
        echo_chamber = variance < EPSILON

        alarm = redundancy_rate > MAX_REDUNDANCY_RATE or echo_chamber
        if alarm:
            if echo_chamber:
                alarms.append(
                    f"ECHO_CHAMBER: cluster {cluster_id} — {k} agents have identical tool vectors (var=0)"
                )
            if redundancy_rate > MAX_REDUNDANCY_RATE:
                alarms.append(
                    f"REDUNDANCY: cluster {cluster_id} — {redundancy_rate:.0%} pairs are near-identical "
                    f"(Hamming < {HAMMING_CLOSE}), worst={worst_pair} d={worst_d:.3f}"
                )

        # Information rate R = (k - r) / k where r = number of redundant agents
        n_redundant = sum(1 for v in vecs if any(
            _hamming_norm(v, vecs[j]) < HAMMING_CLOSE for j in range(k) if j != vecs.index(v)
            if vecs.index(v) != j
        ))
        effective_rate = round((k - n_redundant) / k, 4) if k > 0 else 1.0

        results.append({
            "cluster_id": cluster_id,
            "n_agents": k,
            "redundancy_rate": round(redundancy_rate, 4),
            "effective_info_rate": effective_rate,
            "echo_chamber": echo_chamber,
            "variance": round(variance, 6),
            "alarm": alarm,
        })

    print(f"\n=== Redundancy Stability Monitor — {now[:10]} ===")
    for r in results:
        flag = "  ALARM" if r["alarm"] else "OK"
        print(
            f"  [{flag}] cluster={r['cluster_id']} agents={r['n_agents']} "
            f"redundancy={r['redundancy_rate']:.0%} effective_R={r['effective_info_rate']:.2f} "
            f"var={r['variance']:.4f} echo={r['echo_chamber']}"
        )

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} redundancy alarm(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — delegation diversity within bounds")
        alarm_exit = 0

    if not dry_run:
        out = CACHE_DIR / "redundancy-stability-report.json"
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
