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

## Lessons
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
