#!/usr/bin/env python3
"""
unified-recall.py — Execute a memory query against both Hindsight and Graphiti,
fuse results, and return a ranked deduplicated list.

Usage:
  python3 unified-recall.py "query text" [--top N] [--json] [--min-score 0.5]
  python3 unified-recall.py "query text" --tier l0          # abstract screening (1 sentence)
  python3 unified-recall.py "query text" --tier l1          # excerpt mode (~200 chars)
  python3 unified-recall.py "query text" --tier l2          # full text (default)
  python3 unified-recall.py "query text" --screen           # alias for --tier l0 --top 20
  python3 unified-recall.py "query text" --promote 1,3,5    # expand specific L0 results to L2

Returns ranked results from:
  1. Hindsight (vector similarity via REST API)
  2. Graphiti (entity facts + nodes via MCP)

Fusion: Reciprocal Rank Fusion (RRF) with adaptive specificity weighting.
Dedup: MD5 of normalized text to prevent duplicate facts across sources.

Tiered output (inspired by OpenViking L0/L1/L2):
  L0 (~15-20 tokens) — 1-sentence abstract for screening; no detail
  L1 (~200 chars)    — excerpt with source attribution
  L2 (full)          — complete text (original behaviour)

Note: --promote ALWAYS expands to L2 (full text), regardless of --tier.
      --tier only affects non-promoted results.

Observable trajectory: each result carries a 'path' field showing which
sources contributed and at what ranks. To interpret: item score = sum of
each path entry's rrf value (before normalization).

Exit codes:
  0 — results found and printed
  1 — no results (both sources returned empty)
  2 — argument error
  3 — both sources failed with errors (service down)

This script is callable standalone or imported as a module.
"""

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://127.0.0.1:9177")
HINDSIGHT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes-default")

import os as _os_env

def _hermes_root() -> 'Path':
    """Profile-aware Hermes root: HERMES_HOME env var or ~/.hermes fallback."""
    _h = _os_env.environ.get('HERMES_HOME', '').strip()
    return Path(_h) if _h else Path.home() / '.hermes'


GRAPHITI_BASE = os.environ.get("GRAPHITI_BASE", "http://127.0.0.1:8765/mcp")
GRAPHITI_GROUP_IDS = ["hermes", "hermes-reasoning"]
RRF_K = 60
GRAPHITI_TIMEOUT = 30
HINDSIGHT_TIMEOUT = 15
DEFAULT_TOP = 10

# L0/L1/L2 thresholds
L0_MAX_CHARS = 80    # ~1 sentence / ~15-20 tokens
L1_MAX_CHARS = 200   # excerpt
# L2 = full text, no truncation


# ---------------------------------------------------------------------------
# Tiered text rendering
# ---------------------------------------------------------------------------

def _as_l0(text: str) -> str:
    """Return a 1-sentence abstract (first sentence, capped at L0_MAX_CHARS)."""
    sentence_end = re.search(r"[.!?]", text)
    if sentence_end:
        candidate = text[:sentence_end.start() + 1].strip()
        # Reject degenerate candidates that are just punctuation (e.g. input starts with ".")
        if len(candidate) <= 1:
            candidate = text.strip()
    else:
        candidate = text.strip()
    if len(candidate) > L0_MAX_CHARS:
        candidate = candidate[:L0_MAX_CHARS - 1] + "…"
    return candidate


def _as_l1(text: str) -> str:
    """Return a medium excerpt capped at L1_MAX_CHARS."""
    text = text.strip()
    if len(text) > L1_MAX_CHARS:
        return text[:L1_MAX_CHARS - 1] + "…"
    return text


def apply_tier(text: str, tier: str) -> str:
    if tier == "l0":
        return _as_l0(text)
    elif tier == "l1":
        return _as_l1(text)
    else:  # l2
        return text


def get_injection_tier(recent_tool_errors: int) -> str:
    """AMD injection gating (s19-amd, arXiv:2608.07169).

    L0/L1/L2 in this script are currently *display* tiers (truncate recalled
    text). AMD says injection policy should escalate with tool-error events:
    stay cheap until errors prove the agent needs more memory.

    0 errors -> L0 (only skill_view results)
    1-2 errors -> L1 (skill + hindsight_recall)
    >=3 errors -> L2 (full unified recall)

    This function is the policy hook; callers decide whether to invoke
    skill_view / hindsight / this script. Display --tier remains independent.
    """
    n = int(recent_tool_errors or 0)
    if n <= 0:
        return "L0"
    if n <= 2:
        return "L1"
    return "L2"


# ---------------------------------------------------------------------------
# Hindsight retrieval
# ---------------------------------------------------------------------------

def hindsight_search(query: str, limit: int = 20) -> tuple[list[dict], bool]:
    """Query Hindsight vector store. Returns (results, had_error)."""
    try:
        url = f"{HINDSIGHT_BASE}/v1/default/banks/{HINDSIGHT_BANK}/memories/recall"
        payload = json.dumps({"query": query, "top_k": limit}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=HINDSIGHT_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for rank, item in enumerate(data.get("results", [])):
            text = item.get("text", "")
            # Use actual score if provided; fall back to 0.8
            score = item.get("score", item.get("relevance_score", 0.8))
            if text:
                results.append({
                    "text": text.strip(),
                    "score": float(score),
                    "source": "hindsight",
                    "_raw_rank": rank,
                })
        return results, False
    except Exception as e:
        print(f"[unified-recall] Hindsight error: {e}", file=sys.stderr)
        return [], True


# ---------------------------------------------------------------------------
# Graphiti retrieval via MCP
# ---------------------------------------------------------------------------

HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _graphiti_session() -> str:
    """MCP initialize — returns session ID."""
    payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "unified-recall", "version": "1.0"},
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=dict(HEADERS_BASE), method="POST")
    with urllib.request.urlopen(req, timeout=GRAPHITI_TIMEOUT) as resp:
        session_id = resp.headers.get("mcp-session-id", "")
        resp.read()
    return session_id


def _graphiti_call(session_id: str, tool: str, arguments: dict) -> dict:
    """Call a Graphiti MCP tool. Returns the parsed result dict."""
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    headers = dict(HEADERS_BASE)
    if session_id:
        headers["mcp-session-id"] = session_id
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=GRAPHITI_TIMEOUT) as resp:
        raw = resp.read().decode()
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw)


def graphiti_search(query: str, limit: int = 20) -> tuple[list[dict], bool]:
    """Query Graphiti for facts and nodes. Returns (results, had_error)."""
    try:
        session_id = _graphiti_session()
    except Exception as e:
        print(f"[unified-recall] Graphiti connect error: {e}", file=sys.stderr)
        return [], True

    results = []
    had_error = False

    # Search facts (edges)
    try:
        resp = _graphiti_call(session_id, "search_memory_facts", {
            "query": query,
            "group_ids": GRAPHITI_GROUP_IDS,
            "max_facts": limit,
        })
        raw = resp.get("result", {})
        content = raw.get("content", []) if isinstance(raw, dict) else []
        for rank, item in enumerate(content):
            if isinstance(item, dict):
                text = item.get("text", "")
                if text.strip().startswith("{"):
                    try:
                        inner = json.loads(text)
                        facts = inner.get("facts", [])
                        for fi, fact in enumerate(facts):
                            fact_text = fact.get("fact", "")
                            if fact_text:
                                results.append({
                                    "text": fact_text.strip(),
                                    "score": float(fact.get("score", 0.75)),
                                    "source": "graphiti-facts",
                                    "_raw_rank": rank * 10 + fi,
                                })
                        continue
                    except json.JSONDecodeError:
                        continue  # skip unparseable JSON blobs; don't surface raw JSON as text
                if text and text != "No relevant facts found.":
                    results.append({
                        "text": text.strip(),
                        "score": 0.75,
                        "source": "graphiti-facts",
                        "_raw_rank": rank,
                    })
    except Exception as e:
        print(f"[unified-recall] Graphiti facts error: {e}", file=sys.stderr)
        had_error = True

    # Search nodes (entities)
    try:
        resp = _graphiti_call(session_id, "search_nodes", {
            "query": query,
            "group_ids": GRAPHITI_GROUP_IDS,
            "limit": min(limit // 2, 10),
        })
        raw = resp.get("result", {})
        content = raw.get("content", []) if isinstance(raw, dict) else []
        for rank, item in enumerate(content):
            if isinstance(item, dict):
                text = item.get("text", "")
                if text.strip().startswith("{"):
                    try:
                        inner = json.loads(text)
                        nodes = inner.get("nodes", [])
                        for ni, node in enumerate(nodes):
                            name = node.get("name", "")
                            summary = node.get("summary", "")
                            if name and summary:
                                node_text = f"{name}: {summary}"
                                results.append({
                                    "text": node_text.strip(),
                                    "score": 0.65,
                                    "source": "graphiti-nodes",
                                    "_raw_rank": rank * 10 + ni,
                                })
                        continue
                    except json.JSONDecodeError:
                        continue  # skip unparseable JSON blobs
                if text and "No relevant" not in text:
                    results.append({
                        "text": text.strip(),
                        "score": 0.65,
                        "source": "graphiti-nodes",
                        "_raw_rank": rank,
                    })
    except Exception as e:
        print(f"[unified-recall] Graphiti nodes error: {e}", file=sys.stderr)
        had_error = True

    return results, had_error


# ---------------------------------------------------------------------------
# Fusion: Adaptive RRF with specificity weighting
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize text for dedup."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _md5(text: str) -> str:
    return hashlib.md5(_normalize(text).encode()).hexdigest()


FTRL_STATE_PATH = _hermes_root() / "cache" / "recall-ftrl-state.json"


# --- UCB1 Bandit Source Weighting (Lattimore & Szepesvari, Ch 1) ---
# Replaces fixed RRF k=60 equal weights with adaptive UCB1-weighted fusion.
_BANDIT_STATE_PATH = Path('~/.hermes/cache/recall-bandit-state.json').expanduser()

def _load_bandit_state():
    try:
        if _BANDIT_STATE_PATH.exists():
            import json as _json
            return _json.loads(_BANDIT_STATE_PATH.read_text())
    except Exception:
        pass
    return {'hindsight': {'n': 0, 'reward': 0.0}, 'graphiti': {'n': 0, 'reward': 0.0}, 'l1': {'n': 0, 'reward': 0.0}}

def _ucb1_weight(source, state, t):
    try:
        import math
        s = state.get(source, {'n': 0, 'reward': 0.0})
        if s['n'] == 0 or t == 0:
            return 1.5  # explore with bonus
        mu = s['reward'] / s['n']
        return mu + math.sqrt(2 * math.log(max(t, 1)) / s['n'])
    except Exception:
        return 1.0

def _update_bandit_state(source, reward):
    try:
        import json as _json
        state = _load_bandit_state()
        if source not in state:
            state[source] = {'n': 0, 'reward': 0.0}
        state[source]['n'] += 1
        state[source]['reward'] += float(reward)
        _BANDIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _bandit_tmp = _BANDIT_STATE_PATH.with_suffix(".tmp")
        _bandit_tmp.write_text(_json.dumps(state, indent=2))
        _bandit_tmp.replace(_BANDIT_STATE_PATH)
    except Exception as _bandit_exc:
        import sys as _sys_b
        print(f"[unified-recall] bandit state write failed: {_bandit_exc!r}", file=_sys_b.stderr)


def load_ftrl_weights(query_type):
    """Load FTRL-learned (hindsight_weight, graphiti_weight) for query_type.
    Source: online_learning primer (FTRL/Hedge on 2-expert mixture).
    Returns (None, None) during cold-start (< 5 updates).
    """
    if not FTRL_STATE_PATH.exists():
        return None, None
    try:
        state = json.loads(FTRL_STATE_PATH.read_text())
        entry = state.get(query_type, {})
        if entry.get("n_updates", 0) < 5:
            return None, None
        hw = entry.get("hindsight_weight")
        gw = entry.get("graphiti_weight")
        if hw is not None and gw is not None:
            return float(hw), float(gw)
    except Exception:
        pass
    return None, None


def log_recall_query(query, sources_used, query_type):
    """Append recall event for FTRL weight learning by nightly cron."""
    import time as _t
    log_path = _hermes_root() / "cache" / "recall-query-log.jsonl"
    try:
        entry = {
            "ts": _t.time(),
            "query_type": query_type,
            "sources_used": sources_used,
            "query_len": len(query.split()),
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _log_lock = log_path.with_suffix(".lock")
        with open(_log_lock, "w") as _lf:
            fcntl.flock(_lf, fcntl.LOCK_EX)
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# H4 fix: import tool-auth-shim for EXTERNAL result auditing (module-level, once at startup)
try:
    import importlib.util as _ilu2
    _ta_spec = _ilu2.spec_from_file_location('tool_auth_shim',
                   str(Path('~/.hermes/scripts/tool-auth-shim.py').expanduser()))
    assert _ta_spec is not None
    _ta2 = _ilu2.module_from_spec(_ta_spec)
    _ta_spec.loader.exec_module(_ta2)  # type: ignore[union-attr]
except Exception:
    _ta2 = None


def fuse_results(
    hindsight_results: list[dict],
    graphiti_results: list[dict],
    query: str,
    top: int = DEFAULT_TOP,
    min_score: float = 0.0,
) -> list[dict]:
    """
    Reciprocal Rank Fusion over two ranked lists.

    Specificity weighting: for specific queries (many long terms), Graphiti
    (entity/keyword source) gets higher weight; for generic queries (few or short terms),
    Hindsight (vector source) gets higher weight. This is a heuristic, not true IDF.

    RDM (Relevance Decay Multiplier): items tagged with [vc=ephemeral] or [vc=volatile]
    receive a decay penalty to deprioritise stale context (NECROPHORESIS, arXiv:2608.07440).
    stable items are unaffected.

    Each result carries a 'path' field for observable trajectory.
    The item's final score = sum(path[i].rrf) / max_sum (normalized to [0,1]).

    RANK NOT CUTOFF (Habr RU, Aug 2026): cosine similarity between unrelated memory
    pairs averages 0.53; neighbors average 0.80 — the distributions overlap (p95 random
    can exceed p5 neighbor). Never filter on absolute cosine. Use rank (RRF, top-k)
    only. The dedup gate is the only valid absolute-cosine site (cosine+NLI two-gate).
    """
    # Relevance Decay Multipliers per volatility class (NECROPHORESIS pattern)
    RDM = {"ephemeral": 0.40, "volatile": 0.75, "stable": 1.0}

    query_terms = query.lower().split()
    specific_terms = [t for t in query_terms if len(t) > 5]
    # graphiti_weight grows with query specificity (more specific → more entity-match signal)
    graphiti_weight = min(0.7, 0.3 + len(specific_terms) * 0.08)

    # GraphMemix query-type routing (arXiv:2608.26983): structural vs episodic
    # Structural queries (what is, define, relate, connect) → heavier Graphiti
    # Episodic queries (what happened, when, which session) → heavier Hindsight
    _q_lower = query.lower()
    _structural = any(tok in _q_lower for tok in [
        "what is", "define", "relation", "connect", "depend", "structure", "how does", "schema"
    ])
    _episodic = any(tok in _q_lower for tok in [
        "when", "which session", "last time", "what happened", "remember", "told me", "said"
    ])
    if _structural and not _episodic:
        graphiti_weight = min(0.80, graphiti_weight + 0.15)
    elif _episodic and not _structural:
        graphiti_weight = max(0.20, graphiti_weight - 0.15)

    _q_type = "structural" if _structural else ("episodic" if _episodic else "general")
    _hw_ftrl, _gw_ftrl = load_ftrl_weights(_q_type)
    if _hw_ftrl is not None:
        hindsight_weight = _hw_ftrl
        graphiti_weight = _gw_ftrl
    else:
        hindsight_weight = 1.0 - graphiti_weight

    scores: dict[str, float] = {}
    texts: dict[str, str] = {}
    full_texts: dict[str, str] = {}  # always store full text for L2 promotion
    sources: dict[str, list[str]] = {}
    # trajectory: {key: [{source, rank, rrf_contribution}]}
    # Note: item.rrf_score = sum(path[i].rrf) / normalization_constant
    trajectory: dict[str, list[dict]] = {}

    def add_results(results: list[dict], weight: float):
        for rank, item in enumerate(results):
            key = _md5(item["text"])
            rrf_contrib = weight * (1.0 / (RRF_K + rank + 1))
            # RDM: apply volatility-class decay to deprioritise stale context
            # Parse [vc=X] tag from item text if present
            vc_match = re.search(r'\[vc=(ephemeral|volatile|stable)\]', item.get("text", ""))
            rdm = RDM.get(vc_match.group(1) if vc_match else "stable", 1.0)
            rrf_contrib *= rdm
            scores[key] = scores.get(key, 0.0) + rrf_contrib
            if key not in texts:
                texts[key] = item["text"]
                full_texts[key] = item["text"]
            src = item.get("source", "unknown")
            sources.setdefault(key, [])
            if src not in sources[key]:
                sources[key].append(src)
            trajectory.setdefault(key, [])
            trajectory[key].append({
                "source": src,
                "rank": rank,
                "rrf": round(rrf_contrib, 5),
            })

    # UCB1 bandit source weighting (Lattimore & Szepesvari, Ch 1):
    # Multiply existing specificity/FTRL weights by UCB1 confidence index.
    # _bandit_state tracks {source: {n, reward}} across queries.
    # Feedback loop: _update_bandit_state() called after fuse_results() (H1 fix, ~line 600).
    _bandit_state = _load_bandit_state()
    _t_bandit = sum(s.get('n', 0) for s in _bandit_state.values())
    _ucb_h = _ucb1_weight('hindsight', _bandit_state, _t_bandit)
    _ucb_g = _ucb1_weight('graphiti', _bandit_state, _t_bandit)
    add_results(hindsight_results, (hindsight_weight or 1.0) * _ucb_h)
    add_results(graphiti_results, (graphiti_weight or 1.0) * _ucb_g)

    # Normalize to [0, 1] range
    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

    fused = []
    for key, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        if score >= min_score:
            fused.append({
                "text": texts[key],
                "_full_text": full_texts[key],
                "rrf_score": round(score, 4),
                "sources": sources[key],
                "path": trajectory[key],
            })

    # Provenance trust weighting (arXiv:2606.04990): internal facts outrank external on equal RRF
    # Trust tiers map to source_type metadata set by l1-graphiti-write.py.
    # source field values: 'hindsight', 'graphiti-facts', 'graphiti-nodes', 'lifecycle-pending'
    # source_type in metadata: 'internal' (1.0), 'cron' (0.85), 'external' (0.70); default 1.0
    #
    # Robust Trust probabilistic interpretation (arXiv:2602.09490):
    # Each weight is the alignment probability p for that source class.
    # With probability p the adviser (source) is truthful; with (1-p) it can manipulate.
    # The optimal decision rule clips the adviser's recommendation to a trust region of
    # radius proportional to (1-p)/p (i.e. the weight acts as an upper bound / clip value).
    #   internal: p=1.0  — fully aligned, no clipping needed; trust region radius = ∞
    #   cron:     p=0.85 — ~15% chance of drift; trust-region radius = 0.85/0.15 = 5.7 — weight capped at 0.85
    #   external: p=0.70 — ~30% adversarial mass; trust-region radius = 0.70/0.30 = 2.3 — weight capped at 0.70
    # Robust Trust clipping (arXiv:2602.09490): weight = p/(1+(1-p)) ≈ p for small (1-p)
    _TRUST_WEIGHTS = {"internal": 1.0, "cron": 0.85, "external": 0.70}
    # H3 fix: try to pull live Beta-posterior trust weights from memory-provenance.py
    try:
        import importlib.util as _ilu
        _mp_spec = _ilu.spec_from_file_location('memory_provenance',
                       str(Path('~/.hermes/scripts/memory-provenance.py').expanduser()))
        assert _mp_spec is not None
        _mp = _ilu.module_from_spec(_mp_spec)
        _mp_spec.loader.exec_module(_mp)  # type: ignore[union-attr]
        for _st in ('internal', 'cron', 'external'):
            _TRUST_WEIGHTS[_st] = _mp.get_trust_weight(_st)
    except Exception as _mp_exc:
        import sys as _sys_mp
        print(f"[unified-recall] memory-provenance load failed: {_mp_exc!r} — using static trust weights", file=_sys_mp.stderr)
    # H4 fix: _ta2 is now imported at module level (see above fuse_results definition)

    # EnrichedHom scoring (category theory Tier 1b — arXiv:1102.1889 / memory-monad.py)
    # Enrich over [0,1] × [0,∞]: weight = rrf_score × exp(-decay_rate × age_days)
    import math as _math, time as _time
    _now = _time.time()
    _decay_rate = 0.02  # half-life ≈ 35 days
    for item in fused:
        _created = item.get("created_at") or item.get("timestamp") or ""
        try:
            if isinstance(_created, (int, float)):
                _age_days = (_now - float(_created)) / 86400.0
            elif _created:
                from datetime import datetime, timezone as _tz
                _ts = datetime.fromisoformat(_created.replace("Z", "+00:00")).timestamp()
                _age_days = (_now - _ts) / 86400.0
            else:
                _age_days = 30.0
        except Exception:
            _age_days = 30.0
        _decay = _math.exp(-_decay_rate * max(0.0, _age_days))
        # Apply provenance trust weight: read source_type from metadata if present, else 1.0
        _meta = item.get("metadata")
        _source_type = _meta.get("source_type") if isinstance(_meta, dict) else None
        _trust_weight = _TRUST_WEIGHTS.get(_source_type or "", 1.0)
        item["trust_weight"] = _trust_weight
        # H4: run tool-auth-shim audit on EXTERNAL results (shadow, never raises)
        if _source_type == "external" and _ta2 and hasattr(_ta2, "audit_tool_result"):
            try:
                _ta2.audit_tool_result(_source_type or "unknown", "EXTERNAL", item.get("text", "")[:2000])
            except Exception:
                pass
        # Trust-region clip: weight bounded by p-alignment probability (arXiv:2602.09490)
        item["enriched_weight"] = round(item["rrf_score"] * _decay * _trust_weight, 4)
        item["enriched_distance"] = round(1.0 - item["enriched_weight"], 4)
        item["_age_days"] = round(_age_days, 1)

    _src_used = list({s for k in list(scores.keys())[:top] for s in sources.get(k, [])})
    log_recall_query(query, _src_used, _q_type)
    # H1 fix: UCB1 feedback — update bandit state so weights actually learn
    try:
        _bandit_state_w = _load_bandit_state()
        for _item in fused[:top]:
            for _src in _item.get("sources", []):
                # reward = enriched_weight (quality proxy); clipped to [0,1]
                _reward = min(1.0, max(0.0, _item.get("enriched_weight", 0.0)))
                _src_key = "hindsight" if "hindsight" in _src else (
                            "graphiti" if "graphiti" in _src else "l1")
                _update_bandit_state(_src_key, _reward)
    except Exception:
        pass  # shadow: never block recall on bandit update failure
    # H10 fix: update Beta-Binomial trust posterior with recall outcomes (closes bottleneck #7 write path)
    try:
        _mp_ref = locals().get('_mp') or globals().get('_mp')
        if _mp_ref is None:
            import sys as _sys
            print("[unified-recall] trust posterior skipped: memory-provenance import unavailable", file=_sys.stderr)
        elif _mp_ref and hasattr(_mp_ref, 'update_trust_posterior'):
            for _item in fused[:top]:
                _i_meta = _item.get("metadata") or {}
                _src_type = _i_meta.get("source_type") if isinstance(_i_meta, dict) else None
                if _src_type in ("internal", "cron", "external"):
                    _tp_reward = min(1.0, max(0.0, _item.get("enriched_weight", 0.0)))
                    _mp_ref.update_trust_posterior(_src_type, _tp_reward)
    except Exception:
        pass  # shadow: never block recall on trust posterior update

    return sorted(fused, key=lambda x: x.get("enriched_weight", x.get("rrf_score", 0)), reverse=True)[:top]


def seu_filter(
    fused: list[dict],
    query: str,
    interference_threshold: float = 0.25,
) -> list[dict]:
    """
    SEU (Selective Experience Use) filter — arXiv:2608.01149 (Aug 2026).

    Score each retrieved memory item for relevance vs interference risk before
    injecting into context. Admit only items where relevance > interference.

    Relevance proxy: RRF score (already normalized 0-1).
    Interference proxy: heuristic — memories from sources that often produce false
    positives in this query type (graphiti-nodes are broader/fuzzier than graphiti-facts).

    This is a lightweight approximation of the SEU harness concept — a full
    implementation would require per-task-type interference calibration data.
    """
    INTERFERENCE_WEIGHTS = {
        "graphiti-nodes": 0.20,   # broader entity summaries, higher false-positive rate
        "graphiti-facts": 0.10,   # structured facts, lower interference
        "hindsight": 0.05,        # vector-scored, lowest interference for on-topic queries
    }
    filtered = []
    for item in fused:
        relevance = item.get("rrf_score", 0.0)
        # Estimate interference as max interference weight across contributing sources
        sources = item.get("sources", [])
        interference = max((INTERFERENCE_WEIGHTS.get(s, 0.10) for s in sources), default=0.10)
        if relevance > interference + interference_threshold:
            item["_seu_relevance"] = round(relevance, 4)
            item["_seu_interference"] = round(interference, 4)
            filtered.append(item)
    return filtered


def apply_turn_distance_rdm(
    fused: list[dict],
    current_turn: int,
    rdm_lambda: float = 0.05,
) -> list[dict]:
    """
    NECROPHORESIS turn-distance RDM — arXiv:2608.07440 (Aug 2026).

    The existing vc-tag RDM (in fuse_results) handles static volatility class.
    This applies an ADDITIONAL decay based on how many turns ago the memory was
    last accessed — i.e. recency within the current session's interaction history.

    Formula: score *= exp(-rdm_lambda * delta_turns)
    where delta_turns = current_turn - last_accessed_turn

    last_accessed_turn is stored in lifecycle.db (added Aug 2026).
    For memories without a turn record (most existing ones), decay = 0 (no penalty).

    rdm_lambda default 0.05: 20-turn-old memory scores at exp(-1.0) ≈ 0.37× original.
    """
    import math
    for item in fused:
        last_turn = item.get("_last_accessed_turn", current_turn)
        delta = max(0, current_turn - last_turn)
        decay = math.exp(-rdm_lambda * delta)
        item["rrf_score"] = item.get("rrf_score", 0.0) * decay
        item["_turn_rdm_decay"] = round(decay, 4)
        item["_turn_delta"] = delta
    # Re-sort after applying decay
    return sorted(fused, key=lambda x: x.get("rrf_score", 0.0), reverse=True)


# ---------------------------------------------------------------------------
# Promote: expand specific L0 results to L2
# ---------------------------------------------------------------------------

def promote_results(fused: list[dict], indices: list[int]) -> list[dict]:
    """
    Return only the requested items (1-indexed) with full L2 text.
    Always returns L2 regardless of any tier setting — promote means full expansion.
    Safe if _full_text is absent (falls back to text field).
    """
    out = []
    for i in indices:
        if 1 <= i <= len(fused):
            item = dict(fused[i - 1])
            item["text"] = item.get("_full_text", item.get("text", ""))
            item["tier"] = "l2"
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recall(
    query: str,
    top: int = DEFAULT_TOP,
    min_score: float = 0.0,
    tier: str = "l2",
    sources: tuple[str, ...] = ("hindsight", "graphiti"),
    seu: bool = False,
    turn_rdm: bool = False,
    current_turn: int = 0,
    rdm_lambda: float = 0.05,
) -> list[dict]:
    """
    Public API: query both stores, return fused ranked results.
    tier: 'l0' (abstract), 'l1' (excerpt), 'l2' (full, default)
    sources: which backends to use (default: both)
    seu: if True, apply SEU relevance-vs-interference filter before returning
    turn_rdm: if True, apply NECROPHORESIS turn-distance decay (arXiv:2608.07440).
              Pass current_turn (e.g. session turn counter) for accurate delta.
    Raises RuntimeError if all requested backends errored with zero results.
    """
    # Normalize to set to avoid string-membership footgun (e.g. sources="hindsight")
    source_set = set(sources) if not isinstance(sources, str) else {sources}
    h_results, h_err = hindsight_search(query, limit=top * 2) if "hindsight" in source_set else ([], False)
    g_results, g_err = graphiti_search(query, limit=top * 2) if "graphiti" in source_set else ([], False)
    pending = search_pending_activefacts(query)

    if not h_results and not g_results and not pending:
        if h_err and g_err:
            raise RuntimeError("Both memory backends failed — services may be down.")
        return []

    fused = fuse_results(h_results + pending, g_results, query, top=top, min_score=min_score)

    # F-57 invalidation guard: remove any item whose memory_status == 'invalidated'.
    # Fail-open: wrapped in try/except so recall is never blocked by this filter.
    try:
        fused = [item for item in fused if item.get("memory_status") != "invalidated"]
    except Exception as _inv_exc:
        import sys as _sys_inv
        print(f"[unified-recall] invalidation filter skipped: {_inv_exc}", file=_sys_inv.stderr)

    # ContextRAG lattice expansion (arXiv:2605.19735): activate concept bridge nodes
    # query_activate() returns [] when cache absent — safe to call unconditionally
    try:
        import importlib.util as _ilu, sys as _sys
        _cli_path = str(Path(__file__).parent / "concept-lattice-index.py")
        if "concept-lattice-index" not in _sys.modules:
            _spec = _ilu.spec_from_file_location("concept-lattice-index", _cli_path)
            if _spec is None or _spec.loader is None:
                raise ImportError("concept-lattice-index spec unavailable")
            _cli_mod = _ilu.module_from_spec(_spec)
            _sys.modules["concept-lattice-index"] = _cli_mod
            _spec.loader.exec_module(_cli_mod)  # type: ignore[union-attr]
        else:
            _cli_mod = _sys.modules["concept-lattice-index"]
        _activated = _cli_mod.query_activate(query, top_k=3)
        for _c in _activated:
            _bridge_text = (
                f"[lattice-bridge] {'+'.join(_c['intent'])} "
                f"(support={_c['support']}): {'; '.join(_c.get('members', [])[:4])}"
            )
            fused.append({
                "text": _bridge_text,
                "_full_text": _bridge_text,
                "rrf_score": 0.0,
                "enriched_weight": round(0.15 * _c.get("_activation_score", 1), 4),
                "enriched_distance": 1.0,
                "_age_days": 0.0,
                "sources": ["lattice"],
                "path": [],
            })
    except Exception:
        pass  # lattice expansion is best-effort; never block recall

    # SEU filter: only inject memories where relevance > interference (arXiv:2608.01149)
    if seu:
        fused = seu_filter(fused, query)

    # NECROPHORESIS RDM: penalise memories not accessed recently in this session
    if turn_rdm and current_turn > 0:
        fused = apply_turn_distance_rdm(fused, current_turn, rdm_lambda=rdm_lambda)

    for item in fused:
        item["text"] = apply_tier(item["_full_text"], tier)
        item["tier"] = tier

    record_query_access(fused)

    # ── Skill suggestions (SkillRouter, arXiv:2603.22455) ──────────────────────
    # Activate when query looks like a skill/procedure lookup. Fail-open: any
    # error (index not yet built, import failure) is silently suppressed so
    # recall is never blocked by the skill routing sidecar.
    _SKILL_TRIGGERS = ("how to", "skill", "procedure", "workflow", "steps to")
    _q_lower_sr = query.lower()
    _is_skill_query = (
        any(tok in _q_lower_sr for tok in _SKILL_TRIGGERS)
    )
    if _is_skill_query:
        try:
            import importlib.util as _ilu_sr, sys as _sys_sr
            _sri_key = "skill-router-index"
            if _sri_key not in _sys_sr.modules:
                _sri_path = str(Path(__file__).parent / "skill-router-index.py")
                _sri_spec = _ilu_sr.spec_from_file_location(_sri_key, _sri_path)
                if _sri_spec is None or _sri_spec.loader is None:
                    raise ImportError("skill-router-index spec unavailable")
                _sri_mod = _ilu_sr.module_from_spec(_sri_spec)
                _sys_sr.modules[_sri_key] = _sri_mod
                _sri_spec.loader.exec_module(_sri_mod)  # type: ignore[union-attr]
            else:
                _sri_mod = _sys_sr.modules[_sri_key]
            _skill_hits = _sri_mod.route(query, top=5)
            if _skill_hits:
                # Attach as a list on each top-ranked result item (only on [0])
                # so callers can read fused[0]["skill_suggestions"] without iterating.
                # Also stored on a sentinel item so JSON callers find it easily.
                for _item in fused:
                    _item["skill_suggestions"] = _skill_hits
                    break  # only annotate the first result
        except Exception:
            pass  # index not yet built or import failed — never block recall

    return fused


def record_query_access(fused: list[dict]) -> None:
    """MemSIF (arXiv:2608.01742): increment access_count on recalled facts.

    Query demand is the ActiveFact promotion signal. Fail-open: any DB error
    is logged and ignored so recall never fails because of sidecar writes.
    """
    db = _hermes_root() / "memory-facts" / "lifecycle.db"
    if not db.exists() or not fused:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with sqlite3.connect(str(db)) as conn:
            for item in fused:
                text = (item.get("_full_text") or item.get("text") or "").strip()
                if len(text) < 20:
                    continue
                key = text[:80]
                # Try update first; if no row matched, insert a tracking stub so
                # future access_count bumps accumulate (insert-on-miss pattern).
                cur = conn.execute(
                    """UPDATE fact_lifecycle
                       SET access_count = COALESCE(access_count, 0) + 1,
                           last_accessed = ?,
                           updated_at = ?
                       WHERE fact_text LIKE ?
                         AND COALESCE(memory_status, 'active') != 'invalidated'""",
                    (now, now, key + "%"),
                )
                if cur.rowcount == 0:
                    mem_id = item.get("id") or item.get("memory_id") or ""
                    conn.execute(
                        """INSERT OR IGNORE INTO fact_lifecycle
                           (memory_id, fact_text, fact_type, memory_status,
                            access_count, last_accessed, inserted_at, updated_at)
                           VALUES (?, ?, 'recalled', 'active', 1, ?, ?, ?)""",
                        (mem_id, text[:500], now, now, now),
                    )
                # Sweep 27 FAMA genGap: if fact is old at retrieval, annotate item for SEU/RDM
                try:
                    row = conn.execute(
                        "SELECT valid_from, volatility_class FROM fact_lifecycle "
                        "WHERE fact_text LIKE ? LIMIT 1",
                        (key + "%",),
                    ).fetchone()
                    if row and row[0]:
                        t0 = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
                        gap = (datetime.now(timezone.utc) - t0).total_seconds() / 86400.0
                        item["gen_gap_days"] = round(gap, 2)
                        item["vc"] = item.get("vc") or row[1]
                except Exception:
                    pass
            conn.commit()
    except Exception as e:
        print(f"[unified-recall] access_count bump skipped: {e}", file=sys.stderr)


def _vec_from_tokens(tokens: list[str]) -> dict:
    """Build a simple unit-length TF vector from token list (stdlib only)."""
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
    return {t: v / norm for t, v in tf.items()}


def _cosine_dicts(a: dict, b: dict) -> float:
    """Cosine similarity between two unit-length sparse vectors (dot product / product of norms)."""
    shared = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values())) or 1.0
    norm_b = math.sqrt(sum(v * v for v in b.values())) or 1.0
    return dot / (norm_a * norm_b)


def counterfactual_prefilter(
    query: str,
    candidates: list[dict],
) -> list[dict]:
    """Counterfactual context pre-filter (R3).

    Removes candidates that are both:
      (a) within 0.10 cosine of a higher-ranked candidate's text, AND
      (b) in the bottom 30 % of scores (by rrf_score or enriched_weight).

    Preserves original ranking order for retained candidates.
    Uses only stdlib: cosine = dot(a,b) / (||a|| * ||b||), computed over
    whitespace-tokenised lowercase word vectors.

    Args:
        query:      The recall query string (reserved for future query-aware
                    pruning; currently unused in the filter predicate).
        candidates: Ordered list of result dicts (highest-ranked first).
                    Each dict must have a 'text' key.  Score is read from
                    'enriched_weight' (preferred) or 'rrf_score' (fallback).

    Returns:
        Filtered list (subset of candidates, order preserved).
    """
    if not candidates:
        return candidates

    # Determine per-item scores
    scores = [
        float(c.get("enriched_weight", c.get("rrf_score", 0.0)))
        for c in candidates
    ]
    if not scores:
        return candidates

    sorted_scores = sorted(scores)
    bottom_30_cutoff = sorted_scores[max(0, int(len(sorted_scores) * 0.70) - 1)]

    # Pre-compute token vectors for each candidate
    def _tokenise(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    vecs = [_vec_from_tokens(_tokenise(c.get("text", ""))) for c in candidates]

    kept: list[dict] = []
    kept_vecs: list[dict] = []

    for idx, (cand, vec, score) in enumerate(zip(candidates, vecs, scores)):
        # Only consider pruning if this candidate is in the bottom 30 %
        if score <= bottom_30_cutoff:
            redundant = False
            for higher_vec in kept_vecs:
                sim = _cosine_dicts(vec, higher_vec)
                if sim >= 0.90:  # within 0.10 cosine of a higher-ranked item
                    redundant = True
                    break
            if redundant:
                continue  # drop this candidate

        kept.append(cand)
        kept_vecs.append(vec)

    return kept


def search_pending_activefacts(query: str, limit: int = 5) -> list[dict]:
    """MemSIF: surface pending ActiveFacts so query demand can accrue.

    Token overlap only (no embeddings). Fail-open.
    """
    db = _hermes_root() / "memory-facts" / "lifecycle.db"
    if not db.exists() or not (query or "").strip():
        return []
    terms = sorted({t for t in re.findall(r"[a-zA-Z0-9_]{4,}", query.lower())}, key=len, reverse=True)[:3]
    if not terms:
        return []
    where = " AND ".join(["lower(fact_text) LIKE ?" for _ in terms])
    params = [f"%{t}%" for t in terms]
    try:
        with sqlite3.connect(str(db)) as conn:
            rows = conn.execute(
                f"""SELECT fact_text, access_count FROM fact_lifecycle
                    WHERE memory_status='pending' AND COALESCE(fact_track,'active')='active'
                      AND {where}
                    ORDER BY COALESCE(access_count,0) DESC LIMIT ?""",
                (*params, limit),
            ).fetchall()
    except Exception as e:
        print(f"[unified-recall] pending ActiveFact search skipped: {e}", file=sys.stderr)
        return []
    out = []
    for i, (text, acc) in enumerate(rows):
        text = (text or "").strip()
        if len(text) < 20:
            continue
        out.append({
            "text": text,
            "score": 0.55,
            "source": "lifecycle-pending",
            "_raw_rank": i,
            "_access_count": int(acc or 0),
        })
    return out


def _check_experience_cache(query: str):
    # VikingRAG experience-edge cache (arXiv:2609.11390)
    """Check the experience-edge cache for a near-identical prior query.

    If cosine(query, cached_query) > 0.85 and the entry is < 3600s old,
    returns the cached fused results directly (skipping Hindsight + Graphiti).
    Otherwise returns None so the caller proceeds normally.
    """
    import time as _t
    cache_path = Path("~/.hermes/cache/recall-experience-cache.json").expanduser()
    if not cache_path.exists():
        return None
    try:
        entries = json.loads(cache_path.read_text())
    except Exception:
        return None
    if not isinstance(entries, list):
        return None

    def _tokenise(text: str) -> list:
        return re.findall(r"[a-z0-9]+", text.lower())

    q_vec = _vec_from_tokens(_tokenise(query))
    now = _t.time()
    for entry in reversed(entries):  # most recent first
        age = now - entry.get("ts", 0)
        if age >= 3600:
            continue
        cached_query = entry.get("query", "")
        c_vec = _vec_from_tokens(_tokenise(cached_query))
        sim = _cosine_dicts(q_vec, c_vec)
        if sim > 0.85:
            cached_results = entry.get("fused_results")
            if cached_results:
                print(
                    f"[unified-recall] VikingRAG cache hit (sim={sim:.3f}, age={age:.0f}s)",
                    file=sys.stderr,
                )
                return cached_results
    return None


def _write_experience_cache(query: str, fused: list) -> None:
    # VikingRAG experience-edge cache (arXiv:2609.11390)
    """Append the current query + top-10 result ids to the experience-edge cache.

    Keeps only the 100 most-recent entries; writes atomically via .tmp + rename.
    """
    import time as _t
    cache_path = Path("~/.hermes/cache/recall-experience-cache.json").expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        entries = json.loads(cache_path.read_text()) if cache_path.exists() else []
        if not isinstance(entries, list):
            entries = []
    except Exception:
        entries = []

    new_entry = {
        "query": query,
        "result_ids": [r.get("id", r.get("_md5", "")) for r in fused[:10]],
        "fused_results": fused[:10],
        "ts": _t.time(),
    }
    entries.append(new_entry)
    # Keep only 100 most recent
    entries = entries[-100:]

    tmp_path = cache_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(entries, indent=2))
        tmp_path.rename(cache_path)
    except Exception as e:
        print(f"[unified-recall] experience cache write failed: {e}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(
        description="Unified Hindsight+Graphiti memory recall with tiered output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tiers (OpenViking-inspired):
  l0  ~15-20 tokens  — 1-sentence abstract for screening; use --screen
  l1  ~200 chars     — excerpt with trajectory
  l2  full text      — default behaviour

--promote always expands selected results to full L2 text, ignoring --tier.
--tier only applies to non-promoted (normal) output.

Examples:
  %(prog)s "PPOR budget" --screen
  %(prog)s "PPOR budget" --tier l1 --top 5
  %(prog)s "PPOR budget" --screen --promote 9,10   # screen then expand specific items
  %(prog)s "trading stops" --json
        """,
    )
    p.add_argument("query", help="Natural language query")
    p.add_argument("--top", type=int, default=DEFAULT_TOP, help="Max results (default: 10)")
    p.add_argument("--min-score", type=float, default=0.0, help="Min RRF score 0-1 (default: 0)")
    p.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    p.add_argument("--tier", choices=["l0", "l1", "l2"], default="l2",
                   help="Output tier: l0=abstract, l1=excerpt, l2=full (default: l2)")
    p.add_argument("--screen", action="store_true",
                   help="Screening mode: alias for --tier l0 --top 20")
    p.add_argument("--promote", default="",
                   help="Comma-separated 1-based indices to expand to L2 (use after --screen)")
    p.add_argument("--show-path", action="store_true",
                   help="Show retrieval trajectory for each result")
    p.add_argument("--hindsight-only", action="store_true")
    p.add_argument("--graphiti-only", action="store_true")
    args = p.parse_args()

    if not args.query.strip():
        p.print_help()
        sys.exit(2)

    # Apply --screen shorthand
    tier = args.tier
    top = args.top
    if args.screen:
        tier = "l0"
        top = 20

    # VikingRAG experience-edge cache check (arXiv:2609.11390)
    _cached = _check_experience_cache(args.query)
    if _cached is not None:
        fused = _cached
        fused = counterfactual_prefilter(args.query, fused)
        record_query_access(fused)
        _write_experience_cache(args.query, fused)
        if not fused:
            print("[unified-recall] No results found.", file=sys.stderr)
            sys.exit(1)
        output = []
        for item in fused:
            out_item = dict(item)
            out_item["text"] = apply_tier(item.get("_full_text", item.get("text", "")), tier)
            out_item["tier"] = tier
            output.append(out_item)
        for item in output:
            item.pop("_full_text", None)
        if args.as_json:
            print(json.dumps(output, indent=2))
        else:
            print(f"[unified-recall] {len(output)} results [{tier.upper()}] (cache hit) for: {args.query!r}\n")
            for i, r in enumerate(output, 1):
                srcs = "+".join(r.get("sources", []))
                score = r.get("rrf_score", 0)
                text = r.get("text", "")
                print(f"  {i:2d}. [{score:.3f}] ({srcs})")
                print(f"      {text}")
                print()
        sys.exit(0)

    h_results, h_err = ([], False) if args.graphiti_only else hindsight_search(args.query, limit=top * 2)
    g_results, g_err = ([], False) if args.hindsight_only else graphiti_search(args.query, limit=top * 2)
    pending = search_pending_activefacts(args.query)

    # Both services errored with no results — distinct from "query returned nothing"
    if h_err and g_err and not h_results and not g_results and not pending:
        print("[unified-recall] Both sources failed (services may be down).", file=sys.stderr)
        sys.exit(3)

    fused = fuse_results(h_results + pending, g_results, args.query, top=top, min_score=args.min_score)
    fused = counterfactual_prefilter(args.query, fused)  # R3: remove near-duplicate low-ranked candidates
    record_query_access(fused)
    _write_experience_cache(args.query, fused)  # VikingRAG experience-edge cache (arXiv:2609.11390)

    if not fused:
        print("[unified-recall] No results found.", file=sys.stderr)
        sys.exit(1)

    # Handle --promote: expand specific items to L2
    promote_indices = []
    if args.promote:
        try:
            promote_indices = [int(x.strip()) for x in args.promote.split(",") if x.strip()]
        except ValueError:
            print("[unified-recall] --promote expects comma-separated integers e.g. 1,3,5", file=sys.stderr)
            sys.exit(2)

    if promote_indices:
        output = promote_results(fused, promote_indices)
    else:
        output = []
        for item in fused:
            out_item = dict(item)
            out_item["text"] = apply_tier(item["_full_text"], tier)
            out_item["tier"] = tier
            output.append(out_item)

    # Strip internal key before output
    for item in output:
        item.pop("_full_text", None)

    if args.as_json:
        print(json.dumps(output, indent=2))
    else:
        label = "PROMOTE→L2" if promote_indices else tier.upper()
        print(f"[unified-recall] {len(output)} results [{label}] for: {args.query!r}\n")
        for i, r in enumerate(output, 1):
            srcs = "+".join(r["sources"])
            score = r["rrf_score"]
            text = r["text"]
            print(f"  {i:2d}. [{score:.3f}] ({srcs})")
            print(f"      {text}")
            if args.show_path:
                path_str = ", ".join(
                    f"{p['source']}@{p['rank']}(rrf={p['rrf']})" for p in r.get("path", [])
                )
                print(f"      PATH: {path_str}")
            print()


if __name__ == "__main__":
    main()
