#!/usr/bin/env python3
"""
memory-query-router.py — Query-type routing for Hermes memory retrieval.

Classifies a natural-language query into one of four types and returns
the recommended retrieval surface(s) in priority order.

Source: Memory in LLM Era v3 (arXiv:2604.01707) — P3.9 implementation.

Query types and their primary surfaces:
  semantic   → Hindsight dense vector search (hindsight_recall)
  temporal   → session_search (state.db FTS5, date-capable) then Graphiti
  relational → Graphiti graph traversal (search_memory_facts + search_nodes)
  exact      → session_search (state.db FTS5 keyword query)

Classification uses rule-based heuristics first (fast, zero-token), falling
back to LLM classification only when heuristics are ambiguous.

Usage (standalone):
  python3 memory-query-router.py "when did we last update the arXiv sweep?"
  python3 memory-query-router.py --json "who works at ACME?"

Usage (library):
  from memory_query_router import route_query
  result = route_query("what is the Hindsight dedup threshold?")
  # result = {"type": "semantic", "surfaces": ["hindsight_recall"], "confidence": "high"}

Surfaces returned:
  hindsight_recall    — hindsight_recall(query=...) — dense semantic vector search
  session_search      — session_search(query=...) — keyword/FTS5 over state.db (date-range capable)
  graphiti_facts      — search_memory_facts(query=...) — entity relationship graph
  graphiti_nodes      — search_nodes(query=...) — entity node lookup

Routing rules (arXiv:2604.01707 §3):
  - semantic:   general knowledge / preference / factual recall → hindsight_recall first
  - temporal:   time-anchored: "when", "last", "before", "after", dates → FTS5 + graphiti
  - relational: entity relationships: "who works with", "how does X relate to Y" → graphiti first
  - exact:      verbatim recall: exact quotes, IDs, filenames, error messages → FTS5 first

QMD and MemPalace are disabled in live config — never route to them.
"""

import re
import sys
import json
import os
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).parent))


# --------------------------------------------------------------------------- #
# FTRL Routing Calibration Log (Shalev-Shwartz & Ben-David Ch 21 / FTRL)
# --------------------------------------------------------------------------- #

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root_mq = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
_ROUTING_LOG_PATH = _hermes_root_mq / "cache" / "routing-calibration.jsonl"


def _log_routing_decision(query_type, query, result_count=-1):
    # FTRL routing calibration log (Shalev-Shwartz Ch 11)
    # Records routing decisions so FTRL can adjust route weights over time.
    try:
        import hashlib, json, time
        entry = {'ts': time.time(), 'route': query_type,
                 'qhash': hashlib.md5(query.encode()).hexdigest()[:8],
                 'result_count': result_count}
        _ROUTING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _ROUTING_LOG_PATH.open('a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #

class RouteResult(TypedDict):
    type: str            # "semantic" | "temporal" | "relational" | "exact"
    surfaces: list[str]  # ordered list of recommended retrieval surfaces
    confidence: str      # "high" | "medium" | "low"
    reason: str          # one-line explanation


# --------------------------------------------------------------------------- #
# Heuristic classifiers (zero-token, deterministic)
# --------------------------------------------------------------------------- #

# Temporal signals — time-referencing words/phrases
TEMPORAL_PATTERNS = re.compile(
    r"\b("
    r"when|last|before|after|since|until|recent|latest|earliest|first time|"
    r"yesterday|today|this week|this month|ago|previously|history|timeline|"
    r"date|timestamp|version|updated|changed|modified|added|removed|"
    r"in \d{4}|on \d{4}-\d{2}|at \d{2}:\d{2}"
    r")\b",
    re.IGNORECASE,
)

# Relational signals — entity relationship queries
RELATIONAL_PATTERNS = re.compile(
    r"\b("
    r"who works|who is|relate[sd]? to|connection between|how does .+ connect|"
    r"link between|associated with|depends on|caused by|leads to|followed by|"
    r"parent of|child of|part of|member of|belongs to|owns|manages|reports to|"
    r"between .+ and|relationship|entity|node|graph"
    r")\b",
    re.IGNORECASE,
)

# Exact-recall signals — verbatim lookups.
# NOTE: ALL_CAPS check is CASE-SENSITIVE (no IGNORECASE flag) to avoid matching normal words.
_EXACT_ALLCAPS = re.compile(r"\b[A-Z]{3}[A-Z0-9_]+\b")  # e.g. HINDSIGHT_URL, UUID, POLE
_EXACT_OTHER = re.compile(
    r'('
    r'"[^"]{4,}"|'                    # quoted phrase (4+ chars) — strongest exact signal
    r'`[^`]{4,}`|'                    # backtick literal
    r'\berror:?\s+\w|'                # error messages
    r'\b\w{4,}\.(py|md|yaml|json|sh|toml|txt)\b|'  # filenames with extensions
    r'\bproc_[a-z0-9]+\b|'           # process IDs
    r'\b[0-9a-f]{8}-[0-9a-f]{4}-'   # UUIDs
    r')',
    re.IGNORECASE,
)


def count_exact_hits(query: str) -> int:
    """Count distinct exact-recall signals in query."""
    caps = len(_EXACT_ALLCAPS.findall(query))
    other = len(_EXACT_OTHER.findall(query))
    return caps + other


EXACT_PATTERNS = _EXACT_OTHER  # kept for backward compat; use count_exact_hits() for routing

# POLE entity presence (Person/Organisation/Location/Event + Object) — hints relational
POLE_PATTERNS = re.compile(
    r"\b("
    r"[A-Z][a-z]+ [A-Z][a-z]+|"   # Proper nouns (two-word capitalised)
    r"[A-Z][a-z]+\'s\b"            # Possessives
    r")\b"
)


def heuristic_classify(query: str) -> tuple[str | None, str, str]:
    """
    Return (query_type, confidence, reason) using pattern matching.
    Returns (None, "low", reason) when ambiguous.
    """
    q = query.strip()

    temporal_hits = len(TEMPORAL_PATTERNS.findall(q))
    relational_hits = len(RELATIONAL_PATTERNS.findall(q))
    exact_hits = count_exact_hits(q)

    # Strong exact signal: quoted phrase or filename or UUID
    strong_exact = bool(re.search(r'"[^"]{4,}"', q) or re.search(r'[0-9a-f]{8}-[0-9a-f]{4}', q))

    if strong_exact and exact_hits >= 1:
        return "exact", "high", f"verbatim literal pattern ({exact_hits} exact signals)"

    # Relational beats temporal when we have clear entity + relationship verbs
    if relational_hits >= 2:
        return "relational", "high", f"entity relationship query ({relational_hits} relational signals)"

    if temporal_hits >= 2:
        return "temporal", "high", f"time-anchored query ({temporal_hits} temporal signals)"

    if temporal_hits == 1 and relational_hits == 0 and exact_hits == 0:
        return "temporal", "medium", "single temporal signal, no conflicting patterns"

    if relational_hits == 1 and temporal_hits == 0:
        return "relational", "medium", "single relational signal"

    if exact_hits >= 2:
        return "exact", "medium", f"multiple exact-recall patterns ({exact_hits})"

    if exact_hits == 1:
        return "exact", "medium", "single exact-recall pattern (filename or identifier)"

    if temporal_hits == 0 and relational_hits == 0 and exact_hits == 0:
        return "semantic", "medium", "no temporal/relational/exact signals — general semantic recall"

    return None, "low", f"ambiguous ({temporal_hits}t/{relational_hits}r/{exact_hits}e)"


# --------------------------------------------------------------------------- #
# LLM fallback
# --------------------------------------------------------------------------- #

ROUTER_MODEL = os.environ.get("MEMORY_ROUTER_MODEL", "claude-haiku-4-5")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ROUTER_PROMPT = """Classify this memory retrieval query into exactly one of these types:
  semantic    — general knowledge, preferences, procedural facts, "what is", "how does"
  temporal    — time-anchored questions: "when", "last time", date ranges, history
  relational  — entity relationships: "who works with X", "how does A relate to B"
  exact       — verbatim recall: exact quotes, error messages, IDs, filenames

Query: {query}

Respond with ONLY a JSON object:
{{"type": "<type>", "reason": "<one sentence>"}}
"""


def llm_classify(query: str) -> tuple[str, str]:
    """Call Anthropic API to classify ambiguous query. Returns (type, reason)."""
    import urllib.request
    if not ANTHROPIC_API_KEY:
        return "semantic", "no API key — defaulting to semantic"
    payload = {
        "model": ROUTER_MODEL,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": ROUTER_PROMPT.format(query=query)}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            text = result["content"][0]["text"].strip()
            parsed = json.loads(text)
            return parsed.get("type", "semantic"), parsed.get("reason", "LLM classified")
    except Exception as e:
        return "semantic", f"LLM error ({e}) — defaulting to semantic"


# --------------------------------------------------------------------------- #
# Surface mapping
# --------------------------------------------------------------------------- #

SURFACE_MAP: dict[str, list[str]] = {
    # arXiv:2604.01707 §3 routing rules
    # session_search = state.db FTS (always-on). Do not alias this as Hindsight FTS.
    # QMD / MemPalace are disabled — never route to them.
    "semantic":   ["hindsight_recall", "graphiti_facts"],
    "temporal":   ["session_search", "graphiti_facts", "hindsight_recall"],
    "relational": ["graphiti_facts", "graphiti_nodes", "hindsight_recall"],
    "exact":      ["session_search", "hindsight_recall"],
}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def route_query(query: str, allow_llm: bool = True) -> RouteResult:
    """
    Classify query and return RouteResult with recommended surfaces.

    Args:
        query: Natural-language memory retrieval query.
        allow_llm: If True, call LLM for low-confidence heuristic results.
                   Set False for fast/offline use (falls back to semantic).

    Returns:
        RouteResult with type, surfaces, confidence, reason.
    """
    # FTRL routing-weight feedback (bottleneck #2): load per-route weights from
    # routing-weight-updater.py output.  Weights > 1.0 = historically reliable
    # route; weights < 0.5 = historically unreliable (confidence downgraded).
    # Shadow-wrapped: never raises, defaults to empty dict (weight=1.0 for all).
    try:
        import json as _jrw
        _rw_path = _hermes_root_mq / "cache" / "routing-weights.json"
        _rw_raw = _jrw.loads(_rw_path.read_text()) if _rw_path.exists() else {}
        # Weights may be stored as {route: float} or {route: {weight: float, ...}}
        _route_weights = {}
        for _rk, _rv in _rw_raw.items():
            if isinstance(_rv, dict):
                _route_weights[_rk] = float(_rv.get('weight', 1.0))
            else:
                _route_weights[_rk] = float(_rv)
    except Exception:
        _route_weights = {}

    qtype, confidence, reason = heuristic_classify(query)

    if qtype is None:
        if allow_llm:
            qtype, reason = llm_classify(query)
            confidence = "medium"
        else:
            qtype = "semantic"
            confidence = "low"
            reason = "heuristic ambiguous, LLM disabled — defaulting to semantic"

    _log_routing_decision(qtype, query, result_count=1)  # route always resolves; 1 = success signal for FTRL

    # FTRL weight adjustment: downgrade confidence when route weight is low.
    # weight >= 0.7  → no change (route is historically reliable enough)
    # weight in [0.4, 0.7) → downgrade "high" → "medium" (marginal route)
    # weight < 0.4  → downgrade "high" → "low", "medium" → "low" (weak route)
    # Shadow-wrapped: never raises.
    try:
        _w = _route_weights.get(qtype, 1.0)
        if _w < 0.4:
            if confidence == 'high':
                confidence = 'low'
                reason = reason + f' [ftrl_weight={_w:.3f}→low]'
            elif confidence == 'medium':
                confidence = 'low'
                reason = reason + f' [ftrl_weight={_w:.3f}→low]'
        elif _w < 0.7:
            if confidence == 'high':
                confidence = 'medium'
                reason = reason + f' [ftrl_weight={_w:.3f}→medium]'
    except Exception:
        pass

    return RouteResult(
        type=qtype,
        surfaces=SURFACE_MAP[qtype],
        confidence=confidence,
        reason=reason,
    )


def format_tool_call(result: RouteResult) -> str:
    """Return a human-readable routing recommendation for terminal output."""
    lines = [
        f"query_type:  {result['type']}",
        f"confidence:  {result['confidence']}",
        f"reason:      {result['reason']}",
        f"surfaces:    {' → '.join(result['surfaces'])}",
        "",
        "Recommended call sequence:",
    ]
    surface_docs = {
        "hindsight_recall": "  1. hindsight_recall(query='<query>')",
        "session_search":   "  -. session_search(query='<keywords>', sort='newest')",
        "graphiti_facts":   "  -. search_memory_facts(query='<query>')",
        "graphiti_nodes":   "  -. search_nodes(query='<entity name>')",
    }
    for i, s in enumerate(result["surfaces"], 1):
        doc = surface_docs.get(s, f"  {i}. {s}")
        # Replace the placeholder dash with actual sequence number
        doc = re.sub(r"^  -\.", f"  {i}.", doc)
        lines.append(doc)

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# OT-13: W1-discriminative routing
# --------------------------------------------------------------------------- #

# Built-in skill descriptions for W1 routing when no external skill list is
# available.  Keys match the four memory surface categories.
_W1_SKILL_TEXTS: dict[str, str] = {
    "semantic": (
        "semantic search retrieval query embedding vector similarity cosine "
        "distance recall precision index lookup nearest neighbour dense sparse "
        "knowledge preference factual what how does general"
    ),
    "temporal": (
        "temporal time date timestamp history timeline recent latest earliest "
        "before after since until session memory modified updated changed added "
        "when last week month year ago previously version"
    ),
    "relational": (
        "graph node edge entity relationship traversal knowledge facts memory "
        "graphiti relational association connection link parent child belongs "
        "who works relate connected depends caused leads followed between"
    ),
    "exact": (
        "exact verbatim literal quote filename extension error message uuid "
        "identifier process id allcaps backtick code snippet find locate search "
        "specific exact match keyword fts fulltext"
    ),
}


def w1_route(query: str, skill_texts: dict[str, str] | None = None) -> list[dict]:
    """OT-13: Rank memory routing targets by W1 (earth-mover) distance.

    Computes Sinkhorn-approximated W1 distance between the query TF vector
    and each skill TF vector.  Lower distance = better vocabulary alignment.

    Returns top-5 skills ordered by ascending W1 distance.
    """
    # L9 fix: guard ot_utils import — optional dependency; return [] if absent
    try:
        import ot_utils
    except ImportError:
        return []

    if skill_texts is None:
        skill_texts = _W1_SKILL_TEXTS

    query_tf = ot_utils.build_tf(query)

    distances: list[tuple[str, float]] = []
    for skill_name, text in skill_texts.items():
        skill_tf = ot_utils.build_tf(text)
        dist = ot_utils.w1_distance(query_tf, skill_tf)
        distances.append((skill_name, dist))

    distances.sort(key=lambda x: x[1])
    top5 = distances[:5]

    return [{"skill": name, "w1_distance": round(dist, 6)} for name, dist in top5]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main():
    import argparse
    p = argparse.ArgumentParser(
        description="Classify a memory query and recommend retrieval surfaces."
    )
    p.add_argument("query", nargs="?", help="Query string to classify")
    p.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    p.add_argument("--no-llm", action="store_true", help="Disable LLM fallback (heuristics only)")
    p.add_argument("--test", action="store_true", help="Run built-in test suite")
    p.add_argument(
        "--w1-route",
        action="store_true",
        help="OT-13: append W1-discriminative routing ranking to output (requires --json or standalone)",
    )
    args = p.parse_args()

    if args.test:
        run_tests()
        return

    if not args.query:
        p.print_help()
        sys.exit(1)

    result = route_query(args.query, allow_llm=not args.no_llm)

    if args.w1_route:
        result = dict(result)
        result["w1_routing"] = w1_route(args.query)

    if args.json or args.w1_route:
        print(json.dumps(result, indent=2))
    else:
        print(format_tool_call(RouteResult(**result)))  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Built-in test suite
# --------------------------------------------------------------------------- #

TEST_CASES = [
    # (query, expected_type)
    ("what is the Hindsight dedup threshold?", "semantic"),
    ("when did we last run the arXiv sweep?", "temporal"),
    ("who works at ACME and how do they relate to the project?", "relational"),
    ('find the exact error "libicuuc.so.70 missing"', "exact"),
    ("what are my trading rules for momentum positions?", "semantic"),
    ("what changed since last week?", "temporal"),
    ("how does Graphiti connect to Hindsight?", "relational"),
    ("find l1-promote.py", "exact"),
    ("what does the user prefer for email sign-off?", "semantic"),
    ("when was the last sweep before sweep 17?", "temporal"),
]


def run_tests():
    passed = failed = 0
    for query, expected in TEST_CASES:
        result = route_query(query, allow_llm=False)
        got = result["type"]
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {got:10s} (expected {expected:10s}) | {query[:55]}")
    print(f"\n{passed}/{passed+failed} passed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
