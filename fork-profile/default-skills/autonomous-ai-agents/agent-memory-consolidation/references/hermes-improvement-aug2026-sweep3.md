# Hermes Improvement Research — Aug 2026 Sweep 3
# Generated: 2026-08-11
# Previous sweeps: hermes-improvement-aug2026-sweep2.md (Aug 2026)

This document records net-new findings from the third multilingual research sweep
(academic, web, GitHub, social). Items marked [IMPLEMENTED] have been patched into
skills. Items marked [TIER-2] are validated but require infrastructure changes.

---

## Key Finding Index

| Paper | arXiv | Implemented In | Status |
|---|---|---|---|
| ScrubJay-MEM type-conditioned decay | 2608.04746 | agent-memory-consolidation | IMPLEMENTED |
| SYNAPSE spreading activation | 2601.02744 | agent-memory-consolidation | IMPLEMENTED |
| SkillReact compositional risk | 2606.00448 | hermes-skillspector-guard-maintenance | IMPLEMENTED |
| GenericAgent IDM + hierarchical memory | 2604.17091 | agent-memory-consolidation, hermes-context-budgeting | IMPLEMENTED |
| Headroom tool output compression | github.com/headroom-ai/headroom | hermes-context-budgeting | IMPLEMENTED (docs) |
| Coordination layer separation | 2605.03310 | autonomous-agent-loop-design | IMPLEMENTED |
| RePro retrospective before action | 2606.14302 | autonomous-agent-loop-design | IMPLEMENTED |
| SkillTV-Bench trajectory eval | 2608.05573 | agent-skill-management-research-2026.md | IMPLEMENTED |
| SSGM memory governance | 2603.11768 | agent-memory-consolidation refs | IMPLEMENTED |
| Prompt caching strict ordering | empirical/Anthropic | hermes-context-budgeting | IMPLEMENTED |
| OL-KGC ontology KG completion | 2507.20643 | — | TIER-2 |
| DreamGuard hallucination detection | 2608.05695 | — | NOTED (see sweep2) |

---

## 1. ScrubJay-MEM: Type-Conditioned Temporal Decay (arXiv:2608.04746)
**BITS Pilani, Aug 5 2026 — net-new to this sweep**

Memory perishability varies by type. One-size-fits-all TTL poisons retrieved context
with stale facts of the most durable types while evicting too-early facts of perishable types.

**What-Where-When tuple encoding:**
- What: the fact content (semantic)
- Where: the source/context at write time (episodic anchor)
- When: write timestamp + scheduled re-verification date

**Per-type decay parameters (π = perishability 0-1, τ = utility horizon in days):**
| Memory type | π | τ |
|---|---|---|
| Current task state | 0.95 | 1 |
| Tool behavior quirks | 0.3 | 90 |
| User preferences | 0.1 | 365 |
| Environment facts (OS, config) | 0.2 | 180 |
| Project architecture facts | 0.15 | 120 |
| Security/credential patterns | 0.4 | 30 |

**GenGap metric:** measures gap between what the agent believes (retrieved memory) and
ground truth. High GenGap = retrieval of stale facts. Use as a diagnostic when agent
outputs contradict observed system state — the gap is likely stale memory, not hallucination.

**Retroactive update:** when a memory is found stale, update can be done in O(1) LLM
call per stale entry (re-verify the What against current system state, update When, keep Where).

**Where implemented:** agent-memory-consolidation SKILL.md (ScrubJay-MEM section)

---

## 2. SYNAPSE: Episodic-Semantic Spreading Activation (arXiv:2601.02744)

Two-layer memory graph:
- Episodic layer: specific events, timestamped, source-anchored
- Semantic layer: abstracted generalizations derived from episodic clusters

Retrieval uses spreading activation: start from the seed query node; activate
neighbors proportional to edge weight × node importance; include nodes above
activation threshold. This naturally includes associated context the query didn't
name explicitly — e.g., querying "firecrawl timeout" also activates "web_extract
fallback" and "JavaScript-heavy pages" as associated nodes.

**Hermes mapping:**
- Episodic = Hindsight raw episodes + Graphiti episode nodes
- Semantic = Hindsight promoted summaries + Graphiti entity nodes (after l1-promote)
- Spreading activation = currently missing; approximated by hindsight_reflect's
  cross-memory synthesis, but not graph-traversal-based

**Gap:** Hermes currently has no spreading activation retrieval. hindsight_recall
does embedding similarity; hindsight_reflect does cross-synthesis. Neither propagates
through the graph topology. The Graphiti MCP search_memory_facts is the closest
approximation (it does graph-traversal). Use search_memory_facts over hindsight_recall
when the query has associative context (related entities) rather than direct keyword match.

**Where implemented:** agent-memory-consolidation SKILL.md (SYNAPSE section)

---

## 3. SkillReact: Compositional Skill Risk (arXiv:2606.00448)

Per-skill safety scans are insufficient. 211,575 individually-safe skill pairs evaluated
from 1,520 ClawHub skills. 18.2% of flagged pairs contain genuine compositional risk
(population-weighted validity) — invisible to per-skill scans because every pair is
individually safe.

10 forbidden capability patterns identified (primary: file_read+network_out,
credential_access+network_out, shell_exec+network_out, file_write+shell_exec).
Model disposition: Haiku-4-5 most compliant with risky compositions; Sonnet-4-6 refuses
outright. Full details in hermes-skillspector-guard-maintenance (new SkillReact section)
+ agent-skill-management-research-2026.md (new Section 8).

**Implementation gap:** the current skillspector scanner is per-skill. A pairwise
scan extension would require iterating over skill pairs loaded together (from session
history / cron task definitions) and checking co-presence of risk signals.

**Where implemented:** hermes-skillspector-guard-maintenance (new SkillReact section)
+ agent-skill-management-research-2026.md (new Section 8)

---

## 4. GenericAgent: Context Information Density Maximization (arXiv:2604.17091)

Three principles (all applicable to Hermes):

1. **Hierarchical on-demand memory:** abstract first, detail on demand
   - Already partially implemented via skill description cap + category grouping
   - Gap: skills not relevant to current task still inject full descriptions
   - Future: collapse non-matching skills to name-only (SkillReducer pattern)

2. **Minimal atomic tool set:** orthogonal ops, no overlap
   - Hermes already has clean separation: retain/recall/reflect/replace/remove
   - Anti-pattern to avoid: adding new memory tools that overlap existing ones

3. **SOP extraction from verified trajectories:** distill novel procedures into skills
   - Already the core of self-improve-agent skill
   - GenericAgent provides independent validation of this mechanism

**Where implemented:** agent-memory-consolidation (new GenericAgent section)
+ hermes-context-budgeting (new GenericAgent note in prompt caching section)

---

## 5. Headroom: Tool Output Compression (github.com/headroom-ai/headroom)

Apache 2.0, ~65K GitHub stars (Aug 2026). Dedicated library for compressing tool
output before context injection.

- 60-70% average token reduction; 90-95% on HTML/JSON-heavy outputs
- `pip install headroom-ai[all]`
- Open Hermes GitHub issue: #39691 (native integration)

Acts at ingestion time (before context accumulates), complementary to micro_compact
(at accumulation) and idle_compact (at session end). Should be applied manually until
native integration lands — especially useful for web_extract and terminal results.

**Where implemented:** hermes-context-budgeting (new Headroom section)

---

## 6. Coordination as Separable Layer (arXiv:2605.03310)

41-87% of multi-agent production failures are coordination defects, not per-agent failures.
Coordination logic embedded in worker prompts = undiagnosable failures.

Separation principle: orchestrator owns task decomposition, message routing, failure
handling, consensus reduction. Workers own execution only.

New checklist added to autonomous-agent-loop-design for multi-agent tasks.

**Where implemented:** autonomous-agent-loop-design (new Coordination section + checklist)

---

## 7. RePro: Retrospective Before Next Action (arXiv:2606.14302)

Short retrospective before each new phase prevents re-committing the same error class.
Manual discipline: ~50 tokens, prevents most "elaborating on wrong direction" failures.

**Where implemented:** autonomous-agent-loop-design (new RePro section, Tier-2 note)

---

## 8. Prompt Caching Strict Ordering

Empirically validated ordering: tools → system → docs → history → query.
Cache hit rate <60% = volatile content in the stable prefix.

Key Anthropic-specific: cache TTL = 5 minutes. micro_compact every 3 turns at ~2 min/turn
= 6 min → compaction-triggered system prompt changes miss cache. micro_compact should write
to TASK DYNAMIC section only.

**Where implemented:** hermes-context-budgeting (new section) + compression-research-2026-08.md
(already had partial coverage; new section unifies and links)

---

## TIER-2: Not Yet Implemented

### OL-KGC: Ontology-Enhanced KG Completion (arXiv:2507.20643)
Neural-symbolic integration for knowledge graph completion using LLM + ontological reasoning.
Relevant to the Religion KG project and any multi-entity long-horizon memory system.
Would require changes to the Graphiti ingestion pipeline or a separate ontology-layer query pass.
Defer until Religion KG v2 or a Graphiti extension is being built.

### Headroom Native Integration
Waiting on Hermes GitHub issue #39691. Manual usage pattern already documented.
When native integration lands, the hermes-context-budgeting Headroom section should be
updated to remove the manual-use note and reference the config option instead.

### SYNAPSE Spreading Activation in Retrieval
Currently approximated by hindsight_reflect + Graphiti search_memory_facts.
True graph-traversal spreading activation would require either a Graphiti extension
(graph-traversal retrieval API) or a post-recall graph hop over returned node neighbors.
Not blocked, but no immediate implementation path without modifying the Hindsight plugin.

---

## Adversarial Pass — Findings After Sweep 3

No contradictions found between sweep3 additions and prior content. Verified:
- ScrubJay-MEM decay types do not conflict with FFD taxonomy (they extend it at the type level)
- SkillReact pairwise risk is strictly additive to per-skill scan (not a replacement)
- GenericAgent SOP extraction is consistent with self-improve-agent (independent validation)
- Coordination layer principle is consistent with hermes-swarm-consensus and hermes-role-pipelines
- Headroom operates at a different layer from micro_compact (no overlap)
- RePro is marked Tier-2 to avoid implying a session-loop change was made

One duplication removed: prompt caching ordering was partly in compression-research-2026-08.md
and partly in autonomous-agent-loop-design's "Prompt Caching for Autonomous Loops" section.
The new hermes-context-budgeting section now serves as the canonical reference. No content
was deleted from existing sections — they were left as-is since they have different angles
(one is about cost, one is about cache structure). If they diverge in future, consolidate
into hermes-context-budgeting and link from the other locations.

---

## Sources

- arXiv: 2608.04746, 2601.02744, 2606.00448, 2604.17091, 2605.03310, 2606.14302, 2603.11768, 2507.20643, 2608.05573
- github.com/headroom-ai/headroom
- Anthropic prompt caching docs + empirical study arXiv:2601.06007
- Research agents: task-0 (code/config/architecture), task-1 (memory/ontology), task-2 (skills/workflows)
- Hindsight recall: prior research sessions Aug 2026 sweep 1 + 2
