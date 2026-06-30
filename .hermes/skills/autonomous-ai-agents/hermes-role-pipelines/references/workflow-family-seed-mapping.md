# Workflow family → Seed mapping

Use this reference when converting Hermes collaboration patterns into reusable executable templates or static handoff artifacts.

## Canonical family set

Prefer these five reusable families:
- `pipeline`
- `fanout_fanin`
- `producer_reviewer`
- `supervisor`
- `expert_pool`

These names are stable enough for generated JSON/YAML artifacts and broad enough to avoid one-skill-per-session fragmentation.

## Recommended mapping

### pipeline
- Best fit: later work depends strongly on earlier outputs.
- Typical roles: discovery, design, implementation, verification.
- Seed style: `sequential`.
- Acceptance focus:
  - phase handoffs are explicit
  - later stages cite earlier findings
  - verification includes concrete evidence

### fanout_fanin
- Best fit: independent parallel discovery or analysis that is merged before implementation or final recommendation.
- Typical roles: parallel-discovery, synthesis, implementation, review.
- Seed style: `parallel_then_merge`.
- Acceptance focus:
  - parallel tracks are independent
  - synthesis reconciles conflicts
  - review checks merged coverage

### producer_reviewer
- Best fit: one worker produces and another critiques before final verification.
- Typical roles: producer, reviewer, verifier.
- Seed style: `two_step_with_review`.
- Acceptance focus:
  - reviewer is independent
  - review findings are addressed or documented
  - verification cites the reviewed artifact

### supervisor
- Best fit: parent-managed worker waves where findings change the next assignment.
- Typical roles: supervisor, worker-wave, reviewer, tester.
- Seed style: `iterative_waves`.
- Acceptance focus:
  - todo/state is centralized
  - worker scopes stay narrow
  - each wave changes the next decision

### expert_pool
- Best fit: conditional specialist dispatch where only some experts are needed.
- Typical roles: router, specialist, integrator, verifier.
- Seed style: `conditional_dispatch`.
- Acceptance focus:
  - specialists are conditional
  - specialist reasoning is summarized
  - final output explains why each specialist was used

## Heuristic defaulting

When building a static classifier and a skill does not carry strong family markers, default to `pipeline` rather than inventing a bespoke category.

Good markers:
- fan-out / fan-in, parallel discovery, synthesis → `fanout_fanin`
- producer-reviewer, planner -> implementer -> reviewer → `producer_reviewer`
- supervisor, waves, parent stays active, todo updates → `supervisor`
- expert pool, conditional specialist dispatch → `expert_pool`
- sequential analyze -> design -> implement -> verify → `pipeline`

## Recommended generated artifacts

For skill-to-Seed conversion, emit at least:
- `workflow-family.json` — normalized family classification + roles/phases/acceptance focus
- `workflow-handoff.md` — legible human review handoff
- `workflow-seed.yaml` — executable Seed scaffold

## Verification rule

Do not stop at unit tests only. Verify at least one real CLI generation path and read back the emitted JSON/YAML to confirm the selected family and seed style are actually present on disk.
