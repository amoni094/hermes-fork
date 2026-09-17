#!/usr/bin/env python3
"""
dcr-reconcile.py — Divergent-Convergent Reconciliation for Hermes.

Implements the DCR pattern from arXiv:2608.15303 (93.3% AIME with ~27% less
compute than uniform scaling). Reduces 2-4 independently generated candidate
solutions into a single reconciled answer, gated on actual disagreement.

Usage:
    python3 dcr-reconcile.py check --candidates '<JSON>'
    python3 dcr-reconcile.py reconcile --candidates '<JSON>' [--domain math|code|planning|general]
    python3 dcr-reconcile.py prompt --candidates '<JSON>' [--domain math|code|planning|general]

candidates JSON format:
    [
        {"id": "A", "answer": "...", "reasoning": "...", "confidence": 0.9},
        {"id": "B", "answer": "...", "reasoning": "...", "confidence": 0.8},
        {"id": "C", "answer": "...", "reasoning": "...", "confidence": 0.7}
    ]

Commands:
    check       — check if candidates actually disagree (gate on this before Phase 2)
    reconcile   — full reconcile with disagreement analysis + ranked synthesis prompt
    prompt      — emit just the Phase 2 reconcile prompt (for embedding in delegate_task)

Exit codes:
    0 = success (all subcommands)
    2 = error / malformed input
    Note: cmd_check returns 0 regardless of agreement; read JSON field "phase2_needed"
"""

import argparse
import json
import sys
from difflib import SequenceMatcher
from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Agreement detection
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize answer text for comparison.

    Strips filler phrases and trailing punctuation so that semantically
    equivalent answers like '42' and 'The answer is 42.' compare as equal.
    """
    import re
    t = text.lower().strip()
    # Remove common filler phrases
    t = re.sub(r'\b(the answer is|therefore|thus|so|hence|result:|answer:)\b', '', t)
    # Strip trailing punctuation (period, comma, exclamation)
    t = re.sub(r'[.,;!?]+$', '', t.strip())
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _string_similarity(a: str, b: str) -> float:
    """Normalized string similarity [0, 1]."""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _answers_agree(candidates: list[dict], threshold: float = 0.85) -> tuple[bool, dict]:
    """
    Check if all candidates agree on the answer.

    Returns (agree: bool, analysis: dict).
    Candidates agree if ALL pairwise answer similarities >= threshold.
    """
    answers = [c.get("answer", "") for c in candidates]
    n = len(answers)

    if n <= 1:
        return True, {"note": "Single candidate — no comparison needed"}

    pairwise = []
    min_sim = 1.0
    max_sim = 0.0

    for i in range(n):
        for j in range(i + 1, n):
            sim = _string_similarity(answers[i], answers[j])
            pairwise.append({
                "pair": (candidates[i]["id"], candidates[j]["id"]),
                "similarity": round(sim, 3),
            })
            min_sim = min(min_sim, sim)
            max_sim = max(max_sim, sim)

    agree = min_sim >= threshold
    return agree, {
        "agree": agree,
        "min_similarity": round(min_sim, 3),
        "max_similarity": round(max_sim, 3),
        "threshold": threshold,
        "pairwise": pairwise,
        "n_candidates": n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Disagreement analysis
# ─────────────────────────────────────────────────────────────────────────────

def _find_disagreements(candidates: list[dict]) -> list[str]:
    """
    Identify specific points of disagreement between candidates.
    Heuristic: extract unique key phrases from each candidate's reasoning
    that do not appear in others'.
    """
    import re

    def key_phrases(text: str) -> set[str]:
        """Extract candidate key phrases (noun phrases, numbers, named items)."""
        # Numbers and measurements
        nums = set(re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:ms|kb|mb|gb|%|x|px|tokens|steps))?\b', text.lower()))
        # Capitalized words (likely names/concepts)
        caps = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', text))
        # Short quoted strings
        quoted = set(re.findall(r'"([^"]{3,30})"', text))
        return nums | caps | quoted

    candidate_phrases = [
        (c["id"], key_phrases(c.get("reasoning", "") + " " + c.get("answer", "")))
        for c in candidates
    ]

    disagreements = []
    for i, (cid, phrases) in enumerate(candidate_phrases):
        other_phrases: set[str] = set()
        for j, (_, other) in enumerate(candidate_phrases):
            if j != i:
                other_phrases |= other
        unique = phrases - other_phrases
        if unique:
            sample = sorted(unique)[:3]
            disagreements.append(f"Candidate {cid} uniquely claims: {', '.join(sample)}")

    return disagreements or ["Candidates use different approaches or framings"]


# ─────────────────────────────────────────────────────────────────────────────
# Reconcile prompt generation
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_INSTRUCTIONS = {
    "math": (
        "Focus on mathematical correctness. Check each step for arithmetic errors, "
        "off-by-one errors, and incorrect formula application. The correct answer "
        "must be derivable from the given constraints without additional assumptions."
    ),
    "code": (
        "Focus on correctness and edge cases. Consider: does the code handle empty "
        "inputs, boundary values, and error conditions? Check for off-by-one errors, "
        "resource leaks, and incorrect algorithm complexity claims."
    ),
    "planning": (
        "Focus on feasibility and completeness. Are all dependencies satisfied? "
        "Are irreversible steps identified? Is the plan correct under adversarial "
        "inputs or partial failures? Which plan has the most robust rollback path?"
    ),
    "general": (
        "Focus on factual accuracy and logical consistency. Which answer best "
        "satisfies all stated constraints? Which reasoning chain has the fewest "
        "unsupported assumptions?"
    ),
}


def _build_reconcile_prompt(
    candidates: list[dict],
    disagreements: list[str],
    domain: str = "general",
    analysis: dict | None = None,
) -> str:
    """Build the Phase 2 DCR reconciliation prompt."""

    domain_instr = DOMAIN_INSTRUCTIONS.get(domain, DOMAIN_INSTRUCTIONS["general"])

    # Format candidates
    formatted = []
    for c in candidates:
        conf_str = f" (confidence: {c['confidence']:.0%})" if "confidence" in c else ""
        reasoning = c.get("reasoning", "")
        answer = c.get("answer", "")
        formatted.append(
            f"--- Candidate {c['id']}{conf_str} ---\n"
            f"Answer: {answer}\n"
            f"Reasoning: {reasoning}"
        )

    candidates_block = "\n\n".join(formatted)

    # Format disagreements
    disagreement_block = "\n".join(f"  - {d}" for d in disagreements)

    prompt = f"""You are performing a Phase 2 Divergent-Convergent Reconciliation.

{len(candidates)} independent candidates were generated for the same task.
They disagree on the following specific points:

{disagreement_block}

--- CANDIDATES ---

{candidates_block}

--- END CANDIDATES ---

Domain context: {domain_instr}

Your task:
1. For each point of disagreement listed above, state which candidate is correct
   and why (cite specific evidence or reasoning steps, not just preference).
2. Identify any candidate that makes a clear error — state what the error is.
3. Synthesize a final answer that:
   - Takes the correct elements from each candidate
   - Resolves every disagreement with an explicit decision and rationale
   - Does NOT average or hedge — make a definitive choice
4. State your final answer clearly, followed by a confidence score (0.0-1.0).

Format your response as:
DISAGREEMENT RESOLUTION:
[For each disagreement: which is correct + why]

SYNTHESIS:
[Final reconciled answer]

CONFIDENCE: [0.0-1.0]
"""

    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# CLI commands
# ─────────────────────────────────────────────────────────────────────────────

def cmd_check(args: argparse.Namespace) -> int:
    """Check if candidates actually disagree."""
    try:
        candidates = json.loads(args.candidates)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        return 2

    # Guard: auto-assign "id" if missing (avoids KeyError downstream)
    for i, c in enumerate(candidates):
        if "id" not in c:
            c["id"] = f"C{i}"

    agree, analysis = _answers_agree(candidates, threshold=args.threshold)

    result = {
        "phase2_needed": not agree,
        "recommendation": (
            "Candidates agree -- skip Phase 2 reconcile, use highest-confidence answer."
            if agree else
            "Candidates disagree -- run Phase 2 DCR reconciliation."
        ),
        "agreement_analysis": analysis,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    print(json.dumps(result, indent=2))
    # Unix convention: 0 = success (agreement checked; result in JSON).
    # phase2_needed field carries the semantic; exit code is not the signal.
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    """Emit the Phase 2 reconcile prompt."""
    try:
        candidates = json.loads(args.candidates)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        return 2

    # Guard: auto-assign "id" if missing (avoids KeyError downstream)
    for i, c in enumerate(candidates):
        if "id" not in c:
            c["id"] = f"C{i}"

    agree, analysis = _answers_agree(candidates)
    if agree and not args.force:
        result = {
            "phase2_needed": False,
            "note": "Candidates agree. Use --force to generate prompt anyway.",
            "analysis": analysis,
        }
        print(json.dumps(result, indent=2))
        return 0  # success; phase2_needed=false in JSON

    disagreements = _find_disagreements(candidates)
    prompt = _build_reconcile_prompt(candidates, disagreements, domain=args.domain, analysis=analysis)

    result = {
        "phase2_needed": not agree,
        "disagreements": disagreements,
        "reconcile_prompt": prompt,
        "domain": args.domain,
        "n_candidates": len(candidates),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    """Full reconcile: check + emit prompt + usage instructions."""
    try:
        candidates = json.loads(args.candidates)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        return 2

    # Guard: auto-assign "id" if missing (avoids KeyError downstream)
    for i, c in enumerate(candidates):
        if "id" not in c:
            c["id"] = f"C{i}"

    agree, analysis = _answers_agree(candidates)

    if agree and not args.force:
        # Pick highest confidence
        best = max(candidates, key=lambda c: c.get("confidence", 0.5))
        result = {
            "status": "agreement",
            "phase2_skipped": True,
            "recommendation": "All candidates agree — use highest-confidence answer.",
            "selected": best,
            "agreement_analysis": analysis,
        }
        print(json.dumps(result, indent=2))
        return 0

    disagreements = _find_disagreements(candidates)
    prompt = _build_reconcile_prompt(candidates, disagreements, domain=args.domain, analysis=analysis)

    result = {
        "status": "disagreement" if not agree else "forced_reconcile",
        "phase2_needed": True,
        "disagreements": disagreements,
        "agreement_analysis": analysis,
        "reconcile_prompt": prompt,
        "usage": (
            "Pass reconcile_prompt as the user message in your next call. "
            "The model's response is the Phase 2 synthesis. "
            "Parse CONFIDENCE: <float> from the response."
        ),
        "domain": args.domain,
        "n_candidates": len(candidates),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    print(json.dumps(result, indent=2))
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="DCR reconciler: Divergent-Convergent Reconciliation (arXiv:2608.15303)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Check if candidates agree (gate for Phase 2)")
    p_check.add_argument("--candidates", required=True, help="JSON array of candidate objects")
    p_check.add_argument("--threshold", type=float, default=0.85,
                         help="Similarity threshold to consider candidates as agreeing (default: 0.85)")

    # prompt
    p_prompt = sub.add_parser("prompt", help="Emit the Phase 2 reconcile prompt")
    p_prompt.add_argument("--candidates", required=True)
    p_prompt.add_argument("--domain", default="general",
                          choices=["math", "code", "planning", "general"])
    p_prompt.add_argument("--force", action="store_true", help="Emit prompt even if candidates agree")

    # reconcile
    p_rec = sub.add_parser("reconcile", help="Full reconcile: check + prompt + instructions")
    p_rec.add_argument("--candidates", required=True)
    p_rec.add_argument("--domain", default="general",
                       choices=["math", "code", "planning", "general"])
    p_rec.add_argument("--force", action="store_true", help="Reconcile even if candidates agree")

    args = parser.parse_args()

    if args.command == "check":
        return cmd_check(args)
    elif args.command == "prompt":
        return cmd_prompt(args)
    elif args.command == "reconcile":
        return cmd_reconcile(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())


# ── Plan-Level SMC (Sequential Monte Carlo) ──────────────────────────────────
# Based on NeSyFS twisted SMC pattern (arXiv:2607.28942).
# Use when you have N candidate tool-plans and want to weight/prune them
# before full execution, using cheap simulation or partial execution results.

def smc_weight_plans(
    candidates: list[dict],
    *,
    prior_weights: list[float] | None = None,
    sim_results: list[dict] | None = None,
    n_survivors: int = 3,
) -> dict[str, Any]:
    """
    Weight and prune a set of candidate plans using SMC-style importance sampling.

    Args:
        candidates: list of plan dicts, each with at least {"id": str, "plan": str}
        prior_weights: initial importance weights (uniform if None)
        sim_results: optional simulation/partial execution results per candidate,
                     each dict may have {"success": bool, "cost": float, "notes": str}
        n_survivors: how many plans to keep after pruning

    Returns:
        dict with:
          survivors: list of (candidate, weight) sorted by weight desc, top n_survivors
          pruned: list of pruned candidates
          ess: effective sample size (N_eff = (sum w)^2 / sum w^2)
          recommendation: str
    """
    import math

    n = len(candidates)
    if n == 0:
        return {"survivors": [], "pruned": [], "ess": 0.0, "recommendation": "no candidates"}

    # Initialize weights
    if prior_weights is None:
        weights = [1.0 / n] * n
    else:
        total = sum(prior_weights) or 1.0
        weights = [w / total for w in prior_weights]

    # Update weights from simulation results
    if sim_results:
        for i, (w, res) in enumerate(zip(weights, sim_results)):
            if res is None:
                continue
            likelihood = 1.0
            if res.get("success") is True:
                likelihood *= 2.0
            elif res.get("success") is False:
                likelihood *= 0.1
            cost = float(res.get("cost", 1.0))
            if cost > 0:
                likelihood *= math.exp(-0.3 * math.log(cost + 1))
            weights[i] = w * likelihood

    # Normalize
    total = sum(weights)
    if total == 0:
        weights = [1.0 / n] * n
        total = 1.0
    weights = [w / total for w in weights]

    # Effective sample size: ESS = (sum w)^2 / sum w^2 — here sum w = 1.0
    ess = 1.0 / sum(w * w for w in weights) if any(w > 0 for w in weights) else 0.0

    # Sort and split
    ranked = sorted(zip(candidates, weights), key=lambda x: x[1], reverse=True)
    survivors = ranked[:n_survivors]
    pruned = ranked[n_survivors:]

    recommendation = (
        f"Keep top {len(survivors)}/{n} plans. "
        f"ESS={ess:.1f}/{n} "
        f"({'good diversity' if ess >= n * 0.5 else 'low diversity — consider re-sampling'})."
    )

    return {
        "survivors": [{"candidate": c, "weight": round(w, 4)} for c, w in survivors],
        "pruned": [{"candidate": c, "weight": round(w, 4)} for c, w in pruned],
        "ess": round(ess, 2),
        "recommendation": recommendation,
    }

