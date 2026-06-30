---
name: hermes-self-evolution
description: Evaluate and use the separate hermes-agent-self-evolution repo as a controlled offline optimizer for Hermes skills.
---

# Hermes self-evolution

Use this when the task is to assess, install, validate, or run the separate `hermes-agent-self-evolution` repository against a local Hermes checkout.

Do not confuse this with Hermes' built-in runtime self-improvement loop. Hermes already does background memory/skill review during normal operation. This skill is for the separate DSPy/GEPA optimization pipeline.

Reference: `references/self-evolution-validation.md` for the verified local setup and first-pass evaluation notes.

## What this is
- An offline optimizer for Hermes artifacts, not an always-on live-session mutation loop.
- Best suited to controlled improvement passes on selected skills with explicit verification.
- Currently strongest for skill evolution; broader prompt/tool/code evolution may be planned but should not be assumed live.

## When to use
- The user asks whether Hermes already implements GEPA/DSPy self-evolution.
- The user wants to install or validate `hermes-agent-self-evolution` locally.
- The user wants a cautious recommendation on whether to enable or adopt the repo.
- The user wants to run a real optimization pass on a specific skill.

## Default stance
1. Distinguish built-in Hermes self-improvement from the separate self-evolution repo.
2. Treat the repo as an optional offline optimizer.
3. Do not recommend turning it into an always-on autonomous loop by default.
4. Prefer small, high-value, frequently used skills as the first optimization targets.
5. Keep human review as the merge boundary.

## Workflow
1. Confirm the local Hermes repo path that will be optimized.
2. Clone the self-evolution repo into a disposable local workspace if it is not already present.
3. Create a local virtualenv with `uv venv` and install with `uv pip install -e '.[dev]'`.
4. Run the self-evolution repo test suite before making claims about readiness.
5. Run `python -m evolution.skills.evolve_skill --help` to confirm the entrypoint.
6. Run a `--dry-run` against the target Hermes repo before any real optimization pass.
7. If the user wants a real run, start with a compact skill that has clear success criteria and reviewable outputs.
8. Report scope and guardrails plainly: offline, cost-bearing, eval-dependent, human-reviewed.

## First target selection rules
Prefer:
- compact skills;
- high-frequency skills;
- skills with obvious success criteria;
- skills whose output quality can be judged on holdout examples.

Avoid as first targets:
- giant umbrella skills;
- protected bundled skills that should not be edited in-place;
- skills with weak or ambiguous eval criteria;
- turning the optimizer loose across the whole Hermes repo without review gates.

## Recommendation pattern
Good recommendation:
- keep Hermes' current built-in review loop as the default;
- use the self-evolution repo only for controlled offline passes;
- start with one small skill and inspect the resulting diff, constraints, and holdout score changes.

Bad recommendation:
- wire the repo into a permanent autonomous mutation loop without explicit review, cost controls, and evaluation discipline.

## Verification
Before claiming the repo is ready, verify all of:
- the repo clones successfully;
- dependencies install in a local venv;
- `pytest -q` passes;
- `python -m evolution.skills.evolve_skill --help` works;
- a `--dry-run` succeeds against the intended Hermes repo path.

## Pitfalls
- Do not present the repo as if it already replaces Hermes' built-in runtime self-improvement.
- Do not imply prompt/tool/code evolution is already production-ready if only skill evolution is implemented.
- Do not start with huge umbrella skills just because they are visible; start with smaller reviewable units.
- Do not skip local verification and rely only on the README.
- Do not bypass human review of evolved outputs.

## References
- `references/self-evolution-validation.md` — verified local setup, commands, and adoption guidance.
