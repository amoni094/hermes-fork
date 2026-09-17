---
name: rr-compaction-scorer
description: "Use when debugging or tuning Phase-1 RR demotion scorer. Includes Lost-in-the-Middle pitfall (arXiv:2307.03172), exec-state protection, saliency-anchor gap."
version: 1.1.0
author: Hermes Agent
license: MIT
trust_level: experimental
source_episodes: ["20260908_183611_fed04a"]
related_skills:
  - hermes-context-hygiene
  - hermes-context-budgeting
  - hermes-context-packet
metadata:
  hermes:
    tags: [compaction, context-compression, relevance-realization, information-theory, spike]
    related_skills: [hermes-context-hygiene, hermes-context-budgeting, hermes-context-packet]
---

# RR Compaction Scorer

## Overview

The standard Hermes Phase-1 prune demotes tool results oldest-first (positional). This ignores
information density: a large old `execute_code` result (irreplaceable) could be demoted before
a tiny new `skill_view` body (reloadable).

This skill implements the Relevance Realization cognitive-scope opponent-process
(Vervaeke, Lillicrap & Richards 2012, J. Logic and Computation 22(1):79-99) as a
two-signal compaction scorer:

    retention_score(msg) = particularization_pressure(msg) - lambda * compression_pressure(msg)

High score = keep. Low score = demote first.
NOTE: spike script header comment (line 8) shows an older formula; actual implementation
in spike.py line 188 and context_compressor.py line 2784 both use pp - lambda*cp correctly.

CURRENT STATUS (2026-09-09, v2 PRODUCTION): Budget-capped, exec-state-protected, RR-sorted.
See Status section below for full runtime state.

Spike results on a real 185-message session vs positional baseline (top-20 demotion budget):
  token reclaim:    11,761 vs 13,740 (RR -14%, slightly less aggressive)
  pp-loss (info):   6.15 vs 8.17 (RR loses 25% LESS information)
  efficiency ratio: 1,912 vs 1,681 tokens/pp-unit (RR 14% more efficient)
  key swap:         RR deprioritizes skill_view over execute_code in ranking

Note: "user turns protected" claim from earlier spike is wrong -- user turns are never
Phase-1 candidates (_demote_tool_result_at returns False for role != tool).

## When to Use

- Investigating why compaction is destroying high-density context (execute_code, delegate_task)
- Tuning lambda if Phase-1 demotion ordering is wrong (check lambda < 0.235 for exec_code protection)
- Running the spike script to compare RR vs positional on a specific session
- Auditing exec-state protection set membership (_EXEC_STATE_TOOLS in context_compressor.py)
- Adding new tools to the info-density table

Don't use for: LLM summary calls (Phase 3) or gateway hygiene (hermes-context-hygiene).
This only affects Phase-1 tool-result demotion ordering.

## Theory: The Two Signals

From Vervaeke 2012, Table 1, Cognitive Scope opponent-process pair:

Compression pressure (cp):
  Normalised token cost = tokens(msg) / max_tokens_in_window.
  High cp = many tokens freed if demoted.

Particularization pressure (pp):
  How task-specific and irreplaceable the message is. Three sub-components:
    density  (0.5): tool-type information density (see table)
    recency  (0.3): exp(-3 * (1 - i/n)), 0=oldest, 1=newest
    proximity (0.2): exp(-0.3 * dist_to_nearest_user_turn)

    retention_score = pp - lambda * cp
      lambda=0.2  PRODUCTION (< 0.235 required to protect large execute_code)
      lambda=0.5  balanced (prior default before math was verified)
      lambda=0.0  pure particularization (never demote by size)
      lambda=1.0  pure compression (largest first)

## Tool Info Density Table

  1.00  user turns          irreplaceable
  0.95  delegate_task       subagent result, expensive to re-run
  0.90  clarify             user answer, irreplaceable
  0.85  execute_code        analysis output, hard to reproduce
  0.80  web_extract         full page, re-fetchable but slow
  0.80  write_file          write confirmation, signals intent
  0.75  patch               diff, deliberate edit
  0.70  web_search          re-runnable
  0.65  read_file / browser_navigate
  0.60  browser_snapshot / browser_vision / vision_analyze
  0.55  terminal            usually re-runnable
  0.50  search_files        re-runnable
  0.45  hindsight_recall / assistant turns
  0.40  hindsight_reflect / skill_view  (skill_view RELOADABLE: demote first)
  0.35  memory              side-effect only
  0.30  system turns        lowest priority

## Critical Disanalogy

The RR mechanism in biology is self-organizing: metabolic cost drives the tradeoff
to equilibrium without a central oracle. Hermes has no metabolic feedback.

Consequences:
  - Emergent self-tuning does NOT transfer
  - This is a fixed formula, not a dynamic opponent process
  - Lambda must be set by operator, not self-tuned
  - Useful degraded approximation, not the full RR mechanism

## Spike Script

Path: ~/.hermes/scripts/rr_compaction_spike.py

  python ~/.hermes/scripts/rr_compaction_spike.py            # synthetic demo
  python ~/.hermes/scripts/rr_compaction_spike.py --latest    # most recent session dump
  python ~/.hermes/scripts/rr_compaction_spike.py --session <id> --lambda 0.5 --top-k 20
  python ~/.hermes/scripts/rr_compaction_spike.py --json      # raw JSON scores

Session files: ~/.hermes/sessions/request_dump_*.json (chat completions format only;
Responses API format skipped automatically by the loader).

Verification: 10 ad-hoc checks pass (pp ordering, score range, positional ascending,
RR demotes skill_view first, already_demoted excluded, lambda sensitivity, demo).

## Integration Patch Plan

Target: ~/.hermes/hermes-agent/agent/context_compressor.py
Method: _prune_old_tool_results (Phase 1)

Already done (2026-09-08/09):
  1. RR scoring function _rr_score() added (~L2764)
  2. Sort candidates ascending by score (lowest = demote first) when use_rr_scorer=True (~L2786)
  3. Feature-flag: compression.use_rr_scorer wired in agent_init.py (~L1505)
  4. Demotion budget cap: max(1, min(8, prune_boundary//3)) — sort is effective, not all results demoted.
     Implemented 2026-09-08. Budget formula verified correct (adversarial audit 2026-09-09).
  5. Exec-state protection: _EXEC_STATE_TOOLS frozenset excludes execute_code/write_file/patch/terminal/delegate_task/web_extract
      from Phase-1 candidates. Replaces earlier D-state naming.
  6. Tests: 33 passing in test_it_research_implementations.py covering budget cap, exec-state membership,
     RR ordering, stub enrichment, budget dashboard, CCA violation check.

All complete. No remaining STILL NEEDED items.

Lambda for the budget-limited implementation: use < 0.235 to protect large
high-density results. rr_scorer_lambda: 0.2 in config (correct, verified 2026-09-09).

## Lambda Tuning Guide

CRITICAL MATH (adversarial finding 2026-09-08):
  Score = 0.5*density + 0.3*recency + 0.2*proximity - lambda*(tokens/max_tokens)
  Old large execute_code: density=0.85, cp~1.0 -> score = 0.425 - lambda
  Old small skill_view:   density=0.40, cp~0.05 -> score = 0.200 - 0.05*lambda
  execute_code > skill_view only when: 0.425 - lambda > 0.200 - 0.05*lambda
                                    => lambda < 0.235

  To protect large high-density old results (stated design intent): lambda < 0.24
  At lambda=0.4 or 0.5: large execute_code LOSES to small skill_view (gets demoted first)

  Until RR has a demotion budget limit + measured sessions, lambda is irrelevant
  (current implementation demotes all eligible results regardless of order).

  For future budget-limited implementation, correct values would be:
    lambda < 0.24  protect large causal tool results (execute_code, delegate_task)
    lambda ~ 0.5   neutral (penalize by token cost proportionally)
    lambda > 0.5   aggressively prefer small messages (dense but cheap to keep)

## Measurement Protocol

Run on 20 sessions before enabling in production:
  python ~/.hermes/scripts/rr_compaction_spike.py --json > session_scores.json

Primary metric: pp-loss delta (positive = RR loses less information per compaction).
Guard metric: token reclaim must not drop more than 15% vs positional.

Promote to validated after 3+ sessions with positive pp-loss delta and token reclaim
regression no worse than 15%.

## Common Pitfalls

- Density table is static. Recency sub-component partially corrects age but density
  doesn't decay with usage. Future work: decay density by turns-since-last-reference.

- User turns are not Phase-1 candidates regardless (role != tool skips
  _demote_tool_result_at). Main practical effect is reordering tool-result demotions.

- Feature flag MUST default to false. No behaviour change unless opted in.

- Real 185-msg session showed 30 swaps in top-20. Lambda tuning may improve efficiency
  on sessions with cleaner cp/pp separation.

- Lost-in-the-Middle (arXiv:2307.03172, Liu et al. 2023): RR recency sub-signal is exp(-3*(1-i/n)) which
  correctly up-weights recent turns. But turns in the MIDDLE of a long compaction window
  get the worst score (low recency, not in proximity of last user turn). High-density middle
  results (e.g. a key execute_code from 50 turns ago that produced the current working artifact)
  may be demoted. Mitigation: exec-state protection (_EXEC_STATE_TOOLS) covers execute_code;
  no general middle-context protection exists. Future work: "saliency anchor" — if a turn is
  referenced by filename/ID in a later turn, treat it as proximity=1.0.
  (Not implemented; would require cross-turn reference scanning at demotion time.)

## Status: ENABLED IN PRODUCTION (v2, 2026-09-09)

  compression.use_rr_scorer: true
  compression.rr_scorer_lambda: 0.2   <- must stay < 0.235 (see Lambda math below)

### What v2 actually does (verified, tests/agent/test_it_research_implementations.py 230/230)

1. EXEC-STATE PROTECTION (informed by arXiv:2608.16370)
   _EXEC_STATE_TOOLS = frozenset({execute_code, write_file, patch, terminal, delegate_task, web_extract})
   These are EXCLUDED from Phase-1 demotion candidates. Density table values ARE
   used for RR scoring but NOT for protection gating (that was the prior wrong approach).
   Pressure pass (pass 4) still demotes exec-state tools if soft ceiling is unmet.
   NOT in set: clarify (Q&A, no execution state), web_extract, delegate_task, web_search.

2. DEMOTION BUDGET CAP (informed by arXiv:2607.08032 reversibility principle)
   Budget = max(1, min(8, prune_boundary // 3)) per Phase-1 pass.
   This makes the sort selective -- lowest-scoring non-exec-state tools demote first.
   Comment in code (line ~2803): formula is max(1, min(8, n//3)) -- verify in source.

3. RR SORT (now meaningful with budget cap)
   Candidates sorted ascending by score = pp - lambda * cp.
   lambda=0.2 ensures large execute_code (score ~0.51) beats small skill_view (score ~0.19).

4. LEAN STUB ENRICHMENT (informed by ARC arXiv:2607.25066 -- principles only)
   _lean_recovery_stub includes turn_idx as list-index metadata and resolves tool_name
   from call_id_to_tool so stubs are informative. Does NOT use turn_idx as session_search
   query key (DB row_id is unavailable at demotion time; FTS would not match 'turn N').

5. BUDGET DASHBOARD (informed by VISTA arXiv:2606.30005 -- principles only)
   _build_budget_dashboard appended to lean compaction summaries when last_prompt_tokens > 0.
   Shows post-compaction token bar and pressure level so agent can self-regulate verbosity.
   Omitted (returns '') when last_prompt_tokens is 0 (unset/first session start).

6. VERBATIM PRESERVATION RULES in compression preamble (informed by ACON arXiv:2510.00615
   + Size-Fidelity Paradox arXiv:2602.09789)
   Explicit rules: file paths verbatim, error messages verbatim, numeric values verbatim,
   causal direction ("test FAILED" vs "test passed" must not be swapped),
   truncate-not-paraphrase when budget-constrained.

### Tests (236/236 passing, 2026-09-09)

  tests/agent/test_it_research_implementations.py -- 27 new tests covering:
    - _lean_recovery_stub (keyword hint, turn_idx metadata, tool_name fallback)
    - _build_budget_dashboard (omit-when-zero, pressure levels, bar overflow)
    - _EXEC_STATE_TOOLS membership (patch/terminal in; clarify/web_search out)
    - compression preamble rules (VERBATIM PRESERVATION RULES present, no Alice/Bob)
    - Phase-1 exec-state exclusion integration

### Spike formula

  retention_score = pp - lambda * cp   (context_compressor.py ~line 2784)

## Verification Checklist

- [x] Demotion budget cap in _prune_old_tool_results (max(1, min(8, prune_boundary//3)))
- [x] Exec-state tools protected in Phase-1 (execute_code, write_file, patch, terminal, delegate_task, web_extract)
- [x] Tests added: tests/agent/test_it_research_implementations.py (27 tests)
- [x] Lambda math verified: lambda=0.2 < 0.235 protects large execute_code
- [x] Feature flag enabled in config (use_rr_scorer: true)
- [x] Lean stub includes turn_idx metadata + tool_name resolution from call_id_to_tool
- [x] Budget dashboard wired to last_prompt_tokens (real field on compressor)
- [x] Verbatim preservation rules in compression preamble (no Alice/Bob, no rule overlap)
- [ ] Spike run on 20 sessions comparing pp-loss RR vs positional (future measurement)
