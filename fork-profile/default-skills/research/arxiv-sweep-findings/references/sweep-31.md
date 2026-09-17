# Sweep 31 Findings (2026-09-04)

Cutoff: above arXiv:2608.27454
New cutoff after Sweep 31: arXiv:2609.03201
Sources: hermes-research-sweep.py output — arxiv-search, OpenAlex, HAL (49 titled papers from 347 cache entries)

## HIGH Papers Applied

| ID | Title | Target Skill | Status |
|---|---|---|---|
| arXiv:2609.03201 | MemoryLACE — Atomic Write/Revision Semantics | agent-memory-consolidation | ✅ applied |
| arXiv:2602.06051 | CAST — Character+Scene Episodic Decomposition | agent-memory-consolidation | ✅ applied |
| arXiv:2609.00267 | Delegation Without Trust — Out-of-Model Auth Broker | trajectory-risk-guardrail | ✅ applied |
| arXiv:2609.02253 | APEx — Trajectory-to-Category Distillation + Planner Loop | self-improve-agent | ✅ applied |
| arXiv:2609.00237 | Gated-Memory Routing — Write Gate + Compact Retrieval | hermes-context-budgeting | ✅ applied |
| arXiv:2609.01428 | Act More/Decide Less — Skill-Guided Action Chunking | autonomous-agent-loop-design | ✅ applied |
| arXiv:2609.00829 | Agentic Graph RAG — Query-Type Traversal Strategy | graphiti-mcp-setup | ✅ applied |

## MED Papers (Logged)

### Role Drift Detection in Hierarchical MAS (arXiv:2609.03111) ★ MED

Empirical study of 8 hierarchical multi-agent systems: roles assigned at task start drift
over time as agents reinterpret their scope. Drift compounds with depth (similar to MasDrift,
Sweep 14) but is driven by task ambiguity, not authorization inheritance.

Drift signatures:
1. Executor-role agents begin making strategic decisions
2. Coordinator-role agents begin executing low-level tool calls  
3. Verifier-role agents begin proposing fixes instead of flagging issues

**Hermes pattern:**
- Each `delegate_task` subagent goal must include a role declaration: "Your role is [executor|planner|reviewer]. You may [actions]. You may NOT [boundary actions]."
- If a subagent output shows boundary violations (e.g. a reviewer proposing code changes), treat output with reduced trust weight and re-route through coordinator.
- Pair with MasDrift scope restriction: `enabled_toolsets` at delegation level is the enforcement mechanism; role declaration is the behavioral signal.

**Target skills:** `dispatching-parallel-agents`, `hermes-agent-sync`
**Status:** User-owned — blocked; run `hermes curator adopt dispatching-parallel-agents` to enable patch.

---

### Tool-Use Policy Under Distribution Shift (arXiv:2609.00467) ★ MED

12-benchmark study: tool-using agents calibrated on stable distribution show 18-31% performance
drop when tool availability or output format changes without explicit re-calibration.

Four shift types:
1. Tool unavailable
2. Tool returns different schema
3. New tool available for an existing task class
4. Tool latency degrades past SLA

**Detection signals:**
- Tool calls with increasing retry counts on the same tool → availability or schema shift
- Agent using a suboptimal tool when a better one exists → new-tool shift
- RETRY_LOOP triggers (same args ≥ 3) → possible schema shift

**Hermes pattern:**
- On any tool's first error in a session, pause and check: has the tool's schema changed vs. prior calls?
- When adding a new tool to a session's toolset, explicitly inform the agent of the new tool's capabilities at session start — agents do not discover new tools mid-session reliably.
- Log tool-performance baselines (latency + success rate) per session class; alert if ≥ 2 tools show degradation simultaneously (correlated shift signal).

**Target skills:** `agent-runtime-loop-patterns`
**Status:** User-owned — blocked.

---

### Cross-Session Context Locality Optimization (arXiv:2609.00148) ★ MED

Evidence from long-horizon agent deployments: agents consistently retrieve and re-read context
that was already available in their current working window. Re-buy rate: median 24% per session
vs. ≤10% target. Root cause: agents retrieve from long-term memory when a prior tool result
already answered the question.

**Three-signal context locality rule:**
1. Before calling `hindsight_recall` or `session_search`: scan last 5 tool results for the answer first
2. Before calling `read_file` on a path already read this session: use cached content in context
3. Before making a second web_extract on the same URL: check if first extract covers the question

Re-buy rate estimate: (# retrieval calls) / (# questions with prior context in window). Target ≤10%.

**Target skills:** `hermes-context-hygiene`, `hermes-memory-surface-selection`
**Status:** User-owned — blocked.

## LOW Papers (Skip Notes)

- arXiv:2609.01104 — LLM pretraining data composition analysis. LOW: training-time only, no runtime implication.
- arXiv:2609.00783 — Reward model evaluation benchmark. LOW: no Hermes harness target.
- arXiv:2609.02944 — Multimodal agent for UI navigation (desktop GUI). LOW: no vision toolset active.
- arXiv:2609.01811 — Federated learning for privacy-preserving fine-tuning. LOW: not a runtime pattern.
- arXiv:2609.00341 — Domain-adaptive NLP for biomedical text. LOW: no applicable domain overlap.
- ~298 bare arXiv listing IDs (cs.AI/CL/LG daily dumps) — SKIPPED per maintenance rule: listing IDs without titles are not actionable without abstract fetching. First-pass HTML counts are not a backlog.

## Adversarial Review Results

### CDH Check (Convergent Detour Hijacking)
All 7 patched skills checked: patch content matches the trigger domain.
- agent-memory-consolidation: MemoryLACE + CAST sections are memory-tier findings ✓
- trajectory-risk-guardrail: Delegation Without Trust is a trust/safety finding ✓
- self-improve-agent: APEx is a self-improvement distillation finding ✓
- autonomous-agent-loop-design: Act More/Decide Less is a loop-engineering finding ✓
- hermes-context-budgeting: Gated-Memory Routing is a context management finding ✓
- graphiti-mcp-setup: Agentic Graph RAG is a KG retrieval finding ✓
No CDH patterns detected.

### Oscillation Check
No repeated patches to the same skill; no fix/unfix cycles observed.

### Trigger Coherence
All patches inserted into semantically correct skill sections. No trigger mismatches.

## Verification
- All 7 skill_manage calls returned `success: true`
- Sweep boundary log updated in arxiv-sweep-findings Sweep Boundary Log table
- MED findings written to references/sweep-31.md (arxiv-sweep-findings at char limit)
