#!/usr/bin/env python3
"""
minority-sentinel.py — Meta-classifier for Hermes swarm/multi-agent consensus.

From: arXiv:2606.29270 "Minority Sentinel: When to Overturn Majority Voting
      in Multi-Agent LLM Debates" (He et al., 2026, UNSW/Euler AI)
      AgentSearch Workshop at SIGIR 2026, Melbourne, Australia

Key insight: LLMs share pretraining corpora → errors are correlated → majority
systematically suppresses correct minority opinions ("Minority Truth" phenomenon).
~25% of divergent cases have the minority holding the correct answer.

Minority Sentinel extracts a multi-dimensional "debate fingerprint" from debate logs
and applies a meta-classifier to decide when to overturn majority voting.
Achieves 81.2% Flip Precision with positive Net Gain across 6 datasets/20 trials.

CRITICAL: LLM-as-Judge baseline yields NEGATIVE Net Gain despite higher recall.
The non-LLM classifier (feature-based) is safer because flip SAFETY > recovery volume.

Hermes integration:
  - hermes-swarm-consensus: add minority sentinel check before returning consensus
  - hermes-role-pipelines: use when workers disagree and majority could be wrong
  - adversarial-review: detect when majority is collectively wrong

Usage:
  python3 minority-sentinel.py analyze --verdicts '[{"agent":"a","verdict":"PASS","confidence":0.9,"reasoning":"..."}]'
  python3 minority-sentinel.py check --json-file /path/to/swarm-output.json
  python3 minority-sentinel.py stats

Output: JSON with:
  {should_overturn, confidence, minority_verdict, fingerprint, reason, safety_score}

The "debate fingerprint" features (from the paper):
  1. agreement_rate: fraction of agents agreeing with majority
  2. minority_confidence_delta: how much more confident the minority is vs majority
  3. reasoning_divergence: lexical divergence between majority/minority reasoning
  4. minority_specificity: minority provides more specific evidence (entity count, citations)
  5. majority_certainty_hedging: majority uses hedging language ("probably", "likely")
  6. minority_unique_claims: minority raises claims not addressed by majority
  7. confidence_variance: variance in confidence across all agents

Calibration: Flip Precision is the key metric (precision of overturning decisions).
             False flips (overturning a correct majority) are the primary risk.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

HERMES_HOME = Path.home() / ".hermes"
STATS_PATH = HERMES_HOME / "cache" / "minority-sentinel-stats.jsonl"

# ─────────────────── Debate Fingerprint Extraction ──────────────────────────

def _extract_fingerprint(verdicts: list[dict]) -> dict[str, Any]:
    """
    Extract debate fingerprint features from a list of agent verdicts.
    
    Each verdict: {agent, verdict, confidence (0-1), reasoning (str)}
    """
    if not verdicts or len(verdicts) < 2:
        return {}

    # Count verdicts
    from collections import Counter
    verdict_counts = Counter(v.get("verdict", "").upper() for v in verdicts)
    if not verdict_counts:
        return {}

    majority_verdict, majority_count = verdict_counts.most_common(1)[0]
    n = len(verdicts)
    agreement_rate = majority_count / n

    # Split majority/minority groups
    majority_group = [v for v in verdicts if v.get("verdict", "").upper() == majority_verdict]
    minority_group = [v for v in verdicts if v.get("verdict", "").upper() != majority_verdict]

    if not minority_group:
        return {"agreement_rate": 1.0, "no_minority": 1.0}

    # Feature 1: agreement_rate
    f_agreement = agreement_rate

    # Feature 2: minority_confidence_delta
    maj_conf = sum(v.get("confidence", 0.5) for v in majority_group) / len(majority_group)
    min_conf = sum(v.get("confidence", 0.5) for v in minority_group) / len(minority_group)
    f_conf_delta = min_conf - maj_conf  # positive = minority more confident

    # Feature 3: reasoning_divergence (Jaccard of word sets)
    def words(group):
        text = " ".join(v.get("reasoning", "") for v in group)
        return set(re.sub(r"[^\w\s]", "", text.lower()).split())
    maj_words = words(majority_group)
    min_words = words(minority_group)
    union = maj_words | min_words
    f_divergence = 1.0 - (len(maj_words & min_words) / len(union)) if union else 0.0

    # Feature 4: minority_specificity (named entities, citations, numbers in reasoning)
    def specificity(group):
        text = " ".join(v.get("reasoning", "") for v in group)
        # Count capitalized tokens, numbers, arXiv IDs, quoted strings
        caps = len(re.findall(r'\b[A-Z][A-Za-z]+\b', text))
        nums = len(re.findall(r'\b\d+\.?\d*\b', text))
        refs = len(re.findall(r'arXiv|doi|citation|study|paper|research|\[[\d,]+\]', text, re.I))
        return (caps + nums + refs) / max(len(text.split()), 1)
    f_specificity = specificity(minority_group) - specificity(majority_group)

    # Feature 5: majority_certainty_hedging
    def hedge_rate(group):
        text = " ".join(v.get("reasoning", "") for v in group).lower()
        hedges = re.findall(r'\b(probably|likely|might|perhaps|possibly|could be|seems|appears|uncertain)\b', text)
        words_total = max(len(text.split()), 1)
        return len(hedges) / words_total
    f_hedging = hedge_rate(majority_group) - hedge_rate(minority_group)

    # Feature 6: minority_unique_claims (claims in minority not in majority)
    def unique_claims(source_words, other_words, text_len):
        unique = source_words - other_words
        return len(unique) / max(text_len, 1)
    min_text_len = max(len(" ".join(v.get("reasoning","") for v in minority_group).split()), 1)
    f_unique: float = len(min_words - maj_words) / min_text_len

    # Feature 7: confidence_variance across all agents
    all_confs = [v.get("confidence", 0.5) for v in verdicts]
    mean_conf = sum(all_confs) / len(all_confs)
    f_variance = sum((c - mean_conf) ** 2 for c in all_confs) / len(all_confs)

    return {
        "agreement_rate": round(f_agreement, 4),
        "minority_confidence_delta": round(f_conf_delta, 4),
        "reasoning_divergence": round(f_divergence, 4),
        "minority_specificity": round(f_specificity, 4),
        "majority_hedging": round(f_hedging, 4),
        "minority_unique_claims": round(f_unique, 4),
        "confidence_variance": round(f_variance, 4),
        "majority_verdict": majority_verdict,
        "minority_verdicts": [v.get("verdict","").upper() for v in minority_group],
        "n_majority": len(majority_group),
        "n_minority": len(minority_group),
    }


def _sentinel_score(fp: dict) -> tuple[float, list[str]]:
    """
    Compute a flip-safety score from the fingerprint.
    
    Designed conservatively: only flip when multiple strong signals align.
    False flips (wrong majority → wrong minority) are the primary risk.
    
    Returns (score, reasons) where score > 0.6 → consider overturning.
    """
    if not fp or fp.get("no_minority"):
        return 0.0, ["unanimous agreement — no minority to consider"]

    score = 0.0
    reasons = []

    # Strong signal: minority significantly more confident
    delta = fp.get("minority_confidence_delta", 0)
    if delta > 0.2:
        score += 0.3
        reasons.append(f"minority {delta:.2f} more confident than majority")
    elif delta > 0.1:
        score += 0.15
        reasons.append(f"minority marginally more confident (+{delta:.2f})")

    # Strong signal: majority is hedging (uncertain)
    hedging = fp.get("majority_hedging", 0)
    if hedging > 0.02:
        score += 0.2
        reasons.append(f"majority uses hedging language (rate={hedging:.3f})")

    # Signal: minority is more specific/evidence-backed
    specificity = fp.get("minority_specificity", 0)
    if specificity > 0.005:
        score += 0.15
        reasons.append("minority reasoning more specific/evidence-backed")

    # Signal: reasoning is highly divergent (not just different words, different logic)
    divergence = fp.get("reasoning_divergence", 0)
    if divergence > 0.6:
        score += 0.1
        reasons.append(f"high reasoning divergence ({divergence:.2f})")

    # Signal: minority raises unique claims not addressed by majority
    unique = fp.get("minority_unique_claims", 0)
    if unique > 0.05:
        score += 0.15
        reasons.append("minority raises unique claims not addressed by majority")

    # Strong de-escalation: high agreement rate (majority is very dominant)
    agreement = fp.get("agreement_rate", 1.0)
    if agreement > 0.8:
        score -= 0.25
        reasons.append(f"strong majority ({agreement:.0%}) — flip risk is higher")
    elif agreement > 0.66:
        score -= 0.1
        reasons.append(f"clear majority ({agreement:.0%})")

    # De-escalation: only 1 minority agent (very small minority)
    if fp.get("n_minority", 0) == 1 and fp.get("n_majority", 0) >= 3:
        score -= 0.15
        reasons.append("single agent in minority vs 3+ majority — flip risk elevated")

    return round(max(0.0, min(1.0, score)), 4), reasons


def analyze_verdicts(verdicts: list[dict]) -> dict[str, Any]:
    """Main entry point: analyze verdicts and decide whether to overturn majority."""
    fp = _extract_fingerprint(verdicts)
    if not fp:
        return {
            "should_overturn": False,
            "confidence": 0.0,
            "reason": "insufficient verdicts (<2 agents or no disagreement)",
            "fingerprint": {},
        }

    score, reasons = _sentinel_score(fp)

    # Lexical proxy threshold — NOT from the paper (paper uses LightGBM on 22-d fingerprint).
    # This heuristic is uncalibrated; treat as a soft signal, not a measured precision guarantee.
    OVERTURN_THRESHOLD = 0.55

    # Conjunction gate (adversarial-review fix 2026-09-09):
    # Require ALL of: score >= threshold, exactly 1 minority agent, majority hedging detected.
    # Additive score alone is insufficient; the conjunction guards against false flips.
    n_minority = fp.get("n_minority", 0)
    majority_hedging = fp.get("majority_hedging", 0.0) > 0.1
    conjunction_gate = (score >= OVERTURN_THRESHOLD) and (n_minority == 1) and majority_hedging

    # Find minority verdict (most common minority)
    from collections import Counter
    minority_vs: Counter[str] = Counter(fp.get("minority_verdicts", []))
    minority_verdict = minority_vs.most_common(1)[0][0] if minority_vs else "UNKNOWN"

    return {
        "should_overturn": conjunction_gate,
        "flip_safety_score": score,
        "threshold": OVERTURN_THRESHOLD,
        "conjunction_gate": conjunction_gate,
        "conjunction_components": {
            "score_ok": score >= OVERTURN_THRESHOLD,
            "single_minority": n_minority == 1,
            "majority_hedging": majority_hedging,
        },
        "majority_verdict": fp.get("majority_verdict"),
        "minority_verdict": minority_verdict,
        "n_majority": fp.get("n_majority"),
        "n_minority": fp.get("n_minority"),
        "fingerprint": fp,
        "reasons": reasons,
        "recommendation": (
            f"OVERTURN: minority verdict '{minority_verdict}' is likely correct"
            if conjunction_gate
            else f"KEEP MAJORITY: '{fp.get('majority_verdict')}' "
                 f"(conjunction gate not met: score={score:.2f}, "
                 f"single_minority={n_minority==1}, hedging={majority_hedging})"
        ),
        "warning": (
            "Note: Only flip when multiple strong signals align. "
            "False flips are the primary risk (LLM-as-Judge baseline yields NEGATIVE net gain)."
        ),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─────────────────── Stats ──────────────────────────────────────────────────

def _load_stats() -> list[dict]:
    if not STATS_PATH.exists():
        return []
    entries = []
    with STATS_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _save_stat(entry: dict) -> None:
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATS_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ─────────────────── CLI ────────────────────────────────────────────────────

def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        verdicts = json.loads(args.verdicts)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        return 1
    result = analyze_verdicts(verdicts)
    print(json.dumps(result, indent=2))
    # Auto-save stats
    _save_stat({"event": "analyze", "result": result, "n_agents": len(verdicts)})
    return 0


def cmd_check_file(args: argparse.Namespace) -> int:
    try:
        data = json.loads(Path(args.json_file).read_text())
    except Exception as e:
        print(f"ERROR reading file: {e}", file=sys.stderr)
        return 1

    # Support multiple formats
    if isinstance(data, list):
        verdicts = data
    elif isinstance(data, dict) and "verdicts" in data:
        verdicts = data["verdicts"]
    elif isinstance(data, dict) and "agents" in data:
        verdicts = data["agents"]
    else:
        print("ERROR: JSON must be a list of verdicts or {verdicts: [...]} or {agents: [...]}", file=sys.stderr)
        return 1

    result = analyze_verdicts(verdicts)
    print(json.dumps(result, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    entries = _load_stats()
    flipped = sum(1 for e in entries if e.get("result", {}).get("should_overturn"))
    total = len(entries)
    print(json.dumps({
        "total_analyses": total,
        "total_flipped": flipped,
        "flip_rate": round(flipped / total, 3) if total else 0,
        "note": "Flip Precision tracking requires outcome recording — use calibrate sub-command",
    }, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Minority Sentinel meta-classifier for Hermes swarm consensus (arXiv:2606.29270)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Analyze verdicts for minority truth")
    p_an.add_argument("--verdicts", "-v", required=True,
                      help='JSON array of {agent, verdict, confidence, reasoning}')
    p_an.set_defaults(func=cmd_analyze)

    p_cf = sub.add_parser("check", help="Check a JSON file of swarm verdicts")
    p_cf.add_argument("--json-file", "-f", required=True)
    p_cf.set_defaults(func=cmd_check_file)

    p_st = sub.add_parser("stats", help="Show sentinel statistics")
    p_st.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
