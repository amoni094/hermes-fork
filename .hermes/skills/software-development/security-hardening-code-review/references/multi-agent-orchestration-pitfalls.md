# Multi-Agent Orchestration: Patterns & Pitfalls (2025–2026)

**Sources:** Microsoft Azure Architecture Center, TianPan routing analysis, TrueFoundry cascades, DEV/TheDailyAgent, SitePoint agentic patterns, academic literature (ICLR 2024).

**Context:** When hardening agent code, consider not just threat detection but orchestration resilience. Multi-agent flows resurrect classical distributed-systems failure modes; this reference documents the patterns and their failure surfaces.

---

## Five Core Multi-Agent Patterns

The following patterns account for ~90% of production multi-agent deployments. Each has distinct cost, latency, and failure profiles.

### 1. Sequential Pipeline (Chaining)
**Flow:** Agent A produces output → fed to Agent B → fed to Agent C.

**When to use:**
- Clear dependencies with progressive refinement (draft → review → polish)
- Defined order; each step builds on the prior
- Auditability matters (error at step 2 is traceable)

**Cost model:** Input + sum of forwarded outputs. E.g., 3 agents ≈ 4.5× a single call (compounding context).

**Failure modes:**
- **Error cascading** — a mistake at step 2 (e.g., hallucinated reference) taints steps 3–5. By step 5, the agent confidently elaborates on the error. Mitigation: validate output at each step before passing downstream; cap chain length at 5–7 steps.
- **Context explosion** — each step's output is fed to the next; context windows saturation. Mitigation: summarize intermediate outputs; truncate to relevant fields only.
- **No backtracking** — once step 2 completes, you can't ask step 1 to reconsider. Mitigation: design for feed-forward; if backtracking is needed, switch to concurrent+aggregation pattern.

**Example:** `Draft (ReAct) → LLM Review (code-check) → Polish (tone/formatting)`.

---

### 2. Concurrent / Fan-Out / Map-Reduce
**Flow:** Orchestrator sends independent subtasks to Agents A, B, C in parallel; collects results; aggregates (vote, weighted sum, LLM synthesis).

**When to use:**
- Independent subtasks (no ordering dependency)
- Speed matters (latency is max(A, B, C), not A+B+C)
- Diverse perspectives improve output (e.g., "what would a security engineer, a performance engineer, and a business analyst each say?")

**Cost model:** Input + N×subtask tokens (linear in agent count). Highest resource use but lowest latency for wide tasks.

**Failure modes:**
- **Cost scaling** — N agents = N× the tokens. Even with cheap models, 10 concurrent agents is expensive. Mitigation: right-size the agent count; use cheap models for wide fan-outs.
- **Aggregator quality** — weak aggregator (e.g., naive voting) loses information. Example: two agents produce "remove the function" and "keep and refactor it"; voting picks arbitrarily. Mitigation: use LLM aggregation (pass all N outputs to a synthesis agent) or weighted voting (expert/confidence-scored).
- **Cascading failure** — one agent crashes or hangs; entire fan-in blocks. Mitigation: per-agent timeout; return best-effort result with confidence score if one agent times out.

**Example:** `Fetch data from 5 APIs in parallel → aggregate into a summary`.

---

### 3. Group Chat / Roundtable (Debate / Maker-Checker)
**Flow:** Shared thread; agents read all prior messages; a chat manager picks the next speaker; agents discuss until consensus or iteration cap.

**When to use:**
- HITL (human-in-the-loop) maker-checker flows
- Iterative refinement where agents inform each other
- Auditability of reasoning (all steps visible)
- Budget for 2–3 iteration rounds (gains taper quickly)

**Cost model:** (agent_count + 1) × input + (rounds × agent_count) × refine_tokens. **Limit to ≤3 agents**; cost grows combinatorially.

**Failure modes:**
- **Infinite loops** — agents keep disagreeing; iteration limit reached with no consensus. Mitigation: hard iteration cap (≤3 rounds); fallback to human escalation or best-effort output with confidence.
- **Echo chamber** — agents model each other and converge to a local consensus wrong by group reasoning. Mitigation: add a devil's advocate role; designate one agent to explicitly argue the opposite.
- **Dominant speaker bias** — one verbose agent dominates; others defer. Mitigation: manager explicitly selects quiet speakers on even-numbered rounds.

**Example:** `Security review with [Code Author, Security Engineer, Ops] — 2 rounds, then human approval`.

---

### 4. Router / Triage / Dynamic Dispatch
**Flow:** Lightweight routing agent classifies the request → routes to a specialist agent. Only one specialist is active at a time.

**When to use:**
- Right specialist emerges during processing (support triage, routing to domain expert)
- Cheapest multi-agent overhead (one small routing call + one specialist)
- Clear taxonomy of specialist domains

**Cost model:** Cheap routing call + single specialist call. Lower cost than concurrent, lower latency than sequential.

**Failure modes:**
- **Infinite handoff loops** — A routes to B, B routes back to A, agents loop indefinitely. Mitigation: track visited agents; hard loop-count cap (max 3 hops); fallback to human escalation.
- **Misrouting** — classifier sends request to wrong specialist. Mitigation: require confidence score > threshold; route unconfident requests to a fallback generalist agent.
- **Specialist out of scope** — request requires multiple specialists; router can only pick one. Mitigation: design specialist domains with clear non-overlapping scopes; use sequential or concurrent pattern if multi-specialist is needed.

**Example:** `User question → classify (billing/technical/account) → route to specialist → specialist handles or escalates to human`.

---

### 5. Magentic / Dynamic Planning / Task Ledger
**Flow:** Manager agent builds and refines a task ledger; workers claim/execute tasks; manager updates ledger based on results; repeat until done.

**When to use:**
- Open-ended problems with no predetermined plan (e.g., SRE incident remediation, research synthesis)
- Adaptive decomposition (plan refines as workers report findings)
- Independent worker parallelism

**Cost model:** (manager_rounds × manager_tokens) + (worker_count × worker_tokens). **Most unpredictable cost**; manager may iterate 10+ times on a complex problem.

**Failure modes:**
- **Slow convergence** — manager stalls on ambiguous goals; task ledger never stabilizes. Mitigation: define explicit termination condition (e.g., "5 tasks completed with no new tasks created"); human escalation after N manager rounds.
- **Worker stalls** — a task is assigned but worker is blocked (missing data, tool failure). Mitigation: manager must monitor task age; escalate or reassign stalled tasks.
- **Cost explosion** — manager's iterative refinement multiplies LLM calls. Mitigation: strictly cap manager rounds (≤15); monitor cost per execution.

**Example:** `SRE agent manager creates task ledger ["investigate logs", "query metrics", "check recent deployments"]; workers execute; manager refines based on findings until incident is resolved or escalated`.

---

## Routing Patterns: Cost vs. Quality Optimization

When agents need different models (Haiku for simple classification, Sonnet for reasoning, o1 for planning), the following routing strategies apply:

### Rule-Based Routing
**Decision:** hardcoded logic on explicit signals (e.g., `if user_tier == "premium" → sonnet, else → haiku`).

**Cost:** Sub-millisecond decision.

**Pitfall:** Brittle; edge cases accumulate. Start here, migrate to classifiers if rules exceed ~10.

### Classifier-Based Routing (RouteLLM)
**Decision:** lightweight 110M-param model predicts best LLM for the query.

**Cost:** 10–30ms overhead; reduces overall token cost by 40–85% (maintains ~95% of frontier-model quality).

**Advantage:** Transfers across model pairs without retraining; requires <1,500 labeled training samples.

### Cascade / Waterfall (Cheap-First + Escalation)
**Decision:** send to cheap model (Haiku); measure confidence/quality; escalate to expensive model (Sonnet) only if below threshold.

**Cost:** Cheap call + escalation rate × expensive call. With 20% escalation rate, ≈ 24–30% of frontier-model cost.

**Pitfall:** Threshold miscalibration. Too high → constant escalation (expensive). Too low → quality degrades. Recalibrate monthly against 1,000–5,000 representative production queries.

**Real incident:** A provider-side schema change broke the quality validator; the cascade silently escalated 90% of traffic to the frontier model for 9 days. **Lesson: escalation rate is a live cost variable — alert on it.** If the escalation rate drifts >20% above baseline, investigate immediately.

---

## Distributed-Systems Failure Modes in Multi-Agent Flows

Multi-agent orchestration inherits classical distributed-systems problems. The following mitigations should be embedded in any orchestrator:

### 1. Node Failures (Agent Crashes)
**Mitigation:** Per-agent timeout; return best-effort result with confidence score if agent times out. Don't wait forever for one slow agent.

### 2. Silent Failures (Agent Hallucinates Valid-Looking Output)
**Mitigation:** Validate agent output structurally (schema, bounds, semantic plausibility) before passing downstream. Low-confidence/malformed responses should trigger retry or escalation, not silent propagation.

### 3. Message Loss & Ordering
**Mitigation:** Use a typed state object (LangGraph, Pydantic) as the single source of truth, not message-passing. State transitions must be deterministic and idempotent.

### 4. Cascading Errors
**Mitigation:** Surface errors instead of hiding them. If Agent A fails, don't let Agents B–E silently compound the failure with hallucinated context. Break the cascade at Agent B (validate A's output before using it).

### 5. Resource Exhaustion (Token Budget Exceeded)
**Mitigation:** Per-agent and per-orchestration token budgets. When exhausted, return best-effort result and alert.

---

## When NOT to Go Multi-Agent

The following conditions suggest staying single-agent:

1. **Context-window saturation not yet reached** — a 20-step ReAct trace may hit 50K tokens, but you're not there yet. Optimize the single agent first (compress prompts, group tools, retrieve context dynamically).

2. **Tool count < 12** — keep tools in a single agent. Accuracy degrades past 15 tools, collapses past 50. Only decompose if you truly need 50+ tools.

3. **Error compounding isn't a concern** — the task is well-defined with low ambiguity. A single agent with good prompt engineering handles it.

4. **Latency tolerance is high** — multi-agent adds 200–500ms per hop. If you have a 10-second SLA, stay single-agent.

---

## Pitfalls Across All Patterns

### Silent Quality Regressions
**Most dangerous.** Costs drop, dashboards look fine, until retention moves. Detection requires measuring quality alongside cost from day one. **Track retry rates, explicit feedback, task-completion rates segmented by model tier.** A silent regression that lasted 9 days (the escalation incident) suggests quality metrics were not being monitored in real time.

### Iteration Diminishing Returns
Reflection and group-chat patterns gain the most from 2–3 iterations; gains taper sharply afterward. Every additional loop multiplies cost linearly.

### Cost Unpredictability
- Sequential: cost per step is deterministic.
- Concurrent: cost spikes with agent count.
- Group chat: cost is (agents × rounds) × model cost — unpredictable if rounds vary.
- Magentic: manager iteration count is data-dependent; cost can be 2× or 10× depending on problem complexity.

**Mitigation:** Budget conservatively for magentic and group-chat patterns; cap iterations early.

### Orchestrator Bottleneck
In orchestrator-worker and evaluator-optimizer patterns, the orchestrator becomes a bottleneck. Latency is bounded by the slowest worker; concurrent calls multiply resource use. **Ask first:** do subtasks genuinely differ? Does latency reduction justify the cost?

### State Consistency Races
In loosely-coupled message-passing designs, agents can diverge or deadlock. **Use a single typed state object** (Pydantic, LangGraph) as the source of truth; avoid distributed consensus on state.

---

## Composition: Patterns Stack

Production systems routinely layer 2–3 patterns:
- Sequential pipeline **with** reflection at each step (reflection inside pipeline)
- Concurrent subtasks **with** group-chat aggregation (concurrent workers, group-chat coordinator)
- Router **to** sequential pipelines (router picks the pipeline)

Design for composition; don't assume single-pattern flows.

---

## References

- Microsoft Azure Architecture Center, "AI Agent Orchestration Patterns" (Feb 2026): https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns
- TianPan, "LLM Routing: How to Stop Paying Frontier Model Prices" (Oct 2025): https://tianpan.co/blog/2025-10-19-llm-routing-production
- TrueFoundry, "Intelligent LLM Routing: Cost-, Latency-, and Quality-Aware Model Selection" (Jun 2026): https://www.truefoundry.com/blog/llm-routing-cost-quality-aware-model-selection
- DEV / TheDailyAgent, "Multi-Agent Orchestration: A Guide to Patterns That Work" (Mar 2026): https://dev.to/thedailyagent/multi-agent-orchestration-a-guide-to-patterns-that-work-1h81
- SitePoint, "The Definitive Guide to Agentic Design Patterns in 2026" (Mar 2026): https://www.sitepoint.com/the-definitive-guide-to-agentic-design-patterns-in-2026/
