# Reason battery: deepseek-v4-pro vs gpt-5.5

Date: 2026-11-25
Harness: `evals/toolperf_abeval/ab_eval.py` (`--arm baseline` + `--arm trajectory`, `--reps 3`)
Roots:
- deepseek: `~/.hermes/profiles/fork/cache/scratch/benchmark-reason-deepseek`
- gpt-5.5: `~/.hermes/profiles/fork/cache/scratch/benchmark-reason-gpt55`

Reason battery = all TASKS except math (`err_math_*`), elite (`err_security_review`, `err_adversarial_*`, E3 cascade/injection/multi_file_debug/constraint_propagation), and tooluse (`err_tool_format`), plus all `traj_*` tasks.

## Verdict

**FAIL.** deepseek-v4-pro **50/63 = 79.4%** vs threshold **>= 85%**.
gpt-5.5 **55/63 = 87.3%**. Reason tier stays `openai/gpt-5.5`.

Err-only (excluding traj): deepseek 49/54 = 90.7%, gpt-5.5 50/54 = 92.6%.
The miss is concentrated on multi-turn trajectory coherence and `err_ambiguous_refactor` (token `REFACTORED=OK`).

## Table

```
=== REASON BATTERY: deepseek-v4-pro vs gpt-5.5 ===
task                         | gpt-5.5 | deepseek-v4-pro | delta
err_python_env               | 3/3     | 3/3             | +0pp
err_replay_patch             | 3/3     | 3/3             | +0pp
err_ambiguous_edit           | 3/3     | 3/3             | +0pp
err_case_search              | 3/3     | 3/3             | +0pp
err_hidden_search            | 1/3     | 3/3             | +67pp
err_big_output               | 3/3     | 3/3             | +0pp
err_multi_dir                | 3/3     | 3/3             | +0pp
err_inline_script            | 3/3     | 3/3             | +0pp
err_big_file_read            | 3/3     | 3/3             | +0pp
err_ctx_synthesis            | 3/3     | 3/3             | +0pp
err_deep_search              | 3/3     | 3/3             | +0pp
err_logic_proof              | 3/3     | 3/3             | +0pp
err_multi_tool_chain         | 3/3     | 3/3             | +0pp
err_ambiguous_refactor       | 2/3     | 0/3             | -67pp
err_subtle_bug               | 3/3     | 2/3             | -33pp
err_cross_file_refactor      | 2/3     | 3/3             | +33pp
err_debug_trace              | 3/3     | 2/3             | -33pp
err_multi_constraint_plan    | 3/3     | 3/3             | +0pp
traj_refactor_chain          | 2/3     | 1/3             | -33pp
traj_debug_fix_verify        | 3/3     | 0/3             | -100pp
traj_incremental_build       | 0/3     | 0/3             | +0pp
OVERALL                      | 55/63   | 50/63           | -8pp
```

## Cost

```
=== COST COMPARISON ===
gpt-5.5:          $0.0340/task  (current)
deepseek-v4-pro:  $0.0061/task  (candidate)
Saving:           82% reduction
```

## Failed tasks (deepseek not 3/3)

- `err_ambiguous_refactor` 0/3 — closed-form fix present; checker token `REFACTORED=OK` missing
- `err_subtle_bug` 2/3
- `err_debug_trace` 2/3 (one rep `TRACED=1` vs gold 2)
- `traj_refactor_chain` 1/3 — required step 1 (`VALIDATED=OK`) missed 2/3
- `traj_debug_fix_verify` 0/3 — required step 1 (`FIXED=OK`) missed 3/3 (later steps often passed)
- `traj_incremental_build` 0/3 — gpt-5.5 also 0/3

Gaps >20pp vs gpt-5.5 (would be reason→elite escalation candidates if overall had passed):
`err_ambiguous_refactor`, `err_subtle_bug`, `err_debug_trace`, `traj_refactor_chain`, `traj_debug_fix_verify`.
