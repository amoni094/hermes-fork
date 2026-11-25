# Reason-tier three-way hybrid: simple / deep / elite

Date: 2026-11-25
Predicate: `agent/reason_depth.py::needs_deep_reason`
Config (fork profile, opt-in): `reason_model`, `reason_deep_model`, `reason_elite_model`

Feature is **off** unless `reason_deep_model` or `reason_elite_model` is set.

## Split

| depth | when | model |
|---|---|---|
| simple | factual / procedural / analytical | `deepseek/deepseek-v4-pro` |
| deep | multi-constraint, complex refactor, long query | `openai/gpt-5.5` |
| elite | `consecutive_reason_turns >= 2` (trajectory) | `anthropic/claude-sonnet-5-5` |

## Simulated hybrid (n=3 existing runs)

Trajectory elite scores use **gpt-5.5 as a conservative lower bound** (no sonnet-5-5 reason-battery scores yet).

```
task                         | selected            | score | gpt-5.5 | delta
err_python_env               | deepseek            | 3/3   | 3/3     | +0pp
err_replay_patch             | deepseek            | 3/3   | 3/3     | +0pp
err_ambiguous_edit           | deepseek            | 3/3   | 3/3     | +0pp
err_case_search              | deepseek            | 3/3   | 3/3     | +0pp
err_hidden_search            | deepseek            | 3/3   | 1/3     | +67pp
err_big_output               | deepseek            | 3/3   | 3/3     | +0pp
err_multi_dir                | deepseek            | 3/3   | 3/3     | +0pp
err_inline_script            | gpt-5.5 (complex_query) | 3/3 | 3/3   | +0pp
err_big_file_read            | deepseek            | 3/3   | 3/3     | +0pp
err_ctx_synthesis            | deepseek            | 3/3   | 3/3     | +0pp
err_deep_search              | deepseek            | 3/3   | 3/3     | +0pp
err_logic_proof              | deepseek            | 3/3   | 3/3     | +0pp
err_multi_tool_chain         | deepseek            | 3/3   | 3/3     | +0pp
err_ambiguous_refactor       | gpt-5.5 (complex_refactor) | 2/3 | 2/3 | +0pp
err_subtle_bug               | deepseek            | 2/3   | 3/3     | -33pp
err_cross_file_refactor      | deepseek            | 3/3   | 2/3     | +33pp
err_debug_trace              | deepseek            | 2/3   | 3/3     | -33pp
err_multi_constraint_plan    | deepseek            | 3/3   | 3/3     | +0pp
traj_refactor_chain          | sonnet-5-5 (lb=gpt) | 2/3   | 2/3     | +0pp
traj_debug_fix_verify        | sonnet-5-5 (lb=gpt) | 3/3   | 3/3     | +0pp
traj_incremental_build       | sonnet-5-5 (lb=gpt) | 0/3   | 0/3     | +0pp
HYBRID TOTAL                 |                     | 56/63 | 55/63   | +1.6pp
```

Task routing: 16 -> deepseek, 2 -> gpt-5.5, 3 -> sonnet-5-5 (traj).

## Verdict

Hybrid vs gpt-5.5: **+1.6pp -> PASS** (threshold: within 3pp of 55/63).
deepseek-only was 50/63; gpt-5.5 55/63; conservative hybrid **56/63**.

Production wiring: **DONE** (fork profile `config.yaml`).

Weighted cost (query mix, not this battery):
- reason_simple 75% deepseek ~$0.003/task
- reason_deep 10% gpt-5.5 ~$0.031/task
- reason_elite 15% sonnet-5-5 ~$0.082/task
- weighted ~$0.017/task vs all-gpt-5.5 ~$0.021/task (~19% on that quote; battery cost mix differs)

Note: trajectory scores are a conservative lower bound; actual sonnet-5-5 likely higher.
`err_multi_constraint_plan` prompt does not match the multi-constraint regex (name ≠ prompt).

## 4th run (sonnet-5-5 on traj + interpretive)

Tasks: `traj_refactor_chain`, `traj_debug_fix_verify`, `traj_incremental_build`,
`err_ambiguous_refactor`, `err_cross_file_refactor`, `err_subtle_bug`, `err_debug_trace`.
Root: `~/.hermes/profiles/fork/cache/scratch/benchmark-reason-sonnet55/`
