# Hermes Improvement Research — Sweep 4 (Aug 11, 2026)

Scope: post-Aug-11-2026 papers + high-signal sweep discoveries from agent-0 (arXiv listing
scan 2608.06381–2608.09921), agent-1 (practical/GitHub/blog), agent-2 (KG/memory/skill).
Baseline exclusions: all papers through 2608.09885 (SHE sweep3 baseline).

---

## A. MEMORY TOPOLOGY

### Engram (arXiv:2606.09900) — Bi-Temporal KG Memory Engine
Key: bi-temporal model — every fact stores (1) valid_time (when true in world) and (2)
transaction_time (when system learned it). Point-in-time "as-of" queries. Contradictions
invalidate, never delete. LongMemEval_S: 83.6% vs 73.2% full-context at 8x fewer tokens.
Action: add `valid_from`, `valid_to`, `recorded_at`, `superseded_by` to Hindsight memories table.

### SEEM (arXiv:2601.06411) — Structured Episodic Event Memory
Key: Episodic Event Frames (EEFs) — structured as {agent, action, object, temporal_context,
session_id}. Reverse Provenance Expansion (RPE) reconstructs narrative from fragmented evidence.
Beats flat RAG on LoCoMo and LongMemEval.
Action: extract EEF JSON blob at Hindsight write time; add RPE query mode expanding via session_id.

### SEMA (arXiv:2603.23875) — Self-Evolving Multi-Agent Hybrid Knowledge-Memory
Key: 3-tier memory: micro-trajectories → macro-experience → domain knowledge. Structural entropy
pruning reduces inference time 50%+ without accuracy loss.
Action: add session-summary write as tier-2 between raw episodes and durable skill updates.

### MemReranker (arXiv:2605.06132) — Reasoning-Aware Memory Reranking
Key: semantic similarity miscalibrates for temporal/causal queries. MemReranker-4B: 0.737 MAP,
matching Gemini-3-Flash at 10-20% cost. Multi-teacher distillation + InfoNCE.
Action: augment Hindsight cosine reranking with memory-type routing (temporal vs causal vs coreference).

### Muscle Memory for Agents (arXiv:2608.08995) — Compile not Merely Retrieve [POST-BASELINE]
Key: for personalization, compiling recurring intent into specialist agents beats retrieval.
"Muscle Memory" paradigm: persistent compiled agents for recurring task types vs. RAG lookup.
Action: for Hermes recurring tasks (news briefings, security scans), consider skill-compiled
subagent configs rather than retrieval-augmented generation.

### Veracium "Ground Truth First" (arXiv:2607.21962) — Longitudinal Memory Evaluation
Key: backend rankings INVERT with history length. At 9 weeks: provenance-typed graph (Graphiti)
reaches 90%; curated-map drops to 72%. Write-stage quality predicts 24% failure rate vs 2%.
Action: add `volatility_class: [stable|volatile|ephemeral]` to Hindsight memories at write time.

### ActMem (arXiv:2603.00026) — Memory Retrieval + Causal Reasoning
Key: causal reasoning at retrieval time, not just semantic similarity.
Action: for complex memory queries, chain retrieved facts through a causal inference step.

---

## B. KNOWLEDGE GRAPH / ONTOLOGY EVOLUTION

### EMERGE (arXiv:2507.03617) — KG Update Benchmark
Key: benchmark for updating KGs with emerging textual knowledge; temporally increasing KG deltas.
Action: use as design reference for Graphiti update policy and Religion KG evolution strategy.

### PrimeKG-CL (arXiv:2605.10529) — Continual Learning on Evolving KGs
Key: 5.83M edges added, 889K deprecated between two biomedical KG snapshots. Standard metrics
conflate retention of valid vs deprecated facts — only DistMult separates these signals.
Action: add `is_deprecated` boolean + `deprecated_at` timestamp to Graphiti edges.
Religion KG: implement `owl:deprecated` + `dcterms:modified` on RDF triples.

### Agentic-KGR (arXiv:2510.09156) — Co-evolutionary KG via Multi-Agent RL
Key: dynamic schema expansion beyond predefined boundaries; retrieval-augmented memory that
co-evolves with knowledge structure; learnable multi-scale prompt compression.
Action: allow Graphiti to accept new relation types dynamically; track schema_versions table.

### RELIC (arXiv:2607.16745) — Cross-Agent Skill Transfer via Textual Principles
Key: heterogeneous-interface agents share knowledge via textual principles (compact abstractions)
not executable code. Shared principle memory promotes principles that repeatedly improve team.
Action: implement principle extraction step post-successful run → global_principles.md.
Store principles as PRINCIPLE nodes in Graphiti linked to SKILL nodes via DERIVED_FROM edges.

---

## C. SKILL ARCHITECTURE

### PoisonedEvolution (arXiv:2608.05563) — Trajectory Poisoning Defense [POST-BASELINE]
Key: 3 consistent poisoned records in 30-record batch (10%) achieve 91% SER across 6 LLM evolvers.
Bottleneck is Evolution Attribution — behavior must appear causally useful, recurrent, generalizable.
Action: add source_episodes + evidence_count + trust_level to SKILL.md frontmatter.
Minimum 5 distinct session trajectories before promoting experimental→validated.

### RethinkSkill (arXiv:2608.02636) — Feedback Dynamics in Self-Evolving Skills [POST-BASELINE]
Key: skill evolution is sparse (14% of attempts improve). Success-only feedback cannot improve
skills — failed trajectories required. Validation/downstream metrics sometimes disagree.
Action: add `failed_trajectories: []` to SKILL.md; use downstream score over validation when they disagree.

### SkillComposer (arXiv:2606.06079) — Create/Improve/Merge Skill Operations
Key: specification-generalization tension. Merge + Improve address orthogonal quality dimensions.
4B skill composer improves 27B executor by +4.5 on agent tasks.
Action: add skill_merge operation detecting >70% trigger overlap; implement skill_improve with
validation gate.

### HASTE (arXiv:2606.30911) — Hierarchical Skill Accumulation (ICML 2026 DL4C)
Key: 3-tier hierarchy: global → domain → task-specific. 159 skills: 100% medal rate vs 62.5%
flat loading. Warm starts reduce iterations 52%; acceptance rises 42%→85% at 50+ skills.
Action: add `tier: [global|domain/<cat>|task]` to SKILL.md frontmatter; load only global+domain at start.

### SkillsBench (arXiv:2602.12670 v4) — Benchmarking Skill Efficacy
Key: skills raise pass rate 33.9%→50.5% (+16.6pp). Skills with ≤3 procedural modules
outperform larger bundles. Smaller models + skills match larger models without skills.
Action: enforce ≤3 numbered step groups per skill; split larger skills.

### ECAT (arXiv:2608.09273) — Self-Evolving Memory Tree for Code Migration [POST-BASELINE]
Key: successful low-entropy trajectories distilled into hierarchical memory tree. Incremental
updates. Transferable across repositories without retraining.
Action: implement skill_tree.json hierarchical index; insert new skills at appropriate level post-task.

---

## D. AGENT EVALUATION

### RECON (arXiv:2607.16716) — Compositional Reasoning over Long Contexts
Key: cascading invalidation propagation, source conflict resolution, counterfactual timelines.
Top non-Oracle: 22.4% accuracy. Critical gap: agents can retrieve changed facts but cannot
propagate downstream consequences.
Action: add cascade_invalidation logic in Hindsight when facts deprecated; downstream graph traversal.

### HOB Human-on-the-Bridge (arXiv:2606.16871) — Scalable Agentic Evaluation
Key: Red-Team Traps, Juror Personas, ProofAgent Harness. Surfaces phantom tool-call claims,
missing mandatory tool calls, policy drift, safe-but-non-resolving refusals.
Action: add `red_team_traps: [list]` to SKILL.md frontmatter; periodic skill_audit cron.

---

## E. CONTEXT / COMPRESSION

### AutoWorldBuilder (arXiv:2607.09403) — 4-Layer Context Compression (Chinese-origin)
Key: ~90% token reduction. 4 layers: concept network + conflict detection; DAG semantic scheduling;
iterative review with Auditor agents (42%→85% proposal acceptance); skill-driven differentiated temp.
Action: adopt layer-as-budget compression: L1=current (full), L2=recent (2:1), L3=historical (10:1),
L4=Graphiti/Hindsight (query-retrieved). Separate generation from validation agents.

### MoRSE (arXiv:2608.09251) — Mixture of Role-Subtask Experts [POST-BASELINE]
Key: task-oriented MAS with dynamic role-subtask expert assignment. Improves coordination on
complex multi-step tasks by matching agent specialization to subtask requirements.
Action: for Hermes delegate_task fan-outs, declare subtask role in context packet; route to
role-specialized subagent configs.

### Not Worth Another Token (arXiv:2608.08389) — Marginal Value Estimation [POST-BASELINE]
Key: research agents over-search. Marginal value of N+1th retrieval estimable without running it.
3 consecutive retrievals adding <5% new facts → evidence plateau → stop and synthesize.
Action: implement fact-plateau check in web research loops; terminate research when evidence plateaus.

---

*Sweep 4 conducted: 2026-08-11. arXiv coverage through 2608.09921. HAL/Zhihu/J-STAGE blocked.
Post-baseline papers: 2608.05563, 2608.02636, 2608.09273, 2608.08995, 2608.08389, 2608.09251.*
