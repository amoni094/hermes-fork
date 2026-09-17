## MemGraphRAG 3-layer validation (arXiv:2606.00610, KDD 2026)

MemGraphRAG defines a 3-layer memory architecture for graph-based RAG:
  Layer 1: unstructured passages (raw source text)
  Layer 2: extracted structured facts (entities + relations)
  Layer 3: abstract schemas / ontological summaries

Results: 91% accuracy on 200 projects / 1,000 test queries; 78% reduction in per-project
research time vs baseline RAG. Outperforms SOTA on graph quality, retrieval quality, generation accuracy.

The Hermes Hindsight + l1-pipeline ALREADY implements this structure:
  Layer 1 = Hindsight raw episode storage (episodic memory)
  Layer 2 = l1-extract.py -> memory-facts/ (structured fact extraction)
  Layer 3 = l1-promote.py -> staging.md -> Hindsight semantic summaries (abstract schemas)

MemGraphRAG validates the existing 3-layer design. The missing upgrade path:
Graphiti MCP (already installed) provides a graph database for Layer 2+3 that supports
relation traversal and cross-session entity resolution — currently the l1-pipeline produces
flat facts with no graph traversal. This is the open question for long-horizon multi-project
work (religion KG, PPOR, trading notes): does Graphiti's graph-layer outperform flat Hindsight
for multi-week multi-entity queries?

## ERL heuristic distillation (arXiv:2603.24639, ICLR 2026)

Experiential Reflective Learning: reflect on task trajectories -> generate transferable
heuristics -> retrieve relevant heuristics at inference time.
Results: +7.8% success rate on Gaia2 vs ReAct baseline.

Key finding: heuristics (actionable generalizations) transfer better across tasks than
few-shot trajectory examples. Selective retrieval is essential — injecting all heuristics
degrades performance.

Hermes consolidation rule: after a complex task, the consolidation step should extract
a HEURISTIC not a procedure. Ask: "what was the transferable lesson?" not "what did I do?"
Verbatim trajectory transcripts in memory degrade future performance vs distilled heuristics.

Good heuristic form: "When [trigger condition], [action] because [reason]."
Bad form: "First I did X, then Y, then Z."

Apply in the NREM phase of the cron consolidation loop: before writing to Hindsight,
pass episodic content through a heuristic-distillation prompt.

## LeanMem: 3-Tier Compressibility + Budget-Aware Retrieval (arXiv:2608.03463, Aug 2026) ⭐ CODE

+15.1 accuracy points on LoCoMo/LongMemEval-S at lowest construction cost and latency.

**Three compressibility tiers — classify at write time:**
| Tier | Content type | Update policy | Examples |
|---|---|---|---|
| profile | Stable user/agent attributes | Overwrite on change only | User preferences, skill capabilities |
| event | Dynamic episodic facts | Update on recurrence | Tool outcomes, session decisions |
| record | Verbatim immutable artifacts | Append-only | Exact error messages, API responses |

**Write rule:** only re-embed `event` tier on updates. `profile` and `record` are
write-once (profile overwrites; record appends). This cuts embedding costs 60-80%
in active sessions where tool outcomes dominate.

**Budget-aware retrieval:** allocate different token budgets per query type:
- Preference/config queries → pull `profile` only (cheap)
- Retrospective/causality queries → pull `event` + `record` (expensive, needed)
- General knowledge queries → pull `event` + limited `profile` (medium)

**Hermes implementation:** tag each `hindsight_retain` call with
`context="profile"/"event"/"record"`. Apply type-conditioned retrieval budgets
at `hindsight_recall` time by filtering on the context tag before embedding search.

## MemSIF: Dual-Track Fact Memory — CoreFact/ActiveFact (arXiv:2608.01742, Aug 2026) ⭐ CODE

Identifies two root causes of memory system failures:
- **TSM (Temporal-Structural Misalignment):** temporal proximity ≠ topical relatedness.
  Facts written close together in time are not necessarily related — treating them as
  co-relevant degrades retrieval precision.
- **DUM (Delayed Utility Manifestation):** write-time salience ≠ future query utility.
  A fact important when written may be irrelevant later; a fact that seemed minor becomes
  critical when a related query arrives.

**Two-track response:**
- **CoreFact:** stable, schema-guided facts written eagerly at capture time. Written once;
  updated only on explicit contradiction. Maps to `profile` tier in LeanMem / MEMORY.md entries.
- **ActiveFact:** formed on-demand when a query arrives, promoted to durable storage
  only after being accessed N≥3 times. Maps to Hindsight staging pattern — do not write
  to MEMORY.md until the fact has been useful across multiple sessions.

**Concrete rule:** when a new fact surfaces that seems important but has never been
queried before, write it to Hindsight (staging), not to durable MEMORY.md. Promote only
after it appears in ≥3 independent retrievals. This directly addresses DUM.

**Structural write discipline (anti-TSM):** do not batch-write all facts from a session
together as a single Hindsight episode. Group by topic, not by temporal proximity.
Each `hindsight_retain` call should represent one coherent fact cluster, not one session.

## AMD: Skills-as-Memory Validation (arXiv:2608.07169, Aug 2026) ⭐ HIGHLY RELEVANT

Agent Memory Distillation achieves +27.2pp on AppWorld, +11.2pp on BFCL V3 by distilling
successful teacher trajectories into three memory types. This directly validates Hermes's
existing skills-as-markdown architecture:

| AMD memory type | Hermes equivalent | Notes |
|---|---|---|
| Workflow memory | Top-level skill YAML + trigger conditions | Task-level strategy |
| Subtask memory | Step-by-step sections within a skill | Intermediate behavioral patterns |
| Function memory | Pitfalls sections, per-tool annotations | Retrieved reactively on errors |

**Key finding:** Subtask memory (intermediate steps) contributes the largest gains — not
workflow-level strategy. This means Hermes skill files should prioritize detailed
**numbered step sequences** and **per-tool pitfall blocks** over high-level descriptions.

**Automatic skill population:** AMD suggests that successful trajectories from Claude runs
should be semi-automatically distilled into skill patches — specifically, any trajectory
where a novel multi-step tool sequence succeeded should trigger a `skill_manage(action='patch')`
to add or extend the relevant skill's step list. This is the self-improve-agent loop
with AMD's empirical validation behind it (+27pp is not marginal).

## IFCMemoryBench: 3-Axis Memory Quality Judge (arXiv:2607.26072, KDD Aug 9 2026)

Memory quality cannot be measured by retrieval similarity alone. Three independently
falsifiable axes:
1. **retrieval_relevant** — does retrieved content contain useful facts?
2. **retrieval_covers_key_facts** — are the *critical* facts present and not contradicted?
3. **answer_uses_memory** — does the agent's answer actually leverage the retrieved memory?

**Key finding:** systems frequently score high on axis 1 but fail axis 2. High retrieval
relevance + low key-fact coverage = fragmented storage (facts split across too many
entries, none complete enough to be actionable).

**Consolidation implication:** when writing to Hindsight, prefer one complete fact over
three partial facts covering the same topic. A single entry that answers axis 2 is more
valuable than three entries that each pass axis 1 but collectively fail axis 2.

**Audit trigger:** if you notice the agent retrieving memories but not actually using
them in its final answer, that is an axis 3 failure — the memory exists but is
irrelevant to the decision at hand. This signals that the fact should be rewritten
with a better cue (see MRAgent Cue-Tag-Content pattern above).

## CoEvoKG: Knowledge Graph + Agent Co-Evolution (arXiv:2608.01904, Aug 2026) ⭐ CODE

KG and agent co-evolve in a reinforcing loop:
- KG generates verifiable RL training tasks (multi-hop QA from entity chains)
- Agent writes successful search trajectories back to the KG as enriched evidence on nodes/edges
- Each round: better KG → better agent → richer KG

+10–11.6 macro-average points on 6 QA benchmarks; +2.6–3.7pp over competitive self-play.

**Hermes mapping:** the Graphiti MCP graph and Hindsight vector store can implement
this loop without new infrastructure:
1. Successful tool-use trajectories → distilled via l1-extract → Graphiti facts
2. Graphiti entity nodes → seed future `hindsight_recall` and session search queries
3. High-confidence Graphiti facts → promoted to skill pitfalls via skill_manage patch

This is the CoEvoKG loop at agent-memory scale. The current l1-pipeline already
implements steps 1-2; step 3 (Graphiti→skill) is the gap. When an entity in Graphiti
accumulates 3+ corroborating episodes, treat it as a candidate for skill annotation.

## GenericAgent: Hierarchical On-Demand Memory + SOP Extraction (arXiv:2604.17091, Apr 2026)

GenericAgent achieves context information density maximization through three principles:

**1. Hierarchical on-demand memory:** store facts at their most abstract level;
expose detail only when explicitly requested. This means:
- Hindsight stores full episodic records — never inject them wholesale into context
- MEMORY.md stores only compact declarative summaries (already enforced by the 2200-char limit)
- When retrieving: start with the highest-level abstract form; expand to detail only if the
  abstract answer is insufficient for the current query
- Apply this when calling `hindsight_recall`: read the summary first; call `hindsight_reflect`
  (full synthesis) only if summary-level recall doesn't resolve the task

**2. Minimal atomic tool set:** memory operations should be orthogonal (store / retrieve /
update / forget) with no overlap. Any two operations that do the same thing = redundancy.
Hermes already has this split (hindsight_retain / hindsight_recall / hindsight_reflect /
memory(replace/remove)). Do not add new memory tools that overlap with existing ones.

**3. SOP extraction from successful trajectories:** after a task that required a novel
multi-step procedure, distill it into a Standard Operating Procedure (SOP) and store as a
skill. The SOP is a numbered-step template parameterized for the task class, not a transcript.
This is the `self-improve-agent` skill's core loop — GenericAgent provides independent
validation that SOP extraction from verified trajectories is the right mechanism.

**Information Density Maximization principle (IDM):** at each token of injected context,
ask "does this token contribute to resolving the current task?" If no, remove it. Apply
this as a gate before any large context injection: list what facts are needed, retrieve
only those, discard the rest. This is stricter than the existing "no full file dumps" rule —
it extends to partial file reads, skill body injections, and memory retrievals.

## ScrubJay-MEM: Type-Conditioned Temporal Decay (arXiv:2608.04746, BITS Pilani, Aug 5 2026)

Memory systems that treat all memories as equally persistent contaminate retrieved context
with outdated facts. ScrubJay-MEM operationalizes western scrub jay episodic memory
principles: each memory is encoded as a jointly-bound What-Where-When tuple with a
type-conditioned perishability π_i and utility horizon τ_i.

**Key formula:** retrieval scoring = value_score × exp(-π_i × age / τ_i)
This surfaces still-valid memories and naturally deprioritizes stale ones, without explicit TTL clocks.

**Type-conditioned perishability values (calibrated from paper):**
| Memory type keyword | π_i (high = decays fast) | τ_i (utility horizon) |
|---|---|---|
| contains 'version', 'port', 'PR#', 'issue#' | 0.9 | 14 days |
| contains 'prefer', 'style', 'format' | 0.1 | 365 days |
| contains 'tool', 'config', 'workaround' | 0.5 | 90 days |
| contains '/session/temporary', 'today' | 1.0 | 1 day |
| contains 'how to', 'steps', 'workflow' | 0.4 | 180 days |
| default (declarative fact) | 0.3 | 120 days |

**GenGap metric (Temporal Generalization Test — TGT):**
GenGap = performance at held-out retention intervals − performance at trained intervals.
A positive GenGap means the memory system generalizes across time; negative GenGap means
it memorized the training window only. Apply this as a self-evaluation: periodically ask
"does Hindsight still surface facts correctly across different ages of memories?" A
systematic decline in older memories = negative GenGap = expiry calibration needed.

**Practical application to Hermes memory writes:**
When writing to MEMORY.md, Hindsight, or Graphiti, classify the memory type and
mentally tag it with a decay category. At each adversarial audit pass, apply the decay
scoring to entries that have aged past their τ_i horizon — propose removal rather than
letting them accumulate indefinitely.

**Retroactive update at O(1) LLM calls:** when a What-Where-When tuple is invalidated
(e.g. a port changes, a tool is replaced), a single targeted retrieve-then-update call
corrects the bound without invalidating the full memory store.

## Engram: Bi-Temporal Knowledge Graph Memory Engine (arXiv:2606.09900, Jun 2026)

Every fact stores (1) *valid_time* (when true in the world) and (2) *transaction_time*
(when the system learned it). Contradictions invalidate, never delete — supersession chain
preserved. On LongMemEval_S: 83.6% vs 73.2% full-context at 8x fewer tokens.

**Hermes action (HIGH PRIORITY):**
- Add `valid_from`, `valid_to`, `recorded_at`, `superseded_by` to Hindsight memories table.
- Implement `as_of(timestamp)` filter: `WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)`.
- In Graphiti: extend edges with `valid_time_start`/`valid_time_end` alongside `created_at`.
- Add `volatility_class: [stable|volatile|ephemeral]` at write time (ephemeral = 7-day TTL).

## PoisonedEvolution: Trajectory Poisoning Defense (arXiv:2608.05563, Aug 2026) ⚠️ CRITICAL

3 consistent poisoned records in 30-record batch (10%) achieve 91% Skill Embedding Rate
across 6 LLM evolvers. Attack requires Evolution Attribution: behavior appears causally
useful, recurrent, generalizable.

**Hermes action (CRITICAL):**
- Add to SKILL.md frontmatter: `source_episodes: []`, `evidence_count: 0`, `trust_level: experimental`.
- Minimum 5 *distinct session* trajectories before promoting experimental→validated.
- Add `failed_trajectories: []` — skill optimizer must see failures (RethinkSkill finding).
- Run causal framing audit: flag skills with strong causal language and no `constraints:` evidence.

## RethinkSkill: Feedback Dynamics (arXiv:2608.02636, Jul 2026)

Skill evolution is sparse: 14% of attempts produce improvement. Success-only feedback
CANNOT improve skills. Validation and downstream metrics sometimes disagree — trust downstream.

**Hermes action:**
- Log `failed_trajectories` to SKILL.md. Run old vs new on 3+ held-out tasks before promoting.
- Don't evolve skills on every run; trigger only after 3+ user corrections or task failures.

## HASTE: Hierarchical Skill Accumulation (arXiv:2606.30911, ICML 2026)

3-tier skill hierarchy: global → domain → task-specific. 159-skill inventory: 100% medal
rate vs 62.5% flat loading. Warm starts reduce iterations 52%.

**Hermes action (HIGH PRIORITY):**
- Add `tier: [global|domain/<cat>|task]` to SKILL.md frontmatter.
- Session start: load only global + relevant domain tier; load task tier on demand.

## SYNAPSE: Episodic-Semantic Spreading Activation Retrieval (arXiv:2601.02744, U. Georgia, ACL 2026)

Full implementation in `graphiti-mcp-setup` SKILL.md. Summary:

Flat top-k cosine similarity has a "Contextual Tunneling" problem — returns surface matches
but misses facts connected through intermediate concept hops. SYNAPSE builds a dual-layer
Unified Episodic-Semantic Graph (UESG): episodic nodes = raw interaction logs; semantic
nodes = abstracted concepts derived from episodic clusters. Retrieval propagates activation
energy from the query node through typed edges, returning direct matches AND associated
concepts reachable by graph traversal.

**Hermes two-pass approximation (no dedicated graph engine needed):**
1. `hindsight_recall(query)` — embedding similarity, finds direct matches
2. For each entity name in the results, call `mcp__graphiti__search_memory_facts(entity)`
   — graph traversal, finds relational neighbors
The union of both passes approximates spreading activation.

**Trigger:** use the two-pass when the task is multi-hop (connecting 2+ concepts stored
in different sessions) or when `hindsight_recall` returns plausible but incomplete results.
For single-hop direct-keyword queries, `hindsight_recall` alone is sufficient.

**Write pattern:** tag associated entities explicitly when storing — use
`mcp__graphiti__add_triplet` with typed edges (not just `add_memory`) to populate the
graph topology that traversal depends on. An unlinked episode is invisible to the
spreading-activation pass.

## EDV self-confirmation trap (arXiv:2606.24428, Jun 2026)

Execute-Distill-Verify: the verify step must use an INDEPENDENT check, not the same
reasoning chain that produced the lesson. Without this, distilled lessons inherit the
agent's existing biases ("self-confirmation trap").

For Hermes memory consolidation: when distilling a heuristic from a session, verification
means checking the heuristic against a NEW task or ground-truth outcome — not re-reading
the session and agreeing the heuristic sounds right. The LLM's approval of its own output
is not verification.

Practical check before writing to Hindsight or patching a skill:
"Does this heuristic predict the outcome of a DIFFERENT recent task?" If yes: retain.
If it only explains the current session: it is likely a spurious rationalization.
