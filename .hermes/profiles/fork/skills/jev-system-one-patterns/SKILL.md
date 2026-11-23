---
name: jev-system-one-patterns
description: "Use when designing JEV harness patterns."
---

# JEV / System One Patterns — Hermes-Fork

## What Jev Actually Is

Jev is TypeSafe AI's System One Model (released 2026-09-15). It is NOT an LLM.

  Architecture:
    - Trained with RLCD (Reinforcement Learning for Calibrated Decisions)
    - Non-autoregressive: all output slots computed in ONE parallel forward pass
    - Three question types:
        noul    -- yes/no probability: {"noul": 0.999}
        choice  -- pick from list + per-option probabilities
        score   -- ordinal rating with distribution
    - Type-safe: schema enforced at architecture level; hallucination impossible
    - Deterministic: same input -> same output across runs
    - Cost: ~$0.042/MTok input; outputs free; 70-500ms end-to-end
    - JEV pattern: state + N typed questions -> N (answer, confidence) pairs in parallel

  Contrast with LLMs: sequential, expensive, can hallucinate, non-deterministic

## Hermes-Fork Emulation Layer (jev_verify_fn.py)

Do NOT claim Jev-level type-safety/calibration from these.
Current provider Anthropic -> logprob_classify() always returns NaN.

  atomic_subquestions(context, questions)  -- N typed questions in ONE LLM call
    Types: bool, choice:A,B,C, score:0-5
    Works on Anthropic. Returns typed answers (not probability values).
    Use for: turn evaluation, task classification, quality scoring

  calibrated_gate(confidence)  -- float -> 'act'|'flag'|'escalate'
    NaN -> escalate (safe). Stakes adj: low(-0.10), medium(0.0), high(+0.10)

  logprob_classify()  -- ONLY OpenAI-compat; returns NaN on Anthropic. Don't use here.

  make_verify_fn()  -- single yes/no; use for consistency scoring

  Budget: jev-call-budget.json 200/day (shared with compaction). Use separate files.

## What Is Built (Wave 17)

  jev-turn-evaluator plugin (shadow-only, DISABLED by default)
    Enable: shadow_jev_evaluator: true in plugin config
    post_llm_call observer: 4 dims via atomic_subquestions() on 1/3 sampled turns
    Dims: factual_coherence, task_progress, tool_alignment, efficiency
    Budget: jev_eval_budget.json 100/day (separate from compaction)
    Output: cache/jev-turn-scores.jsonl (atomic O_APPEND)
    H-I7: all exceptions swallowed; returns None
    Promotion: scripts/jev-gate-nightly.py; PROMOTE when scored_turns>=20, mean_score>=3.5, error_rate<10%

  tool-auth-gate extensions (active, deterministic):
    _READ_SAFE_TOOLS: 12 read-only tools fast-path (skip all checks)
    _CREDENTIAL_PATH_PATTERNS: .ssh/, .aws/, .gnupg/, .netrc -> escalate
    _EXEC_CODE_DANGER_PATTERNS: pipe-to-shell, eval, rm -rf -> escalate

## Adversarial Audit Rules (deleg_123bd8ee, 2026-10-07)

  KILLED: jev-model-router
    pre_llm_call cannot select a model (host ignores return value for model selection)
    Extend inject-hermes-routing-note.py instead (deterministic, free)
    RULE: no new LLM-based model routers; heuristics already exist

  KILLED: jev-tool-risk-guard
    pre_tool_call is FAIL-CLOSED with 30s host timeout
    LLM calls there block the agent; tool-auth-gate already owns this surface
    RULE: pre_tool_call = deterministic only, no LLM calls

  REDESIGNED: jev-turn-evaluator
    post_llm_call is observer-only; cannot inject messages from plugins
    Recursive eval loops have no host seam and corrupt compaction
    RULE: post_llm_call = JSONL log only; no injection; no recursion

  Budget rule: separate named budget per consumer (compaction, evaluation, etc.)
  Circular eval rule: same LLM evaluating its own output = telemetry only, not control
  H-I8 rule: all plugin_update -> HIGH governance; shadow-first; 2 approvals + 24h cooldown
  Shadow rule: hook registered + all returns None + JSONL only + exceptions swallowed = real shadow

## Design Rules for Future Work

  1. atomic_subquestions() not logprob_classify() on Anthropic profile
  2. One LLM call covers all questions (never serial calls for same context)
  3. Separate named budget per consumer; never share evaluation + compaction budgets
  4. post_llm_call: O_APPEND JSONL; never inject; never block; never recurse
  5. pre_tool_call: deterministic policy only
  6. Model routing: extend inject-hermes-routing-note.py; no new LLM router plugin
  7. New plugins: start disabled; shadow_flag: true; earn promotion via shadow-gate-nightly
  8. Compute derived facts in code first; ask LLM only about genuine semantic gaps
  9. NaN logprobs -> calibrated_gate -> 'escalate' (safe degradation)
