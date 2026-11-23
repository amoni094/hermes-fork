---
name: wave21c-loop-governance
description: "Use when Wave 21C ISS/SPRT/governance gates."
version: "1.0"
author: hermes-fork
license: MIT
tags: [wave21c, control, governance, safety, sprt]
metadata:
  hermes:
    tags: [wave21c, control, governance, safety]
    related_skills: [hermes-fork-script-development, theory-to-implementation-extrapolation]
---

# Wave 21C loop / governance / safety gates

## When to Use

Wave 21C composite stability, Wald SPRT promotion, multi-principal governance conflicts, falsifiability lint, taint audit, or PID model comparison.

Canonical scripts: `~/.hermes/hermes-scripts/`. Fork wrappers: `profiles/fork/scripts/`.
Do **not** patch `~/.hermes/scripts/loop-pid.py` — use `loop-pid-iss-wrapper.py`.

```bash
HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 ~/.hermes/hermes-scripts/<script>.py --self-test
```

| Script | When |
|---|---|
| loop-pid-iss-wrapper.py | Lyapunov + ISS + two-timescale composite |
| shadow-gate-sprt.py | Sequential promotion (alongside nightly gate) |
| governance-conflict-detector.py | auth-gate vs hard-block disagreement |
| governance-falsifiability-lint.py | proposals missing failure_observable |
| counterfactual-tool-gate.py | `--sequence` minimal footprint |
| loop-model-comparison.py | PID AR(1) vs random walk Bayes factor |
| callgraph-taint-audit.py | taint to replace/move/write sinks |
| nyquist-timescale-bridge.py | Nyquist aliasing vs timescale-ok contradiction |
| loop-cusum-changepoint.py | Page CUSUM on PID error |
| impact-regularizer-gate.py | side-effect ratio > 0.5 |

## SPRT / falsifiability alarm diagnostics

| Alarm | Legitimate vs spurious | Fix |
|---|---|---|
| sprt-falsifiability-handshake: n_hold > 0 | Check if held flags have a hermes-script named after them | If `~/.hermes/hermes-scripts/<flag>.py` exists, the script IS the falsifier — add observable_ok_by_script() |
| sprt-measurement-tamper: identically_zero_error_rate | Check n_scores vs n_turns — if n_scores=0 and n_turns>>0, JEV scoring is inactive | Guard: skip rows where ALL score fields are None; only flag when n_scores >= 8 |
| wave21c-ltl-promotion-invariant: missing | Run wave21c-invariants.py directly | The LTL invariant G(PROMOTE → failure_observable) depends on falsifiability; fix handshake first |
| routing-skill-percolation: FRAGMENTED | Check giant_frac curve at lower thresholds | Expected early in deployment; threshold 0.35 is aggressive; giant_frac at 0.2 is the useful signal |

## Stale composite alarm

If `wave21c-loop-stability-composite.json` shows alarm=true but `iss-justification-gate.py` exits 0 with justified_ok=true when run directly, the composite file is stale — it was written by a cron job that last ran before the fix. Resolution: re-run the script that generates the composite file directly. Check which cron job writes it by grepping: `grep -r 'loop-stability-composite' ~/.hermes/profiles/fork/scripts/`. Run it manually, then re-run wave21c-alarm-bridge.py to refresh the aggregated view.

- loop-pid is Hermes-owned; ISS wiring is a wrapper, never an in-file patch.
- SPRT LLR increment for N(3,1) vs N(4,1) is `x - 3.5`; A=log(19), B=log(1/19).
- error_rate >= 0.10 vetoes SPRT PROMOTE even if LLR crossed A.
- TYPE_A (ALLOW vs DENY) must be logged; silent priority is the bug.
- `_hermes_root` sinks are EXPECTED in taint audit; only alarm constructed sensitive paths.
- BF < 0.1 on loop-model-comparison means switch to MPC/rollout, not retune Kp blindly.
- alarm-aggregator only reads `*-alarm.json` with 2h TTL; always refresh via wave21c-alarm-bridge.py.
- ISS overall_ok is unjustified unless passivity and circle-criterion also hold (iss-justification-gate).
- Raw SPRT PROMOTE is not executable; read sprt-effective-decision.json (handshake/truncation/tamper/mesa).
- Truncated SPRT never PROMOTEs at N_max; fail-closed REJECT.
- Do not patch alarm-aggregator.py; emit sidecars instead.
- sprt-measurement-tamper guards: all-None score rows in jev-turn-scores.jsonl MUST be excluded before computing identically_zero_error_rate. A row where ALL score fields are None is an unscored record, not a zero-error record — counting it as zero inflates n_zero_err and triggers a spurious alarm. Guard: `if all(v is None for v in obj.get('scores',{}).values()): continue`. Only flag identically_zero_error_rate when n_scores (rows with at least one non-None score) >= 8.
- sprt-falsifiability-handshake: a monitoring script whose filename matches a flag name IS a valid failure_observable — the script itself operationalises the falsification condition. Add an observable_ok_by_script() check: if a file named `<flag_name>.py` exists in hermes-scripts/, treat the flag as self-observable. This avoids blocking auto-generated shadow-eval PROMOTE decisions that are inherently self-monitored.
- Routing percolation alarm (routing-skill-percolation.json): giant_frac < 0.1 at the operating_threshold (0.35) means FRAGMENTED — skill graph connectivity is sparse at high co-access weights. This is expected early in deployment (few skill pairs co-accessed enough to reach the threshold). It is NOT a code bug. Alarm clears naturally as skill-access.log accumulates real co-occurrence data.
- Skill graph cold-start (skill-graph-builder): if the cron fires before skill-access.log has 20+ entries, it emits 0 edges. When auditing skill-graph.json and finding edges=0, run skill-graph-builder.py directly (not via cron) to rebuild from accumulated log data. Expected state: nodes=N, edges=0 means the graph ran too early; nodes=N, edges>0 means data is feeding correctly.
