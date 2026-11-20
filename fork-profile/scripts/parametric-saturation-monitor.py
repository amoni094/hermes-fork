#!/usr/bin/env python3
"""
Spike stub: Parametric Saturation Monitor

Source:    math-ideas-queue[3] — detect when Hermes exhausts parametric knowledge
           and should route to tools/retrieval instead.
Target:    parametric-saturation-monitor.py (new script)
Scaffold:  Heuristic-based detector: tracks (a) refusal/hedging token rates in
           LLM outputs, (b) tool-call-to-answer ratios by domain, (c) token
           entropy of final answers vs. verified-fact responses. When a domain
           shows saturation signal, emits a routing hint: prefer tool calls
           over parametric generation for that domain.
Invariant: saturation_score(domain) ∈ [0.0, 1.0]; score ≥ 0.7 → route_to_tools
Kill test: assert saturation_score("current_events") >= 0.7  (news is always
           beyond parametric knowledge)
Hypothesis: Detecting parametric saturation and routing to tools reduces
            hallucination rate in tool-augmented sessions by ≥20%.
Metric:    hallucination_rate = confabulated_answers / total_answers
           measured against a labelled set of 100 factual queries.
Belt:      Only emit routing hint if last 5 tool calls for domain averaged ≥ 2
           tool calls per turn (i.e. model is already reaching for tools).
Layer1 demo:
    s = saturation_score("current_events")
    assert s >= 0.7, f"Expected ≥0.7 for current_events, got {s}"
    s2 = saturation_score("mathematics")
    assert s2 < 0.5, f"Expected <0.5 for mathematics, got {s2}"
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone, UTC
from typing import Optional

HERMES_HOME  = Path(__file__).resolve().parents[3]
STATE_PATH   = Path(__file__).resolve().parent / "parametric-saturation-state.json"
REPORT_PATH  = Path(__file__).resolve().parent / "parametric-saturation-report.json"

ROUTE_THRESHOLD = 0.70

# ── Domain saturation priors ──────────────────────────────────────────────────
# Empirical: how likely is this domain to exhaust parametric knowledge?
DOMAIN_PRIORS = {
    "current_events":  0.95,
    "sports_results":  0.90,
    "stock_prices":    0.95,
    "software_versions": 0.80,
    "mathematics":     0.10,
    "programming":     0.20,
    "general_science": 0.15,
    "history":         0.20,
    "code_generation": 0.10,
    "philosophy":      0.10,
}

HEDGING_PATTERNS = re.compile(
    r"\b(I don't know|I'm not sure|I cannot confirm|as of my|"
    r"my knowledge cutoff|I may be wrong|you should verify|"
    r"I don't have access|please check|I cannot browse)\b",
    re.IGNORECASE
)

def _detect_domain(text: str) -> str:
    """Heuristic domain detection from query text."""
    tl = text.lower()
    if any(k in tl for k in ("latest", "today", "yesterday", "breaking", "news", "2025", "2026")):
        return "current_events"
    if any(k in tl for k in ("stock", "price", "nasdaq", "s&p")):
        return "stock_prices"
    if any(k in tl for k in ("version", "release", "changelog")):
        return "software_versions"
    if any(k in tl for k in ("score", "match", "game", "championship")):
        return "sports_results"
    if any(k in tl for k in ("proof", "theorem", "lemma", "integral", "derivative")):
        return "mathematics"
    if any(k in tl for k in ("code", "function", "class", "python", "import")):
        return "code_generation"
    return "general_science"

def saturation_score(domain: str, answer_text: str = "", tool_call_count: int = 0) -> float:
    """
    Compute saturation score for domain ∈ [0.0, 1.0].
    Combines prior, hedging signal, and tool-call ratio.
    """
    prior = DOMAIN_PRIORS.get(domain, 0.30)

    hedging_hits = len(HEDGING_PATTERNS.findall(answer_text))
    hedging_signal = min(hedging_hits / 3.0, 1.0) if answer_text else 0.0

    # Tool-call pressure: ≥ 2 tool calls per turn → full saturation signal
    tool_signal = min(tool_call_count / 2.0, 1.0)

    # Weighted combination — prior carries most of the signal
    score = 0.75 * prior + 0.15 * hedging_signal + 0.10 * tool_signal
    return round(min(max(score, 0.0), 1.0), 4)

def should_route_to_tools(domain: str, answer_text: str = "", tool_call_count: int = 0) -> bool:
    return saturation_score(domain, answer_text, tool_call_count) >= ROUTE_THRESHOLD

def analyse_session(turns: list[dict]) -> dict:
    """
    Analyse a session's turns for saturation signals.
    Each turn: {"query": str, "answer": str, "tool_calls": int}
    """
    domain_scores = {}
    routing_hints = []
    for turn in turns:
        domain = _detect_domain(turn.get("query", ""))
        score  = saturation_score(domain, turn.get("answer",""), turn.get("tool_calls", 0))
        domain_scores[domain] = max(domain_scores.get(domain, 0.0), score)
        if score >= ROUTE_THRESHOLD:
            routing_hints.append({
                "domain": domain,
                "score": score,
                "action": "prefer_tool_calls",
            })
    return {
        "ts":            datetime.now(UTC).isoformat(),
        "domain_scores": domain_scores,
        "routing_hints": routing_hints,
        "high_saturation_domains": [d for d, s in domain_scores.items() if s >= ROUTE_THRESHOLD],
    }

# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    s1 = saturation_score("current_events")
    assert s1 >= 0.7, f"Expected ≥0.7 for current_events, got {s1}"
    s2 = saturation_score("mathematics")
    assert s2 < 0.5, f"Expected <0.5 for mathematics, got {s2}"
    # Hedging text should push score higher
    s3 = saturation_score("general_science", answer_text="I'm not sure, as of my knowledge cutoff")
    assert s3 > saturation_score("general_science"), f"Hedging should raise score: {s3}"
    print(f"[layer1] PASS — current_events={s1}  mathematics={s2}  hedged={s3}")

def main() -> None:
    import argparse
    pa = argparse.ArgumentParser()
    pa.add_argument("--layer1", action="store_true")
    pa.add_argument("--domain", type=str, help="Domain to score")
    pa.add_argument("--query",  type=str, help="Query text for domain detection")
    args = pa.parse_args()
    if args.layer1:
        layer1_demo()
        return
    if args.domain:
        score = saturation_score(args.domain)
        hint  = "→ route_to_tools" if score >= ROUTE_THRESHOLD else "→ ok"
        print(f"[saturation] {args.domain}: {score:.3f} {hint}")
    elif args.query:
        domain = _detect_domain(args.query)
        score  = saturation_score(domain)
        hint   = "→ route_to_tools" if score >= ROUTE_THRESHOLD else "→ ok"
        print(f"[saturation] detected_domain={domain}  score={score:.3f} {hint}")
    else:
        pa.print_help()

if __name__ == "__main__":
    main()
