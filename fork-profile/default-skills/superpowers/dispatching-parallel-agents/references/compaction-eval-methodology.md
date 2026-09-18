# Compaction Eval Methodology — Rules and Pitfalls

For Hermes context-compaction policy evals (runner.py + policies.py pattern).
Apply when designing, running, or interpreting results from compaction policy A/B tests.

## Question Validity Rules (enforce before seeding any question set)

### 1. Literal-span gate (mandatory)
Every question must have a `where` quote — a verbatim string present in the UNCOMPRESSED
cap window (the actual 500K-token slice, not the full lineage). Run `find_cap_start(msgs,
500_000)` to get the exact index; build questions only from `msgs[cap_start:]`.

Fail classes:
- MEMORY.md leakage: gold answer lives in MEMORY.md or USER.md (always loaded, not in the
  transcript). Easy recall drops to 10-40% because the exam is closed-book.
- Parametric / skill leakage: answer is in a skill's frontmatter or CLI help text.
- Eval-circular: question asks about the eval session itself.
- Full-lineage leakage: question built from full lineage file but answer is outside the 500K window.
  Use `find_cap_start(msgs, cap_tokens)` — never `msgs[-N:]` or a percentage estimate.

### 2. One fact, one gold sentence
No keyword bags. Compound questions inflate judge variance.
Bad: "why did it crash, what was root cause, how fixed?" gold "char_cap / 900_000 / overflow".
Good: "What token cap was set before the first run crashed?" gold: "900000".

### 3. No eval-circular items
Do not ask about the compression harness, previous eval rounds, protect_last_n
calibration, or char_cap values.

### 4. Difficulty calibration by location, not perceived hardness
- Easy = short decision/id that a summary MUST preserve (counts, arXiv IDs, failed filenames,
  specific numbers). Should be ≥80% on uncompacted control and ≥50% on any non-lean policy.
- Medium = mid-session outcome (a conclusion, a config value that was changed, a finding).
- Hard = facts a good compressor should DISTILL from bulk (contradiction+resolution, causal
  chain A→B because C). Must be <50% on lean policy.

### 5. Signal type tagging (report separately, do not average)
- TOKEN_NEUTRAL: model names, skill names, definitions — likely leakage. Exclude from recall_pct.
- TOKEN_SENSITIVE: full narrative sequences, raw crash traces. Rewards "kept more tokens".
- TOKEN_EFFICIENT_SIGNAL: rare identifiers (paper ID + key number, named contradiction+fix).
  This is the only slice that tests compaction quality. Use for primary recall_pct.

### 6. Domain-label / cap-window match (mandatory)
Before running eval, verify the cap-window content matches the lineage label:
  R/C ratio = (sum of research-signal chars) / (sum of code-signal chars) in cap window
  research domain: R/C > 2.0 (research-dominant)
  code domain: R/C < 0.5 (code-dominant)
  mixed domain: 0.5 <= R/C <= 2.0

If the cap window doesn't match the label, rebuild the lineage (truncate to move cap_start
into the correct content type). Do not run eval with mismatched lineages.

## Metrics

### Combined score (primary ship metric)
  combined = recall_pct / (after_tokens / before_tokens * 100)
  Rank arms by combined, not recall_pct alone.
  Ship bar: combined >= 4.0

### Per-difficulty combined
  Report easy/med/hard recall alongside overall. Minimum 10 questions per tier (N=30 total).

### Head-hit-rate (Lost-in-Middle probe)
  Fraction of TOKEN_EFFICIENT_SIGNAL gold strings appearing in first 5000 chars of compressed output.
  Target: ≥30% (fact ledger at summary HEAD is the fix when low).

### Classifier routing field
  Always emit `classifier_decision` in scorecard.json for the classified arm.
  Compare classified arm against the domain-matched policy (not the lineage label).

## Eval Architecture Rules

### force=True makes threshold_percent a no-op
All eval arms run with force=True. threshold_percent has zero effect on forced compression.
Real differentiators: summary template, demotion rules, tail_token_budget, protect_last_n,
importance_biased_prune_enabled, session_type.

### Policies must set session_type
Eval policies must explicitly stamp session_type on the compressor before compress().
Without it, the lambda-tuner classifier does not fire.

### importance_biased_prune_enabled must be True in fork arms
Default is False. Eval arms that don't set it measure a dead scorer.

### N=30 minimum before drawing policy conclusions
At N=15, a 2-question difference = 13.3 percentage points. CI is ~±14pp.
Target N=30 (10/10/10 tiered) before ranking policies.

### Scorecard results live in scorecard.json (list), not per-arm files
The runner writes all arm results to `{out_dir}/scorecard.json` as a JSON list.
Per-arm files (`{policy}.json`) exist but have `summary` + `results` keys, not top-level
recall/combined fields. Always read scorecard.json for the final ranked table.

## Ship-gate v4 Results (N=30, domain-matched lineages — AUTHORITATIVE)

Lineages were constructed so the 500K cap window content matches the domain label:
  research_v2: msgs[:1400], cap_start=979, R=4355 C=953, ratio 4.57 (research-dominant)
  code_v2:     msgs[1500:], cap_start=1645, R=527 C=3060, ratio 0.17 (code-dominant)
  mixed_v2:    msgs[700:1700], cap_start=421, R=1099 C=1223, ratio 0.47 (mixed)

RESEARCH_V2 results (N=30, 10/10/10):
  fork_mixed     45.0%  combined=5.10  easy=50 med=45 hard=40  <- WINNER
  fork_research  41.7%  combined=4.71  easy=45 med=45 hard=35
  lean           35.0%  combined=3.96
  fork_code      30.0%  combined=3.44
  classified(fork_research)  36.7%  combined=4.18  <- correctly routed, 8.3pts below winner

CODE_V2 results (N=30, 10/10/10):
  fork_mixed     38.3%  combined=5.52  easy=40 med=50 hard=25  <- WINNER
  lean           35.0%  combined=4.78  easy=40 med=40 hard=25
  fork_research  35.0%  combined=4.85  easy=50 med=35 hard=20
  current        35.0%  combined=4.75  easy=45 med=25 hard=35
  fork_code      31.7%  combined=4.53  easy=35 med=35 hard=25
  classified(fork_code)  30.0%  combined=4.29  easy=50 med=25 hard=15  <- correctly routed

MIXED_V2 results (N=30, 10/10/10):
  fork_research  43.3%  combined=5.10  easy=50 med=45 hard=35  <- WINNER
  classified(fork_code)  40.0%  combined=4.73  easy=45 med=40 hard=35  <- within CI of winner
  fork_mixed     38.3%  combined=4.52
  fork_code      35.0%  combined=4.18
  current        30.0%  combined=3.55
  lean           28.3%  combined=3.35

Ship decision:
  All arms >= 4.0 on code_v2. All arms >= 4.0 on research_v2 except lean (3.96, borderline).
  Mixed_v2: fork_research, classified, fork_mixed, fork_code ship; current and lean do not.
  RECOMMENDED DEFAULT: fork_mixed — wins 2/3 domains, competitive on all three.

## Key Architectural Finding (v4)

fork_mixed is the dominant general-purpose policy. Domain-specific policies (fork_research,
fork_code) over-prune content of the "other" type and lose on their own home domain.
Reason: real sessions always contain mixed content even when labelled single-domain.

Classifier routing is CORRECT — the classifier identifies cap-window content accurately.
The classified arm's gap vs winner is a policy quality issue, not a routing issue.
All session types route to fork_mixed by default (updated in _FORK_PROFILE after v4).

If classified arm underperforms: first check whether lineage label matches cap-window
content type. If it does, the gap is in the policy quality, not the routing.

## Domain-Matched Lineage Construction

To build a domain-matched lineage:
1. Load full lineage messages
2. Compute cap_start = find_cap_start(msgs, 500_000)
3. Measure R/C ratio on msgs[cap_start:]
4. If ratio doesn't match target domain: truncate msgs and recompute
   - Scan 300-msg chunks to find where content type shifts
   - Adjust truncation point until cap window hits target ratio
5. Write truncated msgs to new lineage file
6. Verify: recompute cap_start + R/C on the new file before building questions

## Top Validated Improvement Targets

1. Fact ledger at summary HEAD (not middle/tail) — defeats Lost-in-Middle without extra tokens
   Expected: research_easy 10% → 60%, after_tokens flat or -1.5k

2. CAUSAL/NOISE tagger wired to Phase-1 demotion
   CAUSAL = tool in {execute_code, write_file, patch, terminal, delegate_task} OR decision verbs
   NOISE = empty search / no-op read / truncated catalog dump
   Demotion order: NOISE first; CAUSAL skips eviction

3. Session-type summarizer template via pre_compress hook
   research template: Fact ledger + Causal chains + Open questions (cap 2500 tokens)
   code template: file paths, test outcomes, diffs, exit codes

4. fork_code policy tuning: currently loses on its own domain (code_v2). The policy
   over-prunes code blocks that the eval questions test. Increase protect_last_n for
   code sessions and reduce demotion aggressiveness on tool-output blocks.

## Calibration Dry-Run Procedure

Before seeding any question set, run a 2-arm calibration dry-run:
  Arm A: uncompacted_control (no compression)
  Arm B: lean (most aggressive)
  Easy questions must be: >=80% on A, >=50% on B
  Hard questions must be: >=70% on A, <50% on B
  Questions outside these bands are miscalibrated — re-tier or replace before full eval.
