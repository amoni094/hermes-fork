#!/usr/bin/env python3
"""
reasoning-complexity-classifier.py — Adaptive reasoning depth classifier for Hermes.

Addresses over-reasoning and under-reasoning failure modes identified in:
  arXiv:2608.26442 "Don't Overthink, Don't Underthink" (Mia & Amini, 2026)
  arXiv:2606.03965 ACTS "Agentic Chain-of-Thought Steering" (Xia et al., 2026)
  autonomous-agent-loop-design § Fast/Slow ReAct pattern

Key insight: reasoning requirements evolve dynamically through planning, tool use,
memory retrieval, and agent-to-agent interactions. Fixed token budgets cause:
  - Over-reasoning: higher computational cost without proportional accuracy gains
  - Under-reasoning: consistently incorrect or incomplete solutions

This classifier runs BEFORE expensive LLM calls to right-size reasoning depth.

Usage:
  python3 reasoning-complexity-classifier.py classify --task "fix bug in X" [--context "..."]
  python3 reasoning-complexity-classifier.py select-frameworks --task "..." [--context "..."] [--level L0-L3] [--active-frameworks '["causal-check"]']
  python3 reasoning-complexity-classifier.py history [--session SID]
  python3 reasoning-complexity-classifier.py calibrate --session SID --task "..." --actual LEVEL --correct 1|0
  python3 reasoning-complexity-classifier.py stats

select-frameworks exit: 0=primary selected (or L0/L1 skip_frameworks with --treat-empty-ok),
  1=none apply (trivial L0/L1 empty primary — NOT a crash; proceed with no gates),
  2=insufficient context / invalid --level.
If --level is omitted, the level is the same value classify would emit (shared classify_task()).
If --level is passed, it MUST be that classify output (L0-L3); out-of-range is exit 2.

Output: JSON with {level, budget_tokens, strategy, rationale, evidence, recommended_frameworks}
  level: L0 (trivial) | L1 (routine) | L2 (complex) | L3 (critical)
  budget_tokens: suggested token budget for reasoning phase
  strategy: direct | chain | reflect | deliberate
  rationale: why this level was chosen
  evidence: list of signals that drove classification
  recommended_frameworks: script names to invoke (causal-check, hypothesize, lookahead, ...)

Integrates with:
  working-memory.py add-constraint --text "reasoning_budget: ..." (per-task)
  autonomous-agent-loop-design § Token Budget Discipline
  hermes-context-budgeting

Calibration: records predicted level vs actual outcome for accuracy-based calibration tracking.
  See ~/.hermes/cache/reasoning-calibration.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import re
import os
import sys
import time
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
CALIB_PATH = HERMES_HOME / "cache" / "reasoning-calibration.jsonl"


def _reasoning_runtime():
    import importlib.util
    p = Path(__file__).resolve().parent / "reasoning-hooks.py"
    spec = importlib.util.spec_from_file_location("reasoning_hooks_rt", p)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ─────────────────── Complexity Signal Weights ──────────────────────────────
# Signals that increase complexity, from "Don't Overthink, Don't Underthink"
# and ACTS literature on reasoning allocation.

ESCALATE_SIGNALS = {
    # Task type signals
    "multi_step": 0.4,          # "then", "after", "first ... then", "finally"
    "conditional": 0.3,          # "if", "unless", "depends on", "when"
    "tradeoff": 0.3,             # "versus", "compare", "weigh", "tradeoff"
    "irreversible": 0.5,         # "delete", "drop", "push", "deploy", "rm -rf"
    "design": 0.4,               # "design", "architect", "plan", "strategy"
    "debug_complex": 0.35,       # "why does", "root cause", "trace", "investigate"
    "causal_attribution": 0.4,   # "why did", "caused by", "root cause" → min L2
    "abductive_task": 0.4,       # "what explains", "hypothesis", "diagnose" → min L2
    "math_formal": 0.45,         # "prove", "verify", "formal", "theorem"
    "ambiguous": 0.3,            # "unclear", "it depends", "might", "could"
    # Context signals
    "has_constraints": 0.25,     # explicit constraints stated by user
    "high_stakes": 0.45,         # production, security, financial, medical
    "long_horizon": 0.35,        # multi-session, long-running, or >5 steps/stages/phases
}

DEESCALATE_SIGNALS = {
    # Simplicity signals
    "lookup": -0.4,              # "what is", "show me", "list", "how many"
    "formatting": -0.5,          # "format this", "convert", "translate"
    "confirmation": -0.4,        # "yes/no", "true/false", "does X support Y"
    "short_task": -0.3,          # task description < 30 words
    "single_file": -0.2,         # operates on exactly one file
}

# ─────────────────── Level Definitions ──────────────────────────────────────

LEVELS = {
    "L0": {
        "name": "trivial",
        "budget_tokens": 0,
        "strategy": "direct",
        "description": "Lookup, formatting, direct retrieval. No chain-of-thought needed.",
        "examples": ["what is X", "convert Y to Z", "list all X"],
    },
    "L1": {
        "name": "routine",
        "budget_tokens": 80,
        "strategy": "chain",
        "description": "Standard task with known pattern. Use CoD not full CoT (l01-token-efficiency skill).",
        "examples": ["fix this specific bug", "add test for function X", "update config"],
    },
    "L2": {
        "name": "complex",
        "budget_tokens": 1200,
        "strategy": "reflect",
        "description": "Multi-step planning, tradeoffs, or novel territory. Full CoT + reflection.",
        "examples": ["design the caching layer", "debug root cause of intermittent failure"],
    },
    "L3": {
        "name": "critical",
        "budget_tokens": 3000,
        "strategy": "deliberate",
        "description": "Irreversible or high-stakes. Extended deliberation + adversarial self-check.",
        "examples": ["deploy to production", "rm -rf / equivalent", "architectural overhaul"],
    },
}

# ─────────────────── Signal Detection ──────────────────────────────────────

def _horizon_step_count(text: str) -> int:
    """Count planning-horizon size from steps/stages/phases mentions.

    Uses the largest explicit N in phrases like '8 steps' / 'stage 7', else
    the number of step/stage/phase keyword occurrences.
    """
    explicit = [int(n) for n in re.findall(r"\b(\d+)\s*(?:steps?|stages?|phases?)\b", text)]
    hyphenated = [int(n) for n in re.findall(r"\b(\d+)[-/](?:steps?|stages?|phases?)\b", text)]
    numbered = [int(n) for n in re.findall(r"\b(?:step|stage|phase)\s*(\d+)\b", text)]
    if explicit or numbered or hyphenated:
        return max(explicit + numbered + hyphenated)
    return len(re.findall(r"\b(?:steps?|stages?|phases?)\b", text))


def _detect_signals(task: str, context: str = "") -> dict[str, float]:
    """Return {signal_name: weight} for all detected signals."""
    text = (task + " " + context).lower()
    detected = {}

    # Escalation patterns
    if re.search(r"\bthen\b|\bafter\b|\bfirst.*then\b|\bfinally\b|\bstep.*by.*step\b", text):
        detected["multi_step"] = ESCALATE_SIGNALS["multi_step"]
    if re.search(r"\bif\b|\bunless\b|\bdepends\b|\bwhen\b|\bgiven.*condition\b", text):
        detected["conditional"] = ESCALATE_SIGNALS["conditional"]
    if re.search(r"\bversus\b|\bvs\b|\bcompare\b|\btradeoff\b|\bweigh\b|\bpros.*cons\b|\bbetween.*and\b", text):
        detected["tradeoff"] = ESCALATE_SIGNALS["tradeoff"]
    # Context-aware irreversible detection (adversarial-review fix 2026-09-09).
    # "delete a comment/word/line" should NOT fire -- only structural/data deletions.
    _irrev_structural = re.search(
        r"\brm\s+-rf?\b|\bdestroy\b|\bwipe\b|\birreversible\b"
        r"|\bdrop\b.{0,40}\b(table|database|db|index|column|schema)\b"
        r"|\bdelete\s+(all|from|table|row|record|account|file|data|user|prod)\b"
        r"|\bdelete.*\b(database|db|table|record|account|user|production|repo|branch)\b"
        r"|\b(purge|truncate)\s+(table|data|db|database)\b",
        text, re.IGNORECASE
    )
    _irrev_deploy = re.search(
        r"\b(deploy|push)\b.*\b(production|prod|main|master)\b"
        r"|\bpush\s+to\s+(main|master|prod)\b"
        r"|\bdeploy\s+to\s+(production|prod|live|staging)\b",
        text, re.IGNORECASE
    )
    if _irrev_structural or _irrev_deploy:
        detected["irreversible"] = ESCALATE_SIGNALS["irreversible"]
    # Standalone deploy-to-production -> L3 floor (via _irrev_deploy_flag)
    if _irrev_deploy:
        detected["_irrev_deploy_flag"] = 1  # triggers hard L3 floor in _score_to_level
    # Filesystem wipe (rm -rf, wipe + target, destroy + target) -> L3 unconditionally
    _irrev_wipe = re.search(
        r'\brm\s+-[rf]{1,3}\b|\bwipe\b.*\b(/|disk|drive|filesystem|all|database|db|data|table|storage)\b'
        r'|\bdestroy\b.*\b(all|everything|database|db|cluster|server|instance)\b',
        text, re.IGNORECASE
    )
    if _irrev_wipe:
        detected["irreversible_critical"] = 0.4  # wipe is always L3
        detected["irreversible"] = ESCALATE_SIGNALS["irreversible"]
    # irreversible_critical: structural irreversible + production/security context -> L3
    if _irrev_structural and re.search(r"\bproduction\b|\bprod\b|\bsecurity\b", text, re.IGNORECASE):
        detected["irreversible_critical"] = 0.4  # extra push to ensure L3
    if _irrev_deploy and re.search(r"\bdelete\b|\bdrop\b|\bdestroy\b|\bwipe\b", text, re.IGNORECASE):
        detected["irreversible_critical"] = 0.4  # extra push to ensure L3
    if re.search(r"\bdesign\b|\barchitect\b|\bplan\b|\bstrateg\b|\bframework\b|\brefactor\b|\bmigrat\b|\brestructur\b|\bimplement\b|\bbuild\b.*\b(system|service|module|pipeline|algorithm|protocol)\b", text):
        detected["design"] = ESCALATE_SIGNALS["design"]
    if re.search(r"\bwhy does\b|\broot cause\b|\btrace\b|\binvestigat\b|\bdebug\b|\bdiagnos\b|\brace.condition\b|\bconcurrenc\b|\bdeadlock\b|\bthread.safe\b|\bmemory.leak\b", text):
        detected["debug_complex"] = ESCALATE_SIGNALS["debug_complex"]
    # Do not use bare "explains" — it double-counts with abductive "what explains".
    if re.search(
        r"\bwhy did\b|\bcaused by\b|\bbecause of\b|\broot cause\b|\battributed to\b|\breason for\b",
        text,
    ):
        detected["causal_attribution"] = ESCALATE_SIGNALS["causal_attribution"]
    if re.search(
        r"\bwhat explains\b|\bbest explanation\b|\bhypothesis\b|\bdiagnose\b|\binvestigate why\b",
        text,
    ):
        detected["abductive_task"] = ESCALATE_SIGNALS["abductive_task"]
    if re.search(r"\bprove\b|\bverif\b|\bformal\b|\btheorem\b|\blemma\b|\bmath\b", text):
        detected["math_formal"] = ESCALATE_SIGNALS["math_formal"]
    if re.search(r"\bunclear\b|\bit depends\b|\bmight\b|\bcould\b|\bperhaps\b|\bambiguous\b", text):
        detected["ambiguous"] = ESCALATE_SIGNALS["ambiguous"]
    if re.search(r"\bproduction\b|\bsecurity\b|\bfinancial\b|\bmedical\b|\bcritical\b", text):
        detected["high_stakes"] = ESCALATE_SIGNALS["high_stakes"]
    if re.search(r"\bmust\b|\bshould not\b|\bconstraint\b|\brequirement\b|\blimit\b", text):
        detected["has_constraints"] = ESCALATE_SIGNALS["has_constraints"]
    if re.search(r"\blong.term\b|\bmulti.session\b|\bevolution\b|\blong.running\b", text):
        detected["long_horizon"] = ESCALATE_SIGNALS["long_horizon"]
    if _horizon_step_count(text) > 5:
        detected["long_horizon"] = ESCALATE_SIGNALS["long_horizon"]

    # De-escalation patterns
    if re.search(r"\bwhat is\b|\bshow me\b|\blist\b|\bhow many\b|\bwhere is\b|\bwho is\b", text):
        detected["lookup"] = DEESCALATE_SIGNALS["lookup"]
    if re.search(r"\bformat\b|\bconvert\b|\btranslate\b|\bsummarize briefly\b", text):
        detected["formatting"] = DEESCALATE_SIGNALS["formatting"]
    if re.search(r"\byes or no\b|\btrue or false\b|\bdoes.*support\b|\bis.*correct\b", text):
        detected["confirmation"] = DEESCALATE_SIGNALS["confirmation"]
    # short_task de-escalation is suppressed when a strong expert-domain signal is present
    _strong_escalation = any(s in {"design", "debug_complex", "math_formal", "tradeoff", "conditional",
                                   "causal_attribution", "abductive_task"}
                              for s in detected)
    if len(task.split()) < 30 and not _strong_escalation:
        detected["short_task"] = DEESCALATE_SIGNALS["short_task"]
    if re.search(r"\bone file\b|\bsingle file\b|\bjust.*file\b", text):
        detected["single_file"] = DEESCALATE_SIGNALS["single_file"]

    return detected


def _recommend_frameworks(detected: dict) -> list[str]:
    """Map detected signals to reasoning-framework script names."""
    frameworks: list[str] = []
    if "causal_attribution" in detected:
        frameworks.append("causal-check")
    if "abductive_task" in detected:
        frameworks.append("hypothesize")
    if (
        "long_horizon" in detected
        or "irreversible" in detected
        or "irreversible_critical" in detected
        or "_irrev_deploy_flag" in detected
    ):
        frameworks.append("lookahead")
        frameworks.append("subplan-verify")
    return frameworks


def _score_to_level(score: float, detected: dict) -> str:
    """Map total signal score to complexity level.

    Hard floors guarantee safety classes are never downgraded by de-escalators.
    Priority: L3 floors checked first, then L2, then scored bands.
    """
    # L3 FLOORS — production-mutating, filesystem-wiping, or compound destructive ops.
    # These are safety class decisions; short_task/-0.3 cannot override them.
    if "irreversible_critical" in detected:
        # Compound: structural irreversible + production/security context, or deploy+delete
        return "L3"
    if "irreversible" in detected and "high_stakes" in detected:
        # Any destructive action in a high-stakes context (production, security, financial)
        return "L3"
    if "_irrev_deploy_flag" in detected:
        # Standalone deploy-to-production is L3 regardless of word count
        return "L3"
    # L2 FLOOR — single destructive action without production context
    if "irreversible" in detected:
        return "L2"
    # Score-based bands (de-escalators can operate freely below here)
    if score < 0.05:
        level = "L0"
    elif score < 0.4:
        level = "L1"
    elif score < 0.8:
        level = "L2"
    else:
        level = "L3"
    # Causal / abductive tasks warrant at least L2 (never L0/L1)
    if level in ("L0", "L1") and (
        "causal_attribution" in detected or "abductive_task" in detected
    ):
        return "L2"
    # Do not promote to L3 on causal/abductive (+ weak multi_step) alone.
    # L3 remains a safety class: irreversible / high-stakes / deploy / wipe.
    if level == "L3":
        l3_class = any(
            k in detected
            for k in (
                "irreversible",
                "irreversible_critical",
                "_irrev_deploy_flag",
                "high_stakes",
            )
        )
        if not l3_class:
            return "L2"
    return level


def _entropy_signal(task: str, context: str = "") -> dict:
    """Compute word-unigram entropy of task prompt as CoT phase-transition signal.

    Based on arXiv:2605.22873 (Entropy Phase Transitions in LLM Reasoning):
    low-entropy tasks (repetitive/formulaic) rarely benefit from CoT;
    high-entropy tasks (novel vocabulary, diverse concepts) benefit from L2/L3.

    Returns:
      entropy_score: float in [0, 1] (normalized by max possible H for vocab size)
      entropy_bias:  str in {"L0L1", "neutral", "L2L3"}
    Thresholds are heuristic (calibrate after 50+ labeled sessions):
      H < 0.35 -> L0L1 bias (skip CoT escalation)
      H > 0.65 -> L2L3 bias (favor CoT)
    """
    text = (task + " " + (context or "")).lower()
    words = [w for w in re.findall(r"[a-z][a-z0-9_]+", text) if len(w) > 2]
    if not words:
        return {"entropy_score": 0.5, "entropy_bias": "neutral"}
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    n = len(words)
    h_raw = -sum((c / n) * math.log2(c / n) for c in freq.values())
    h_max = math.log2(n) if n > 1 else 1.0
    h_norm = min(1.0, h_raw / h_max) if h_max > 0 else 0.5
    if h_norm < 0.35:
        bias = "L0L1"
    elif h_norm > 0.65:
        bias = "L2L3"
    else:
        bias = "neutral"
    return {"entropy_score": round(h_norm, 3), "entropy_bias": bias}


def classify_task(task: str, context: str = "") -> dict[str, Any]:
    """Classify a task's reasoning complexity."""
    detected = _detect_signals(task, context)
    signals = detected
    total_score = sum(signals.values())
    level_key = _score_to_level(total_score, detected)
    level_info = LEVELS[level_key]
    entropy_info = _entropy_signal(task, context)

    # Build evidence list
    evidence = []
    for sig, weight in sorted(signals.items(), key=lambda x: -abs(x[1])):
        direction = "escalates" if weight > 0 else "de-escalates"
        evidence.append(f"{sig} ({direction}, {weight:+.2f})")

    # Entropy advisory: warn if entropy disagrees with level assignment
    entropy_advisory = None
    eb = entropy_info["entropy_bias"]
    if eb == "L0L1" and level_key in ("L2", "L3"):
        entropy_advisory = (
            f"entropy_signal ({entropy_info['entropy_score']:.3f}) suggests L0/L1 "
            f"(low-entropy task may not benefit from CoT escalation to {level_key}). "
            "Verify complexity signals before invoking extended reasoning."
        )
    elif eb == "L2L3" and level_key in ("L0", "L1"):
        entropy_advisory = (
            f"entropy_signal ({entropy_info['entropy_score']:.3f}) suggests L2/L3 "
            f"(high-entropy task assigned {level_key}; ensure complexity is not underestimated)."
        )

    return {
        "level": level_key,
        "level_name": level_info["name"],
        "budget_tokens": level_info["budget_tokens"],
        "strategy": level_info["strategy"],
        "description": level_info["description"],
        "total_score": round(total_score, 3),
        "signals_detected": len(signals),
        "evidence": evidence,
        "entropy_score": entropy_info["entropy_score"],
        "entropy_bias": entropy_info["entropy_bias"],
        "entropy_advisory": entropy_advisory,
        "rationale": (
            f"Score {total_score:.2f} → {level_key} ({level_info['name']}). "
            f"Strategy: {level_info['strategy']}. "
            f"Budget: {level_info['budget_tokens']} tokens."
        ),
        "prompt_prefix": _build_prefix(level_key, level_info),
        "recommended_frameworks": _recommend_frameworks(detected),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─────────────────── Reasoning-type selector ────────────────────────────────
# Rule/feature router (Select-then-Solve arXiv:2604.06753; Route to Reason
# arXiv:2505.19435). No LLM call. Hermes = prompt + external feature router
# (HRBench arXiv:2605.28398) — not speculative decoding.
# L3 emits an ordered cascade workflow (HDFlow arXiv:2409.17433). Cheap
# gates (abstain-check) run before slow frameworks (SOFAI-LM arXiv:2508.17959;
# AbstentionBench: more slow reasoning can worsen abstention).

ALL_FRAMEWORKS = (
    "abstain-check",
    "causal-check",
    "lookahead",
    "subplan-verify",
    "hypothesize",
    "boundary-check",
    "kapro-check",
)

# Cascade order: cheap/safety gates first, then explanation, then planning.
CASCADE_ORDER = (
    "abstain-check",
    "causal-check",
    "lookahead",
    "subplan-verify",
    "hypothesize",
    "boundary-check",
    "kapro-check",
)

CONFLICT_PROTOCOL = (
    "If primary frameworks produce contradictory verdicts, run "
    "metacognitive-harness.py conflict-resolve (meta-reasoning). "
    "Do not majority-vote away disagreement (arXiv:2606.04223); "
    "isolate the crux or abstain/escalate."
)


def _parse_active_frameworks(raw: str) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return [x.strip() for x in raw.split(",") if x.strip()]
    if isinstance(val, list):
        return [str(x) for x in val]
    return [str(val)]


def _task_features(task: str, context: str, detected: dict) -> dict[str, bool]:
    text = (task + " " + context).lower()
    return {
        "has_causal_claim": (
            "causal_attribution" in detected
            or bool(re.search(r"\bwhy did\b|\bcaused by\b|\broot cause\b|\battributed to\b", text))
        ),
        "has_uncertainty": (
            "ambiguous" in detected
            or bool(re.search(
                r"\buncertain\b|\bunsure\b|\bmissing\b|\bunknown\b|"
                r"\bmight\b|\bcould\b|\bunclear\b|\bit depends\b",
                text,
            ))
        ),
        "is_irreversible": any(
            k in detected
            for k in ("irreversible", "irreversible_critical", "_irrev_deploy_flag")
        ),
        "has_long_horizon": "long_horizon" in detected,
        "is_abductive": (
            "abductive_task" in detected
            or bool(re.search(
                r"\bwhat explains\b|\bbest explanation\b|\bhypothesis\b|"
                r"\bdiagnose\b|\binvestigate why\b",
                text,
            ))
        ),
        "is_relational": (
            "tradeoff" in detected
            or bool(re.search(
                r"\bversus\b|\bvs\b|\bcompare\b|\brelationship\b|"
                r"\bbetween\b.+\band\b|\bpros.*cons\b",
                text,
            ))
        ),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _order_cascade(frameworks: list[str]) -> list[str]:
    rank = {name: i for i, name in enumerate(CASCADE_ORDER)}
    return sorted(_dedupe(frameworks), key=lambda n: rank.get(n, 100))


def select_frameworks(
    task: str,
    context: str = "",
    active_frameworks: list[str] | None = None,
    level_override: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Rule-based reasoning-type selector. Returns (payload, exit_code).

    Exit: 0 = OK, 1 = no frameworks apply (trivial L0/L1 — proceed, not a crash),
    2 = insufficient context.
    --level, when set, is the classify output (same classify_task()); it is not
    recomputed independently.
    """
    rt = _reasoning_runtime()
    if rt is not None and not rt.hook_enabled("pre_task_select_frameworks"):
        return {
            "primary": [],
            "secondary": [],
            "exclude": [],
            "level": None,
            "selection_rationale": "Hook pre_task_select_frameworks disabled in config.",
            "conflict_protocol": CONFLICT_PROTOCOL,
            "blend_strategy": "sequential",
            "task_features": {},
            "hook_skipped": True,
            "proceed": True,
            "empty_primary": True,
        }, 0

    active = [str(x) for x in (active_frameworks or []) if str(x).strip()]
    if not (task or "").strip():
        empty_features = {
            "has_causal_claim": False,
            "has_uncertainty": False,
            "is_irreversible": False,
            "has_long_horizon": False,
            "is_abductive": False,
            "is_relational": False,
        }
        return {
            "primary": [],
            "secondary": [],
            "exclude": list(ALL_FRAMEWORKS),
            "level": None,
            "selection_rationale": "Insufficient context: --task is empty.",
            "conflict_protocol": CONFLICT_PROTOCOL,
            "blend_strategy": "sequential",
            "task_features": empty_features,
            "proceed": False,
            "empty_primary": True,
        }, 2

    classification = classify_task(task, context)
    detected = _detect_signals(task, context)
    features = _task_features(task, context, detected)
    level = level_override or classification["level"]
    rules = rt.level_rules() if rt is not None else {
        "L0": "no_frameworks", "L1": "no_frameworks",
        "L2": "primary_only", "L3": "primary_and_secondary_cascade",
    }
    rule = str(rules.get(level, "")).strip() or (
        "no_frameworks" if level in ("L0", "L1") else
        "primary_only" if level == "L2" else "primary_and_secondary_cascade"
    )

    primary: list[str] = []
    secondary: list[str] = []

    if level in ("L0", "L1") or rule == "no_frameworks":
        payload = {
            "primary": [],
            "secondary": [],
            "exclude": list(ALL_FRAMEWORKS),
            "level": level,
            "selection_rationale": (
                f"{level} trivial/routine task — exclude all reasoning frameworks "
                "(Route-to-Reason: do not spend slow strategies on easy tasks). "
                "exit 1 means empty primary (proceed with no gates), not a crash."
            ),
            "conflict_protocol": CONFLICT_PROTOCOL,
            "blend_strategy": "sequential",
            "task_features": features,
            "proceed": True,
            "empty_primary": True,
            "level_rule": rule,
        }
        return payload, 1
    populate_secondary = rule in ("primary_and_secondary", "primary_and_secondary_cascade")
    extras_as_primary = rule == "primary_only" and level == "L3"
    if rule == "primary_and_secondary_cascade" and level == "L3":
        populate_secondary = True
        extras_as_primary = False
    if rule == "primary_only" and level == "L2":
        populate_secondary = False
        extras_as_primary = False
    # Default code path: L2 extras → secondary; L3 extras → primary.
    if not rule:
        populate_secondary = level == "L2"
        extras_as_primary = level == "L3"

    # Core selection rules
    if features["has_causal_claim"]:
        primary.append("causal-check")
    if features["is_irreversible"] and features["has_long_horizon"]:
        primary.extend(["lookahead", "subplan-verify"])
    elif features["is_irreversible"] and not features["has_long_horizon"]:
        primary.append("abstain-check")
    if features["is_abductive"]:
        primary.append("hypothesize")

    extras: list[str] = []
    if features["has_causal_claim"] and "hypothesize" not in primary:
        extras.append("hypothesize")
    if features["is_abductive"] and "causal-check" not in primary:
        extras.append("causal-check")
    if features["has_long_horizon"] and "lookahead" not in primary:
        extras.extend(["lookahead", "subplan-verify"])
    if features["has_uncertainty"] and "abstain-check" not in primary:
        extras.append("abstain-check")
    if ("multi_step" in detected or "design" in detected) and "boundary-check" not in primary:
        extras.append("boundary-check")
    if "debug_complex" in detected and "kapro-check" not in primary:
        extras.append("kapro-check")
    if features["is_relational"] and "causal-check" not in primary and "causal-check" not in extras:
        extras.append("causal-check")

    if extras_as_primary or level == "L3":
        if features["has_uncertainty"] or features["is_irreversible"] or "high_stakes" in detected:
            primary.append("abstain-check")
        if features["is_irreversible"] or "high_stakes" in detected or features["has_long_horizon"]:
            primary.extend(["lookahead", "subplan-verify"])
        if "multi_step" in detected or "design" in detected or "has_constraints" in detected:
            primary.append("boundary-check")
        if "debug_complex" in detected or features["has_causal_claim"]:
            primary.append("kapro-check")
        if features["has_causal_claim"] and "hypothesize" not in primary:
            primary.append("hypothesize")
        if features["is_abductive"] and "causal-check" not in primary:
            primary.append("causal-check")
        if extras_as_primary or not populate_secondary:
            secondary = []
        else:
            secondary.extend(extras)
    elif populate_secondary:
        secondary.extend(extras)

    primary = _order_cascade(primary)
    secondary = [f for f in _order_cascade(secondary) if f not in primary]
    exclude = [f for f in ALL_FRAMEWORKS if f not in primary and f not in secondary]

    # Snapshot fit vs already-running before stripping. Active names in
    # exclude are a poor fit (consider switch); active names in primary
    # must not be re-selected — they are already running.
    stale = [f for f in active if f in exclude]
    selected_running = [f for f in primary if f in active]
    if active:
        active_set = set(active)
        primary = [f for f in primary if f not in active_set]
        secondary = [f for f in secondary if f not in active_set]
        if not primary and secondary:
            primary = [secondary[0]]
            secondary = secondary[1:]
        exclude = [f for f in ALL_FRAMEWORKS if f not in primary and f not in secondary]

    if len(primary) > 1:
        blend_strategy = "cascade"
    else:
        blend_strategy = "sequential"

    why_bits = [k for k, v in features.items() if v]
    why = ", ".join(why_bits) if why_bits else "no typed features"
    rationale = (
        f"{level} task ({why}); primary={primary or 'none'} "
        f"via rule router; blend={blend_strategy}."
    )
    if active:
        rationale += f" Active frameworks={active}."
        if selected_running:
            rationale += (
                f" Already-running {selected_running} omitted from primary."
            )
        if stale:
            rationale += (
                f" Active {stale} are a poor fit — consider working-memory.py "
                "switch-framework."
            )

    payload = {
        "primary": primary,
        "secondary": secondary,
        "exclude": exclude,
        "level": level,
        "selection_rationale": rationale,
        "conflict_protocol": CONFLICT_PROTOCOL,
        "blend_strategy": blend_strategy,
        "task_features": features,
        "proceed": True,
        "empty_primary": not bool(primary),
        "level_rule": rule,
        "classified_level": classification["level"],
    }
    if not primary:
        # L2/L3 where every selected framework is already running is not "none apply".
        if selected_running:
            return payload, 0
        return payload, 1
    return payload, 0


def cmd_select_frameworks(args: argparse.Namespace) -> int:
    rt = _reasoning_runtime()
    raw_level = getattr(args, "level", None)
    level_override = None
    if raw_level is not None and str(raw_level).strip() != "":
        if rt is not None:
            level_override, err = rt.parse_level(raw_level)
        else:
            s = str(raw_level).strip().upper()
            if s in ("0", "1", "2", "3"):
                s = f"L{s}"
            level_override, err = (s, None) if s in ("L0", "L1", "L2", "L3") else (
                None, f"Invalid --level {raw_level!r}: expected L0-L3 (or 0-3)."
            )
        if err:
            print(json.dumps({"error": err, "proceed": False, "empty_primary": True}))
            return 2
    active = _parse_active_frameworks(getattr(args, "active_frameworks", "") or "")
    payload, code = select_frameworks(
        args.task,
        getattr(args, "context", "") or "",
        active,
        level_override,
    )
    print(json.dumps(payload, indent=2))
    return code


def _build_prefix(level_key: str, level_info: dict) -> str:
    """Build a reasoning prompt prefix appropriate for this complexity level."""
    if level_key == "L0":
        return "Answer directly and concisely."
    elif level_key == "L1":
        return (
            f"Think through this step by step. "
            f"Token budget: ~{level_info['budget_tokens']} reasoning tokens. "
            "State your approach, then execute."
        )
    elif level_key == "L2":
        return (
            f"This is a complex task requiring careful reasoning. "
            f"Token budget: ~{level_info['budget_tokens']} tokens. "
            "1) State the problem precisely. "
            "2) Identify constraints and edge cases. "
            "3) Consider 2-3 approaches. "
            "4) Select the best with rationale. "
            "5) Execute with verification."
        )
    else:  # L3
        return (
            f"CRITICAL TASK — Requires deliberate reasoning. "
            f"Token budget: ~{level_info['budget_tokens']} tokens. "
            "1) Restate the task and confirm scope. "
            "2) List all irreversible actions. "
            "3) Identify failure modes and rollback paths. "
            "4) Write the adversarial case: what could go wrong? "
            "5) Only proceed if adversarial check passes. "
            "6) Execute with checkpoints."
        )


# ─────────────────── Calibration Tracking ──────────────────────────────────

def _load_calibration() -> list[dict]:
    if not CALIB_PATH.exists():
        return []
    entries = []
    with CALIB_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _save_calibration(entry: dict) -> None:
    CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CALIB_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _compute_accuracy(entries: list[dict]) -> dict:
    """Compute accuracy-based calibration stats from historical records.

    Each entry: {"level": "L2", "actual": "L2"}  (predicted vs ground-truth).
    Returns accuracy, confusion rates, and a simple calibration label.
    Note: the old Brier/probability approach was unsound (ordinal index != probability);
    replaced with direct accuracy + directional error rates.
    """
    if not entries:
        return {"total": 0, "accuracy": None, "over_reasoning_rate": 0, "under_reasoning_rate": 0,
                "calibration_status": "no_data"}

    levels = ["L0", "L1", "L2", "L3"]
    level_idx = {l: i for i, l in enumerate(levels)}

    correct = over = under = 0
    for e in entries:
        pred_i = level_idx.get(e.get("predicted_level", e.get("level", "L1")), 1)
        act_i  = level_idx.get(e.get("actual_level",    e.get("actual", "L1")), 1)
        if pred_i == act_i:
            correct += 1
        elif pred_i > act_i:
            over += 1
        else:
            under += 1

    total = len(entries)
    accuracy = correct / total
    over_rate   = over  / total
    under_rate  = under / total

    if accuracy >= 0.8:
        status = "well-calibrated"
    elif over_rate > 0.25:
        status = "over-reasoning"
    elif under_rate > 0.25:
        status = "under-reasoning"
    else:
        status = "miscalibrated"

    return {"total": total, "accuracy": round(accuracy, 3),
            "over_reasoning_rate": round(over_rate, 3),
            "under_reasoning_rate": round(under_rate, 3),
            "calibration_status": status}


def cmd_classify(args: argparse.Namespace) -> int:
    result = classify_task(args.task, getattr(args, "context", "") or "")
    print(json.dumps(result, indent=2))
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    entry = {
        "task": args.task,
        "predicted_level": args.predicted,
        "actual_level": args.actual,
        "was_correct": bool(int(args.correct)),
        "session": getattr(args, "session", None),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_calibration(entry)
    print(json.dumps({"ok": True, "entry": entry}, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    entries = _load_calibration()
    stats = _compute_accuracy(entries)
    print(json.dumps(stats, indent=2))
    if stats["accuracy"] is not None and stats["accuracy"] < 0.75:
        print(f"\n[WARNING] Accuracy {stats['accuracy']:.2f} < 0.75 — classifier is poorly calibrated.")
        print("Consider reviewing signal weights or adding task-specific signals.")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    entries = _load_calibration()
    session = getattr(args, "session", None)
    if session:
        entries = [e for e in entries if e.get("session") == session]
    print(json.dumps(entries[-20:], indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Adaptive reasoning depth classifier for Hermes (arXiv:2608.26442)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cls = sub.add_parser("classify", help="Classify task complexity")
    p_cls.add_argument("--task", "-t", required=True, help="Task description")
    p_cls.add_argument("--context", "-c", default="", help="Additional context")
    p_cls.set_defaults(func=cmd_classify)

    p_cal = sub.add_parser("calibrate", help="Record prediction vs actual for calibration")
    p_cal.add_argument("--task", required=True)
    p_cal.add_argument("--predicted", required=True, choices=["L0", "L1", "L2", "L3"])
    p_cal.add_argument("--actual", required=True, choices=["L0", "L1", "L2", "L3"])
    p_cal.add_argument("--correct", required=True, help="1 if task completed correctly, 0 if not")
    p_cal.add_argument("--session", default=None)
    p_cal.set_defaults(func=cmd_calibrate)

    p_stats = sub.add_parser("stats", help="Show calibration statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_hist = sub.add_parser("history", help="Show calibration history")
    p_hist.add_argument("--session", default=None)
    p_hist.set_defaults(func=cmd_history)

    p_sel = sub.add_parser(
        "select-frameworks",
        help="Select reasoning frameworks for a task (rule-based selector)",
    )
    p_sel.add_argument("--task", "-t", required=True, help="Task description")
    p_sel.add_argument("--context", "-c", default="", help="Additional context")
    p_sel.add_argument(
        "--level",
        default=None,
        help="Classify output L0-L3 (or 0-3). Omit to use classify_task() on --task. Out of range → exit 2.",
    )
    p_sel.add_argument(
        "--active-frameworks",
        default="",
        dest="active_frameworks",
        help="JSON list of already-running frameworks",
    )
    p_sel.set_defaults(func=cmd_select_frameworks)

    args = ap.parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
