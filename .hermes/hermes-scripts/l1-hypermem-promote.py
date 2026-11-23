#!/usr/bin/env python3
"""
l1-hypermem-promote.py — HyperMem episode grouping at l1-promote time.

At session end (or on demand), scans recent Graphiti episodes and groups
co-occurring facts (≥3 shared entities) into HYPEREDGE nodes.

Structure: 3-level hypergraph
  topics / episodes / facts
  hyperedges group related episodes+facts (high-order associations)

Source: HyperMem arXiv:2604.08256 (ACL 2026)
Usage:
  python3 l1-hypermem-promote.py [--dry-run] [--min-entities 3] [--top 20]
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GRAPHITI_BASE  = os.environ.get("GRAPHITI_BASE",  "http://127.0.0.1:8765/mcp")
GRAPHITI_GROUP = os.environ.get("GRAPHITI_GROUP_IDS", "hermes").split(",")
HERMES_HOME    = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HYPERMEM_LOG   = HERMES_HOME / "cache" / "hypermem-promote.jsonl"


# ---------------------------------------------------------------------------
# Graphiti helpers
# ---------------------------------------------------------------------------

def _gql(method: str, params: dict, timeout: int = 30) -> Any:
    """Call Graphiti MCP endpoint."""
    url = f"{GRAPHITI_BASE}/tools/{method}"
    payload = json.dumps(params).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def get_recent_episodes(top: int = 50) -> list[dict]:
    """Fetch recent episodes from Graphiti."""
    result = _gql("mcp__graphiti__get_episodes", {
        "group_ids": GRAPHITI_GROUP,
        "last_n": top,
    })
    if "error" in result:
        print(f"[warn] Graphiti episode fetch failed: {result['error']}")
        return []
    return result.get("episodes") or result.get("results") or []


def get_episode_entities(episode_uuid: str) -> list[dict]:
    """Get entities for a given episode."""
    result = _gql("mcp__graphiti__get_episode_entities", {"episode_uuid": episode_uuid})
    if "error" in result:
        return []
    return result.get("entities") or result.get("nodes") or []


def add_hyperedge(episode_uuids: list[str], shared_entities: list[str],
                  label: str, dry_run: bool = False) -> dict:
    """Add a HYPEREDGE episode grouping to Graphiti."""
    he_id = hashlib.sha256(
        json.dumps(sorted(episode_uuids)).encode()
    ).hexdigest()[:16]
    content = (
        f"HYPEREDGE:{he_id} | episodes={len(episode_uuids)} "
        f"| entities={','.join(shared_entities[:5])} | {label}"
    )
    if dry_run:
        return {"dry_run": True, "he_id": he_id, "content": content,
                "episodes": episode_uuids, "entities": shared_entities}
    result = _gql("mcp__graphiti__add_memory", {
        "content": content,
        "group_id": GRAPHITI_GROUP[0],
        "source": "hypermem-promote",
        "source_description": f"HyperMem hyperedge linking {len(episode_uuids)} episodes",
    })
    return {"he_id": he_id, "result": result, "episodes": episode_uuids}


# ---------------------------------------------------------------------------
# Hyperedge detection: cluster episodes by shared entity overlap
# ---------------------------------------------------------------------------

def detect_hyperedges(episodes: list[dict], entity_map: dict[str, list[str]],
                      min_entities: int = 3) -> list[dict]:
    """
    Find clusters of episodes sharing >= min_entities entities.
    Returns list of hyperedge dicts: {episodes, entities, label}.

    Simple greedy: for each pair of episodes sharing >= min_entities entities,
    group them. Then merge overlapping groups (union-find).
    """
    uuids = [ep.get("uuid") or ep.get("id", "") for ep in episodes]
    # Build co-occurrence: which episodes share which entities
    entity_to_eps: dict[str, set[str]] = {}
    for uuid in uuids:
        for ent in entity_map.get(uuid, []):
            entity_to_eps.setdefault(ent, set()).add(uuid)

    # Union-find
    parent: dict[str, str] = {u: u for u in uuids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str):
        parent[find(a)] = find(b)

    # For each entity shared by >= 2 episodes, union them
    entity_groups: dict[str, list[str]] = {}
    for ent, eps in entity_to_eps.items():
        if len(eps) >= 2:
            entity_groups[ent] = list(eps)
            ep_list = list(eps)
            for i in range(1, len(ep_list)):
                union(ep_list[0], ep_list[i])

    # Collect clusters
    clusters: dict[str, set[str]] = {}
    for u in uuids:
        root = find(u)
        clusters.setdefault(root, set()).add(u)

    # For each cluster, find shared entities
    hyperedges = []
    for root, cluster_uuids in clusters.items():
        if len(cluster_uuids) < 2:
            continue
        # entities that appear in ALL cluster episodes
        entity_sets = [set(entity_map.get(u, [])) for u in cluster_uuids]
        shared = entity_sets[0].intersection(*entity_sets[1:])
        if len(shared) >= min_entities:
            label = ",".join(sorted(shared)[:3])
            hyperedges.append({
                "episodes": list(cluster_uuids),
                "entities": list(shared),
                "label": f"shared:{label}",
            })

    return hyperedges


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HyperMem episode hyperedge promotion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done, don't write to Graphiti")
    parser.add_argument("--min-entities", type=int, default=3,
                        help="Minimum shared entities to form a hyperedge (default: 3)")
    parser.add_argument("--top", type=int, default=50,
                        help="How many recent episodes to scan (default: 50)")
    args = parser.parse_args()

    # no_agent mode: only print when there is something to report (non-empty stdout = delivery)
    verbose = args.dry_run or sys.stdout.isatty()

    episodes = get_recent_episodes(top=args.top)
    if not episodes:
        # silent exit — Graphiti offline or no episodes; watchdog pattern
        return 0

    entity_map: dict[str, list[str]] = {}
    for ep in episodes:
        uuid = ep.get("uuid") or ep.get("id", "")
        if not uuid:
            continue
        entities = get_episode_entities(uuid)
        entity_map[uuid] = [
            e.get("name") or e.get("uuid", "") for e in entities if e
        ]

    hyperedges = detect_hyperedges(episodes, entity_map, min_entities=args.min_entities)

    if not hyperedges:
        # nothing new to report — stay silent
        return 0

    results = []
    for he in hyperedges:
        if verbose:
            print(f"  HE: {len(he['episodes'])} episodes | entities: {he['entities'][:5]}")
        r = add_hyperedge(
            episode_uuids=he["episodes"],
            shared_entities=he["entities"],
            label=he["label"],
            dry_run=args.dry_run,
        )
        results.append(r)

    # Log
    HYPERMEM_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HYPERMEM_LOG, "a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "episodes_scanned": len(episodes),
            "hyperedges_found": len(hyperedges),
            "dry_run": args.dry_run,
            "results": results,
        }) + "\n")

    if args.dry_run:
        print("[hypermem] DRY RUN — no writes to Graphiti.")
    elif verbose:
        print(f"[hypermem] Done. {len(results)} hyperedges written.")
    else:
        # no_agent watchdog: emit summary only when hyperedges were actually found
        print(f"hypermem: {len(results)} new hyperedges written from {len(episodes)} episodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
