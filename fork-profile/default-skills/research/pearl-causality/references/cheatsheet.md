# Pearl causality — decision rules

## See vs do

| You have | You can claim |
|----------|----------------|
| P(Y \| X) from logs | association only |
| P(Y \| do(X)) from A/B, surgery, or identified adjustment | causal effect |
| P(Y_x \| evidence) | counterfactual ("would Y have been…") |

If you did not intervene and cannot reduce do(x) via back-door/front-door/do-calculus, you do not have a causal effect.

## What to condition on

- **Confounder (fork X ← Z → Y):** condition on Z to block the back-door.
- **Mediator (chain X → Z → Y):** do **not** condition on Z if you want the *total* effect of X.
- **Collider (X → Z ← Y):** do **not** condition on Z or descendants of Z.

**Back-door Z for effect of X on Y:** no descendant of X in Z; Z blocks every path into X toward Y.

**Front-door Z:** Z sits on all directed X	o Y paths; no open back-door X—Z; X blocks back-doors Z—Y.

## Debugging / eval tells

- Fix green in CI, red in prod → unobserved confounder (env, data, load) correlated with both "applied the fix" and the outcome. Confirm the causal path, not the correlation.
- "X shows up in failing traces" → observation. Disable/enable X (intervention). Only then causation.
- Error-only logs, ticket-only users, crashed-only dumps → collider. Independent causes look dependent.
- Test that would pass even without the fix → no counterfactual evidence.
- Async/distributed races → missing ordering edges or a cycle in the causal DAG of mutations.

## do-calculus (when to swap see/do)

- Rule 2: if back-doors from Z to Y are blocked (in the graph with arrows into X gone, arrows out of Z gone), then observing Z = doing Z.
- Rule 1: drop an observation that is d-separated from Y after the intervention.
- Rule 3: drop an intervention that cannot reach Y in the mutilated graph.

Unidentifiable query: more of the same observational data will not identify it.
