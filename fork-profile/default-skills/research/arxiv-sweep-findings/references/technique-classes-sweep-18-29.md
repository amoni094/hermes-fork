# Technique classes (Sweeps 18, 24, 27–29 — previously appended after References)

## Technique Class: Offline Harness + Multi-Agent Diversity + Failure Catch States (Sweep 27)

### AutoSaddler (arXiv:2608.23041) ★ HIGH
Offline failure-trace diagnosis → structured harness patches → validation-gated accept.
**Applied to:** `self-improve-agent`

### Interaction Tax (arXiv:2608.23541) ★ HIGH
Full-solution peer exchange erases multi-agent diversity in one round. Independent proposals first; parent synthesis second.
**Applied to:** `dispatching-parallel-agents` (full rule), `autonomous-ai-agents` (pointer only — SkillZip)

### CatchBench PRE/LIVE/POST (arXiv:2608.22808) ★ HIGH
Catch failures at earliest information state (config / live prefix / finished trace).
**Applied to:** `verification-before-completion` (elevated from sweep-26 SKIP)

### Config/code promote-threshold sync + FAMA gen_gap ★ HIGH (runtime)
`config.yaml` promote_thresholds aligned to l1-promote gates; scripts load caps from config;
stale-reuse and recall annotate `gen_gap_days`.
**Applied to:** `config.yaml`, `l1-promote.py`, `memory-ttl-purge.py`, `unified-recall.py`, `l1-graphiti-write.py`

### Defer discipline (Sweep 27 user follow-up) ★ HIGH (process)
Bare "Explicitly not built" lists are incomplete. Required matrix + residual naming live in
Maintenance Notes §8 and `references/sweep-27.md`. Highest unfinished high-benefit items:
MemSIF topical/event (only after arc-recall pain) and Graphiti hard eviction (only at capacity).

---

## Technique Class: Operational State + Working Memory Topology (Sweep 28)

### Constraint Weakening (arXiv:2608.24569) ★ HIGH
Handoffs/compaction rewrite must→maybe. Constraints are operational state with binding force.
**Applied to:** `handoff`, `hermes-context-packet`, `focus_compress.py`, `constraint-binding-lint.py`, `config.memory.handoff`

### Handoff Tax (arXiv:2608.24358) ★ HIGH
Full trajectory on model switch recovers <50% of native quality. Prefer structured WM + constraints.
**Applied to:** `handoff`, `working-memory.py handoff-export`, config `full_trajectory_on_model_switch: false`

### Recuris WM vs Experiential (arXiv:2608.24876) ★ HIGH
Skill selection from working memory needs; durable lessons stay experiential (Hindsight/skills).
**Applied to:** `working-memory.py`, context-packet `working_memory_ref`, runtime-loop OODA

### Paritok intent-conditioned extractive compress (arXiv:2608.24188) ★ HIGH
Cold offload conditioned on current task goal; prefer extractive spans.
**Applied to:** `l1-context-offload.py --intent`, `focus_compress.py`, config `compression.intent_conditioned_offload`

### OODA-Tool state/action split (arXiv:2608.24368) ★ HIGH
**Applied to:** `agent-runtime-loop-patterns`

### Belief miscalibration at action (arXiv:2608.24691) ★ HIGH
Never gate HAZARD on self-reported confidence alone.
**Applied to:** `trajectory-risk-guardrail`

### Runtime: web.search_backend brave → brave-free ★ HIGH
Provider registry id is `brave-free` (post-plugin web backends). Misname → NotFoundError.
**Applied to:** `config.yaml`

### MED: StepGuard checklist (2608.24777), PeakBench parallel (2608.24509)
**Applied to:** trajectory-risk-guardrail + runtime-loop decision guide (SkillZip; no new skills).

### Defer (see matrix in sweep-28.md)
CAFE/SMITH/RePolicy train-time; MemSIF/Graphiti hard eviction still pain-gated; StarHarness/SkillForge → AutoSaddler already owns offline harness evolution.

---

## Technique Class: Harness Compilation from Execution (Sweep 18)

### Evo-Harness — Context-to-Harness Skill Compilation (arXiv:2608.15071) ★ HIGH

Formulates "online harness learning" as continual compilation of noisy single-shot execution contexts into structured, reusable skill harnesses. Evaluated across five benchmarks (TerminalBench2, SWE-bench, CL-Bench, WebArena-Infinity). The "frozen agent + evolving harness" split: agent core stays fixed, improvement flows through harness/skill layer only.

Key: strip task-specific artifacts (filenames, IDs, branch names) before distilling cross-domain lessons into the harness. Group by topic cluster; update harness only when cluster size ≥ 3 (avoids noise from sparse execution).

Reference implementation: github.com/A-EVO-Lab/a-evolve/tree/release/evo-harness

**Applied to:** `agent-runtime-loop-patterns` (Context-to-Harness Compilation section), `agent-memory-consolidation`, `ralph-loops` (Harness-Update Phase section), `hermes-context-hygiene`
**Status:** writable — patches applied (Sweep 18)

---

## Technique Class: Path-Dependent Experience Interference (Sweep 18)

### PATH-Bench / SEU — Selective Experience Use (arXiv:2608.01149) ★ HIGH

First benchmark measuring how the *ordering and composition* of accumulated experience causes forward transfer, backward interference, and forgetting in lifelong LLM agents. SEU harness: score each stored experience item for relevance vs. interference risk before injecting into context; admit only items where relevance > interference.

Evaluated on 8 representative agents across code generation and multi-turn tool-use. PATH-Bench is categorically distinct from AgentMemBench (fidelity), OBLIVION (unlearning), and RRM (lifecycle decay) — it measures causal path effects on current task performance.

**Applied to:** `agent-memory-consolidation` (SEU Filter section), `ralph-loops` (SEU Filter Between Iterations section)
**Partial targets:** `hermes-memory-surface-selection` (path-dependency check principle noted in skill), `hindsight-stack-operations` (task-type annotation for SEU-aware retrieval)
**Status:** writable — core patches applied (Sweep 18)

---

## Technique Class: Goal-Structure Alignment Failure (Sweep 18)

### Post-Incident Goal Drift Analysis (Interconnects.ai, Aug 9 2026) ★ MED

Post-mortem of Aug 2026 Anthropic/OpenAI production agent incidents: alignment failures arose from misspecified goal structures, not capability failures. Goal drift (intermediate objectives diverging from session intent) is the failure mode, not jailbreak or capability limits.

**Applied to:** `adversarial-review` (Pre-Task Goal Structure Audit section), `trajectory-risk-guardrail` (Goal Drift Guardrail section)
**Status:** writable — patches applied (Sweep 18)

---

## Technique Class: Agent-Native Model Cost Horizon (Sweep 18)

### Token-Efficiency Crossover — NVIDIA Agent-Native Model Thesis (Interconnects.ai, Aug 18 2026) ★ MED

NVIDIA thesis: inference-efficient agent-native models will displace API-locked cloud models for skill-invocation-heavy workloads, creating a cost-efficiency crossover. The "fishing for tokens" framing validates aggressive context compression not just for cost but for portability.

Implications: (1) track per-skill-invocation token cost now as baseline for future crossover measurement; (2) design skills to be model-agnostic, routed by task complexity not model capability assumptions; (3) annotate skills with token cost class (low/medium/high) for routing use.

**Applied to:** `hermes-context-budgeting` (Agent-Native Model Cost Horizon section)
**Status:** writable — patch applied (Sweep 18)

---

## Technique Class: Bounded KV-Cache Long-Horizon Memory (Sweep 24)

### ReWorld — Landmark Bank + Per-Head Routing (arXiv:2608.23565) ★ HIGH

Fixed-budget long-horizon memory via bounded KV cache backed by a pose-indexed landmark bank.
Mixed per-head attention: short-horizon heads + long-horizon global heads routed separately.
Achieves 64s / 384-latent fixed budget without growing context.

**Hermes application:** The short-horizon/long-horizon head split maps to Hermes's
hindsight memory design — active session (short horizon) vs. Graphiti/Hindsight (long horizon).
Key insight: l1-promote.py should keep fact selection bounded at inference time rather than
accumulating unbounded context; the landmark bank pattern (fixed-index retrieval) justifies
the existing stable/volatile/ephemeral tier design. <!-- why: unbounded context accumulation
is the core problem ReWorld solves; bounded retrieval is the correct long-horizon architecture -->

**Applied to:** `agent-memory-consolidation` references/sweep-24-findings.md
**Status:** reference file written; no direct script change required (architecture validation)

---

## Technique Class: Action-Layer Threat Detection (Sweep 24)

### NL-Policy Gap + Tool-Sequence Anomaly + AIREP (Sweep 24) ★ HIGH

Three coordinated sweep-24 security findings applied to am-sentry.py:

1. **NL-policy gap** (arXiv:2608.23550 — "When 'Do Not' Is Not Deny"): natural-language deny
   rules in system prompts are interpreted, not enforced. am-sentry now scans for injected
   instructions that exploit semantic gaps around NL policy boundaries via `NL_POLICY_BYPASS`
   regex constant and `scan_action_layer()`.

2. **Tool-sequence anomaly** (arXiv:2608.22248 — Latent Instruction Manifolds): indirect
   prompt injection exploits gaps between surface cues and deep instruction manifolds. Anomaly
   detection in `scan_action_layer()` now flags tool sequences that deviate from baseline
   call patterns.

3. **AIREP-compatible signed decision records** (l1-tracegrant.py): `tracegrant_log_grant()`
   now records `taint_path` (provenance chain like "l1-extract→l1-promote"), HMAC
   `decision_hash` over canonical fields, and `tracegrant_verify()` checks hash integrity.
   <!-- why: taint tracking enables rollback repair (arXiv:2608.10502) without full trace replay -->

**Applied to:** `am-sentry.py` (action-layer scan), `l1-tracegrant.py` (taint_path + AIREP)
**Status:** scripts patched; all 5 scripts pass py_compile; 32-point ad-hoc verification passed

---

## Technique Class: Memory Lifecycle — FAMA Staleness + Type-Conditioned TTL (Sweep 24)

### FAMA Staleness Logging + ScrubJay Type-Conditioned Decay (Sweep 24) ★ HIGH

Two memory lifecycle improvements applied to memory-ttl-purge.py:

1. **FAMA-style staleness detection**: stale memory reuse tracking — log when expired entries
   are accessed before purge (stale_reuse log). Enables post-hoc audit of decisions made
   with stale facts.

2. **Type-conditioned volatile TTL** (ScrubJay-MEM, arXiv:2608.04746): preference-type facts
   get 14d volatile TTL vs 30d for general facts. Per-memory-type perishability coefficients
   are the key ScrubJay contribution — global decay lambda is insufficient.
   <!-- why: preference memories go stale faster than stable procedural facts — uniform TTL
   causes either over-retention or premature deletion depending on memory type -->

**Applied to:** `memory-ttl-purge.py`; type-conditioned TTL via `VOLATILE_PREFERENCE_TTL`
**Status:** scripts patched; reference file: agent-memory-consolidation/references/sweep-24-findings.md

---

## Technique Class: Promote Threshold + Cold-Fact Penalty (Sweep 24)

### l1-promote: Stable Threshold Raise + Retrieval-Frequency Signal (Sweep 24) ★ MED

Two changes to l1-promote.py:

1. **Stable promote threshold raised 0.35 → 0.45** with a retrieval-count gate (N ≥ 2
   retrievals required for stable promotion). Cold facts (never retrieved) face a penalty
   coefficient in `compute_retention_score()`. <!-- why: sweep-24 context budgeting finding
   confirmed that false-positive promotions fill Hindsight with low-utility facts,
   reducing retrieval precision — raising the bar corrects this -->

2. **Gate reason logging**: skip log now includes gate failure reason
   (`ret=X<threshold or rec=N<min_recurrences`) for observability.

**Applied to:** `l1-promote.py`
**Status:** script patched

---

## Technique Class: Graphiti Entity Deduplication (Sweep 24)

### Entity Dedup Pre-Write Check + Session-Completion Trigger (Sweep 24) ★ MED

Two additions to l1-graphiti-write.py:

1. **Entity dedup**: before writing each episode, `search_nodes_for_entity()` queries
   Graphiti for existing nodes matching the fact's primary entity. Logs a dedup note when
   found — Graphiti's own merge semantics then handle the actual merge. Prevents episode
   bloat from repeated entity creation.

2. **`--on-session-complete` flag**: triggers a session-boundary write (only facts from
   most recent session) immediately when a session ends, complementing the 4h cron write.
   <!-- why: LiCoMemory and G-Memory both validate tri-tier KG with session-completion trigger
   for bi-directional retrieval (insight + interaction nodes) -->

**Applied to:** `l1-graphiti-write.py`
**Status:** script patched

---

## Technique Class: Prompt-Caching Self-Consistency Fast Path (Sweep 24)

### Self-Consistency via Prompt Caching (HN Aug 2026) ★ MED

HN thread observation: prompt caching (Anthropic extended cache) makes self-consistency
sampling cheap — most of the prefix is stable across N draws, so only the sampled completion
incurs full token cost. This changes the economics: self-consistency is now viable for
MED-confidence decisions, not just HIGH-stakes decisions.

**Applied to:** `hermes-swarm-consensus` (prompt-caching fast path section)
**Status:** skill patched

---

## Technique Class: Gisting Turn-Boundary Compression (Sweep 24)

### Gisting — Semantic Boundary Compression (HN/web, Aug 2026) ★ MED

Compress at turn boundaries using semantic summary ("gist") rather than token truncation.
Unlike `micro_compact`, gisting runs immediately when a turn closes, not on a schedule.
Gist nodes replace raw turn content in context but remain expandable on demand.

**Applied to:** `hermes-context-budgeting` (Gisting section)
**Status:** skill patched

---

## Technique Class: Memory Capture Architecture (github:akitaonrails/ai-memory, Aug 2026)

### ai-memory — Three Practitioner Patterns (github:akitaonrails/ai-memory, 2.3k stars) ★ MED

A Rust MCP memory server for cross-agent handoff (Claude Code → Codex → Cursor etc.) that explicitly studied Hermes's self-improvement loop for its auto-improvement design. Not a tool to install — three architectural patterns worth integrating:

**1. Drop-before-spool capture exclusion:** Before a hook event enters the storage pipeline, a nearest-marker policy drops any event that touches the memory store itself (self-referential writes). Prevents the memory system from logging its own writes. Cleaner than post-write PSE contamination detection.

**2. Hard size caps at the write boundary:** 16 KB max per durable memory body; 2 KB max for tool excerpts. Truncated before reaching the embedding layer. Bloated entries degrade vector retrieval precision by mixing signal with noise in a single embedding.

**3. Fast/slow consolidation split + `_pending/` staging:** Fast pass (minutes after session) extracts lessons and stages proposals. Slow pass (weekly) deduplicates, merges, and applies. Autonomous improvement proposals from cron/agents write to a staging area first — not directly to memory. Approval policy is separate from the review loop.

**Applied to:**
- `hindsight-stack-operations` (Memory Write Size Discipline section)
- `agent-memory-consolidation` (Fast/Slow Consolidation Split section)
**Status:** writable — patches applied (Sweep 18 addendum)

### Sweep 29 Findings Log (2026-08-29) — Cutoff: above arXiv:2608.24885

**New cutoff after Sweep 29: arXiv:2608.27454**
Sources: arXiv cs.AI/CL/MA/LG recent listings; GitHub; Hacker News; Habr (RU); Zenn.dev/Qiita (JP)
22 papers reviewed above cutoff. 7 HIGH, 5 MED applied. All implementations verified with py_compile.

---

## Technique Class: Harness Evolution + Verification (Sweep 29)

### JIT-Agent: Harness as Composable Machine-Generatable Artifact (arXiv:2608.25593) ★ HIGH

Harness contribution dominates model contribution for long-horizon tasks. JIT-Agent trains a
harness-intelligence model that synthesizes task-adaptive harnesses as 4-module protocols:
Goal Spec → Decomposition → Execution Graph → Verification Hooks. Self-evolves by distilling
performance signals from an expanding archive of execution traces.

**Applied to:** `harness-first-agent-design` (Sweep 29 Additions section)
**Status:** skill patched

---

### Verify Smarter / HarnessLens (arXiv:2608.27311) ★ HIGH

Behavior-aware verification for harness evolution. Verification must observe behavioral
invariants (not just output diffs) when evolving a harness. Prevents false-positive passes
when output format changes but semantic meaning degrades.

**Applied to:** `harness-first-agent-design` (Sweep 29 Additions section)
**Status:** skill patched

---

## Technique Class: Mutable Execution State (Sweep 29)

### SKILL.state: Replace Append-Only History for Long-Horizon Tasks (arXiv:2608.26263) ★ HIGH

For tasks exceeding ~10 steps, replace conversation history with a compact mutable state:
`{goal, completed_steps[], current_step, observations[], pending_decisions[]}`. Each step
receives only (1) immutable skill spec, (2) current state, (3) last N observations.
Reduces context growth from O(N²) to O(N). 32% latency reduction, 18% accuracy gain.

**Applied to:**
- `autonomous-agent-loop-design` (Sweep 29 Additions section — SKILL.state)
- `skill-state.py` (new script: ~/.hermes/scripts/skill-state.py)
- `config.yaml` (skill_state: enabled, gc_after_hours: 24)
**Status:** script written, skill patched, config updated

---

## Technique Class: Tool Authorization (Sweep 29)

### Tool-Output-as-Command Guard (arXiv:2608.27146) ★ HIGH

Tool outputs can become implicit "commands" driving subsequent agent actions — a
prompt-injection vector in disguise. Separate action induction (what to do) from runtime
authorization (allowed to do it). Track source tier per tool call: user/system = trusted,
external-fetch/agent-generated = untrusted. Log and warn on EXTERNAL-tier → high-risk action.

**Applied to:**
- `tool-auth-gate.py` (new script: ~/.hermes/scripts/tool-auth-gate.py)
- `config.yaml` (tool_auth: enabled, governance_primitives section)
**Status:** script written, config updated

---

### Five Governance Primitives for AI Agents (arXiv:2608.26696) ★ HIGH

Runtime agent governance requires five primitives: (1) Discovery — how agents find each other;
(2) Identity — stable agent identity across sessions; (3) Governance — policy enforcement;
(4) Attestation — verifiable capability claims; (5) Supply Chain — provenance of tools/skills.
Log-mode for attestation/supply_chain; enforce for discovery/identity/governance.

**Applied to:** `config.yaml` (tool_auth.governance_primitives)
**Status:** config updated

---

## Technique Class: Retrieval Routing (Sweep 29)

### CaSKG: Counterfactual-Causal Skill Graphs (arXiv:2608.25500) ★ HIGH

Reusable skill libraries turn memory access into a retrieval problem. CaSKG builds a
directed acyclic graph where edges represent counterfactual skill-success relationships
(skill A succeeds iff skill B has run). Enables principled skill sequencing and dependency
resolution. Retrieved skills carry their causal preconditions.

**Applied to:** `harness-first-agent-design` (CaSKG section)
**Status:** skill patched; full DAG implementation is a future sprint item

---

### GraphMemix: Query-Aware Evidence Forest Retrieval (arXiv:2608.26983) ★ MED

Query-type routing for recall: structural queries (what is X, define, relate) → heavier
Graphiti weight; episodic queries (when, which session, what happened) → heavier Hindsight.
Prevents query-type mismatch from degrading retrieval quality.

**Applied to:** `unified-recall.py` (GraphMemix query-type routing block in fuse_results)
**Status:** script patched

---

## Technique Class: Agent Safety + Reliability (Sweep 29)

### Agent Mesh Reliability Primitives (arXiv:2608.26225) ★ HIGH

Production study of agent mesh failures. Key finding: circuit-breaker assumptions violated
by long-tail token generation. Adds: (1) progress-rate breaker — zero-error loops that make
no real progress; (2) event budget — cap total events per delegation chain; (3) diverse-agent
fallback — 2 diverse agents sometimes outperform 16 homogeneous ones.

**Applied to:**
- `config.yaml` (no_effective_progress: 5, delegation_event_budget: 50)
- `autonomous-agent-loop-design` (Sweep 29 section — LivePlan progress guardrail)
**Status:** config patched, skill patched

---

### INTENT-AS-A-TOOL: Semantic Intent Drift Tracking (arXiv:2608.27348) ★ MED

Track semantic drift between user's stated intent and agent actions. Detect: goal-rewrite
language, external-content-to-system-command tool sequences, high-autonomy ratio (few user
checkpoints over many assistant turns).

**Applied to:** `am-sentry.py` (scan_intent_drift function, wired into main)
**Status:** script patched

---

## Technique Class: Memory Calibration (Sweep 29)

### Calibration Gate: Authoritative Display Despite Uncertainty (arXiv:2608.27167) ★ MED

Agents commit to uncertain actions when evidence looks authoritative. Flag facts that mix
uncertainty hedges (may, might, perhaps, unclear) with authoritative surface language
(always, never, definitely, proven). These are highest-risk for downstream over-commitment.

**Applied to:**
- `l1-promote.py` (calibration_flag function + cal_warn tag in STAGE log)
- `config.yaml` (calibration_gate: enabled, commitment_threshold: 0.3)
**Status:** script patched, config updated

---

## Technique Class: Experience Context Binding (Sweep 29)

### BCIT: Bind Experience to Source Context Before Reuse (arXiv:2608.26730) ★ MED

Constraint reuse without source context causes silent failures across model/data generations.
Constraint schema extended with: `source_context` (e.g. "session:abc" or "skill:name"),
`predecessor_model` (model that learned this constraint). Schema bumped to v2.

**Applied to:** `working-memory.py` (constraint entry schema, BCIT fields, v2 bump)
**Status:** script patched

---

## Technique Class: Skill Evolution (Sweep 29)

### WikiSkill: Co-Evolving Skill + Wiki Knowledge Base (arXiv:2608.27454) ★ MED

Each skill co-evolves with a structured wiki: raw execution separates from optimization
insight. Wiki entries: description, typical_inputs, success_patterns, failure_modes,
optimization_notes, linked_skills. Skills stay clean; lessons accumulate in wiki.
Prune entries stale >90 days.

**Applied to:**
- `skill-wiki.py` (new script: ~/.hermes/scripts/skill-wiki.py)
- `config.yaml` (skill_wiki: enabled, upsert_on_skill_update: true)
- `skill_prune_audit.py` (wired wiki-prune into weekly audit)
**Status:** script written, config updated, wired into prune cron

---

### MemToC: Tools Override Parametric Memory Even When Wrong (arXiv:2608.26295) ★ MED

Tools dominate parametric memory 86-93% of the time even when tool output is wrong.
Design implication: tool output verification matters more than model internal knowledge
correction. MemToC confirms tool-auth-gate tier separation is the right intervention point.

**Applied to:** `harness-first-agent-design` (MemToC section — confirms tool_auth_gate)
**Status:** skill patched (confirms existing design, no new code needed)

---

## Skipped / LOW Priority (Sweep 29)

- arXiv:2608.26788 Decoupling Planning and Control — conceptually covered by SKILL.state
- arXiv:2608.27086 Contract-Centered Architecture — covered by constraint-binding-lint.py
- arXiv:2608.27102 LAAF governance survey — survey only, Five Primitives is the actionable extract
- arXiv:2608.27128 TwinKV KV cache repair — KV cache ops not in Hermes scope
- arXiv:2608.27260 What Makes Good Agentic Data — training data, not runtime
- arXiv:2608.27334 BTS-AgentBench — benchmark, no novel mechanism
- arXiv:2608.27338 One Model Many Minds (MoRe) — covered by hermes-swarm-consensus
- arXiv:2608.26867 BekchiAI — observability benchmark, no new runtime pattern
- arXiv:2608.26626 Risks and Controls Multi-Agent — covered by Five Primitives
