#!/usr/bin/env python3
"""
graphiti-edge-health.py — Spectral edge health check for Graphiti KG
arXiv:2609.24638 — Edge-based Katz Centralities (edge ranking / prune signal)
arXiv:2609.24683 — Semi-Monotonicity for Spectral Centrality (hub-score monotonicity)

Runs as a no_agent cron job every 6 hours. Queries Graphiti, computes edge Katz
scores, flags low-signal edges, checks hub-score monotonicity.

Output: one JSON line to ~/.hermes/profiles/fork/logs/graphiti-edge-health.jsonl
Prints nothing if status=ok (silent cron). Prints summary line if status=warn.
"""
import sys
import json
import os
import math
import datetime
import urllib.request
import urllib.error
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hh = str(_HERMES_HOME)
_FORK_ROOT = _HERMES_HOME if ("profiles" in _hh and _hh.endswith("fork")) else _HERMES_HOME / "profiles/fork"
LOG_PATH = _FORK_ROOT / "logs/graphiti-edge-health.jsonl"
GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Katz parameters (stdlib-only power iteration)
KATZ_ALPHA = 0.01
KATZ_ITERATIONS = 30
LOW_SIGNAL_ZSCORE = -2.0  # flag edges below mean - 2*stdev

# Hub-score state (compare run-over-run via log)
HUB_STATE_PATH = _FORK_ROOT / "logs/graphiti-hub-scores.json"


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _graphiti_call(method_name: str, arguments: dict) -> dict:
    """MCP JSON-RPC call to Graphiti."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": method_name, "arguments": arguments},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        GRAPHITI_BASE,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _fetch_edges() -> list[dict]:
    """Fetch up to 200 facts from Graphiti and parse into edge records."""
    resp = _graphiti_call(
        "mcp__graphiti__search_memory_facts",
        {"query": "*", "max_facts": 200},
    )
    # Graphiti returns content as text in result[0].text
    try:
        result_text = resp["result"]["content"][0]["text"]
        facts = json.loads(result_text) if result_text.startswith("[") else []
    except (KeyError, IndexError, json.JSONDecodeError):
        # Try alternate response shapes
        try:
            facts = resp.get("result", {}).get("facts", [])
        except Exception:
            facts = []
    return facts


def _compute_katz(edges: list[dict]) -> dict[str, float]:
    """
    Edge-based Katz centrality (arXiv:2609.24638).
    Treats each edge as a node in the line graph; adjacency = shared endpoint.
    Returns {edge_uuid: katz_score}.
    """
    if not edges:
        return {}

    # Build edge adjacency via shared source/target nodes
    edge_ids = [e.get("uuid", e.get("fact_id", str(i))) for i, e in enumerate(edges)]
    edge_sources = [e.get("source_node_uuid", "") for e in edges]
    edge_targets = [e.get("target_node_uuid", "") for e in edges]

    n = len(edges)
    # scores vector, initialised to 1/n
    scores = {eid: 1.0 / n for eid in edge_ids}

    for _ in range(KATZ_ITERATIONS):
        new_scores = {}
        for i, eid_i in enumerate(edge_ids):
            # Neighbours: edges sharing a node endpoint
            neighbour_sum = 0.0
            for j, eid_j in enumerate(edge_ids):
                if i == j:
                    continue
                if (edge_sources[i] and edge_sources[i] in (edge_sources[j], edge_targets[j])) or \
                   (edge_targets[i] and edge_targets[i] in (edge_sources[j], edge_targets[j])):
                    neighbour_sum += scores[eid_j]
            new_scores[eid_i] = KATZ_ALPHA * neighbour_sum + 1.0
        # Normalise
        total = sum(new_scores.values())
        scores = {k: v / total for k, v in new_scores.items()}

    return scores


def _stdev(values: list[float]) -> tuple[float, float]:
    """Return (mean, stdev) for a list of floats."""
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return mean, math.sqrt(variance)


def _hub_score_delta(scores: dict[str, float]) -> float:
    """
    Semi-monotonicity check (arXiv:2609.24683).
    Compare max hub score vs previous run. Delta > 0 = growing hub (warn if large).
    """
    max_score = max(scores.values()) if scores else 0.0
    prev = {}
    if HUB_STATE_PATH.exists():
        try:
            prev = json.loads(HUB_STATE_PATH.read_text())
        except Exception:
            prev = {}
    prev_max = prev.get("max_hub_score", max_score)
    delta = max_score - prev_max
    # Persist for next run — atomic tmp+rename to avoid data loss on crash
    try:
        _tmp = HUB_STATE_PATH.with_suffix(".tmp")
        _tmp.write_text(json.dumps({"max_hub_score": max_score, "ts": _now_iso()}))
        _tmp.rename(HUB_STATE_PATH)
    except OSError:
        pass
    return delta


def main() -> None:
    ts = _now_iso()
    try:
        edges = _fetch_edges()
    except (urllib.error.URLError, OSError, Exception) as exc:
        record = {"ts": ts, "total_edges": 0, "flagged_low_signal": 0,
                  "flagged_ids": [], "hub_score_delta": 0.0, "status": "error",
                  "error": str(exc)}
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
        # Return (not sys.exit) so atexit handlers fire; caller sees exit code via main()
        return

    scores = _compute_katz(edges)
    values = list(scores.values())
    mean, stdev = _stdev(values)
    threshold = mean + LOW_SIGNAL_ZSCORE * stdev  # mean - 2*stdev

    flagged_ids = [eid for eid, score in scores.items() if score < threshold]
    hub_delta = _hub_score_delta(scores)

    status = "ok"
    if flagged_ids or abs(hub_delta) > 0.1:
        status = "warn"

    record = {
        "ts": ts,
        "total_edges": len(edges),
        "mean_katz": round(mean, 6),
        "stdev_katz": round(stdev, 6),
        "threshold": round(threshold, 6),
        "flagged_low_signal": len(flagged_ids),
        "flagged_ids": flagged_ids[:20],  # cap to avoid huge log lines
        "hub_score_delta": round(hub_delta, 6),
        "status": status,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")

    # Only print if warn (cron silent-unless-output pattern)
    if status == "warn":
        print(f"graphiti-edge-health: {status} — {len(flagged_ids)} low-signal edges, "
              f"hub_delta={hub_delta:+.4f}")


if __name__ == "__main__":
    main()
