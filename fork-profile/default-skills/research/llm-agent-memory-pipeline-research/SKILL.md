---
name: llm-agent-memory-pipeline-research
description: >
  Use when researching agent memory for Hermes pipeline improvements — memory topology,
  ontology, consolidation, forgetting curves, and cross-session transfer. Provides the
  curated implementation roadmap for the l1-extract → l1-promote → Hindsight pipeline.
  NOT for operating the pipeline (use hindsight-stack-operations or agent-memory-consolidation).
  NOT for general arXiv search (use arxiv). NOT for applying findings to other skills (use
  trajectory-research-synthesis-to-skills after consulting arxiv-sweep-findings).
version: 1.1.0
triggers:
  - memory topology research
  - agent memory architecture papers
  - l1 pipeline improvements
  - hierarchical memory agent
  - ontology schema agent memory
  - memory consolidation trigger
  - forgetting pruning mechanism
  - cross-session memory transfer
  - knowledge graph agent memory
  - what memory papers should we implement
  - NOT for applying findings to existing skills (use trajectory-research-synthesis-to-skills)
  - NOT for general arXiv search (use arxiv skill)
  - NOT for operating the memory pipeline (use hindsight-stack-operations or agent-memory-consolidation)
related_skills:
  - arxiv
  - arxiv-sweep-findings
  - agent-memory-consolidation
  - hindsight-stack-operations
  - hermes-memory-surface-selection
---

# LLM Agent Memory Pipeline Research

Curated 2025–2026 research bank: agent memory topology, ontology, consolidation,
forgetting, and cross-session transfer. Each finding includes source URL, quantified
result, and concrete implementation signal for the Hermes pipeline
(l1-extract → memory-facts → l1-promote → staging.md → Hindsight ingest).

Full structured output: `references/memory-topology-research-2026-08.md` (Aug 2026 sweep).
Complementary: `agent-memory-consolidation` skill → `references/agent-memory-systems-2024-2026.md` (Jul 2026 snapshot — re-verify).

## Research Methodology

For sweep methodology, source access matrix, and pitfalls see:
- `academic-literature-review` skill (Phase 0–4 workflow, non-English venue access)
- `academic-literature-review` skill → `references/arxiv-sweep-source-access-aug2026.md`
- `references/source-access-status-sep2026.md` — **authoritative Sep 2026 access status**;
  supersedes individual sweep notes; documents HAL API vs web UI distinction,
  OpenAIRE gap, and unresolvable research gaps (GN-IVO, Zhihu OOD claim)
- `arxiv` skill (arXiv API patterns, fallback chain)

Memory-specific search targets beyond the standard academic-literature-review workflow:
1. **arXiv listing walk** (cs.AI/current, cs.MA/current) — highest yield for very recent papers
2. **GitHub** — trending repos by topic (`agent memory`, `RAG knowledge graph`)
3. **Reddit r/LLMDevs** — practitioner lessons missing from papers
4. **Benchmark blogs** (vectorize.io, etc.) — comparative analyses
5. **J-STAGE / CyberLeninka** — low yield for this domain (Aug 2026 finding)
6. **CNKI** — paywalled; search arXiv with Chinese institution names instead

**CRITICAL — arXiv delta sweep order:** Use `order=-submitted_date` (not `-announced_date_first`) when sweeping past a known ID threshold.

## Key Findings Summary

### 1. Hierarchical Memory Beyond Simple RAG

| Paper | arXiv | Result | l1 signal |
|-------|-------|--------|-----------|
| G-Memory (NeurIPS 2025) | 2506.07398 | +20.89% embodied tasks | Add insight-graph tier via cross-session haiku distillation |
| GAM (Apr 2026) | 2604.12285 | Beats Mem0/A-Mem on LoCoMo | Centroid cosine > 0.3 → flush staging within session |
| Memory in LLM Era v3 (Aug 2026) | 2604.01707 | Composite method beats SOTA | Add routing layer: FTS5/Hindsight/KG by query type |
| Are We Ready? (Jun 2026) | 2606.24775 | Localized maintenance cheapest | Cluster-aware ingest: top-K=3 clusters only |
| Graph Memory Taxonomy (Feb 2026) | 2602.05665 | Experience memory = separate tier | Tag: `fact/correction/outcome/preference/reasoning` |

### LeanMem - 3-Namespace Memory Classification (arXiv:2608.03463)
Result: +15.1pp on LoCoMo/LongMemEval-S at lowest token cost. CODE AVAILABLE.
Namespaces: profile (stable schema-guided, never re-embedded), event (temporally evolving, re-embed on every write), record (verbatim immutable, never re-embedded).
Hermes: Tag staging.md entries with memory_namespace: profile|event|record from l1-extract.py. Only re-embed in l1-promote.py when memory_namespace == event.

### 2. Ontology Schemas

- **POLE+O** (Reddit r/LLMDevs, Paul Iusztin, ~Jun 2026): Person/Object/Location/Event/Org. Extend on collision, not upfront. Dedup thresholds: ≥0.95 auto-merge, 0.85–0.95 review, ≤0.85 new node. LLM-extracted relations expand to ~360 labels; collapse to ~80 canonical before multi-hop works.
- **AriGraph** (arXiv:2407.04363): semantic facts (λ=0.01 decay, ~69d half-life) vs episodic events (λ=0.05, ~14d) — different retention per type.
- **Graphiti bi-temporal** (Zep, production): `valid_from`, `valid_to`, `superseded_by` per fact. Contradiction → `valid_to: now`, never delete.
- **l1-extract.py gap**: emit `{entity_type: POLE+O, relation, confidence, source_session_id, timestamp, extraction_confidence, memory_type}`.

### 3. Consolidation Triggers

| System | Trigger | Threshold | Hermes signal |
|--------|---------|-----------|--------------|
| MemoryOS | Page-full | >70% + topic shift | Already in agent-memory-consolidation |
| GAM (2604.12285) | Semantic centroid shift | cosine > 0.3 | Mini-flush within long sessions |
| MS Research (2605.08538) | Sleep-phase | End of session | l1-promote.py IS this — confirm post-session-close |
| RecMem | Recurrence gate | 2+ sessions | Gate staging→Hindsight promotion |

**Engram maturation** (arXiv:2605.08538): promote staging.md → Hindsight only after `access_count ≥ 2` or confidence threshold met.

**Reconsolidation on retrieval** (arXiv:2605.08538): when query context differs from stored context (cosine distance > 0.4), queue fact for haiku re-eval on next sleep cycle. Add `last_reconsolidated` + `reconsolidation_score` to Hindsight metadata.

### 4. Cross-Session Memory Transfer

- **Agent Lifespan Engineering** (arXiv:2605.26302): formalize l1-promote.py as "boundary controller" — at session start, inject top-N Hindsight facts relevant to current task into working context preamble.
- **Provenance fields** (arXiv:2604.16548, Peking U): `source_session_id` + `extraction_confidence` must be stored at ingest time. Gate: `confidence < 0.5` → do not promote.
- **SuperLocalMemory V3.3** (arXiv:2604.04514): serialize full lifecycle state (`confidence`, `access_count`, `quantization_tier`) alongside text → 100% session-boundary continuity.

### 5. Forgetting / Pruning

| Mechanism | Paper | Metric | Implementation |
|-----------|-------|--------|---------------|
| Dedup gate (cosine > 0.92 → skip + increment `access_count`) | 2605.08538 | **58% store reduction, 97.2% retention** | PRIORITY 1 for l1-promote.py |
| Ebbinghaus: `score = confidence * e^(-days/30) * log(1+access_count)` | 2604.04514 | 6.7× discriminative power | `retention_score`; archive < 0.1, delete < 0.05 |
| Interference-based forgetting | 2605.08538 | Independent of time-decay | NLI check on contradiction → penalize old fact score |
| Three-tier status: Active → Archived → Deleted | 2604.04514 | Graduated utility preservation | `memory_status`; archived = searchable but not default-returned |

### ScrubJay-MEM - Type-Conditioned Perishability Decay (arXiv:2608.04746)
Result: Only retrieval system with positive GenGap (+0.108); +2.66 F1 over Mem0. Ablating type-conditioned decay collapses GenGap 5.7x.

Label table: ephemeral (pi=0.9, tau=2h, keywords: today/immediate/right now/session/temporary), task_specific (pi=0.6, tau=24h, keywords: task/ticket/issue/meeting/project), procedural (pi=0.3, tau=10d, keywords: how to/steps/process/procedure/workflow), factual (pi=0.1, tau=45d, default).

Retrieval score: value_score x exp(-pi x age/tau). Hermes: Add perishability, pi, tau_sec, inserted_at to Hindsight SQLite memories table.

### 6. Error Recovery Patterns (Aug 2026)

**DARR Loop** (AgentDebugX, arXiv:2607.18754, code available):
- **Detect**: classify failure type from trajectory (tool error / logic error / context loss)
- **Attribute**: multi-turn root-cause diagnosis via global trajectory understanding — the step where error *surfaces* ≠ the step that *caused* it
- **Recover**: behavior-scoped guidance from cross-iteration Repair Memory (store scrubbed failure+repair pairs as retrievable memory)
- **Rerun**: guarded re-execution with correction active
- Result: 55.8% → 63.6% accuracy on GAIA (vs 4-6 tasks repaired by self-correction, 13 repaired by DARR)

**Critical Transition Graph** (AgentTether, arXiv:2607.06273):
- Abstracts run into Transition Units → dependency-aware CTG → localizes failure subtrajectory via offline normal-behavior model
- Reduces agent turns AND tokens during recovery

Error-recovery *memory* (store scrubbed failure+repair pairs) stays here. Tool-schema width, orchestration break-even, and debate-critic rules do not — see `hermes-context-hygiene`, `complexity-gated-planning`, `adversarial-review`.

---

## Prioritized l1-pipeline Roadmap

### Priority 1 — High Impact, Low Effort ✅ IMPLEMENTED (2026-08-11)

1. ✅ **Dedup gate in l1-promote.py**: embed fact via OpenAI text-embedding-3-small, query Hindsight top-1; cosine ≥ 0.92 → skip + increment `access_count` on existing memory. Fails-open (8s timeout) if Hindsight unavailable. `--no-dedup` flag for offline testing.
2. ✅ **Temporal reranking stub**: `last_accessed` + `access_count` written to staging metadata on every dedup hit for downstream Hindsight retrieval reranking. Full 0.6·semantic + 0.25·recency + 0.15·freq requires Hindsight query-hook (Priority 3 prerequisite).
3. ✅ **`memory_type` tagging**: l1-extract.py emits `fact|correction|outcome|preference|reasoning`. l1-promote.py parses it for type-specific forgetting curves.
4. ✅ **Temporal validity fields**: `valid_from` written at staging time. `valid_to` + `superseded_by` set by `contradiction_check()` in l1-promote.py when NLI confidence ≥ 0.75.

### Priority 2 — Medium Impact, Medium Effort ✅ IMPLEMENTED (2026-08-11)

5. ✅ **Retention score + lifecycle status**: `compute_retention_score()` uses Ebbinghaus formula (confidence × e^(-days/30) × log(1+access_count)). `lifecycle_status()` returns Active/Archived/Deleted. Written to staging.md header.
6. ✅ **Interference-based forgetting gate**: `contradiction_check()` runs haiku NLI on Hindsight top-3 recall. CONTRADICTS ≥ 0.75 → old memory gets `valid_to`, new fact supersedes. 0.50–0.75 → interference penalty only (access_count-- on old memory). `--no-contradiction` flag for offline runs.
7. ✅ **POLE+O entity typing**: l1-extract.py prompt emits `entities: [{type: Person|Organisation|Location|Event|Object, name}]`. l1-promote.py serialises entity annotations into staging.md lines.
8. ✅ **Reasoning memory category**: `reasoning` is a valid `memory_type` in l1-extract.py.

### Priority 3 — Higher impact (mix of done vs pending)

9. ✅ **Query-type routing layer** — `~/.hermes/scripts/memory-query-router.py`. Classifies queries (semantic/temporal/relational/exact) → returns ordered surface list (Hindsight dense / FTS5 / Graphiti graph). Zero-token heuristic fast path, LLM fallback for ambiguous. 10/10 test cases pass. Source: Memory in LLM Era v3 (arXiv:2604.01707). **Usage:** `route_query(query)` returns `{type, surfaces, confidence, reason}`; surfaces: `hindsight_recall`, `hindsight_fts`, `graphiti_facts`, `graphiti_nodes`.
10. **Semantic-shift mini-consolidation** — within-session flush when centroid distance > 0.3 (GAM arXiv:2604.12285). Requires an online centroid tracker injected into l1-promote.py or the session lifecycle hook.
11. ✅ **Three-tier consolidation** — session → query tier → insight tier via cross-session haiku distillation at ≥3 recurrence (G-Memory arXiv:2506.07398). Live cron: `g-memory-tier3-nightly` (do not invent a second nightly job).
12. ✅ **Graphiti bi-temporal entity layer** — POLE+O entity tags from l1-extract.py are now parsed in `l1-graphiti-write.py` (`parse_staging` + `write_fact`). Entities stripped from fact text and prepended as structured hint (`[entities: Type:Name, ...]`) in Graphiti episode_body, guiding LLM entity extractor. Facts without entities write cleanly with no regression. Wired Aug 2026.
13. **Experience graph cases (EXG, arXiv:2605.17721):** EXG collapses each attempt into a *compact case* `(task, input, output, success bit, execution signatures)` — not a full trajectory dump — then links cases with contain / similar_to / fixed_by edges. Hermes approximation: store those cases as Graphiti episodes (episode-level, not fact-level); at task start retrieve matching cases by task_class. Tag `trajectory_class` on extract output when implementing.
    Principle only until a verified script change — do not patch `l1-extract.py` / `l1-promote.py` from this finding. Operating procedure: `agent-memory-consolidation` (EXG section). Graphiti MCP is HTTP on :8765.

---

## Production Practitioner Lessons (r/LLMDevs, ~Jun 2026)

Source: https://www.reddit.com/r/LLMDevs/comments/1ts3qc3/

1. Own the memory layer — frameworks break at custom ontology constraints + multi-hop traversal.
2. Start with POLE+O, extend on collision (entity-type misclassification = extension signal).
3. Relation labels explode to ~360; collapse to ~80 canonical before multi-hop works.
4. Resolution ≠ deduplication: resolve names (same-type) first, then dedup (threshold-based).
5. Add reasoning memory (per-run trace) as a third tier — "RL at the database layer."
6. Edges as first-class documents enable native graph traversal without adjacency list duplication.
7. Immutable log + materialized graph simultaneously is too RAM-expensive — choose one.

---

## GitHub Ecosystem (Aug 2026)

| Repo | Stars | Relevance |
|------|-------|-----------|
| mem0ai/mem0 | ~48K | Write-time normalization + dedup reference |
| getzep/graphiti | ~24K | Bi-temporal property graph schema |
| letta-ai/letta | ~21K | OS-inspired tiered memory model |
| akitaonrails/ai-memory | ~5.1K | Cross-agent memory handoff via git-backed markdown wiki; cites Hermes as influence; Hermes community plugin at github.com/MrLuciano/ai-memory-hermes-plugin (audit before use) |
| DEEP-PolyU/Awesome-GraphMemory | — | Curated paper list |
| OpenDataBox/MemoryData | — | 11-dataset eval harness |
| bingreeky/GMemory | — | G-Memory NeurIPS 2025 impl |
| qualixar/superlocalmemory | — | Zero-LLM, 7-channel retrieval, bio-inspired |

### ai-memory design patterns worth borrowing (Aug 2026 review)

Source: github.com/akitaonrails/ai-memory (MIT, Rust, actively maintained)

Primary use case: cross-agent memory handoff — quit Claude Code, start Codex or Hermes in same directory, next agent sees typed "where you left off" handoff. For Hermes-only setups, overlap with Hindsight + session_search is high; marginal gain is smaller.

Key patterns applicable to Hermes l1-pipeline:

1. **Git-versioned wiki with supersession chains** — each compiled page is git-committed; time-travel via `restore-page --from <rev>`. Applies to Hermes: staging.md + Hindsight could gain a `superseded_by` pointer per fact rather than in-place overwrite, enabling audit trails without full git overhead.

2. **Authority-aware recall tiers** — retrieval ranking gives a bounded boost to `_rules/`, `decisions/`, `procedures/`, `gotchas/` namespaces over episodic session pages. Durable facts beat temporally close but ephemeral matches. Maps directly to: tag Hindsight entries with namespace tier (rules/decisions/episodic) and apply a tier multiplier in the query-type router.

3. **Decay + salience scoring for episodic pages** — episodic session pages accumulate a salience score; the forget-sweep prunes low-salience pages; pinned pages are exempt. This is the same Ebbinghaus model in Priority 2 above but applied at the page level, not the fact level. ai-memory applies it on auto-generated session wiki pages.

4. **Compile-not-retrieve pattern** (Karpathy-origin) — raw observations are compiled into coherent summary pages at session end via LLM; subsequent agents receive bounded handoffs, not raw log dumps. Already implemented in Hermes l1-promote.py; ai-memory's independent validation confirms the pattern at production scale.

5. **Capture exclusions per repo** — nearest-marker `.ai-memory.toml` can drop matching file-tool events before they reach the spool. Useful pattern for Hermes: a per-repo `.hermes-capture.toml` marker could suppress noisy tool events (e.g. large read_file calls on binary/generated files) from the l1-extract input.

Hermes community plugin status: hooks inject into ai-memory server via MCP; Hermes ignores SessionStart stdout so handoffs must be recovered via `memory_handoff_accept` MCP call, not injection. Review ai-memory-hermes-plugin compatibility matrix and secret handling before wiring in.

## Pitfalls

- High cosine ≠ NLI agreement. "User prefers X" and "user prefers not-X" look similar in embedding space. Always run NLI, not just cosine, for dedup decisions on semantic-content facts.
- Graph vs flat vector: Mem0+graph gave only +2% over Mem0 base on LOCOMO. Improve extraction quality and retrieval routing before switching storage backends.
- J-STAGE and CyberLeninka: very low yield for this domain. Chinese-institution papers are on arXiv concurrently.
- **EIA violation in self-grading (Echo Gap):** Any agent that grades its own extracted memories (e.g. l1-extract.py writing `extraction_confidence`) has correlated bias between extractor and judge — the judge shares the same model and thus the same errors. This causes incorrect memories to get inflated confidence scores and be over-retrieved (compounding errors). Fix: route confidence assessment through an independent evaluator (different framing, or use the contradiction_check NLI score as the independent signal). Source: arXiv:2608.00017.
- **Blind retry without attribution:** Retrying failed agent steps without first detecting which Transition Unit caused the failure adds near-zero improvement. Always Detect→Attribute before Recover→Rerun (DARR pattern). Source: AgentDebugX arXiv:2607.18754, AgentTether arXiv:2607.06273.
- **Memory faithfulness gate:** Before writing extracted facts to long-term memory (graphiti, MEMORY.md), verify the fact is actually supported by the source context. SIRIN (arXiv:2608.00033) is span-level unsupported detection — prevents confabulated facts from entering the store. Skill-file secret-embedding and content-hash skill dedup belong in `hermes-agent-skill-authoring`, not this pipeline skill.

## ERSkill — Self-Evolving Skill-Guided Memory Retrieval (arXiv:2608.12720, Sweep 15) ★ HIGH

Prerequisite-skill graphs and YAML `requires:` / preload belong in `hermes-agent-skill-authoring` (SkillTrace, arXiv:2608.02356), not this pipeline skill.

Retrieval mechanisms governing long-term memory are rarely treated as evolvable components.
ERSkill compiles interaction histories into a structured store and represents **retrieval
behaviors as executable skills** composed of fundamental primitives.

**Core architecture:**

1. **Experience Trie** — organizes past retrieval experiences by strategy path:
   - Each node = a retrieval primitive (e.g., `dense_search`, `keyword_filter`, `temporal_sort`)
   - Each path = a successful retrieval strategy for a query type
   - New paths are added from successful retrievals; failed paths are pruned

2. **Double-Frontier evolution** — maintains two active fronts:
   - **Exploration frontier**: novel strategy compositions not yet validated
   - **Exploitation frontier**: proven high-recall strategies for known query types
   - Router switches between frontiers based on query novelty signal

3. **Trained router** — maps query features → frontier → skill → retrieval action

**Empirical results:** +31% over non-evolving baselines on memory benchmarks. Co-evolution of
skills + router is the source of gains — neither skills alone nor router alone achieves them.

**Why this matters for Hermes:** Current `hindsight_recall` + Graphiti retrieval is static —
the same strategy is used for all query types. ERSkill's principle is that retrieval strategy
should adapt per query type, not per memory store.

**Hermes approximation (no retraining required):** do **not** maintain a second inline router. Live path is `~/.hermes/scripts/memory-query-router.py` (Priority 3 #9: semantic/temporal/relational/exact → ordered surfaces). ERSkill extras not in that script yet: experience-trie logging and double-frontier promotion (below).

**Experience trie log entry** — add to `l1-extract.py` output for retrieval sessions:

```
retrieval_log:
  query_type: temporal | relational | procedural | semantic
  strategy_used: <strategy name>
  recall_success: true/false
  trie_path: [dense_search, temporal_sort, entity_filter]
```

**Double-frontier in practice:** after 20+ retrieval logs, cluster by `query_type` and
promote the top-2 strategies per type to "exploitation frontier" (use by default). Keep
3 alternative strategies in "exploration frontier" (use when the top-2 fail 2+ times on
a query type). <!-- why: prevents strategy overfitting to one retrieval mechanism -->

## GPM — Governed Persistent Memory: Fail-Closed Release (arXiv:2608.12476, Sweep 15)

See mnemosyne-atp-safety skill for full implementation. Key memory pipeline implications:

- **Non-revival** must be enforced in `l1-promote.py`: before promoting any fact from
  staging.md, check the retraction ledger (`~/.hermes/memory-facts/retractions.log`).
  A fact that was previously retracted and now re-extracted must NOT be re-promoted
  without human review. <!-- why: GPM proves naive re-extraction re-admits retracted facts in 50% of violation cases -->
- **Conflict isolation (pending — not live policy):** GPM would tag BOTH facts `memory_status: conflict_isolated` until a reconciliation pass. **Live code is Priority 2:** CONTRADICTS ≥ 0.75 → old memory gets `valid_to`, new fact supersedes. Do not document isolation as current behavior.
- **Source binding**: the `source_session_id` written at ingest time is immutable.
  Never update it via l1-promote.py, even if a later session provides a "better" source.

## Delivery, Not Storage — Memory Must Be a Harness Property (arXiv:2607.20972) ★ HIGH <!-- rationale: 98% of conversation-only facts vanish at first compaction; validates existing pattern with hard numbers -->

Empirical study of memory loss at compaction boundaries. Key findings:
- Facts held ONLY in conversation are absent 106/108 times after the first compaction
- 39% of intra-session re-reads are re-buying content that existed pre-compaction
- Memory write must be a harness responsibility, not agent initiative

**Hermes validation:** The existing l1-extract → Hindsight pipeline already implements this.
The implication is NEVER rely on context persistence for facts that must survive sessions.
Concretely: any fact derived from tool output that the agent may need in a future session
must be written to Hindsight or Graphiti BEFORE the session ends — not just held in context.

**New metric to track in the l1-pipeline:** track "re-buy rate" — how often does the agent
ask hindsight_recall for a fact that was already retrieved earlier in the same session?
High re-buy rate (>20%) signals that facts are not surviving compaction and are being
re-retrieved at cost. Target: <10% re-buy rate per session.

Context-window offload/eviction/summarization cascade belongs in `hermes-context-hygiene`, not this pipeline skill.

## MasDrift — Authorization Drift in Hierarchical Multi-Agent Systems (arXiv:2608.07556) ★ HIGH <!-- rationale: 2.7–19.8% unauthorized actions in hierarchical vs 0.6–0.8% in peer networks; depth amplifies -->

Centralized hierarchical MAS architectures experience authorization drift: delegated
permissions escalate unpredictably through the delegation chain. Deeper hierarchies
show worse drift (depth amplifies authorization scope).

**Empirical results:** Hierarchical: 2.7–19.8% unauthorized action rate. Peer: 0.6–0.8%.
Re-anchoring (explicit permission reset at each delegation level) beats chain propagation.
Operational `delegate_task` scoping lives in `hermes-cron-and-agents` / `trajectory-risk-guardrail` — do not fork a second permission religion here.

## RippleMem: Associative Recollection for Long-Term Agent Memory (arXiv:2608.13334, Aug 13 2026) ★ HIGH

Standard flat retrieval returns isolated memory records; relevant evidence is spread across
many interactions. RippleMem uses an **event-centric memory graph** with adaptive associative
recollection:

1. Query retrieves **anchor memories** via hybrid cues (semantic + keyword)
2. A **ripple expansion** walks outward along semantic and structural edges, recovering
   supporting evidence the anchor alone would miss
3. Graph construction cost is ~30x lower than prior graph-memory systems

Results: +3.95–11.87% LLM-as-Judge accuracy on LoCoMo and LongMemEval-S.

**Hermes application:**
- `session_search` + `hindsight_recall` approximate the anchor-retrieval phase
- Graphiti provides the graph traversal layer but doesn't currently do ripple expansion
- The missing piece: after `hindsight_recall` returns anchors, issue follow-up Graphiti
  `search_memory_facts` queries using the anchor entity names as seeds — this manually
  approximates one ripple hop at zero infrastructure cost
- Full RippleMem: implement as a wrapper around `hindsight_recall` that fans out to
  `mcp__graphiti__search_memory_facts` with each returned entity as a secondary query

## AgentMemBench Benchmark Verdict (arXiv:2608.00009, Aug 2026) ★ HIGH

Most comprehensive head-to-head memory-strategy benchmark to date. 5 strategies:
ICW (in-context windowing), EKV (external key-value/dense retrieval), GEM (graph-episodic),
CBS (compression-based summarization), WAM (web-augmented).

**Results:**
- **EKV dominates on every quality axis**: Recall@5=0.792, MRR=0.677
- At long horizons (LoCoMo benchmark): only EKV scales — ICW/WAM/GEM/CBS all collapse
  to Recall@5 ≤ 0.005 while EKV reaches 0.573
- **Retriever choice dominates memory construction**: changing retriever alone shifts accuracy
  58.1% → 75.5% on fixed LightMem store (corroborated by Reproducing LightMem, arXiv:2607.29104)
- CBS (summarization) is runner-up for short/medium horizons; GEM underperforms despite intuitive appeal
- EKV cost: ~5,100 tokens vs ~300 for ICW/WAM — cost-quality tradeoff must be explicit

**Hermes memory architecture implication:**

| Horizon | Recommended strategy | Hermes tool |
|---|---|---|
| Short (< 10 turns) | ICW (in-context windowing) | In-context + session_search |
| Medium (10–50 turns) | CBS or EKV | Hindsight (summarization) |
| Long (50+ turns, multi-session) | **EKV only** | Hindsight dense retrieval; supplement Graphiti with vector store |

Key finding: **Graphiti graph memory (GEM class) underperforms at true long horizons**.
Do not rely on Graphiti alone for cross-session recall on long-running agent tasks — pair
it with Hindsight's dense vector retrieval path. Invest in retriever quality before
memory construction complexity (LightMem reproduction result).

**MRAgent: Cue-Tag-Content Graph Active Reconstruction (arXiv:2606.06036, ICML 2026)**

Augments graph memory with active reconstruction: reasoning is integrated INTO the retrieval
path, not applied after retrieval.

Memory structure: **Cue-Tag-Content graph**
- **Cue nodes**: fine-grained retrieval handles (entity aliases, partial facts, trigger phrases)
- **Tag edges**: semantic bridges connecting cues to related cues and to content
- **Content nodes**: the actual stored facts/episodes

Iterative path exploration: agent explores retrieval paths, prunes based on accumulated
evidence, avoids combinatorial explosion. Results: +23% over baselines on LoCoMo + LongMemEval
with reduced token and runtime cost.

**Hermes implementation sketch (on top of Graphiti):**
- Add explicit "cue" nodes at ingest (aliases, trigger phrases, partial-fact handles) linked
  to main entity/episode nodes via "CUE_FOR" edges
- At retrieval: start from the cue matching the query, traverse tags to reach content,
  prune paths that don't accumulate supporting evidence within N hops
- Handles partial/approximate recall better than direct entity-name search

## Reference files

- `references/agent-community-engineering-aug12-2026.md` — Agent Engineering Community Findings — Aug 12 2026
- `references/agent-engineering-aug12-2026-community-sweep.md` — Agent Engineering — Community Sweep: Aug 12 2026
- `references/agent-engineering-jul-aug-2026.md` — Agent Engineering Findings — Jul–Aug 2026
- `references/agent-improvement-aug12-2026-sweep6.md` — Agent Improvement Research — Aug 12, 2026 (Sweep 6)
- `references/agent-improvement-aug12-2026-sweep7.md` — Agent Improvement Research — Aug 12 2026 Sweep 7
- `references/agent-improvement-aug12-2026-sweep9.md` — Agent Runtime Research — Aug 12 2026 Sweep 9 (arXiv ≥ 2608.09931)
- `references/agent-memory-skill-aug11-2026-sweep.md` — Agent Memory, KG & Skill Architecture — Aug 11 2026 Delta Sweep
- `references/anthropic-api-agent-engineering-aug2026.md` — Anthropic API + Agent Engineering — Aug 12 2026 Research Sweep
- `references/audit-corrections-aug2026.md` — Audit Corrections — Aug 2026
- `references/blast-direction-risk-taxonomy.md` — Blast-Direction Risk Taxonomy
- `references/community-sweep-aug12-2026.md` — Community Sweep — Aug 12 2026 (Sweep 9)
- `references/community-sweep-aug12-2026b.md` — Community Sweep — Aug 12 2026 (Multilingual Sources)
- `references/memory-topology-aug2026-sweep.md` — Memory Topology & Evaluation — Post-Aug 8 2026 Sweep
- `references/multilingual-agent-research-aug12-2026.md` — Multilingual AI Agent Research — Aug 12, 2026 Delta Sweep
- `references/multilingual-agent-research-aug13-2026.md` — Multilingual + Novel Agent Research — Aug 13 2026 Sweep
- `references/practitioner-community-sweep-aug13-2026.md` — Practitioner Community Sweep — Aug 13 2026
- `references/research-links-2026-08-11.md` — Research Links Sweep — Aug 10–11 2026
- `references/rumba-memory-eval-taxonomy-aug2026.md` — RUMBA: Russian User Memory Benchmark — Evaluation Taxonomy
- `references/skill-architecture-aug2026-sweep.md` — Skill Architecture Research — Post-Aug 8 2026 Sweep
- `references/zero-mem-note.md` — Zero-Mem Quick Note (arXiv:2607.29377)
- `references/source-access-status-sep2026.md` — Authoritative source access matrix (Sep 2026)
- `references/memory-topology-research-2026-08.md` — condensed knowledge bank (17 findings)
- `references/agent-runtime-aug2026-sweep.md` — Aug 9–11 2026 delta sweep
- `references/agent-runtime-aug2026-sweep2.md` — Aug 11 Sweep 4
- `references/agent-improvement-aug12-2026-sweep.md` — Aug 12 Sweep 5
- `references/agent-improvement-aug12-2026-sweep8.md` — Aug 12 Sweep 8 (EIA/DARR/SIRIN)
- `references/agent-improvement-aug12-2026-sweep10.md` — Aug 12 Sweep 10 (GitSkills / arXiv order)
- `references/agent-memory-sweep-aug14-2026.md` — Agent Memory Sweep — Aug 14 2026 (Sweep 13)
- `references/agent-memory-sweep-aug14-2026-sweep14.md` — Sweep 14 paper bank (already applied: LycheeMemory V2, skill-induced failures, SafeEvolve, Delivery-not-storage, MasDrift); do not re-apply
