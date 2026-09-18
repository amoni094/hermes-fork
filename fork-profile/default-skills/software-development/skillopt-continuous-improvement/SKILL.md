---
name: skillopt-continuous-improvement
depends_on: [hermes-skill-library-consolidation-audit]
provides: [skillopt-score, skill-quality-improvement, evidence-based-edit]
description: >
  Use when applying SkillOpt-style evidence-backed skill improvement: score skills with skillopt_score.py, diagnose gaps, propose bounded add/delete/replace edits, and accept only on clear quality improvement. Based on SkillOpt (arXiv:2605.23904, +19.1pp Claude Code). Use after tasks surface skill gaps, or as a periodic sweep.
version: 1.2.0
triggers:
  - skill quality improvement pass
  - skills scoring below threshold
  - improve skills based on session learnings
  - apply SkillOpt to Hermes skills
  - periodic skill maintenance sweep
  - skill gap detected during a task
related_skills:
  - self-improve-agent
  - hermes-self-evolution
  - agent-memory-consolidation
  - hermes-skill-library-consolidation-audit
  - writing-skills
  - gepa-omni-optimization
  - hermes-agent-skill-authoring
  - runtime-skill-synthesis
counter_triggers:
  - "For evolutionary/automated offline optimization use gepa-omni-optimization"
  - "For authoring standards and SKILL.md frontmatter use hermes-agent-skill-authoring"
  - "This skill is for post-use reflection and incremental patching only"
platforms: [linux, macos, windows]
metadata:
  tags: [skills, self-improvement, quality, SkillOpt, maintenance]
  related_skills: [self-improve-agent, hermes-skill-library-consolidation-audit]
---

# SkillOpt Continuous Skill Improvement

Applies the core SkillOpt loop (arXiv:2605.23904, Microsoft Research, +19.1pp Claude Code)
to Hermes SKILL.md files — without requiring a training loop or separate optimizer model.

The loop: SCORE → DIAGNOSE → EDIT (bounded) → ACCEPT only on quality improvement.

## Research basis

- **SkillOpt** (arXiv:2605.23904): separate optimizer model proposes bounded add/delete/replace
  edits to skill docs; accepts only if held-out validation improves. +19.1pp on Claude Code,
  +23.5pp on GPT-5.5 direct chat, +24.8pp on Codex agentic loop.
- **ExpeL** (arXiv:2308.10144, AAAI 2024): extractive insight distillation from task trajectories
  into a reusable knowledge pool — analogous to what triggers a skill edit here.
- **CoALA** (arXiv:2309.02427, TMLR 2024): procedural memory (= skills) is the key leverage point;
  episodic memory feeds it via consolidation.

## SkillOpt executive strategy (arXiv:2605.23904)

Treat skill improvement as gradient-free optimization:

1. Fitness function: task success rate on a held-out benchmark set (NOT the tasks that generated the failure signal — see arXiv:2607.12227 overfitting pitfall).
2. Evolution signal: task failure logs + session outcome tags. Skills with fitness < 0.6 on their declared task domain are candidates for evolution.
3. Evolution operator: LLM proposes a skill body patch; require an explicit user "yes" before any `skill_manage` (adversarial-review Class I: an interactive session is *not* approval). Evaluate on held-out tasks; accept if fitness improves.
4. Executive strategy: do not evolve all skills simultaneously. Prioritize the skill with the highest failure rate × task frequency product. Fix the highest-impact skill first, re-evaluate the fitness landscape, then pick the next candidate.
5. Convergence: stop evolving a skill when 3 consecutive proposals fail to improve held-out fitness — the skill may have hit its capability ceiling for the current model.

This is the outer controller for SCORE → DIAGNOSE → EDIT → ACCEPT. The scorer (`< 60/100` + high traffic) is a proxy for (2)+(4) when held-out fitness is not yet instrumented. Do not treat a high skillopt_score as proof the skill is good.

## When to run

- After a task where you hit a skill pitfall NOT documented in the skill
- After patching a skill mid-task (good hygiene to verify the patch is sufficient)
- Periodically (monthly), on the bottom-10 scoring skills from skillopt_score.py
- When a skill is loaded and you notice stale/wrong commands or missing triggers

**Safety rule**: NEVER apply edits without a clear quality justification.
SkillOpt's own finding: "Applied without human review it quickly degrades the workflow."
Every proposed edit needs a REASON tied to a real observed failure or gap.

## Step 1: Score

Run the scorer to identify priority candidates:

```bash
# Bottom 15 skills overall (excluding archive):
python3 ~/.hermes/scripts/skillopt_score.py --top 15

# Score a specific skill you just used:
python3 ~/.hermes/scripts/skillopt_score.py ~/.hermes/skills/<category>/<name>/SKILL.md

# Full report with improvement suggestions:
python3 ~/.hermes/scripts/skillopt_score.py ~/.hermes/skills/<category>/<name>/SKILL.md --quiet=0
```

Prioritize skills that score < 60/100 AND are frequently used (high-traffic skills with
gaps cause the most recurring failures).

## Step 2: Diagnose

For each low-scoring skill, check the specific gaps the scorer flagged:

| Gap flagged | Diagnosis question |
|-------------|-------------------|
| No triggers | Does the skill have clear load conditions? Can the agent discover it? |
| No pitfalls | Did any task using this skill hit an undocumented error or wrong path? |
| No verification | Can you tell from outside the skill when it succeeded? |
| No commands | Are instructions vague ("run X") vs exact ("hermes config get compression")? |
| Short description | Is the description specific enough to distinguish this from sibling skills? |

## Step 3: Edit (bounded)

SkillOpt's key constraint: **bounded edits only** — no wholesale rewrites.
Each edit must be:
- add: a new section (triggers entry, pitfall, verification step, command)
- delete: a stale/wrong entry
- replace: fix a wrong command or outdated reference

Document the proposed edit using this format, then STOP — do not call skill_manage:
```
SKILL: <name>
REASON: <what gap / failure / observation triggered this>
TYPE: add | delete | replace
LOCATION: <section heading or old_string snippet>
CHANGE: <new content>
EXPECTED QUALITY IMPROVEMENT: <what gets better: routing, avoiding error X, etc.>
```

Hand the proposal to self-improve-agent Step 4 for human review before any skill_manage call.
SkillOpt is a SCORE/DIAGNOSE skill — it proposes edits, it does not apply them.

## Step 4: Accept/Reject gate (human decision)

Present the proposal to the user. Accept only on explicit user approval.
Reject (and log why) if:
- The edit is based on a single anomalous observation
- The change makes the skill longer without adding navigation value
- The change has no clear retrieval or execution improvement

Accept-reason gate: if you can't articulate what gets better, don't merge the edit.

**Eval overfitting gate (arXiv:2607.12227):** When fitness is instrumented, score on held-out tasks, not the tasks that drove the evolution. Never report skill fitness on training tasks only. Minimum: 20% task reserve before marking a skill as improved. When fitness is not instrumented (scorer-only), the accept-reason gate is the stand-in — a higher `skillopt_score` is not held-out proof. <!-- why: training-task fitness overstates improvement; held-out can fall while unit pass rate rises -->

## Branch2Skill — MCTS Skill Evolution (arXiv 2608.08677)

Optional MCTS upgrade path — does **not** replace the SCORE → DIAGNOSE → EDIT loop.
Paper reports 73.2% fewer tokens than SkillOpt with superior performance on 6 benchmarks.

Algorithm for Hermes cron integration:
1. For a skill under evaluation, generate N task variants via delegate_task (paraphrase query)
2. MCTS tree: node = YAML skill candidate; children = perturbations (add/remove/reword step)
3. Rollout: execute skill via delegate_task subagent, collect outcome score
4. Backprop UCB1 selection; compare elite paths against sibling alternatives sharing prefixes
5. Stage the proposed winner in `~/.hermes/cache/pending-improvements/` for human review.
   Do not call `skill_manage(action='patch')` from this MCTS loop.
Store MCTS tree in SQLite (node_id, parent_id, skill_yaml_hash, score, visits). Budget: 16 rollouts.

## COBRA-Skills: Bandit-Guided Skill Candidate Prioritization (arXiv:2609.11682)

When the skill portfolio has many candidates to evaluate (SkillOpt queue, Branch2Skill, MCTS candidates), **prioritize by UCB1 score** rather than evaluating all skills equally. This reduces optimization cost by 55–58% vs. uniform SkillOpt while maintaining or improving final quality.

**UCB1 score per skill:**
```
ucb1 = mean_improvement_score + sqrt(2 * ln(total_evals_all_skills) / n_evals_this_skill)
```
- `mean_improvement_score`: average delta on held-out tasks from past edits to this skill (0 if no edits yet)
- `n_evals_this_skill`: number of times this skill has been evaluated
- `total_evals_all_skills`: sum of evals across all skills in the queue

**Apply:** Sort the SkillOpt candidate queue by UCB1 score descending before running Step 1 (SCORE). High-UCB1 candidates = either high historical improvers (exploit) or rarely-tested skills with high uncertainty (explore). Skip skills with UCB1 below a floor threshold (e.g. < 0.1) for this cycle — revisit next cycle.

**Tracking:** Add `{skill_name, eval_count, mean_improvement, last_eval_ts}` rows to `~/.hermes/cache/skillopt-bandit.jsonl` after each evaluation. The UCB1 formula requires this history.

Source: arXiv:2609.11682, "COBRA-Skills: Contextual Bandit-Guided Evolution for Agent Skill Optimization", Sep 2026. 55–58% cost reduction vs SkillOpt; 50 unique tasks sufficient across 6 heterogeneous benchmarks.



## NeSy-Spatial — Typed Atomic Tool Skills + Closed-Loop Pruning (arXiv 2608.07955)

Two skill type taxonomy — add to YAML frontmatter:
- `skill_type: tool_orchestration` — sequences of tool calls with typed inputs/outputs
- `skill_type: structured_reasoning` — CoT patterns + constraint satisfaction steps
Also add: `usage_count: 0`, `success_rate: null` — update after each invocation.
Pruning threshold: if usage_count >= 10 AND success_rate < 0.40, flag for review.
Closed-loop: buffer success/failure trajectories in Hindsight; periodic analysis → pitfalls update.

## Generic > Personalized: Empirical Validation (arXiv:2608.10319, Aug 2026)

"Do Personalized Skills Help Coding Agents?" — empirical study of developer interaction histories. Key finding: **generic skills pooled across all users achieve the largest, most consistent gains. Personalized skills show small, inconsistent improvements.** Personalization only helps when the same preference appears ≥3 times in history.

Hermes implication:
- Do NOT create user-specific skill variants unless the behavior has appeared ≥3 times in session history
- Invest in making existing generic skills more robust (wider trigger coverage, better examples) rather than narrowing them to user-specific use cases
- The current Hermes skill library design (generic procedural skills) is empirically validated

Promotion gate: only promote a pattern from `USER.md` (personal preference note) to a skill when it has 3+ independent session observations.

## Prompt-Space Skill Evolution (ZO-SelfEvolve Analogue, arXiv:2608.09292)

ZO-SelfEvolve uses zeroth-order gradient estimation to evolve agent parameters without trajectory labels. The prompt-space analogue applies the same principle to skill instructions without model weights:

When a skill consistently fails on specific task patterns:
1. Identify hard examples — collect 2-3 concrete cases where the skill produced wrong output
2. Generate N variants — produce 3-5 slight rewrites of the skill's key instruction block (vary emphasis, order, specificity, examples)
3. Score variants — apply each variant mentally or via a delegate_task scoring pass
4. Stage the best-scoring variant in `~/.hermes/cache/pending-improvements/` for human review.
   Do not call `skill_manage(action='patch')` from this loop.

Trigger: use when a skill has been invoked 3+ times with the same failure mode. Keep N ≤ 5 to bound cost.

## SkillZip — MDL-Guided Skill Deduplication (arXiv:2608.11079, Aug 2026)

Self-evolving agents accumulate bloat: the same requirement gets restated across branches,
examples, and warnings; common action sequences are copied rather than reused. SkillZip
formalizes compression as a typed MDL objective over a skill contract + residual, with a hard
coverage constraint (every trigger, workflow edge, tool requirement, output field must still be
reachable). Key principle: **"explain once, reference many"** — state a repeated rule at the
widest applicable scope, factor repeated action sequences into shared procedures, keep only diffs
as exceptions in individual skills.

**SkillZip pass** (add to each consolidation run):
1. After detecting duplicated warnings, workflow edges, or tool usage patterns across 3+ skills,
   factor the shared rule into the widest-scope skill (or a shared procedure skill) and replace
   per-skill copies with a `See: <skill-name>` cross-reference.
2. After each proposed patch (before submitting to self-improve-agent for review), verify the trigger-to-action
   mapping is still complete (no orphaned step). Prevent re-introducing a rule already in the
   shared library.
3. Use `Zip-on-Write` discipline: before writing a new rule to a skill, grep the skill library
   for the same principle. If found elsewhere, add a cross-reference instead of a duplicate.
4. For each skill with > 500 lines, list H2/H3 sections. If `session_search` finds 0 hits in 90 days
   for a section topic, it is a prune *candidate* (not automatic deletion).
5. Near-duplicate sections in one skill: merge. Same pattern in two skills: keep the canonical skill
   and cross-reference. After pruning, run `acceptance_criteria` if present.
6. MDL target: 20-30% word-count cut on skills > 500 lines without new task failures. If a 10%
   cut would cause failures, leave the skill alone.

## Pitfalls

- **Premature trigger addition**: adding triggers that are too broad makes the skill
  load when it shouldn't, injecting noise. Triggers should be specific, not aspirational.
- **Pitfall inflation**: every tool quirk doesn't belong in every skill. A pitfall that's
  already in a linked skill should be a cross-reference, not a copy.
- **Verification theater**: "check that it worked" without a concrete command is not a
  verification step. Every verification step must have a real command or observable output.
- **SkillOpt's training-loop trap**: the full SkillOpt system uses a separate optimizer
  model trained on rollouts. Without that, this skill's scoring is heuristic-only. Don't
  treat a high score as proof the skill is good — only treat a low score as a signal to look.

## Verification

After patching a skill, verify:
1. Re-run scorer — score should increase: `python3 ~/.hermes/scripts/skillopt_score.py <path>`
2. Load the skill and check it reads naturally: `skill_view(name='<name>')`
3. If triggers were changed, confirm the new triggers would have fired on the task that
   prompted the improvement (mental simulation is sufficient — no automated test needed).

## Periodic sweep cadence

Monthly (or after a burst of new skills/patches):
```bash
python3 ~/.hermes/scripts/skillopt_score.py --all --quiet | grep "YES" | wc -l
```
Target: < 20% of active skills flagged as priority-fix.
If > 30% are flagged, run a full consolidation pass with hermes-skill-library-consolidation-audit.

## Aug 2026: Muscle Memory Pattern — Compile, Don't Retrieve (arXiv:2608.08995)

Source: "Muscle Memory for Agents: Compile not Merely Retrieve"
Instead of retrieving stored experience, mines conversational history for recurring behavioral
patterns and COMPILES them into purpose-built "specialist" mini-skills via:
Harvest → Analyze → Augment → Evaluate pipeline.
Results: 88.9% win rate when specialist fires, +2.05 personalization vs -0.28 accuracy cost.

**Hermes implementation:**
After the memory-consolidation cron identifies a recurring task pattern (same task type
solved 3+ times in session history), generate a compact SKILL.md stub capturing:
- Trigger: the recurring task pattern
- Steps: the solution sequence that worked
- Pitfalls: failures observed across the instances
Generate a stub and pass to self-improve-agent Step 4 for human review. Do not call skill_manage create directly.
Route future matching tasks to this compiled skill instead of raw retrieval, only after that review lands.
This is the "compile over retrieve" principle — the skill IS the compiled experience.

### SkillShapley — Shapley-Value Step Attribution for Skill Pruning (arXiv:2608.13173) ★ HIGH
Source: Sweep 13. Assigns Shapley values to individual steps within a skill to isolate which
steps actually contribute to task success vs which are dead weight.

**Core finding:** Many multi-step skills have 30–60% of steps with near-zero Shapley value
(they don't move outcomes). Pruning them reduces skill length without accuracy loss.

**Hermes implementation:**
During skillopt audit pass, for each skill with >= 5 steps:
1. Sample 5-10 recent task runs that used this skill (from session_search).
2. For each run: which steps were actually executed? Which were skipped? Did the task succeed?
3. Assign a "step weight" = (% of successful runs that executed this step) / (% of all runs).
4. Steps with weight < 0.2 across 5+ runs are candidates for pruning.
5. Flag in skill audit output with `[low-shapley]` tag; do NOT auto-delete — propose to user.

Practical shortcut: steps that are never mentioned in session transcripts of successful runs
(grep for key verbs from the step) have effectively zero Shapley value.

### SkillEvo — Multi-Turn Governance-Layer Skill Evolution (arXiv:2608.13120) ★ HIGH
Source: Sweep 13. Governance layer that wraps skill updates: propose → validate → accept.
Key finding: ungoverned skill updates (direct edits after task success) cause 23% regression
on previously-passing task types within 5 days (catastrophic forgetting pattern).

**Hermes implementation:**
Before any skill_manage patch/edit (which requires explicit user approval via self-improve-agent):
1. State the specific improvement being made and why.
2. Check: does this change break the skill's existing trigger criteria? If yes, update trigger.
3. Check: does this change remove a pitfall that was still relevant? If yes, keep it.
4. After editing: run a mental test — does the skill still apply correctly to its 3 canonical
   use cases? If not, revise before saving.
This is lightweight governance — no separate validation script required. The 4-step check
prevents the most common regression pattern (trigger drift + pitfall erasure).

### RRM Reflective Experience Lifecycle — Frequency + Decay for Skill Pruning (arXiv:2607.28156)
Source: Sweep 13. Skills behave as the reflective experience memory tier (RRM analogue).
RRM lifecycle: prune nodes by usage frequency, reuse feedback, and temporal decay.

RRM Lifecycle: prune procedural memory (skills) by usage frequency × temporal decay. Skills that haven't been loaded in >30 days AND have no recent successful task completions logged against them are candidates for archival. Usage frequency tracked via session logs; temporal decay factor: 0.9 per 7-day period of non-use.

**Hermes prune criteria (RRM-derived):**
- Usage frequency: skill not triggered in last 30 days → candidate for archival.
- Reuse feedback: skill triggered but task failed (user corrected) → candidate for revision.
- Temporal decay: skill references a tool/API/model that no longer exists → stale, prune.
Note: Hermes does not automatically write last_used or triggered fields into SKILL.md at runtime. The grep above returns nothing useful. Instead, use session_search to manually assess recency for specific skills, or log to ~/.hermes/cache/skill-usage.jsonl from sessions that load skills to build a queryable usage history.
Skills passing none of the three criteria should be kept regardless of size.

### TMLR 8-Stage Skill Lifecycle (arXiv:2607.10113, Yubo Li CMU)

Evidence-graded model for skill library governance at 100+ skills. Maintenance is load-bearing:
without periodic prune+merge, pass rate drops 35.6%→31.1%, repo bloats 4.5×,
utilization crashes 0.71→0.08 (AutoRefine, arXiv:2601.22758).

Eight stages applicable to Hermes SkillOpt cron design:
1. Evidence acquisition — trajectories, failures, user corrections (load from session_search + skill-failures/*.jsonl)
2. Proposal — Add / Refine / Merge / Split / Distill / Abstract (6 distinct operations)
3. Verify & Admit ← GATE: most critical; curated > unverified self-generated by +23.5pp (ASI)
4. Organize — flat → tree → DAG topology; Hermes at 170 skills needs structured retrieval
5. Retrieve & Compose — routing_signals field enables accurate retrieval at this scale
6. Maintain & Repair ← load-bearing: failure trajectories are the best repair input (all 11 successful repairs used them)
7. Distill & Port — slow loop, cross-session knowledge transfer (what l1-promote.py does)
8. Governance — lifecycle_stage, provenance, lineage, supersedes fields

**Practical SkillOpt cron extension:** read ~/.hermes/skill-failures/*.jsonl before each
maintenance pass. Skills with ≥3 failure entries in the last 30 days are repair candidates.

## Catastrophic Remembering Rationale Audit (arXiv:2608.11095) — combined with SkillZip
When pruning a section, check its rationale comment first (see hermes-agent-skill-authoring).
If the section has a rationale comment explaining WHY it exists, the rationale must be
explicitly refuted before removal — not just "it hasn't been used recently".
A section with a strong rationale and low recent usage may be a safeguard for rare edge cases.
Distinguish between "not needed often" (OK to archive) vs "needed rarely but critically" (keep).

### Macaron-V1 — Versioned Skill Acceptance Contracts (arXiv:2608.09819)
Each skill version gets acceptance criteria (test cases). After cron-based SkillOpt proposes
a skill update, only accept if it passes the contract. Self-improvement becomes bounded.
**Hermes:** Add `acceptance_criteria` field to SKILL.md frontmatter. Example:
```yaml
acceptance_criteria:
  - "skill trigger fires on 'which model should I use'"
  - "routing table covers all 3 active tiers"
  - "no stale model names"
```
Validate during consolidation audit pass: check criteria are satisfied before version bump.

## Four-Tier Pruning Decision Matrix (agent-skill-management-research-2026)

For each skill, classify by recency × success rate:
- **ACTIVE** (recent use + high success): keep, update pitfalls only
- **ACTIVE_DORMANT** (infrequent use + high success): keep, move to cold category
- **MERGE** (overlap hint: cosine > 0.92 OR shared triggers/steps): do **not** delete on cosine. Load `runtime-skill-synthesis` step 5 — classify DISTINCT/COMPLEMENT/OVERLAP/DUPLICATE, merge into dominant, set `supersedes`/`superseded_by`, archive only after Pass^k ≥ 3 on the dominant
- **ARCHIVE/DELETE** (no use in 90d + low success, or content fully absorbed): archive or delete

Run this classification pass monthly via LLM-induced re-clustering prompt over skill names +
descriptions. Log decisions in a `pruning-log.md` reference file under the skill.

## Composite Quality Score (agent-skill-management-research-2026)

Q = 0.35 × success_rate + 0.25 × (1 - correction_rate) + 0.20 × invocation_frequency + 0.20 × recency_score

- success_rate: task completions without user correction / total invocations
- correction_rate: explicit user-override patches / invocations
- invocation_frequency: normalized to 0–1 across library
- recency_score: 1 if used in last 30d, decays to 0 at 90d

Score < 0.40 → candidate for archive. Score > 0.75 → pin-eligible.

## Evidence-Gated Resurrection (agent-skill-management-research-2026)

Archived skills can be resurrected if: (a) an active-set skill fails on a task AND
(b) a cosine search of the archive finds a match with similarity > 0.70.
Before resurrecting, load the archived skill, verify it addresses the active failure case,
then re-add with a `resurrected: true` frontmatter flag and a note on what triggered it.

## Runtime synthesis gates (ARISE / SkillAlchemy / Pass^k)

SkillOpt edits existing skills. Creating, admitting, merging, or promoting skills is
`runtime-skill-synthesis` — load it instead of improvising. Minimum SkillOpt hooks:

1. **Do not create from a score gap.** A low skillopt_score is an edit signal, not a new-skill
   signal. New skills need ARISE harvest (`trace2skill.py SESSION_ID`) plus the SkillAlchemy
   admission checklist (2+ traces, implicit-requirement pitfall, overlap audit).
2. **Failure logs before repair.** Read `~/.hermes/skill-failures/<name>.jsonl` in Diagnose.
   Pair the latest fail with the latest pass in `~/.hermes/skill-quality/<name>.jsonl`. Patch
   only the contrastive delta (EvoAgent). If the jsonl files are missing, create the dirs and
   log this run — do not invent a repair from memory.
3. **Pass^k, not Pass@1.** After a skill-using task, append `{date,session,outcome,task_class}`
   to `~/.hermes/skill-quality/<name>.jsonl`. Promote `experimental`→`validated` only on Pass^3
   (3 consecutive independent sessions) and `validated`→`production` on Pass^5 plus at least
   one patched failure trajectory. A single successful SkillOpt edit does not promote.
4. **Monthly sweep extra:** `ls ~/.hermes/skill-failures/` (≥3 fails / 30d = repair-first),
   overlap-classify flagged pairs, then pending `skill-candidate-*.md` through admission.

