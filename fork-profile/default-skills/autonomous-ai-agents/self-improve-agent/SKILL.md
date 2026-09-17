---
name: self-improve-agent
description: >
  Use when: After a task or agentic run completes, scan the execution for high-signal lessons and propose targeted updates to skills, CLAUDE.md, or AGENTS.md. MUST be human-gated before any changes are applied. On task failure, write a Reflexion-style verbal reflection to Hindsight for the next attempt (not a skill patch). Double-edged: can continuously improve a workflow or quickly degrade it if applied without review.
version: 1.3.0
triggers:
  - "self-improve after this run"
  - "update the skill based on what we learned"
  - "what should we improve in this workflow"
  - "propagate lessons from this run"
  - "update CLAUDE.md based on this session"
  - "task failed, write a reflection"
  - "reflexion"
  - "what to try next time after this failure"
related_skills:
  - ralph-loops
  - autonomous-agent-loop-design
  - agent-runtime-loop-patterns
  - subagent-driven-development
  - hermes-self-evolution
  - trajectory-risk-guardrail
  - verification-before-completion
  - agent-task-signoff
  - agent-memory-consolidation
  - runtime-skill-synthesis
  - skillopt-continuous-improvement
boundary_note: >
  self-improve-agent = post-task lesson extraction within a live Hermes session (human-gated patches to skills/CLAUDE.md).
  hermes-self-evolution = the separate offline DSPy/GEPA repo for automated evolutionary optimization. Load hermes-self-evolution only when working on that separate repo.
---

# Self-Improve Agent

Pattern from Squid (Paul Iusztin, May 2026): after a feature is built and merged, an
optional meta-agent scans the run for high-signal lessons and proposes updates to the
agentic coding layer (CLAUDE.md, skills, subagent configs).

<!-- metacognition wiring: see adaptive-agent-reasoning skill -->
After running a self-improvement cycle on a complex task, calibrate the complexity classifier:
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py calibrate --predicted PRED --actual ACT
Load adaptive-agent-reasoning for FOK/JOL gating before re-attempting failed steps.


## Critical Safety Rule

**This step MUST be gated by a human reviewer before any changes are applied.**

Before proposing any skill changes, run `trajectory-risk-guardrail` to classify
proposed mutations as SAFE/CAUTION/DANGER. Reject DANGER mutations without review.
After human approval and applying changes, run `verification-before-completion`
and produce an `agent-task-signoff` table listing what changed and why.

The self-improve agent is a double-edged sword:
- Applied with human review: it continuously improves the workflow
- Applied without review: it quickly degrades the workflow by encoding past mistakes
  as permanent behavior

Never run self-improve **skill/config patches** in a fully autonomous loop without human approval of changes.

The Reflexion verbal buffer below is **not** a skill patch: on task failure, write it to Hindsight without waiting for review.

## Reflexion verbal episodic buffer (on failure — not a skill patch)

Shinn et al., [Reflexion](https://arxiv.org/abs/2303.11366) (NeurIPS 2023): after a failed trial the agent writes a *verbal* reflection (why it failed + what to try next) into an episodic buffer and conditions the next attempt on that text. No weight updates. 91% HumanEval pass@1 vs GPT-4 80% in the paper's coding agent (paper benchmark, Hermes coding-agent setup, not a Hermes SLO).

This is **not** EvoAgent / RethinkSkill / AutoSaddler. Those turn failures into **skill-body patches** (procedural memory) and stay human-gated. Reflexion stores a **single-attempt verbal trace** so the *next try of the same task type* does not repeat the same error class. Do not skip the buffer because you plan to patch a skill later.

| Reflexion component | Hermes mapping |
|---|---|
| (a) Evaluator | External signal: test/linter exit, `verify_on_stop`, user correction, circuit-breaker `stop-fail`. Do not self-grade success. |
| (b) Self-reflection | Structured prose: what failed, why (structural cause), what to try next. |
| (c) Episodic buffer | `hindsight_retain` tagged by task type. Not Graphiti (confirmed 2+ session lessons only). Not a SKILL.md edit. |
| (d) Multi-trial loop | Next attempt (same session retry, ralph iteration, or later session) recalls before acting. |

### When it fires

Fire when the **task or attempt** failed — not on every in-session tool error that already recovered (those are MERIT / LivePlan in `agent-runtime-loop-patterns`).

Triggers: tests red, verifier fail, user had to correct a wrong result, abort after retries, circuit-breaker stop-fail, ralph iteration that did not meet the exit condition.

Skip: one-off tool timeouts that succeeded on retry; cosmetic gaps; successes.

Cap: **one reflection per failed attempt**. Do not write on success. Do not encode the reflection as a global skill rule in the same step.

### Write (no human gate)

```
hindsight_retain(
  content=(
    "REFLEXION task_type=<slug>\n"
    "what_failed: <observable failure, not a vibe>\n"
    "why: <structural cause — wrong tool, lost precondition, bad assumption>\n"
    "try_next: <concrete alternative for the next attempt>"
  ),
  context="reflexion-failure",
  tags=["reflexion", "failure", "task_type:<slug>"]
)
```

`<slug>` is a short task class (`skill-patch`, `git-pr`, `web-extract`, `pdf-fill`), not the full user prompt. `why` must name a cause, not "be more careful".

Do **not** write this to Graphiti. Do **not** call `skill_manage` from this step. Those remain the human-gated path in Steps 3–6.

### Read before the next attempt

Before retrying the same task type (same session or a later one):

1. Recall `hindsight_recall` / memory search with tags `reflexion` + `task_type:<slug>` (or query `REFLEXION task_type=<slug>`).
2. If a prior reflection exists, treat `try_next` as a constraint: do not repeat `what_failed`.
3. If 3+ reflections for the same slug share the same `why`, escalate to the human-gated Avoid-rule / EvoAgent skill-patch path — the error class is now procedural, not episodic.

## Failure-to-knowledge pipeline (ANNEAL / FDKA, arXiv:2605.16309)

Recurring failures should patch **process knowledge** (typed, canary'd, human-gated) — not accumulate more logs or freeform prompt appends.

When the **same error class** recurs **3+ times** in session history (same Reflexion `why`, same exception signature, or same tool+error token), trigger a **skill-patch proposal** for the owning skill. Do not stop at another `hindsight_retain`.

Pipeline:
1. **Detect** — `session_search` / Reflexion tags `task_type:<slug>` / repeated cobra-outcome-logger wasteful events. Count ≥3 of the same class.
2. **Map** — error class → the skill whose procedure should have prevented it. If none, name the gap; do not dump the error into MEMORY.md.
3. **Propose** — a typed skill patch (Avoid-rule, missing precondition, or step insertion). Not a narrative "be more careful" append.
4. **Canary** — human gate first (this skill's Critical Safety Rule). Keep the old SKILL.md until one successful replay of the failing task class.
5. **Stop logging-only** — after a declined patch, do not re-propose the same patch for the same error within 7 days; further identical failures do not justify a fourth identical Reflexion as the only action.

If a proposed skill patch is declined by the user, do not re-propose the same patch for the same error within 7 days.

This is the named 3+ escalation: logging is episodic; the third recurrence is procedural.

## When to Run

Run self-improve AFTER a task completes, as an optional, human-initiated step:
- After a complex multi-agent run that encountered unexpected problems
- After a `/night` or end-to-end workflow run where patterns emerged
- After debugging a non-obvious failure that took multiple attempts
- After discovering a tool quirk or agent behavior pattern
- Periodically (e.g., monthly) on frequently-used skills

Do NOT run SKILL/CONFIG PATCHES automatically. Reflexion (reflect on failure and log) may fire automatically after task failure. Only skill_manage calls require human gate.

Do NOT run skill/config patches:
- Automatically on every task (noise-to-signal ratio too high)
- On simple or one-off tasks with nothing generalizable
- On tasks where the "lesson" would encode a context-specific workaround as global rule

## Process

### Step 1 — Scan the run

Review the completed run or session for:
- Steps that failed unexpectedly and required backtracking
- Tool calls that returned surprising or unhelpful results
- Instructions that were misinterpreted or required clarification mid-run
- Agent behaviors that diverged from what the skill described
- Patterns that improved quality or speed when applied
- Any context that had to be re-explained from scratch (signals a skill gap)

### Step 2 — Identify high-signal lessons

A high-signal lesson has ALL of:
- Generalizable (applies beyond this specific task)
- Actionable (can be expressed as a concrete instruction change)
- Not already in the existing skill/config
- Likely to recur in future similar tasks

Low-signal lessons (skip these):
- Context-specific workarounds ("use X because project Y has Z bug")
- One-off edge cases that are unlikely to repeat
- Preferences that vary by user request
- Vague generalizations ("be more careful")
- Patterns already fully covered by an existing loaded skill — before tagging something as a gap, read the relevant skill; many "missing" patterns are already there

#### Generating Avoid rules from failures

On failure, trace backwards to the structural root step before writing the lesson:
identify the wrong output → walk back to the step that produced the bad input →
name the structural cause (prompt gap, wrong tool, lost context handoff, topology
mismatch). Then write the Avoid rule targeting that cause, not the symptom.

Bad: "be more careful with context"
Good: "Avoid passing raw history (> 3000 tokens) to reviewer subagents on
large-file tasks — use artifact-only propagation instead"

#### Preserve / Modify / Avoid classification

For every high-signal lesson, assign an action before writing it:

- **Preserve** — a pattern that worked and should be kept exactly as-is
- **Modify** — a pattern that partially worked but needs adjustment for the next use
- **Avoid** — a pattern that caused failures, cost overruns, or coverage loss

Avoid-rules are first-class outputs. Do not skip them. A negative lesson ("this
topology / this approach caused X failure") is as valuable as a positive one and
prevents the same mistake from being re-encoded as normal behaviour.

#### Falsification gate (QueenBee discipline)

Before writing any Preserve or Modify lesson to a skill, apply this gate:

1. Identify a second, distinct example from the session (or a prior session via
   `session_search`) where the same pattern was used.
2. Does the lesson hold on that second example? If yes: write it. If no or unknown:
   downgrade to a candidate note, not a skill patch.

This prevents a lucky single run from masquerading as a design principle. A lesson
confirmed on only one run gets flagged as "single-run evidence — not yet generalised"
in the proposed change, so the human reviewer can decide whether to accept it.

### Step 3 — Formulate targeted changes

For each high-signal lesson, produce a concrete, minimal diff:
- **Skill patch**: add a new section, update a step, add a pitfall, or correct wrong guidance
- **New skill**: if the lesson represents a whole new pattern not covered by any skill
- **CLAUDE.md / AGENTS.md update**: if the lesson is project-specific context or a convention
- **Memory entry**: if the lesson is a durable user preference or system fact

  Memory proposals follow the full `agent-memory-consolidation` loop (Steps 1–7 there). The quick gate for deciding whether to even propose one:
  - Recency ≥ 1: fact will still matter in 30+ days
  - Utility ≥ 1: without it, agent must re-ask or re-discover
  - Uniqueness ≥ 1: not already captured in memory or an active skill
  - Total ≥ 2 required. Otherwise route to Hindsight staging or skip.
  - Falsification gate: only promote episodic → semantic when the pattern appeared in 2+ independent sessions. Single-run evidence → Hindsight only.
  - If in doubt about which surface fits, consult `hermes-memory-surface-selection` decision rules.

Format each proposed change as:
```
TARGET: <file path>
TYPE: patch | new | memory
ACTION: preserve | modify | avoid
EVIDENCE: single-run | confirmed (2+ examples)
REASON: <one-sentence justification>
CHANGE:
<exact proposed content>
```

Include ACTION and EVIDENCE on every proposal. Proposals with `EVIDENCE: single-run`
should be clearly marked as provisional in the proposed change text so the reviewer
knows the falsification gate was not passed.

### Step 4 — Present to human for review

Present ALL proposed changes to the user. Do NOT apply any without explicit approval.

For each proposed change:
- Show the target file and current content (if patching)
- Show the exact diff or new content
- State the lesson that motivated it
- Ask explicitly: "Apply this change? [yes/no/modify]"

### Step 5 — Apply approved changes

Apply ONLY the changes explicitly approved. For rejected changes, note the rejection reason
briefly — do not re-propose the same change in the next session without new evidence.

### Step 5b — ACON failure-analysis compression (arXiv:2510.00615, ICML 2026, Microsoft Research)

When a task produces context that is too long, token-expensive, or causes agent errors,
run a failure-analysis pass to refine your compression guidelines — not just compress
the content, but improve *how* you compress in future:

1. Identify the compression failure: was the context too long? Did summarization drop
   a critical constraint? Did the agent lose track of a key variable?
2. Write a one-sentence compression guideline update:
   "When compressing <task type>, always preserve <critical element> and discard <noise pattern>."
3. Store this as a Graphiti fact in group hermes-reasoning under entity "compression-guidelines".
4. On the next similar task, retrieve these guidelines BEFORE compressing:
   `mcp_graphiti_search_memory_facts(query="compression guidelines <task type>", group_ids=["hermes-reasoning"])`

This makes the compression policy itself self-improving: each failure refines the guidelines,
and the guidelines are retrieved and applied on future tasks. 26-54% token reduction on
AppWorld/OfficeBench benchmarks. The mechanism is distinct from structural pruning (AgentPrune)
or token-level compression (LLMLingua) — it operates at the guideline/policy level.

### Step 6 — Write approved lessons to Graphiti (experience retrieval loop, K3 pattern)

After applying approved skill/memory changes, write a structured outcome record to Graphiti
so future similar tasks can retrieve it as few-shot context:

```python  # pseudocode — import json at top of any real script
mcp_graphiti_add_memory(
    name="<TaskType>: <one-line summary>",
    episode_body=json.dumps({
        "task_type": "<classification, e.g. 'adversarial-review', 'skill-patch', 'delegation'>",
        "what_worked": "<key technique or approach>",
        "what_failed": "<if applicable>",
        "lesson": "<one declarative sentence>",
        "skill_patched": "<skill name if applicable>",
        "evidence": "confirmed | single-run"
    }),
    source="json",
    group_id="hermes-reasoning"
)
```

This closes the experience retrieval loop: the lesson is now retrievable on the next
similar task via `mcp_graphiti_search_memory_facts(query="<task type>", group_ids=["hermes-reasoning"])`.

Pattern source: K3 (RISS 2024–2025, Korean) + ExpeL (Zhao 2024) — extend the ExpeL trajectory-pair
pattern with explicit Graphiti writes so lessons survive context compression and session boundaries.

Constraint: only write approved, confirmed lessons. Do not write provisional single-run observations —
those go to Hindsight staging only (hindsight_retain), not Graphiti.

## 5-Axis Self-Evaluation Rubric

Before proposing skill/memory updates, optionally run this rubric to assess the completed task.
Score each axis 1–5. Evidence is REQUIRED for any score below 5 — name the gap, don't just name the rating.

| Axis | Score (1-5) | Evidence (if < 5) |
|------|-------------|-------------------|
| **Accuracy** — did the output match the ground truth / spec? | | |
| **Completeness** — were all required parts addressed? | | |
| **Clarity** — could a fresh agent resume from the output? | | |
| **Actionability** — can the result be acted on directly? | | |
| **Conciseness** — was there unnecessary repetition or padding? | | |

Anti-patterns to avoid:
- Giving everything a 5 (uncritical rubber stamp)
- Penalizing scope creep that was actually warranted
- Re-litigating design decisions made before the task started
- Using the rubric to block a task-complete signal when only cosmetic gaps remain

Only surface the rubric output if it produces at least one score < 5 with concrete evidence. A perfect 5/5 across the board needs no report.

## Muscle Memory for Agents: Compile Not Merely Retrieve (arXiv:2608.08995, Aug 2026)

Core argument: retrieval is the wrong default for personalization. Recurring user patterns
should be *compiled* into purpose-built specialist sub-agents, not re-retrieved each turn.

4-phase pipeline:
1. Harvest — mine conversational history for recurring intent patterns (format, depth, scope)
2. Analyze — separate behavioral patterns (how user wants responses) from task patterns (what)
3. Augment — emit quality-gated executable specialist agents with two-stage trigger matching
4. Evaluate — hold-out scenarios validate specialist fires correctly

Empirical: 88.9% win rate (32/36 cases where specialist fires), +2.05 personalization gain,
only -0.28 accuracy cost on 1-4 scale across 90 scenarios / 5 user personas.

Hermes apply: When session_search reveals a pattern repeated 3+ times (same format request,
same scope correction, same depth preference), instead of remembering the fact, write a
mini-skill or memory entry that embodies the compiled behavior — a specialist trigger.
E.g., "User always wants top-3 bullet lists for research summaries" → skill trigger entry,
not just a memory note. This is compilation, not retrieval.



## RethinkSkill: Feedback Dynamics for Skill Evolution (arXiv:2608.02636, Jul 2026)

Key empirical findings on when and how skill evolution actually works:

**Sparsity reality:** Only 55/388 candidate skill evolutions (14%) become byte-distinct
validation bests. Do NOT evolve skills on every run — most attempts produce no improvement.
Only trigger skill evolution after 3+ user corrections or task failures involving that skill.

**Failed trajectories are required:** Success-only feedback CANNOT improve skills. Extra
test-time compute (parallel sampling) gets within 0.43 points on SearchQA but 30.96 points
behind on SpreadsheetBench — skill persistence is irreplaceable for specialized domains.

**Implementation:**
- Add `failed_trajectories: [session_id_list]` to SKILL.md — the skill optimizer must see
  these alongside successful ones.
- Validation-based selection: before replacing SKILL.md, run old vs. new version on 3+
  held-out tasks; only promote if new version wins majority.
- Implement validation/downstream metric disaggrement check: if validation says "improved"
  but downstream task score doesn't, trust the downstream score.

**When to NOT evolve:**
- After a single run (single-run evidence, no confirmed second example)
- When the "failure" was actually user preference change, not skill deficit
- For one-off task-specific workarounds

## SkillOpt: text-space skill optimization (arXiv:2605.23904, MS Research 2026)

The first verified optimizer for agent skill documents. The pattern:

1. Optimizer model proposes bounded edits to a SKILL.md
2. Run the modified skill on a held-out task set (minimum 5 tasks)
3. Accept the edit only if measured performance improves (routing_precision delta >= 0.05)
4. Repeat until no edit improves further

Results: +23.5pp accuracy in direct chat, +24.8pp inside Codex on skill-gated tasks.
Prioritize skills with: ambiguous trigger conditions, high user_correction_rate, or known
gaps from post-task self-improve passes.

Use `python3 ~/.hermes/scripts/skillopt_score.py --top 15` to find lowest-quality skills.
See `skillopt-continuous-improvement` skill for the full SCORE→DIAGNOSE→EDIT→ACCEPT loop.

## MetaSkill-Evolve: recursive meta-skill optimization (arXiv:2607.05297, Jul 2026)

Two-timescale extension of SkillOpt: fast task-skill loop + slow meta-skill loop that
improves the improvement procedure itself. Five pipeline agents: Analyzer, Retriever,
Allocator, Proposer, Evolver — all API-only around one frozen backbone.
Results: +23.5pp OfficeQA, +16.1pp SealQA, +1.9pp ALFWorld over raw backbone.

When applying SkillOpt stalls (no further improvement from per-skill edits), apply the
meta-skill loop: audit the *process* of how you edit skills, not just the skills themselves.

## GRASP validation gate for new skills (arXiv:2605.29668)

Before saving a new or heavily-revised skill, run an independent judge pass to prevent
regression. Without this gate, skill-writing is no better than the no-skills baseline;
with it, task completion jumps 17–40 points across tested models (gpt-oss-120b: 40.6→88.8%).

Gate pattern (delegate to `mistral-small-latest` or equivalent cheap leaf):
```
You are a skill quality judge. Rate this skill on:
1. Trigger clarity — will a future agent load this at the right time? (0-10)
2. Command accuracy — are all tool/CLI commands verified and current? (0-10)
3. Pitfall coverage — are the 3 most likely failure modes documented? (0-10)
4. Regression risk — does this contradict any existing skill or config? (0-10, 10=no risk)
Score < 7 on any dimension: reject and specify what must be fixed before saving.
```

Apply this before skill_manage(action='create') for any skill with 3+ steps, or
after skill_manage(action='edit') for major rewrites. Skip for minor patches.

## SCOPE critique for self-improvement validation (arXiv:2607.05810)

When validating whether an improvement actually improved something, use structured critique
rather than free-form assessment. Use `LLMVerifier.scope_critique_prompt(code)` from nesy.py:

```
subgoals: [what this code/skill/change must accomplish]
gap_analysis: [where current version falls short of each subgoal]
robustness_checklist: [edge cases and invariants to verify]
```

This format prevents hallucinating improvements that aren't there (39.4% vs 36.6% Reflexion on LiveCodeBench, arXiv:2607.05810).

## AlphaMemo: Search-Process Memory Patterns for Self-Evolving Agents (arXiv:2606.20625, May 2026)

Source: Hang Yu et al., Univ. of Sydney + Edinburgh. Code: github.com/jarrettyu/AlphaMemo

AlphaMemo addresses redundant discovery and overfitting in self-evolving agents. Directly
transferable patterns for Hermes skill improvement loops:

1. **AST-diff motifs**: Track which edit patterns (additions, deletions, replacements at the
   structural level) consistently improve vs. degrade skill performance. For skill patches, the
   "motif" is the type of change: adding a pitfall section, adding a numbered step, adding a
   reference — not the content. Meta-pattern: "pitfall additions reliably increase skill success rate."

2. **Confidence-gated residual memory**: Only update the skill knowledge base when confidence
   in the improvement exceeds a threshold. Below threshold: keep exploring. Above threshold:
   commit the change. Prevents low-signal improvements from polluting the skill with noise.

3. **Asymmetric veto control**: High-confidence FAILURE patterns get a veto — suppressing
   retried approaches that reliably fail. Maps directly to the `failed_trajectories` concept:
   if a skill improvement approach has failed 3+ times under similar conditions, veto it
   regardless of the current confidence. This is stricter than just noting the failure.

4. **Search-ledger prior**: Before generating a new improvement attempt, check a ledger of
   what has already been tried. Prevents re-exploring the same improvement path in a new session.
   Implement as a references/improvement-ledger.md in each skill.

**Implementation for Hermes ralph loops / self-improve-agent:**
- Log each skill patch attempt as: {motif_type, confidence, outcome} in references/patch-ledger.md
- After 3+ failed attempts with the same motif_type on the same skill, set a veto flag
- During skill-improvement planning, check the ledger before generating options

## Recursive adversarial self-audit loop (from references/recursive-adversarial-audit-pattern.md)

Loop: **Phase 1 Gather → Phase 2 Analyze → Phase 3 Fix → Phase 4 Verify → Phase 5 Recurse**
Terminates when no C/H/M severity issues remain. LOW items may carry over if they require user input.

**Five domains per pass** (missing one means it accumulates silently):
1. Memory architecture — redundancy, stale entries, surface overlap, correctness
2. Workflow efficiency — dead crons, duplicate jobs, stale assumptions
3. Token optimization — model routing, compression config, skill catalog bloat
4. Security — API key handling (.env hygiene), script permissions, CVEs, trust boundaries
5. Efficiency — disk usage, never-used skills (use_count=0 AND view_count=0)

**Context carry-forward** (CRITICAL — without it, the next pass re-diagnoses already-fixed items):
```
WHAT PRIOR PASSES ALREADY FIXED (do not re-fix):
- CRITICAL: <description> (date fixed, verification method)
- HIGH: <description>
- LOW: <description> — confirmed intentional / confirmed clean
```
Include false positives explicitly with `confirmed false positive` label.

**Severity**: CRITICAL (breaks operation/security) · HIGH (operational risk) · MEDIUM (efficiency loss) · LOW (minor hygiene)

## See also

- **references/recursive-adversarial-audit-pattern.md** — Full multi-pass recursive
  adversarial audit pattern: domain checklist (memory/workflow/token/security/efficiency),
  context carry-forward format, baseline check commands, Fable-5 invocation steps,
  and a catalogue of confirmed false positives to skip on future passes.

## Scope Limits

Self-improve is authorized to propose changes to:
- Skills in `~/.hermes/skills/` (the default profile)
- CLAUDE.md or AGENTS.md in the current project directory
- Memory entries for durable facts

Self-improve must NOT propose changes to:
- Another user's Hermes profile
- System-level Hermes config without explicit user approval
- Skills that are locked or marked as authoritative references

## Autonomous Run Staging Gate

When self-improve runs inside a cron job, ralph-loop, or subagent chain (no user present),
skill patches must be STAGED, not applied directly:

1. Write the proposed patch as a markdown file using the staging helper:
   ```bash
   ~/.hermes/scripts/stage-improvement.sh <skill-name> '<one-liner description>' <<'EOF'
   ## Proposed patch to: <skill-name>

   ### Old text (unique anchor):
   <old_string>

   ### New text:
   <new_string>

   ### Rationale:
   <why this change is correct>
   EOF
   ```
2. The file lands in `~/.hermes/cache/pending-improvements/`.
3. Do NOT call `skill_manage` directly from the autonomous loop.
4. The curator slow pass (168h) or the user reviews and applies staged proposals.

**All sessions (interactive or autonomous):** stage proposals; do not apply `skill_manage` without explicit user approval ("yes"/"apply it"/"go ahead"). Interactive presence is not approval — the user must say yes.
**Autonomous loops (cron/ralph/subagent):** staging is mandatory.

## Aug 2026: EvolveNet — Collaborative Harness Evolution (arXiv:2608.04968)

Source: https://arxiv.org/abs/2608.04968 — "EvolveNet: Collaborative Harness Evolution for Agent Self-Improvement" (Nie et al., Aug 2026)

Key insight: harness evolution (skills, memory design, tool configs) yields persistent improvements
WITHOUT updating model weights. Distributed agents evolve a shared harness locally on their own
workloads; only *adaptations* (not raw workload data) are composed into an updated shared harness.

Key findings:
- **Composition beats selection**: merging adaptations from different agents outperforms picking the best single one
- **Largest gains under heterogeneous workloads** — each agent discovers something others don't
- **Scope-typed aggregation**: tag adaptations by scope (memory, routing, tool-call, context) before merging to enable conflict detection

## Recursive Adversarial Self-Audit Loop (references/recursive-adversarial-audit-pattern.md)

Structured 5-phase loop for deep self-improvement runs. Terminates when no C/H/M issues remain.

**Five domains — audit ALL five each pass (missing one lets it accumulate silently):**
1. Memory architecture — redundancy, stale entries, surface overlap, correctness
2. Workflow efficiency — dead crons, duplicate jobs, scripts with stale assumptions
3. Token optimisation — model routing, compression config, skill catalog bloat, unused assets
4. Security — API key handling (.env hygiene), script permissions, CVEs, trust boundaries
5. Efficiency — disk usage, never-used skills (use_count=0 AND view_count=0), cold-start cost

**Phase loop:** Gather → Analyse → Fix → Verify → Recurse. Stop when CRITICAL + HIGH + MEDIUM all resolved. LOW items may carry over with explicit "confirmed intentional" or "confirmed clean" label.

**Context carry between passes (CRITICAL — without this, next pass re-diagnoses already-fixed items):**
Include in `context=` of delegate_task (not `goal=`):
```
WHAT PRIOR PASSES ALREADY FIXED (do not re-fix):
- CRITICAL: <description> (date fixed, verification method)
- HIGH: <description>
- MEDIUM: <description> — confirmed intentional / confirmed clean
```

**Severity:**
- CRITICAL: breaks agent operation, silent data loss, security exposure
- HIGH: operational risk, major waste, cron collision, dead code that misleads
- MEDIUM: efficiency loss, redundancy, stale config
- LOW: minor hygiene, unused assets, documentation gaps

**Baseline commands to run at start of each pass:**
```bash
hermes doctor
hermes cron list
bash ~/.hermes/scripts/hermes-platform-watchdog.sh
```

## Sweep 11: Reflection-Guided Self-Distillation + Contrastive Calibration Gate (MED)

### Reflection-Guided Self-Distillation
When self-improve-agent generates candidate skill updates, filter through a distillation gate:
1. Generate 2 candidate patches for each finding (one conservative, one aggressive).
2. Ask: "Which version would I choose if I had to bet on which is still correct in 30 days?"
3. Keep only the version that survives the 30-day bet. This is the distillation step.
Rationale: aggressive patches optimize for the current task; distilled patches optimize for
durable reuse — which is what skills are for.

### Self-Improving Agent Fragility — Task Order and Noise (arXiv:2608.18066, Aug 2026)

Memory-based self-improving agents are fragile in ways overlooked by optimistic prior work (SkillOpt, AWM, etc.):

1. **Noise amplification**: stacking self-improvement compounds inherent evaluation noise. Small differences in evaluation rubric → inconsistent skill promotion → skill library diverges across runs even with identical task streams. Cannot tell "did the skill improve?" from "did the noise go the right way this time?"

2. **Task-order sensitivity**: improvement quality is highly sensitive to the *order* tasks are presented. Prior works implicitly impose a hidden curriculum (easy → hard, or domain-sequential) that masks fragility. When task order is randomized, improvement often degrades or reverses.

3. **Underspecification**: vague or environment-underspecified tasks create skills that overfit to the specific evaluation context, not the underlying problem.

**Recommendations (directly applicable to Hermes skill evolution)**:
- **Multi-run reporting**: never assess a skill improvement from a single run. Require N≥3 independent runs; report mean and variance. A skill that improves 60% on one run but 20% on the next has high variance — promote cautiously.
- **Task-order stress test**: after a proposed skill improvement, test on tasks drawn in randomized order, not the order they were discovered. If performance degrades under shuffled order, the improvement is curriculum-dependent.
- **Rubric injection into memory construction**: when writing a skill or memory entry, include the evaluation rubric it was validated against as a comment. This prevents future runs from validating the same skill against an inconsistent rubric.

Reference: arXiv:2608.18066, "On the Fragility of Self-Improving Agents: Variance, Task Order, and Underspecification", Aug 2026.

---

## EvoTS-Agent — 3-Operator Trajectory Evolution (arXiv:2608.17933, Aug 2026)

Three-operator trajectory evolution framework: all operators gate on **validation feedback** before accepting evolution:

- **Revision** (exploit): refine the current best trajectory — small targeted improvements when performance is high
- **Alternative Strategy** (explore): generate a new trajectory direction when current approach is stagnant (performance plateau detected)
- **Recombination** (synthesize): merge complementary high-performing trajectories — useful when two approaches each solve different failure modes

**Selection rule**: choose operator based on trajectory performance history. If last N runs show plateau → Alternative. If two distinct high-performing trajectories exist → Recombination. Otherwise → Revision.

**100% execution success rate** across all backbone LLMs tested — the validation gate prevents accepting trajectories that fail to execute.

**Hermes translation**: when iterating on a skill through multiple patches:
- Track which sections were changed and what validation showed improvement
- If 2+ patches in a row haven't moved the metric → switch from Revision to Alternative Strategy (try a fundamentally different section structure)
- If two prior skill variants each solved different failure modes → Recombination (write a combined section that incorporates both mechanisms)

Reference: arXiv:2608.17933, "EvoTS-Agent: A Self-Evolving LLM Agent for Financial Time Series Change Point Detection", Aug 2026.

---

## TMI — Hierarchical Task Model Induction from Execution Traces (arXiv:2608.20319, Sweep 20) <!-- why: unconstrained traces contain recoverable latent task structure; induction outperforms retrospective prose summarisation -->

Task Model Induction recovers interleaved tasks from unconstrained traces with 0.974 agreement, producing hierarchical objective models (recursive goal decomposition) + procedure models (control flow). Applied to agent self-improvement:

After a completed multi-step task, run TMI-style induction on the session trace:
1. Discover latent tasks: group tool calls by semantic continuity — a topic shift in consecutive calls signals a task boundary
2. For each discovered task group: produce an objective model (what was the goal?) and a procedure model (what was the execution order?)
3. Compare the induced model against any skill that claims to cover this task type
4. If the induced procedure diverges from the skill's steps in 2+ places: the skill is stale — patch it
5. If no skill covers the induced task: it is a candidate for a new SKILL.md (apply the ≥3-session threshold before creating)

This formalises the self-improvement loop: trace → induce → compare → patch or create. The induction step is the gap that "look back at what I did" misses — it recovers structure from interleaved activity, not just chronological replay.

 (arXiv:2608.17684) <!-- why: prevents capability gains from silently expanding attack surface and unauthorized state changes -->

Empirical audit of SkillOpt, AWM, and ReasoningBank: self-evolution raises benign utility BUT simultaneously increases attack-surface contact and unauthorized state changes, even when per-attack conditional success rate drops. Post-evolution accuracy alone is insufficient to declare an evolution safe.

**Four audit dimensions required after any skill/memory self-evolution pass:**

1. **Regression check** — does evolved agent still succeed on tasks it solved before evolution? (run sealed evaluation endpoints, not live endpoints)
2. **Attack-surface contact** — did exposure to injected/adversarial content rise? (track separately from conditional attack success rate)
3. **Unauthorized state changes** — did the agent perform any state mutations beyond task scope? (execution-grounded check, not just output check)
4. **Artifact-executor compatibility** — if the evolved skill includes a tool-call envelope or action format from a different executor (e.g. WebArena text-action format), verify it doesn't break native function calling. The AWM finding: removing a literal text-action envelope restored utility from 0.319 to 0.756.

**Key insight:** Conditional ASR can drop while overall ASR rises (more attack-surface contact compensates). Do not use conditional ASR as the sole security signal.

**Hermes implementation:** After any autonomous skill patch applied in a loop:
- Run a held-out task set before AND after the patch (sealed)
- Check Hindsight for any writes that occurred during the evolution that weren't explicitly intended
- Compare `enabled_toolsets` scope before and after — evolution should never widen toolset scope automatically
- Log evolution event to `~/.hermes/skill-failures/<name>.jsonl` with `evolution_type` field

## On-Policy Skill Repair: Localize Before Rewriting (arXiv:2609.09134) ★ HIGH

When a skill causes a task failure, **do not rewrite the whole skill**. Imitation of expert full-trajectories backfires (4–30pp regression across 7 tasks): the agent adopts the expert's planning strategy without the competence to execute it, breaking model–harness fit.

**On-policy correction rule:** Localize the exact failing section (trigger condition, step, or pitfall that was active during failure) then rewrite **only that section**. Keep all other sections intact.

**Hermes apply:**
1. When a skill step caused failure: identify which step was active via session trace or Reflexion `what_failed`.
2. Patch only the matching section — use `patch(old_string=..., new_string=...)`, never `write_file` on a skill that failed a single section.
3. If 2+ sections contributed to failure: patch them independently rather than rewriting the skill body.
4. Validate with EDD on the failing task type only before broadening to other task types.

**Falsification gate:** Does the patch change behavior for OLD scenarios where the skill worked? If yes, require explicit justification. If no, proceed. (Same as Contrastive Calibration Gate below.)

Source: arXiv:2609.09134, "Co-Evolving Harnesses and Models: On-Policy Correction Helps Weaker Models Catch Up Where Imitation Fails", Sep 2026.

## Harness Self-Evolution Feasibility Bounds (arXiv:2609.08175)
Promotion is safe iff BOTH conditions hold:
1. n_eval >= ceil(log(2/delta) / epsilon^2) historical task evaluations exist (PAC bound; use delta=0.05, epsilon=0.1 -> n_min=738 tasks, or delta=0.2, epsilon=0.2 -> n_min=100 tasks for faster iteration)
2. E[R(h')] - E[R(h)] > 0 on the held-out eval set (positive expected improvement)
Contraction limit: repeated harness updates converge to a fixed point if the update operator is a contraction (||T(h1)-T(h2)|| < k||h1-h2|| for k<1). If performance plateaus across 3+ update cycles, the system has likely reached its fixed point — stop updating and investigate the reward signal instead.
WARNING: The paper proves that self-evolution CANNOT escape the expressivity limits of the frozen underlying model. Skill additions that require the model to perform tasks it cannot do will not improve with more iterations.

## AutoSaddler — Offline Harness Optimization from Failure Traces (arXiv:2608.23041) ★ HIGH <!-- why: durable harness gains come from offline failure diagnosis + validation-gated patches, not online thrash -->

AutoSaddler treats harness improvement as an **offline learning** problem: mini-batch failure
traces → structured diagnosis → code-like harness patches → **validation-based** accept/reject.
Gains on GAIA2 / SWE-Bench Pro / Terminal-Bench 2.0 came from durable harness updates, not
weight updates.

**Hermes mapping (self-improve + skill/scripts):**
1. **Collect failure traces** only (success-only feedback is weak — RethinkSkill). Prefer
   `failed_trajectories`, purge/staleness logs, and sessions with explicit user corrections.
2. **Diagnose offline** after the run (not mid-task): root cause = harness gap (skill step,
   toolset, config threshold, memory gate) vs model failure.
3. **Emit structured patches** (skill section / script constant / config key) with a single
   clear acceptance metric.
4. **Validate before promote**: old vs new on ≥3 held-out tasks or a sealed checklist.
   Reject if validation improves but downstream task score does not.
   **HarnessEvolve Performance Gate (arXiv:2609.00829):** Additionally, require that the update does not degrade performance on the last 3 skill evaluation cycles (not just the current batch). Epoch-end validation selects the best-accepted snapshot — do not promote the most recent change; promote the best across all accepted candidates so far.
5. **Batch**: accumulate ≥3 related failures before a harness change (matches RethinkSkill
   sparsity — most single-shot evolutions are noise).

Do not run AutoSaddler-style loops inside the same autonomous session that is still executing
the user task. Stage via `stage-improvement.sh` when no human is present.

## Gated RSI Pattern (s28-recuris-rsi, human-gate required)

Working memory (`working-memory.py`) is already adopted from Recuris. Recursive
self-improvement is the risky remainder: never autonomously mutate skills.

After AutoSaddler finds a skill with 3+ failures on similar tasks:
1. Generate a **proposed** skill rewrite only (diff + rationale). Do not apply it.
2. Present the full diff and rationale to the user.
3. Apply **only** if the user explicitly approves. Do not auto-apply. Do not treat
   silence, staging, or cron as approval.
4. Log every proposal and decision in `/var/home/rainbow/.hermes/cache/rsi-proposals.json`
   (`proposed` / `accepted` / `rejected`, skill name, failure count, timestamp).
5. Cross-link to the ANNEAL failure pipeline in this skill: harvest failures first,
   then propose; ANNEAL still owns failure-to-knowledge, RSI only proposes the rewrite.

## Contrastive Calibration Gate
Before committing a self-improve patch:
1. Find a past session where the OLD skill behavior produced a correct result.
2. Check: does the proposed patch change behavior for that old case?
3. If yes → require explicit justification for the regression.
4. If no → proceed.
This prevents a common failure mode: optimizing a skill for the most recent task at the
cost of correctness on earlier tasks (skill overfit).

**When to apply:** any skill_manage patch that changes steps, trigger, or removes pitfalls.
Skip for: adding a new section without modifying existing ones.

---

## Trace2Skill / ARISE crystallization

Do not promote a candidate from this section alone. Load `runtime-skill-synthesis` and run
its pipeline (harvest → crystallize check → SkillAlchemy admit → EvoAgent fail-log → merge
audit → Pass^k). This section is only the post-task trigger.

> **Evo-Harness cross-domain filter (arXiv:2608.15071, EMNLP 2026):** When synthesizing a new skill from a completed task, apply the Evo-Harness cross-domain filter (see `runtime-skill-synthesis` skill § Evo-Harness) before writing any lesson to the harness. Keep only insights that apply to 2+ different task types; discard task-specific artifacts (file paths, user names, one-off configs). Single-task artifacts degrade skill quality by polluting routing signals and causing misfires on future tasks where those specifics differ.

After any complex task (5+ tool calls, novel workflow, errors overcome), if no existing
skill already covers the procedure:

```
python3 ~/.hermes/scripts/trace2skill.py SESSION_ID
```

Where SESSION_ID is the current session (visible in `hermes session list` or state.db).
This writes a candidate SKILL.md to `~/.hermes/cache/pending-improvements/` — **staging,
not admission**.

**When to trigger harvest:**
- Task required non-trivial tool sequencing not covered by an existing skill
- Errors were overcome in the trace (pitfalls worth capturing)
- A novel multi-step workflow was discovered

**Admission (required before create):** SkillAlchemy checklist in `runtime-skill-synthesis`
step 3 — 2+ traces, one implicit-requirement pitfall, overlap classify, `trust_level:
experimental`. Single-trace candidates stay staged.

**Failure traces (EvoAgent):** if a loaded skill failed, log first to
`~/.hermes/skill-failures/<name>.jsonl`, pair with the latest success, patch only the
contrastive delta. Autonomous loops still use `stage-improvement.sh` — do not treat
"log the failure" as permission to skip the human/staging gate.

**Review cadence:** weekly `omni-skill-quality-scan` plus `runtime-skill-synthesis` monthly
refinement. Never `skill_manage create` from cron on a raw candidate.

**Merge gate (two-trajectory validation):** if two sessions solved the same problem,
`python3 ~/.hermes/scripts/trace2skill.py --merge FILE1 FILE2`. Shared steps = universal;
unique steps = conditionals. Overlapping *live* skills use synthesis step 5 (not this
intersection helper).


---

## Sweep 21: Self-Evolving Agent Failure Modes

### Capability Degradation (GS013: arXiv:2605.09315) ★ HIGH
Self-evolving agents that adapt to new tasks can silently degrade previously acquired capabilities
across workflow, skill, and memory components. This is a systematic failure mode, not rare.

Preservation strategies:
- **Selective update masking**: isolate patches to the skill section that addresses the new task;
  do not rewrite adjacent sections unless they conflict
- **Regression-tested harness commits**: after patching a skill, check that prior known-good
  trigger scenarios still resolve to correct behaviors before committing

**Hermes rule:** when patching a skill for a new task pattern, explicitly verify:
"Does this patch change behavior for the OLD trigger scenarios?" If yes → document the
intended regression or restore backward compatibility.

### Textual Backpropagation for Multi-Agent Self-Improvement (GS006: ACL Findings 2026) ★ MED
Agentic Neural Network (ANN) model: multi-agent pipelines as differentiable networks optimized
via textual backpropagation. Enables end-to-end self-improvement without gradient computation.

**Hermes pattern:** after a multi-agent pipeline run (e.g. parallel subagent dispatch + synthesis),
the consolidation step is the equivalent of backward pass — explicitly identify which subagent's
output caused poor synthesis results and patch that subagent's task specification.
This closes the textual gradient loop: task spec → output quality → patch task spec.


## APEx — Trajectory-to-Category Distillation + Planner Loop (arXiv:2609.02253, Sweep 31) ★ HIGH

APEx (Agentic Pattern Extraction) empirically shows that single-shot skill induction from one
trajectory is unreliable. Reliable skill promotion requires distillation across a task *category*
(not a single instance) via a 4-phase planner loop.

**Core contribution: trajectory-to-category distillation**
1. **Cluster** — after 3+ successful trajectories of the same task type (by slug/class),
   cluster them and identify the *common* tool-call sequence skeleton across instances.
2. **Extract** — the common skeleton becomes the candidate skill body. Steps unique to one
   trajectory are demoted to pitfall notes or optional branches, not core steps.
3. **Validate** — run the extracted skill on a held-out trajectory (one it wasn't trained on).
   If it reproduces the key tool-call sequence: admit. If it diverges on ≥2 steps: reject.
4. **Annotate** — attach the task-category label and the 3+ source trajectory IDs to the
   skill YAML so future evolution audits can verify the evidence base.

**Planner loop (4-phase, not single-shot):**
- Phase 1 — Plan: outline the task decomposition before executing any tool calls.
- Phase 2 — Execute: run tool calls as planned.
- Phase 3 — Evaluate: compare actual outputs against plan expectations explicitly.
- Phase 4 — Refine: if evaluation shows divergence, return to Phase 1 with updated plan before re-executing.

Key difference from Reflexion: APEx refines the *plan* (task decomposition), not just
the *skill text*. Reflexion patches what to do; APEx patches how to decompose.

**Hermes integration:**
- The existing `≥3 sessions` threshold for skill admission is consistent with APEx.
  Extend it: the 3 sessions must be categorized under the same task slug.
- When logging to `~/.hermes/skill-failures/<name>.jsonl`, add `trajectory_cluster: <slug>`
  field so APEx-style clustering can be done offline.
- Before any cron-driven skill promotion (staged or interactive), verify a minimum of 3
  cluster members exist in the trajectory log with `trajectory_cluster == target_slug`.
- The planner loop applies to complex multi-tool tasks (>5 steps): always plan before executing,
  evaluate mid-task at natural checkpoints, and refine before the final synthesis step.

<!-- why: single-trajectory skill induction is high-variance; category distillation from 3+ instances produces transferable procedural rules rather than context-specific heuristics -->

## Sweep 29: Pre-Task and Post-Task Hooks (Aug 2026)

### PRE-TASK (run at start of every improvement loop iteration)
```bash
# 1. Pull relevant failure critiques (CritICL, arXiv:2608.27455)
python3 ~/.hermes/scripts/critique-bank.py inject --query "<task goal>" --top 3

# 2. Check for analogous prior plans (Synapse, ACL 2026)
python3 ~/.hermes/scripts/working-memory.py plan-from-memory \
  --session $SESSION --task-summary "<task goal>"
```

### MID-TASK (for loops >10 steps — SKILL.state, arXiv:2608.26263)
```bash
python3 ~/.hermes/scripts/skill-state.py step \
  --session $SESSION --skill SKILL_NAME --observation "<milestone result>"
```

### POST-TASK (on completion or partial failure)
```bash
# If novel insight discovered:
python3 ~/.hermes/scripts/skill-wiki.py upsert \
  --skill SKILL_NAME --section results --text "<insight>"

# If failure occurred — am-sentry auto-writes to critique-bank on HIGH flags,
# but also write manually for recoverable failures:
python3 ~/.hermes/scripts/critique-bank.py add \
  --session $SESSION --failure-mode <mode> --critique "<what went wrong>"
```

### HANDOFF (model switch or session end)
```bash
python3 ~/.hermes/scripts/working-memory.py handoff-export --session $SESSION
# Output includes skill-state init hint for the receiver
```
