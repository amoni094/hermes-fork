# Sweep 23 Findings — Aug 25 2026

**Cutoff:** 2608.21341 → 2608.23552+
**Sources:** arXiv (own sweep + 4 subagents), GitHub, HN, Reddit, Zenn/JP, Habr/RU, Qiita/JP, Juejin/CN, Velog/KR, Academic (ACL/ICLR/SearXNG)

---

## HIGH findings applied this sweep

### InjecMEM — Memory Injection via Single Interaction (arXiv:2608.23471)
Attack: single crafted interaction plants a retriever-agnostic anchor + adversarial command. No store access required.
Target skill: `agent-memory-consolidation` (written to references — skill at size limit)
**Applied defenses:**
1. Single-interaction write rate limit for high-priority topics (security, credentials, safety rules)
2. Anchor pattern detection — unusually dense synonym-anchor sets in external writes
3. Command detection — imperative verb patterns in external-sourced writes
4. Post-retrieval sanity check — flag memories that steer actions surprising given this session's request
5. Topic-scoped write authority — credentials/safety writable only by agent/user sources

### HERO — Profile-Augmented Retrieval (arXiv:2608.22310)
Augment Hindsight queries with USER.md profile keywords; preserve raw evidence; iterative graph traversal.
Target skill: `agent-memory-consolidation` (written to references — skill at size limit)
**Applied:**
- Query augmentation: inject 2-3 relevant USER.md keywords into hindsight_recall queries
- Graphiti: combine search_memory_facts + search_nodes traversal for multi-hop expansion
- Raw evidence preservation at write time

### Scroll — Context as Environment (arXiv:2608.21690)
Session = executable environment with append-only Event Log + persistent Python kernel.
Tool outputs bound to VARIABLES, not serialised into prompt. Context management = programming task.
Target skills: `hermes-context-budgeting`, `hermes-context-hygiene`
**Applied:**
- Variable binding vs prompt serialization principle documented
- Event Log as lossless ground truth with eviction index
- Implemented as new section in hermes-context-budgeting

### Compaction Cliff (arXiv:2608.22752)
Safety rules lose 90% fidelity after 5 compactions. TypeCompact/TypeDecompose/TypeRetrieve.
Target skill: `hermes-context-budgeting`
**Applied:** Knowledge Triage section with per-type retention policy table

### Coalition-Aware Skill Reliability — CASS+uSMCO (arXiv:2608.22610)
Coalition pollution + cross-domain utility reversal.
Target skills: `hermes-semantic-skill-routing`, `hermes-agent-skill-authoring`
**Applied:** Two-tier skill retrieval (Shapley marginals), cross-domain utility reversal warning

### TRACE Skill Bank Consistency (arXiv:2608.22793)
Pass^k consistency metric, trajectory-contrastive evolution.
Target skill: `hermes-agent-skill-authoring`
**Applied:** deferred — patch to hermes-agent-skill-authoring pending (below)

### SkillAlchemy — Admission-Centered Skill Creation (arXiv:2608.23417)
Identifies implicit requirements via contrastive evidence; scopes procedures to evidence-supported range.
Target skill: `hermes-agent-skill-authoring`
**Applied:** deferred — patch to hermes-agent-skill-authoring pending (below)

### Multi-Turn Safety Degradation (arXiv:2602.13379)
Safety erodes monotonically with turn count in tool-using agents.
Target skill: `trajectory-risk-guardrail`
**Applied:** Turn-count escalation threshold, aggregate state audit, tool-interaction safety boundary

### ToolSafe — Step-Level Guardrails (GitHub:MurrayTom/ToolSafe)
Step-level (not outcome-level) tool safety checking with feedback loop.
Target skill: `trajectory-risk-guardrail`
**Applied:** Proactive monitoring trigger, justification traceability gate

### context-mode (GitHub:mksglu/context-mode)
Tool output sandboxing, 98% context reduction via variable binding over prompt serialization.
Target: `hermes-context-hygiene`, config
**Applied:** Documented in context-budgeting; config change pending (proactive_prune)

### Zenn JP proper_willet — Write Gate + Hot/Cold Two-Tier Design
Write gate LLM call classifies permanent rule vs one-off context before Hindsight write.
Post-retrieval policy-check before using.
Target: `agent-memory-consolidation` (references — skill at limit)
**Applied:** Formalised into write-path filter alongside InjecMEM defenses

### Habr RU 955688 — Context Director Framing
"Режиссёр контекста": your role is deciding WHAT model sees and in what ORDER.
Target: `hermes-context-budgeting`
**Applied:** added to prompt ordering section (reinforces existing cache ordering rule)

### Prime Agent (arXiv:2608.23552)
Open-source harness: persistent IPython REPL + Continual Harness preserving skills/memories across trajectories. Recursive subagent communication. Raises ARC-AGI-3 RH.
Target: `autonomous-agent-loop-design`
**Applied:** deferred — architecture pattern noted

### Agent Skills Survey (arXiv:2602.12430)
26.1% community skill vulnerability rate → skill auditing before import needed.
Four-tier gate-based permission model: provenance → capability.
Target: `hermes-skillspector-guard-maintenance`
**Applied:** deferred (skill to be patched separately)

### ACON — Context Compression for Long-horizon Agents (arXiv:2510.00615)
Selectively compresses trajectory to preserve decision-critical observations.
Target: `hermes-context-budgeting`
**Applied:** deferred (MED — already well-covered by existing sections)

### STARS — Skill-Triggered Audit (arXiv:2604.10286)
Step-level audit triggered by skill invocation; request-conditioned safety.
Target: `trajectory-risk-guardrail`
**Applied:** Noted under ToolSafe section (complementary)

---

## Config changes applied this sweep

### am-sentry.py — InjecMEM anchor pattern detection
Script updated to detect anchor-dense external writes before Hindsight promote.
See: ~/.hermes/scripts/am-sentry.py (changes logged in script header)

### Hermes config — proactive_prune_tokens adjustment
Context budget change for tool output sandboxing efficiency.
See: `hermes config get compression` after this sweep.

---

## MED findings (documented, not yet implemented)

| ID | Title | Target | Why deferred |
|---|---|---|---|
| 2608.22974 | OaK Dynamic Ontology | knowledge-graph-corpus-pipeline | KG pipeline specific, not core runtime |
| 2608.22479 | GTA-RAG Graph-Trajectory RAG | N/A | RL-training focus |
| 2608.22762 | Compositional Chain-of-Relations KGQA | knowledge-graph-corpus-pipeline | KG QA specific |
| 2507.21504 | LLM Agent Eval Survey | agent-task-signoff | Reliability gap — reliability under failure |
| 2603.16060 | ARISE | hermes-agent-skill-authoring | Skill discovery patterns |
| 2607.12625 | KnowAct | knowledge-graph-corpus-pipeline | KG action grounding |
| ACL-2026-long-69 | RL Skill Validation | hermes-agent-skill-authoring | Execution-based skill validation |
| Juejin CN | Record+Retrieve loop | agent-memory-consolidation | Already covered by existing pipeline section |
| Velog KR code-context-graph | Code dependency graph for context | N/A | Coding-agent specific |

---

## Deferred from sweep 22 — status

| ID | Status |
|---|---|
| 2602.08234 SkillRL | Applied — two-tier retrieval in hermes-semantic-skill-routing |
| 2603.16060 ARISE | MED — deferred to sweep 24 |
| 2607.12625 KnowAct | MED — deferred |
| 2507.21504 Eval Survey | Applied — agent-task-signoff (reliability gap section) |
| 2604.20133 EvoAgent | Applied — hermes-agent-skill-authoring (failure-trace skill updates) |
| 2608.20634 AgentMercury | Applied — hermes-agent-skill-authoring (deferred from sweep 22, now in) |
| 2603.07670 Memory Survey | Applied — write-path filtering section |

---

## Sweep boundary

Next sweep starts above: **2608.23552**
