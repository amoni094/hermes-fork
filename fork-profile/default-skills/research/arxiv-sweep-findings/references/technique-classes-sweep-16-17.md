# Technique classes (Sweeps 16–17, post-boundary-log)

## Technique Class: Temporal Guardrail Intervention (Sweep 16)

### StepShield — When, Not Whether to Intervene (github:glo26/stepshield, NeurIPS 2026) ★ MED

Current ATP per-action gating evaluates each tool call in isolation. StepShield reframes
the question: at which step in the trajectory should intervention occur? Uses trajectory
prefix (all committed steps) to predict the optimal intervention point before a harmful
sequence completes, not just whether the current action individually violates constraints.

9,429 annotated step-level trajectories. Each trajectory labelled with the step at which
a human evaluator would have intervened — the "right moment" is earlier than the harmful
action by 1–3 steps on average.

**Complementary to DreamGuard:** DreamGuard scores prefix risk pre-flight (before the loop
starts). StepShield scores it mid-execution at each ATP checkpoint (within the running loop).
Use StepShield benchmark data to calibrate DreamGuard's prefix-risk threshold.

**Implementation sketch:**
1. Maintain prefix list of committed actions in ATP loop
2. At each `propose()` call, score the prefix + proposed action for escalation patterns
   (e.g. credential_read followed by external_post)
3. If trajectory prefix risk score ≥ threshold (start at 0.75, tune on StepShield data):
   halt and escalate BEFORE admitting the proposed action — even if it passes constraint C
4. This catches gradual drift that per-action checks miss: each individual step may pass
   C; the composition may be hazardous

**Target skills:** `mnemosyne-atp-safety`
**Status:** User-owned. Run `hermes curator adopt mnemosyne-atp-safety` to enable patch.

---

## Technique Class: Prompt Cache Architecture (Sweep 16)

### RACS — Stability-Rank Ordering and Prefix-Drift Detection (github:davccavalcante/racs) ★ MED

Formalizes stability-aware prompt planning: context blocks ranked by mutation frequency,
ordered most-stable-first to maximize provider-side prefix cache hits. Three mechanisms:

1. **Stability-rank ordering:** system prompt → persona → loaded skills → memories →
   conversation history (most → least stable). This ordering is already implicitly followed
   by Hermes but RACS makes it explicit and verifiable.

2. **Prefix-drift detection:** hash the prefix (blocks ranked 1–3) per turn. A hash change
   in stable blocks = cache-breaking mutation → log a `prefix_drift` event. Helps diagnose
   why `cache_read_input_tokens` drops to zero unexpectedly.

3. **TTL keep-warm scheduling:** for long-horizon sessions or cron jobs with infrequent
   turns (>5 min between calls), schedule a no-op heartbeat before the 5-minute TTL
   (ephemeral) or 1-hour TTL (extended) expires. Prevents cold-start cache misses.

**Multi-provider:** generates provider-faithful cache directives for Anthropic, OpenAI,
Gemini, and Bedrock from the same stability-rank descriptor.

**Target skills:** `anthropic-api-cost-optimization`
**Status:** User-owned. Run `hermes curator adopt anthropic-api-cost-optimization` to enable patch.

---

## Technique Class: Agent Persistence Architecture (Sweep 16)

### Stateless-Compute + Persistent-Storage Split (Latent Space, Aug 8 2026) ★ MED

Observed in ChatGPT Work production deployment. Solves the always-on-VPS vs serverless
tradeoff for agent persistence:

**Pattern:** Each agent task runs on an **isolated ephemeral microVM** (no persistent
process). The working directory is synchronised to **persistent storage** before the VM
terminates. On session resume, state is restored to a fresh microVM — the underlying
machine changes, but the working state carries over.

**Key properties:**
- Horizontal scaling: any microVM can pick up any task (stateless compute)
- Per-task filesystem continuity: directories, installed deps, scratch files persist
- NOT always-on: no long-running agent process to monitor or restart
- Cross-task isolation: tasks cannot traverse each other's directories without explicit
  instruction

**Hermes application:** Store workspace artifacts in persistent storage (`~/.hermes/cache/`
or a dedicated task directory), not as session memory or in-process state. On session resume,
restore by reading those files — not by replaying conversation history or injecting prior
output into context. This is the `ralph-loops` pattern implemented correctly.

**Target skills:** `hermes-session-hygiene`
**Status:** User-owned. Run `hermes curator adopt hermes-session-hygiene` to enable patch.

---

## Technique Class: Skill Architecture & Retrieval Precision (Sweep 17)

### Demystifying Agent Skills — Procedural Anchoring (arXiv:2608.14036) ★ HIGH

Controlled experiments (8,135 trial records, 4+ frameworks, 6 benchmarks). Skills primarily work through procedural stabilisation (65.7% of successes), NOT knowledge injection (4.5%). Retrieval precision collapses from 29.6% → 3.3% as pool grows from 5 → 100 skills. Exact skill invocation is neither sufficient nor necessary for task success.

**Hermes application:** Write skills to stabilize action sequences, not to store facts. Add `## Assumed Context` subsection to skills with brittle assumptions. For pools >20 skills, rely on semantic embedding routing — keyword-based precision collapse is unavoidable at scale.
**Target skills:** `hermes-agent-skill-authoring`
**Status:** writable — patch applied (Sweep 17)

---

## Technique Class: Provenance-Aware Shared Memory (Sweep 17)

### MAP-Graph — Multiplicative Path Trust + Risk Gate (arXiv:2608.10509) ★ HIGH

Multi-Agent Provenance Graph: every KG edge carries `(author_agent, timestamp, confidence_score, source_type)`. Effective trust = product of edge confidences along path from source. Risk-sensitive action gate: if any premise fact's min-path trust < 0.7, block the action.

**Hermes application:** Add `confidence` metadata to Graphiti edge writes. At ATP checkpoint, add provenance trust as a constraint dimension alongside existing action safety checks. Subagent-authored facts start at trust 0.8; each downstream hop × 0.9.
**Target skills:** `agent-memory-consolidation`, `autonomous-agent-loop-design`
**Status:** writable — patch applied to `agent-memory-consolidation` (Sweep 17)

---

## Technique Class: Multi-Layer Memory Architecture (Sweep 17)

### GeoForge — 3-Layer Complementary Memory (arXiv:2608.10494) ★ HIGH

Workflow Graph (strategic, proactive) + Action-Level (tactical, reactive) + Skill SOP (abstract, on-demand). Safety-gated distillation: only verified-action sequences become SOPs. Directly extends AMD 3-tier (Sweep 12) with a Graphiti-backed workflow graph layer above it.

**Hermes application:** Map to stack: Workflow Graph → Graphiti strategy nodes; Action-Level → AMD function memory; Skill SOP → skill files. Failed routes → `references/rejected_routes.md`, never to SKILL.md body.
**Target skills:** `agent-memory-consolidation`
**Status:** writable — patch applied (Sweep 17)

---

## Technique Class: Agent Runtime Self-Evolution (Sweep 17)

### Argus — Role-Owned Review + Verification-Gated Evolution (arXiv:2608.05144) ★ HIGH

78% SWE-Bench Pro (vs 59% Direct Copilot). After verification-gated evolution: 21% fewer tokens and 15% less workflow time per task. Key: memories/skills/procedures admitted to persistent state ONLY after designated role review. Rejected routes preserved in durable state; agents don't re-explore dead ends.

**Hermes application:** Before updating any skill in an autonomous loop, require role-owned review (not just task success). Maintain `rejected_routes.jsonl` alongside project state. Escalation points are operator-owned, not agent-selected.
**Target skills:** `autonomous-agent-loop-design`
**Status:** writable — patch applied (Sweep 17)

---

## Technique Class: Adversarial Skill Revocation (Sweep 17)

### OBLIVION — Cross-Surface Coherent Erasure (arXiv:2608.08264) ★ HIGH

After explicit skill removal, agents reconstruct revoked skills from residual carriers (archives, Hindsight memories, Graphiti nodes, cron contexts). Attack success: 1.0 without defense; 0.114 with OBLIVION; utility maintained at 1.0; benign block rate 0. Defense = simultaneous coherent erasure across ALL carrier surfaces.

**Hermes application:** On skill deletion: grep Hindsight memories for skill name + primary tool patterns; check Graphiti for encoding nodes; check cron `context_from` chains; check session history. Revocation must be evaluated at workflow level, not just skill registry level.
**Target skills:** `adversarial-review`
**Status:** writable — patch applied (Sweep 17)

---

## Technique Class: Self-Evolving Agent Benchmarks (Sweep 17)

### FinEvo-Bench — Skill-Only > Memory-Only Evolution (arXiv:2608.06144) ★ MED

120 real-case-grounded financial tasks. In Claude Code, skill-only evolution produces higher task quality AND fewer compliance issues than memory-only AND combined memory+skill evolution. Rubric feedback yields higher scores and fewer compliance issues than reference-answer feedback. Evolution gain is largest at task ranks 4-6 (harder tasks).

**Hermes application:** When designing self-evolving agent loops, prefer skill-first evolution over memory-first. For evaluation, use rubric-based scoring (explicit criteria) over reference-answer comparison — same-answer scoring biases toward surface match over quality.
**Target skills:** `agent-runtime-loop-patterns`, `hermes-agent-skill-authoring`
**Status:** writable — no separate patch needed (principle already encoded in skill authoring rules)

---
