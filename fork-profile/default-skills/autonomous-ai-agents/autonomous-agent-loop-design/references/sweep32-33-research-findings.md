# Autonomous Agent Loop Design -- Sweep 30-33 Research Findings

Extracted from SKILL.md to keep the main body manageable.
Load: skill_view(name='autonomous-agent-loop-design', file_path='references/sweep32-33-research-findings.md')

Covers: DAG task tracking, loop contracts, memory health gate, LoopsBench, LoopArena, MetaGovern,
ExecCritic, Governance Decay, SE-GoS, Skill Retrieval patterns, RelLift95/PRISM, SkillDreamer,
Recuris memory split, Procedural Graphs, AutoFyn, ArcticSwarm, CoSkill, Sweep 33 memory gate
extensions (MemGuard, MeClear, MemSentry, revocation filter).

---

## Sweep 30 Additions (Aug 2026)

### Prime Agent: Harness Separation + Continual Harness (arXiv:2608.23552) ★ HIGH <!-- why: validates harness-first-agent-design with empirical trajectory data; adds persistent-REPL and recursive-subagent patterns absent from this skill -->

Prime Agent separates the **execution harness** from **strategy** into distinct runtime layers that do not share code paths. Key findings applicable to Hermes autonomous loops:

**Four harness responsibilities (never mix with strategy code):**
1. **Execution** — shell/tool dispatch, timeout, retry with exponential backoff
2. **Recovery** — detect stuck/failed states; rollback to last checkpoint; re-enter loop at safe point
3. **Verification** — compare pre/post state hashes; check required tool calls were made; confirm outputs non-empty
4. **Resource accounting** — token budget tracking per iteration; cost accumulation; hard stop at budget

**Continual Harness pattern:** maintain a persistent REPL across trajectory boundaries so the agent does not lose working state between sessions. This is distinct from memory — it is an active execution environment that survives checkpointing.

**Recursive subagent comms:** subagents communicate directly with their parent (not only via shared memory). The parent harness receives typed JSON from subagents and validates schema before consuming — prevents cascade failures from silent type errors.

**Hermes implementation:**
- `delegate_task` is already the recursive-subagent dispatch mechanism — ensure every subagent output_schema is specified and validated before acting on results
- Persistent REPL ≈ background terminal session with `background=True`; keep session_id across calls
- Recovery entry point: when a loop iteration fails, rollback to last verified checkpoint (last confirmed tool output) and re-enter, not restart
- Resource accounting: track cumulative API calls per loop; add hard-stop guard at N iterations or M tokens

Reference: arXiv:2608.23552, "Prime Agent: Persistent Harness for Recursive Multi-Agent Execution", Aug 2026.

## Sweep 31 Additions: Skill-Guided Action Chunking (Act More/Decide Less)

### Act More/Decide Less — Chunked Execution Over Known Skills (arXiv:2609.02042) ★ HIGH <!-- why: one LLM round per primitive tool wastes budget on routine sequences; chunk at skill boundaries -->

Do not spend an LLM decision round on every primitive tool call once a skill sequence is known.
SPACE (arXiv:2609.02042) learns chunk boundaries from trajectory-induced programmatic skills:
+7.0–31.3% success and up to 78.9% fewer LLM rounds vs strongest baseline (ALFWorld/ScienceWorld).
Naive multi-action RL either collapses to single-action or over-commits — the hard problem is
**where to pause**, not whether to emit more than one action.

**Stale ID:** arXiv:2609.01428 is TRIAGE (next subsection), not this paper. Cite 2609.02042 here.

**Hermes rule:**
1. If the next 2–6 tools are a known skill/SOP/PreAct chunk, emit the chunk and execute open-loop
   until an observation is outside the expected set.
2. Abort the chunk immediately on unexpected observation, tool error, or LivePlan stuck-state —
   then one LLM round to replan.
3. Cap open-loop at 6 primitives or the current skill-step boundary. Never unbounded chunks.
4. Compile repeated successes with `preact-trajectory-compilation`; those sequences are the chunk library.

### TRIAGE — Trajectory-as-a-Skill three-level routing (arXiv:2609.01428) ★ HIGH <!-- why: Full ReAct on every similar query repeats identical steps; route reuse before reasoning -->

Before starting a Full ReAct loop, classify the query:
1. **Direct Reuse** — identical to a stored trajectory → replay, 0 tokens
2. **Skill Substitution** — same skill, different params → deterministic substitute, 0 tokens
3. **Full ReAct** — novel → run the loop and store the trajectory for later reuse

Reported: 62.3% token savings on 1,007 security queries (56% L2, 5.5% L1); 76.3% on ToolBench;
L2 hit rate 0→57% in the first 100 queries. Hermes: check PreAct compiled trajectories / skill
library before a new unattended loop. Identical cron → replay. Parameterized sibling → substitute.
Only novel work pays for Full ReAct.

### SKILL.state for Long-Horizon Loops (arXiv:2608.26263) ★ HIGH

For loops exceeding ~10 steps, switch from append-only conversation history to SKILL.state:
- At each step: model receives only (1) immutable skill spec, (2) current structured state,
  (3) latest observation (ring-buffered to last 3)
- Intermediate reasoning is discarded after commit — prevents prompt bloat
- Token savings accumulate linearly; accuracy improves on long-horizon tasks

Usage: `python3 ~/.hermes/scripts/skill-state.py init --session $SID --skill SKILL_NAME`
Then at each loop step: `skill-state.py step --session $SID --skill SKILL_NAME --observation "..."`
See config: `memory.skill_state.activate_threshold_steps: 10`

### LivePlan-style Progress Guardrail: Add Progress-Rate Breaker (arXiv:2608.26225)

Agent Mesh failure study found: error-rate=0 but no useful progress is a common failure mode
that circuit breakers miss entirely. A 54-step loop ran to budget completion with zero errors
but zero useful output.

Add to Pre-launch checklist:
- [ ] `should_continue` includes a **progress-rate check**, not just error check
      Example: `if last_N_observations_unchanged(): break`
- [ ] Delegation event budget tracked (not just per-call retry count)
- [ ] Progress signal validated as genuinely dynamic before loop launch

### BCIT Predecessor Context Check for Experience Reuse (arXiv:2608.26730)

Before applying a past successful pattern to a new situation, verify:
1. Was the success observed under similar context conditions (same model tier, same task type)?
2. Are applicability conditions still met?
3. Are there named hard conflicts with current constraints?

Add to Post-Task Consolidation step 1 (self-improve-agent):
- Record context conditions alongside extracted lessons (model version, task category, tool set)
- l1-promote.py successor_context field: stores applicability metadata

### Argus Rejected-Routes Log for Autonomous Loops (arXiv:2608.05144)

For multi-session autonomous loops, maintain a `rejected_routes.jsonl` alongside project state:
```
~/.hermes/cache/rejected-routes/<project-id>.jsonl
```
Each entry: `{"route": "what was tried", "reason": "why it failed", "session": SID, "ts": ISO8601}`

At loop start: fresh-context agent reads rejected_routes to avoid re-exploring dead ends.
This prevents the Ralph-loop failure mode where each fresh session re-tries the same bad approach.

## Quick Checklist Before Launching an Autonomous Task

- [ ] Numeric objective defined and computable
- [ ] Baseline measured
- [ ] Tested on surrogate/subset first
- [ ] Reference material attached (files, prior examples, related code)
- [ ] Eval is runnable (not just describable)
- [ ] Duration and budget set (max iterations, max cost, stop condition)
- [ ] Safety scope defined (is the loop repo-contained? no irreversible external side effects?)
- [ ] Planning-before-execution when ≥2 approaches are plausible: N=2–3 candidate plans,
      critic that did *not* generate them picks one; no mutating tools until then
      (`hermes-role-pipelines` ToT-lite). Skip on complexity Level 0–1 with no HAZARD.
- [ ] Critique-before-commit: separate critic (fresh context, read-only) must `pass` before
      durable commit; executor self-grade is not a gate
- [ ] Max iteration cap set as backstop (e.g. MAX_ITER=20)
- [ ] K-failure budget set: max N consecutive failures before escalation, not open-ended retry
      (arXiv:2604.11378: bounded K-failure budget prevents open escalation cascades)
      Recommended: K=3 for tool errors; K=2 for provider errors; K=1 for irreversible actions
- [ ] session_stall_timeout in config.yaml >= max expected child runtime
      (production root cause 2026-08-30: parent killed research children at 300s; fix: 1800s)
      Verify: grep -E 'session_stall_timeout|gateway_timeout' ~/.hermes/config.yaml
- [ ] Token budget set in prompt for reasoning steps (TALE pattern)
- [ ] Prompt structured cache-first: static prefix, dynamic suffix (41–80% cost savings)
- [ ] If N>3 agents: topology is sparse or dynamically routed, not fully-connected
- [ ] Cost proxy recorded: note model tier + estimated prompt tokens per iteration × MAX_ITER
      (cost proxy = prompt_tokens × rate × iterations; Anthropic: input cached 0.1×, uncached 1×)
      This is an estimation floor, not a real-time cap, but catches runaway loops before they finish.
      If estimated cost exceeds budget at checklist time, reduce MAX_ITER or switch surrogate.
- [ ] `should_continue` is deterministic (file exists / tests pass / todos==0) or has an LLM-judge fallback with an explicit cost cap
- [ ] `record_feedback` summaries ≤140 tokens per iteration (not full transcripts)
- [ ] For 20+ LLM-interaction tasks: persistent-project (ralph-loop + worktree), not a long-lived session — EvoX
- [ ] Progress-rate breaker alongside error-rate: `last_N_observations_unchanged` / no_effective_progress trips even when error_rate=0
- [ ] Progress signal is actually dynamic (a constant-by-construction metric will false-trip)
- [ ] Delegation event budget set (cap accumulated events across re-invocations, not just per-call retries)

## PreAct: Trajectory Compilation for Repeated Tasks (arXiv:2606.17929)

When an agent task runs repeatedly on identical or structurally-similar inputs, compile the
successful run into a deterministic state machine for **8.5–13× replay speedup** (zero LLM calls
on replay). A screen-state verifier fires the LLM fallback on unexpected conditions.

Trigger: task has run successfully ≥2 times with stable tool-call sequence.
See `preact-trajectory-compilation` skill for full implementation pattern.

## Mnemosyne ATP: Safe Workflow Commitment (arXiv:2607.00269)

For loops that execute **irreversible actions** (file deletes, deployments, DB migrations,
external API calls), wrap proposed actions with Agentic Transaction Processing:
- LLM proposals are "untrusted" — admitted only if they pass constraint set C
- Append-only log + effective-state projection + local repair on failure
- `<6% overhead`, `~10× fewer repair ops`, zero invalid commits in live pilots

Trigger: any loop step that cannot be undone. See `mnemosyne-atp-safety` skill.

**Pre-flight safety order for loops with side effects:**
Before designing the loop execution sequence, run `trajectory-risk-guardrail` first to
enumerate and classify the whole trajectory. TRG is the pre-flight filter; ATP
(mnemosyne-atp-safety) is the per-action runtime gate. They compose: TRG shapes the
trajectory; ATP enforces each committed step. See also `async-agent-nightshift-patterns`
for unattended-specific safety (deny-by-default, HITL timeout).

## LivePlan: Cheap Monitor + Expensive LLM Advisor Only on Trigger (arXiv:2608.06701, Aug 2026)

+9.9% average issue-resolution rate on SWE-bench Verified/Pro at only $0.08/instance
additional cost.

**Key design:** decouple monitoring (deterministic, rule-based, zero LLM cost) from
advising (LLM called only when a problem is detected). Current pattern in most agent
loops calls the LLM for self-correction on every turn — this is 10-100x more expensive
than necessary and fires corrections when none are needed.

**Three detectable stuck-states (rule-based, no LLM):**
1. **Repetition:** same tool called with same args ≥3 consecutive times → stuck
2. **Drift:** current tool sequence no longer relates to the original plan step → drift
3. **Failure cascade:** ≥N consecutive tool failures on different approaches → escalate

**Implementation for Hermes ralph-loops and autonomous-agent-loop-design:**
```python
# Cheap monitor — run before every LLM call, no tokens spent.
# Drift needs the current plan step's allowed tool names (empty set = skip drift).
def monitor_state(tool_history: list[dict], plan_tools: set[str] | None = None) -> str | None:
    last3 = tool_history[-3:]
    if len(last3) == 3 and len({(t["tool"], str(t["args"])) for t in last3}) == 1:
        return "STUCK:repetition"
    if sum(1 for t in last3 if not t.get("success", True)) >= 3:
        return "STUCK:failure_cascade"
    if plan_tools and last3 and not any(t["tool"] in plan_tools for t in last3):
        return "STUCK:drift"
    return None  # healthy — no LLM correction needed

# Expensive advisor — call LLM only when monitor fires
if (signal := monitor_state(history, plan_tools)):
    correction = llm_call(f"Trajectory stuck: {signal}. Original goal: {goal}. Suggest correction.")
```

Apply this pattern in any loop with ≥10 iterations. Saves 80-90% of correction-call
overhead in healthy sessions while still catching genuine stuck states.

## EASR: Efficiency-Adjusted Success Rate (arXiv:2608.00805, Aug 2026) ⭐ CODE

New metric for agent evaluation that penalizes resource-burning successes:

**EASR = success_rate × resource_efficiency_weight**

Where resource_efficiency_weight combines: latency, API cost, context tokens consumed,
and CPU/memory under declared budget constraints.

A skill that succeeds but burns 3x the expected token budget gets penalized; a skill
that succeeds at 0.5x the expected cost gets rewarded. This matches real production
constraints better than raw task success rate.

**Hermes application:** adopt EASR as the secondary metric alongside task success rate
in skill benchmark runs. Log: `{skill, task, success: bool, tokens_used, api_cost, latency_s}`
per run. Compute `efficiency_weight = declared_budget / tokens_used` (capped at 1.0).
Skills with EASR < 0.6 (succeeds but profligate) should be flagged for context optimization.

## Coordination as a Separable Architecture Layer (arXiv:2605.03310, May 2026)

Multi-agent systems that embed coordination logic inside individual agents produce
41-87% of production failures from coordination defects — role ambiguity, message
routing errors, consensus failures, and deadlocks that are invisible to per-agent tests.

**The key design principle:** coordination (who does what, when, in what order) should
be a SEPARATE layer from execution (how each agent does its task). Mixed architectures
embed routing and orchestration decisions inside the worker agent prompts — this makes
coordination failures indistinguishable from task failures.

**Applied to Hermes delegate_task patterns:**
| Anti-pattern | Symptom | Fix |
|---|---|---|
| Coordination logic in worker prompt | Worker decides whether to hand off | Move hand-off decision to orchestrator |
| Implicit message routing | Workers infer who to report to from context | Explicit `deliver=` + structured output contracts |
| Shared state without ownership | Multiple agents write the same file/memory | Single writer; others read-only |
| No consensus protocol | Parallel agents produce conflicting results | Designate one reducer (hermes-swarm-consensus skill) |

**Hermes coordination checklist for any multi-agent task:**
- [ ] Orchestrator decides task decomposition — workers don't re-decompose
- [ ] Each worker has a single, typed output contract (use `subagent-output-contract` skill)
- [ ] Message routing is explicit: which agent reads which output
- [ ] State ownership is assigned: one writer per shared artifact
- [ ] Failure handling defined at coordination layer: if worker N fails, what fires?
- [ ] Consensus reduction defined for parallel tasks (swarm voting or designated reducer)

**Failure rate reference:** 41% in structured pipelines (clear role definitions);
87% in ad-hoc agent networks (roles determined at runtime). The gap is entirely
coordination defects — no difference in per-agent capability.

## RepRo: Review Prior Plan Before Next Action (arXiv:2606.14302, Jun 2026, Tier-2)

Before generating each next action in a multi-step task, inject a brief retrospective:
"Prior plan: X. What I did: Y. What happened: Z. Does my next action still make sense?"
Agents using RePro avoid re-committing the same mistake class across iterations.

This is currently Tier-2 (not implemented) because it requires a change at the session
loop entry point. However it can be applied MANUALLY as a prompt discipline: before each
new phase in a long task, write a one-sentence prior-plan review. Cost: ~50 tokens.
Benefit: prevents the most common failure mode where an agent commits to a wrong direction
early and elaborates on it for many turns without re-checking the original goal.

**Trigger for manual RePro:** use it whenever you've completed a phase and are about to
start a new one in the same session, especially if the prior phase surfaced unexpected results.

## Concurrency-1 Default Guardrail (SQLite Advisory Lock)

Cron-triggered agents can double-invoke if a previous run is slow (cron fires again while first run still active). Use a SQLite advisory lock — the same DB Hermes already uses for sessions — to enforce single-instance execution:

```python
import sqlite3, os, sys
db = sqlite3.connect(os.path.expanduser("~/.hermes/locks.db"))
db.execute("CREATE TABLE IF NOT EXISTS locks (agent TEXT PRIMARY KEY, ts TEXT)")
try:
    db.execute("INSERT INTO locks VALUES (?, datetime('now'))", (AGENT_NAME,))
    db.commit()
except sqlite3.IntegrityError:
    print(f"[SKIP] {AGENT_NAME} already running — exiting", flush=True)
    sys.exit(0)
try:
    run_agent()
finally:
    db.execute("DELETE FROM locks WHERE agent=?", (AGENT_NAME,))
    db.commit()
```

`INSERT OR FAIL` (unique constraint) is atomic in SQLite WAL mode. Lock is cleared on exit regardless of success/failure. No external dependencies. Source: sqlite-s3-agent-tutorial (Equational Applications, Aug 2026).

## Reasoning Integration (Aug-Sep 2026 findings)

These patterns from adaptive-agent-reasoning integrate directly into autonomous loops:

### Societies of Thought for Hard Agent Subtasks (arXiv:2601.10825)
Long-CoT gains in reasoning models come from internally simulating diverse perspectives
(different roles/expertise), not just longer chains. For hard agent subtasks, prompt an
internal 2-3 role debate within a single call before committing:
  "You are simultaneously a skeptic, an implementer, and a domain expert. Each role gives
  its assessment. A chair then reconciles them."
Cost: ~1.5x single call. Benefit: matches quality of 3-agent fan-out at a fraction of the
delegation overhead. Use for L2/L3 classification subtasks within the loop.

### Adaptive TTS Routing Inside Loops (arXiv:2408.03314, 2608.04001)
For each subtask in the loop, route TTS by first-pass difficulty:
  - If first short pass (300 tokens) produces confident output -> stop, use it
  - If uncertain or truncated -> GROW (sequential extension)
  - If math/code/planning with stakes -> BRANCH k=3 + DCR reconcile
Do not apply uniform max-token reasoning across the whole loop. The complexity
classifier script outputs the routing decision:
  python3 ~/.hermes/scripts/reasoning-complexity-classifier.py classify --task "<subtask>"

### DCR Reconcile for Parallel Subtask Merge (arXiv:2608.15303)
When the loop uses parallel workers (PRUNE or parallel delegate_task), merge outputs
using DCR rather than naive first-result-wins or manual prose merge:
  python3 ~/.hermes/scripts/dcr-reconcile.py check --candidates '<JSON>'
  python3 ~/.hermes/scripts/dcr-reconcile.py reconcile --candidates '<JSON>' --domain <math|code|planning|general>
  (--candidates is required; each object must have an "id" field or KeyError is raised)
Gate the Phase 2 reconcile call on actual disagreement (dcr check returns phase2_needed=true).
This saves reconcile cost when workers happen to agree.

### Role Relabeling in Iteration N+1 (arXiv:2606.05976)
In iterative loops, never ask the loop agent to critique its own prior output in-place.
Place the prior output into a tool_result or memory block before asking for critique.
This applies to all self-correction patterns in the loop, including re-review-on-failure.

## References

## Agent Topology Selection Evidence (agent-topology-research-2026.md, Jul 2026)

**Single vs. Multi-Agent decision rule (arXiv:2505.18286, UIUC):**
- SAS (single-agent) for short/well-scoped tasks with frontier models
- MAS required for structured operational tasks (incident response, RCA) — gap is qualitative:
  SAS: 1.7% actionable rate vs. MAS: 100%, 80× specificity, 140× correctness on 348 trials
- Hybrid routing (+1.1–12% accuracy, up to 88% cost reduction) beats committing to one mode

**Topology selection dominates model selection (AdaptOrch, arXiv:2602.16873):**
When models are within 3 MMLU points of each other, topology choice outperforms model choice.
Dynamic topology adaptation beats static single-topology by 12–23%.
Implication: routing architecture matters more than model upgrades at similar capability levels.

**AgentPrune — sparse topology vs. dense (arXiv:2410.02506, ICLR 2025):**
Dense agent graphs are wasteful. Pruning to sparse topology: $5.60 vs $43.70 dense (7.8× cheaper),
28–73% token reduction, +3.5–10.8% robustness vs adversarial inputs.
Prefer narrow, focused delegate_task calls over large fan-out swarms. Only add workers when
parallelism is genuine — each extra child has overhead.

**Self-MoA — same model ×N beats cross-model ensemble (arXiv:2502.00674, Princeton):**
+6.6% over cross-model MoA; same model as both proposer and aggregator.
Spawning N sonnet-4-6 workers beats mixing sonnet + haiku for reasoning quality.

Typed graph state management for long-horizon Hermes tasks. 0.94 normalized defense score
(+9.5%) on 100 Docker-based cyber ranges.

State graph (maps to Graphiti/SQLite):
- Nodes = milestones; edges = transitions; attributes = artifact refs to outputs
- Stage Router dispatches subagents based on current state node type
- Execution feedback updates state; validated effects stored as reusable experiences

Stage routing for delegate_task chains:
  Clarify (grill-me) → Plan (plan/isa) → Execute (claude-code) → Verify (verification-before-completion)
State transitions logged to SQLite; historical experiences retrieved to guide subsequent runs.

## Search-G1 — Retrieval Necessity Heuristic (arXiv 2608.07531)

Before each Hindsight memory lookup, probe whether context already suffices:
- Closed-book check: "Score 0-10 how well you can answer [query] from context alone."
  If >= 7: skip Hindsight retrieval; save ~one embedding lookup + API call.
- After retrieval: "Would your answer change if the retrieved memory were removed?"
  If no: cache the skip decision for similar future queries in this session.
Estimated: 20-30% reduction in Hindsight lookups on well-contextualized sessions.

## P³ — Joint Plan+Test Generation for Coding Subagents (arXiv 2608.09277)

Before coding: single Claude API call emitting {plan, test_scaffold} simultaneously.
Reduces API cost ~40% and wall-clock ~37% vs sequential plan-then-code pipeline.
Add to `isa` skill as a mandatory pre-step: spec → joint plan+test → implementation.

## Aug 2026 Additions

### Effort levels (claude-sonnet-5, claude-opus-5 only)
`effort: low | medium | high (default) | xhigh | max` in the API call.
- low: faster/cheaper, good for routing/classification subtasks
- high: default — balanced reasoning
- xhigh/max: extended thinking, significant extra latency + cost
Not available on claude-sonnet-4-6/opus-4-8 (silently ignored).
Hermes pattern: effort=low for tool-routing subtasks, high for synthesis, max only for ambiguous multi-step plans.

### Task budgets (beta)
Cap extended thinking via `budget_tokens` to prevent runaway costs in agentic loops:
```python
client.beta.messages.create(..., budget_tokens=8000, betas=["interleaved-thinking-2025-05-14"])
```
Set per-subtask budgets proportional to complexity; reset between iterations.

### Mid-conversation tool changes (beta: `mid-conversation-tool-changes-2026-07-01`)
Add/remove tools mid-session without editing the original `tools` array — preserves prompt cache:
```python
client.beta.messages.create(..., betas=["mid-conversation-tool-changes-2026-07-01"],
  extra_body={"tool_additions": [...], "tool_removals": ["tool_name"]})
```
Pattern: inject search tools only when retrieval needed, drop risky tools after a checkpoint.

### Thought-action decoupling pathology (CoffeeBench, Sakana AI × KPMG Azusa, 2026)
Source: https://sakana.ai/coffee-bench/ | arXiv: 2606.16613
Agents reason correctly but *fail to act* — long context causes model to lose the thread
between reasoning and tool call.
Mitigations:
- Keep reasoning + action in the same assistant turn (no multi-turn reasoning without tool calls)
- After N reasoning steps, force a concrete tool call or explicit "no-op" acknowledgement
- Re-anchor long loops: repeat current goal at top of each iteration prompt

### Initializer/coding agent pattern
First session: write `~/.hermes/agent-progress.txt` (goal, step, blockers) +
`feature_list.json` (planned items + completion status).
Subsequent sessions: read both before acting — stateful multi-session work without
relying on compacted session history.

### LLM+RL policy synergy (JSAI survey, 2026 — Japanese AI Society)
Source: https://www.jstage.jst.go.jp/article/tjsai/41/4/41_41-4_C-P102/_article/-char/en
LLMs as policy generators in actor-critic RL loops: LLM provides initial action proposals,
critic refines via reward signal. Hermes relevance: track per-skill/per-agent success rates
as a reward signal to weight future routing decisions (see hermes-acp-routing skill).

### Fast/Slow ReAct — Event-Triggered Deliberation (arXiv:2608.09816, Aug 2026)
Separate fast reactive loop (cheap, low-latency) from slow deliberative loop (expensive,
triggered only on high-uncertainty events). Fast loop handles routine tool calls; slow loop
kicks in when confidence < threshold, novel error type, or cumulative cost exceeds budget.
Hermes pattern:
- Route tool-result parsing and trivial next-step choices through a cheaper/faster path
  (effort=low on sonnet-4-6, or a scripted rule)
- Trigger full LLM reasoning only for: unexpected error codes, ambiguous results, plan
  contradictions, or explicit "deliberation trigger" markers in tool output
- Implement as a simple sentinel: if `tool_result.startswith("ERROR") or "unexpected" in
  tool_result.lower()` → force a reasoning step before next action

### Async Computer-Use Failure Mode (Anthropic Engineering Blog, Aug 2026)
Source: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
Production finding: async computer-use loops fail silently when:
1. UI state diverges from expected (modal dialog blocks, page redirect mid-action)
2. No timeout/recovery: agent waits indefinitely on a stale element ref
3. Tool call rate limit hits mid-sequence, leaving the UI in a partial state
Mitigations:
- After every computer_use action, verify state with a fresh capture before next action
- Set explicit timeouts (30s max per interaction step)
- On unexpected state: emit a structured error and restart from last known good checkpoint
- Never batch more than 3 computer_use steps without an intermediate verify capture

### DREAM — L0/L1/L2 Intent Hierarchy for Memory (arXiv:2608.09408, Aug 2026)
Decompose task intent into 3 levels before deciding what to store:
- L0 Immediate intent: what the user is asking right now (ephemeral, don't persist)
- L1 Session intent: the goal for this conversation (persist to session notes, not MEMORY.md)
- L2 Long-term intent: stable preferences, patterns, identity (persist to MEMORY.md / Hindsight)
Hermes application: before calling memory() or hindsight_retain(), classify the fact at L0/L1/L2.
Only L2 facts go to persistent memory. L1 facts go to session_search context. L0 facts are acted
on immediately and discarded. Prevents MEMORY.md bloat from session-specific details.

### 10-Category Failure Taxonomy (arXiv:2608.09939)
Empirical classification of autonomous agent failures into 10 categories: tool hallucination,
context truncation, goal drift, over-delegation, under-delegation, loop stall, permission error,
partial success treated as complete, cascade failure, and state corruption.
**Hermes loop design:** Before any unattended agent run, enumerate which of the 10 failure modes
apply to this task. For each applicable mode, define the detection heuristic and recovery action.
Loop stall (mode 6): detect via iteration cap + no-progress sentinel. Goal drift (mode 3): compare
current subgoal against original goal every N iterations. Partial success (mode 8): require explicit
completion evidence, not just absence of error output.

- `references/nanochat-autoresearch-patterns.md` — Karpathy's nanochat loop (Mar 2026): concrete repo structure, agent loop shape, critical success factors, and what-not-to-do pitfalls. Start here for a real working example.
- `references/agent-topology-research-2026.md` — Evidence base: 29 papers on topology selection and token optimization (2024–2026). Cite this for specific metrics and arXiv IDs.

**Ark Taxonomy note (arXiv:2608.10934):** Context Window Manager is a first-class loop
component — treat context hygiene as an explicit phase at each iteration boundary, not a
runtime side effect. Checklist for any new subagent design: planner, context manager, tool
dispatcher, memory retrieval, verifier, and orchestrator all explicitly covered.

## Sweep 29 Additions (batch 2)

### Dot Reflex: 10-Decision Outer Recovery Controller (github:usedotai/dot-reflex) ★ HIGH

Separate outer controller (not the worker) with 10 explicit decisions:
continue / verify / retry / replan / rollback / branch / switch-model / ask-human / stop-ok / stop-fail

Each decision is a named exit from the controller loop — no implicit continuation.
The controller receives a compact trajectory JSON (not full transcript) and returns one decision.
**Hermes pattern:** The controller role should be a cheap model (haiku) reading a structured
summary. Workers that hit `stop-fail` should write a `DART-SD breakpoint` annotation so the
next run knows where the trajectory broke (see DART-SD arXiv:2608.18524 below).

### DART-SD: Localize the Breakpoint, Distill Recovery Only (arXiv:2608.18524) ★ HIGH

Never SFT or replay full failed trajectories — error propagation is the dominant failure mode
(ACL 2026 "How Memory Management Impacts LLM Agents"). DART-SD:
1. Localize the Critical Topological Breakpoint (CTB) — exact step where trajectory diverged
2. Distill recovery steps only (not the full rollout)
3. At inference: retrieve recovery references at CTB instead of restarting from step 1

**Hermes/stalled-session-recovery:** When a session fails mid-task, annotate the last
successful step as the CTB. Next run: inject CTB annotation + recovery pattern, resume from CTB.

## Sweep 32 Implementation Recipes (Sep 2026)

### Script Locations

The three Sweep 32 helper scripts live in THIS skill's scripts/ directory (agent-writable):

  Loop contract:   ~/.hermes/skills/autonomous-ai-agents/autonomous-agent-loop-design/scripts/loop-contract-init.py
  DAG tracker:     ~/.hermes/skills/autonomous-ai-agents/autonomous-agent-loop-design/scripts/dag-task-tracker.py
  Memory gate:     ~/.hermes/skills/autonomous-ai-agents/autonomous-agent-loop-design/scripts/memory-health-gate.py

NOTE: 0-byte stubs exist at ~/.hermes/scripts/{loop-contract-init,dag-task-tracker,memory-health-gate}.py
(root-owned, empty). Do NOT invoke those paths. If you see exit 0 with no output, you hit a stub.
User action required to remove: sudo rm ~/.hermes/scripts/loop-contract-init.py dag-task-tracker.py memory-health-gate.py

### Loop Contract Init — Concrete Pattern

Before dispatching any worker subagent, write a Loop Contract to disk:

```bash
# ~/.hermes/scripts/loop-contract-init.py writes a hash-locked contract
python ~/.hermes/scripts/loop-contract-init.py \
  --objective "Implement feature X" \
  --verify "pytest tests/test_x.py passes" \
  --stop_if "3 consecutive failures on same tool" \
  --budget_turns 50 \
  --budget_delegations 8 \
  --output ~/.hermes/cache/loop-harness/contracts/<task-id>.json
```

Contract JSON schema:
```json
{
  "objective": "string — immutable task description",
  "verify": "string — completion criterion (verifiable artifact)",
  "stop_if": "string — early-stop conditions",
  "budget_turns": 50,
  "budget_delegations": 8,
  "hash": "sha256 of objective+verify+stop_if — worker cannot change these"
}
```

Worker receives contract path in context; harness re-hashes at end to detect scope drift.

### DAG Task Tracker — Feature List Pattern

For multi-step tasks, write a `feature_list.json` before starting:

```json
{
  "tasks": [
    {"id": "T1", "description": "...", "deps": [], "passed": false, "regression_obligations": []},
    {"id": "T2", "description": "...", "deps": ["T1"], "passed": false, "regression_obligations": ["T1"]}
  ]
}
```

Rules:
- After completing T2, re-run T1's check (regression_obligation)
- A task is DONE only when it passes AND all its regression_obligations still pass
- `passed: true` is provisional until the dependent task's regression check runs

### Rejected Routes — Dead-End Store

For multi-session autonomous loops, initialize before starting:
```bash
mkdir -p ~/.hermes/cache/rejected-routes
touch ~/.hermes/cache/rejected-routes/<project>.jsonl
```

At loop start, read this file and skip any approach already marked as dead-end:
```python
import json, pathlib
rejected = [json.loads(l) for l in pathlib.Path('~/.hermes/cache/rejected-routes/<project>.jsonl').expanduser().read_text().splitlines() if l]
# Before exploring approach X: if any r['approach'] == X, skip it
```

At loop end (on failure), append:
```json
{"approach": "string", "reason": "string", "ts": "ISO8601"}
```

## Sweep 32 Additions (Sep 2026)

### LoopsBench: DAG Task Completion with Regression Tracking (arXiv:2608.00267) ★ HIGH

Frontier loops still fail long-horizon DAG tasks. 25% resolution rate with best config (Opus-4.7 + outer continuation). Regression events are the root cause: a completed node fails again after later writes.

**Hermes pattern:**
- Pre-launch: write `feature_list.json` with `{"id": "F1", "deps": ["F2"], "passed": false, "regression_check": true}`
- After each node completes, re-run all predecessor nodes as regression check before advancing
- `agent.verify_on_stop: auto` handles final pass; add mid-task regression gates at DAG checkpoints
- Add to Pre-launch checklist: `[ ] DAG structure written to feature_list.json with deps[] and regression_check fields`

### LoopArena: Controller/Worker Separation + Loop Contracts (arXiv:2608.28281) ★ HIGH

LoopArena benchmark: 24.69% Strict Success Rate (SSR). Type II vs Type III ranking agreement: Spearman ρ=0.9747. Controller-worker split enables model tiering (cheap model executes, expensive model decides) — the "64.4%" figure refers to inference cost reduction via tiering, not loop success improvement.

Key: worker cannot rewrite the Loop Contract; parent scores from artifact (diff, test output), not prose.

**Loop Contract (add to ralph-loops and any multi-turn autonomous loop):**
```json
{
  "objective": "<immutable from user>",
  "verify": "pytest tests/ || hermes doctor",
  "stop_if": "all passes:true in feature_list.json",
  "budget": {"max_iterations": 20, "max_tokens": 50000}
}
```
- Hash-lock the contract at loop start — agent cannot change scope mid-run
- Parent scores progress from git diff / test output, NOT worker prose
- Worker self-reported success without verifiable artifact = ignored
- Store `(summary, contract, outcome)` tuples for cheap classifier before next worker spend

Add to Pre-launch checklist:
- `[ ] Loop Contract written and hash-locked before first worker dispatch`
- `[ ] Worker receives contract in goal field; cannot modify it`

### ExecCritic: Learn to Test, Test to Improve (arXiv:2609.09133) ★ HIGH

Same-trajectory test+patch creates false confidence. Role separation prevents the same agent evaluating its own work.

**What the paper actually shows:** Naive untrained Test agent *lowers* resolve rate (61.2% → 57.3%). The 72.6% figure requires two role-specific RL post-trained Qwen agents — Hermes does not have this. The Hermes value is **false-confidence prevention**, not a score gain.

**Pattern for hermes-coding-review-loop:**
- Phase 1: Test subagent writes tests, commits them
- Phase 2: Harness freezes test dir (tool-auth-gate effect ceiling: test files → read-only)
- Phase 3: Repair subagent edits source ONLY; any attempt to edit test files is denied
- Adversarial reviewer (gpt-5.6-sol) stays completely off the Repair path

Add to Pre-launch checklist:
- `[ ] For coding tasks: Test agent committed before Repair agent starts; test files locked`

### Governance Decay: Pin Constraints Outside Compaction (arXiv:2606.22528) ★ HIGH

After compaction, dropped constraints cause 30-59% violation rate. Fix: re-inject ~47 pinned constraint tokens after every compact event. The key is that constraints must live in the SYSTEM PROMPT or the Hermes MEMORY.md — wherever the compressor is instructed NOT to discard.

**Critical constraint:** MEMORY.md is 2046/2200 chars (92% full) and write-gated. New constraints must replace stale entries — do not append blindly. Use the memory tool's `replace` action, not `add`.

- After any compact event, force one `verify_on_stop` pass to check constraint survival
- If post-compact retrieval calls spike (read_file/session_search dominate first 3 turns), log `REACQUISITION_SPIKE` and consolidate the retrieved fact into MEMORY.md by replacing a less-used entry
- `rr_scorer` must never demote constraint/policy text (treat as infinite retain)
- `protect_last_n: 32` is NOT pinning — it preserves recency, not constraint type

**Do NOT** write to MEMORY.md in a loop (file is nearly full). Pin only the most critical constraints; let session_search serve as the recovery mechanism for secondary ones.

Add to Pre-launch checklist:
- `[ ] Critical constraints written to MEMORY.md or system prompt, not only in tool results`
- `[ ] Post-compact reacquisition check: if retrieval dominates first 3 turns, pin the fact by replacing a stale MEMORY.md entry`

### Skill Retrieval: Graph for Composition, Hybrid for Lookup (arXiv:2608.02356, 2608.06196, 2609.08228)

Three findings on skill retrieval that together define the correct architecture:

1. **SkillTrace (2608.02356):** Graph is for finding the executable skill CLOSURE, not primary retrieval. After description match, use BFS over `depends_on:` edges to find all skills needed. Do NOT use a separate `requires:` field — skill-graph-walk.py ignores it.
2. **2608.06196:** Hybrid lexical+dense hit@5=73.5%. Typed LLM graphs are -11.2pp vs ranker. Never replace hybrid retrieval with graph-only.
3. **SE-GoS (2609.08228):** Evolve the skill graph from execution traces. One round: 52.4%→59.4% reward; round 3 overfits to 54.0% — weekly, not daily.

**Hermes application:**
- Use `depends_on:` frontmatter (not `requires:` — skill-graph-walk.py ignores `requires:`)
- `skill-graph-walk.py` BFS over `depends_on` after initial match
- Live cron `se-gos-weekly` (670a8904edf4, Sundays 05:00): `se-gos-graphiti-bridge.py` reads yield metrics and writes Graphiti `[se-gos]` reinforce/decay episodes
- `skill-yield-tracker.py` does NOT write Graphiti edges itself — the bridge does. Tracker must still record invocations or the cron is a no-op

### Memory Health Gate + Dead-End Store (arXiv:2609.05510) ★ HIGH

Month-long session: 85 memory failures; 84 in first 3 weeks, 1 after health gate. Mandatory session-start memory check.

**Before any long autonomous run:**
1. Verify Hindsight/Graphiti provider is up
2. Check `graphiti_warn_nodes: 40000` threshold
3. Check SQLite WAL status (`state-wal-checkpoint.py`)
4. Write dead-ends to `~/.hermes/cache/rejected-routes/<project>.jsonl` — read at loop start to avoid re-exploring known failures

Add to Pre-launch checklist:
- `[ ] Memory health gate: provider up, Graphiti below warn_nodes, WAL ok`
- `[ ] Rejected-routes file initialized at ~/.hermes/cache/rejected-routes/<project>.jsonl`

Sweep 33 write/retrieve checklist (all 12 findings): `skill_view(name='autonomous-agent-loop-design', file_path='references/sweep33-memory-patterns.md')`.
Architecture (compaction, dual-layer, permissions): `harness-first-agent-design` § Sweep 33 Memory Architecture.

### Sweep 33 — Memory Health Gate extensions <!-- why: verifier bits, revocation, query-scoped suppression, and write triaging close the retrieval/poisoning holes the session-start gate does not cover -->

`mcp__graphiti__add_memory` has **no structured metadata argument**. Encode every field below in the episode *text*. `memory-health-gate.py` remains the session-start provider/WAL/node-count gate; the write path it protects must stamp these bits before add.

**MemGuard — persist verifier bits (arXiv:2608.21867).** Unreliable admission + drift washes out verifier signals unless they live on the stored episode. On every add, include `verified: true|false` and `confidence: <0-1>`. Retrieval: do not use `verified: false` for task-critical decisions.

**Revocation at retrieval (arXiv:2609.08258).** Five tested memory systems leave invalidated/superseded facts retrievable. After `mcp__graphiti__search_memory_facts`, drop any hit whose episode text has `invalidated: true` or `superseded_by:` set. Do not act on revoked facts even if ranked high.

**MeClear — query-scoped suppression (arXiv:2609.09115).** Clearing negative-utility memories recovers 82.3% of tasks (paper result); non-destructive suppression is enough. Before injecting hits, use search ranking as relevance. Suppress (do **not** delete) facts with low relevance to the current query. The threshold of 0.2 is a **local heuristic, not a paper result** — tune per task type.

**MemSentry — write triage (arXiv:2609.08747).** Content screening misses poisoning. Before add: (a) source trust — user turn=1.0, known-API tool=0.8, web=0.3; (b) semantic risk — contradiction vs a high-confidence node; (c) if `trust < 0.5` AND `risk > 0.7`, still add but with `tag: unverified` and exclude that tag from task-critical retrieval.

Add to Pre-launch checklist:
- `[ ] Graphiti writes encode verified+confidence (+ provenance) in episode text`
- `[ ] Retrieval drops invalidated/superseded and score<0.2; unverified excluded from task-critical inject`

## Sweep 32 Pre-launch checklist additions

The following items are added to the Quick Checklist (append after existing items):

- `[ ] DAG structure written to feature_list.json with deps[] and regression_check fields (for multi-step tasks)`
- `[ ] Loop Contract written and hash-locked; worker cannot modify it`
- `[ ] For coding tasks: Test agent committed before Repair agent starts; test files locked`
- `[ ] Critical constraints in MEMORY.md or system prompt, not only in tool results`
- `[ ] Memory health gate: provider up, Graphiti below warn_nodes, WAL ok`
- `[ ] Rejected-routes file initialized for autonomous multi-session loops`
- `[ ] Post-compact reacquisition monitored: retrieval spike = REACQUISITION_SPIKE, pin the fact`



From github:Framework-Drift/governed-pass — a 4d8h multi-day autonomous research run
that **refused to self-certify** (`METHOD_NEEDS_REPAIR`). Key lessons:
- Hash-lock the task contract at start — agent cannot silently change scope
- Agreement ≠ independence: reviewers sharing a spec will find the same bugs
- Adversarial review must use heterogeneous instruments (different model families)
- Disposition vocabulary must be closed (no free-form pass/fail improvisation)

## Sweep 33 Additions (Sep 2026) — Delegation integrity, working memory architecture

### Recuris — Experiential vs working memory split (arXiv:2608.24876) ★ HIGH <!-- why: summarizing working scratch into Graphiti mixes ephemeral task state with durable facts -->

Splitting experiential vs working memory and evolving both: +17.8 on GPT-5.6 Sol tasks, Claude Opus 5 τ-bench 87.9% (+15.6pp), +32.2 on longest tasks.

**Hermes pattern:** Graphiti = experiential memory (persistent cross-session facts; `group_id` separates profiles). Working memory = a small typed scratch block rewritten each compaction, NOT summarized into Graphiti. Separate their compaction policies.

### Procedural Graphs (arXiv:2609.09153) ★ HIGH <!-- why: factual-only Graphiti misses what-to-do-next; unvalidated topology edits regress -->

Procedure–relation–procedure overlay in Graphiti beats factual-only memory. Self-evolution from successful vs failed traces matches or beats hand-designed graphs.

**Hermes pattern:** In Graphiti, store procedural nodes (what-to-do-next) as a separate overlay from factual nodes. Commit procedural topology edits only after held-out validation confirms no regression.

### AutoFyn Expert Iteration (arXiv:2609.05446) ★ HIGH <!-- why: carrying the full conversation across long-horizon rounds poisons the next round; artifacts carry verifier reward instead -->

Frozen-model expert iteration via persistent state (files + reports + repo) + task-grounded verifier. Every model with headroom beats its provider's coding agent on 2026 IMO. Top Spider 2.0 dbt agent.

**Hermes pattern:** Between long-horizon task rounds, start a fresh Hermes session and reintroduce only the artifact files (reports, repo state) — not the full conversation. Distill verifier reward into those artifacts, not into prompt text.

## Sweep 33 (Sep 2026)

### RelLift95/PRISM — Harness-Selection Lift (arXiv:2609.05736) ★ HIGH <!-- why: harness routing policy, not prompting, is the dominant recovery lever for long-horizon failures -->
Finding: RelLift95(B) is a conservative held-out harness-selection benchmark. PRISM routes repairs to prompt vs tool-boundary middleware. Reported mean lifts: 14.2pp / 14.9pp / 10.1pp across three task families. (Stats "recovers 31–44% of forgotten commitments" and "0/12 ablations beat live steering" were NOT in the abstract — do not cite.)
Hermes pattern: In long-horizon loops, harness routing policy (which tool boundary to use for repair) matters more than prompt rewriting. When a commitment is dropped, route the repair to a structured tool call (e.g. todo_list update) rather than a prompt re-statement. Track which repair routes recover most commitments.

### SkillDreamer (arXiv:2609.01642) ★ HIGH <!-- why: prospective skill inference before retrieval closes the query-skill misalignment gap -->
Finding: SkillDreamer addresses Query–Skill Misalignment (QSM) by inferring what capabilities a task needs, generating pseudo-skills, then retrieving from those. (Stat "+14.2 success rate" and "loading only the predicted path" were NOT in the abstract — do not cite.)
Hermes pattern: Before loading skills for a complex task, infer what capability families the task requires ("this task needs web-search + code-execution + file-write"). Use those inferences to guide skill retrieval queries rather than using the raw task description as the retrieval query. Do not load the full skill library.
