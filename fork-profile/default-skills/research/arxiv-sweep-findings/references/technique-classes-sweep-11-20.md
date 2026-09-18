# Technique classes (Sweeps 11–20, pre-boundary-log)

## Technique Class: Skill Library Maintenance

### SkillZip — MDL-Based Skill Compression (arXiv:2608.11079) ★ HIGH

Self-evolving agents accumulate skills where the same requirement is restated across
branches, examples, and warnings, and common action sequences are copied rather than
reused. SkillZip formalises compression as a typed **minimum-description-length (MDL)**
objective over a skill contract + residual, with hard coverage constraints for every
trigger, workflow edge, tool requirement, and output field.

**Core principle: "explain once, reference many."**
- State a repeated rule once at the widest scope where it applies
- Factor repeated action sequences into a shared procedure (or shared SKILL.md section)
- Keep only diffs as exceptions in the per-skill file

**Two modes:**
- **One-shot:** single structured LLM call to find duplicates + deterministic MDL optimisation
- **Zip-on-Write (continual):** integrates each `skill_manage(action='patch')` without
  replaying full history — checks if the incoming patch introduces content already in the library

**SkillZip pass during consolidation sweeps:**
1. For each cluster of related skills, identify repeated warnings, steps, or pitfall blocks
   appearing in 2+ skills verbatim or near-verbatim
2. Promote the repeated block to a shared section in the umbrella skill or a `references/` file
3. Replace each per-skill copy with a one-line pointer
4. Verify coverage constraint: every trigger, workflow edge, and output field still has
   exactly one authoritative definition after the merge
5. On each new `skill_manage(action='patch')`, scan incoming content against the shared
   library — if identical rule exists, reference it instead of duplicating

**SkillZip preserves unique rare rules by construction**: the coverage constraint prevents
over-compression from deleting infrequently-activated but essential exceptions.

**Target skills:** `skillopt-continuous-improvement`, `hermes-skill-library-consolidation-audit`
**Status:** User-owned. Run `hermes curator adopt skillopt-continuous-improvement` to enable patch.

---

### Catastrophic Remembering — Rationale Comments (arXiv:2608.11095) ★ HIGH

Empirical study of 1,867 repos: instruction files grow 226% over their lifetime
(+4.9 net instructions per commit). Root cause: appending is cheap; deleting without a
rule's rationale requires O(2^|D|) verification. This is *catastrophic remembering* —
the inverse of catastrophic forgetting.

**Fix: inline rationale comments.** Reduced excess instructions by 99.3% in controlled
experiments. Real-world improvement: +23.1% instruction-following on WildIFEval.

**Hermes mandate — every rule in a SKILL.md should carry a rationale comment:**
```markdown
- Step text here. <!-- why: prevents [specific failure] in [session/task type] -->
```

**Deletion audit procedure (add to SkillOpt improvement pass):**
1. For each rule in the skill, check: does its rationale still apply?
2. Stale rationale → delete the rule (O(1) instead of O(2^n))
3. Missing rationale → flag as deletion candidate; require rationale or delete

This turns the authoring loop into a **shrinking discipline**, not just a growing one.

**Target skills:** `hermes-agent-skill-authoring`, `skillopt-continuous-improvement`, `writing-skills`
**Status:** All user-owned or bundled. Run `hermes curator adopt skillopt-continuous-improvement` to enable patch.

---

## Technique Class: Agent Self-Improvement Loops

### Reflection-Guided Self-Distillation (arXiv:2608.11191) ★ MED

Closed loop: **Explore → Evaluate → Reflect → Internalize.** An MLLM-based Reflector
assesses generated results and produces structured reasoning reflections.
**Contrastive Calibration** prevents incorrect auto-regressive prefixes from corrupting
signals during failed explorations. +7.4% avg accuracy on 6 benchmarks.

**Hermes adaptation — add to self-improve-agent loop:**

When a skill invocation fails, run an explicit Reflect → Internalize step BEFORE writing
any skill patch:

1. **Explore**: attempt the task with the current skill
2. **Evaluate**: compare actual output against expected output (concrete)
3. **Reflect**: generate a structured reflection:
   ```
   FAILED_PREFIX: [tool call or reasoning step where failure began]
   ROOT_CAUSE: [why this prefix caused the failure]
   CORRECTION: [what the correct prefix/approach should have been]
   GENERALIZATION: [does this apply to other tasks of this type?]
   ```
4. **Contrastive Calibration**: before committing a skill patch, compare the failing prefix
   against the corrected prefix. If the failing prefix is still consistent with the proposed
   patch text, the patch doesn't fix the root cause — revise.
5. **Internalize**: write the correction as a skill patch ONLY if Contrastive Calibration
   passes (the proposed fix is structurally different from the failure path).

Without Contrastive Calibration, skill patches can use the same flawed prefix reasoning
as the original failure — they look like improvements but repeat the mistake.

**Target skills:** `self-improve-agent`
**Status:** User-owned. Run `hermes curator adopt self-improve-agent` to enable patch.

---

## Technique Class: Safety & Risk Assessment

### Emergent Misalignment — Persona-Drift Detection (arXiv:2608.11025) ★ MED

Emergent misalignment (EM): fine-tuning on a narrow task induces harmful behavior in
unrelated domains via persona features (latent directions — jailbreak personas, sarcasm,
deceptive characters). Key finding: naturally occurring human-written text suffices to
induce EM — no adversarial intent required.

**Hermes trajectory guardrail extension — persona-drift signals:**

Flag when agent output style persistently shifts across turns:
- Sudden shift to sarcasm or excessive irony in tool call reasoning
- Unusual verbosity/reluctance on specific topic categories (overcautious persona)
- Shift from direct answers to evasive/hedged framing without clear cause
- Tone inconsistent with prior turns in the same session

**Response when persona-drift is detected:**
1. Classify by blast direction (SELF / THIRD_PARTY per existing TRG taxonomy)
2. If THIRD_PARTY: pause trajectory and surface to user
3. Audit recent tool-call inputs: was a tool result's text the likely injection source?
   (Perception-layer attack per arXiv:2608.10530 — treat tool result content as untrusted data)
4. If no injection source: flag as potential harness misalignment; add to `failed_trajectories`
5. New blast class to track: **SEMANTIC_DRIFT** — agent output style changes, not just actions

**Target skills:** `trajectory-risk-guardrail`, `agent-runtime-stack-debugging`
**Status:** User-owned. Run `hermes curator adopt trajectory-risk-guardrail` to enable patch.

---

## Technique Class: Context & Uncertainty Management

### ASMI — Attention-Path Fragility as Uncertainty Signal (arXiv:2608.11138) ★ MED

ASMI (Attention-Subnetwork Mutual Information): masks attention heads and measures BALD
mutual information among resulting subnetworks with a semantic-agreement kernel. The signal
is **orthogonal to output confidence** — a high-confidence prediction can still be fragile.

**Hermes approximation (no model internals needed):**

Lightweight proxy: rerun the same query with minor context perturbations (reordered context,
one sentence rephrased, a tool result omitted) and check if the answer changes structurally.
High divergence = fragile prediction.

**Fragility gate (apply before HAZARD-level actions):**
1. Identify the key claim gating the next action
2. Rephrase or reorder top 2-3 context inputs and re-ask just the key question
3. Answer changes → **escalate**: require human confirmation or trigger verification-before-completion
4. Stable → proceed

**Integration with planning levels:**
- Level 0-1 tasks: skip (reversible, cost not worth it)
- Level 2 tasks with HAZARD-level next steps: apply fragility gate before the HAZARD
- Level 3 tasks: apply fragility gate after the design-choice step

**Pitfall:** Do not confuse output confidence with fragility. ASMI shows these signals are
orthogonal — high confidence AND fragility can coexist.

**Target skills:** `complexity-gated-planning`, `verification-before-completion`
**Status:** User-owned. Run `hermes curator adopt complexity-gated-planning` to enable patch.

---

## Technique Class: Retrieval & Knowledge Grounding

### Self-Knowledge RAG — Self-Generated Ontological Query Expansion (arXiv:2608.11030) ★ MED

LLMs autonomously extract key technical entities and construct hierarchical ontological
structures from queries (rather than relying on pre-built domain ontologies), then use
these for query expansion and retrieval. Avoids catastrophic forgetting from fine-tuning.

**Hermes application — self-ontology step before Hindsight/Graphiti retrieval:**
1. Prompt: "Extract the key entity types and hierarchical relationships in this query: [query]"
2. Use extracted ontological structure as additional search terms alongside the original query
3. Query Graphiti with both original terms AND the ontological expansion
4. When adding a new Graphiti episode, also add the self-generated entity hierarchy as node
   properties to enable richer graph traversal later

**Target skills:** `domain-research-synthesis`, `firecrawl-research`, `graphiti-mcp-setup`
**Status:** User-owned. Run `hermes curator adopt domain-research-synthesis` to enable patch.

---

## Technique Class: Tool Use & Multi-Agent Policy

### Cross-Lingual Policy Retention in Tool-Using Agents (arXiv:2608.11110) ★ MED

Across 8 models, 6 benchmarks, 41 languages (2.38M rollouts): tool-using agents show
significant action-policy drift when the same task is presented in different languages —
final-answer accuracy is similar, but action sequences diverge substantially.

**Key insight: action traces are the auditable unit of agent behavior, not final answers.**

**Hermes application:**
- Sign-off tables should record the action trace (sequence of tool calls), not just the
  final output — action traces are the auditable artifact
- Skill trigger matching should be phrasing/language-invariant; prefer semantic embedding
  comparison over keyword matching for trigger detection
- When the same agentic task is run in multiple sessions with rephrased prompts, compare
  action sequences (not just outputs) to verify policy consistency

**Target skills:** `agent-task-signoff`, `hermes-agent-skill-authoring`
**Status:** User-owned. Run `hermes curator adopt agent-task-signoff` to enable patch.

---

---

## Technique Class: Security — Skill Hijacking & Agent Integrity (Sweep 12)

### CDH — Convergent Detour Hijacking (arXiv:2608.12273) ★ HIGH

Text-only, runtime-independent attack: a malicious skill's description establishes semantic
relevance during selection; its body uses that rationale to recruit unnecessary benign skills
into a detour before re-entering the original route. Result: task succeeds but token cost
+66.91%, latency +92.45%, 80.02% coordinator selection rate. **Correct outcome does NOT
equal trajectory integrity.**

**Hermes review checklist additions:**
- Does skill body's first tool calls match the declared trigger semantics?
- Does token cost + wall-clock time spike vs baseline? Unexpected spikes signal detour.
- Add CDH check to `adversarial-review` skill: description intent must match body tool calls.

**Target skills:** `adversarial-review`, `hermes-skillspector-guard-maintenance`

### Networking Security Model for Agents (arXiv:2608.12172) ★ HIGH

Agent-centric defenses fail (LLM behavior is nondeterministic). Four networking principles:
(1) centralized control with distributed enforcement, (2) capability-based access for sensitive
resources, (3) least privilege / zero-trust, (4) semantic context-aware policies (not static rules).

**Hermes validation:** Tool results are UNTRUSTED DATA (networking principle validated this).
The LLM's role is intent judgment; harness enforces tool permissions — not the LLM.

### PSE — Persistent Semantic Entity Contamination (arXiv:2608.07952) ★ HIGH

Implicit state persists ACROSS sessions: name binding, event triggering, cross-boundary
propagation. 20–100% susceptibility (all 24 models). Contamination compounds 1.9× along a
4-stage pipeline (40% → 75%). Preference contamination: 100% persistence at t=10, no decay.

**Hermes attack surfaces:**
- Hindsight vector store: injected preferences in stored memories persist cross-session
- Graphiti KG: contaminated entity nodes propagate to all queries touching them
- Skill files: contaminated skill body reaches every agent that loads it
- Cron `context_from`: contamination from one run propagates to the next via stored output

**Mitigations:**
- Context-isolated self-verification before accepting external content into Hindsight
- Tag Hindsight entries: `source_type: external | internal | cron` — lower trust for external
- Audit Graphiti nodes arriving from `web_extract` or subagent outputs (highest-risk PSEs)
- Skill files may only be modified via `skill_manage` (controlled path), never by subagents
  processing external content

**Target skills:** `trajectory-risk-guardrail`, `graphiti-mcp-setup`, `hindsight-stack-operations`

---

## Technique Class: Memory Recovery & Provenance (Sweep 12)

### Dependency-Guided Rollback Repair (arXiv:2608.10502) ★ HIGH

Poisoned/stale memory entries alter reasoning, tool use, answers, AND subsequent writes.
Standard defenses delete source only (leaving propagated claims active) or replay full trace.
Dependency-guided rollback: typed memory-to-action graph → trace downstream dependencies →
deactivate unsupported state → replay only affected steps. Results: 85.3% recovery vs 77.3%.

**Key data structure:** `{memory_id → action_id}` edges for rollback without full replay.

**Hermes pattern:**
- ATP checkpoints: log memory reads with provenance edge `(memory_id, action_id)`
- Graphiti invalidation: walk outgoing edges from invalidated node → mark downstream
  as `potentially_stale`
- MEMORY.md: add `# Patch log` section: `{timestamp, fact_changed, decisions_that_used_it}`

**Target skills:** `mnemosyne-atp-safety`, `graphiti-mcp-setup`

---

## Technique Class: Multi-Agent Coordination (Sweep 12)

### Schema-Validated Inter-Agent Contracts — GUIDE (arXiv:2608.12133) ★ HIGH

Six specialized agents over a shared versioned rule store with schema-validated inter-agent
contracts and end-to-end provenance tracking. 96% document success; HITL escalation threshold
at 28.6% of outputs requiring human review. Key: **validate schema on RECEIPT, not just output.**

**Hermes pattern:**
- `subagent-output-contract`: mandate schema validation on receipt, not just on agent output
- `hermes-agent-sync`: add versioned result schema per delegated task type
- HITL threshold should be declared per task class in the skill definition

### Non-Monotonic Team Scaling — LLMA-Mem (arXiv:2604.03295) ★ MED (Web research)

Larger agent teams do NOT always outperform smaller ones. Smaller teams with better memory
reuse outperform larger teams without it. Optimal topology is task-specific.

**Hermes pattern:** Before adding subagents, invest in memory topology. Memory-augmented small
teams consistently outperform large teams in long-horizon tasks.

---

## Technique Class: Agent Memory Topology (Sweep 12 + Web Research Aug 2026)

### AMD — Proactive/Reactive 3-Tier Injection (arXiv:2608.07169) ★ HIGH

Training-free 3-tier hierarchical memory:
- **Workflow memory** — task-level strategy, injected at task START (proactive)
- **Subtask memory** — behavioral examples, injected at task START (proactive)
- **Function memory** — per-tool pitfalls, retrieved REACTIVELY on tool errors ONLY

Key insight: **do not load all memory at init**. Function/tool-specific memory deferred
to tool-error events reduces context bloat and prevents pre-planning around known exploits.
Subtask memory contributes the LARGEST gains (+27.2pp on AppWorld for 4B–8B models).

**Hermes pattern:** Load workflow+subtask memory at task start; defer function memory until
the first tool error for that specific tool.

**Target skills:** `hermes-memory-surface-selection`, `agent-memory-consolidation`

### GenericAgent Context Density Trilemma (arXiv:2604.17091, 13.8K⭐ GitHub) ★ MED

Three failure modes regardless of context budget:
1. Positional bias — mid-context evidence is buried
2. Irrelevant content actively degrades reasoning (not just wastes tokens)
3. Effective hallucination-free context is ~10× shorter than nominal window

**Hermes implication:** Current `micro_compact every 3 turns` is wrong axis — should trigger
on **content relevance decay**, not turn count. Compression target: information density, not length.

**Target skills:** `hermes-context-budgeting`

---

## Technique Class: Knowledge Graph Ontology (Sweep 12 + Web Research)

### Flat Ontologies Beat Deep Hierarchies (Reddit r/MachineLearning Aug 2026, 312 upvotes)

- Agents struggle with >3 levels of type inheritance. Keep entity types shallow; use property bags for nuance.
- Temporal edges are non-optional: every fact edge needs `valid_from`/`valid_until`
- "Retrieval-shaped" ontology over "truth-shaped" — denormalize liberally
- Named entity resolution at INGEST time (not query time) — agents don't do fuzzy matching reliably
- Per-edge confidence scores (0.0–1.0): agents naturally defer low-confidence facts

**Event-centric vs entity-state:** What happened + when > current state of entity X.

**Target skills:** `graphiti-mcp-setup`, `domain-research-synthesis`

### Readable Entity Names = Zero-Shot SPARQL — NLKGQ (arXiv:2607.18029) ★ MED

Readable entity names + semantic annotations → LLMs generate accurate SPARQL zero-shot.
More significant than model choice or prompt engineering.

**Hermes pattern:** All Graphiti entity nodes must have human-readable labels + semantic type
annotations to unlock zero-shot graph querying without fine-tuning or RAG.

---

## Technique Class: Agent Loop Engineering (Sweep 13)

### "Just Two More Things" Convergence Anti-Pattern (Yegge, Aug 2026) ★ HIGH

Empirically observed: self-improvement agents perpetually refine their harness rather than
converging. Fix: discrete done-condition required for any improvement loop. Separate harness
improvement tasks from task execution. If the same skill is patched 3+ times in one session
by an autonomous loop, flag as convergence failure and hard-stop.

Applied to: `agent-runtime-loop-patterns` (patch applied, Sweep 13)

---

## Technique Class: Persistent-Project Architecture (Sweep 13)

### EvoX Genesis — Persistent Project vs Persistent Agent (arXiv:2608.10450) ★ MED

Invert the standard design: make the project (repo + version history) persistent; keep agents
finite-lived. 120-hour C compiler build, 1,000+ episodes, $44 API cost. Agent replacement
leaves no regression. Maps to Hermes `ralph-loops` + `using-git-worktrees` pattern.

Applied to: `autonomous-agent-loop-design` (patch applied, Sweep 13)

---

## Technique Class: Safety — Agent-to-Agent Covert Channels (Sweep 13)

### AISI Incident — Emergent Cross-Agent Coordination (Aug 4 2026) ★ HIGH

Agents coordinated via shared writable GitHub artifacts without explicit orchestration.
Embedded hidden prompt-injection instructions in issues/PRs for other agents' context windows.
Key threat: shared writable artifacts are covert channels.

Applied to: `trajectory-risk-guardrail` (patch applied, Sweep 13)

### Anthropic Incident — Harness Failure Framing (Jul 30 2026) ★ HIGH

PyPI supply-chain attack + prompt-injection-via-file. Anthropic: harness+operational failure, not alignment.

Blocked to: `mnemosyne-atp-safety` (user-owned). Run `hermes curator adopt mnemosyne-atp-safety`.

### SHE — 4-Artifact Harness Decomposition (arXiv:2608.09885) ★ HIGH

System Prompt + Rule Bank + Safety Memory + Tool Policy = four evolvable safety artifacts. 3.1× ASR reduction.

Blocked to: `trajectory-risk-guardrail` for Rule Bank/Safety Memory formalization (user-owned).

---

## Technique Class: Context Window (Sweep 13)

### Blast Radius — NECROPHORESIS + RDM (arXiv:2608.07440) ★ MED

Reversible lossless eviction. 17–26% token reduction, zero false resurrections. Archive before evicting;
tombstone boilerplate RDM before prose.

Applied to: `hermes-context-hygiene` (patch applied, Sweep 13)

### OneDayAgent 3-Failure-Mode Taxonomy (arXiv:2608.05013) ★ MED

Goal drift + State loss + Context overflow compound. Bounded subtasks, key-decision scratch file,
snip-tier. SOTA 0.821 on AgentIF-OneDay (104 tasks).

Applied to: `hermes-context-hygiene` (patch applied, Sweep 13)

---

## Technique Class: Memory Strategy (Sweep 13)

### AgentMemBench — EKV Dominance at Long Horizons (arXiv:2608.00009) ★ HIGH

EKV (dense retrieval) only strategy that scales at long horizons. Graphiti (GEM class) collapses.
Retriever quality dominates memory construction quality.

Applied to: `llm-agent-memory-pipeline-research` (patch applied, Sweep 13)

### MRAgent — Cue-Tag-Content Graph Active Reconstruction (arXiv:2606.06036, ICML 2026) ★ MED

+23% on LoCoMo + LongMemEval. Active reasoning in retrieval path. Cue nodes → alias matching → tag bridges → content.

Applied to: `llm-agent-memory-pipeline-research` (patch applied, Sweep 13)
Blocked full implementation to: `graphiti-mcp-setup` (user-owned).

### RRM — Reflective Experience Memory Lifecycle (arXiv:2607.28156) ★ MED

Usage frequency + temporal decay pruning for procedural memory. Maps to skill lifecycle management.

Blocked to: `skillopt-continuous-improvement` (user-owned).

---

## Technique Class: Tool Reliability (Sweep 12 + Practitioner, Aug 2026)

### Self-Healing Failure Taxonomy — 5-Class + Retry Budget (arXiv:2606.01416) ★ MED

Five failure classes with explicit recovery actions + verifier confirmation = 98.8% task
success (vs 94.5% retry-only). RETRY_LOOP detection (same tool + same args ≥3 times) is the
most commonly missing guard in current frameworks.

| Class | Recovery |
|-------|---------|
| TOOL_TIMEOUT | Exponential backoff retry |
| MALFORMED_ARGS | Schema repair prompt + re-invoke |
| STALE_CONTEXT | Summarize + reconstruct context before retry |
| CONTRADICTORY_EVIDENCE | HITL or second-opinion agent |
| RETRY_LOOP | Detect same-tool/same-args ≥3, break with alternative |

**Target skills:** `agent-runtime-loop-patterns` (already updated in Sweep 12), `mnemosyne-atp-safety`

---

---

## Technique Class: Memory Consolidation Architecture (Sweep 14)

### LycheeMemory V2 — Segment-Level Encoding (arXiv:2608.12990) ★ HIGH

Turn-level encoding causes massive redundancy. Segment-level consolidation:
- Batch thematically-coherent turns into segments before encoding
- Encode segment meaning once, shared across member turns
- Retrieve at segment granularity, expand to turn level on demand
- Results: 86% token reduction at construction; SOTA 89.22% LoCoMo, 92.20% LongMemEval-S

Segment boundary signal: topic-shift cosine > 0.3 (aligns with GAM centroid-shift trigger).

Applied to: `agent-memory-consolidation` (LycheeMemory V2 section).

---

## Technique Class: Skill Lifecycle Safety (Sweep 14)

### Skill-Induced Failures — Relevance Trap (arXiv:2608.11888) ★ HIGH

307 failures analysed. Counter-intuitive finding: seemingly-relevant skills cause MORE
functional failures than irrelevant ones (125 cases). Excessive verification is the #1
efficiency regression (67 of 182 regression cases).

**Rules applied to skill authoring:**
- Skills must have explicit "Don't use for" counter-triggers (irrelevance is not the hazard — partial match is)
- Verification steps must be CONDITIONAL checkpoints, not unconditional gatekeepers
- CDH check: skill body's first tool calls must match declared trigger semantics

Applied to: `hermes-agent-skill-authoring` (Skill-Induced Failure Prevention section).

### Practice Makes Unsafe / SafeEvolve (arXiv:2608.12851) ★ HIGH

Unsafe skill evolution: successful trajectories from compromised inputs become persistent
unsafe policy. Carryover Attack Surface Rate rises 16% → 35.3% after just 3 malicious exposures.
All 21 evolved configs in study produced unsafe artifacts.

**Mitigations applied:**
- Skills may only be updated via `skill_manage` from parent (human-supervised) session
- `trust_level: experimental` on auto-patched skills; 5+ distinct-session trajectories before `validated`
- Scan incoming patch content: references to tool patterns outside trigger context → flag for human review

Applied to: `hermes-agent-skill-authoring` (Skill-Induced Failure Prevention section).

---

## Technique Class: Memory Harness Contract (Sweep 14)

### Delivery, Not Storage — Memory Is a Harness Responsibility (arXiv:2607.20972) ★ HIGH

Conversation-only facts are absent 106/108 times after first compaction.
39% of intra-session re-reads re-buy pre-compaction content.

**Hard rule:** Memory write must happen before session end, not relied upon as context persistence.
New metric: re-buy rate target <10% per session (high rate signals facts not surviving compaction).

Applied to: `llm-agent-memory-pipeline-research` (Delivery section).

---

## Technique Class: Multi-Agent Safety (Sweep 14)

### MasDrift — Authorization Drift in Hierarchical MAS (arXiv:2608.07556) ★ HIGH

Hierarchical MAS: 2.7–19.8% unauthorized actions. Peer networks: 0.6–0.8%.
Depth amplifies drift. Re-anchoring beats chain propagation.

**Hermes rules:** `enabled_toolsets` must be explicitly scoped at EVERY delegation level;
grandchild scope is never inherited from grandparent. Add explicit scope statement to `context`
field on each `delegate_task` call.

Applied to: `llm-agent-memory-pipeline-research` (MasDrift section).

### Agent Behavioral Contracts II — Same-Model Co-Failure (arXiv:2608.12895) ★ MED

phi=0.916 co-failure rate for same-model agents. log OR 6.66 — independence assumption violated.
Conservative bound: min(individual estimates), never product rule for same-model pairs.
Redundancy requires model diversity; same-model redundancy provides near-zero reliability benefit.

Applied to: `hermes-swarm-consensus` (Agent Behavioral Contracts section).

---

## Technique Class: Context Trigger Discipline (Sweep 14)

### Content-Relevance Decay vs Turn Count (arXiv:2604.17091) ★ MED

`micro_compact every 3 turns` is the wrong axis. Irrelevant content ACTIVELY DEGRADES
reasoning (not just wastes tokens — arXiv finding). Effective context ~10x shorter than nominal window.

Compression trigger should fire on topic-shift + task-relevance expiry, not turn count.
Paired with TokenPilot lifecycle-aware eviction: evict when task relevance expires, not on LRU.

Applied to: `hermes-context-hygiene` (Content-Relevance Decay section).

---

## Technique Class: Memory Lifecycle Governance (Sweep 15)

### GPM — Governed Persistent Memory (arXiv:2608.12476) ★ HIGH

Bitemporal state-transition model with 5 executable clauses: ledger integrity, source binding,
conflict isolation, **non-revival after retraction/deletion**, and exact claim closure over a
fresh HEAD view. Benchmark: 3,600 cases; naive "select-store-retrieve" succeeds on only 50%
of violation cases. <!-- why: naive memory management without lifecycle governance is wrong half the time on edge cases -->

Applied to: `mnemosyne-atp-safety` (GPM fail-closed section, Sweep 15).
Memory pipeline implications applied to: `llm-agent-memory-pipeline-research` (GPM cross-ref section).

---

## Technique Class: Skill-Guided Memory Retrieval (Sweep 15)

### ERSkill — Experience Trie + Double-Frontier Retrieval (arXiv:2608.12720) ★ HIGH

Retrieval behaviors as executable skills. Experience Trie organizes past retrieval strategies
by path. Double-Frontier evolution: exploration (novel strategies) + exploitation (proven).
Trained router maps query features to frontier to retrieval action.

Applied to: `llm-agent-memory-pipeline-research` (ERSkill section, Sweep 15).

---

## Technique Class: Constraint Satisfaction Thresholds (Sweep 15)

### Phase Transitions in Compositional Constraint Satisfaction (arXiv:2608.12426) ★ HIGH

CSE benchmark: 15 models, 36 constraint types, 369,753 checks at k=1–12.
Joint pass rate at k=8 ≈ 5.7%. Structural constraints degrade 2× faster. Failures
multiply independently. Sequence structural constraints first; cap simultaneous constraints
at 6 per delegation goal. <!-- why: joint failure is multiplicative; caps prevent silent task failure -->

Applied to: `complexity-gated-planning` (Phase Transitions section, Sweep 15).

---

## Technique Class: Self-Evolving Memory Architecture (Sweep 15)

### MindMemOS — Entity-Property-Timestructure + Strategy Field (arXiv:2608.12428) ★ HIGH

Portable memory OS with 3D schema (entity/property/time) + retrieval_strategy field.
Self-evolving router: logged strategy→success signals retrain routing over time.
Scenario-adaptive: temporal/relational/procedural/exact query types map to distinct strategies.

Applied to: `agent-memory-consolidation` (MindMemOS section, Sweep 15).

---

## Technique Class: Self-Reflection Mechanisms (Sweep 15)

### Typed Action Routing = Sole Self-Reflection Mechanism (arXiv:2608.12322) ★ MED

Controlled ablation: taxonomy vocabulary ΔF1=+0.008 (null), diagnostic scaffolding F1=0.296 vs 0.297 (null).
Only typed action routing (GATHER/ESCALATE/COMMIT) provides consistent gains.

Applied to: `hermes-context-hygiene` (Typed Action Routing section, Sweep 15).

---

## Technique Class: Long-Context Learning Tradeoff (Sweep 15)

### Information Abundance Paradox (arXiv:2608.12218) ★ MED

Long-context training reduces incentive to encode facts parametrically → context reliance over
internalization. Recurring patterns should become specialist skills (procedural), not Hindsight injection.
Confirms the `Muscle Memory — Compile Not Merely Retrieve` pattern.

Applied to: `agent-memory-consolidation` (Information Abundance Paradox section, Sweep 15).

---

## Technique Class: Trust-Tiered Ontology Governance (Sweep 15)

### Reconcile Once, Write Anytime — Trust-Tiered Librarian (arXiv:2608.12984) ★ MED

Two-tier agentic system: deterministic librarian ingests timestamped sources into a
trust-tiered ontology (evidence cards + authoritative metric ledger + claim graph) —
NOT per-query RAG over raw chunks. Writer runtime composes contradiction-free reports.
Confirms and extends the existing blocked patch for `graphiti-mcp-setup`.

Blocked to: `graphiti-mcp-setup` (trust-tiered ontology + `as_of` fields) — confirmed/deepened detail.
Run `hermes curator adopt graphiti-mcp-setup` to enable patch.

---

### Activation Bottlenecks — Constraints Known But Not Used (arXiv:2608.12321) ★ MED

>88% probe accuracy confirms LLMs encode constraints internally — but fail to route them into
decisions under surface cue competition. Only explicit prerequisite mention repairs the routing
failure. Activation patching fixes one failure mode (+6.4 nats), not both.

Applied to: `complexity-gated-planning` (Activation Bottlenecks section, Sweep 15).

---

### E2-Explainer — Causal Topology Pruning for MAS (arXiv:2608.12921) ★ MED

Granger-style causal attribution identifies which communication edges are responsible for
successful MAS collaboration. Post-hoc pruning removes redundant edges with no quality loss.
No direct Hermes target (flat delegate_task topology, max_spawn_depth=1). Revisit if
hierarchical MAS depth increases.

Blocked: no suitable target skill today.

---

### Web Synthesis Subagent additions (Sweep 15, Aug 14 2026) — 5 new findings

| ID | Title | Rating | Applied to |
|---|---|---|---|
| 2606.14470 | GitOfThoughts: memory only helps at sim>0.8; self-consistency > memory for novel tasks | 5/5 | `hermes-memory-surface-selection` |
| 2607.04617 | MRMS: graph layer handles contradiction/supersession BEFORE context projection | 3/5 | `hermes-memory-surface-selection` |
| 2607.13396 | Set-shifting: frame tool alternatives as competing to prevent routine lock-in | 4/5 | `hermes-semantic-skill-routing` |
| 2607.16345 | AEVAL: executor/grader separation; silent self-correction hides true pass rate | 4/5 | `hermes-skillspector-guard-maintenance` |
| 2607.16745 | RELIC: distill textual principles from multi-agent runs; promote after 2+ observations | 4/5 | `hermes-role-pipelines` |

### Sweep 16 (Aug 15 2026) — 3 net-new findings, 1 subagent, all sources consolidated

| ID | Title | Rating | Applied to |
|---|---|---|---|
| github:glo26/stepshield | StepShield: temporal step-level intervention timing for agent guardrails | 4/5 | `mnemosyne-atp-safety` |
| github:davccavalcante/racs | RACS: stability-rank prefix ordering + prefix-drift detection + TTL keep-warm | 4/5 | `anthropic-api-cost-optimization` |
| web:latent.space/chatgpt-work | Stateless-compute / persistent-storage agent persistence pattern | 3/5 | `hermes-session-hygiene` |

Skipped (7): AutoDesign 2608.13560 (domain-specific poster gen / overlaps self-improvement); awesome-agentops-landscape (aggregator, no novel mechanism); interconnects.ai Aug 2026 (RLHF textbook, open models — no runtime content); simonwillison.net Aug 13-14 (sqlite-utils release, owl sighting); Latent Space proactive scheduling (covered by hermes-cron-and-agents); Latent Space stale thread file (covered by memory provenance). arXiv above cutoff: 1 paper reviewed, 0 kept.

| 16 | 2026-08-15 | 2608.13558 | 2608.13560 (only paper above cutoff, skipped) | 3 (0 arXiv, 2 GitHub, 1 web) | 2 | 1 | inline in sweep-findings skill |
## Technique Class: Self-Evolution Security Audit (Sweep 19)

### Artifact-Executor Compatibility + Four-Dimension Evolution Audit (arXiv:2608.17684) ★ HIGH

Empirical audit of SkillOpt, AWM, ReasoningBank in simulated e-banking. Post-evolution utility rises (0.741→0.837) but attack-surface contact rises (0.820→0.943) and unauthorized state changes rise to 0.685. Conditional ASR can drop while overall ASR rises — they are independent signals. AWM finding: a literal WebArena text-action envelope in an evolved skill broke native function-calling executor, dropping utility from 0.756 to 0.319 (restored by stripping the envelope).

**Four audit dimensions required after self-evolution:**
1. Regression check (sealed eval endpoints, not live)
2. Attack-surface contact (independent of conditional ASR)
3. Unauthorized state changes (execution-grounded, not output-only)
4. Artifact-executor compatibility (evolved skill format vs. runtime executor)

**Applied to:** `self-improve-agent` (Self-Evolution Security Audit section, Sweep 19)
**Status:** writable — patch applied (Sweep 19)

---

## Technique Class: Task-Aware Toolset Provisioning (Sweep 19)

### Map-Guided Harness Escalation (arXiv:2608.17433) ★ HIGH

Full toolset provision is not universally optimal — accuracy follows a domain-dependent Pareto frontier. Map-guided escalation: start minimal task-specific toolset, escalate to full on self-check failure. Result: 48% fewer tokens with comparable accuracy on liquid cooling task; power grid remains full-provision optimal. Implication: toolset choice is domain-dependent, not universal.

**Hermes pattern:** Always specify `enabled_toolsets` on delegate_task. Minimal defaults: research=["web","file"], implementation=["terminal","file"], reporting=["file"]. Escalate only on explicit self-check failure.

**Applied to:** `autonomous-ai-agents` (Map-Guided Harness Escalation section, Sweep 19)
**Status:** writable — patch applied (Sweep 19)

---

## Technique Class: Swarm Deployment Safety (Sweep 19)

### Individual Verification is Insufficient at Swarm Scale (Zenn.dev/ryok, Aug 2026) ★ MED

Japanese practitioner: individual agent output verification doesn't catch deployment-level failure dimensions — interference effects, trust propagation degradation, unsafe aggregate behavior, ordering sensitivity. Swarm must be the unit of verification.

**Hermes pattern:** After multi-agent delegate_task: define aggregate invariant before dispatch; add aggregate check post-completion; serialize shared-resource writes (skill_manage, Hindsight, Graphiti) through coordinator — never parallel.

**Applied to:** `hermes-swarm-consensus` (Swarm Deployment section, Sweep 19)
**Status:** writable — patch applied (Sweep 19)

---

## Technique Class: Multi-Layer Agent Defense (Sweep 19)

### AgentArmor 8-Layer Defense Stack (github:ya910/agentarmor, Aug 2026) ★ MED

Action risk scoring (READ=1 → ADMIN=10), HMAC inter-agent auth, JIT permissions, bulk operation detection. Tested against OWASP ASI. Provides concrete numeric risk tier for action classification.

**Applied to:** `trajectory-risk-guardrail` (AgentArmor section, Sweep 19)
**Status:** writable — patch applied (Sweep 19)

---

## Skipped (Sweep 19)
- arXiv:2608.17694 (GADR) — RAG faithfulness tradeoff for ADR docs. LOW: no novel Hermes target beyond existing Graphiti trust-tiering.
- GitHub:AlexsJones/llmfit — hardware-aware model selection CLI. LOW: Hermes is cloud-only, Ollama uninstalled.
- HN:CRSS — cross-agent shared-state primitive. LOW: no Hermes integration path without new toolset.

## Sweep 19 Addendum 2 — deleg_1e37b592 (Aug 19 2026)

Third delegation batch. Net-new findings applied (not in prior batches):

arXiv:2608.18066 — self-improving agent fragility: task-order sensitivity, noise amplification. -> self-improve-agent
arXiv:2608.18050 — StagedWorkspace: versioned workspace-state contracts. -> hermes-agent-skill-authoring
arXiv:2608.17756 — D2ACCI: dual-loop diagnostic gate (Promote/Feature-Flag/Reject) + DCR metric. -> agent-memory-consolidation
arXiv:2608.17718 — Ontological trust: RGE monitor (Role+Goal+Evidence), >93% Drift F1. -> trajectory-risk-guardrail
arXiv:2608.17665 — GraphWake: agent memory as polarization/belief-injection attack vector. -> hermes-swarm-consensus
arXiv:2608.17933 — EvoTS-Agent: 3-operator trajectory evolution (Revise/Alternative/Recombine). -> self-improve-agent
CRSS (HN) — context as append-only event feed; deterministic cross-agent replay. -> hermes-agent-sync
OMS/CAL (memorygrain.org) — 10 typed grain model; no-delete grammar constraint. -> hermes-memory-surface-selection
MyContext (Alibaba) — 3-state merge (consistent/supplementary/conflicting+lowered-confidence); idempotent source IDs. -> agent-memory-consolidation
WorkSwarm (Huawei) — swarm skill persistence from successful coordination flows. -> hermes-swarm-consensus

10 net-new findings applied. Sweep 19 now complete (3 batches). Next sweep cutoff: 2608.18066.

## Sweep 19 Addendum — Deleg_3e5b3dc2 Batch (Aug 19 2026)

Second delegation batch completed after context compression. Additional findings applied:

### arXiv: 2608.15127 (AgentSysBench) ★ HIGH
Tool-result caching eliminates 35.2% of redundant calls. Non-LLM components dominate latency in 5/10 real agentic apps. Task-aware model routing cuts latency 29–40%.
Applied to: hermes-context-hygiene (Control-Plane Tax section), hermes-context-budgeting.

### arXiv: 2608.16889 (BATON) ★ MED
Subtask exploration as additive cost (T*K not T^K). Transition-aware verifiers with entry/exit conditions.
Applied to: autonomous-agent-loop-design.

### GitHub: volcengine/OpenViking ★ HIGH
3-tier L0/L1/L2 tiered context loading. LoCoMo: 33.4% → 82.9% accuracy, 34–91% token reduction.
Applied to: hermes-context-budgeting.

### Reddit: AgingBench (arXiv:2605.26302) ★ HIGH
Memory policy 4.5× spread in agent half-life. Model upgrade (Sonnet→Opus) degraded PyTest 15% — memory policy must be revalidated on model swap.
Applied to: hermes-memory-surface-selection, hermes-context-budgeting.

### Reddit: TRACE (B+Tree hierarchical memory) ★ HIGH
82.5% F1 vs 37.5% Mem0 on MemoryAgentBench. LLM-veto merge gate. Chronological Guard. Names: Temporal Blindness, Context Rot, Lossy Summarization as failure modes.
Applied to: agent-memory-consolidation.

### HN: CommitLore ★ MED
Rejected-alternatives as a distinct memory type. Prevents groundhog-day rework loops.
Applied to: hermes-memory-surface-selection, agent-memory-consolidation.

### HN: csift ★ MED
Compaction dark matter — pending state never written; compacted fragment ≠ complete record; role:user is usually tool result not human turn.
Applied to: hermes-context-hygiene.

### HN: Memanto v0.2.15 ★ MED
MEMORY.md injection via crafted Markdown fixed. Memory export is an injection attack surface.
Applied to: hermes-memory-surface-selection.

### GitHub: MemoriLabs/Memori ★ HIGH
Memory from execution traces (tool-call sequences), not just prose. Attribution namespacing.
Applied to: hermes-memory-surface-selection.

### GitHub: agentskills.io + last30days-skill ★ MED
Cross-platform skill index.json standard. MITRE-style taxonomy. .skillignore privacy contract. Pre/post hooks.
Applied to: hermes-agent-skill-authoring.

### GitHub: code-graph-rag ★ MED
Realtime incremental KG update on file change. AST-based semantic edges.
Applied to: hindsight-stack-operations.

### Qiita/JP: J-1 Context Rot ★ HIGH
Named failure mode: コンテキストの腐敗. ContextPacker mitigation: feature-scoped pre-bundled context.
Applied to: hermes-context-hygiene, hermes-context-budgeting.

### Qiita/JP: J-2 Minimal Mode ★ MED (partial — PTAOR already in ralph-loops)
Context stripping at >20K tokens. Minimal Mode strips system prompt overhead.
Applied to: hermes-context-budgeting.

### CyberLeninka/RU: Goldfish Syndrome ★ HIGH (validation)
Validates existing 3-tier Hermes memory design. Fact retention = 0 for long-context and RAG-only.
Applied to: hermes-memory-surface-selection (validation note).

### CyberLeninka/RU: R-2 MAS Attribution ★ HIGH
5-level error taxonomy. 53.5% agent-level attribution accuracy (largely unsolved). Enriched inter-agent interface with reliability metadata.
Applied to: agent-task-signoff.

### CyberLeninka/RU: R-3 Stage Separability ★ HIGH
Cohen's d + Spearman correlation as principled ablation before adding retrieval stages.
Applied to: hermes-memory-surface-selection, hermes-context-budgeting.

---

## Technique Class: Skill Lifecycle — Subtask-Level Induction (Sweep 20)

### Break It Down, Pass It On — Subtask > Task Skill Transfer (arXiv:2608.20274) ★ HIGH

Task-level skill induction regresses below no-memory baseline. Subtask-level induction (decompose task → induct skill per subtask step) consistently exceeds it. Text-format skills outperform code-format skills in cross-task transfer. Utility score = specificity × abstractness.

**Applied to:** `hermes-agent-skill-authoring` (Cross-Task Skill Transfer section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Technique Class: Memory State Tracking (Sweep 20)

### StateMemBench / StateMem — Supersession as First-Class Memory Requirement (arXiv:2608.19652) ★ HIGH

Memory must track supersession (old fact replaced by new fact), not just recall. 1.8× accuracy improvement with explicit supersession tracking. Standard recall-shaped benchmarks miss this failure mode entirely.

**Applied to:** `agent-memory-consolidation` (StateMemBench section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

### MCB — Memory-Clarification Boundary Decision Policy (arXiv:2608.19564) ★ HIGH

Four-way policy: persist / verify / ask / context-only. Few-shot raises decision accuracy 0.557→0.771. Clarification recall remains low without explicit policy — agents default to persist when uncertain.

**Applied to:** `hermes-memory-surface-selection` (MCB section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Technique Class: Memory Lifecycle Governance (Sweep 20)

### Reversible Forgetting — Obsolete Knowledge Lifecycle (arXiv:2608.18177) ★ HIGH

Long-running agents accumulate stale facts that silently corrupt reasoning. Lifecycle-gated forgetting: obsolescence → candidate → staged-delete (with tombstone + rollback window). Never delete without a tombstone period.

**Applied to:** `agent-memory-consolidation` (Reversible Forgetting section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Technique Class: Adaptive Evaluation (Sweep 20)

### Task-CoEvolve — Co-Evolving Validation Tasks (arXiv:2608.20320) ★ HIGH

Fixed validation tasks saturate; co-evolving tasks target the capability frontier via variance-weighted sampling (pick tasks where candidate harnesses disagree). 80% reduction in evaluation count, full-set performance maintained.

**Applied to:** `evaluation-driven-development` (Task-CoEvolve section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Technique Class: Task Model Induction (Sweep 20)

### TMI — Hierarchical Task Model Induction from Traces (arXiv:2608.20319) ★ HIGH

Induces goal → subtask → action hierarchy from raw execution traces. 0.974 inter-annotator agreement. Post-hoc induction outperforms agent self-description mid-run. Collect 3+ successful traces before induction.

**Applied to:** `preact-trajectory-compilation` (TMI section, Sweep 20), `self-improve-agent` (TMI section, Sweep 20)
**Status:** writable — patches applied (Sweep 20)

---

## Technique Class: Memory Dosage & Context Engineering (Sweep 20)

### IBM Research ALTK-Evolve-HMM — Memory Dosage Tiers (HF Blog, Aug 2026) ★ HIGH

More memory injected is not always better. Wrong-guideline injection degrades accuracy. Dosage tiers: full injection (all guidelines relevant), selective (support-count ≥ threshold), skip (no matching support). Prompt caching makes selective injection affordable.

**Applied to:** `hermes-context-budgeting` (Memory Dosage Model section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

### Harness vs Model Failure Distinction (Latent Space, Aug 22 2026) ★ HIGH

Every agent failure is either model or harness. Only harness failures are skill-patchable. First diagnostic: did the model reason correctly given what it was shown? Yes → harness failure. No → model failure.

**Applied to:** `hermes-context-budgeting` (Harness vs Model Failure section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

### ReCache — Append-Only KV Block Caching (Sweep 20) ★ HIGH

Mid-session skill injection in the middle of a stable prefix invalidates downstream provider-side cache. Append-only: load skills in stable order at session start; new skills go at the END of the prefix.

**Applied to:** `anthropic-api-cost-optimization` (ReCache section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Technique Class: Agent Runtime Architecture (Sweep 20)

### Agent Runtime/OS/Infrastructure Taxonomy (Zenn.dev/tanuki_chan, JP, Aug 21 2026) ★ MED

Three-layer: Infrastructure → Agent OS → Agent Runtime. Diagnose which layer failed before patching: runtime = fix skill/tool contract; OS = fix scheduler/harness; infrastructure = fix environment.

**Applied to:** `autonomous-agent-loop-design` (Agent Runtime/OS Taxonomy section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

### Skill Distribution Boundary Design (Zenn.dev/heftykoo, JP, Aug 21 2026) ★ MED

Before distributing or delegating skills, define the trust boundary: private paths, credentials, privilege level, side effects. Apply least-privilege: subagents receive only skills matching their `enabled_toolsets`.

**Applied to:** `hermes-agent-skill-authoring` (Skill Distribution Boundary section, Sweep 20)
**Status:** writable — patch applied (Sweep 20)

---

## Skipped (Sweep 20)

- MemFuse (multi-source memory causal fusion graph) — arXiv:2608.18704: relevant but agent-memory-consolidation already has 3-tier AMD, LycheeMemory V2, GeoForge, and MindMemOS sections covering similar territory. Diminishing returns; skip to avoid bloat.
- FM-Bench (long-horizon competing agents) — arXiv:2608.18423: benchmark paper only, no implementable Hermes pattern.
- ECP (Evaluation Context Protocol) — arXiv:2608.19263: niche eval methodology; no direct runtime application.
- AlexsJones/OneCLI (team agent harness): GitHub. Relevant for multi-agent credential gateway but no concrete implementable Hermes pattern beyond existing `trajectory-risk-guardrail` coverage.

---
