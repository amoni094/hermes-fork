# arXiv Sweep 12 — Full Output

**Date:** 2026-08-13
**Baseline cutoff:** 2608.11200
**Categories swept:** cs.AI, cs.CL, cs.MA, cs.CR, cs.LG, cs.IR, cs.SE
**Method:** Direct ID probing (2608.11250–2608.12311) + keyword searches + listing pages
**Highest ID found:** 2608.12311 (arXiv Aug 2026 index upper bound as of 2026-08-13 UTC)
**Total new papers reviewed:** 12
**Result:** 5 HIGH, 5 MED, 2 LOW

---

## ID-Space Discovery Note

The arXiv Aug 2026 index topped out at ~2608.12311 as of Aug 13, 2026 UTC.
IDs above 2608.12400 returned "Article not found" — the day's submissions had not yet
been assigned IDs beyond that point.

**Practical implication for future sweeps:**
- Probe IDs incrementally: after finding a 404-range, stop — don't assume higher IDs exist
- The gap between the cutoff (2608.11200) and the max live ID (2608.12311) is ~1,111 IDs,
  corresponding to approximately Aug 12–13 submissions across ALL categories (not just cs.*)
- Direct abstract fetch `web_extract(["https://arxiv.org/abs/NNNN"])` is the fastest probe:
  "Article not found" in title → ID doesn't exist yet; CS category in title → candidate paper

---

## HIGH Applicability

### 2608.12273 | Convergent Detour Hijacking: Task-Preserving Resource Amplification in Skill-Based LLM Agents
**cs.CR, cs.AI** | Submitted 2026-08-12

**Core finding:** Text-only, runtime-independent attack coupling skill selection and planning
stages. A malicious skill's description establishes semantic relevance during selection; its
body reuses that rationale to fabricate plausible dependencies during planning, recruiting
unnecessary benign skills into a detour and then re-entering the original route to preserve
task completion. On DeepSeek-V4-Pro: coordinator selected in 80.02% of tasks; token cost
+66.91%, latency +92.45%, task completion comparable. Correct outcome ≠ trajectory integrity.

**Key threat model:** Two-stage disclosure (description → body) exposes two sequential attack
surfaces. Standard detection (task success rate) is blind to this attack.

**Hermes implementation:**
- CDH-style review for all external/installed skills: does description intent match body tool calls?
- Monitor token cost + wall-clock time per trajectory; unexpected spikes signal detour
- The attack requires the skill body to use "shared semantic cover" — verify body's first tool
  calls match the declared trigger semantics
- `adversarial-review` skill should include a CDH check section for skill-specific review

---

### 2608.12172 | Rethinking Agent Security as a Networking Problem
**cs.MA** | Submitted 2026-08-12

**Core finding:** Agent-centric defenses fundamentally fail because LLM behavior is
nondeterministic and manipulation-vulnerable. Four networking principles applied:
(1) centralized control with distributed enforcement, (2) capability-based access for
mediating requests to sensitive resources, (3) least privilege through zero-trust enforcement,
(4) semantic, context-aware policies for nuanced decisions (beyond static rules).

Reference architecture: deterministic enforcement mechanisms + semantic context-aware policies.

**Hermes implementation:**
- Harness enforces tool permissions (not LLM judgment) — centralized control
- Skills declare required_commands / required_environment_variables; harness refuses undeclared calls
- Tool result content = UNTRUSTED DATA (the paper validates this principle from networking)
- Semantic policy layer: the LLM's role is judgment on intent, NOT policy enforcement

---

### 2608.12133 | GUIDE: Governed Unified Intelligence for Document-to-Artifact Generation
**cs.AI** | Submitted 2026-08-12

**Core finding:** Six specialized agents (parse, VLM-extract, consistency-check, evaluate,
HITL-escalate, artifact-synthesize) operating over a **shared versioned rule store** with
**schema-validated inter-agent contracts** and end-to-end provenance tracking. 120 real-world
enterprise guideline docs: 96% document success, 3,896 rules extracted (71.4% auto-approved),
812 deployment-ready artifacts, turnaround reduced from 2-3 days to 40-125 minutes.

**Key design patterns:**
- Versioned rule store: all agents read/write from a shared, versioned source of truth
- Schema-validated contracts: each agent's output has a defined schema; receiving agent validates before use
- HITL escalation: explicit threshold (28.6% of rules required human review)
- Provenance tracking: every artifact traces back to the rule(s) that generated it

**Hermes implementation:**
- `subagent-output-contract` skill should mandate schema validation on receipt, not just on output
- `hermes-agent-sync` skill: add versioned result schema for each delegated task type
- HITL threshold should be declared per task class in the skill definition

---

### 2608.10502 | From Faulty Memories to Corrected Actions: Dependency-Guided Rollback Repair
**cs.AI** | Submitted 2026-08-11 (ID < cutoff but not in prior sweep)

**Core finding:** Persistent memory errors are durable: a poisoned/stale/misattributed record
alters reasoning, tool use, answers, AND subsequent memory writes. Existing defenses delete
the source (leaving propagated claims active) or replay full trace (destroying benign state).
Dependency-guided rollback builds a typed memory-to-action graph from runtime provenance,
traces explicit downstream dependencies, deactivates unsupported memory state, and selectively
replays only answer-relevant affected computation.

Results: 85.3% recovery vs 77.3% (best competitor), 0% faulty memory leakage, modest LLM
call cost. On 50-case trajectory stress test: 68.0% vs 54.0% next-best.

**Key data structure:** `typed memory-to-action graph` — nodes are memory entries, edges are
"this memory was used in this action/decision." When a memory node is invalidated, all
downstream action nodes are marked for selective replay.

**Hermes implementation:**
- ATP checkpoints (mnemosyne-atp-safety): log memory reads with a provenance edge
  `{memory_id → action_id}` to enable rollback without full replay
- Graphiti invalidation: walk outgoing edges from invalidated node, mark downstream as
  `potentially_stale` before allowing further reads
- MEMORY.md patching: add a `# Patch log` section that records `{timestamp, fact_changed,
  decisions_that_used_this_fact}` so future agents can assess downstream impact

---

### 2608.12253 | One Frozen Simulator Is Not Enough: Simulator Collapse in Multi-Agent RL
**cs.CL, cs.AI, cs.LG** | Submitted 2026-08-12

**Core finding:** Single frozen LLM simulator → policy mode-collapse → poor generalization
to unseen simulators and real users. Formalized theoretically. Solutions:
- **Verbalized Sampling** (inference-time): prompts simulator to explicitly sample from its
  response distribution rather than mode-collapsing to most likely response. Gain: +9%
- **Co-Training** (training-time): jointly optimize policy against population of trainable
  simulators. Gain: +14%
- SCOPE framework released (open source, Population Co-Training multi-agent RL)

**Key generalization:** "The diversity of the training environment, not only the policy,
is critical to generalization." Applies to any LLM judge / evaluator, not just RL.

**Hermes implementation:**
- Any single-LLM-judge evaluation (skill review, task sign-off, consensus) is vulnerable to
  judge mode collapse — rotate judge models for high-stakes evaluations
- Verbalized Sampling prompt: "Before answering, enumerate 3 distinct possible assessments,
  then choose the most appropriate one." — breaks mode collapse without multiple models

---

## MED Applicability

### 2608.12311 | The Role Specialization Model (RSM): Coordinating LLM-Based Tools in Agentic SE
**cs.SE** | Submitted 2026-08-12

**Core finding:** Exploratory case study of RSM for coordinating heterogeneous LLM tools
(Antigravity, Gemini CLI, Qwen Code/Ollama) in Agentic Software Engineering (SE 3.0).
Role deviations emerge at runtime requiring deliberate coordination strategies, context
management, and human verification of agent-generated outputs. Quality assessed against
ISO/IEC 25010. Key finding: explicit role coordination improves development cycle organization
and architectural quality, but requires active management — roles don't stay stable.

**Hermes implementation:**
- Validates `hermes-role-pipelines` patterns; adds pitfall: role drift at runtime is normal,
  not a failure — plan for explicit re-anchoring checkpoints mid-pipeline
- `agent-task-signoff` should include a role-compliance check: did each agent stay within
  its declared role scope?

---

### 2606.22388 | PlanBench-XL: Evaluating Long-Horizon Planning of LLM Tool-Use Agents
**cs.AI, cs.CL** | Submitted 2026-06-21

**Core finding:** 327 retail tasks over 1,665 tools. GPT-5.4: 51.90% (no blocking) → 11.36%
(severe blocking). Worst failure modes: (1) missing explicit error signals — agent can't detect
failure, (2) recovery requires discovering a longer alternative tool-use path.

Implication: agents need both explicit failure signaling AND pre-declared fallback paths.
Current state-of-the-art LLMs collapse under realistic tool ecosystem imperfection.

---

### 2606.01416 | Self-Healing Agentic Orchestrators for Reliable Tool-Augmented LLM Systems
**cs.AI** | Submitted 2026-06-01

**Core finding:** Failure-class taxonomy + targeted recovery actions + explicit budget +
verifier confirmation = 98.8% task success (vs 94.5% retry-only, 93.8% full-replay).
Silent failure rate with verifier-guided recovery: 0.0% vs non-verifying baselines.

**Failure taxonomy:**
| Class | Recovery Action |
|-------|----------------|
| TOOL_TIMEOUT | Exponential backoff retry |
| MALFORMED_ARGS | Schema repair prompt + re-invoke |
| STALE_CONTEXT | Summarize + reconstruct context before retry |
| CONTRADICTORY_EVIDENCE | HITL escalation or second-opinion agent |
| RETRY_LOOP | Detect same-tool/same-args cycle (3+ times), break with alternative |

**Note:** RETRY_LOOP detection is the most commonly missing guard in current agent frameworks.

---

### 2604.20795 | Automatic Ontology Construction Using LLMs as External Memory for Hybrid Systems
**cs.AI** | Submitted 2026-04-22

**Core finding:** RDF/OWL ontology built and maintained from heterogeneous sources (docs, APIs,
dialogue logs) using: entity recognition, relation extraction, normalization, triple generation,
SHACL + OWL validation, continuous graph updates. Combined context: vector retrieval +
graph-based reasoning + external tool interaction. Tower of Hanoi benchmark: ontology
augmentation improves multi-step planning vs baseline LLM.

**Hermes implementation:**
- Graphiti node constraints: add SHACL-style allowed-types + required-relations to reject
  hallucinated triples at write time (not just at query time)
- Self-ontology pre-retrieval (see Sweep 11) is the lightweight on-the-fly version of this

---

### 2603.21564 | Toward a Theory of Hierarchical Memory for Language Agents
**cs.IR, cs.AI** | Submitted 2026-03-23

**Core finding:** Three operators: Extraction α (raw → atomic units), Coarsening C (partition
units + assign representative), Traversal τ (select under token budget given query).
Key theorem: coarsening-traversal coupling — the representative function constrains viable
retrieval strategies. Instantiated on 11 existing systems.

**Hermes memory tier mapping:**
| Tier | Coarsening C | Traversal τ | Coupling note |
|------|-------------|-------------|---------------|
| In-context (L1) | None | Identity | N/A |
| session_search (L2) | Session boundary + summary | FTS5 | MISMATCH for semantic queries |
| MEMORY.md (L3) | Fact distillation | Full read | Works (small enough for identity) |
| graphiti (L4) | Entity/edge extraction | Graph walk | MATCH for semantic queries |

**Implication:** Use graphiti for semantic queries; session_search only for lexically-precise terms.

---

## LOW / Skip

### 2608.11250 | AgonAlpha: Autonomous Alpha Discovery via Prompt Economy and Agentic Search
**cs.AI, cs.MA** | Submitted 2026-08-04

Finance-domain agentic pipeline. The "frozen research artifact" storage pattern (hypothesis +
evidence + rationale + review status as immutable records) has general applicability for
long-running research agents but is too domain-specific to encode as a technique class now.
Note for future: if Hermes research agent patterns are developed, CDH adversarial reviewer
pattern + pending-aware parallel budget allocation from this paper are worth revisiting.

### 2601.15625 | Robust Tool Use via Fission-GRPO: Learning to Recover from Execution Errors
**cs.LG, cs.AI** | ACL 2026

Training-time result. Core insight (learn from exact errors during exploration, not static
error datasets) reinforces on-policy learning direction in `self-improve-agent`. Not a
runtime technique applicable to Hermes harness directly.

---

## Search Provenance

**Most effective approach this sweep:** Direct ID probing by range + abstract fetch.
- Start at cutoff + 1, probe by ~50-ID increments to find the active range
- Switch to consecutive fetches within the active range for the target categories
- Keyword searches via `web_extract(arxiv.org/search?...)` surfaced additional papers not
  found by ID probing (particularly for papers with IDs below the cutoff that weren't
  in the previous sweep due to keyword overlap)

**arXiv ID space structure (Aug 2026 observation):**
- Total Aug 2026 IDs: ~0–12311 as of Aug 13 UTC
- cs.* papers represent roughly 30-40% of all submissions (mixed with physics, math, bio, etc.)
- Probing every 50 IDs is sufficient for category discovery; switch to consecutive probing
  only after identifying a cs.AI/CL/MA cluster

**Category listing approach (still valid, recommended alternative):**
```
https://arxiv.org/list/cs.AI/2026-08
https://arxiv.org/list/cs.CL/2026-08
https://arxiv.org/list/cs.MA/2026-08
https://arxiv.org/list/cs.LG/2026-08
https://arxiv.org/list/cs.IR/2026-08
https://arxiv.org/list/cs.SE/2026-08
```
Month listing returns ALL submissions for that month. Parse IDs with regex, filter by > cutoff.
