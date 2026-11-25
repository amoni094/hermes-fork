# Hermes compaction recall — N=60 medium lineage (2026-11-24)

Lineage: Fedora 44→45 post-upgrade audit (`local-e64dbdf391f597f35f86c6bd62eba186456d5dd1ac579d7e3bb817f64cda4881`).
Reconstructed 7 sessions, 630 msgs, 466,874 tok (fits 500K cap). `--full-lineage` on; recovery arms labeled `*_recovery_full`.
Questions: 60 (same bank all arms), exam-sample-msgs=200. Literal-span gate: 32/60 valid (53%). Aux: `claude-haiku-4-5`.
Raw JSON: `evals/compaction/results/n60-2026-11-24-fedora/`.

## Results (N=60, 95% CI)

| policy | recall | 95% CI | CI width | head_hit_rate | after tok | kept | compress s |
|---|---|---|---|---|---|---|---|
| **current+recovery_full** | **57.5%** | 45.4–69.6 | 24.3 | 0.333 | 63,126 | 13.5% | 67.9 |
| lean+recovery_full | 42.5% | 31.6–55.9 | 24.3 | 0.333 | 63,659 | 13.6% | 67.2 |
| lean (closed-book) | 41.7% | 29.6–53.8 | 24.2 | 0.400 | 62,503 | 13.4% | 55.1 |
| current (closed-book) | 38.3% | 26.4–50.3 | 23.9 | 0.333 | 61,933 | 13.3% | 50.0 |

`compaction_cost_usd` = null on every arm. Last-arm exam metering (lean+recovery_full only): `total_cost_usd≈14.00` (`cost_per_task_usd≈0.233`); other arms not metered.

## Notes

- Shipping `current+recovery` lift vs closed-book current: **+19.2 pts** (outside ~10 pt distinguishability).
- `lean` vs `current` closed-book: +3.4 pts (noise). `lean+recovery` vs `lean`: +0.8 pts (noise). One judge JSON parse failure scored 0 on lean+recovery.
- `head_hit_rate` 0.33–0.40 (not 0.0). Oct-8 all-zero HHR was a metric/window issue; this run sees gold in the summary head.
- CI still ~±12 pt per arm at N=60; do not rank lean vs current on this bank. Recovery vs closed-book on **current** is the only gap that clears noise.
- Question quality: 28/60 failed literal-span (`where` not in transcript). Scores include invalid items. Easy-tier valid=7 (<9).
- Harness fixes needed to run: `fixtures.py` `selected` NameError; `runner.py` missing `logger = logging.getLogger(__name__)`.
