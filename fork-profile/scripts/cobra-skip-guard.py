#!/usr/bin/env python3
"""
cobra-skip-guard.py — CoBRA-approximation tool-use skip guard
arXiv:2609.00967 (CoBRA: Learning Tool-Use Boundaries via Counterfactual Margins)

CoBRA trains a model to estimate per-instance marginal benefit of a tool call.
This script implements the heuristic approximation: rule-based skip detection
grounded in observed tool-call data from 13,038 Hermes session calls.

Usage (from agent scripts or cron guards):
    python3 ~/.hermes/scripts/cobra-skip-guard.py \\
        --tool web_search \\
        --query "what is the capital of France" \\
        --context-has-tool web_search \\
        --context-has-tool hindsight_recall

Returns:
    exit 0  + JSON {"skip": false, "reason": "..."}  → call the tool
    exit 1  + JSON {"skip": true,  "reason": "..."}  → skip the tool call
    exit 2  → bad arguments

Hermes integration: ~/.hermes/plugins/cobra-guard registers pre_tool_call
(warn-only, never blocks) and post_tool_call (outcome log). Also usable as a
CLI from cron scripts. HERMES_COBRA_GUARD=0 disables the plugin.
"""

import argparse
import json
import sys
import re
from pathlib import Path
from typing import Optional

# ── Evidence-grounded cost table (from 13,038 agent.log records, 2026-09-08) ──
# median_duration_s: measured p50 latency per tool call
# yield_chars:       measured p50 output chars
# skip_threshold:    minimum query complexity below which tool is likely wasteful

TOOL_COSTS = {
    "web_search":       {"dur_s": 1.11,  "yield": 3294,  "class": "network"},
    "web_extract":      {"dur_s": 9.60,  "yield": 18978, "class": "network"},
    "hindsight_recall": {"dur_s": 7.29,  "yield": 17930, "class": "network"},
    "delegate_task":    {"dur_s": 900.0, "yield": 4213,  "class": "async"},
    "vision_analyze":   {"dur_s": 5.59,  "yield": 1553,  "class": "api"},
    "execute_code":     {"dur_s": 0.31,  "yield": 1322,  "class": "local"},
    "terminal":         {"dur_s": 0.83,  "yield": 421,   "class": "local"},
    "skill_view":       {"dur_s": 0.18,  "yield": 22355, "class": "local"},
    "read_file":        {"dur_s": 0.06,  "yield": 3646,  "class": "local"},
    "search_files":     {"dur_s": 0.08,  "yield": 578,   "class": "local"},
    "session_search":   {"dur_s": 0.01,  "yield": 546,   "class": "local"},
}

# ── Skip rules (CoBRA approximation) ─────────────────────────────────────────
# Each rule is (condition_fn, reason_str).
# Rules are evaluated in order; first match wins.
# rule returns True → skip the tool call.

def rules(tool: str, query: str, context_tools: list[str], context_chars: int) -> tuple[bool, str]:
    """
    Returns (should_skip, reason).
    
    context_tools: list of tool names already called this turn/session
    context_chars: total chars of context already retrieved this turn
    """
    query_tokens = len(query.split()) if query else 0
    tool_info = TOOL_COSTS.get(tool, {})
    tool_class = tool_info.get("class", "unknown")

    # Rule 1: web_search after hindsight_recall already returned sufficient context
    # Counterfactual: if hindsight already returned >5000 chars, marginal benefit
    # of an additional web_search is likely low for factual/memory queries.
    if (tool == "web_search"
            and "hindsight_recall" in context_tools
            and context_chars > 5000
            and query_tokens < 8):
        return True, (
            "web_search skipped: hindsight_recall already retrieved "
            f"{context_chars} chars and query is short ({query_tokens} tokens). "
            "Marginal benefit likely low (CoBRA Rule 1)."
        )

    # Rule 2: web_extract when web_search hasn't been called yet for the same query
    # Calling web_extract without a prior web_search on an unknown URL is low-confidence.
    # Exception: URL is already known/given explicitly (long URL in query).
    url_in_query = bool(re.search(r'https?://', query or ''))
    if (tool == "web_extract"
            and "web_search" not in context_tools
            and not url_in_query
            and query_tokens < 15):
        return True, (
            "web_extract skipped: no prior web_search to establish target URL, "
            "and no explicit URL in query. Run web_search first (CoBRA Rule 2)."
        )

    # Rule 3: exact duplicate tool+query — same tool AND same query already in context.
    # Read-only local tools with identical query return the same result; skip the repeat.
    # NOTE: context_tools contains tool NAMES only, not prior queries. This rule can only
    # fire when the caller passes both prior tool names AND a query string that exactly
    # matches one of the tool name strings — which is almost never true. Rule is effectively
    # disabled until context_tools is extended to carry (tool, query) pairs. Left in place
    # as a stub; do not rely on it for real duplicate detection.
    # TODO: extend --context-has-tool to accept "toolname:query" pairs, then re-enable.
    if False and (tool in ("read_file", "search_files", "session_search", "skills_list")
            and tool in context_tools
            and query and any(query in ct for ct in context_tools)):
        return True, (
            f"{tool} skipped: identical call already made this turn. "
            "Re-calling with the same query returns the same output (CoBRA Rule 3). "
            "Use a different path/query if you need different data.\n"
            "(NOTE: Rule 3 is currently disabled — context_tools only carries tool names.)"
        )

    # Rule 4: web_search when context_chars already exceeds 20k
    # Context is already saturated; additional web_search is likely noise.
    if (tool == "web_search"
            and context_chars > 20000):
        return True, (
            f"web_search skipped: context already contains {context_chars:,} chars. "
            "Additional search unlikely to add signal above noise (CoBRA Rule 4)."
        )

    # Rule 5: hindsight_recall with a very short query (<3 tokens)
    # Short queries produce low-precision recall; skip and use session context instead.
    if (tool == "hindsight_recall" and query_tokens < 3):
        return True, (
            f"hindsight_recall skipped: query '{query}' is too short ({query_tokens} tokens) "
            "for precise recall. Broaden the query or use session_search (CoBRA Rule 5)."
        )

    # Rule 6: delegate_task for tasks that are unambiguously single-step local ops.
    # Only skip if the query is a known single-tool pattern (not just short).
    # Rationale: short review tasks ("review this") legitimately use delegate_task.
    # We never skip on token count alone — that was producing false positives.
    _LOCAL_PATTERNS = ("list ", "count ", "echo ", "what is the current ", "show me the value of ")
    if (tool == "delegate_task"
            and query_tokens < 5
            and any(query.lower().startswith(p) for p in _LOCAL_PATTERNS)):
        return True, (
            f"delegate_task skipped: task '{query}' matches a known single-step local pattern "
            "and doesn't need async delegation (CoBRA Rule 6)."
        )

    return False, f"{tool}: no skip rule matched; marginal benefit estimated positive."


# ── Logistic probe (lightweight classifier trained on synthetic data) ─────────
# Since we don't have labelled (query, tool, useful) triples from the logs,
# we train a logistic probe on synthetic examples generated from the rule table.
# This gives a probability estimate P(useful | tool, context_chars, query_len)
# that complements the rule-based skip decision.

def train_probe():
    """
    Train a logistic probe on synthetic examples.
    Features: [tool_dur_s, tool_yield, context_chars, query_tokens, same_tool_in_ctx]
    Label: 1=useful, 0=wasteful
    """
    try:
        from sklearn.linear_model import LogisticRegression
        import numpy as np
    except ImportError:
        return None

    rng = np.random.default_rng(42)
    n = 2000
    X, y = [], []

    for _ in range(n):
        tool = rng.choice(list(TOOL_COSTS.keys()))
        info = TOOL_COSTS[tool]
        dur = info["dur_s"]
        yield_chars = info["yield"]
        ctx_chars = rng.integers(0, 30000)
        query_toks = rng.integers(1, 30)
        same_tool = rng.integers(0, 2)  # 0 or 1

        # Generate label from rules (synthetic ground truth)
        ctx_tools = [tool] if same_tool else []
        skip, _ = rules(tool, " ".join(["x"] * int(query_toks)), ctx_tools, int(ctx_chars))
        label = 0 if skip else 1

        # Add noise (15%) to simulate real-world uncertainty
        if rng.random() < 0.15:
            label = 1 - label

        X.append([dur, yield_chars / 1000, ctx_chars / 1000, query_toks, same_tool])
        y.append(label)

    X = np.array(X)
    y = np.array(y)

    clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
    clf.fit(X, y)
    return clf


def probe_score(clf, tool: str, context_chars: int, query_tokens: int, same_tool: bool) -> float:
    """Returns P(useful) from the trained probe. Returns 0.5 if probe unavailable."""
    if clf is None:
        return 0.5
    import numpy as np
    info = TOOL_COSTS.get(tool, {"dur_s": 1.0, "yield": 1000})
    X = np.array([[
        info["dur_s"],
        info["yield"] / 1000,
        context_chars / 1000,
        query_tokens,
        int(same_tool),
    ]])
    return float(clf.predict_proba(X)[0][1])


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CoBRA tool-use skip guard")
    parser.add_argument("--tool", default="", help="Tool name to evaluate (required unless --train-probe-only)")
    parser.add_argument("--query", default="", help="Query/intent for the tool call")
    parser.add_argument("--context-has-tool", action="append", default=[], dest="context_tools",
                        help="Tool already called this turn (repeat for multiple)")
    parser.add_argument("--context-chars", type=int, default=0,
                        help="Total chars already in context this turn")
    parser.add_argument("--probe", action="store_true",
                        help="Also output logistic probe P(useful) score")
    parser.add_argument("--train-probe-only", action="store_true",
                        help="Train and save probe, then exit")
    args = parser.parse_args()

    if not args.train_probe_only and not args.tool:
        parser.error("--tool is required unless --train-probe-only is set")

    probe_path = Path.home() / ".hermes/cache/cobra-probe.json"

    if args.train_probe_only:
        clf = train_probe()
        if clf is None:
            print(json.dumps({"error": "sklearn not available"}))
            sys.exit(2)
        # Serialize coefficients
        import numpy as np  # noqa: F811
        probe_data = {
            "coef": np.array(clf.coef_).tolist(),
            "intercept": np.array(clf.intercept_).tolist(),
            "classes": np.array(clf.classes_).tolist(),
            "features": ["dur_s", "yield_k", "ctx_chars_k", "query_toks", "same_tool"],
            "trained_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "n_synthetic": 2000,
        }
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        _tmp = probe_path.with_suffix('.tmp')
        _tmp.write_text(json.dumps(probe_data, indent=2), encoding='utf-8')
        _tmp.replace(probe_path)
        print(json.dumps({"status": "trained", "path": str(probe_path)}))
        sys.exit(0)

    # Evaluate rules
    query_tokens = len(args.query.split()) if args.query else 0
    should_skip, reason = rules(
        args.tool, args.query, args.context_tools, args.context_chars
    )

    result = {
        "skip": should_skip,
        "reason": reason,
        "tool": args.tool,
        "rule_based": True,
    }

    if args.probe:
        # Load or train probe
        clf = None
        if probe_path.exists():
            try:
                import numpy as np
                from sklearn.linear_model import LogisticRegression
                probe_data = json.loads(probe_path.read_text())
                clf = LogisticRegression()
                clf.coef_ = np.array(probe_data["coef"])
                clf.intercept_ = np.array(probe_data["intercept"])
                clf.classes_ = np.array(probe_data["classes"])
            except Exception:
                clf = None
        if clf is None:
            clf = train_probe()

        p_useful = probe_score(
            clf, args.tool, args.context_chars, query_tokens,
            args.tool in args.context_tools
        )
        result["probe_p_useful"] = round(p_useful, 3)
        result["probe_skip"] = p_useful < 0.4  # skip if P(useful) < 40%

    print(json.dumps(result))
    # --probe: exit code follows probe_skip (P(useful) threshold), not rule-based should_skip.
    if args.probe and "probe_skip" in result:
        sys.exit(1 if result["probe_skip"] else 0)
    sys.exit(1 if should_skip else 0)


if __name__ == "__main__":
    main()
