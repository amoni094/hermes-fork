---
name: hermes-self-evolution
triggers:
  - User asks whether Hermes already implements GEPA or DSPy self-evolution
  - User wants to install or validate hermes-agent-self-evolution locally
  - Running the separate hermes-agent-self-evolution repo as a controlled offline optimizer
  - Evaluating whether skill self-improvement can be done safely offline
description: >
  Use when evaluating and using the separate hermes-agent-self-evolution repo as a controlled offline optimizer for Hermes skills (DSPy/GEPA). For post-task in-session lesson extraction use self-improve-agent instead.
related_skills:
  - gepa-omni-optimization
  - self-improve-agent
  - autonomous-agent-loop-design
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

## Self-Improvement Traps — Critical Failure Modes

The following failure modes are documented in production agent systems and are directly relevant to this skill:

### 1. Self-Validation Loop
**Pattern:** Agent uses the same skill it just modified to evaluate whether the modification was correct. Circular.
**Detection:** Check if the evaluator invokes the skill being evaluated.
**Mitigation:** Always evaluate against examples that predate the modification. Never use the modified skill as its own test harness. Use a fixed holdout example set for skill evaluation (store in `~/.hermes/skills/.tests/`).

### 2. Confirmation Bias in Skill Updates
**Pattern:** Agent proposes a skill modification, then searches for evidence supporting the change rather than falsifying it. Results in skills that appear well-justified but fail on unseen cases.
**Detection:** Track whether the post-modification search was "does this work?" vs "how does this fail?".
**Mitigation:** Required adversarial pass: after any skill modification, explicitly ask "under what conditions does this new behavior fail?" before writing the patch. At least 2 failure conditions must be identified.

### 3. Reward Hacking in Skill Evaluation
**Pattern:** Skill evaluation metric improves (e.g. "no errors in last 5 invocations") but real-world utility degrades because the metric is gameable (skill narrowed its trigger to avoid error cases).
**Detection:** Monitor trigger breadth over time. If a skill's trigger list shrinks across revisions, investigate.
**Mitigation:** Track both precision (correct when invoked) and recall (invoked when needed). A skill that never triggers is not a good skill.

### 4. Osmosis Drift (Regression Tax, arXiv:2607.22520)
**Pattern:** Over time, accumulating skills in the system prompt biases agent behavior even on tasks where no skill is explicitly loaded. Behavior shifts without any skill being invoked.
**Detection:** Run a baseline task (no skills loaded) periodically and compare against skill-loaded behavior on the same task. Divergence > 10% is a signal.
**Mitigation:** Quarterly: prune skills whose trigger-57-char-description contains action verbs rather than context descriptions. Action verbs in descriptions are the highest osmosis risk.

## Core Workflow
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
- SkillProx insight (arXiv:2608.07449): skill updates must be proximal — constrained distance from working version. Large rewrites break previously working cases. Apply this as a filter: if a proposed skill diff changes >40% of lines, break it into smaller passes.
- Self-Confirmation Trap (arXiv:2606.24428): agents mistake wrong-but-self-consistent trajectories for success. When writing a skill patch from session experience, the LLM's own approval of the patch is NOT verification. The verify step must use an independent check: does the patched skill reproduce the successful outcome on a fresh task?
- Single-trajectory weakness (SkillCAT, arXiv:2606.13317): a skill patch derived from one failure has weak evidence. Before committing, ask: what succeeded vs failed across multiple attempts? Contrastive evidence (CCE principle) is stronger than single-case reasoning.
- Retrospective beats online (RePro, arXiv:2606.14302): do not interject with progress assessments during execution. Reflect AFTER the trajectory completes. "How far did I get and why?" is a post-hoc question.

## ERL heuristic distillation (arXiv:2603.24639, ICLR 2026 MemAgents)
When a task completes (success or failure), explicitly reflect to extract a transferable heuristic:
  - What was the generalizable lesson? (not: what did I do step by step)
  - Heuristics transfer across tasks better than few-shot trajectory examples.
  - Selective retrieval of heuristics is essential — do not inject all past lessons at once.
This pattern is what Hindsight [procedural] memory entries should capture: distilled heuristics,
not verbatim procedure transcripts. Apply at session end or after difficult tasks.

## Research context (Aug 2026)
Key papers informing this skill's design:
- arXiv:2608.07449 (SkillProx) — proximal textual gradient descent for conservative skill evolution
- arXiv:2604.05333 (GoS) — dependency graph enables safe targeted updates (only update leaves, not roots)
- arXiv:2604.24026 (SSL) — risk_level in ssl_logical frontmatter informs update caution level
Master synthesis: ~/.hermes/skills/autonomous-ai-agents/autonomous-ai-agents/references/hermes-improvement-master-2026.md

## References
- `references/self-evolution-validation.md` — verified local setup, commands, and adoption guidance.
