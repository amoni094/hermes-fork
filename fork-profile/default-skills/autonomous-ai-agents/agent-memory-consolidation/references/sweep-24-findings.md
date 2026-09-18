# Sweep 24 Findings — Aug 25 2026

**Cutoff:** 2608.23552 → 2608.23566
**Sources:** arXiv (5 parallel subagents), GitHub trending, Hacker News (Aug 18–25 2026)

---

## HIGH findings

### ScrubJay-MEM — Type-Conditioned Temporal Decay (arXiv:2608.04746)
**Caching for the Future: Scrub Jay Episodic Memory Principles for Agent Memory Systems**

Key findings:
- Per-memory **type-conditioned decay** (π_i coefficient per content type) — global lambda is wrong
- What–Where–When tuple structure with utility horizon τ_i per fact
- **Temporal Generalization Test (TGT)** + **GenGap metric** (+0.108 when decay is type-conditioned)
- Decay ablation collapses GenGap **5.7×** — type-conditioned decay is necessary, not optional

**Applied to scripts:**
- `l1-promote.py`: ScrubJay lambdas already in place (stable=0.005, volatile=0.05, ephemeral=0.5)
- These ARE type-conditioned (by volatility class) — structurally correct

**Diagnostic to adopt:**
- **GenGap metric** = accuracy at long retention interval minus accuracy at short interval
  Negative GenGap = decay rate is too aggressive. Positive = system generalizes across time.
- Can be approximated by comparing hindsight recall accuracy of 30d-old vs 7d-old facts.
- Add to `memory-staleness.py` output: `genGap = accuracy_30d - accuracy_7d`

**Additional finding:** Gains **reverse on fact-consolidation tasks** when facts are perishable
in the training domain but stable in deployment. Watch for over-decay of procedure facts
(stable class) under user-context shifts.

---

### Episodic-Semantic Dual Process (arXiv:2605.17625)
**Dual Process Architecture for LLM Agent Memory**

Key findings:
- Constant 10-message episodic window (volatile) + growing consolidated semantic (stable)
- 70–85% accuracy at 10K messages with 62% fewer tokens
- **Consolidation quality** is the primary scalability bottleneck, not retrieval mechanism
- RAG excels at historical retrieval; dual-process excels at numeric/temporal — complementary

**Applied insight:** Volatile TTL (30d calendar) may be better expressed as a **message-count
cap** (N recent sessions) rather than absolute calendar days. A 30d window that includes 1
session is very different from one with 50 sessions.

**Recommendation:** `memory-ttl-purge.py` — add a secondary `max_volatile_sessions=20` cap:
if a volatile fact's source session is >20 sessions ago (regardless of calendar age), it's
eligible for review. This prevents sparse-usage users from accumulating stale volatile facts.

---

### CraniMem — Bounded Episodic Buffer (arXiv:2603.15642)
**Goal-Conditioned Memory Gating with Utility-Aware Consolidation**

Key findings:
- Bounded episodic buffer with hard size cap + utility-ranked eviction
- Scheduled consolidation: high-utility traces → KG; low-utility items pruned
- More robust than Mem0 under injected noise/distraction

**Applied insight:** Current ephemeral tier has no hard size cap — it's score-only. CraniMem
validates adding a **hard cap** on ephemeral tier size: when full, evict oldest regardless of
score. This prevents accumulation under heavy session load.
- Suggest: `max_ephemeral_facts = 500` (configurable) in `l1-promote.py`

---

### G-Memory — Hierarchical 3-Tier KG (arXiv:2506.07398)
**Hierarchical Memory for Multi-Agent Systems**

Key findings:
- Three-tier: interaction graph → query graph → insight graph
- Bi-directional traversal: retrieve both high-level insights AND recent interactions
- +20.89% embodied action, +10.12% knowledge QA
- Whole hierarchy co-evolves via trajectory assimilation

**Applied to l1-graphiti-write.py:**
- `--on-session-complete` mode added (sweep 24) to support session-boundary write trigger
- Maps: ephemeral → interaction graph, volatile → query graph, stable → insight graph

**Still needed:** Bi-directional retrieval in Graphiti queries:
- Current: `mcp__graphiti__search_memory_facts(query)` — returns top-k facts only
- Needed: also call `mcp__graphiti__search_nodes(query)` and merge, to get high-level insight
  nodes alongside fine-grained interaction records
- Add this pattern to `hindsight_recall` wrappers and `agent-memory-consolidation` skill

---

### Memora + FAMA Metric (arXiv:2604.20006)
**Forgetting-Aware Memory Accuracy for Long-Term Agent Evaluation**

Key findings:
- **FAMA** penalizes reliance on obsolete/invalidated memory
- Dominant failure mode: **frequent reuse of invalid/stale memories**
- Memory agents offer only marginal improvements over no-memory baseline (without TTL)
- Human evaluation confirms: reconciling evolving memories is the core challenge

**Applied to memory-ttl-purge.py (sweep 24):**
- FAMA-style staleness logging added: stale access events tracked to `memory-staleness-log.jsonl`
- TTL enforcement already in place — FAMA validates it as non-optional

**FAMA as health metric:**
- Track ratio: `stale_accesses / total_accesses` per week from `memory-staleness-log.jsonl`
- Target: < 5% stale access rate (current baseline unknown — establish first measurement)
- Add to monthly skill-prune-audit cron report

---

### SkillEvolBench — Critical Negative Result on Skill Abstraction (arXiv:2605.25430)

Key findings:
- **Raw trajectory reuse frequently outperforms distilled skills**
- Over-abstraction discards contextual cues that remain useful at test time
- Writing more skills introduces **procedural clutter and drift**
- Gains from distillation unstable under frozen deployment

**Applied to l1-promote.py (sweep 24):**
- Stable promote threshold raised from 0.35 → 0.45 with recurrences ≥ 2 gate
- Cold-fact penalty (15% score reduction for 0-recurrence facts)

**Implication for skill library:** Prefer narrow, evidence-backed skills with stated scope
over broad procedural skills. See: `hermes-agent-skill-authoring` SkillAlchemy section.

---

### SkeMex — Read-Write-Assess-Govern Lifecycle (arXiv:2606.09365)

Key findings:
- Read→Write→Assess→Govern closed loop for continual memory evolution
- Context-dependent utility (not static threshold) for retrieval + governance
- Promotes useful memories, removes harmful entries
- Multi-branch: general + task-specific + action-level

**Applied:** Retrieval-frequency signal added to `l1-promote.py` (cold-fact penalty).
Govern step maps to `memory-ttl-purge.py` + `memory-staleness.py`.

**Gap:** The **Assess** step (checking current utility, not just historical score) is not yet
implemented. A fact that was high-utility 6 months ago but has never been retrieved since
should decay. The cold-fact penalty in `l1-promote.py` approximates this but doesn't track
time-since-last-retrieval. Add `last_retrieved_at` field to `fact_lifecycle` schema.

---

## MED findings (documented, deferred)

| ID | Title | Target | Why deferred |
|---|---|---|---|
| 2607.14275 | Context Quality Score (7 criteria) | hermes-context-budgeting | Already covered by CompactionCliff section |
| 2606.10921 | DocTrace On-Demand Hypergraph | l1-graphiti-write.py | On-demand trigger added; hypergraph structure TBD |
| 2511.11017 | 3-Agent KG Construction Pipeline | l1-graphiti-write.py | Architecture pattern — future iteration |
| 2505.04016 | SLOT Schema Enforcement | l1-extract.py | Constrained decoding — needs l1-extract refactor |
| OzBrain HN | graphiti 50k node hard limit | l1-graphiti-write.py | Monitor node count; implement tier eviction at 40k |

---

## Architecture notes

### Graphiti 50k Node Limit (OzBrain HN thread, 92 pts)
Teams hit retrieval latency cliffs at ~50k KG nodes. Current Hermes KG size unknown.

**Action:** Add node count check to l1-graphiti-write.py:
```python
# Check node count before write; warn at 40k, halt at 50k
result = mcp_request(session_id, "tools/call", {"name": "mcp__graphiti__get_status", ...})
```
Add quarterly node-count audit to cron schedule.

### volcengine/OpenViking — Self-Evolving Context Database
ByteDance production system that unifies Memory + RAG + Skills in one self-pruning store.
Most relevant: **eviction policy** (LRU + utility-score hybrid) and **skill indexing model**
(semantic similarity over skill descriptions for on-demand retrieval).

Study: https://github.com/volcengine/OpenViking — compare eviction policy against current
`memory-ttl-purge.py` logic.

### akitaonrails/ai-memory — Cross-Vendor Handoff Format (Rust)
Serialization format for cross-session, cross-vendor memory portability.
Relevant for: hindsight export format if Hermes profile is ever migrated or backed up.
URL: https://github.com/akitaonrails/ai-memory

---

## Sweep boundary

Next sweep starts above: **2608.23566**
