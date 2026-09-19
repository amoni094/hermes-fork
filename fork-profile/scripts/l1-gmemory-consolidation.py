#!/usr/bin/env python3
"""
l1-gmemory-consolidation.py — Three-tier G-Memory nightly cross-session consolidation.

Implements G-Memory (arXiv:2506.07398, NeurIPS 2025) three-tier memory architecture:
  Tier 1 — Session memory   : individual session facts (Hindsight/Graphiti per-session)
  Tier 2 — Query tier       : promoted facts that appeared 2+ times (existing l1-promote)
  Tier 3 — Insight tier     : cross-session distillations for facts with 3+ recurrences

This script handles the Tier-2 → Tier-3 promotion:
  1. Queries Hindsight for the N most-frequently recalled facts (access_count >= 3)
  2. Groups them by semantic theme (cosine clustering, k=5 by default)
  3. Calls haiku to distill each cluster into a single insight-tier sentence
  4. Writes insights to Graphiti as [type=insight] [trust=1.2] episodes

Design constraints:
  - Read-only access to Hindsight (no deletions)
  - Graphiti write only — no file mutations
  - Idempotent: insights are named by cluster_hash, so re-runs are safe
  - Soft failure: any cluster that fails is logged and skipped, not a fatal error

Usage:
  python3 l1-gmemory-consolidation.py [--dry-run] [--min-recurrence N] [--clusters K]
  python3 l1-gmemory-consolidation.py --dry-run          # show what would be written
  python3 l1-gmemory-consolidation.py --min-recurrence 2  # lower threshold for testing

Scheduled nightly via Hermes cron (g-memory-tier3-nightly).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
HINDSIGHT_BASE = "http://127.0.0.1:9177"
GRAPHITI_GROUP_ID = "hermes"
GRAPHITI_TIMEOUT = 60
ANTHROPIC_TIMEOUT = 60
ANTHROPIC_MODEL = "claude-haiku-4-5"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
HINDSIGHT_BANK = "hermes-default"
HINDSIGHT_RECALL_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories/recall"
HINDSIGHT_LIST_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories/list"
HINDSIGHT_TIMEOUT = 30

# 406 fix: Graphiti MCP requires both JSON and SSE in Accept.
GRAPHITI_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

DEFAULT_MIN_RECURRENCE = 3
DEFAULT_NUM_CLUSTERS = 5
DEFAULT_TOP_FACTS = 100

TOKEN_RE = re.compile(r"[a-z]{3,}")

SEED_QUERIES = [
    "user preferences workflow settings",
    "project configuration environment setup",
    "memory pipeline Hindsight Graphiti",
    "Hermes agent configuration skills",
    "research findings arxiv papers",
]


def _load_dotenv() -> None:
    """Load ~/.hermes/.env into os.environ without overwriting existing keys."""
    env_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / ".env"
    try:
        text = env_path.read_text()
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


def _parse_sse_or_json(raw: str) -> dict:
    """Parse MCP SSE (`data: {json}`) or plain JSON body."""
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw)


def hindsight_search(query: str, top_k: int = 20) -> list[dict]:
    """Search Hindsight for facts using the versioned recall API."""
    payload = {"query": query, "top_k": top_k, "budget": "low"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        HINDSIGHT_RECALL_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HINDSIGHT_TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [hindsight] WARNING: recall failed: {e}", file=sys.stderr)
        return []
    results = body.get("results") or body.get("memories") or body.get("items") or []
    return results if isinstance(results, list) else []


def hindsight_list(limit: int = 100, offset: int = 0) -> list[dict]:
    """List memories from Hindsight, sorted by proof_count (recurrence proxy)."""
    url = f"{HINDSIGHT_LIST_URL}?limit={limit}&offset={offset}"
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=HINDSIGHT_TIMEOUT) as resp:
            body = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [hindsight] WARNING: list failed: {e}", file=sys.stderr)
        return []
    results = body.get("memories") or body.get("results") or body.get("items") or []
    return results if isinstance(results, list) else []


def _memory_id(item: dict) -> str:
    return str(
        item.get("id")
        or item.get("memory_id")
        or item.get("uuid")
        or item.get("document_id")
        or ""
    )


def _memory_text(item: dict) -> str:
    if not isinstance(item, dict):
        return str(item)
    for key in ("content", "text", "memory", "body"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _memory_count(item: dict) -> int:
    meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    for src in (item, meta):
        for key in ("proof_count", "access_count", "score"):
            val = src.get(key)
            if isinstance(val, (int, float)):
                return int(val)
    return 0


def _normalize_fact(item: dict) -> dict | None:
    text = _memory_text(item)
    if not text:
        return None
    fid = _memory_id(item) or hashlib.sha256(text.encode()).hexdigest()[:16]
    count = _memory_count(item)
    return {"id": fid, "text": text, "proof_count": count, "access_count": count, "raw": item}


def fetch_high_recurrence_facts(min_recurrence: int, top_facts: int) -> list[dict]:
    """Pull facts from Hindsight with proof_count >= min_recurrence.

    proof_count is Hindsight's dedup counter — incremented each time a near-duplicate
    is merged into this memory. High proof_count = high recurrence across sessions.

    Strategy: bulk-list all memories, then filter by proof_count.
    Falls back to seed-query recall if list returns no proof_count data.
    """
    all_items: list[dict] = []
    offset = 0
    page = 100
    had_count_field = False
    while len(all_items) < max(top_facts * 4, 400):
        batch = hindsight_list(limit=page, offset=offset)
        if not batch:
            break
        all_items.extend(batch)
        for item in batch:
            if isinstance(item, dict):
                meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                if any(k in item or k in meta for k in ("proof_count", "access_count")):
                    had_count_field = True
        if len(batch) < page:
            break
        offset += page

    facts: list[dict] = []
    seen_ids: set[str] = set()
    if had_count_field:
        for item in all_items:
            norm = _normalize_fact(item) if isinstance(item, dict) else None
            if not norm or norm["id"] in seen_ids:
                continue
            if norm["proof_count"] < min_recurrence:
                continue
            seen_ids.add(norm["id"])
            facts.append(norm)
    else:
        for query in SEED_QUERIES:
            for item in hindsight_search(query, top_k=min(40, top_facts)):
                if not isinstance(item, dict):
                    continue
                norm = _normalize_fact(item)
                if not norm or norm["id"] in seen_ids:
                    continue
                count = norm["proof_count"]
                if count and count < min_recurrence:
                    continue
                if not count:
                    norm["proof_count"] = min_recurrence
                    norm["access_count"] = min_recurrence
                seen_ids.add(norm["id"])
                facts.append(norm)

    facts.sort(key=lambda f: f.get("proof_count") or 0, reverse=True)
    return facts[:top_facts]


def tokenize(text: str) -> list[str]:
    """Bag-of-words tokenizer (same as memory-query-router.py for consistency)."""
    return TOKEN_RE.findall((text or "").lower())


def _bow(text: str) -> dict[str, int]:
    return dict(Counter(tokenize(text)))


def cosine_sim(a: dict[str, int], b: dict[str, int]) -> float:
    """Cosine similarity between two bag-of-words dicts."""
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in keys)
    mag_a = sum(v * v for v in a.values()) ** 0.5
    mag_b = sum(v * v for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def cluster_facts(facts: list[dict], k: int) -> list[list[dict]]:
    """Simple greedy k-means-style clustering on BoW cosine similarity.

    Assigns each fact to the nearest centroid; initialises centroids
    by spreading across the sorted fact list (avoids k-means++ overhead).
    Returns k clusters (some may be empty if facts < k).
    """
    if not facts:
        return []
    k = max(1, min(k, len(facts)))
    bows = [_bow(f.get("text", "")) for f in facts]
    n = len(facts)
    centroid_indices = [min(n - 1, int(i * n / k)) for i in range(k)]
    centroids = [dict(bows[i]) for i in centroid_indices]

    assignments = [0] * n
    for _ in range(8):
        for i, bow in enumerate(bows):
            best_c, best_s = 0, -1.0
            for c, cent in enumerate(centroids):
                s = cosine_sim(bow, cent)
                if s > best_s:
                    best_c, best_s = c, s
            assignments[i] = best_c
        new_centroids: list[dict[str, float]] = []
        for c in range(k):
            members = [bows[i] for i, a in enumerate(assignments) if a == c]
            if not members:
                new_centroids.append(centroids[c])
                continue
            merged: dict[str, float] = {}
            for bow in members:
                for tok, cnt in bow.items():
                    merged[tok] = merged.get(tok, 0.0) + cnt
            scale = 1.0 / len(members)
            new_centroids.append({tok: cnt * scale for tok, cnt in merged.items()})
        centroids = new_centroids

    clusters: list[list[dict]] = [[] for _ in range(k)]
    for i, fact in enumerate(facts):
        clusters[assignments[i]].append(fact)
    return [c for c in clusters if c]


def distill_cluster(facts: list[dict]) -> str | None:
    """Call claude-haiku to distill a cluster of related facts into a single
    compact insight-tier sentence.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("  [distill] ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None
    bullets = []
    for f in facts:
        count = f.get("proof_count") or f.get("access_count") or "?"
        text = (f.get("text") or "").replace("\n", " ").strip()
        bullets.append(f"- {text} (seen {count})")
    bullet_list = "\n".join(bullets)
    prompt = (
        "You are a memory consolidation engine. The following facts have been "
        "frequently recalled from an AI agent's long-term memory "
        "(high access_count = high recurrence).\n"
        "Distill them into ONE compact insight sentence (25 words max) that captures "
        "the stable, reusable knowledge. Be specific and concrete. Do not add hedges or caveats.\n\n"
        f"Facts:\n{bullet_list}\n\n"
        "Insight (one sentence, no prefix):"
    )
    payload = {
        "model": os.environ.get("ANTHROPIC_MODEL", ANTHROPIC_MODEL),
        "max_tokens": 120,
        "messages": [{"role": "user", "content": prompt}],
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=ANTHROPIC_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [distill] WARNING: haiku call failed: {e}", file=sys.stderr)
        return None
    content = data.get("content") or []
    if isinstance(content, list) and content:
        text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
        text = (text or "").strip()
        if text:
            return text.splitlines()[0].strip().strip('"')
    return None


def _graphiti_post(session_id: str, method: str, params: dict) -> dict:
    """Send a single MCP JSON-RPC request. Parses SSE `data:` lines (Graphiti 406 fix)."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = dict(GRAPHITI_HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=GRAPHITI_TIMEOUT) as resp:
        raw = resp.read().decode()
        return _parse_sse_or_json(raw)


def graphiti_init() -> str:
    """MCP initialize handshake — session id comes from the HTTP response header."""
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "l1-gmemory-consolidation", "version": "1.0"},
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        GRAPHITI_BASE, data=data, headers=dict(GRAPHITI_HEADERS), method="POST"
    )
    with urllib.request.urlopen(req, timeout=GRAPHITI_TIMEOUT) as resp:
        session_id = resp.headers.get("mcp-session-id", "")
        resp.read()
    if not session_id:
        raise RuntimeError("No mcp-session-id returned from initialize")
    return session_id


def cluster_hash(facts: list[dict]) -> str:
    """Deterministic hash of a cluster's fact IDs for idempotent naming."""
    ids = sorted(str(f.get("id") or f.get("text", "")[:80]) for f in facts)
    blob = "\n".join(ids).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def graphiti_write_insight(session_id: str, insight: str, chash: str, source_facts: list[dict]) -> bool:
    """Write a distilled insight to Graphiti as a tier-3 memory episode."""
    derived = ", ".join(str(f.get("id", "")) for f in source_facts[:12] if f.get("id"))
    if len(source_facts) > 12:
        derived += f", ... ({len(source_facts)} total)"
    episode_body = (
        f"[type=insight] [trust=1.2] [source_type=internal] [cluster={chash}]\n"
        f"[derived_from: {derived}]\n"
        f"{insight}"
    )
    name = f"insight-{chash}"
    try:
        resp = _graphiti_post(session_id, "tools/call", {
            "name": "add_memory",
            "arguments": {
                "episode_body": episode_body,
                "name": name,
                "group_id": GRAPHITI_GROUP_ID,
            },
        })
    except Exception as e:
        print(f"  [graphiti] WARNING: failed to write insight '{name}': {e}", file=sys.stderr)
        return False
    result = resp.get("result", {})
    if isinstance(result, dict):
        content = result.get("content", [])
        if content and isinstance(content, list):
            text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            return "queued" in text.lower() or "success" in text.lower()
    return False


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(
        description="G-Memory three-tier insight consolidation (arXiv:2506.07398)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without calling Graphiti",
    )
    parser.add_argument(
        "--min-recurrence",
        type=int,
        default=DEFAULT_MIN_RECURRENCE,
        help=f"Min access_count for a fact to be included (default {DEFAULT_MIN_RECURRENCE})",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=DEFAULT_NUM_CLUSTERS,
        help=f"Number of semantic clusters (default {DEFAULT_NUM_CLUSTERS})",
    )
    parser.add_argument(
        "--top-facts",
        type=int,
        default=DEFAULT_TOP_FACTS,
        help=f"Max facts to pull from Hindsight (default {DEFAULT_TOP_FACTS})",
    )
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"[l1-gmemory] G-Memory Tier-3 consolidation run ({mode})")
    print(
        f"[l1-gmemory] params: min_recurrence={args.min_recurrence}, "
        f"clusters={args.clusters}, top_facts={args.top_facts}"
    )

    print(f"\n[l1-gmemory] Fetching facts with access_count >= {args.min_recurrence}...")
    facts = fetch_high_recurrence_facts(args.min_recurrence, args.top_facts)
    if not facts:
        print(
            f"[l1-gmemory] No facts found with access_count >= {args.min_recurrence}. "
            "Try --min-recurrence 1 to test.\n"
            "  Note: access_count is only populated when facts are deduped by l1-promote.py.\n"
            "  If running for the first time, the pipeline may not yet have deduplicated any facts."
        )
        return 0

    print(f"[l1-gmemory] Found {len(facts)} recurring facts:")
    for f in facts[:8]:
        preview = (f.get("text") or "")[:80]
        print(f"  [{f.get('id', '?')[:12]}] (seen {f.get('proof_count')}) {preview}")

    print(f"\n[l1-gmemory] Clustering into {args.clusters} semantic groups...")
    clusters = cluster_facts(facts, args.clusters)
    print(f"[l1-gmemory] Formed {len(clusters)} non-empty clusters")
    for i, cluster in enumerate(clusters, 1):
        lead = (cluster[0].get("text") or "")[:70]
        print(f"  Cluster {i}: {len(cluster)} facts — lead: {lead}")

    if args.dry_run:
        print("\n[l1-gmemory] DRY RUN — showing what would be distilled and written:")
        for i, cluster in enumerate(clusters, 1):
            chash = cluster_hash(cluster)
            print(f"  Cluster {i} (hash={chash}, {len(cluster)} facts):")
            for f in cluster[:5]:
                preview = (f.get("text") or "")[:90]
                print(f"    [{f.get('id', '?')[:12]}] {preview}")
            print("    Would call haiku to distill -> write to Graphiti as [type=insight]")
        print(f"[l1-gmemory] DRY RUN complete — {len(clusters)} insights would be written")
        return 0

    print("\n[l1-gmemory] Initializing Graphiti session...")
    try:
        session_id = graphiti_init()
    except Exception as e:
        print(f"[l1-gmemory] ERROR: Cannot connect to Graphiti: {e}", file=sys.stderr)
        return 1

    written = 0
    failed = 0
    for i, cluster in enumerate(clusters, 1):
        chash = cluster_hash(cluster)
        print(f"[l1-gmemory] Cluster {i}: {len(cluster)} facts, hash={chash}...")
        insight = distill_cluster(cluster)
        if not insight:
            print(f"  [SKIP] distillation failed for cluster {chash}")
            failed += 1
            continue
        print(f"  insight: {insight}")
        ok = graphiti_write_insight(session_id, insight, chash, cluster)
        if ok:
            print("  [OK] queued to Graphiti")
            written += 1
        else:
            print("  [FAIL] Graphiti write failed")
            failed += 1
        if i < len(clusters):
            time.sleep(0.3)

    print(f"\n[l1-gmemory] Done: {written} insights written, {failed} failed.")
    if failed:
        print(
            f"[l1-gmemory] {failed} clusters failed — check Hindsight/Graphiti connectivity.",
            file=sys.stderr,
        )

    # Post-consolidation: surface unresolved H2 obstructions from profinite-thread-check.
    # Fail-open: any I/O or parse error is silently skipped.
    try:
        _hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        _profile = os.environ.get("HERMES_PROFILE", "")
        # Profile-aware cache path: prefer <profile>/cache/ when HERMES_PROFILE is set,
        # otherwise fall back to the default <HERMES_HOME>/cache/ location.
        if _profile:
            _ob_path = _hermes_home / "profiles" / _profile / "cache" / "h2-obstructions.json"
            if not _ob_path.exists():
                _ob_path = _hermes_home / "cache" / "h2-obstructions.json"
        else:
            _ob_path = _hermes_home / "cache" / "h2-obstructions.json"
        if _ob_path.exists():
            _ob_data = json.loads(_ob_path.read_text())
            _obstructions = _ob_data.get("obstructions", [])
            for _ob in _obstructions:
                if _ob.get("resolved") is True:
                    continue
                _key = _ob.get("class_id", "<unknown>")
                _cls = _ob.get("type", "<unknown>")
                print(
                    f"[l1-gmemory] unresolved H2 obstruction: {_key} ({_cls})",
                    file=sys.stderr,
                )
    except Exception:
        pass  # fail-open: H2 ledger check must never abort the pipeline

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
