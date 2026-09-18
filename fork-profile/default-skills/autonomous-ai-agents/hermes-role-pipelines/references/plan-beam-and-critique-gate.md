# Plan beam + critique-before-commit (ToT-lite)

Operational detail for the Plan-then-Execute section in SKILL.md.
Skip this file on simple/single-step work. Use it when the parent is about to mutate state and more than one approach is plausible.

## What this is not

- Not full MCTS. Do not spawn rollout children to simulate futures before execute. Depth-1 `delegate_task` plus cost make MCTS plan-selection a non-fit. Skill-variant MCTS lives in `skillopt-continuous-improvement` (Branch2Skill), not here.
- Not Canvas-of-Thought (named in-session state nodes). CoT is a scratchpad; Canvas is a mutable node graph; ToT-lite is a *plan beam* pruned *before* side effects.
- Not Producer-Reviewer after the fact. Reviewer-after-implement can still ship a bad plan that already wrote files. This gate selects the plan first, then blocks commit until a *different* critic passes.
- Not `hermes-swarm-consensus`. That reduces conflicting *execution* verdicts. This selects among *plans*.

## Phase 0 — emit N candidate plans (read-only)

Parent or a planner child with `toolsets=['file']` (add `'web'` only if the approach depends on external docs). N=2, N=3 if the approaches actually differ in blast radius or rollback. Never N>3.

Each candidate is a JSON object, not prose:

```json
{
  "id": "plan-a",
  "thesis": "one sentence: the approach",
  "phases": [
    {
      "name": "discover",
      "mutating": false,
      "done_when": "artifact path + schema",
      "on_fail": "retry-same",
      "on_ambiguous": "branch"
    }
  ],
  "irreversible_steps": ["git push", "skill_manage delete"],
  "checkpoint_after": ["discover", "implement"],
  "blast": "SELF|THIRD_PARTY|SYSTEMIC"
}
```

Rules:
- Every phase names `on_fail` and `on_ambiguous` (LangGraph-style conditional edges). Allowed values: `retry-same` | `replan` | `branch` | `ask-human` | `accept-partial`. Same meanings as Review loop branching in SKILL.md.
- `mutating: true` phases must not run until Phase 0 + critic prune complete.
- If you cannot name an `on_fail` edge, the plan is incomplete — do not execute it.

## Phase 0b — critic prunes the beam

Spawn a *separate* critic (fresh context packet: objective, constraints, the N plan objects). Do not include the planner's chain-of-thought. Critic toolsets: `['file']` only.

Critic returns exactly one of:

```json
{
  "winner": "plan-a",
  "rejected": ["plan-b"],
  "reason": "one sentence",
  "missing_edges": []
}
```

Score rubric (all must be true for a winner):
1. Covers the stated objective without extra scope.
2. Irreversible steps are isolated and have an ask-human or ATP gate.
3. Every phase has `on_fail` / `on_ambiguous`.
4. Checkpoints exist at phase boundaries.

Tie: run `trajectory-risk-guardrail` on both remaining plans; pick lower prefix-risk. If still tied and blast is THIRD_PARTY/SYSTEMIC: `ask-human`. Else pick the plan with fewer mutating phases.

The planner must not grade its own beam. Parent-with-critique-appended is not this critic.

## Execute the winner as parent-orchestrated waves

Depth-1 constraint still applies. Map `phases[]` to serial waves. After each phase:

1. Write `~/.hermes/agent-workspace/<pipeline_id>-stage-<N>.checkpoint.json` (existing Handoff Checkpointing).
2. Verifier (cheap, preferably non-LLM): artifact exists and matches `done_when`. This is BATON's transition-aware verifier from `autonomous-agent-loop-design`.
3. On verifier fail: fire the phase's `on_fail` edge. Cap `retry-same` at 2, then `replan` (back to Phase 0 for *this* phase only, not the whole task).
4. On ambiguous output: fire `on_ambiguous`. `branch` = two narrow children with distinct interpretations, then `hermes-swarm-consensus` before the next phase.

Do not start phase N+1 on a failed verifier.

## Critique-before-commit (blocking)

After the last implementation wave, *before* claiming done, merging, pushing, or promoting skills:

1. Critic child, fresh packet: original objective + done-criteria + artifact paths/diffs. No executor transcript. `toolsets` read-only (`['file']`, plus `'terminal'` only if tests must be run by the critic).
2. Output: `pass` | `fail` | `ambiguous` plus evidence refs. Not a rewrite.
3. `fail` → Review loop branching (`retry-same` / `replan`). `ambiguous` → `branch` or `ask-human`.
4. Commit only on `pass`. Executor self-grade is banned (see Verification-Gated Escalation).

Producer-Reviewer is the collaboration *shape*. Critique-before-commit is the *gate*: the parent does not treat the implementer's handoff as terminal.

## When to skip

- Task intake class `simple`.
- Complexity-gated-planning Level 0–1 (0–3 signals) unless a HAZARD step is already in the trajectory.
- Single obvious approach with only reversible local edits.
- Read-only research with no durable write.

## Cost cap

Phase 0 + critic = at most 2 extra `delegate_task` children (or parent-local if N=2 and no HAZARD). If the beam would cost more than one implementation wave, skip ToT-lite and use a single Level-2 plan from `complexity-gated-planning` plus this file's critique-before-commit gate only.
