# Agent Memory, KG & Skill Architecture — Aug 11 2026 Delta Sweep

Post-baseline sweep (cutoff: arXiv 2608.09885). All papers verified via direct `web_extract` on abs pages.
Full structured report: `/var/home/rainbow/research/2026-08-11_agent_kg_memory_skill_sweep.md`

---

## A. ONTOLOGY EVOLUTION & KG DESIGN

### A1. PrimeKG-CL — Continual Graph Learning on Evolving KGs
**arXiv:** 2605.10529 | **Date:** May 2026 | **Code:** github.com/yradwan147/primekg-cl-neurips2026

Real KGs evolve asynchronously: 5.83M edges added, 889K deprecated between two snapshots of the same biomedical graph. **Critical finding:** standard metrics conflate *retention of valid facts* with *failure to forget deprecated ones* — only DistMult separates these signals (RotatE does not). Decoder × CL-strategy interaction is strong; no single combo dominates.

**Hermes action:** Add `is_deprecated` boolean + `deprecated_at` timestamp to Graphiti edges. Never delete stale facts — flag them. Implement stratified queries: `persistent`, `added`, `deprecated` as first-class query categories.

---

### A2. Agentic-KGR — Co-evolutionary KG via Multi-Agent RL
**arXiv:** 2510.09156 | **Date:** Oct 2025

Three innovations: (1) dynamic schema expansion — ontology grows beyond predefined boundaries during RL training; (2) retrieval-augmented memory co-evolving with knowledge structure; (3) learnable multi-scale prompt compression preserving critical info at reduced token cost. GraphRAG integration gives gains on downstream QA.

**Hermes action:** Accept new relation types dynamically during Graphiti write operations (not just predefined schema). Track schema versions in `graph_schema_versions` SQLite table.

---

### A3. Engram — Bi-Temporal KG Memory Engine  ⭐ HIGH PRIORITY
**arXiv:** 2606.09900 | **Date:** Jun 2026 | **Code:** github.com/ly-wang19/engram

**Bi-temporal model** = core insight: every fact stores (1) *valid time* (when true in world) and (2) *transaction time* (when system learned it). Enables point-in-time `as-of` queries. Contradictions resolved by *invalidating* facts (`valid_to: now`, supersession chain kept), never deleting. Hybrid read path: dense + lexical + graph + recency/salience signals.

**Result:** 83.6% vs 73.2% full-context on LongMemEval_S (+10.4pp, McNemar p < 10^-6) at 8× fewer tokens (9.6k vs 79k).

**Hermes action (HIGH PRIORITY):**
- Add `valid_from`, `valid_to`, `recorded_at`, `superseded_by` to Hindsight SQLite memories table
- Implement `as_of(timestamp)` filter: `WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)`
- Add `valid_time_start`, `valid_time_end`, `transaction_time` to Graphiti edges
- Engram code (open-source) can be studied for the hybrid read path implementation

---

## B. MEMORY TOPOLOGY

### B1. SEEM — Structured Episodic Event Memory
**arXiv:** 2601.06411 | **Date:** Jan 2026

Introduces **Episodic Event Frames (EEFs)** anchored by provenance pointers — each episode structured as a cognitive "frame" (who, what, when, where, why). Graph memory layer handles relational facts; episodic layer handles narrative progression. **Reverse Provenance Expansion (RPE)** reconstructs coherent narratives from fragmented evidence. Significantly outperforms flat RAG on LoCoMo and LongMemEval.

**Hermes action:** Restructure Hindsight write path to extract `{agent, action, object, temporal_context, session_id}` EEF JSON alongside raw text. Add RPE query mode: given a question, expand to all memories sharing same `session_id` or `agent`.

---

### B2. VTM-Nav — Hierarchical Visual-Topological Memory
**arXiv:** 2607.14514 | **Date:** Jul 2026

Cross-episode memory reuse without retraining via two-level hierarchy: *coarse room topology* (graph) → *room-owned visual memories* (detailed records). Re-localization pins agent in accumulated scene structure before querying. Distinguishes in-scope vs. remote-visible evidence. Result: +4.6 SR points on HM3D at same step budget.

**Hermes action:** Two-level skill retrieval: (1) `CATEGORY` nodes (coarse, always loaded) → (2) skill content (loaded on demand). In Graphiti: `CATEGORY` nodes own `SKILL` nodes; queries resolve category first, then fetch specific skill edges.

---

### B3. Veracium / "Ground Truth First" — Longitudinal Memory Evaluation  ⭐ HIGH PRIORITY
**arXiv:** 2607.21962 | **Date:** Jul 2026 | **Code:** github.com/veracium-ai/Veracium

**Ground-truth-first design:** generate facts with validity intervals and volatility classes *before* any text, so gold answers are script-valid by construction. Key finding: **backend rankings invert at 9 weeks** — curated-map memory drops from 96% to 72% while a provenance-typed graph rises to 90%. Write-stage quality strongly predicts downstream quality (weakly-written facts fail 24% vs 2%). Injection resistance: tracked whether provenance boundaries survive representation.

**Hermes action (HIGH PRIORITY):**
- Add `volatility_class: [stable|volatile|ephemeral]` to Hindsight memories at write time
- Ephemeral facts (e.g., pricing) expire in 7 days; stable facts (e.g., doctrine) persist indefinitely
- Graphiti (provenance-typed graph) beats Hindsight flat memory at 9-week horizon — use Graphiti for long-lived entities

---

### B4. RECON — Compositional Reasoning over Long Contexts (Memory Eval Benchmark)
**arXiv:** 2607.16716 | **Date:** Jul 2026

Six memory-intensive tasks missing from prior benchmarks: cascading invalidation propagation, source conflict resolution, counterfactual timelines, temporal constraint satisfaction, multi-hop evidence reconstruction. Best non-Oracle: **22.4% accuracy**. Agents can retrieve changed facts but cannot propagate *downstream consequences* of changes.

**Hermes action:** Add `cascade_invalidation` logic: when a fact is marked deprecated, identify all Hindsight entries citing it (via `source_episode`) and flag `needs_review`. In Graphiti: downstream propagation query — when node A changes, traverse outgoing edges to flag dependent conclusions.

---

### B5. MemReranker — Reasoning-Aware Memory Reranking
**arXiv:** 2605.06132 | **Date:** May 2026

Standard semantic similarity reranking miscalibrates for temporal and causal queries. MemReranker (0.6B/4B on Qwen3-Reranker) uses multi-teacher pairwise comparisons (calibrated soft labels) + BCE pointwise distillation + InfoNCE contrastive learning for hard-sample discrimination. Result: MemReranker-0.6B matches open-source 4B/8B models on key metrics; MemReranker-4B achieves 0.737 MAP at 10-20% the inference cost of large models.

**Hermes action:** Augment current cosine-similarity retrieval in Hindsight with a reasoning-aware reranker. Qwen3-Reranker-0.6B is viable via Ollama. Flag memories as `temporal_constraint`, `causal_reasoning`, or `coreference_resolution` type at write time.

---

## C. SKILL ARCHITECTURE

### C1. PoisonedEvolution — Trajectory Poisoning in SES  ⚠️ SECURITY CRITICAL
**arXiv:** 2608.05563 | **Date:** Aug 6, 2026 (POST-BASELINE)

Self-evolving skill systems (SES) are vulnerable to trajectory poisoning. With 10% attacker support (3 consistent records in 30-record batch): **91% Skill Embedding Rate (SER)** across 6 LLM evolvers in SkillClaw. Attack requires three conditions: (1) Inclusion, (2) **Evolution Attribution** (bottleneck — must appear causally useful, recurrent, generalizable), (3) Realization. Single record is weak; 3 consistent records suffice.

**Hermes action (CRITICAL):**
- Add `source_episodes: [session_id_list]` and `evidence_count: N` to SKILL.md YAML frontmatter
- Minimum 5 *distinct-session* trajectories before auto-promoting a skill (not 3 from same session)
- Add validation gate: candidate skill runs against held-out test cases before promotion
- Add `trust_level: [experimental|validated|production]` to SKILL.md frontmatter
- Auto-flag skills with strong causal language in description but no corresponding `constraints:` evidence

---

### C2. RethinkSkill — Feedback Dynamics in Self-Evolving Skills
**arXiv:** 2608.02636 | **Date:** Jul 31, 2026 (POST-BASELINE) | **Code:** github.com/HKUST-KnowComp/rethinkskill

Skill evolution is **sparse**: only 55/388 candidates become byte-distinct validation bests. Evolution helps (11/14 settings improve), but all successful gains come from feedback conditions including *failed trajectories*. **Success-only feedback cannot improve skills.** Extra test-time compute (parallel sampling) gets within 0.43 points on SearchQA but 30.96 points behind on SpreadsheetBench — skill persistence is irreplaceable for specialized domains.

**Hermes action:**
- Log sessions where skill invocation failed and surface to skill optimizer
- Add `failed_trajectories: [session_id_list]` to SKILL.md — improver must see these
- Sparsity expectation: ~14% of attempted skill evolutions produce improvement
- Validation-based selection: before replacing SKILL.md, run old vs new on 3+ held-out tasks

---

### C3. SkillComposer — Evolving Skills via Create/Improve/Merge
**arXiv:** 2606.06079 | **Date:** Jun 2026

Addresses specification-generalization tension: specific skills don't transfer; abstract skills give insufficient guidance. Three learnable operations: **create**, **improve** (task-specific refinement), **merge** (combine overlapping into generalized). `merge` and `improve` address orthogonal quality dimensions. A 4B composer improves a 27B executor by +4.5 on agent tasks.

**Hermes action:** Add `skill_merge` operation: detect skills with >70% trigger overlap and auto-propose merged version. Add `skill_improve` as constrained operation: existing skill + failed sessions → validated candidate.

---

### C4. HASTE — Hierarchical Skill Accumulation for Transfer  ⭐ HIGH PRIORITY
**arXiv:** 2606.30911 | **Date:** Jun 2026, ICML 2026 DL4C Workshop

Three-tier skill hierarchy: **global** (universal) → **domain** (area-specific) → **task** (local). Tiered loading with 159-skill inventory: 100% medal rate vs 62.5% for flat loading (same as no skills). Warm starts (global + domain transfer): 52% fewer refinement iterations; proposal acceptance rises from 42% (low inventory) to 85% (50+ skills).

**Hermes action (HIGH PRIORITY):**
- Add `tier: [global|domain|task]` to SKILL.md frontmatter alongside existing `category:`
- At session start: load all global skills + relevant domain skills; load task-specific on demand
- This directly formalizes Hermes's existing category system into a functional loading hierarchy

---

### C5. SkillsBench — Benchmarking Skill Efficacy
**arXiv:** 2602.12670 v4 | **Date:** updated Jun 2026

87 tasks, 18 model-harness configs. Skills raise average pass rate from 33.9% to 50.5% (+16.6pp). **Focused skills with ≤3 modules outperform larger bundles** — exhaustive packages hurt. Smaller models + skills can match larger models without skills.

**Hermes action:** Target ≤3 procedural modules per skill. Refactor large skills into focused sub-skills with `related_skills:` links. Paired evaluation methodology (no-skill vs skill baseline) validates actual value.

---

## D. CROSS-AGENT KNOWLEDGE TRANSFER

### D1. RELIC — Revealed Principles for Cross-Agent Skill Transfer
**arXiv:** 2607.16745 | **Date:** Jul-Aug 2026, ICML 2026 LM4Plan Workshop

Agents with heterogeneous interfaces share knowledge via **textual principles** (compact decision-logic abstractions) rather than executable code. A shared principle memory accumulates knowledge; principles that repeatedly improve team performance get promoted. Supports transfer across heterogeneous-role and shared-role cooperative teams.

**Hermes action:** Post-run principle extraction — extract 1-3 sentence decision principles (not full skill markdown) into shared `global_principles.md`. Lighter than full skill transfer; describes *what worked* abstractly.

---

### D2. ECAT — Self-Evolving Memory Tree for Cross-Repo Transfer
**arXiv:** 2608.09273 | **Date:** Aug 10, 2026 (POST-BASELINE)

Successful low-entropy translation trajectories distilled into a **self-evolving memory tree** — hierarchical structure where each node represents a learned migration pattern. Enables transferable knowledge across repositories without retraining.

**Hermes action:** Implement `skill_tree.json` hierarchical index alongside SKILL.md files. After a successful complex task, insert a new skill at the appropriate tree level.

---

## E. EVALUATION

### E1. HOB (Human-on-the-Bridge) — Scalable Agentic Evaluation
**arXiv:** 2606.16871 | **Date:** Jun 2026

Experts curate reusable evaluation intelligence upstream (Red-Team Traps, Juror Personas, audit rules); ProofAgent Harness executes repeatedly. 23,500 agent turns. Surfaces failures invisible to static benchmarks: **phantom tool-call claims**, **missing mandatory tool calls**, **policy drift**, **manipulation paths**, **safe-but-non-resolving refusals**.

**Hermes action:** Add `red_team_traps: [list]` to SKILL.md frontmatter. Track `phantom_tool_claim_count` in session logs. Periodic `skill_audit` cron runs Red-Team Traps.

---

## F. MULTILINGUAL NOTE

**HAL (French):** Bot-blocked by Anubis proof-of-work — no access.
**Zhihu (Chinese):** Anti-scraping block — no direct access.
**J-STAGE (Japanese), RISS/KISS (Korean):** Not directly accessible.

Chinese-institution papers recovered via English arXiv submissions: SkillComposer (Alibaba/Zhejiang), SEMA (Chinese Academy), Agentic-KGR, AutoWorldBuilder. This is consistent with prior sweeps — major Chinese AI research labs publish simultaneously to arXiv.

Vietnamese/Korean origin: RELIC (ICML 2026 LM4Plan) provides cross-agent skill transfer primitives.

---

## Priority Action Queue

| Priority | Action | Source |
|----------|--------|--------|
| 🔴 CRITICAL | Bi-temporal Hindsight schema (valid_from/valid_to/superseded_by) | Engram 2606.09900 |
| 🔴 CRITICAL | Skill poisoning defense: provenance + 5-session evidence threshold | PoisonedEvolution 2608.05563 |
| 🟠 HIGH | `volatility_class` on Hindsight memories + Graphiti for long-horizon | Veracium 2607.21962 |
| 🟠 HIGH | 3-tier skill hierarchy (tier: global/domain/task) + tiered loading | HASTE 2606.30911 |
| 🟡 MEDIUM | Failed-trajectory logging in SKILL.md | RethinkSkill 2608.02636 |
| 🟡 MEDIUM | EEF-structured episode write + RPE retrieval | SEEM 2601.06411 |
| 🟡 MEDIUM | Cascade invalidation propagation in Graphiti | RECON 2607.16716 |
| 🟢 LOW | RELIC principle extraction → global_principles.md | RELIC 2607.16745 |
| 🟢 LOW | SkillComposer merge/improve operations | SkillComposer 2606.06079 |
| 🟢 LOW | MemReranker integration (temporal/causal reranking) | MemReranker 2605.06132 |
