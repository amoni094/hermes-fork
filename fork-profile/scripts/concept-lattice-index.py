#!/usr/bin/env python3
"""
concept-lattice-index.py — ContextRAG-style nightly concept lattice over Hindsight facts.

Builds a fuzzy concept lattice from Hindsight embeddings + persistent KV facts.
Nightly cron job; adds lattice-derived bridge nodes to the retrieval index.

Structure:
  1. Fetch fact texts from Hindsight
  2. RQ-kmeans clustering to get attribute assignments
  3. FCA: formal context (facts × clusters) → concept lattice
  4. Store top meet-nodes as bridge facts back to Hindsight
  5. Query activation: incoming query activates meet-nodes → retrieves members

Source: ContextRAG arXiv:2605.19735 (May 2026) — +3.9 pp F1 vs flat kNN

Usage:
  python3 concept-lattice-index.py [--dry-run] [--clusters 16] [--min-support 3]
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

HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://127.0.0.1:9177")
HINDSIGHT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes-default")
HERMES_HOME    = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
LATTICE_CACHE  = HERMES_HOME / "cache" / "concept-lattice.json"
LATTICE_LOG    = HERMES_HOME / "cache" / "concept-lattice.jsonl"

# v1 API prefix (hindsight-api >= 1.0; legacy /recall stub returns 404)
_H_RECALL_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories/recall"
_H_RETAIN_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories"


# ---------------------------------------------------------------------------
# Hindsight helpers
# ---------------------------------------------------------------------------

def _h_request(path: str, payload: dict, timeout: int = 15) -> Any:
    # Route legacy short paths to v1 endpoints
    if path == "/recall":
        url = _H_RECALL_URL
    elif path == "/retain":
        url = _H_RETAIN_URL
    else:
        url = f"{HINDSIGHT_BASE}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        import time as _time
        _t0 = _time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.loads(r.read())
        elapsed = _time.monotonic() - _t0
        if elapsed > 5.0:
            print(f"[lattice] SLOW hindsight {path} ({HINDSIGHT_BANK}): {elapsed:.2f}s "
                  f"— bank has {result.get('total', '?')} results; "
                  "consider HINDSIGHT_BANK env override or ANN index audit", flush=True)
        return result
    except Exception as e:
        return {"error": str(e)}


def fetch_facts(limit: int = 500) -> list[dict]:
    """Fetch recent facts from Hindsight."""
    result = _h_request("/recall", {"query": "*", "bank": HINDSIGHT_BANK, "top_k": limit})
    if "error" in result:
        print(f"[lattice] Hindsight fetch failed: {result['error']}")
        return []
    return result.get("results") or result.get("memories") or []


def store_bridge_node(content: str, tags: list[str]) -> dict:
    """Store a lattice bridge concept node back to Hindsight."""
    result = _h_request("/retain", {
        "content": content,
        "bank": HINDSIGHT_BANK,
        "tags": tags + ["lattice-bridge"],
        "source": "concept-lattice-index",
    })
    if isinstance(result, dict) and "error" in result:
        import sys as _s; print(f"[concept-lattice] bridge node retain failed: {result['error']}", file=_s.stderr)
    return result


# ---------------------------------------------------------------------------
# FCA (Formal Concept Analysis) — lightweight pure-Python implementation
# ---------------------------------------------------------------------------

def rq_kmeans_assign(texts: list[str], n_clusters: int) -> list[int]:
    """
    TF-IDF cosine k-means clustering (stdlib-only: math, collections, re, hashlib).
    Returns cluster IDs in [0, n_clusters).

    Steps:
      1. Tokenise with stopword removal
      2. Build TF-IDF vectors
      3. k-means with cosine similarity, max 20 iterations
         - Deterministic seeding via sha256 hash spread
         - Recompute centroids as mean TF-IDF vectors
         - Early stop when assignments unchanged
    """
    import math
    import re
    from collections import Counter

    _STOPWORDS = {
        'the','a','an','is','are','was','were','in','on','at','to','of','and',
        'or','for','with','by','from','that','this','it','as','be','has','have',
        'had','do','does','did','not','but','if','so','can','will','would',
        'could','should','may','might','shall',
    }

    def _tokenise(text: str) -> list[str]:
        tokens = re.split(r'[^a-z0-9]+', text.lower())
        return [t for t in tokens if t and t not in _STOPWORDS]

    def _tfidf(token_lists: list[list[str]]) -> list[dict]:
        N = len(token_lists)
        # document frequency
        df: dict[str, int] = Counter()
        for toks in token_lists:
            for t in set(toks):
                df[t] += 1
        vectors: list[dict] = []
        for toks in token_lists:
            if not toks:
                vectors.append({})
                continue
            tf_map = Counter(toks)
            doclen = len(toks)
            vec: dict[str, float] = {}
            for term, cnt in tf_map.items():
                tf = cnt / doclen
                idf = math.log((N + 1) / (df[term] + 1) + 1)
                vec[term] = tf * idf
            vectors.append(vec)
        return vectors

    def _cosine(a: dict, b: dict) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a.get(t, 0.0) * v for t, v in b.items())
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _mean_vec(vecs: list[dict]) -> dict:
        if not vecs:
            return {}
        acc: dict[str, float] = {}
        for v in vecs:
            for term, val in v.items():
                acc[term] = acc.get(term, 0.0) + val
        n = len(vecs)
        return {term: val / n for term, val in acc.items()}

    # Edge cases
    if not texts:
        return []
    n_clusters = max(1, min(n_clusters, len(texts)))

    token_lists = [_tokenise(t) for t in texts]
    vectors = _tfidf(token_lists)

    # --- Deterministic seed: pick n_clusters indices whose sha256 hashes
    #     spread most evenly across the [0, 2^256) range ---
    target_gap = (2 ** 256) // n_clusters
    sorted_by_hash = sorted(
        range(len(texts)),
        key=lambda i: int(hashlib.sha256(texts[i].encode()).hexdigest(), 16),
    )
    # Place seeds at equal intervals across the sorted hash order
    seed_indices: list[int] = []
    step = max(1, len(texts) // n_clusters)
    for k in range(n_clusters):
        idx = min(k * step, len(texts) - 1)
        seed_indices.append(sorted_by_hash[idx])

    centroids: list[dict] = [vectors[i] for i in seed_indices]

    assignments: list[int] = [0] * len(texts)
    for _iter in range(20):
        new_assignments: list[int] = []
        for vec in vectors:
            best_cluster = 0
            best_sim = -1.0
            for k, centroid in enumerate(centroids):
                sim = _cosine(vec, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = k
            new_assignments.append(best_cluster)

        if new_assignments == assignments and _iter > 0:
            break
        assignments = new_assignments

        # Recompute centroids
        for k in range(n_clusters):
            members = [vectors[i] for i, a in enumerate(assignments) if a == k]
            if members:
                centroids[k] = _mean_vec(members)
            # else: keep old centroid (dead cluster)

    return assignments


def build_formal_context(facts: list[dict], n_clusters: int) -> tuple[list, list, list[list[bool]]]:
    """
    Build formal context (G×M, I) where:
      G = facts (objects)
      M = clusters (attributes)
      I[i][j] = True if fact i belongs to cluster j

    Returns: (fact_labels, cluster_labels, incidence_matrix)
    """
    texts = [f.get("text") or f.get("content") or "" for f in facts]
    labels = [f.get("text", "")[:60] for f in facts]
    assignments = rq_kmeans_assign(texts, n_clusters)
    cluster_labels = [f"C{j}" for j in range(n_clusters)]
    incidence: list[list[bool]] = []
    for a in assignments:
        row = [False] * n_clusters
        row[a] = True
        incidence.append(row)
    return labels, cluster_labels, incidence


def find_concepts(g_labels: list[str], m_labels: list[str],
                  incidence: list[list[bool]],
                  min_support: int = 3) -> list[dict]:
    """
    Extract formal concepts (extent, intent) with support >= min_support.
    Concept = (extent={objects with ALL attributes in intent},
               intent={attributes shared by ALL objects in extent}).
    Simplified: single-attribute intents (clusters) and their extents.
    For a real lattice, use a library like concepts or fcapy.
    """
    n_m = len(m_labels)
    concepts = []
    for j in range(n_m):
        # Single-attribute concept: extent = all facts assigned to cluster j
        extent = [g_labels[i] for i, row in enumerate(incidence) if row[j]]
        if len(extent) >= min_support:
            concepts.append({
                "intent": [m_labels[j]],
                "extent": extent,
                "support": len(extent),
            })
    # Also compute pairwise meet-nodes (intersection of two cluster extents)
    for j1 in range(n_m):
        for j2 in range(j1 + 1, n_m):
            e1 = {g_labels[i] for i, row in enumerate(incidence) if row[j1]}
            e2 = {g_labels[i] for i, row in enumerate(incidence) if row[j2]}
            shared = e1 & e2
            if len(shared) >= min_support:
                concepts.append({
                    "intent": [m_labels[j1], m_labels[j2]],
                    "extent": list(shared),
                    "support": len(shared),
                    "is_meet": True,
                })
    return sorted(concepts, key=lambda c: -c["support"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ContextRAG concept lattice nightly index")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clusters", type=int, default=16,
                        help="Number of RQ-kmeans clusters (default: 16)")
    parser.add_argument("--min-support", type=int, default=3,
                        help="Minimum facts per concept to emit bridge node (default: 3)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Max facts to fetch from Hindsight (default: 300)")
    parser.add_argument("--query", metavar="TEXT", default=None,
                        help="Query the cached lattice and print JSON hits to stdout")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of lattice hits to return for --query (default: 5)")
    args = parser.parse_args()

    # ── Query path: semantic fallback called by skill-router-index ──────────
    if args.query is not None:
        hits = query_activate(args.query, top_k=args.top_k)
        print(json.dumps(hits))
        return 0

    verbose = args.dry_run or sys.stdout.isatty()

    facts = fetch_facts(limit=args.limit)
    if not facts:
        # silent exit — Hindsight offline; watchdog pattern
        return 0

    if verbose:
        print(f"[lattice] Got {len(facts)} facts. Building formal context ({args.clusters} clusters)...")
    g_labels, m_labels, incidence = build_formal_context(facts, n_clusters=args.clusters)
    concepts = find_concepts(g_labels, m_labels, incidence, min_support=args.min_support)
    if verbose:
        print(f"[lattice] Found {len(concepts)} concepts (support >= {args.min_support}).")

    # Select top concepts as bridge nodes (by support)
    top_concepts = concepts[:min(20, len(concepts))]
    bridge_results = []
    for c in top_concepts:
        intent_str = "+".join(c["intent"])
        content = (
            f"LATTICE-BRIDGE:{intent_str} | support={c['support']} | "
            f"members: {'; '.join(c['extent'][:5])}"
            + (f" [+{c['support']-5} more]" if c['support'] > 5 else "")
        )
        tags = [f"cluster:{i}" for i in c["intent"]] + ["fca"]
        if args.dry_run:
            print(f"  DRY: {content[:100]}...")
            bridge_results.append({"dry_run": True, "content": content})
        else:
            r = store_bridge_node(content, tags)
            bridge_results.append(r)

    # Save lattice to cache for query-time activation
    lattice_data = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "n_facts": len(facts),
        "n_clusters": args.clusters,
        "concepts": [
            {"intent": c["intent"], "support": c["support"],
             "members": c["extent"][:10]}
            for c in top_concepts
        ],
    }
    if not args.dry_run:
        LATTICE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _tmp_l = LATTICE_CACHE.with_suffix('.tmp')
        _tmp_l.write_text(json.dumps(lattice_data, indent=2))
        _tmp_l.rename(LATTICE_CACHE)
        if verbose:
            print(f"[lattice] Lattice saved to {LATTICE_CACHE}")

    # Log
    LATTICE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LATTICE_LOG, "a") as f:
        f.write(json.dumps({
            "ts": lattice_data["built_at"],
            "facts_indexed": len(facts),
            "concepts_found": len(concepts),
            "bridge_nodes_written": len(top_concepts),
            "dry_run": args.dry_run,
        }) + "\n")

    if args.dry_run:
        print(f"[lattice] DRY RUN — {len(top_concepts)} bridge nodes would be written.")
    elif verbose:
        print(f"[lattice] Done. {len(top_concepts)} bridge nodes written.")
    else:
        # no_agent watchdog: emit summary line (non-empty → delivered to local)
        print(f"concept-lattice: {len(top_concepts)} bridge nodes from {len(facts)} facts.")
    return 0


def query_activate(query_text: str, top_k: int = 5) -> list[dict]:
    """
    Query-time lattice activation: given a query, find relevant bridge concepts
    from the cached lattice and return their member labels for retrieval expansion.
    Called by unified-recall.py when LATTICE_CACHE exists.
    """
    if not LATTICE_CACHE.exists():
        return []
    try:
        lattice = json.loads(LATTICE_CACHE.read_text())
    except Exception:
        return []
    # Simple keyword overlap activation
    query_words = set(query_text.lower().split())
    activated = []
    for c in lattice.get("concepts", []):
        # Score: how many member labels overlap with query words
        member_text = " ".join(c.get("members", [])).lower()
        overlap = sum(1 for w in query_words if len(w) > 3 and w in member_text)
        if overlap > 0:
            activated.append({**c, "_activation_score": overlap})
    activated.sort(key=lambda x: -x["_activation_score"])
    return activated[:top_k]


if __name__ == "__main__":
    raise SystemExit(main())
