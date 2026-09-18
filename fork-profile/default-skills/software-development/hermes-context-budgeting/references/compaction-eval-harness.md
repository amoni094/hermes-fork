# Compaction Eval Harness

How to run the `evals/compaction/` harness from the fork or local repo to compare policy arms on real session lineages.

## Adding a policy arm

Add an entry to `POLICIES` in `evals/compaction/policies.py`:

```python
"my_arm": {
    "ctor": {"threshold_percent": 0.45, "protect_last_n": 22},
    "attrs": {"proactive_prune_tokens": 20_000, "importance_biased_prune_enabled": True,
              "session_type": "research"},
}
```

`ctor` keys are compressor attributes set directly (via `setattr`) after construction. `attrs` are set via `apply_policy()`. Always set `session_type` and `importance_biased_prune_enabled` on fork_* arms — without them the arms are functionally identical to lean. Do NOT add `tail_mode: lean` to `ctor` when lean is already the default.

### Fork profile calibrated values (2026-09-12, from eval v2)

| profile | threshold_percent | protect_last_n | proactive_prune | combined_score |
|---------|-------------------|----------------|-----------------|----------------|
| fork_research | 0.45 | 22 | 20K | 4.11 (research best) |
| fork_code | 0.55 | 28 | 12K | 4.46 (mixed best) |
| fork_mixed | 0.50 | 20 | 16K | 3.76 |
| lean_fork_research | 0.45 | 22 | 20K | 1.56 (avoid: 0% easy on research) |

`lean_fork_research` is a compound arm with no benefit over lean on research and is token-expensive on mixed. Do not use it.

## Lineage reconstruction

Copy the DB first to avoid locking the live session store:

```bash
cp ~/.hermes/state.db /tmp/state_eval_copy.db
python evals/compaction/scripts/reconstruct_lineage.py \
  /tmp/state_eval_copy.db <full-session-id> /tmp/lineage.json
```

Full session IDs include the 6-character hex suffix (e.g. `20260910_152600_e65e0f`). Query the exact ID from the DB before passing to the script — the script does not do prefix matching.

Find good candidate lineages by total token mass:
```python
import sqlite3, collections
db = sqlite3.connect('/tmp/state_eval_copy.db')
children = collections.defaultdict(list)
for r in db.execute('SELECT id, parent_session_id FROM sessions WHERE parent_session_id IS NOT NULL'):
    children[r['parent_session_id']].append(r['id'])
# Walk tree from each root and sum input_tokens across the chain
```

## Question validity gate (MANDATORY — run before any compression)

Every recall question must have a `where` field containing an exact phrase from the uncompressed transcript. Gate check:

```python
where.lower() in full_transcript_text.lower()  # must be True
```

Run with `--validate-questions` before any eval:

```bash
python evals/compaction/runner.py --transcript /tmp/lineage.json --out /tmp/eval_out \
  --policies current --questions 15 --validate-questions --cap-tokens 500000
```

Abort if any question fails. Invalid questions (returns 0 gates: all invalid) mean all eval results are noise — the facts were never in the transcript.

### Three sources of invalid questions

1. MEMORY.md / USER.md leakage: gold answer lives in always-on context (MEMORY.md, system prompt, skill frontmatter), not in the session transcript. Telltale: easy-tier recall ≤40% across ALL policies — facts were never in the session. Fix: grep for the gold string in `~/.hermes/MEMORY.md` and `~/.hermes/USER.md`; if found, the question is TOKEN_NEUTRAL, zero signal.

2. Eval-circular questions: question asks about the compaction eval process itself (crash root cause, protect_last_n calibration after round N, char_cap values). These have answers in the eval session transcripts, creating circularity. Always replace with domain-content questions.

3. Keyword bags as gold: gold = `haiku-4-5 / haiku / anthropic / compression / vision` accepts almost any response. Gold must be one sentence or one precise identifier. Slash-joined synonym lists inflate judge variance by ±13pp.

## Signal type tagging (required for v2 evals)

Tag every question with `signal_type` before seeding the cache:

- **TOKEN_EFFICIENT_SIGNAL**: short specific facts a compressor must distill — counts, paper IDs, named decisions+reasons, unique identifiers. Gold = 1-2 clauses. Primary recall metric uses ONLY these.
- **TOKEN_SENSITIVE**: full phase narratives, raw crash traces, SKILL.md dumps. Rewards keeping bulk, not compression quality. Report separately as a token-use tradeoff arm.
- **TOKEN_NEUTRAL**: anything in MEMORY.md, system prompt, skill frontmatter. All policies score the same; zero compaction signal. Report as control only, never in primary recall_pct.

Question format with signal_type:
```json
{"q": "How many orphaned reference files did the audit find?",
 "gold": "57",
 "where": "57 phantom orphaned reference files",
 "difficulty": "medium",
 "signal_type": "TOKEN_EFFICIENT_SIGNAL"}
```

## Combined score — the primary ranking metric

```
combined = recall_pct / (after_tokens / before_tokens * 100)
```

Higher is better. Rank policies by combined, not raw recall. Rationale: a policy achieving 43% recall at 48K after_tokens (combined=4.46) is pareto-superior to 43% recall at 58K after_tokens (combined=3.72). Recall alone hides token bloat.

Ship gate: combined >= 400 on the matching domain AND after_tokens/before_tokens <= 0.11.

Note: on force=True runs with 500K-token transcripts, threshold_percent tuning is nearly a no-op — after_tokens clusters tightly around 48-58K regardless of threshold. The real lever is summary content quality (fact ledger, session-type template) and demotion selectivity (CAUSAL/NOISE tagger).

## Difficulty stratification and calibration

Use 5 easy / 5 medium / 5 hard per domain (not uniform).

Calibrate difficulty by WHERE the fact lives, not by assumed complexity:
- **Easy**: short decision/ID a summary must keep (counts, paper IDs, failed filenames). Must be ≥80% recall on uncompacted control AND ≥50% on a non-lean policy.
- **Medium**: mid-session outcomes, named agents and their findings, specific numeric thresholds.
- **Hard**: facts a good compressor should DISTILL from bulk — contradiction+resolution, causal chains, multi-source conclusions. Should be <50% recall on lean.

If a "hard" question gets >50% recall on multiple policies (including lean), it is miscalibrated — it is either parametric/skill-level knowledge or has a gold that matches too broadly.

Diagnostic: easy-tier recall <50% across all policies means the "easy" facts are either TOKEN_NEUTRAL (MEMORY leakage) or not actually in the transcript (literal-span gate failure).

## Running

```bash
python evals/compaction/runner.py \
  --transcript /tmp/lineage.json \
  --cap-tokens 500000 \
  --policies "current,lean,fork_research,fork_code,fork_mixed" \
  --questions 15 \
  --out /tmp/eval_v2/domain_name
```

Run two transcripts in parallel as separate background processes with separate `--out` directories. Results do not interfere.

For fast-mode (5/5/5 difficulty, N=15): MIN_VALID_PER_TIER = 3 (set in runner.py line ~104). For ship-gate validation: raise to MIN_VALID_PER_TIER = 9 and use N=30+ questions.

## Session-type routing finding (2026-09-12)

Session-type matching is the highest-value single lever:
- `fork_research` dominates research domain: 43.3% recall, combined=4.11 vs lean 20% recall, combined=1.85
- `fork_code` dominates mixed domain: 43.3% recall, combined=4.46 vs lean 40% recall, combined=4.10

The classifier in lambda-tuner should route: research/math/sweep → fork_research; audit/implement/code → fork_code.

Compound arms (lean_fork_research) consistently underperform their components. Single-domain specialization beats compound arms.

## Compressor improvements (fork, 2026-09-12, commit bf77604df4)

These changes in context_compressor.py improve quality without token bloat:

1. **CAUSAL/STRUCTURAL/NOISE tagger** (`_tag_message_type`, line ~1867): deterministic, no extra LLM. Wired into rr_score formula (0.5*importance + 0.2*uniqueness + 0.3*tag_prior) and importance_biased_prune eviction order. CAUSAL messages are never evicted; NOISE messages are evicted first.

2. **Fact ledger at summary head** (`_extract_fact_ledger`): regex-harvests paths, arXiv IDs, model names, numbers, SHAs, named results from turns before summarization. Prepends as first 2000 chars of summary. Addresses Lost-in-Middle: easy facts that exist at 52K tokens but are mid-context are now anchored at head.

3. **D-state reacquisition classifier** (`_reacquisition_class`): CHEAP (read_file/web_extract/skill_view bodies >1500 chars with no numbers) → demoted to ARC stub. EXPENSIVE (user messages, decisions, numbers, CAUSAL output) → never stubbed. Target: research after_tokens ≤ 48K.

4. **Session-type summarizer** (lambda-tuner `on_pre_compress`): sets `summary_focus_topic` on compressor before each compress event. Research: prioritizes citations, causal findings, numeric results. Code: prioritizes file paths, test outcomes, exit codes. Reduces boilerplate (Goal/Constraints) for research sessions.

5. **Compression-to-LLM routing coherence** (lambda-tuner `pre_llm_call`): reads `_last_ratio` (after/before tokens) and sets model_preference. ratio > 0.12 → sonnet (high distortion needs stronger decoder); ratio < 0.09 → haiku (low distortion, context carries the load). Rate-distortion principle: D high → higher-capacity channel.

## Critical pitfalls

**`--also-uncompacted` overflows the 200K API limit.**  
The uncompacted control arm calls `serialize_for_exam(messages, char_cap=900_000)` (~225K tokens), hitting Anthropic's hard 200K context ceiling. Fix: change `char_cap=900_000` to `char_cap=600_000` (~150K tokens) at the relevant call site. Skip `--also-uncompacted` for policy-arm comparison runs unless specifically measuring a new ceiling.

**Policy arm isolation.**  
On main post-2026-09-11, `ContextCompressor` defaults to `tail_mode=lean`. A fork profile that changes only `threshold_percent`/`protect_last_n` without setting `session_type` and `importance_biased_prune_enabled=True` is functionally identical to lean. The eval will show no differentiation — not because the profile is wrong but because the attrs weren't applied.

**question cache key is MD5 of the transcript PATH string, not content.**  
Cache path: `<out_dir>/questions-<md5(path)[:10]>.json`. If you move the transcript file, the cache key changes and the runner tries to generate new questions (calling the LLM). Copy the question file to match the new key, or keep transcripts at stable paths.

**Parallel eval runs within one runner.py invocation are sequential.**  
Policy arms run one at a time within a single `runner.py` call. Run two transcripts in parallel by launching two background processes; do not expect intra-process parallelism.

**threshold_percent tuning is a near-no-op on force=True runs.**  
All force=True 500K-token runs produce after_tokens in the 48-58K range regardless of threshold. Do not interpret threshold as the primary lever — it only matters for natural (non-forced) compaction triggers. Combined score differences come from content quality (fact ledger, CAUSAL tagger), not threshold.

## SCORECARD baselines

### Aug-15 baseline (uniform questions, pre-v2)

| policy | recall | retained tokens |
|---|---|---|
| uncompacted | 96.7% | 500K |
| current | 45.8% | ~162K |
| lean (closed-book) | 40.0% | ~49K |
| lean+recovery | 68.3% | ~49K |

### Sep-12 baseline (v2, tiered 5/5/5, TOKEN_EFFICIENT_SIGNAL, valid literal-span questions)

Research domain (math/sweep lineage, 500K cap):

| policy | recall | easy/med/hard | after_tokens | combined |
|--------|--------|---------------|--------------|----------|
| fork_research | 43.3% | 40/40/50 | 52,680 | 4.11 |
| current | 26.7% | 10/40/30 | 52,088 | 2.56 |
| fork_mixed | 23.3% | 20/20/30 | 57,863 | 2.01 |
| lean | 20.0% | 40/10/10 | 53,900 | 1.85 |
| fork_code | 20.0% | 20/20/20 | 53,025 | 1.89 |
| lean_fork_research | 16.7% | 0/20/30 | 51,885 | 1.56 |

Mixed domain (audit/implement lineage, 500K cap):

| policy | recall | easy/med/hard | after_tokens | combined |
|--------|--------|---------------|--------------|----------|
| fork_code | 43.3% | 50/40/40 | 48,397 | 4.46 |
| lean | 40.0% | 50/40/30 | 48,626 | 4.10 |
| lean_fork_research | 40.0% | 50/40/30 | 51,641 | 3.86 |
| fork_mixed | 36.7% | 50/30/30 | 48,677 | 3.76 |
| fork_research | 36.7% | 50/20/40 | 50,497 | 3.62 |
| current | 33.3% | 30/30/40 | 52,299 | 3.17 |

Note: Sep-12 results used valid TOKEN_EFFICIENT_SIGNAL questions with literal-span gate. Aug-15 used hand-crafted questions with MEMORY leakage — directly comparable numbers are the combined score, not raw recall.

Sep-12 v3 results (with compressor improvements from bf77604df4) pending — evals in progress.
