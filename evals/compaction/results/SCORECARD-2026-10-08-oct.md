# Hermes compaction recall — 3-transcript scorecard (2026-10-08)

## Verdict

**Shipping `current+recovery` is weaker on this October bank than on the 2026-09-19 bank:
45.6% @ 37K vs 78.9% @ 55K.** Closed-book `current` also dropped (34.4 vs 43.3) but the
recovery lift collapsed: +11 pts here vs +36 pts in September. `lean+recovery` is the
best arm on this run (52.2% @ 37K), still well below September's shipping number.

Jev was not re-run (no `OPENROUTER_API_KEY` in the fork profile `.env`).

Caveats that block a "the compressor got worse" claim:

- Different lineages (WAL-journal 24.8M-token chain, fork-architecture work, system
  review) vs September's PR-review / sysprompt / SIGSEGV bank.
- Different aux route: compaction + exam answers + judge all went through
  `claude-haiku-4-5` (`task=compression`). September used gemini-3.8-flash via Nous.
- Classifier always chose `fork_mixed` / `session_type=code` on all three prefixes.
- `head_hit_rate=0.0` on every arm: gold strings from the exam were not in the
  compacted summary head, so closed-book answers were already starting from a miss.
- N=15 per transcript; reported 95% CI widths are ~41–45 pts. Treat ±7 pt
  between-arm gaps as noise except where they repeat across transcripts.

Question asked: on three fresh October 2026 500K-token lineage prefixes, how do
`current+recovery` (production), `lean+recovery`, and the two closed-book baselines
compare on recall, retained tokens, compaction cost, and wall time — and how does
that sit next to SCORECARD-2026-09-19-jev.md?

Harness: `evals/compaction/runner.py` (`--policies current+recovery,lean+recovery,current,lean
--questions 15 --cap-tokens 500000`). Transcripts reconstructed with
`scripts/reconstruct_lineage.py` from a copy of
`/var/home/rainbow/.hermes/profiles/fork/state.db`. Same question bank per transcript
for every arm. `HERMES_HOME=ABEVAL_HOME=/var/home/rainbow/.hermes/profiles/fork`.

## Results (recall % @ retained tokens; compaction wall time per event)

| policy | wal_journal | fork_arch | sys_review | AVG | compaction in/out | compaction s |
|---|---|---|---|---|---|---|
| **lean+recovery** | 36.7 @ 43K | **70.0 @ 37K** | 50.0 @ 31K | **52.2 @ 37K** | 62K / 4.4K | 50.9 |
| **current+recovery** (what we ship) | 26.7 @ 43K | 56.7 @ 36K | **53.3 @ 31K** | **45.6 @ 37K** | 62K / 3.9K | 47.2 |
| lean (closed-book) | 33.3 @ 44K | 36.7 @ 37K | 40.0 @ 31K | 36.7 @ 37K | 62K / 4.4K | 51.4 |
| current (closed-book) | 23.3 @ 43K | 40.0 @ 37K | 40.0 @ 31K | 34.4 @ 37K | 62K / 4.3K | 50.6 |

`compaction_cost_usd` was not metered (`null` on every arm). Compaction model:
`claude-haiku-4-5`, one call per event, ~58–65K input tokens.

Per-transcript recovery lift (recovery − closed-book):

| transcript | current | lean |
|---|---|---|
| sys_review (`20261007_113443_6c2b65`, 14 sessions, 747 msgs, ~720K tok reconstructed) | +13.3 | +10.0 |
| fork_arch (`20261008_185330_ba0ef4`, 9 sessions, 1,242 msgs, ~858K tok) | +16.7 | +33.3 |
| wal_journal (`20261007_164247_28e403`, 87 sessions, 10,434 msgs, ~7.57M tok; eval prefix 500K) | +3.4 | +3.4 |

WAL is the failure mode: 500K of a 7.6M-token chain, recovery barely moves the needle.

## vs 2026-09-19 (same harness shape, different bank + aux model)

September shipping number: **78.9% @ 55K**, closed-book current **43.3% @ 55K**,
lean **41.1% @ 55K**, compaction **$0.061 / 36.9 s** (gemini-3.8-flash).

| policy | Sep 19 AVG | Oct 8 AVG | Δ recall | Δ retained | Δ compress s |
|---|---|---|---|---|---|
| current+recovery | **78.9 @ 55K** | **45.6 @ 37K** | **−33.3** | −18K | +10.3 |
| current closed-book | 43.3 @ 55K | 34.4 @ 37K | −8.9 | −18K | +13.7 |
| lean closed-book | 41.1 @ 55K | 36.7 @ 37K | −4.4 | −18K | +18.0 |
| lean+recovery | (not scored) | 52.2 @ 37K | — | — | — |
| jev (plugin defaults) | 75.5 @ 115K | skipped | — | — | — |

Reading, not a causal claim:

1. **Retained context is tighter** (37K vs 55K, ~7.4% kept vs ~11%). That is
   consistent with `fork_mixed` being more aggressive than the September main path,
   and it is the one number that looks like a win.
2. **Closed-book recall is in the same ballpark** (34–37 vs 41–43). The 7–9 pt
   drop is inside a 15-question noise floor plus a harder exam (WAL identifiers).
3. **Recovery is the regression that matters.** September's session_search round
   trip almost doubled closed-book recall (43 → 79). October's average lift is
   +11 (current) / +16 (lean), and on WAL it is +3. Either the exam facts are not
   in the search index for that prefix, or one recovery hop is not enough on an
   87-session lineage.
4. **Wall time is worse** (~47–51 s vs ~34–37 s). Same "one summary LLM call"
   shape; haiku-4-5 on ~62K input is slower here than gemini-3.8-flash was in
   September. Still noise against per-turn cost of the retained context.

## Lineages (500K-token cap each)

| name | root session | reconstructed | eval prefix |
|---|---|---|---|
| wal_journal | `20261007_164247_28e403` | 87 sessions, 10,434 msgs, ~7.57M tok | 499,407 tok → ~43K after |
| fork_arch | `20261008_185330_ba0ef4` | 9 sessions, 1,242 msgs, ~858K tok | 499,929 tok → ~37K after |
| sys_review | `20261007_113443_6c2b65` | 14 sessions, 747 msgs, ~720K tok | 497,435 tok → ~31K after |

Raw per-run JSON: `evals/compaction/results/oct-run-{wal_journal,fork_arch,sys_review}/`.

## Method notes

- Transcripts from `/tmp/state_copy_oct.db` (copy of fork `state.db`); not committed.
- Question banks generated from the region current compaction summarises, cached as
  `questions-<tid>.json` so every arm on a transcript answers the same exam.
  Generator had to use an 40–80K char exam window: a 600K dump on the compression
  aux route produced non-JSON / agent-continuation instead of a question list.
- Judge scale 0/1/2; `recall_pct = 100 * sum(scores) / (2N)`.
- Eval LLM usage (answer+judge, not compaction): sys_review 150 calls / 2.60M in;
  fork_arch 150 / 2.63M in; wal_journal 300 / 5.37M in (recovery extra hops).
- Runner fixes applied during this run (kept in `evals/compaction/runner.py`):
  duplicate argparse flags removed; `_original` assigned before compress;
  `classifier_decision` plumbed into the summary dict; `_extract_json` uses
  `JSONDecoder.raw_decode`; question-gen accepts a wrapped object and a smaller
  exam window.

## What this suggests

Do not change the shipping policy on this scorecard alone. Do investigate why
recovery is nearly inert on the WAL lineage (search corpus vs 500K prefix, single
hop, identifier capture). `lean+recovery` beating `current+recovery` by 6.6 pts
at the same retained size is inside noise except on fork_arch (+13.3), which is
the one transcript where lean's extra tail actually held exam gold.
