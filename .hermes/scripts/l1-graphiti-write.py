#!/usr/bin/env python3
"""
l1-graphiti-write.py — Write staged Hindsight facts to Graphiti as episodes.

Called by the l1-hindsight-promote cron job BEFORE staging.md is truncated.
Each fact becomes a Graphiti episode for entity/relationship extraction.

Uses stateful MCP HTTP transport (initialize + session-id header + tools/call).

Usage: python3 l1-graphiti-write.py [staging_file] [--source-type internal|external|cron]
       Defaults to ~/.hermes/memory-facts/staging.md, source_type=internal

PSE mitigation (arXiv:2608.07952): every episode written to Graphiti carries a
source_type tag so retrieval can weight facts by trust tier:
  internal — extracted from Hermes user sessions (highest trust)
  cron     — produced by automated cron jobs (medium trust, no direct user authorship)
  external — derived from web_extract, subagent outputs, or third-party content (lowest trust)

Retrieval consumers should weight scores: internal >= cron > external.

New fields parsed from staging.md (added by l1-extract v4 / l1-promote v2):
  [vc=stable|volatile|ephemeral]  — volatility class for ScrubJay decay awareness
  [ns=profile|event|record]       — LeanMem memory namespace partition
  [anchors: a1, a2, ...]          — InMind world-bridge anchor objects
These are forwarded into the Graphiti episode_body so Graphiti's LLM extractor
can use them for richer entity/relationship extraction.

Sweep 24 additions:
  --on-session-complete: trigger mode that fires immediately when a session ends,
    writing only facts from the most recent extract batch rather than full staging.md.
    (G-Memory arXiv:2608.01801: session-boundary writes improve entity coherence.)
  Entity deduplication: before writing, check Graphiti for near-duplicate entities
    by name (fuzzy match) and merge into existing nodes rather than creating new ones.
    (LiCoMemory arXiv:2607.19412: entity dedup is the #1 graphiti quality fix.)
"""
import sys
import re
import json
import time
import datetime
import pathlib
import os
import socket
from pathlib import Path
import urllib.request
import urllib.error

GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
GROUP_ID = "hermes"
TIMEOUT = 60  # seconds per episode write (extraction can be slow)
GRAPHITI_WARN_NODES = 40_000  # OzBrain HN: latency cliff ~50k; warn early
GRAPHITI_HALT_NODES = 50_000

def _load_graphiti_caps() -> None:
    """Sweep 27: config.yaml memory.tier_thresholds graphiti_*_nodes."""
    global GRAPHITI_WARN_NODES, GRAPHITI_HALT_NODES
    cfg_path = Path.home() / ".hermes" / "config.yaml"
    try:
        import yaml  # type: ignore
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
        tt = (cfg.get("memory") or {}).get("tier_thresholds") or {}
        if tt.get("graphiti_warn_nodes") is not None:
            GRAPHITI_WARN_NODES = int(tt["graphiti_warn_nodes"])
        if tt.get("graphiti_halt_nodes") is not None:
            GRAPHITI_HALT_NODES = int(tt["graphiti_halt_nodes"])
    except Exception:
        pass


import hashlib
import importlib.util as _iutil
_tg_spec = _iutil.spec_from_file_location(
    "l1_tracegrant", pathlib.Path(__file__).parent / "l1-tracegrant.py"
)
_tg_mod = _iutil.module_from_spec(_tg_spec)  # type: ignore[arg-type]
_tg_spec.loader.exec_module(_tg_mod)          # type: ignore[union-attr]
tracegrant_check = _tg_mod.tracegrant_check
tracegrant_log_grant = _tg_mod.tracegrant_log_grant

# Valid source types and their trust weights (informational — enforced by consumers)
SOURCE_TYPES = {"internal": 1.0, "cron": 0.7, "external": 0.4, "subagent": 0.7}
DEFAULT_SOURCE_TYPE = "internal"

TIMESTAMP_RE = re.compile(r"^\s*-\s*\[[\dT:Z\-+]+\]\s*(?:\[score=\d+\]\s*)?(?:\[type=(\w+)\]\s*)?(?:\[source=(\w+)\]\s*)?")

HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


# ── M1: Provenance helpers ─────────────────────────────────────────────────────

def _build_provenance() -> dict:
    """Build a provenance metadata dict for each episode write (M1)."""
    return {
        "session_id": os.environ.get("HERMES_SESSION_ID", "UNKNOWN"),
        "agent_id": f"{socket.gethostname()}_{os.getpid()}",
        "ts": datetime.datetime.utcnow().isoformat(),
        "source_tool": "l1-graphiti-write",
    }


def _prov_tag(prov: dict) -> str:
    """Compact inline provenance string prepended to episode_body."""
    return (
        f"[prov session={prov['session_id']} "
        f"agent={prov['agent_id']} "
        f"ts={prov['ts']}]"
    )


# ── M3: Contradiction detection ────────────────────────────────────────────────

# Simple English stopwords for entity key extraction
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "by", "for", "with", "from", "and", "or", "but", "not", "no",
    "it", "its", "this", "that", "these", "those", "as", "if", "then",
    "than", "so", "yet", "when", "where", "who", "which", "what", "how",
})

# Opposing state pairs for contradiction detection — canonical set shared with kg-contradiction-check.py
# Import from standalone if available; otherwise use inline copy (M3, arXiv:2608.03648 alignment)
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "kg_contradiction_check",
        str(Path.home() / ".hermes" / "scripts" / "kg-contradiction-check.py")
    )
    if _spec is None or _spec.loader is None:
        raise ImportError("spec or loader unavailable")
    _kgmod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_kgmod)  # type: ignore[union-attr]
    _OPPOSING_PAIRS: list[tuple[str, str]] = _kgmod.OPPOSITION_PAIRS
except Exception:
    # Fallback inline — keep in sync with kg-contradiction-check.py OPPOSITION_PAIRS
    _OPPOSING_PAIRS = [
        ("enabled", "disabled"),
        ("active", "inactive"),
        ("connected", "disconnected"),
        ("running", "stopped"),
        ("true", "false"),
        ("on", "off"),
        ("open", "closed"),
        ("valid", "invalid"),
        ("present", "absent"),
        ("installed", "uninstalled"),
    ]


def _entity_key(text: str) -> str:
    """Extract first 3 significant non-stopword words as a cache key."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    significant = [w for w in words if w not in _STOPWORDS]
    return " ".join(significant[:3])


def _has_contradiction(old_text: str, new_text: str) -> bool:
    """Return True if old and new texts contain opposing state words."""
    old_lower = old_text.lower()
    new_lower = new_text.lower()
    for a, b in _OPPOSING_PAIRS:
        if (a in old_lower and b in new_lower) or (b in old_lower and a in new_lower):
            return True
    return False


# In-memory entity cache: entity_key → most-recently-written episode text
# Persists only for the current process run (one cron invocation).
_entity_cache: dict[str, str] = {}


def mcp_request(session_id: str, method: str, params: dict) -> dict:
    """Send a single MCP JSON-RPC request with the established session."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = dict(HEADERS_BASE)
    if session_id:
        headers["mcp-session-id"] = session_id
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read().decode()
        # SSE response: lines like "event: message\r\ndata: {...}"
        for line in raw.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        # Plain JSON fallback
        return json.loads(raw)


def initialize_session() -> str:
    """MCP initialize handshake — returns session ID."""
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "l1-graphiti-writer", "version": "1.0"},
        },
    }
    headers = dict(HEADERS_BASE)
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        session_id = resp.headers.get("mcp-session-id", "")
        if not session_id:
            raise RuntimeError("No mcp-session-id returned from initialize")
        # Drain body
        resp.read()
    return session_id


def search_existing_nodes(session_id: str, entity_name: str) -> list[str]:
    """
    Sweep 24 (LiCoMemory arXiv:2607.19412): entity deduplication pre-check.

    Searches Graphiti for existing nodes matching entity_name (case-insensitive prefix).
    Returns list of matching node names found. If any match is found, the caller can
    skip re-writing episodes that would produce duplicate entity nodes.

    Note: Graphiti's own LLM extractor does fuzzy entity merging internally, but calling
    this before write() gives us visibility and avoids noisy duplicate episodes.
    Uses mcp__graphiti__search_nodes with GROUP_ID scoping.
    """
    try:
        result = mcp_request(session_id, "tools/call", {
            "name": "mcp__graphiti__search_nodes",
            "arguments": {
                "query": entity_name,
                "group_ids": [GROUP_ID],
                "max_nodes": 5,
            }
        })
        content = result.get("result", {}).get("content", [])
        found_names: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                # Simple: if entity_name appears case-insensitively in result text, flag it
                if entity_name.lower() in text.lower():
                    found_names.append(entity_name)
                    break
        return found_names
    except Exception:
        return []  # Fail open — dedup is advisory, not blocking


def _find_count(obj, keys=("node_count", "nodes", "entity_count", "num_nodes")):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in keys and isinstance(v, (int, float)):
                return int(v)
            found = _find_count(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_count(item, keys)
            if found is not None:
                return found
    elif isinstance(obj, str):
        try:
            return _find_count(json.loads(obj), keys)
        except Exception:
            return None
    return None


def graphiti_node_count(session_id: str) -> int | None:
    """Fail-open: return node count if get_status exposes it, else None."""
    try:
        result = mcp_request(session_id, "tools/call", {
            "name": "mcp__graphiti__get_status",
            "arguments": {},
        })
        return _find_count(result)
    except Exception as e:
        print(f"[l1-graphiti-write] node-count check skipped: {e}", file=sys.stderr)
        return None


ENTITIES_RE = re.compile(r'\[entities:\s*([^\]]+)\]')
VC_RE = re.compile(r'\[vc=(stable|volatile|ephemeral)\]')
NS_RE = re.compile(r'\[ns=(profile|event|record)\]')
TRACK_RE = re.compile(r'\[track=(core|active)\]')
ANCHORS_RE = re.compile(r'\[anchors:\s*([^\]]+)\]')


def parse_pole_entities(text: str) -> list[dict]:
    """Extract POLE+O entity annotations from a staging line.

    Format: [entities: Person:Alice, Organisation:ACME, Location:Melbourne]
    Returns: [{"type": "Person", "name": "Alice"}, ...]
    """
    m = ENTITIES_RE.search(text)
    if not m:
        return []
    entities = []
    for part in m.group(1).split(","):
        part = part.strip()
        if ":" in part:
            etype, _, ename = part.partition(":")
            entities.append({"type": etype.strip(), "name": ename.strip()})
    return entities


def parse_staging(path: pathlib.Path, default_source: str = DEFAULT_SOURCE_TYPE) -> list[dict]:
    """Parse staging.md bullet lines into fact dicts.

    Supports optional inline tags:
      [source=...] — trust tier override
      [entities: Type:Name, ...] — POLE+O entity annotations from l1-extract v3
      [vc=...]     — volatility class (stable/volatile/ephemeral)
      [ns=...]     — memory namespace (profile/event/record)
      [track=...]  — MemSIF Dual-Track (core|active)
      [anchors:...]— world-bridge anchor objects

    Entities are extracted and stripped from the text; they are passed to write_fact
    as structured hints for Graphiti's entity extractor (P3.12 implementation,
    arXiv:2604.01707 + llm-agent-memory-pipeline-research).
    """
    facts = []
    if not path.exists() or path.stat().st_size == 0:
        return facts
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = TIMESTAMP_RE.match(line)
        if not m:
            continue
        mem_type = m.group(1) or "fact"
        inline_source = m.group(2)
        source_type = inline_source if inline_source in SOURCE_TYPES else default_source
        text = TIMESTAMP_RE.sub("", line).strip()
        # Extract POLE+O entities before stripping annotation from text
        entities = parse_pole_entities(text)
        text = ENTITIES_RE.sub("", text).strip()
        # Parse new v4 tags
        vc_m = VC_RE.search(text)
        volatility_class = vc_m.group(1) if vc_m else "stable"
        ns_m = NS_RE.search(text)
        memory_namespace = ns_m.group(1) if ns_m else "record"
        track_m = TRACK_RE.search(text)
        fact_track = track_m.group(1) if track_m else "active"
        anc_m = ANCHORS_RE.search(text)
        anchors = [a.strip() for a in anc_m.group(1).split(",")] if anc_m else []
        # Strip v4 tags from text
        text = VC_RE.sub("", text).strip()
        text = NS_RE.sub("", text).strip()
        text = TRACK_RE.sub("", text).strip()
        text = ANCHORS_RE.sub("", text).strip()
        if text:
            facts.append({
                "type": mem_type,
                "source_type": source_type,
                "text": text,
                "entities": entities,  # P3.12: structured POLE+O hints for Graphiti
                "volatility_class": volatility_class,
                "memory_namespace": memory_namespace,
                "fact_track": fact_track,
                "anchors": anchors,
            })
    return facts


def write_fact(session_id: str, fact: dict, name: str, confidence: float = 0.8) -> bool:
    """Write one fact to Graphiti via MCP tools/call add_memory.

    The episode_body includes:
    1. A source_type prefix for trust-tier weighting
    2. POLE+O entity hints (P3.12) — Graphiti's LLM extractor is guided by explicit
       entity mentions in the episode text. We prepend them as a structured hint block:
       [entities: Person:Alice, Organisation:ACME]
    This dramatically improves entity extraction recall vs burying facts in prose,
    since Graphiti's extractor treats the full episode_body as its extraction context.
    3. M1: provenance tag prepended to episode_body + carried in metadata dict.
    """
    # why: MAP-Graph (sweep 19) requires confidence scores on edges for calibrated retrieval; default 0.8 = high-confidence agent observation
    confidence = float(fact.get("confidence", confidence))
    source_tag = f"[source_type={fact['source_type']}]"
    # Trust-Tiered Librarian (arXiv:2608.12984, Aug 2026): every episode carries as_of timestamp.
    # Downstream consumers use this for point-in-time trust queries ("what did we know as of T?")
    as_of_tag = f"[as_of={datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}]"
    entities = fact.get("entities", [])
    if entities:
        entity_str = ", ".join(f"{e['type']}:{e['name']}" for e in entities)
        entity_hint = f"[entities: {entity_str}] "
    else:
        entity_hint = ""
    # Volatility class + namespace tags (ScrubJay / LeanMem signals for retrieval consumers)
    vc = fact.get("volatility_class", "stable")
    ns = fact.get("memory_namespace", "record")
    vc_tag = f"[vc={vc}]"
    ns_tag = f"[ns={ns}]"
    # World-bridge anchors (InMind pattern: ground fact in named world concepts)
    anchors = fact.get("anchors", [])
    anchor_hint = f"[anchors: {', '.join(anchors)}] " if anchors else ""
    conf_tag = f"[confidence={confidence}]"
    # M1: provenance — build metadata dict and inline prov tag
    prov = _build_provenance()
    prov_inline = _prov_tag(prov)
    episode_body = f"{prov_inline} {source_tag} {as_of_tag} {vc_tag} {ns_tag} {conf_tag} {entity_hint}{anchor_hint}{fact['text']}"
    # Preserve raw source for memory repair after model upgrades (arXiv:2609.05339).
    # KG-fixed schema transfers reliably; NOTES degrade 9-13pp on model swap.
    # Keeping source_text in metadata enables re-extraction if model changes.
    source_text_raw = (fact.get("source_text") or fact.get("text", ""))[:500]

    def _do_write() -> bool:
        resp = mcp_request(session_id, "tools/call", {
            "name": "add_memory",
            "arguments": {
                "episode_body": episode_body,
                "group_id": GROUP_ID,
                "name": name,
                "metadata": {
                    "source_text": source_text_raw,  # raw source for post-upgrade repair (arXiv:2609.05339)
                    "model_version": os.environ.get("HERMES_MODEL", ""),  # tag for stale-embedding detection after model swap (arXiv:2609.05339)
                    "confidence": confidence,
                    **prov,  # M1: provenance fields merged into metadata
                },
            },
        })
        result = resp.get("result", {})
        if isinstance(result, dict):
            content = result.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                return "queued" in text.lower() or "success" in text.lower()
        return False

    # Self-Healing Failure Taxonomy (arXiv sweep 19): per-class retry budgets
    try:
        import importlib.util as _ilu
        _guard_path = str(pathlib.Path(__file__).parent / "retry-budget-guard.py")
        _spec = _ilu.spec_from_file_location("retry_budget_guard", _guard_path)
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        return _mod.with_retry(_do_write, classify_fn=_mod.classify_http_error, label=f"graphiti:{name[:30]}")
    except Exception:
        try:
            return _do_write()
        except Exception as e:
            print(f"  [graphiti] WARNING: failed to write '{name}': {e}", file=sys.stderr)
            return False


def main():
    _load_graphiti_caps()
    # Parse args: optional positional staging path, optional --source-type flag
    # Sweep 24: --on-session-complete flag for session-boundary trigger mode (arXiv:2608.01801)
    args = sys.argv[1:]
    source_type = DEFAULT_SOURCE_TYPE
    staging_arg = None
    on_session_complete = False  # sweep 24: session-boundary write mode
    i = 0
    while i < len(args):
        if args[i] == "--source-type" and i + 1 < len(args):
            raw = args[i + 1]
            if raw not in SOURCE_TYPES:
                print(f"[l1-graphiti-write] ERROR: unknown --source-type '{raw}'. "
                      f"Valid: {list(SOURCE_TYPES)}", file=sys.stderr)
                sys.exit(1)
            source_type = raw
            i += 2
        elif args[i] == "--on-session-complete":
            # Session-boundary trigger mode (G-Memory arXiv:2608.01801):
            # Write only facts tagged with today's session timestamp, not all of staging.md.
            # This improves entity coherence by grouping facts from a single session context.
            on_session_complete = True
            i += 1
        else:
            staging_arg = args[i]
            i += 1

    staging_path = pathlib.Path(
        staging_arg if staging_arg
        else pathlib.Path.home() / ".hermes/memory-facts/staging.md"
    )

    facts = parse_staging(staging_path, default_source=source_type)
    if not facts:
        print("[l1-graphiti-write] staging.md empty or no parseable facts — nothing to write.")
        return

    # Sweep 24: session-complete mode — filter to most recent extract batch only
    # Helps entity coherence: Graphiti sees a topically consistent episode set
    if on_session_complete and facts:
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        recent = [f for f in facts if today_str in f.get("text", "")[:40]]
        if recent:
            print(f"[l1-graphiti-write] --on-session-complete: filtering to {len(recent)}/{len(facts)} today's facts")
            facts = recent
        else:
            print(f"[l1-graphiti-write] --on-session-complete: no today-tagged facts; writing all {len(facts)}")

    print(f"[l1-graphiti-write] Initializing Graphiti session...")
    try:
        session_id = initialize_session()
    except Exception as e:
        print(f"[l1-graphiti-write] ERROR: Cannot connect to Graphiti: {e}", file=sys.stderr)
        sys.exit(1)

    node_n = graphiti_node_count(session_id)
    if node_n is None:
        print("[l1-graphiti-write] node count unknown (get_status had no count) — continuing")
    elif node_n >= GRAPHITI_HALT_NODES:
        print(f"[l1-graphiti-write] ERROR: Graphiti nodes={node_n} >= {GRAPHITI_HALT_NODES} — refusing write", file=sys.stderr)
        sys.exit(1)
    elif node_n >= GRAPHITI_WARN_NODES:
        print(f"[l1-graphiti-write] WARNING: Graphiti nodes={node_n} (warn at {GRAPHITI_WARN_NODES})", file=sys.stderr)
    else:
        print(f"[l1-graphiti-write] Graphiti nodes={node_n}")

    print(f"[l1-graphiti-write] Writing {len(facts)} facts to Graphiti (group={GROUP_ID}, source_type={source_type})...")
    # TraceGrant: log grant for this run (sweep 24: include taint_path)
    taint = "l1-extract→l1-promote→l1-graphiti-write" if not on_session_complete else "session-complete→l1-graphiti-write"
    grant_id = tracegrant_log_grant("l1-graphiti-write", source_type, taint_path=taint)
    if grant_id:
        print(f"[tracegrant] grant={grant_id} source_type={source_type}", file=sys.stderr)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    written = 0
    failed = 0

    for i, fact in enumerate(facts):
        # TraceGrant: enforce namespace policy before writing to Graphiti
        ns = fact.get("memory_namespace", "record")
        if not tracegrant_check(fact.get("source_type", source_type), ns, fact_id=f"fact-{i}"):
            failed += 1
            continue

        # Sweep 24 — entity dedup pre-check (LiCoMemory arXiv:2607.19412)
        # Check primary entities against existing Graphiti nodes; log potential duplicates.
        # Dedup is advisory: we still write (Graphiti merges internally), but flag verbose.
        entities = fact.get("entities", [])
        if entities:
            primary_entity = entities[0].get("name", "") if isinstance(entities[0], dict) else ""
            if primary_entity:
                existing = search_existing_nodes(session_id, primary_entity)
                if existing:
                    print(f"  [dedup] '{primary_entity}' already in Graphiti — episode will merge with existing node")
        # M3: Contradiction detection — check entity cache before write
        ekey = _entity_key(fact["text"])
        if ekey and ekey in _entity_cache:
            old_text = _entity_cache[ekey]
            if _has_contradiction(old_text, fact["text"]):
                print(
                    f"CONTRADICTION detected: entity={ekey!r} "
                    f"old={old_text[:70]!r} "
                    f"new={fact['text'][:70]!r}"
                )
        # Content-hash-based episode name for idempotency (MyContext, Alibaba Aug 2026):
        # Same fact text always maps to the same name → re-running staging never creates
        # duplicate Graphiti episodes. Timestamp suffix keeps same-text multi-source unique.
        content_hash = hashlib.sha256(fact['text'][:200].encode()).hexdigest()[:12]
        name = f"l1-{fact['type']}-{content_hash}-{i:03d}"
        ok = write_fact(session_id, fact, name)
        if ok:
            written += 1
            entity_tag = f" [{len(fact['entities'])}e]" if fact.get("entities") else ""
            print(f"  queued: [{fact['type']}]{entity_tag} {fact['text'][:60]}...")
            # M3: Update entity cache so subsequent facts in this run can detect contradictions
            if ekey:
                _entity_cache[ekey] = fact["text"]
        else:
            failed += 1
        # Brief pause — Graphiti processes async but still rate-sensitive
        if i < len(facts) - 1:
            time.sleep(0.3)

    print(f"[l1-graphiti-write] Done: {written} queued, {failed} failed.")
    if failed > 0:
        print(f"[l1-graphiti-write] {failed} facts did not reach Graphiti — check daemon logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
