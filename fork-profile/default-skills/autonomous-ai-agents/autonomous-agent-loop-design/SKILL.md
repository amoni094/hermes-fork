---
version: 1.4.3
name: autonomous-agent-loop-design
description: >
  Use when designing autonomous agent loops that can run unattended and self-improve — measurable objectives, cheap surrogates, reference-driven context, and eval-as-infrastructure patterns from Karpathy's autoresearch work on nanochat.
triggers:
  - designing a cron job or background agent task
  - delegating a long-running optimization or research task
  - asking an agent to improve, refactor, or explore something autonomously
  - setting up Ouroboros evolve loop
  - "how do I make this run unattended"
  - multi-phase task where subtask history will bloat context (Context-Folding trigger)
  - complex multi-constraint reasoning with state that needs in-place revision (Canvas-of-Thought trigger)
  - authoring chain-of-thought prompts or compressing agent reasoning traces (forking-token trigger)
  - loop contract, DAG task tracking, loop integrity, or harness tampering audit
  # Disambiguation:
  # This skill = loop ARCHITECTURE (eval design, numeric objectives, long-run patterns)
  # async-agent-nightshift-patterns = unattended SAFETY (deny-by-default, HITL timeout=deny, sandbox)
  # agent-runtime-loop-patterns = per-turn/per-tool GUARDRAILS (retry logic, tool schema, self-correction)
  # agent-memory-consolidation = write/promote/poison gates (not this skill)
related_skills:
  - autonomous-ai-agents
  - hermes-role-pipelines
  - trajectory-risk-guardrail
  - mnemosyne-atp-safety
  - preact-trajectory-compilation
  - hermes-cron-and-agents
  - hermes-self-evolution
  - agent-memory-consolidation
  - ralph-loops
---

# Autonomous Agent Loop Design

Patterns extracted from Karpathy's autoresearch work on nanochat (Mar 2026), where an agent ran unattended for 2 days, found 20 improvements a human missed, and cut GPT-2 training time from 2.02h to 1.80h (then 1.65h in round 2).

## Additive-Cost Subtask Decomposition (arXiv:2608.16889 BATON, Aug 2026)

BATON: +11.6% over SoTA on RoboMemArena. Two applicable patterns:

**Subtask as the unit of exploration** (T*K not T^K): each child agent gets exactly one bounded subtask with a defined exit condition, rather than a large open-ended task that internally branches. The parent composes results; children don't discover the full problem space.

**Transition-aware verifiers**: each subtask boundary has a named verifier that checks preconditions for the *next* subtask before handing off. If entry conditions fail, the verifier re-runs the prior subtask (with modified context) rather than passing broken state forward.

Hermes pattern:
- Structure delegation as: subtask_1 → verifier_1 → subtask_2 → verifier_2 → ...
- Verifier is lightweight (not a full LLM call): did subtask_1 produce the required artifact in the expected format?
- If verifier fails: re-dispatch subtask_1 with the failure mode in its context (not a full task re-run)
- Record verifier agent IDs and input references in Hindsight for cascade attribution

Reference: arXiv:2608.16889, "Don't Drop the BATON", Aug 2026.

---

## PILOT — Three-Role Agentic Loop Separation (arXiv:2608.18637, Sweep 20) <!-- why: monolithic agent loops conflate lifecycle governance, planning, and memory distillation causing each to degrade the others -->

PILOT separates three roles that naive agent loops conflate:
- **Experiment Manager**: lifecycle governance via a rule-generated legal-command envelope. Only commands in the envelope are actionable; everything else is refused. +1.4% IPV, search efficiency 53% → 93% on Taobao.
- **Search Planner**: invoked on-demand when the envelope allows exploration, not always running.
- **Async Memory Curator**: distills task postmortems into reusable domain knowledge, running independently of the main loop (a separate cron-like process).

Hermes mapping:
- Experiment Manager → `trajectory-risk-guardrail`: enumerate legal actions before each agentic run; refuse unlisted actions
- Search Planner → skills that invoke `delegate_task` for exploration subtasks (already present)
- Async Memory Curator → an independent periodic memory job (must not interleave with the execution loop). Distillation policy: `agent-memory-consolidation`, not this skill.

Key principle: the curator is ASYNC — it must not block or interleave with the execution loop. Memory distillation happens after the session, not during.

## Agile AI-DLC — Executable Spec Loop (valeriavg.dev, Aug 22 2026, Sweep 20) <!-- why: documentation-heavy agent task specs leave correctness undefined; executable checks give the agent a deterministic exit condition -->

"Agile AI Development Lifecycle": replace task descriptions with executable specifications (tests, linters, CI checks). The agent iterates until all deterministic checks pass — no agent self-assessment of "done", only objective pass/fail from the spec.

Hermes implementation: for any agentic task that produces code or config:
1. Define acceptance checks BEFORE starting: `hermes doctor`, test commands, linter commands
2. The agent loop runs until all checks return exit code 0 — this IS the exit condition
3. Track "path errors" (wrong-path attempts before success) as a quality metric; high path-error counts signal skill gaps
4. Cost budget: estimate max iterations × per-turn cost; abort loop if budget exceeded and surface partial work

"Paved paths" principle: common success paths should be documented as skills so the agent doesn't re-explore them from scratch each run.

## Agent Runtime/OS/Infrastructure Taxonomy (Zenn.dev/tanuki_chan, JP, Aug 21 2026, Sweep 20) <!-- why: conflating runtime, OS, and infrastructure layers leads to wrong-layer patches -->

Three-layer stack: Infrastructure (compute/storage/network) → Agent OS (process management, scheduling, memory harness) → Agent Runtime (conversation loop, context, skill loading).

Diagnose which layer failed before patching: runtime failures = fix skill/tool contract; OS failures = fix scheduler/harness config; infrastructure failures = fix environment. A runtime skill patch cannot fix an OS scheduling bug.

Hermes mapping: Infrastructure = Linux/disk/API; Agent OS = Hermes daemon, cron, skill router; Agent Runtime = conversation loop, context window, skill injection per turn.

## The 5 Principles

### 1. Define a numeric objective before launching

The agent worked because CORE score is a number. Without a concrete metric, an agent optimizes vibes.

Before delegating any optimization/research task, ask:
- What number goes up (or down) when this succeeds?
- Is that number computable from within the agent's environment?
- What is the current baseline?

If you can't answer these, the task is not ready for autonomous execution. Write the eval first.

Good: "run pytest, report pass rate" / "measure p95 latency before and after" / "count lint errors"
Bad: "make this better" / "clean this up" / "improve quality"

### 2. Use a cheap surrogate, not the full target

Karpathy ran autoresearch on d12 (tiny model, fast) before applying findings to d24/d26.

For agent tasks in Hermes:
- Run the agent on one file before all files
- Run on one day of data before a month
- Run on a small dataset/subset before the full thing
- Run one iteration of a loop before scheduling it daily

Promote to full scope only after the surrogate validates the approach. This catches prompt bugs, broken tool calls, and wrong assumptions cheaply.

### 3. References beat instructions — and structure delegation context for cache hits

When delegating to subagents (Hermes delegate_task), the `context` field is injected as
dynamic content in the worker's prompt. If the context is large and unstructured, it breaks
the worker's cache prefix on every re-run.

To maximize worker-side cache hits:
- Put stable reference content (skill descriptions, project conventions, tool docs) in the
  *goal* field where possible — goal text is more likely to be repeated across similar tasks.
- Keep the `context` field minimal: goal-specific state only (current file, task ID, constraints).
- For repeated delegation patterns (same worker role, different inputs), use a fixed preamble
  in `context` (e.g., a project-context block) followed by the variable part. The fixed preamble
  will cache; the variable tail will not.
- Avoid timestamps, session IDs, or randomly-ordered lists in the context preamble — one volatile
  token in the stable zone breaks cache for the entire prefix.

For jobs using `context_from` (chained cron jobs): the injected prior output is always dynamic.
Structure the job's own prompt as a stable prefix + dynamic context_from injection at the end.

Round 2 was more productive because Karpathy gave the agent a reference repo (modded-nanogpt) to draw from. The agent found combinations of ideas it couldn't have generated from the problem statement alone.

When writing prompts for subagents or cron jobs:
- Point at real code files, not described behavior
- Link to a reference implementation or prior working example
- For skills: a concrete reference file beats prose explanation of the same concept
- Use `context_from` in cron jobs to chain outputs — job A collects, job B reasons over it

### 4. Uninterrupted duration finds what sessions miss

The 2-day run found 20 things months of manual work missed. Interactive sessions with a human present and steering are often the wrong tool for optimization tasks.

Use background execution (cron, Ouroboros evolve, delegate_task) when:
- The search space is large (many hyperparameters, many files, many approaches)
- Each trial takes minutes, not seconds
- You want to come back to results, not watch them happen

The Ouroboros `evolve` loop is the primary tool for this in Hermes. It is underutilized relative to what this pattern suggests.

### 5. Eval is infrastructure, not an afterthought

The reason autoresearch could run autonomously: eval was runnable scripts in the repo (`tasks/arc.py`, `tasks/mmlu.py` etc.), not docs or manual checks.

An agent cannot close its own feedback loop without executable eval. Before delegating:
- Does the codebase have tests the agent can run?
- If not, write minimal test coverage first — even 3-5 targeted tests beats zero
- The agent's loop is: change -> run eval -> accept/reject. Without step 2, it's just change -> hope.

## Shared-Language Project Doc

For projects you work on across multiple sessions, maintain a short shared-language document:
- What the project does (one paragraph).
- Key domain terms and what they mean in this codebase.
- Non-obvious architectural decisions and why they were made.
- Current known constraints, tech debt, or active refactors.

Store as `<project-root>/.hermes/project-context.md`. Hermes does not auto-load `.claude/skills/`.

This pays off across sessions: the agent doesn't rediscover the same context repeatedly, and subagents get aligned shared vocabulary without you repeating it.

Update the doc when: a major decision is made, a key term is defined, or significant architecture changes.

## Repo-Level Skills Pattern

Karpathy keeps `.claude/skills/read-arxiv-paper` inside the nanochat repo (his layout, not Hermes).

For Hermes projects you work on heavily, prefer:
```
<project-root>/.hermes/project-context.md
```
Pass `workdir=<project-root>` when creating cron jobs or `delegate_task` calls against that project.
Do not author a parallel `.claude/skills/` tree unless the user is actually using Claude Code in that repo.

## Ralph Loops: When Context Rot Is the Main Risk

For tasks where a ReAct loop risks context accumulation over many iterations (migrating
a large codebase, raising coverage from 16% to 95%, implementing a ticket backlog),
switch to Ralph Loops instead of a long-running single ReAct session:

- Each iteration gets a **fresh context window** — spec + filesystem state only
- State lives on disk (files + git diff) — not in the conversation history
- Exit condition is **objective and executable** (tests pass, CI green, coverage ≥ threshold)
- Never exits on model self-assessment

Implementation: a fresh-context outer loop over the project worktree. See `ralph-loops` — do not copy a vendor CLI one-liner here.

Use Ralph Loops when:
- A single task needs 5+ reasoning passes to complete
- Prior attempts' outputs need to be re-read (git diff) rather than re-remembered
- Context rot (model forgetting the spec) is the actual failure mode you've observed

## HTC / AUQ: trajectory-level calibration (arXiv 2601.15778 / 2601.15703)

Per-prediction Brier ≠ trajectory Brier. Early overconfidence compounds ("Spiral of Hallucination").
HTC: weight earlier steps more; pause if trajectory Brier > 0.25 or confidence stdev is high.
AUQ: propagate confidence with facts (System 1); reflect only below a threshold (System 2);
if still uncertain, flag — do not keep propagating.

Code: `references/trajectory-calibration.md`. If the model does not emit confidence, skip the
classes and use the **manual shortcut** in Brier Score Self-Calibration below.

## Brier Score Self-Calibration (OpenFang Predictor pattern)

OpenFang's Predictor Hand tracks its own prediction accuracy over time using Brier scores.
This is applicable to any agent that makes uncertain predictions (bug risk, performance
improvement estimates, search quality estimates, relevance scores).

**What is a Brier score:** mean squared error of a probability prediction.
- Score 0.0 = perfect calibration; Score 1.0 = perfectly wrong; Score 0.25 = coin flip.
- A Brier score < 0.1 indicates well-calibrated predictions.

**Pattern for Hermes agent loops:**

```python
from statistics import mean

# At prediction time: record the probability estimate + what it was about
predictions = []
predictions.append({
    "id": "task-42-success",
    "predicted_prob": 0.8,  # "80% this approach will fix the bug"
    "outcome": None,         # fill in after task
    "timestamp": time.time()
})

# After the task: record actual outcome
predictions[-1]["outcome"] = 1.0  # 1.0 = happened, 0.0 = didn't happen

# Compute Brier score
brier = mean((p["predicted_prob"] - p["outcome"])**2 for p in predictions if p["outcome"] is not None)
# If brier > 0.25: agent is systematically overconfident or underconfident — adjust
```

**When to apply:**
- Agents that estimate task complexity before attempting
- Agents that score relevance or quality before expensive operations
- Any agent making a repeated probabilistic decision (ranking, routing, filtering)

**In a multi-iteration loop:** track Brier scores across iterations. If the score degrades
(predictions getting worse over time), the agent has drifted from its calibration baseline
— trigger a context reset or recalibration pass.

**Practical shortcut (no code required):** After each autonomous run, note:
- What you predicted (e.g., "this refactor will break 2 tests")
- What actually happened (e.g., "broke 5 tests")
- Whether you were systematically over/under-confident

Over 3+ runs, a pattern of 1.5–2× underestimating failures → add a 1.5× correction factor
to your future estimates. This is manual Brier calibration without scoring infrastructure.

## Autonomy Slider: Workflow First, Agent Second

Before choosing agents, work through this decision chain:

1. Is the task deterministic with predictable steps? -> Use a workflow pattern (prompt chaining, parallelization, routing, orchestrator-worker, evaluator-optimizer). These are cheaper, debuggable, and reliable.
2. Does the task require dynamic decision-making based on intermediate results? -> Consider agents.
3. Is a single large LLM call failing? -> First try splitting into chained workflow steps, not agents. "Lost in the middle" and modularity issues are the most common root cause.

Rule: Agents add complexity (unpredictable costs, harder debugging, more failure modes). Only escalate when workflows genuinely cannot handle the task's decision surface.

The five workflow patterns to try before agents:
- Prompt Chaining: sequential LLM calls, each building on prior output
- Parallelization: independent sub-tasks run concurrently, results merged
- Routing: classify input, dispatch to the right specialist path
- Orchestrator-Worker: one LLM breaks work into tasks, workers execute
- Evaluator-Optimizer: worker produces, evaluator scores, loop until threshold met

## Active Context Compression (Focus Agent Pattern)

For long agent runs where context grows monotonically (many tool calls, large outputs),
apply intra-task compression via a "sawtooth" pattern rather than waiting for session
compaction to kick in.

Two primitives:
- `start_focus` — checkpoint the current state; mark start of an exploration phase
- `complete_focus` — summarize the exploration phase, prune the full history back to
  checkpoint + summary, carry forward only learnings into a persistent "Knowledge" block

Trigger: every 10–15 tool calls in a long-running task, or whenever tool outputs sum
to >3K tokens in recent history. For precise token-count thresholds, treat
`hermes-context-hygiene` as authoritative (160K/200K window thresholds); the tool-call
count is a rough proxy when token counts aren't directly visible.

Key finding (arXiv:2601.07190, Focus Agent, 2026): passive prompting ("be concise")
achieves only ~6% token reduction. Aggressive, explicit prompting with periodic system
reminders achieves 22.7% (14.9M → 11.5M tokens) with identical accuracy on SWE-bench
Lite. The difference is the instruction specificity and trigger frequency.

Caveat: tasks where exploration IS the work (broad search, open-ended investigation) may
see a token INCREASE from Focus if extra exploration exceeds compression savings. Apply to
bounded, goal-directed loops, not open-ended search.

## Context-Folding: branch-execute-fold orchestration (arXiv:2510.11967, ByteDance, 2025)

For long-horizon tasks where subtask history accumulates unmanageable context, use a
branch→execute→fold→return pattern instead of a flat linear scratchpad:

1. **Branch**: before starting a subtask, explicitly checkpoint current state:
   `CHECKPOINT: {goal: "...", completed: [...], pending: [...], key_facts: [...]}`
2. **Execute**: run the subtask in its own reasoning space (or subagent context).
3. **Fold**: when the subtask completes, collapse its full trajectory into a summary:
   `FOLD: subtask="<name>", result="<one-sentence outcome>", key_outputs=[...]`
   Discard the full subtask reasoning; keep only the fold summary.
4. **Return**: continue the parent task with the fold summary as context, not the
   full subtask history.

Why this works: active context is 10x smaller because folded subtask histories are
collapsed to summaries. The parent loop never sees subtask internals — only outcomes.
This is structurally different from Focus Agent (which compresses the current context
in-place) and Canvas-of-Thought (which maintains a named-node state graph).

Hermes implementation (no fine-tuning required — use the pattern at skill design time):
- For delegation: spawn a subagent for the subtask; its output IS the fold summary.
- For sequential tool calls: explicitly write a FOLD checkpoint after each major phase
  and discard prior tool outputs from your active reasoning.
- Apply when: task has 3+ sequential subtasks, each with 5+ tool calls.
- Skip when: task is short enough to fit comfortably in one context window.

## Canvas-of-Thought: DOM-tree structured reasoning (arXiv:2602.10494, 2026)

For complex agent tasks where a flat scratchpad causes state-management failures
(variables overwritten mid-reasoning, branching logic collapsed into linear text),
use a DOM-tree structured reasoning space instead.

Core idea: treat the reasoning context as a named-node tree, not a linear string.
Each reasoning step operates on a named variable node. Nodes can be:
- Created: `SET node_name = <value>`
- Read: `GET node_name`
- Forked: `BRANCH node_name IF <condition>`
- Merged: `MERGE [nodeA, nodeB] INTO result`

Benefits vs flat scratchpad:
- Variable state is explicit and addressable, not embedded in prose
- Branching paths do not overwrite each other (each fork is a separate node)
- The agent can `GET` any prior state without re-reading the full scratchpad
- Post-task: the tree is a structured audit trail of what was decided and why

Hermes implementation pattern (no framework required):
1. At task start, declare the reasoning structure: "I will maintain nodes: [goal, constraints, candidates, selected, rationale]"
2. At each significant decision, explicitly write: "UPDATE candidates = [A, B, C]"
3. When branching: "BRANCH: if A then explore X; if B then explore Y. Following A."
4. At task end: "FINAL: selected=X, rationale=<one sentence>"

This is distinct from chain-of-thought (linear) and tree-of-thought (sampled branches).
Canvas-of-Thought keeps a persistent named state graph the agent can query mid-task.
For ToT-style *plan beams before side effects*, do not improvise N scratchpad branches
here — use `hermes-role-pipelines` Plan-then-Execute (ToT-lite) plus critique-before-commit.

Best suited for: multi-constraint planning, code generation with interdependent components,
adversarial review with multiple competing findings. Overhead exceeds benefit on simple
linear tasks — apply only when state-tracking failure is the observed bottleneck.

## Token Budget Discipline

Inject an explicit token budget into reasoning prompts for long-horizon tasks. LLM CoT is
unnecessarily long by default; a prompt-level budget cap significantly compresses it with
only ~2% performance drop [TALE, 2412.18547]. Calibrate the budget to task complexity:
simple tasks get tight budgets; complex multi-step tasks get larger ones.

**Forking-token density** (arXiv:2506.01939): only ~20% of CoT tokens drive decisions (the
forking tokens at branch points). Front-load budget on explicit decision points; when compressing
traces, keep forking-point sentences and drop elaboration. Signal grep: "I will choose", "because",
"the key constraint is".

CRITICAL WARNING: naive hard-cutoff budget forcing causes wrong answers — the model truncates
mid-reasoning and commits to an incomplete conclusion. Use iterative calibration:
- Estimate complexity first (TALE-EP pattern: "rate this task 1-5")
- Set budget proportionally (100/300/800 tokens for low/medium/high)
- Never hard-truncate generation mid-token; use prompt pressure, not stop sequences
[ACC-RAG, COLM 2025; TALE critical finding, 2412.18547]

For iterative improvement loops: if using a model with extended thinking, apply RL-style token
pruning discipline — reward completion within budget, penalize overflow. ~50% reasoning-length
reduction at ~2% perf cost is reported [ThinkPrune, 2504.01296]. Do not pin this to a named model family.

## Prompt Caching for Autonomous Loops

See anthropic-api-cost-optimization skill for canonical prompt caching structure rules (provider-specific thresholds, static/dynamic split). Load that skill when making caching decisions.

In long-running autonomous loops, prompt caching yields 41–80% API cost reduction and 13–31%
TTFT improvement [empirical study across Anthropic/OpenAI/Google, 2601.06007].

Rules for cache-friendly prompt construction:
1. **Static content first** — system prompt, skills, constraints, tool definitions go at the top.
   Never interleave dynamic content (tool results, task state) into the stable prefix.
2. **Dynamic content last** — task context, tool call results, conversation history at the bottom.
3. **Exclude tool results from the cached block** — dynamic tool outputs invalidate the cache.
4. **Avoid dynamic function-calling formats** — keep tool definitions static across turns.

Cache reads are steeply discounted vs base tokens on major providers — confirm *live* pricing.
Structure prompts to exploit prefix caching; do not hard-code a discount factor here.

## Topology Pruning for Multi-Agent Loops

If spawning N>3 parallel agents, do not use fully-connected communication. Dense topologies waste
28–73% of tokens on redundant messages with no accuracy gain. Apply one of:
- One-shot graph pruning (AgentPrune pattern): prune low-signal edges before the run starts
- Semantic routing (DyTopo pattern): each agent declares Need/Offer; routes only to semantically
  matched peers each round. Yields +6.2% accuracy at 51% token savings vs. fixed dense topology.

For multi-round loops: use dense communication in early exploration rounds, sparse in later
verification rounds. Fixed topology across all rounds wastes tokens and hurts performance.

## EvoX: Persistent Project vs Persistent Agent (arXiv:2608.10450, Aug 2026)

Standard agentic systems make agents persistent (long-lived sessions, handoffs, memory).
EvoX inverts this: **make the project persistent; keep agents finite-lived**.

Architecture: each "local world" = accepted version + repo path. Agents propose changes;
only accepted changes advance the version history. Agents die and are replaced — no
handoff overhead because the worktree IS the state.

**Result:** 120-hour C compiler build, 1,000+ agent episodes, only $44 in API costs
(DeepSeek V4 Flash). Compiler passed c-testsuite + most LLVM/Csmith tests; agent
replacement during the run left no regression.

**Key implication for Hermes multi-agent design:**

| Persistent-agent (old default) | Persistent-project (EvoX) |
|---|---|
| Agent needs context handoffs | No handoff — agent reads worktree |
| Agent memory grows indefinitely | Agent memory is zero — state is in repo |
| Agent replacement breaks continuity | Agent replacement is trivially safe |
| Session cost: O(n_turns × context) | Session cost: O(n_agents × small_context) |

**When to apply:**
- Any task with 20+ sequential LLM interactions (migration, code generation campaigns)
- Tasks where context rot (model forgetting the spec after many turns) is the observed failure mode
- Already implemented in Hermes as the `ralph-loops` + `using-git-worktrees` combo:
  the worktree is the persistent world; each `ralph` iteration is a finite agent

**Connection to existing Hermes patterns:**
- `ralph-loops`: each loop iteration is a fresh context window reading only spec + disk state —
  exactly the EvoX finite-agent pattern
- `using-git-worktrees`: git worktree = the "local world" in EvoX terminology; the committed
  version history IS the persistent substrate
- `autonomous-agent-loop-design` checklist item 4 (eval as infrastructure) = EvoX's
  "accepted version" gate — only changes that pass the verifier advance the history

For 20+ LLM-interaction tasks, prefer persistent-project (ralph-loop + worktree) over persistent-session — listed in **Pre-launch checklist** below. The worktree is the memory; keep agents short-lived.

## Argus: Role-Owned Review + Verification-Gated Self-Evolution (arXiv:2608.05144, Aug 2026) <!-- why: prevents unsafe skill/procedure evolution by requiring role review before any state is admitted -->

Persistent, self-evolving runtime with Manager/Planner/Engineer/Reviewer executing bounded missions over **durable project state**. Benchmark: ~78% SWE-Bench Pro (vs 59% Direct Copilot). After verification-gated self-evolution, mature runs use 21% fewer tokens and 15% less active workflow time per task.

**Key design principles:**
1. **Separate stable user intent from operational objectives** — user goal is immutable; constraints and verification criteria are modifiable operational state, not hard-coded
2. **Role-owned review before admission** — memories, skills, procedures, verifiers, and routing decisions are admitted into persistent state ONLY after the designated role (Engineer/Reviewer) approves them
3. **Rejected routes are preserved** — `rejected_routes` in durable state; agents do not re-explore dead ends. A mathematics campaign retained falsified routes and proof-backed frontier updates across multi-day runs
4. **Verification-gated evolution** — model weights are fixed; self-evolution happens through persistent runtime state and control policy, with autonomous execution BETWEEN operator-owned escalation points

**Hermes pattern — apply to any multi-session autonomous loop:**
- Before updating any skill in an autonomous loop, require: role-owned review (not just task success)
- Maintain a `rejected_routes.jsonl` alongside the project state — log what was tried and failed with rationale
- Prefer verifier recovery over manual rewrite for known failure modes
- Escalation points are **operator-owned** (user-defined), not agent-selected — the agent cannot promote itself past an escalation boundary

**Integration with existing patterns:**
- EvoX persistent-project: Argus adds role-owned review gate to the "accepted version" promotion step
- mnemosyne-atp-safety: Argus's "admission only after role review" maps to ATP constraint set C
- ralph-loops: rejected routes become a persistent file the next fresh-context agent reads at loop start

## Loop Governance Formalization — should_continue / record_feedback / fresh_context (Qiita:nohanaga, 2026-08-17) <!-- why: prevents unbounded context growth from inter-iteration progress accumulation -->

Three independently-tunable outer-loop parameters (from Microsoft Agent Framework's AgentLoopMiddleware):
- **`should_continue`** — explicit stop-condition callback; evaluated each iteration before the next LLM call
- **`record_feedback`** — inter-iteration summarizer; **must return short summary (~140 tokens max)**, not full text — token accumulation compounds exponentially across iterations otherwise
- **`fresh_context` toggle** — re-generation tasks (rewrites, refinements): fresh context = original prompt + progress summary; accumulative tasks (todo-driven, multi-step plans): preserve session state across iterations

**4 stop-condition types (apply in priority order: deterministic first, LLM judge last):**
1. Deterministic check (todos_remaining == 0, file written, test passes) → zero LLM cost
2. Completion marker in output (sentinel string, structured field)
3. Max iterations cap (hard ceiling, required)
4. LLM judge (expensive; use only when deterministic checks are genuinely impossible)

**Capability seams for provider swap without skill rewrites (DeepSeek dsh, 2026-08-17):**
Define Service Definitions (interfaces) for Hermes key capabilities (terminal backend, memory read/write, web search) — swapping providers (e.g., local terminal → Modal sandbox) shouldn't require skill rewrites. The Pre-launch checklist item "Safety scope defined" maps to this.

## Pre-launch checklist

Gate before any unattended / 20+ turn loop. Principles above are the design; this is the go/no-go.

- [ ] Reasoning type selected: run select-frameworks before dispatching workers
      ```
      python3 ~/.hermes/scripts/reasoning-complexity-classifier.py select-frameworks \
        --task "<loop goal>" --level <L>
      ```
      L0-L1: no reasoning gates. L2-L3: primary list drives which gates run per iteration
      (lookahead before HAZARD steps, subplan-verify at subtask boundaries, causal-check on attributions).
- [ ] Numeric objective + current baseline exist (Principle 1)
- [ ] Cheap surrogate defined (Principle 2)
- [ ] Eval is a runnable command, not a vibe (Principle 5)
- [ ] Safety scope defined (`trajectory-risk-guardrail`; ATP if irreversible)
- [ ] `should_continue` is deterministic (preferred) or LLM-judge with an explicit cost cap
- [ ] `record_feedback` summaries ≤140 tokens/iteration
- [ ] 20+ LLM-interaction tasks use persistent-project (ralph + worktree), not persistent-session
- [ ] Live memory surfaces only: durable MEMORY.md/USER.md, Hindsight, Graphiti. QMD and MemPalace are **disabled** in this config — do not route loop state there


## Post-Task Consolidation (run after every complex autonomous loop)

After a multi-iteration autonomous run completes, run the consolidation sequence:

1. **Skill lessons** → `self-improve-agent`: scan for high-signal procedural patterns;
   apply Preserve/Modify/Avoid classification; gate with falsification check; present to user.
   Always propose changes and wait for explicit user confirmation. Never apply in the same session without a user yes.
   - If autonomous (cron/subagent): stage to `~/.hermes/cache/pending-improvements/` using
     `~/.hermes/scripts/stage-improvement.sh`. Do NOT call `skill_manage` from the loop.
2. **Declarative facts** → `agent-memory-consolidation`: score candidates (3-axis),
   apply falsification gate, synthesize episodic → semantic, contradiction-check, propose.
3. **Surface routing** → `hermes-memory-surface-selection`: for each approved fact,
   confirm the right surface (durable memory vs Hindsight vs Graphiti vs skill patch).
   QMD and MemPalace are disabled — do not send consolidation there.

Do this ONCE per run, not after every iteration. Single-iteration observations are not
yet ready for consolidation — wait for the full run to complete.

Token budget note: the consolidation pass itself costs tokens. For long runs (>20
iterations), run it in a fresh session with a cache-first prompt layout (see
`hermes-context-hygiene` caching rules) to avoid paying the full context cost again.

## Procedural graph tracking (arXiv:2609.09153) ★ HIGH

A procedural graph stores (procedure, relation, procedure) and evolves by pruning failed transitions / reinforcing successful ones. Hermes has no graph-refiner or held-out auto-commit; do not fake one.

**Outer loop (this skill):** skill step lists are the graph. After the run, stage edits via `self-improve-agent` / `stage-improvement.sh`. Human yes, then `skill_manage`. Do **not** `skill_manage` from the unattended loop (Argus: weights fixed; role-owned review before admission).

**Inner loop:** failed vs successful transitions this iteration — `agent-runtime-loop-patterns` § execution template evolution (session notes / ERRORS.md only). Phantom-guardrail: do not promote a pitfall from an unverified failure.

<!-- why: in-loop skill_manage is unsafe self-evolution; the paper's auto-refiner is out of scope -->

## Workflow Suffix Repair on Evidence Invalidation (arXiv:2609.12533) ★ HIGH

**Earth-Agent-Pro** (Sep 2026): Plan-and-Execute framework that introduces **partial plan repair** — when evidence retrieved mid-plan invalidates a completed step, only the suffix (affected step onward) is replanned, not the entire trajectory. Key components:

- **Workflow-centered structured memory:** stores step inputs/outputs AND causal dependencies between steps
- **Dependency tracking:** when step K fails validation, all steps that depend on K are flagged for re-execution; steps upstream of K are preserved
- **Expert-authored skill constraints:** static guard rails applied at step selection time to prevent skill misapplication (complements runtime-loop error handling)

**Hermes adaptation:**
- In multi-step autonomous loops: when a validation check fails mid-loop (e.g. a read-back shows unexpected state, a tool returns error), do NOT restart from the beginning
  1. Identify the first step whose output is now invalid
  2. Replay only from that step, preserving all earlier confirmed outputs
  3. Log the invalidation event with the step index in ERRORS.md / session notes so the next retry can skip the replan of confirmed-good prefix
- This pairs with the DAG task tracker (dag-task-tracker.py): mark steps as DONE / INVALID / PENDING rather than re-queuing the full plan
- For Hermes cron loops: preserve the `.hermes/cache/task-state.json` partial state across retries; reload it at loop start to skip confirmed steps

**When NOT to use suffix repair:** if the failed step was the plan's load-bearing assumption (e.g. source data turned out to not exist), full replan is cheaper than repairing a suffix built on a false foundation.

<!-- why: replanning the full trajectory after a mid-plan failure discards verified-good work; suffix repair preserves prefix, reduces cost, and applies only the minimal re-execution needed -->

## Research Findings -- Sweep 30-33 (Aug-Sep 2026)

Extracted to keep this file manageable. Full findings in the reference file:

  skill_view(name='autonomous-agent-loop-design', file_path='references/sweep32-33-research-findings.md')

Load when you need loop contract patterns, memory health gate specs, SE-GoS, or Sweep 33 memory patterns.

## Nanochat loop constraints (beyond the five principles)

- Surrogate must finish in <1 hour on real train/eval code and report the same metric as the full run — a hypothetical "will work at scale" is not a surrogate.
- Constrain the search space with explicit ranges (config keys + bounds). Do not say "improve anything."
- Version-pin reference repos to a commit SHA so the agent does not learn from stale or incompatible code.
- Stop if 3 consecutive trials show <0.5% improvement; set `repeat` or a stop condition. Autonomous means unattended, not forever.
- Metrics that work: pass/fail counts, numeric KPIs, lint/security counts, benchmark scores. Metrics that don't: "quality", "better code", "more readable", human judgment.

## Topology selection (research 2024–2026)

See **Topology Pruning for Multi-Agent Loops** above. Extra evidence: `references/agent-topology-research-2026.md`.
When candidate models are within ~3 MMLU points, topology choice dominates model selection.
SAS for short well-scoped frontier tasks; MAS for structured operational work. Self-MoA (same top model ×N) beats mixed-model MoA. Never ship fully-connected N>3 graphs.

## References

- `references/nanochat-autoresearch-patterns.md` — Karpathy nanochat loop: surrogate, baseline, search-space, pinned reference, exit condition, Hermes adaptation.
- `references/agent-topology-research-2026.md` — Topology + token-optimization evidence base (AdaptOrch, AgentPrune, DyTopo, Self-MoA, SkillRouter).
- `references/sweep33-memory-patterns.md` — Sweep 33 memory write/retrieve/compact checklist. **Operational policy lives in `agent-memory-consolidation`** — this file is evidence only.
- `references/sweep32-33-research-findings.md` — Sweep 32–33 loop-contract and memory-health findings (load via skill_view).
- `references/trajectory-calibration.md` — HTC TrajectoryCalibrator + AUQ gate (optional; needs real confidence scores).

Bundled scripts (loop architecture helpers; memory *policy* is not this skill):
- `scripts/loop-contract-init.py`
- `scripts/dag-task-tracker.py`
- `scripts/memory-health-gate.py` — invoke as a pre-write hook; rules come from `agent-memory-consolidation`
- `scripts/se-gos-graphiti-bridge.py` — skill-graph evolution plumbing; authoring policy is `hermes-agent-skill-authoring`
