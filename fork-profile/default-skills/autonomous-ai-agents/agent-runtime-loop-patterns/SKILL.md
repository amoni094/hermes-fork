---
name: agent-runtime-loop-patterns
description: "Use when tuning per-turn/per-tool guardrails, retry logic, or self-correction in an existing agent loop. Covers tool schema, MCP context, failure recovery. Not for greenfield harness architecture (use harness-first-agent-design). For loop architecture/design use autonomous-agent-loop-design."
version: 1.7.1
triggers:
  - tuning existing agent loop guardrails or failure recovery logic
  - tuning tool selection, schema efficiency, or MCP tool context management
  - multi-turn conversation state management or context ceiling problems
  - parallel tool call batching or grouping strategies
  - agent self-correction, reflection, or repair patterns
  - "how many tools should I expose to the agent"
  - "my agent is hitting a context ceiling"
  - "agent keeps retrying the same failed approach"
  - "how do I make agent self-correction work"
  - tool schema eviction or MCP context management
related_skills:
  - autonomous-agent-loop-design
  - harness-first-agent-design
  - hermes-context-hygiene
  - hermes-cron-and-agents
  - claude-routing-hierarchy
  - trajectory-risk-guardrail
  - stalled-session-recovery
  - hermes-context-budgeting
  - browser-agent-ops
  - self-improve-agent
---

# Agent Runtime Loop Patterns

Research-grounded patterns for agent loop design, tool use efficiency, state management, and self-correction. Findings from 2025–2026 arXiv papers, with concrete Hermes config/code implications.

See `references/agent-runtime-research-2025-2026.md` for the full evidence base (10+ papers with quantified results, non-English sources, and community practitioner reports).

---

## 1. Loop Guardrails & Failure Recovery

### Phantom Guardrail Problem (arXiv:2607.13083, Jul 2026)

Self-improving harnesses that read failing episodes and propose scaffold edits **hallucinate failures in 25% of runs** and install permanent guardrails against them.

**Three conditions that cause phantom guardrails (all three must co-occur):**
1. A rule-shaped pattern in the input
2. An open-ended rule set (not closed/enumerated)
3. An instruction that *presupposes* failures exist

Remove any one → fabrication disappears. Inside an add-only accept loop, phantom guardrails re-enter even without condition 3 — the loop's "keep adding" role supplies the presupposition.

**Standard "suppression-only" acceptance cannot detect phantom guardrails** because a phantom guardrail changes no true outcome and cannot improve an already-perfect suppression score.

**Hermes pattern:** Fixed guardrail thresholds (warn at 2 exact failures / 3 same-tool failures) are safer than dynamic adaptive thresholds. If ever implementing harness self-optimization:
- Require ≥1 verified true-positive suppression before accepting a new guardrail
- Use delete-allowed loops, not add-only loops
- Test proposed guardrails against clean "featureless" input before accepting

### Typed Failure Memory: MERIT Pattern (arXiv:2608.05906, Aug 2026)

Maintaining a **dual-polarity failure store** (successful repairs + failed repair directions), typed by failure category, improves iterative repair accuracy by 3–3.5pp without retraining.

**Key mechanics:**
- 5–7 failure type categories (auth/schema/timeout/rate-limit/parse/permission/unknown)
- Coarse failure-type classifier conditions retrieval before each repair attempt
- **Negative memory** (what NOT to retry) is as important as positive corrections
- Schema-local experience gives the most consistent gain

**Hermes pattern:** When a tool fails and `api_max_retries=1` triggers, the retry record should include: failure_type, attempts_tried, resolution. Reuse within a session to avoid cycling through already-failed repairs.

**Retry layers — do not mix the numbers:**
1. **Transport** — `api_max_retries`: automatic re-issue of the *same* call. Keep at 1.
2. **Class-based** — `retry-budget-guard.py` (TRANSIENT / RESOURCE / SEMANTIC / AUTH / FATAL). Only after classifying the error. Details: `references/python-runtime-pitfalls-aug2026.md`.
3. **Loop** — same tool + same args ≥3 → RETRY_LOOP / LivePlan / circuit-breaker Rung 1. That 3 is a *switch/steer trigger*, not "retry three more times".
Phantom guardrail warns at 2 exact failures / 3 same-tool failures — same loop layer, not a fourth budget.

---

### Bifurcation / Critical-Slowing-Down Detector (Strogatz Ch 3)

Near a saddle-node bifurcation, a dynamical system exhibits **critical slowing down**: recovery time grows as (µ_c − µ)^{-1/2} before the stable fixed point annihilates. Empirically: latency and variance both increase before failure, not after.

**Agent-loop translation:** when a tool enters a degradation regime, its response latency escalates geometrically. Waiting for outright failure wastes time; the *onset signature* (geometric latency growth) is detectable earlier.

**Rule (tool-call latency bifurcation guard):**
```
if len(tool_latencies) >= 3:
    ratios = [tool_latencies[i] / tool_latencies[i-1]
              for i in range(len(tool_latencies)-2, len(tool_latencies))]
    geom_mean_ratio = (ratios[0] * ratios[1]) ** 0.5
    if geom_mean_ratio > 1.5:  # each call taking 50%+ longer than last
        warn("Bifurcation signal: tool latency escalating geometrically; switch tool or escalate")
        do_not_retry_same_call()
```

**Threshold:** geometric mean ratio > 1.5 over 2 consecutive pairs (i.e., 3 calls). This is the signature of critical slowing down, not random variance. Single-outlier slowness does NOT trigger.

**Why not just wait for failure?** At the saddle-node, the stable fixed point disappears — after bifurcation there is no nearby attractor to converge to. Retrying into a bifurcated regime does not recover. The Lyapunov exponent for the latency series goes positive before success probability reaches zero.

**Composability:** apply Inertia Pattern AFTER this guard — if a bifurcation signal fires, complete in-flight sibling tasks to their boundary, THEN switch the failing tool.

### Inertia Pattern: Complete In-Flight Transitions Before Recovery (Cordis, Aug 2026)

Source: Cordis §4.3.3 + §4.4, Shi/Zhang/Cui (Peking University + DeepSeek-AI, Aug 2026).

**Principle:** A transition in progress runs to completion before the system responds to a
dependency state change. Recovery retries that fire before an in-flight transition settles
create partial-write corruption in shared state (memory, files, config).

**Pattern:**
1. Dependency failure detected mid-run → flag it, do NOT re-dispatch immediately.
2. All in-flight sibling tasks run to their current iteration boundary (checkpoint).
3. Only after all in-flight work reaches a stable state does the orchestrator evaluate
   the new dependency state and decide on retry vs escalate.

**When to skip inertia:** pure read-only tasks (search, extract) with no shared write
state may be cancelled and retried immediately — no partial-write risk.

**Contrast with MERIT pattern (above):** MERIT classifies failure types for better retry
direction. Inertia determines WHEN to retry. They compose: apply inertia to determine the
retry window, then use MERIT to pick the correct retry strategy within that window.

---

## 2. Tool Selection & Schema Efficiency

### Tool Schema Eviction: MemTool Pattern (arXiv:2507.21428, Jul 2025)

Tool schema eviction is **more impactful than message compression** for multi-turn agents. Fixed context windows are the primary multi-turn bottleneck.

**Results on 13+ LLMs, ScaleMCP benchmark (100 consecutive interactions):**
- Reasoning LLMs (autonomous eviction): 90–94% tool removal efficiency (3-window average)
- Medium-sized models (autonomous eviction): 0–60% — need deterministic eviction policy
- Hybrid mode: best task completion + effective removal combined

**Hermes pattern:** Message compression (`micro_compact`) is a separate layer from tool-schema eviction. Prefer **event-aligned** compaction at tool-call commit boundaries (see CommitKV in `references/extended-runtime-patterns.md`) over a fixed every-N-turns rule. For many-MCP-tool sessions: track relevance decay per tool per turn and evict stale tool schemas independently of message compression. Smaller models need deterministic eviction; larger models can use autonomous eviction.

### HyperTool: Code-Block Batching (arXiv:2606.13663, Jun 2026)

Step-wise atomic tool calls create an **execution-granularity mismatch**: deterministic sub-workflows unfolded into repeated model-visible decisions, consuming context and forcing low-level dataflow management in the reasoning trace.

**Results on MCP-Universe benchmark:**
- Qwen3-32B: 15.69% → 35.29% accuracy (+125% relative)
- Qwen3-8B: 9.93% → 33.33% accuracy (+235% relative)
- Surpasses GPT-OSS and Kimi-k2.5

**Hermes pattern:** For deterministic sequential tool sub-workflows (read-file → parse → write-file), wrap as a single compound tool call. Reduces context inflation AND removes unnecessary decision overhead at each intermediate step. Goes beyond parallel batching: covers sequential dependencies too.

### Type-Affinity Fusion: LLM-Tool Compiler (arXiv:2405.17438, May 2024)

Runtime fusion of **similar-type** tool operations into a single unified function before presenting to the LLM.

**Results on large-scale Copilot platform:** 4× more parallel calls; −40% token cost; −12% latency.

**Hermes pattern:** When scheduling parallel calls, group same-type tools together and present them as a fused call rather than individual operations.

### Per-Step Context Narrowing: AOrchestra (arXiv:2602.03786, Feb 2026, Chinese institutions)

Agent abstracted as `(Instruction, Context, Tools, Model)` tuple, concretized per step. Curates task-relevant context and selects tools at each step rather than forwarding wholesale.

**Results:** +16.28% relative improvement over strongest baseline on GAIA/SWE-Bench/Terminal-Bench.

**Hermes pattern:** Context forwarded to delegated subagents should be narrowed per sub-task. Passing full conversation history directly degrades performance. Scope context slices to what the subagent's specific task needs.

### Fewer Tools Often Beat More: Sketch.dev Production Finding (HN, May 2025)

A 9-line agent loop with a **single `bash` tool** is surprisingly effective for a wide class of tasks — no tool selection overhead, no schema management complexity.

**Hermes pattern:** Reduce active tool surface for simpler tasks. Tool descriptions should explain *when not to use* a tool to reduce false-positive selection.

### SkillTrace: Dependency-Aware Skill Graph Traversal (arXiv:2608.02356, Aug 2026) ⭐ CODE

Flat embedding search for skill selection misses **skill dependencies** — skill A retrieved for step 3 may require skill B that wasn't retrieved for step 1. SkillTrace builds a three-level graph: (1) decompose task into sub-queries, (2) embed sub-queries against skill library, (3) propagate skill dependency edges to auto-include required prerequisites.

SOTA: 53.17% SkillsBench, 91.43% ALFWorld.

**Hermes implementation:** skill prerequisite edges belong in `hermes-agent-skill-authoring` / `hermes-semantic-skill-routing`. Do not invent a `requires:` frontmatter field from this skill. At load time, resolve declared dependencies so skill A is not applied without B's pitfalls.

### Practitioner-Confirmed Tool Reliability Fixes (r/LocalLLaMA Aug 2026, production)

Independent from papers — these are field-discovered by practitioners shipping agent products:

**Idempotency markers (confirmed ~80% reduction in duplicate writes):** Add "[IDEMPOTENT: safe to retry]" or "[DESTRUCTIVE: verify before calling]" inline in tool descriptions. Low implementation cost; agents read and respect this. The most common cause of silent data corruption in production loops.

**Structured error returns over exception traces:** When a tool fails, return `{"error": "reason", "suggested_fix": "..."}` in the tool result instead of raising an exception. Models recover from structured error returns far more reliably. Exception stack traces are optimized for human reading, not LLM recovery.

**Dry-run mode for destructive tools:** Add `dry_run: bool` parameter to any tool with side effects. Agents learn to dry-run first, then execute. Catches ~90% of destructive mistakes before they happen.

**Retry cap at 3 with exponential backoff + escalation:** After 3 *loop-layer* failures (same tool / same args), switch or escalate — see Retry layers above. Two is too few for transients; four or more wastes budget. This is not `api_max_retries` and not the 5-class transport budget.

**Dynamic tool injection (most-impactful harness fix, independently confirmed):** Practitioners report >12 tools in the schema causes noticeable degradation in tool-selection accuracy. Present only the tools relevant to the current task phase. This was the most-upvoted practical tip across multiple production communities in Aug 2026 — confirmed by multiple independent deployments, not just the Aethelgard paper. It is first-class production advice, not an optimization.

### Canary Tools: 6-Type Tool Selection Failure Taxonomy (arXiv:2608.04719, Aug 2026) ⭐ CODE

CSR (Canary Susceptibility Rate) varies **36	imes across models**. Six failure types:
| Type | Description | Most affected |
|---|---|---|
| Semantic decoys | Similar-sounding tool with different purpose | Small models |
| Parameter traps | Same tool name but wrong param signature | Small models |
| Capability mirages | Tool described as able to do X but cannot | Frontier models |
| Prerequisite blindness | Tool requires prior tool not selected | All |
| Temporal decoys | Tool only valid in certain system states | Medium |
| Granularity traps | Too-coarse or too-fine tool for task | All |

Re-measure CSR on the *live* model; do not hard-code a winner. Capability mirages uniquely trap frontier models.

**Hermes pattern:** Use the 6-type taxonomy as a test checklist for every new tool/MCP schema. During development: plant one capability mirage and one prerequisite blindness canary and verify the model catches them. Required: explicit `when_not_to_use:` in tool descriptions (addresses granularity traps). Cross-ref: `hermes-skillspector-guard-maintenance` for the safety test harness.

### Tool Distribution-Shift Triage Protocol (arXiv:2609.00467, Sweep 31)

Tool-using agents show 18-31% performance drop when tool availability, schema, or SLA changes without re-calibration. The failure mode is silent: the agent retries the broken configuration rather than detecting the structural change.

**Four shift types and detection signals:**
1. **Tool unavailable** → first call returns connection error or 404; do not retry > 1 time
2. **Schema change** → error message references unexpected field names vs prior successful calls; flag and pause
3. **New tool available** → if a task fails with current tool AND a new tool was added this session, explicitly check its capabilities before deciding it can't help
4. **Latency SLA breach** → applies Bifurcation Guard (geometric mean ratio > 1.5, see above)

**Correlated-shift signal (2+ tools degrading simultaneously):**
```
if failed_tools_this_session >= 2:
    treat_as_environment_shift = True  # NOT independent failures
    pause_and_report("Correlated tool degradation: possible environment/API change")
    do_not_dispatch_new_subagents_until_resolved()
```

**Switch-not-retry rule:** if retry count on a specific tool reaches 2 in a session AND an alternative tool exists for the same function, switch to the alternative. Do NOT retry a third time on the original tool in the same session without user confirmation.

**Schema change detection (lightweight):** compare the keys in the error response to the keys seen in the last successful response. If new keys appear or prior keys are absent, log `schema_shift_suspected` and avoid assuming prior call patterns work.

Tool availability, schemas, and SLAs are not stationary. Treat a change in the tool surface as a **policy distribution shift**, not as a one-off error.

Four shift types:
1. **Tool unavailable** — previously callable tool missing from schema / MCP / auth gate
2. **Schema change** — same tool name, different parameters or return shape
3. **New-tool available** — a better or replacement tool appeared mid-session
4. **SLA latency degradation** — tool still works but latency/success diverges from the session baseline

**Rules:**
- Track in-session tool latency estimate: note roughly when each tool call starts and ends (agent-estimated via turn count, not a precise logger). If the same tool takes noticeably longer or fails more in turns N through N+5 than it did in turns 1 through 5, treat as candidate degradation. This is an agent-estimated heuristic, not an instrumented baseline — relabel to cobra/outcome-logger latency field when available.
- On first tool error: **pause** and compare the live schema vs prior calls in this session before retrying. Do not treat a schema-mismatch as a transient.
- Alert (log warning **and** note in the tool result) if **2+ tools degrade together in the same turn** — correlated SLA drop, not independent flakes.
- Retry **once** with a fallback tool if one is available (PlanBench-XL fallback path). Do **not** blindly retry the same failing tool.

Pairs with BENCH2ROBUST retry/switch/abstain and PlanBench-XL pre-declared fallbacks. Environment-shift rule for skills: `hermes-operating-pattern` Harness Effect.

---

## 3. Multi-Turn State Management

### OODA-Tool separation (arXiv:2608.24368) ★ HIGH
Direct function-calling and ReAct couple state tracking and action generation in one
autoregressive stream → state-action competition (next call overwrites earlier state).

**Hermes pattern (manual OODA):**
1. **Observe** — reconstruct task state from WM (`working-memory.py show|skill-hint`), not only chat tail.
2. **Orient** — update progress/next/must-constraints in WM before choosing tools.
3. **Decide** — name the next action and why it matches current WM (one line).
4. **Act** — issue tool call(s). Do not invent state inside the tool-call arguments.

Long-horizon: skill selection is driven by WM needs (Recuris 2608.24876), while durable
lessons stay in experiential memory (Hindsight/Graphiti/skills).

### Session-as-Event-Log: Selective Slice Loading (Anthropic Engineering, Apr 2026)

Store the full session as an **ordered, append-only event log outside the context window**.
Inject only positional slices: `getEvents(from_turn, to_turn)` rather than compacting irreversibly.

Key properties:
- Every event is immutable once written — no destructive compression of past events
- Slices are loaded on demand: "last 10 events", "events before action X", "events where tool=Y"
- The harness transforms the slice before injecting (strip raw tool payloads, keep summaries)
- Context stays bounded regardless of session length; recall is selective not exhaustive

**Hermes mapping:**
- Hermes's SQLite session DB already stores events as rows — `session_search` is the slice mechanism
- The compaction pipeline should treat the session DB as the primary source of truth and
  the in-context window as a working-memory projection, not the authoritative record
- `session_search(session_id=..., around_message_id=..., window=N)` is the `getEvents(from, to)` call
- Implication: do NOT rely on compaction to preserve full fidelity — query the DB instead

**Brain/Hands decoupling (same paper):**
- Orchestrator (brain) decides what to do — uses a powerful/expensive model, runs rarely
- Executor (hands) actually calls tools — can use fast/cheap model, runs many times
- Enables parallel execution: multiple hands can run simultaneously under one brain
- Already present in Hermes via `delegate_task` — the formal pattern validates this design

### Context Ceiling & Verification Gap (arXiv:2602.18998, Feb 2026, CMU)

Two fundamental limits prevent test-time scaling from working in practice:

**Context ceiling (sequential scaling):** Performance degrades as agents accumulate tool results. More turns ≠ better results.

**Verification gap (parallel scaling):** Sampling multiple trajectories fails — agents cannot reliably self-verify which result is best without ground truth.

All 10 tested LLM agents showed "substantial performance degradation" in general-agent settings.

**Hermes pattern:**
- `agent.max_turns=500` is a ceiling, not a target
- Adaptive compression should trigger based on **tool-result density** (proportion of context that is raw tool output), not just total character count
- `verify_on_stop=auto` addresses the verification gap correctly — always verify externally
- `compression.threshold=0.5` (live config as of Sep 2026 — verify with `grep threshold ~/.hermes/config.yaml`) may need to trigger earlier based on tool density — set it at session start if tool-heavy work is anticipated, not mid-session

**Community confirmation (Reddit r/LocalLLaMA, Dec 2025):** Over-isolation → incompatible changes; over-sharing → eliminates parallel benefit. The right level is interface/schema context only, not full conversation history.

---

## 4. Self-Correction Patterns

### Reflexion: Verbal Episodic Buffer on Task Failure (arXiv:2303.11366)

ReAct already gives Hermes action–observation via the tool-call loop. Reflexion adds a **post-failure verbal trace** used on the *next attempt*, not a skill patch.

When a **task/attempt** fails (verifier/tests/user correction/stop-fail) — not a single recovered tool error:

1. Write one structured reflection with `hindsight_retain` (`context="reflexion-failure"`, tags `reflexion`, `failure`, `task_type:<slug>`): what failed, why, what to try next.
2. On the next attempt of that task type, recall those tags **before** choosing tools; do not repeat `what_failed`.
3. Do not `skill_manage` from this step. Recurring same-`why` failures (≥3) escalate to the human-gated path in `self-improve-agent`.

Full template and EvoAgent distinction: `self-improve-agent` § Reflexion verbal episodic buffer. In-loop retries stay MERIT / LivePlan / circuit-breaker; this buffer is for the attempt boundary.

### Prospective Reflection: PreFlect (arXiv:2602.07187, Feb 2026)

Existing reflection is **retrospective**: act → fail → correct. PreFlect introduces **prospective** reflection: critique and refine plans *before* execution, distilled from historical trajectory error patterns.

"Significantly improves overall agent utility on complex real-world tasks, outperforming strong reflection-based baselines and several more complex agent architectures."

**Hermes pattern:** Before beginning a multi-step tool call sequence:
1. Outline the planned tool call sequence
2. Ask the model to identify likely failure modes from prior similar tasks
3. Revise the plan to avoid them before execution begins

### Per-Stage ODR Loop: REGREACT (arXiv:2604.12054, Apr 2026)

Each pipeline stage implements **Observe-Diagnose-Repair (ODR)**: validate → diagnose → repair. Outperforms GPT-4o single-pass on all structural and semantic metrics.

**Hermes pattern:** `verify_on_stop` operates at the task level. ODR operates at the tool-call level. For tools producing structured output (JSON, code), a lightweight schema validator at each tool boundary prevents downstream error cascade. The two are complementary.

### Tool Synthesis Self-Correction (arXiv:2502.11705, ACL 2025)

Agents dynamically synthesize new Python tool functions from task descriptions and self-critique the tool before using it.

**Hermes pattern (soft version):** When a tool call fails with a schema error, allow the model to suggest an improved tool schema/description and cache the session-local improvement for subsequent calls.

### Self-Improvement Hype vs. Reality (r/LocalLLaMA + HN Aug 2026, practitioner-confirmed)

These patterns were validated or disproven in production deployments independent of academic research:

**Works:** Test-driven self-improvement (external, static test suite as the evaluation signal). Error carry-forward (`ERRORS.md` with root cause; inject last 5 at session start; 30–40% reduction in repeated mistakes). Skill versioning with performance snapshots (roll back on regression). Peer review between model variants (15–25% quality gain on complex tasks; critic must have different framing from generator).

**Does NOT work in production:**
- Recursive self-improvement loops ("agent improves itself, improved agent improves itself"): converges to local optima and collapses; agent optimizes for its evaluation metric, not actual performance. Universal practitioner report: dead end without a fixed external evaluator.
- Fully autonomous skill generation without human review: self-generated skills drift from actual runtime capabilities within 2–3 iterations, hallucinating tool capabilities that don't exist.
- Continuous memory consolidation without human checkpoints: automated compression without periodic validation accumulates confident-but-wrong beliefs.
- Automatic tool discovery at runtime: agents select plausible-sounding tools that don't exist or have unmodeled side effects.

**The core principle:** self-improvement works when it's *improvement against a fixed external benchmark*. The fixedness of the evaluation signal is what separates "helpful self-tuning" from "reward hacking." The eval is the most important part of the harness for self-improvement, not the loop itself.

---

## 5. Monitoring, Safety Evolution & Efficiency (Aug 2026)

### PlanBench-XL: Pre-declare Fallback Tool Paths (arXiv:2606.22388)

327 retail tasks over 1,665 tools. GPT-5.4 dropped from 51.90% → 11.36% success under
realistic tool ecosystem failures. Two failure modes dominated: (1) missing explicit error
signals — agent can't detect it failed; (2) recovery required discovering a longer
alternative path the agent had no prior knowledge of.

**Hermes pattern:** For any task with more than 3 sequential tool calls, before execution:
1. Identify the 1-2 highest-risk tool calls (external API, auth-gated, flaky service)
2. Pre-declare one fallback path for each: "if X fails → try Y instead"
3. Ensure every tool call produces an explicit success/failure signal — never infer success
   from absence of error. Check return values, status codes, or read back the written state.

This pairs with the failure-type classifier below (retry logic) — PlanBench is about
knowing *where to go next*, the classifier is about *how many times to retry in place*.

### RADEG: Retroactive Policy Generation for Skill Load Gating (arXiv:2608.09168)

Log query-skill-outcome triples → lightweight classifier → gate low-utility skill loads.
When a skill produces no actionable output for 3+ consecutive sessions on the same trigger,
flag it for removal from auto-routing. Routing layer: `hermes-semantic-skill-routing`.
ATP approval logs as training signal: `mnemosyne-atp-safety`.

Paper-level patterns extracted to `references/extended-runtime-patterns.md` (load on demand):
Salience induction defense, zero-replay event KG, SHE 4-artifact evolution, CommitKV
event-aligned compaction, ATP-Bench planning failures, PSE cross-session contamination,
EASy milestone routing, DreamGuard prefix-risk (`trajectory-risk-guardrail`).


Decouples trajectory monitoring from correction: a **deterministic rule-based monitor** scans general trajectory signals (repeated actions, no-progress streaks, empty patches) without invoking an LLM; an **advisor LLM is called only when the monitor fires**. Achieves +9.9% average issue-resolution on SWE-bench at $0.08/instance additional cost.

**Hermes pattern:** Implement as a SQLite-backed loop watchdog:
1. After each tool call, write `(turn, tool_name, success, result_hash)` to a session table.
2. If `COUNT(*) WHERE tool_name=X AND success=0 >= 3` OR `result_hash matches previous turn` → trigger a corrective prompt: "You've tried X three times and failed. What alternative approach should you take?"
3. No LLM call for the monitoring step — pure SQL.

SHE / CommitKV / ATP-Bench / PSE / EASy / DreamGuard: `references/extended-runtime-patterns.md`.
Event-aligned compaction (CommitKV principle) is the rule for micro-compact; do not use a fixed every-N-turns cadence.
Long `computer_use` prefix-risk: `trajectory-risk-guardrail`. Milestone executor routing: `claude-routing-hierarchy`.

### Oscillatory Instability Guard — Sign-Flip Detector (Strogatz Ch 8.6, Lyapunov Exponent)

Near chaos (Lyapunov exponent λ > 0), nearby trajectories diverge at rate e^{λt}. In correction loops, this manifests as sign-reversal of the error: over-correction → under-correction → over-correction. Once oscillation begins, increasing the correction magnitude amplifies divergence.

**Oscillation detection rule (apply in any loop that applies a corrective action):**
```
if len(signed_errors) >= 4:
    sign_flips = sum(
        1 for i in range(1, 4)
        if signed_errors[-i] * signed_errors[-(i+1)] < 0
    )
    if sign_flips >= 3:  # 3+ sign reversals in last 4 steps
        warn("Oscillatory correction: Lyapunov instability signature")
        halve_correction_magnitude()
        # OR halt if halving has already been applied once
```

**What counts as signed_error:** (expected_value − actual_value). Positive = over-corrected, negative = under-corrected. If your loop does not naturally produce signed errors, use (current_metric − target) each iteration.

**Do NOT increase correction magnitude when oscillation is detected** — that is anti-stabilising. Halve it first (damping); if oscillation persists after halving, halt and report.

**Composability:** applies AFTER the Lyapunov Convergence Guard (above). Lyapunov guard catches non-improving monotone divergence; this guard catches oscillatory divergence — they are complementary.

### BENCH2ROBUST: Retry/Switch/Abstain Tool Policy (arXiv:2608.11977)

Real deployed tools fail transiently, persistently, or silently. Agents trained on
failure-free benchmarks have no recovery policy. BENCH2ROBUST reveals three recovery
strategies that must be explicitly programmed:

| Failure type | Recovery strategy | When to apply |
|---|---|---|
| Transient (network, timeout) | **Retry** with backoff | Error is expected to resolve with time |
| Persistent (broken API, wrong args) | **Switch** to alternative tool | Same input to same tool keeps failing |
| Silent (tool returns but is wrong) | **Abstain** / escalate | Verifier detects incorrect output |

**Bayesian Tool Memory (BTM)** — zero-retraining runtime overlay:
- After each tool call, update a lightweight belief state: `P(tool_works | context_signature)`
- On next call: route to the highest-reliability tool for this context
- Improves robustness 16.8 pp without retraining; combined with RL adds 40.8–45.5% under injection

**Hermes application:**
- The existing RETRY_LOOP detection (same-tool/same-args ≥3) is the Retry→Switch boundary
- **RETRY_LOOP guard (arXiv:2606.01416):** if the agent calls the same tool with the same arguments 3+ times in a row, classify as RETRY_LOOP and break by (1) identifying the underlying cause, (2) trying an alternative approach or tool, (3) escalating to HITL if alternatives exhausted. Typed 5-class recovery (TOOL_TIMEOUT / MALFORMED_ARGS / STALE_CONTEXT / CONTRADICTORY_EVIDENCE / RETRY_LOOP) reaches 98.8% task success vs 94.5% retry-only — see `mnemosyne-atp-safety`.
- Add context-signature check before each tool retry: if `context == prior_failure_context`,
  switch immediately rather than retrying (BTM without Bayesian weights)
- For `browser_*` tools specifically: transient = retry 2x; persistent = switch to `web_extract`;
  silent failure (empty result but no error) = flag as RETRY_LOOP_SILENT, abstain and escalate

**Browser silent loop (RETRY_LOOP_SILENT):** browser agent ops that receive no error but make no progress (page not loading, element not found repeatedly) are a 6th failure class not in the taxonomy above. Detect by checking: same browser_navigate/browser_click call with same args >= 3 times with no content change. Recovery: reload page, try alternative selector, or escalate to HITL.

**No retraining or model change needed** — BTM is implemented as a runtime overlay using
existing tool call metadata.

### "Just Two More Things" Convergence Anti-Pattern (Steve Yegge, Aug 2026)

Observed empirically in production agent harnesses: a self-improvement loop
where the agent perpetually wants to refine its own harness before doing the actual work.
Each iteration produces "just two more improvements" to the harness rather than converging
to task completion. Named after the classic "Columbo" pattern of indefinite reopening.

**Root cause:** open-ended harness self-improvement with no discrete done-state. The agent
optimises for the meta-goal (improve harness) rather than the object-level task.

**Hermes prevention:**
- Never run a self-improvement loop without an explicit discrete done-condition (not "stop
  when improved" — "stop after N iterations" or "stop when metric X crosses threshold Y")
- Separate harness improvement tasks from task execution tasks entirely: an agent improving
  a skill should not also be completing the task that triggered the improvement
- Signs of convergence failure: same skill is patched 3+ times in one session; agent
  produces rationale for "one more pass" after each pass; tool call count keeps rising
  without measurable task progress
- Apply `LivePlan` stuck-state monitor: if `result_hash matches previous turn` for a skill
  patch tool call, flag as convergence failure and hard-stop the loop

Yegge reported this on one frontier model and not another — treat it as model-dependent.
Watch for it in multi-turn self-improvement crons regardless of model.

### TrajectorysentinelL: Lightweight Failure Detection Without LLM Judges (arXiv:2608.02464, Aug 2026) ★ HIGH

On 2,823 agent episodes across 3 frameworks and 4 models: a **one-class echo-state-network
+ CUSUM alarm** detects 71% of failures at 5% false-alarm budget (AUROC 0.872). The detector
triggers at 200 microseconds per step — three orders of magnitude below a judge call.
Detection advantage is monotone with post-onset horizon: +0.09 at ≤3 steps, +0.40 at ≥9.

**More powerful: deterministic verification layer** (zero retraining, transfers unchanged):
- Recompute the agent's stated totals from the tool results it actually received
- Confirm every required tool call was made (coverage check)
- Head-to-head: catches 60% of failures at 0 of 63 false positives (vs monitor: 54% at 17% FP)
- Combined with coverage check: 96% catch rate
- Transfers unchanged to llama3.1:8b (110/110 at 0/10 FP); 0 false positives on 1,825 healthy episodes

**Rollback + replay recovery:**
- Flagged runs rolled back and re-run live: recovers 45% of failures vs 16% resampling control (p=0.0005)
- Lifts task success from 52% → 73% for ~1 extra model call per run
- Code + traces: github.com/sunnydubey1111/agent-trajectory-sentinel

**Hermes pattern:**
1. **Deterministic verification** (add to `verification-before-completion` workflow): after any multi-tool run, recompute claimed outputs from tool results received. If claimed sum ≠ sum of tool outputs: flag.
2. **Coverage check**: confirm every required tool call category was made (e.g. if plan says "search then write", verify both happened).
3. **Rollback+replay**: when LivePlan watchdog fires AND deterministic verification catches a failure, don't just steer — rollback to last verified state and re-run the failed sub-sequence (one extra model call; 45% recovery rate).
4. **No LLM for monitoring**: the SQL watchdog (section 5) IS the cheap monitor. Add a coverage-check column to the session table.

---

## 5b. Circuit Breaker Ladder: Steer → Constrain → Stop

Pattern distilled from: munder-difflin (chaitanyagiri/munder-difflin, MIT, ~1.7k stars).
Complements the LivePlan SQL watchdog (section 5) with an explicit 3-rung escalation
that applies when an agent is looping, storming errors, or blowing its budget.

### The Three Rungs

**Rung 1 — Steer:** inject a corrective prompt into the agent's next turn.
- Trigger: same tool failed 3 times OR result_hash unchanged for 2 consecutive turns.
- Action: append to next tool result: "You've tried X N times without progress. What
  alternative approach should you take? List it before continuing."
- Cost: zero additional model calls; steers rather than interrupts.

**Rung 2 — Constrain:** restrict the agent's active tool surface or context scope.
- Trigger: steer had no effect (result_hash still unchanged after another 2 turns OR
  failure count crossed 6 total on the same tool).
- Action: drop non-essential tools from the active schema (evict stale MCP tools);
  narrow context to the failing subtask only; set a hard iteration cap for this subtask.
- Cost: one schema-reload turn.

**Rung 3 — Stop (Graceful):** halt the agent loop and escalate to the user or parent orchestrator.
- Trigger: constraint had no effect after 3 more turns, OR budget is within 20% of
  per-session cap, OR a destructive operation is about to execute with unverified state.
- Action: emit a structured stop signal with cause, last N tool calls, and a recovery suggestion.
  For cron agents: write a `signals.json` entry `{"type": "stop", "cause": "...", "ts": "..."}` to
  the blackboard (see agent-mailbox-ipc skill) so the parent or sibling agents can react.
- Cost: no further model calls after the stop is emitted.

### When to Skip Rungs

Skip Rung 1 and go directly to Rung 2 when:
- A destructive tool (file delete, git push, API mutation) is about to execute and
  prior result verification failed.

Skip to Rung 3 immediately when:
- A hard budget cap is reached.
- A human-gated operation (spend, scope change, external API with side effects) is
  queued and the session has no approval mechanism active.

### Relationship to Other Patterns

- LivePlan SQL watchdog (section 5): detects the failure signal (cheap, no LLM).
  Circuit breaker ladder: defines WHAT TO DO after the signal fires.
- Browser-specific thrash (same click index / stagnant page fingerprint):
  use `browser-agent-ops` + `~/.hermes/scripts/browser_act_guard.py observe`.
  That is the soft loop detector for interactive browser runs; this section
  remains the generic steer→constrain→stop policy.
- mnemosyne-atp-safety: handles admission control for individual tool calls (ATP commit/deny).
  Circuit breaker: handles loop-level escalation across multiple turns.
- PlanBench-XL fallback paths: pre-declare fallback before execution.
  Circuit breaker: activates when the fallback path itself is also failing.

The full chain: PlanBench pre-declare fallback → LivePlan detects failure → Circuit breaker
escalates through steer/constrain/stop → mnemosyne-atp-safety blocks individual
destructive tool calls while the escalation resolves.

### Lyapunov Convergence Guard (Astrom-Murray Ch 5.4, Theorem 5.6)

For any iterative agent loop with a measurable progress metric (error count, diff size, test pass rate, Bellman residual), apply the Lyapunov criterion before each iteration:

**Rule:** Track V[t] = ‖metric[t] − goal‖ (lower is better). If V[t] ≥ V[t-1] ≥ V[t-2] (non-decreasing over 3 consecutive iterations) AND the relative improvement (V[t-2] - V[t]) / V[t-2] < 0.01 (less than 1%), the loop is not converging — halt and report.

**Concrete implementation (no new infrastructure):**
```
loop_metrics = []   # append metric value after each iteration
if len(loop_metrics) >= 3:
    V = loop_metrics[-3:]
    if V[0] <= V[1] <= V[2] and (V[0] - V[2]) / max(V[0], 1e-9) < 0.01:
        halt("Lyapunov condition violated: loop not converging after 3 non-improving iterations")
```

**Why:** Lyapunov's theorem (Astrom-Murray §5.4, Theorem 5.6) proves that a system asymptotically converges iff a valid Lyapunov function is strictly decreasing. If V is non-decreasing, the system is not in the basin of attraction of the target — further iterations will not help without a structural change (new strategy, new tool, or user clarification). Stopping at iteration 3 saves on average 60-70% of wasted budget vs waiting for a hard iteration cap.

**Does NOT apply to:** one-shot tasks (no iteration), tasks where the metric legitimately plateaus (verify metric is appropriate before using), randomised search where variance is expected.

### HaReCAP Reflex Rules (arXiv:2608.16447)

If the same **leaf decision** (same tool + same argument pattern) has occurred **3+ times** in the current session, compile it to a **reflex rule**.

Pre-reflex gate: before compiling OR applying a HaReCAP reflex rule, check tool distribution-shift state. If 2+ tools are currently below session baseline latency/success rate, run the Tool-Use Distribution Shift check (see above section) first. Suspend reflex compilation until shift is resolved. Reason: a correlated multi-tool degradation would be compiled into a reflex, bypassing future shift detection.

- Reflex rules **bypass deliberation**: apply the compiled mapping directly; do not re-reason about alternatives on each occurrence.
- This is a session-local compile, not a skill patch. Recurring verified reflexes that should persist across sessions: `preact-trajectory-compilation` (turn reflex rules into persistent PreAct graphs).
- Claimed **14–20% token reduction** on repetitive task patterns (paper metric; do not treat as a guaranteed local gain).

Do not compile a reflex from a RETRY_LOOP (same failing call). Reflexes are for **successful** repeated leaf decisions only. Circuit-breaker Rung 1 still owns failed repeats.

---

## 6. Loop Governance: Stop-Condition & Progress Injection Discipline

Outer-loop parameters (`should_continue`, `record_feedback` ≤140 tokens, `fresh_context`) and
the 4 stop-condition types live in `autonomous-agent-loop-design`. This skill owns the **inner**
tool loop (one model request + its tool calls).

Do not confuse: outer loop = cron/subagent cycle; inner loop = one reasoning step. Mixing them
is a root cause of exponential context growth.

Event schema and append-only session log: `references/extended-runtime-patterns.md` (Zero-Replay).

## 6b. Drift Recovery: Multi-Node Recovery Graph

### Graph-Based Drift Recovery with Per-Node Role Specialization (arXiv:2608.14109, Aug 2026) <!-- why: prevents single-prompt recovery from missing recovery subtasks (classification vs decision vs execution) -->

A plug-and-play recovery graph in which each node specializes in one recovery subtask:
1. Drift-class detection (what type of drift occurred)
2. Operation-type extraction (what the agent was attempting)
3. Risk level assessment (low/medium/high)
4. Recovery decision (retry / rollback / escalate)

Key findings: knowing the **drift onset step** (not just current state) dramatically improves recovery decision accuracy. Schema-constrained XML outputs with dual reward (rule-based structural + LLM-as-judge semantic) are required for reliable per-node specialization.

**Hermes pattern:** model the 4 nodes as separate system-prompt contexts rather than full RL — on tool failure, route through: (1) drift-class classifier prompt, (2) operation-type extractor, (3) risk assessor, (4) recovery decision. No RL required; the node decomposition is the valuable pattern.

**Drift onset timestamp:** in `verification-before-completion`, capture the step index at which recovery was triggered — this enables post-hoc analysis of drift frequency per task type.

### Tool-Call Pattern FSM for Online Drift Detection (arXiv:2608.23670)

Collapse a session’s tool-call trace into a compact FSM (7–43 states). Per-state features
reach held-out AUROC 0.94 for failure prediction from a partial trace. FSM topology is
shaper by the harness than by the LLM — the harness’s toolset and approval gates define
what state space is possible.

Hermes applicability:
  - `session_search` traces over 15–20 sessions can be collapsed into a baseline FSM
  - States map to recognizable loop patterns: [search → write → verify] vs
    [search → search → search → ...] (S1 IAL) vs [skill_load → skill_load → ...] (thrash)
  - Partial-trace monitor: after 5+ tool calls, current position in FSM predicts final outcome
    with AUROC ~0.85; flag if current path maps to a known failure state

### Known Open Gap: Multi-Agent Memory Consistency (arXiv:2603.10062)

CPUs have SC / TSO / Release Consistency with formal machine-checked proofs. Agent memory
has no equivalent formalism — identified as "the most pressing open challenge in multi-agent
systems" (2026 position paper). TLA+-verified MESI-style versioning (arXiv:2603.15183)
is the closest current analog; it covers artifact versioning, not full sequential consistency.

Hermes consequence: any guarantee about cross-agent memory state is best-effort, not
formally bounded. Design loops to tolerate stale reads rather than assuming consistency.
Use exclusive write ownership (one writer per key) as the strongest available invariant.

KAPRO/KAware metacognition check (arXiv:2606.20661):
Decouples Knowing (do I need a tool?) from Acting (calling it). Self-awareness correlates
with success but collapses on internal-capability tasks. Open-source and instruction models
over-call tools. Symptom: repeated tool calls where the answer was already in context.
Hermes: before calling a search or read tool, ask “is this in current context already?”
Over-calling pattern = drift signal independent of task failure.

---

## 6c. Host contract (Agentao)

Permission-mediated tool execution and skill `uses: [...]` declarations belong in
`hermes-skillspector-guard-maintenance`. Layer map: `references/extended-runtime-patterns.md`.

## 7. Enterprise Grounding

Non-English production surveys confirming HITL + context-ceiling: `references/extended-runtime-patterns.md`
and `references/noneng-agent-patterns-aug2026.md`.

---

## Context engineering discipline (arXiv:2606.10209) ★ HIGH

Paper result (expense-itemization tool agents): **last-N tool pairs + compact summarization beats full history** (91.6% complete vs 71% full-context, fewer tokens). Verbose tool dumps cause overflow, stale-state errors, and cost.

**Hermes:**
1. Field-select at the call site (`char_limit`, offset/limit, targeted grep) — do not inject full dumps hoping the model ignores noise.
2. Keep only the last ~5 tool call/response pairs in the hot window; fold older ones to a short state summary (pair with `hermes-context-hygiene`).
3. Do not treat this as a substitute for OODA working-memory separation.

<!-- why: full tool dumps force the inner loop to spend context on noise; last-N+summary is the paper's actual intervention -->

## Execution template evolution (arXiv:2609.09153) ★ HIGH

Same paper as `autonomous-agent-loop-design` § procedural graph. **This skill owns the inner loop only.**

After each attempt, note whether each step contributed to success or failure (session / ERRORS.md). Prune in-run retries of steps that add latency without outcomes. Do **not** `skill_manage` from this step — that contradicts Reflexion above and the phantom-guardrail rule (unverified failures must not become permanent pitfalls). Recurring same-step failures (≥2 verified, not phantom) escalate to `self-improve-agent` (human-gated), which owns skill-body graph edits.

<!-- why: in-loop skill_manage installs phantom guardrails and skips Argus admission -->


## AIMD Concurrency Controller (Denuto Pattern)

Additive Increase / Multiplicative Decrease for LLM concurrency.
Source: Denuto `src/aimd.py`. Theoretical basis: TCP congestion control (Chiu & Jain 1989).

**Architecture**: Per `(provider, node)` independent controller instances via registry.
Throttling OpenAI extractor does NOT affect Anthropic extractor or OpenAI compiler.

```
# Default node budgets:
extractor=8 (HIGH), compiler=4 (MEDIUM), profiler=2 (MEDIUM),
structural=2 (LOW), llm_checks=2 (LOW)

# AIMD adjustment (every 5 ops, sliding window of 20):
throttles >= 2: limit = max(1, limit // 2)        # multiplicative decrease
errors >= 3:    limit = max(1, int(limit * 0.7))  # moderate decrease
all_clear + 75% full window: limit = min(max*3, limit + 1)  # additive increase
```

```python
# Usage (contextmanager-based slot acquisition with timeout):
ctrl = get_controller(provider="anthropic", node="extractor")
with ctrl.control():
    result = call_llm(prompt)  # auto-released; 429/503 detected as throttle
```

**Convergence Note (GATE GAP)**: AIMD converges to fair-share only if all agents see the
same throttle signal. In Hermes parallel subagents each has independent state, so the
TCP convergence proof does NOT apply cross-agent. Subagents may produce divergent limits
for the same provider if they see different throttle patterns.

**Backpressure**: LOW-priority nodes block if provider health ratio < 0.5.
**Full-jitter backoff**: use explicitly-passed `random.Random` (never module-global) —
Karn's algorithm — for reproducibility under test.

See also: `hermes-reasoning-layer-engineering`, `hermes-llm-middleware-stack`.

## Quick Decision Guide

| Symptom | Pattern to Apply |
|---------|-----------------|
| Agent installs guardrails that don't match real failures | Phantom Guardrail check — counterfactual oracle |
| Agent retries same failed approach multiple times | MERIT typed failure memory |
| Multi-turn performance degrades after ~10 turns | Context ceiling — trigger compression by tool-result density |
| Tool calls produce huge intermediate traces | HyperTool code-block batching |
| Many parallel tool calls of same type | LLM-Tool Compiler type-affinity fusion |
| Parallel multi-tool under resource caps | PeakBench: dependency-aware schedule; avoid resource-agnostic fan-out (2608.24509) |
| Long-horizon skill selection | WM skill-hint (Recuris) — not full history |
| Cross-model handoff | WM handoff-export + binding constraints (Handoff Tax) |
| Subagent gets confused by too much context | AOrchestra per-step context narrowing |
| Mid-plan step fails validation; later steps depend on it | Workflow suffix repair — replan from failed step only, preserve confirmed prefix (arXiv:2609.12533) |
| Task/attempt failed; next retry would repeat the same approach | Reflexion verbal buffer — `hindsight_retain` then recall on retry (`self-improve-agent`) |
| Late-stage failures are expensive to recover from | PreFlect prospective reflection |
| Structured output errors propagate downstream | ODR per-tool validation (REGREACT pattern) |
| Agent repeats failed tool call ≥3 times | LivePlan watchdog → Circuit breaker Rung 1 (steer) |
| Steer had no effect after 2 more turns | Circuit breaker Rung 2 (constrain: evict tools, narrow context) |
| Budget near cap or destructive op unverified | Circuit breaker Rung 3 (stop + escalate) |
| Skill-file gap caused a trajectory failure | SHE attribution: localize to skill file, patch only that artifact |
| Complex task benefits from cost-aware routing | EASy milestone decomposition + executor capability/cost profiles |
| Long computer_use sequence drifting toward hazard | DreamGuard pattern: recurrent trajectory state + prefix-risk check |
| Tool results bloat context / overflow | Context engineering — last-N pairs + field-select (2606.10209) |
| Skill steps fail repeatedly in the same context | Inner-loop template notes; skill-body edits via `self-improve-agent` (2609.09153) |
| Tool-diversity collapse (Lyapunov V_n below 0.20 for 3 or more consecutive 5-turn windows) | Halt loop and force new tool branch or escalate to user |
| Context projection vs compaction: next turn needs specific tool output values | Project — variable binding (print only the needed value; see hermes-context-hygiene § Scroll pattern, arXiv:2608.21690) |
| Context projection vs compaction: only the conclusion matters long-term | Compact+summarize — do not carry raw tool output forward |

## References

- `references/agent-runtime-research-2025-2026.md` — Evidence base (papers, numbers, non-English sources, practitioner reports).
- `references/extended-runtime-patterns.md` — Extracted paper-level patterns (salience, event KG, SHE, CommitKV, ATP-Bench, PSE, EASy, DreamGuard, Agentao, Python pitfalls, cold-start, Sweep 31, Evo-Harness).
- `references/agent-improvements-2026-08.md` — Post-Aug 8 2026 sweep; cold-start preamble lives here.
- `references/noneng-agent-patterns-aug2026.md` — Non-English agent patterns.
- `references/agent-runtime-sweep-aug14-2026.md` — Sweep 13; convergence-gate evidence.
- `references/python-runtime-pitfalls-aug2026.md` — Hyphenated imports, ast extract, 5-class retry, SQLite ALTER TABLE.

**Convergence gate** (same as "Just Two More Things" above): after each improvement iteration, require a measurable metric or a new distinct finding. N=3 consecutive iterations with zero verified improvement → stop. Never expand scope mid-run to dodge the gate.

## Rule of Succession as Retry Prior (Jaynes Ch 18)

**Theory:** If a tool succeeded k times in n attempts, the Laplace rule of succession gives P(next success) = (k+1)/(n+2). This is the posterior mean of a Beta(k+1, n-k+1) distribution, providing a calibrated prior for retry decisions without needing historical data.

**Hermes rules:**
- Before retrying a tool, compute the session retry prior: P(success) = (k+1)/(n+2).
- When k=0, n=1 (one failure, zero successes): P(success) = 1/3. Use this as a retry gate — 1/3 is low but not negligible; retry once more.
- When k=0, n=3 (three failures): P(success) = 1/5. Below the 0.2 threshold, do NOT retry; escalate or switch approach.
- This formalizes the intuition behind "try twice before giving up" and the circuit-breaker pattern.

**Citation:** E.T. Jaynes — *Probability Theory: The Logic of Science*, Ch 18 (The Ap distribution and the rule of succession); originally Laplace (1814).

## Lyapunov Loop-Divergence Detector (Khalil Thm 4.1)

Map iteration error to V(x) = ||goal_metric[t] - goal_metric[t-1]||. If V is non-decreasing over 3 consecutive iterations AND absolute error is not shrinking (less than 1% relative improvement), halt and report loop not converging — Lyapunov condition violated. This catches runaway retry spirals before they exhaust budget.

## Critical-Slowing-Down Bifurcation Detector (Strogatz Ch 3)

When consecutive tool-call latencies on the same tool are increasing AND success rate is falling, this matches the saddle-node bifurcation signature. Rule: if geometric mean of last 3 consecutive latency ratios (latency[i]/latency[i-1]) exceeds 1.5, treat as bifurcation warning and switch tool or escalate — do NOT retry the same call again.

## Sign-Flip Oscillation Detector (Strogatz Ch 8.6)

If signed correction error flips sign on 4 consecutive iterations (3+ sign-flip pairs), the correction dynamics are oscillating — chaotic instability signature. Emit: oscillatory correction detected — consider damping (reduce step size) or halting.

## Tool Distribution-Shift Triage Rule (arXiv:2609.00467)

On any tool first error: before retrying, check if tool schema changed since last successful call. When >=2 tools show degradation simultaneously, treat as correlated shift (environment change). Rule: if retry count on same tool reaches 2 AND a different tool could serve the same function, switch tools — do not retry a third time.
