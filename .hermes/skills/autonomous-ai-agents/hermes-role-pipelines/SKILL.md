---
name: hermes-role-pipelines
related_skills:
  - autonomous-ai-agents
  - dispatching-parallel-agents
  - hermes-acp-routing
  - subagent-driven-development
  - hermes-swarm-consensus
  - trajectory-risk-guardrail
  - autonomous-agent-loop-design
  - complexity-gated-planning
  - hermes-context-packet
  - hermes-semantic-skill-routing
triggers:
  - Designing a multi-agent role pipeline (analyst → designer → implementer → reviewer)
  - Need to choose between serial delegate_task waves and parallel fan-out patterns
  - Mapping a team or squad structure onto Hermes delegate_task
  - Running analyze → design → implement → verify phases as a pipeline
  - Need Tree-of-Thought candidate-plan beam before mutating execution
  - Need a critique-before-commit gate separate from the executor
  - Need AutoGen-style speaker selection (who talks next) during a multi-agent run
  - Need task decomposition via conversation rather than a frozen DAG
description: >
  Use when: Multi-agent role pipeline patterns adapted from the opencode-hermes-multiagent role catalog for Hermes delegate_task.
version: 2.3.0
author: Hermes
---

# Hermes Role Pipelines

Use this when a task benefits from explicit specialist roles rather than a single worker.

If the task is only broadly about autonomous/multi-agent orchestration and the right specialist workflow is not yet obvious, load `autonomous-ai-agents` first, then route here when the concrete need is role and pattern selection.

**See also**: `references/audit-delegation-pattern.md` for large-scale audits; `references/plan-beam-and-critique-gate.md` for ToT-lite plan selection and the critique-before-commit gate; `references/autogen-toolformer-patterns.md` for AutoGen speaker selection, conversation-driven decomposition, and Toolformer tool-gating.

Installed source catalog:
- `/var/home/rainbow/.hermes/integrations/opencode-hermes-multiagent/agent/subagents/`

## Task intake classifier (run before choosing a pattern)

Before selecting a pipeline shape or spawning any agents, classify the incoming task:

| Class | Criteria | Recommended dispatch |
|---|---|---|
| **simple** | Single-step, no branching, no parallel, no durability needed | Direct tool call or single session; no delegation |
| **multi-step/short-lived** | Sequential but bounded, finishes in one session, no retry/replan needed | `delegate_task` pipeline or supervisor; parent stays in session |
| **durable/background** | Must outlive the current session, needs retries, or runs on schedule | Kanban task + gateway, or cron job with `notify_on_complete` |
| **requires-human-input** | Missing context only the user can provide, approval gate needed | Pause and ask; never synthesize from weak signals |
| **requires-MCP** | Needs an external integration (browser automation, external API, workflow approval) not expressible as a single tool call | Fan-out with tool-scoped agent; scope toolsets precisely; see Tool Scoping Discipline |

Apply this classifier before choosing a pattern. The most common mistake is treating a `durable` task as `multi-step/short-lived` — the delegate_task result returns to the parent but the actual work outlasts the session, losing progress.

**Putrid_Assistant_557 layer model** (from r/hermesagent orchestration thread, Jul 2026):
A clean decomposition for any orchestration system built on Hermes:
- **Hermes** = user-facing agent, intent interpreter, tool caller
- **Skill** = teaches Hermes when to escalate from normal tool use into a workflow
- **MCP** = integration boundary (external tools, approvals, artifacts, workflow state)
- **Workflow runtime** = owns state, retries, approvals, review loops, artifacts, resumability

In practice for this stack: Hermes + `delegate_task` covers the first two. Kanban + gateway covers the workflow runtime. MCP tools cover the integration boundary. Don't collapse these layers — the most common failure is having Hermes own state and retries directly, which becomes brittle on real long-running jobs.

## Depth constraint (read before planning)

`delegation.max_spawn_depth` is currently **1**: only parent → direct leaf children.
Grandchild spawning (orchestrator subagents spawning their own subagents) is blocked
at runtime. Do NOT plan pipelines that assume >1 level of nesting unless you have
first confirmed max_spawn_depth has been raised.

Workaround for deep pipelines: use serial parent-orchestrated waves. The parent
fans out to a batch of leaves, waits, synthesises, then fans out a second batch.
This achieves multi-stage parallelism within the depth-1 constraint.

To raise the limit (both values must be changed together):
  - config.yaml: delegation.max_spawn_depth
  - budget-policy.yaml: hard_limits.delegation_depth

## Recommended Hermes mapping

Research:
- finder -> fast file scout
- analyst -> dependency/risk analysis
- researcher -> external docs

Audit / Review:
- auditor -> systematic assessment across a domain (config, security, architecture, performance)
  - Produces structured findings, severity ratings, and actionable recommendations
  - Often runs as a single expert-level agent (opus-4-8) due to complexity synthesis needs
    (as of 2026-07-08 this is also the standing default for the orchestrator role in
    orchestration workflows more generally — see `claude-routing-hierarchy`'s
    "Orchestrator model selection" section)
  - Output shape: JSON report with findings, config diffs, and priority matrix
  - Follow-up: orchestrator parses report and fans out implementation subagents by area

Planning:
- architect -> solution shape
- planner -> task decomposition

Implementation:
- coder -> new code
- editor -> safe edits
- fixer -> bug fix
- refactorer -> structure cleanup

Quality:
- reviewer -> review findings
- tester -> focused tests
- security -> auth/secrets/data review
- debugger -> root cause analysis

Infrastructure:
- devops -> CI/CD, containers, deployment
- optimizer -> performance

## Architecture patterns adapted from Harness

Harness adds a useful layer above role names: choose the collaboration shape first, then assign roles.
In Hermes, adapt the six patterns like this:

1. Pipeline
- Use when later work depends strongly on earlier outputs.
- Hermes shape: serial `delegate_task` waves or parent-led phases.
- Good fits: analyze -> design -> implement -> verify.

2. Fan-out / Fan-in
- Use when several independent investigations can run in parallel and then be merged.
- Hermes shape: one `delegate_task(tasks=[...])` batch for discovery, then a parent synthesis pass, then one implementation worker.
- Good fits: code review across security/perf/architecture; multi-source research; cross-surface bug triage.

3. Expert pool
- Use when only some specialties are needed depending on what is found.
- Hermes shape: parent routes narrowly scoped one-off tasks to the right role instead of spawning a standing team.
- Good fits: call security only if auth/tokens appear; call devops only if CI/container paths are touched.

4. Producer-Reviewer
- Use when one worker should create and a separate worker should critique.
- Hermes shape: implementer child -> reviewer child -> parent verification.
- Good fits: code generation, documentation, migration plans.

5. Supervisor
- Use when the parent must dynamically assign work as findings arrive.
- Hermes shape: parent stays active, updates todo state, dispatches narrow workers in waves.
- Good fits: large refactors, multi-file migrations, staged debugging.

6. Hierarchical delegation
- Harness supports this conceptually, but Hermes has max spawn depth 1 for this user.
- Hermes adaptation: flatten into parent-orchestrated waves; do not expect child agents to spawn grandchildren.
- Good fits: convert would-be trees into pipeline or supervisor patterns.

7. Speaker-selected group (AutoGen GroupChat)
- Use when the next specialist depends on the last artifact and a frozen pipeline would idle unused roles.
- Hermes shape: parent is GroupChatManager (depth-1). Each turn: role-play select ONE speaker → one `delegate_task` → keep transcript on parent → next speaker gets a compact packet, not a broadcast.
- Do not confuse with `hermes-swarm-consensus` (post-fan-out verdict reduction, not turn-taking).
- Full procedure: `references/autogen-toolformer-patterns.md`.

8. Conversation-driven decomposition (AutoGen nested chat)
- Use when the task DAG is not knowable until agents talk; partition through dialogue, then re-open after each node.
- Hermes shape: provisional 2–5 node DAG; after each completed node keep/split/drop remaining nodes. Nested AutoGen chats flatten to serial parent waves with a new context packet and a fresh `enabled_toolsets` — children still cannot spawn children.
- Pass artifacts via `prior_findings_refs`, never inner transcripts.

## Pattern chooser

Prefer:
- Fan-out / Fan-in for independent read-only discovery
- Producer-Reviewer for non-trivial code changes
- Supervisor for dynamic multi-batch work (new work items from a backlog)
- Speaker-selected group when later speakers need prior artifacts *and* who speaks next is state-dependent
- Conversation-driven decomposition when the DAG cannot be frozen before the first leaf returns
- Pipeline when outputs are naturally sequential and order is known up front
- Expert pool when most specialists are conditional *and* you will skip GroupChat (one-shot dispatch)
- Plan-beam (ToT-lite) when ≥2 plausible approaches exist, *before* any mutating wave — see Plan-then-Execute below

Avoid planning for hierarchical delegation here unless the runtime nesting limit changes.
Avoid GroupChat for independent discovery (use fan-out) and avoid broadcasting sibling reasoning if the next step is a consensus vote.

## Example pipelines

Bug fix, unknown cause:
- Pattern: Fan-out / Fan-in -> Producer-Reviewer
1. finder
2. debugger
3. fixer
4. reviewer
5. tester

Feature with security impact:
- Pattern: Pipeline with expert-pool branches
1. finder
2. analyst
3. researcher
4. architect
5. planner
6. coder
7. reviewer
8. security
9. tester

Large migration with changing hotspots:
- Pattern: Supervisor
1. architect
2. planner
3. editor/refactorer wave 1
4. reviewer
5. editor/refactorer wave 2 if needed
6. tester

## Hermes execution pattern

Use parallel delegation for independent discovery, then a second wave for implementation and review.
Keep each subtask self-contained and pass compact context packets only.
Choose the architecture pattern before choosing the role names.

### Eliminating the synthesise-then-implement rework cycle

When fan-out agents produce changes that must be merged (not just read), load
`hermes-agent-sync` and use the Structured Findings Contract. Agents write typed
JSON action payloads (patch / file_append / config_set / git_commit / observation)
to `~/.hermes/agent-workspace/*.finding.json`. The parent runs
`apply-findings.py` once — no manual synthesis, idempotent re-runs safe.

Load `hermes-agent-sync` whenever:
- 2+ parallel agents touch the same files/config
- You want deterministic merge rather than prose synthesis
- You need reliable idempotency (re-dispatch safety)

When converting these collaboration shapes into reusable workflow generators or Seed scaffolds, use `references/workflow-family-seed-mapping.md` for the canonical five-family taxonomy, normalized seed styles, default-to-pipeline rule, and verification expectations.

## Evaluator-Optimizer Pattern

When output quality matters, use a separate evaluator pass:

1. Worker produces output.
2. Evaluator (or parent) scores it against explicit criteria set before the first call.
3. If criteria not met, refine with feedback. Max 2–3 rounds; escalate if still failing.

In Hermes: Producer-Reviewer shape (worker child → reviewer child → parent verify),
or parent calls worker then re-dispatches with critique appended inline.

When to use: non-trivial code generation, documentation, migration plans, any output
used downstream without further human review.

Evaluator-Optimizer and Producer-Reviewer critique *after* a worker has already produced.
They do not select among plans before side effects, and they do not block commit if the
parent just appends critique inline. Use Plan-then-Execute when those two gaps matter.

## Plan-then-Execute + Critique-before-Commit (ToT-lite)

Hermes default is pick-one-shape-then-run. That skips Tree-of-Thought beam search
(maintain N candidate plans, prune with a critic) and treats execution and critique as
the same loop. Skip Plan-then-Execute unless: 2+ divergent approaches exist OR HAZARD flag is set. Critique-before-commit applies only to: merging branches, pushing to main, promoting skill trust_level, or publishing.

**Skip when:** complexity-gated-planning Level 0–1 with no HAZARD step; single obvious
reversible approach; read-only research; ordinary local edits. Full procedure: `references/plan-beam-and-critique-gate.md`.

1. **Plan beam (before any mutating tool).** Planner child, `toolsets=['file']`, emits
   N=2 (N=3 only if blast radius actually differs) candidate plans. Each plan lists
   phases, which phases mutate, irreversible steps, and named conditional edges:
   `on_fail` and `on_ambiguous` per phase (`retry-same` | `replan` | `branch` |
   `ask-human` | `accept-partial` — same vocabulary as Review loop branching).
   A plan without those edges is incomplete; do not execute it.
2. **Critic prunes the beam.** Separate child, *fresh* context (objective + the N plan
   objects, no planner chain-of-thought). Returns one winner. Planner must not grade
   its own beam. Tie → `trajectory-risk-guardrail` on both; still tied + THIRD_PARTY/
   SYSTEMIC blast → `ask-human`. This is planning-before-execution.
3. **Execute the winner as parent-orchestrated waves** (depth-1). After each phase:
   write the existing stage checkpoint, run a cheap BATON-style verifier (`done_when`
   artifact exists). Verifier fail fires `on_fail` (cap `retry-same` at 2, then replan
   *this phase*). Ambiguous output fires `on_ambiguous` (`branch` = two interpretations
   then `hermes-swarm-consensus` before the next phase). Do not start phase N+1 on a
   failed verifier.
4. **Critique-before-commit (blocking, narrow).** After the last implementation wave, apply this gate only when merging branches, pushing to main, promoting skill `trust_level`, or publishing. Critic child with original
   objective + done-criteria + artifact paths, *no executor transcript*, read-only
   toolsets. Returns `pass` | `fail` | `ambiguous` — not a rewrite. Commit only on
   `pass`. Executor self-grade is banned (Verification-Gated Escalation). Ordinary local edits do not need this gate.

Do **not** implement MCTS plan-selection here (rollout children before execute). Depth-1
plus cost make it a non-fit; skill-variant MCTS is `skillopt-continuous-improvement`.
Canvas-of-Thought (`autonomous-agent-loop-design`) is in-session named state, not a plan beam.

Cost cap: Phase 0 + critic ≤ 2 extra children. If the beam would cost more than one
implementation wave, skip the beam and keep only step 4 (critique-before-commit).

## Tool Scoping Discipline

Giving an agent too many tools degrades performance. Every `delegate_task` call
MUST set `toolsets` to only what that subagent actually needs:

- Pure read/analysis: `['file']`
- Code fix: `['terminal', 'file']`
- Research: `['web']` or `['web', 'file']`
- DOM interaction: add `'browser'` only if needed (not just extraction)

Before each fan-out: list tools per subagent explicitly.

**Toolformer gate (tools ≠ skills):** `hermes-semantic-skill-routing` selects skills by predicted utility. `enabled_toolsets` still loads every tool in a toolset. Approximate Toolformer's keep-if-loss-drops filter without logprobs: add a toolset only if the speaker's `output_contract` requires evidence that tool produces *and* that evidence is not already in `prior_findings_refs` / `current_state`. Escalate one toolset on self-check fail; do not preload the union. Inner GroupChat waves do not inherit the outer wave's toolset. Never put `delegation` on a GroupChat leaf. Details: `references/autogen-toolformer-patterns.md`.

## Per-Subagent Model Tiering (bidirectional cascade)

Apply the escalation/de-escalation decision at the **subagent level in the prompt**,
not by assuming a per-task model field. `delegate_task` has **no** `tasks[].model`.
Every child uses `delegation.model` (`mistral-small-latest` as of 2026-08-25). A
fan-out batch is rarely uniform difficulty — keep hard synthesis on the parent
(Grok) and mechanical work on the cheap leaf default. Do not write `model:` on
a task dict; it is ignored.

**Honesty caveat**: this cannot be a live calibrated-confidence router like UCCI
(arXiv:2605.18796) — that method needs per-token logprob margins, which the Claude API
doesn't expose in normal tool-calling use. The trigger here is an a-priori classification
by role/task-type decided before dispatch, not a runtime uncertainty score. Don't claim
more precision than that.

**Downward — cheap tier for mechanical leaf work:**
- Trigger: file listing/formatting, simple extraction, boilerplate, single-fact lookup,
  high-volume near-identical fan-out items (N similar small subtasks).
- Live default: `mistral-small-latest` via `delegation.model` (already the child model).
  Do not override Haiku/glm for this — glm is archived; Haiku is override-only.
- Cross-family leaf output can still break a Grok synthesizer (MAS-PromptBench). Prefer
  structural verification of leaf output before synthesis.

**Upward — escalate a specific role, not the batch:**
Same discipline as the top-level gate in `claude-routing-hierarchy`, scoped to one
subagent's role: escalate to Opus when that role is the arbiter/reconciler over
conflicting sibling outputs, a security/architecture signoff, or the one genuinely hard
chunk in an otherwise easy expert-pool batch. Escalate Opus→Fable only per that same
skill's stricter second gate. Never escalate a leaf role just because its sibling tasks
in the same batch are hard — evaluate each role independently.

**Verification requirement**: per MAS-PromptBench (already noted above), changing one
subagent's model tier can cause system-level degradation even when that subagent's own
output looks fine — always check the pipeline's final output quality after retiering a
role, not just that role's isolated output.

## BATON-style Role-Model Pairing (arXiv:2608.16889)

BATON ("Don't Drop the BATON") treats each subtask as the unit of exploration and stamps
handoffs with transition-aware verifiers. Role-specific model pairing is a planning hint
for that chain — not a live `delegate_task` field.

Preferred tiers (document in the role's goal; do not assume they bind):
- orchestrator / critic: parent session model (claude-sonnet-4-6 or Grok intensive)
- implementer / mechanical leaf: `delegation.model` (`grok-4.6` here; cheap default)
- reviewer / adversarial: cross-family judge when cost is justified (see Verification-Gated Escalation)

**Config:** there is no `delegation.model_per_role` today. Forward-only key if the runtime
ever grows it: `delegation.role_model_map`. Do **not** add that key to `config.yaml` until
the schema reads it. `delegate_task` has **no** `tasks[].model`; a `model` field on a task
dict or in the context packet is ignored by the runtime. All children use `delegation.model`.

**Current support:** pair roles only by *who runs them* — keep hard synthesis on the parent,
mechanical work on the leaf default, escalate one role via a dedicated session/cron pin.
Handoff stamps stay the existing 4-field schema + BATON `done_when` verifier.

**Role-drift:** runtime role drift is expected (RSM). Re-anchor at stage checkpoints. When
parallel roles write conflicting findings, load `hermes-agent-sync` (Structured Findings
Contract / `apply-findings.py`) instead of prose-merging drifted role output.

Assigned sweep ID `2504.09714` is a different paper (Turkish benchmark quality). Cite BATON as `2608.16889`.

## Verification-Gated Escalation (post-hoc, not pre-hoc confidence)

The a-priori tiering above decides where a task *starts*. It has no feedback loop — a
cheap-tier subagent can be confidently wrong with nothing to catch it. Add a verification
gate before accepting a cheap-tier subagent's output, using structural or independent
checks — never the generating model's own self-reported confidence.

**Why self-confidence is banned as a signal (live-verified, not theoretical):**
A cascade benchmark (dennisonbertram/llm-model-routing-benchmark, live-verified 2026-06-21)
tested a cheap model rating its own answer 0–1 (FrugalGPT-style self-confidence gate). The
cheap model returned confidence 0.9 on ALL SIX wrong hard-math answers; sweeping the
threshold 0.1–0.9 produced identical results (accuracy == always-cheap baseline, cost 2.4x
higher for zero gain). Verbalized/self-reported confidence is the same failure mode as raw
logprob confidence — overconfident-and-wrong is exactly the case that needs escalation, and
self-report cannot discriminate it. Do not implement a "have the subagent state its
confidence" gate; it has been tested and does not work.

**What does work, in order of preference:**
1. **Structural verification** (best): run the actual check — unit tests, schema
   validation, lint/typecheck, a deterministic parser confirming required fields are
   present. Escalate to Opus only on structural failure. Live-verified result on coding
   tasks: 100% accuracy, 1/18 unnecessary escalations, 0 false accepts. Use this whenever
   the subagent's output is checkable by a non-LLM process.
2. **Independent judge model** (when no structural check exists): a *separate* call —
   different context, evaluating the output strictly against the task's stated
   done-criteria (pass/fail/ambiguous), not asking the generator to grade itself. The
   verifier must be more reliable than the generator (FrugalGPT's own constraint) —
   self-grading violates this by construction; a fresh independent call does not.

   **Same-family judge caveat**: a same-model-family judge (e.g. claude-haiku-4-5 judging
   claude-sonnet-4-6 output) is a weaker independent check than it looks. Wataoka et al.
   (NeurIPS 2024 Safe GenAI workshop, arXiv:2410.21819) show LLM judges exhibit measurable
   self-preference bias, and the mechanism is perplexity-based: judges score
   lower-perplexity ("more familiar-sounding") outputs higher regardless of who generated
   them — and outputs are lowest-perplexity to judges from their own family. A same-family
   judge is more likely to wave through same-family-flavored wrongness than a genuinely
   cross-family one would. Where the cost is justified (see `claude-routing-hierarchy`'s
   OpenAI section for the wired `custom:openai` provider and its live pricing/pitfalls),
   prefer a cross-family judge for the escalation gate specifically — e.g. gpt-5.4-nano or
   gpt-4.1-nano judging Claude-generated output, or vice versa — over a same-family
   haiku-tier judge. This is a targeted use of the second provider for the verifier role
   only; it is not an argument for adding GPT to default/fallback routing (that question is
   answered separately, and negatively, in `claude-routing-hierarchy`).
3. **Self-verify resampling (k=3, same model)** — usable but costly: matched strong-model
   accuracy at 71.6% savings in benchmarks, but verifier overhead alone ran 2.85x the
   theoretical oracle cost. Only worth it when escalation is rare and a judge call isn't
   available; prefer option 2 over this for most cases in this stack.

**Escalation trigger**: escalate cheap-tier → parent Grok (4.5, or 4.6 if intensive),
matching `claude-routing-hierarchy`. Do not escalate to `claude-sonnet-4-6` as if it
were still the mid rung. On structural-check failure or judge "fail"/"ambiguous"
verdict. Do not escalate on the generator's own stated confidence under
any circumstance — that signal is proven non-discriminative, not just unavailable.

## MAS Prompt Optimization Risk

WARNING — MAS prompt optimization risk (MAS-PromptBench, arXiv, Jun 2026):
Optimizing prompts for individual subagent roles in a multi-agent system can
cause -16pp system-level degradation even when per-agent metrics improve.
Reason: role prompts interact — a "better" analyst prompt can break the
downstream synthesiser's expectations. Never apply per-agent prompt optimization
blindly. Test system-level metrics after any prompt change to a role in a pipeline.

## Experience-Driven Role Evolution (arXiv:2604.00901 HERA; AutoSaddler gate arXiv:2608.23041)

HERA jointly evolves orchestration and role-specific prompts from execution experience.
Hermes can adopt the *flagging* half without AutoSaddler infrastructure. Do **not** auto-update role prompts.

After a pipeline run completes, inspect downstream hand-offs:
- Flag the **orchestrator** (or the role that produced the hand-off) as a refinement candidate if a downstream agent returned `PARTIAL` / `accept-partial`, or needed **>2 clarification turns**.
- Record the candidate in `~/.hermes/agent-workspace/topology-memory.md` as a Modify entry: role name, hand-off symptom, and the compact prompt fragment that caused the bad packet. Not a skill patch yet.

**Gate before any role-prompt edit:** AutoSaddler-style validation, or equivalent human review. Required because MAS-PromptBench (section above) shows per-role prompt wins can drop system quality. Propose via `self-improve-agent`; wait for explicit approval. Never `skill_manage` a role prompt from this detector alone.

Assigned sweep ID `2608.05231` is a different paper (CyberBridge). Cite HERA as `2604.00901`.

## Context Packet Discipline

Before every `delegate_task` call, assemble a context packet using
`hermes-context-packet`. Pass the compact `hermes-context-packet/v1` JSON as the
task `context` instead of free-form prose. Trim `prior_findings_refs` to summaries
if a packet exceeds ~2000 tokens.

## Structured handoff schema

When chaining agents in a pipeline, each worker should produce a typed handoff object
rather than free-form prose. This prevents the next stage from having to parse intent
from unstructured text and makes review/replan decisions deterministic.

**Minimum 4-field handoff** (sourced from r/hermesagent orchestrator design thread, Jul 2026):

```json
{
  "what_done": "one sentence summary of the completed work",
  "evidence": ["path/to/file", "URL", "tool output excerpt"],
  "files_changed": ["relative/path/to/changed.file"],
  "unresolved_issues": ["issue description or empty list"]
}
```

- Do not put a numeric self-confidence score on the handoff. Escalate on structural inability (tool error, missing evidence in output_contract) not on self-assessed confidence.
- `unresolved_issues` is non-empty when the worker hit a blocker but still produced partial output.
- `files_changed` enables the orchestrator to scope downstream agents to only affected paths (don't pass the whole repo).

This is an extension of the Artifact Handoff Rules below — use this schema for any pipeline stage that crosses a delegate_task boundary. Intra-parent steps don't need this level of formality.

## Review loop branching

When a reviewer rejects a worker's output, the orchestrator must choose a named next action — not just "retry." Name the branch explicitly in the context packet passed back to the orchestrator:

| Reviewer verdict | Trigger condition | Orchestrator action |
|---|---|---|
| **retry-same** | Output is mostly correct; minor error or incomplete section | Re-dispatch same worker with reviewer critique appended |
| **replan** | Wrong approach taken; different tools or decomposition needed | Return to planner; regenerate task DAG for this subtask |
| **decompose-further** | Task too broad for one agent; no single output possible | Split into 2+ narrower tasks; re-enter execution phase |
| **ask-human** | Missing context only the user can provide; structural inability (tool error, missing evidence in output_contract) | Surface clarification_needed; pause and escalate |
| **accept-partial** | Output is incomplete but usable; downstream can compensate | Pass handoff with `unresolved_issues` populated; continue pipeline |

Max retry cap: 2 retry-same passes per task node before escalating to replan or ask-human. A node that fails 3 times with the same approach has a structural problem, not a transient one.

## Handoff Checkpointing

At each major pipeline stage boundary, save a checkpoint file so a stalled or
re-dispatched pipeline can resume without redoing prior stages. Write it to:

```
~/.hermes/agent-workspace/<pipeline_id>-stage-<N>.checkpoint.json
```

Capture the stage's resolved objective, the findings/output paths produced, and
the context packet handed to the next stage. Checkpoints make Supervisor and
Pipeline patterns recoverable across multi-wave work.

## Artifact Handoff Rules

When chaining more than 2 skill stages:
- Pass only the **output artifact** to the next stage (code diff, findings JSON,
  summary paragraph, verdict object) — not the full parent context or transcript.
- If a downstream stage genuinely needs upstream context, attach a compact context
  packet (see `hermes-context-packet`), not a raw conversation dump.
- State the **artifact type** explicitly in each subagent's context so it knows
  what format to accept and return. This enables routing by type match rather than
  hardcoded pipeline position.
- The orchestrating parent retains full context; workers do not.

At each major handoff in non-trivial pipelines, add a lightweight quality check
before passing the artifact forward (is the JSON valid? does the file exist?
does it meet the input contract for the next stage?). Log pass/fail in
topology-memory.md. This does not require a separate subagent.

After a fan-out, score each output 1–3 (1=not useful, 2=partial, 3=essential)
before synthesis. Weight or exclude outputs scored below 1.5. Scores below 1.5
across runs → Avoid entry; above 2.5 → Preserve entry in topology-memory.md.

## Topology Memory (QueenBee pattern)

After a multi-agent run, record a brief topology note in the skill bank file at
`~/.hermes/agent-workspace/topology-memory.md`. This is lightweight design
knowledge — not task results, but which pipeline shape worked or failed.

Each entry uses three actions (Preserve / Modify / Avoid):

```
## <date> — <task type>
pattern: <pattern name e.g. fan-out/fan-in, producer-reviewer, supervisor>
action: preserve | modify | avoid
task_condition: <what kind of task triggered this>
observation: <one sentence — what happened>
structural_note: <which connection type, fan-in width, round count, or role combination mattered>
cost_signal: pass | high-token-cost | context-bloat | timeout
```

Rules:
- Write an Avoid entry whenever a topology caused context bloat, a merge failure,
  contradictory outputs that required expensive arbitration, or exceeded token budget.
- Write a Preserve entry when a topology produced clean, low-cost results on a task
  type you'll run again.
- Write a Modify entry when the shape was correct but needed a small adjustment
  (e.g. fan-in was too wide, synthesis step needed a dedicated role).
- Apply the falsification gate before converting a single Preserve observation into
  a recommended default: require the pattern to hold on at least two distinct runs
  before treating it as the default choice for that task condition.
- Never append a Modify or Avoid entry without naming the structural cause — "it
  was slow" is not enough; "fan-in width 4 with full-context passing caused bloat
  for large-file review tasks" is.

Use `session_search` to check whether a pattern has been seen before before
writing a new entry. If a prior entry exists for the same pattern + task type,
update it rather than creating a duplicate.

Topology memory entries feed back into the Pattern Chooser above: when selecting a
pattern for a new run, first check `~/.hermes/agent-workspace/topology-memory.md`
for Avoid entries matching the current task condition before defaulting to the
standard guidance.

### Edge Probability Table (GPTSwarm pattern)

Append a YAML skill-connection probability block at the bottom of topology-memory.md.
Update after each run using outcome quality as the reward signal (pass = +, fail = -):

```yaml
# skill_connections: cumulative success-weighted probability for each skill-to-skill
# edge. Values: 0.0–1.0. Prune candidates: < 0.3. Strong signal: > 0.75.
# Update rule: new_prob = old_prob * 0.9 + outcome * 0.1  (outcome: 1=success, 0=fail)
skill_connections:
  fan-out/fan-in → swarm-consensus: 0.92    # high AIS, preserve
  supervisor → validator: 0.88              # strong signal
  fan-out → early-synthesis: 0.41           # borderline, modify
  parallel-review → merge-prose: 0.21       # prune candidate, use agent-sync instead
```

This table makes topology intuition explicit and machine-readable. Over time it
becomes a lightweight learned routing policy — without training a model.

## Conflict Resolution

When parallel (fan-out) agents return contradictory findings or verdicts on the
same question, use conflict-resolve before applying swarm-consensus:
  ```
  python3 ~/.hermes/scripts/metacognitive-harness.py conflict-resolve \
    --framework-a '<role-A framework>' --verdict-a '<PROCEED|BLOCK|UNKNOWN>' \
    --framework-b '<role-B framework>' --verdict-b '<PROCEED|BLOCK|UNKNOWN>' \
    --task '<task description>' --confidence-a <0.0-1.0> --confidence-b <0.0-1.0>
  ```
  conflict-resolve handles action-level conflicts (PROCEED vs BLOCK).
  hermes-swarm-consensus handles epistemic disagreements (competing factual claims).
  Exit 2 (both UNKNOWN) = escalate to human; do not invent a resolution.

For L2+ role pipelines, run select-frameworks before instantiating roles:
  ```
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
    --task "<pipeline goal>" --level <L>
  ```
  Include the primary framework list in each role's context packet.
same claim, do not hand-merge them in prose. Load `hermes-swarm-consensus` and run
its deterministic reducer (majority rule / highest-confidence / arbiter
escalation) to produce a single authoritative verdict before the merge step.

## Aug 2026: Mid-Conversation System Messages (GA, Anthropic API)

Anthropic now supports updating the system message mid-conversation without breaking
the thread or invalidating the prompt cache. Previously required starting a new session.

**Pattern — dynamic skill injection:**
When the semantic skill router detects a topic shift (e.g. user pivots from planning to
code review), inject a skill-specific system prompt mid-conversation to add domain expertise
without resetting state.

```python
# Add a mid-turn system update (no cache invalidation)
messages.append({"role": "user", "content": [
    {"type": "text", "text": "[SYSTEM UPDATE] You are now acting as a code reviewer..."},
]})
# Or via the API system_update field (check beta header: mid-conversation-system-messages)
```

**Other use cases:**
- Switch persona/role based on detected intent (research → code → review)
- Inject tool availability changes based on conversation state
- Add time-sensitive context (current date, live prices) at the right moment, not upfront

**Hermes workflow:**
Load the relevant skill's key instructions as a compact system update when routing detects
a skill switch. Preserves context window efficiency vs loading all skills upfront.

## RELIC: Distill Textual Principles from Multi-Agent Runs (arXiv:2607.16745, Sweep 15)

RELIC showed that agents sharing decision logic as compact **textual principles** (not code or
model weights) enables cross-agent skill transfer across heterogeneous teams. Principles that
repeatedly improve team performance get promoted; others decay.

**Key insight for Hermes multi-agent runs:**
After a delegate_task fan-out, the parent synthesizes task outputs — but also loses the
inter-agent coordination patterns that made the run work. Those patterns should be distilled
into reusable skill principles.

**After any multi-agent run (3+ agents, non-trivial result):**

1. In the synthesis phase, also review: "What coordination pattern worked?"
   - Did serializing agent X before agent Y prevent a conflict?
   - Did a specific context packet structure get clean handoffs?
   - Did a particular role decomposition reduce context bloat?

2. Distill into a one-line principle:
   ```
   # Examples:
   "For PR review fan-outs: security reviewer runs AFTER code reviewer, not in parallel —
    security findings depend on code reviewer's diff scoping."
   
   "For research fan-outs: researcher agents with enabled_toolsets=['web'] outperform
    full-toolset agents — extra tools cause distraction, not quality gain."
   ```

3. Append to `~/.hermes/agent-workspace/topology-memory.md` as a Preserve entry.
   (Use the existing QueenBee topology memory pattern — it's the right location.)

4. After a principle appears in 2+ independent runs: **propose** adding it to the relevant
   Hermes skill as a `## Best Practice` or `## Pattern` section. Present the proposal to the
   user and wait for explicit confirmation before calling skill_manage. Do not auto-promote.

**Promotion threshold:** same falsification gate as memory — 2+ independent observations
before a principle becomes a persistent recommendation. Single-observation principles
go to topology-memory.md only (not directly into skills).

**What NOT to distill:**
- Task-specific parameters (these are task context, not principles)
- Individual success/failure counts (these belong in the edge probability table)
- Role output quality scores (topology memory handoff scores cover this)

## Audit Delegation Pattern (from references/audit-delegation-pattern.md)

Use when a large domain (config, architecture, security, performance) needs systematic assessment + implementation orchestration.

1. **Context gather** (5-10 min local reads): key config files, policies, hooks, relevant skills — NOT everything. Output: mental model of what's live
2. **Audit dimensions**: list 5-7 areas + 2-3 specific things to look for per area (narrows focus, prevents tangents)
3. **Context packet** (500-800 words): key config highlights with line-by-line interpretation, budget policy, skills structure, active toolsets, known gaps. Point auditor to actual files to read. Format: "==" section headers
4. **Delegate with explicit output schema**: `audit_ts`, `auditor`, `summary`, `priority_improvements[]` (id/area/severity/title/finding/recommendation/effort), `config_patches[]`, `skill_actions[]`, `security_findings`. Instruct: "Read actual files before finalizing. Be critical and specific."
5. **Task ledger entry**: write to `~/.hermes/logs/hermes-task-ledger.jsonl` (task, initiated_by, phases, status)
6. **Implementation orchestration**: while auditor runs, draft an orchestrator plan to fan out implementation subagents by area (config/skills/security/multiagent). Do NOT execute until auditor finishes; do NOT re-use audit subagent

## Workflow family → seed mapping (from references/workflow-family-seed-mapping.md)

Six workflow families for multi-agent patterns:

| Family | Best fit | Seed style |
|---|---|---|
| `pipeline` | later work depends on earlier outputs | `sequential` |
| `fanout_fanin` | independent parallel discovery merged before action | `parallel_then_merge` |
| `producer_reviewer` | one worker produces, another critiques | `two_step_with_review` |
| `supervisor` | parent-managed worker waves where findings change next assignment | `iterative_waves` |
| `expert_pool` | conditional specialist dispatch | `conditional_dispatch` |
| `groupchat` | next speaker is state-dependent; sequential turns on one work item | `speaker_selected_turns` |

**Heuristic default**: when markers are weak, use `pipeline` rather than inventing a bespoke category.
Emit at least: `workflow-family.json`, `workflow-handoff.md`, `workflow-seed.yaml`.
Verify: read back emitted JSON/YAML to confirm the selected family and seed style are actually on disk.

## Local note

The upstream role catalog was designed for OpenCode AI; Harness was designed for
Claude Code agent teams. In Hermes, treat both as design references: map roles into
`delegate_task` goals, keep orchestration in the parent, and adapt hierarchical
patterns to Hermes's depth-1 constraint (serial parent-orchestrated waves).
