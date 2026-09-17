---
name: graphiti-mcp-setup
related_skills:
  - hermes-memory-surface-selection
  - agent-memory-consolidation
  - hermes-memory-capture-and-bridge
description: >
  Use when setting up and operate Graphiti knowledge graph as a Hermes MCP sidecar (FalkorDB + Anthropic LLM + OpenAI text-embedding-3-small).
triggers:
  - graphiti
  - knowledge graph
  - entity extraction
  - relationship graph
  - falkordb
---

# Graphiti MCP Setup

Graphiti adds typed entity/relationship extraction to the Hermes memory stack.
It complements Hindsight (similarity search) and MemPalace (structured notes) with a
persistent knowledge graph queryable by entity name and relationship type.

## Stack

- **Backend DB**: FalkorDB (rootless podman, port 6379 Redis + port 3000 browser UI)
- **LLM**: Anthropic `claude-haiku-4-5` (entity extraction, cheap)
- **Embedder**: OpenAI `text-embedding-3-small` via `HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY` (1536d)
- **Transport**: HTTP streamable MCP at `http://127.0.0.1:8765/mcp/`
- **Hermes MCP name**: `graphiti`

## Key Paths

- Repo: `~/graphiti/` (cloned depth=1 from https://github.com/getzep/graphiti)
- Config: `~/graphiti/mcp_server/config/config-hermes.yaml`
- Env: `~/graphiti/mcp_server/.env`
- Systemd unit: `~/.config/systemd/user/graphiti-mcp.service`
- Hermes config entry: `~/.hermes/config.yaml` under `mcp_servers.graphiti`

## Starting / Restarting

```bash
# FalkorDB (rootless podman, survives reboots via --restart unless-stopped)
podman start falkordb         # if stopped
podman ps | grep falkordb     # verify

# Graphiti MCP server
systemctl --user start graphiti-mcp.service
systemctl --user status graphiti-mcp.service --no-pager
journalctl --user -u graphiti-mcp.service -n 30 --no-pager
```

## Enabling on boot + dependencies

```bash
# FalkorDB: --restart unless-stopped handles reboots via podman-restart.service
systemctl --user enable --now podman-restart.service
systemctl --user enable graphiti-mcp.service

# hermes-gateway.service must wait for graphiti — already patched:
# After=network-online.target graphiti-mcp.service
# Wants=network-online.target graphiti-mcp.service
# Verify: grep -i graphiti ~/.config/systemd/user/hermes-gateway.service

systemctl --user is-enabled podman-restart.service graphiti-mcp.service  # both: enabled
```

**Applied patches (one-time, already done):**
- `graphiti-mcp.service [Unit]`: `After=network.target podman-restart.service` + `Wants=podman-restart.service` — prevents crash loop when FalkorDB hasn't started yet
- `hermes-gateway.service [Unit]`: added `graphiti-mcp.service` to After/Wants — gateway no longer exhausts MCP retries before Graphiti is ready

## Diagnosing a crash-restart loop

```bash
systemctl --user status graphiti-mcp.service
# "activating (auto-restart)" = FalkorDB not up

journalctl --user -u graphiti-mcp.service -n 20 --no-pager
# Look for: "Database Connection Error: FalkorDB is not running"

podman ps -a --filter name=falkordb   # check container state
podman start falkordb                  # restart if exited
systemctl --user restart graphiti-mcp.service
```

## Bug fix applied (must reapply after uv sync)

`graphiti_core` passes `temperature=None` to Anthropic API which rejects it.
Patch applied to both venv and source:

File: `~/graphiti/mcp_server/.venv/lib/python3.10/site-packages/graphiti_core/llm_client/anthropic_client.py`
File: `~/graphiti/graphiti_core/llm_client/anthropic_client.py`

Change (around line 285, inside `_generate` method):
```python
# BEFORE
result = await self.client.messages.create(
    ...
    temperature=self.temperature,
    ...
)

# AFTER
extra_kwargs: dict = {}
if self.temperature is not None:
    extra_kwargs['temperature'] = float(self.temperature)
result = await self.client.messages.create(
    ...
    **extra_kwargs,
)
```

After any `uv sync`, reapply the venv patch.

## MCP Tools Available

- `add_memory` — ingest episode (text, name, group_id); extraction is async (~10-30s)
- `search_nodes` — find entities by semantic query + group_ids
- `search_memory_facts` — find typed relationships (edges) by query
- `get_episodes` — list raw episodes for a group
- `delete_episode` / `delete_entity_node` — remove data

## When to Use Graphiti vs Other Memory

| Need | Use |
|------|-----|
| Who/what/how are entities related? | Graphiti `search_memory_facts` |
| Fuzzy semantic similarity | Hindsight recall |
| Structured notes / rooms | MemPalace search |
| Broad cross-session recall | session_search |

## Reasoning memory (group: hermes-reasoning)
Store per-task traces for significant tasks (5+ steps, failures, non-obvious solutions).

**Write episodes in verbose paragraph/prose form, NOT AAAK-compressed shorthand.**
Graphiti's LLM extractor needs full sentences to pull entity nodes and typed edges.
Compressed notation like "SESSION:2026-04-04|built.X|ALC.req:Y" produces no usable entities.

Good episode structure (plain prose, 5-10 sentences):
- What the goal was and why the standard approach was not enough
- What strategy was chosen and which tools were involved
- What the key decision points were (with their rationale)
- What the outcome was (success/failure/partial)
- What the lesson is for future sessions

Example:
"Patched the Graphiti Anthropic client to skip the temperature kwarg when it is None
because the Anthropic API rejects explicit None values. The patch was applied to both
the venv copy and the source copy because uv sync overwrites the venv. The lesson is
that after any uv sync on ~/graphiti, the venv patch must be reapplied manually from
the source file at ~/graphiti/graphiti_core/llm_client/anthropic_client.py."

Query with: mcp_graphiti_search_memory_facts(query="...", group_ids="hermes-reasoning")
Do NOT add traces for trivial one-off tasks — signal/noise matters.

## Pre-normalization before add_memory (improves extraction quality)

Graphiti's LLM extractor sees raw episode text. Noisy or ambiguous input produces noisy entities.
Before calling add_memory for anything important, normalize the text:

1. Resolve pronouns and implicit references: "it" → the actual tool/service name
2. Spell out abbreviations on first use: "the MCP" → "the Graphiti MCP server"
3. Flatten informal phrasing: "yeah the port thing again" → "port 8765 was held by a stale process"
4. If the episode covers multiple unrelated facts, split into separate add_memory calls

This is especially important for relationship-heavy content (config changes, service interactions,
decisions with multiple entities). Short factual episodes with clear subject/predicate/object
can be ingested as-is.

Downstream benefit: cleaner entity deduplication (exact name matching fires before semantic
threshold checks), fewer false merges, better BFS traversal results at query time.

## Group ID taxonomy

Every add_memory call requires a group_id. Use these consistently so searches scope correctly:

| group_id | What goes here |
|---|---|
| `hermes` | Default — Hermes stack facts, tool configs, service relationships |
| `hermes-reasoning` | Per-task traces (verbose prose, 5+ step tasks, non-obvious solutions) |
| `hermes-projects` | Project-specific entity relationships (use project name as suffix: `hermes-projects-myproject`) |
| `hermes-agent-<task-id>` | Ephemeral per-subagent namespace for parallel delegate_task fan-outs; clean up after run |

Do NOT invent new group_ids without adding them here. Inconsistent group_ids silently split
the graph — search_memory_facts queries miss facts stored under different group names.
Ephemeral `hermes-agent-*` group_ids are the exception: they are intentionally scoped to
a single parallel run and can be cleared via `clear_graph(group_ids="hermes-agent-...")` after.

## Entity & Edge Type Schema (Hermes profile — config-hermes.yaml)

Entity types active in config (ordered by priority at extraction time):
- Preference, Procedure, Task — high-signal, extract at low threshold
- Project, Tool, Artifact, Skill, Requirement — core structural types
- Person, Organization, Event, Location, Document — general; prefer specific types above

Deprecated entity types (kept in registry for backward compat, NOT in config entity_types list):
- Object — deprecated 2026-07-22; use Artifact (digital) or Tool (software) instead
- Topic — deprecated 2026-07-22; use Task (actionable), Project (initiative), or Document (reference)

Edge types active in config:
Uses, Configures, BelongsTo, Produces, Supersedes, Requires (with reason field), WorksFor, DerivedFrom (provenance/lineage, added 2026-07-22)

Edge types in Python registry but NOT in config (fallback/catch-all types):
RelatesTo, MentionedIn, LocatedAt, ParticipatesIn, Owns

## Hindsight re-embedding (OpenAI 1536d migration)

If Hindsight embeddings need to be migrated from 384d (local) to 1536d (OpenAI):
1. Add embedding keys to ~/.hindsight/profiles/hermes.env (the plugin may overwrite this on restart):
   HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
   HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY=<full sk-proj-... key>
   HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=text-embedding-3-small
   HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS=1536
2. NULL out all embeddings: UPDATE memory_units SET embedding = NULL;
3. Kill daemon + rm ~/.hindsight/profiles/hermes.lock, trigger restart via hindsight_recall
4. Run ~/.hermes/scripts/hindsight-reembed.py --batch-size 200 to backfill

Root cause: _build_embedded_profile_env in hindsight/__init__.py only forwards LLM keys.
Fix: patch applied to forward HINDSIGHT_API_EMBEDDINGS_* keys from config.json (active after Hermes restart).
Config keys in ~/.hermes/hindsight/config.json: HINDSIGHT_API_EMBEDDINGS_PROVIDER, _OPENAI_API_KEY, _OPENAI_MODEL, _OPENAI_DIMENSIONS.

Pydantic models live in:
- ~/graphiti/mcp_server/src/models/entity_types.py (ENTITY_TYPES dict + .update() at bottom)
- ~/graphiti/mcp_server/src/models/edge_types.py (EDGE_TYPES dict + .update() at bottom; DerivedFrom class defined before the .update() block)

Config YAML keys: entity_types[], edge_types[], edge_type_map[] under graphiti:

## Boot dependency: patch hermes-gateway.service to wait for Graphiti

**Already applied.** hermes-gateway.service now has:
```ini
After=network-online.target graphiti-mcp.service
Wants=graphiti-mcp.service
```
If you recreate hermes-gateway.service, reapply this. Verify: `grep -i graphiti ~/.config/systemd/user/hermes-gateway.service`

## Port conflict: news-dashboard

news-dashboard.service and graphiti-mcp.service both default to 8765.
Resolved by moving news-dashboard to 8766 (`Environment=PORT=8766` in its service file).
Graphiti owns 8765. Do not revert this — if news-dashboard.service is recreated, verify
its PORT env var is not 8765.

## L1 Dual-Write Pipeline (Hindsight + Graphiti)

The `l1-hindsight-promote` cron job (every 4h) now writes facts to BOTH Hindsight and Graphiti:
- Hindsight: flat vector store for semantic similarity search
- Graphiti: typed entity/relationship graph for structured reasoning

**Script**: `~/.hermes/scripts/l1-graphiti-write.py`
- Reads staging.md, initializes MCP session (initialize → session-id), writes each fact as a Graphiti episode
- Must be called BEFORE staging.md is truncated by the cron job
- MCP transport: stateful HTTP (`initialize` → get `mcp-session-id` → `tools/call` with header)
- Note: Graphiti URL is `/mcp` NOT `/mcp/` (trailing slash causes 307 redirect)
- Note: `Accept: application/json, text/event-stream` required (both must be present)

**To test**:
```bash
echo "- [2026-01-01T00:00Z] [score=3] [type=fact] Test fact for Graphiti." > /tmp/test-staging.md
python3 ~/.hermes/scripts/l1-graphiti-write.py /tmp/test-staging.md
rm /tmp/test-staging.md
# Then verify: mcp__graphiti__search_nodes(query="Test fact", group_ids=["hermes"])
```

**Cron job toolsets** (as of Aug 2026): `["file", "terminal", "memory"]`
The `l1-graphiti-write.py` is called via `terminal` — no need for graphiti MCP toolset in cron.

## SYNAPSE: Triple Hybrid Retrieval with spreading activation (arXiv 2601.02744)

Standard vector similarity retrieval has a "Contextual Tunneling" problem: it returns
results similar to the query embedding but misses results connected through intermediate
hops. SYNAPSE (University of Georgia, Jan 2026) addresses this with a three-component
fusion strategy grounded in cognitive neuroscience.

### Three retrieval signals to fuse:

1. **Geometric embeddings** — standard vector similarity (cosine/dot product). Fast.
   What Graphiti/Hindsight do today.

2. **Spreading activation** — graph traversal that propagates activation from the query
   node outward through entity-relationship edges, decaying with hop distance. Surfaces
   facts connected to the query node's neighborhood, not just the node itself.
   Implementation pattern for Graphiti:
   ```python
   def spreading_activation(start_uuid, graph, decay=0.5, max_hops=3):
       activated = {start_uuid: 1.0}
       frontier = [(start_uuid, 1.0)]
       for hop in range(max_hops):
           next_frontier = []
           for node_id, strength in frontier:
               neighbors = graph.get_neighbors(node_id)  # Graphiti edge traversal
               for nbr in neighbors:
                   new_strength = strength * decay
                   if nbr not in activated or activated[nbr] < new_strength:
                       activated[nbr] = new_strength
                       next_frontier.append((nbr, new_strength))
           frontier = next_frontier
       return activated  # {node_uuid: activation_strength}
   ```

3. **Lateral inhibition** — suppress nodes that are closely similar to already-selected
   results (diversity enforcement). Equivalent to MMR but applied at graph traversal time,
   not post-retrieval. When a node is added to results, reduce the activation of its
   nearest neighbors by a suppression factor (0.3-0.5).

4. **Temporal decay** — reduce activation weight of older episodes. Apply exponential
   decay to node activation based on `(now - valid_at).days`:
   ```python
   temporal_weight = math.exp(-lambda_ * days_old)  # lambda_=0.01 for 1% decay/day
   ```

### Fusion formula (Triple Hybrid):
```
score(node) = alpha * cosine_sim + beta * activation_strength * temporal_weight
```
Typical: alpha=0.6, beta=0.4. Tune on your query distribution.

### LoCoMo benchmark results:
- Multi-hop temporal reasoning: SYNAPSE significantly outperforms RAG baselines
- Handles "Contextual Tunneling" (query matches wrong time period) via temporal decay
- Code available pending acceptance (check arxiv.org/abs/2601.02744 for updates)

### Practical Hermes application:
When building Graphiti queries for multi-hop reasoning tasks (e.g. "what did we decide
about X in relation to Y"), use `center_node_uuid` in `search_memory_facts` to seed a
spreading activation fan-out. Chain 2-3 search calls expanding outward from the initial
match rather than a single broad search.

## Two-stage hybrid retrieval + neural reranking (arXiv 2604.01733)

Financial QA benchmark (23,088 queries, 7,318 mixed text+table documents) shows:
- **BM25 alone** outperforms dense retrieval on financial documents (domain-specific
  terminology is sparse, not semantic)
- **Two-stage pipeline** (hybrid BM25+dense → cross-encoder reranking) achieves
  Recall@5 = 0.816, MRR@3 = 0.605 — outperforms all single-stage methods by large margin
- Query expansion (HyDE, multi-query) adds limited value for precise numerical queries
- Contextual retrieval yields consistent gains across document types

For Hermes corpus work (Religion DB, legal docs, financial docs):
- Stage 1: hybrid search (BM25 on Whoosh/ElasticSearch + Hindsight vector)
- Stage 2: cross-encoder reranker (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) to
  rescore top-20 candidates → return top-5
- Fusion: Reciprocal Rank Fusion (RRF) score = Σ 1/(k + rank_i) for each retrieval signal

BM25 note: current Hindsight + Graphiti stack is vector-only. Consider adding session_search
(FTS5) results as the "BM25 leg" of hybrid retrieval for agent memory queries.

## GraphFlow: GFlowNet-based KG retrieval diversity (arXiv 2510.16582, NeurIPS 2025 Spotlight)

Standard MMR is greedy — it deduplicates post-hoc. GraphFlow (Junchi Yu, Yujie Liu,
Jindong Gu/Oxford et al.) uses a GFlowNet transition-based flow estimator to learn a
retrieval *policy* that samples proportionally to reward across diverse KG trajectories.

Key insight: MMR greedily removes near-duplicates after ranking. GFlowNet explores
multiple high-reward paths during retrieval — diversity is baked in, not grafted on.

Results: +10% hit rate and recall vs. GPT-4o on STaRK benchmark (Amazon/MAG/Prime).
Strong generalization to unseen KGs without retraining.

Practical approximation for Hermes without training a GFlowNet:
```python
def graphflow_approx(query: str, n: int = 10) -> list:
    """Approximate GFlowNet exploration via stochastic KG traversal."""
    import random
    # 1. Get top-k seed facts by standard search
    seeds = search_memory_facts(query, max_facts=n*3)
    # 2. For each seed, sample a 2-hop neighbor (random walk step)
    expanded = list(seeds)
    for seed in seeds[:n]:
        neighbors = search_memory_facts(
            seed['fact'], max_facts=3,
            center_node_uuid=seed.get('source_node_uuid')
        )
        # Probabilistic inclusion proportional to score * novelty
        for nb in neighbors:
            if nb not in expanded and random.random() < nb.get('score', 0.5):
                expanded.append(nb)
    # 3. Apply diversity filter: cluster by source entity, pick one per cluster
    seen_entities = set()
    diverse = []
    for fact in expanded:
        key = fact.get('source_node_uuid', fact['fact'][:30])
        if key not in seen_entities:
            seen_entities.add(key)
            diverse.append(fact)
    return diverse[:n]
```

## KG²RAG: KG-guided chunk organization for retrieval diversity (arXiv 2502.06864, NJU/NAACL 2025)

Nanjing University (Xiangrong Zhu, Yuexiang Xie, Yi Liu, Yaliang Li, Wei Hu).
GitHub: https://github.com/nju-websoft/KG2RAG

Two-stage pattern:
1. KG-guided chunk expansion: use fact-level KG relationships to expand a seed query
   to related entities (2-hop neighborhood in Graphiti)
2. KG-based chunk organization: group retrieved facts by KG neighborhood cluster,
   enforce minimum inter-cluster diversity — prevents returning 5 facts about the
   same entity

Implementation for Graphiti:
```python
def kg2rag_retrieve(query: str, n: int = 10) -> list:
    # Seed retrieval
    seeds = search_memory_facts(query, max_facts=n)
    # Expand via KG neighbors (2-hop)
    expanded = list(seeds)
    for seed in seeds[:5]:
        nbrs = search_memory_facts(
            seed['fact'], max_facts=4,
            center_node_uuid=seed.get('target_node_uuid')
        )
        expanded.extend(nbrs)
    # Cluster by entity pair, enforce diversity (1 fact per source entity)
    clusters = {}
    for fact in expanded:
        src = fact.get('source_node_uuid', 'unknown')
        if src not in clusters:
            clusters[src] = fact  # keep highest-scored per entity
    return list(clusters.values())[:n]
```

Byte-exact dedup as pre-filter (arXiv 2605.09611):
Before any of the above, hash all retrieved fact strings — deduplicate exact/near-exact
duplicates cheaply before semantic diversity ranking:
```python
import hashlib
def dedup_facts(facts: list) -> list:
    seen = set()
    out = []
    for f in facts:
        h = hashlib.md5(f['fact'].strip().lower().encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(f)
    return out
```

## MEMTIER: 5-signal weighted retrieval (arXiv 2605.03675, Ben-Gurion University)

MEMTIER (Bronislav Sidik, Lior Rokach — Ben-Gurion University, Israel):
- Tripartite architecture: episodic JSONL + 5-signal weighted retrieval + async
  consolidation daemon promoting episodic → semantic tier
- +33 pp improvement over full-context baseline (5% → 38% accuracy, LongMemEval-S)
- With DeepSeek pre-population: 0.686–0.714 vs RAG BM25 GPT-4o baseline 0.560
- Runs on consumer 6GB GPU laptop

5-signal weighted retrieval for Graphiti search_memory_facts wrapper:
```python
import time, math

def memtier_rerank(facts: list, query_context: dict) -> list:
    """Re-rank Graphiti results using 5-signal MEMTIER scoring."""
    now = time.time()
    for f in facts:
        # 1. Recency: exponential decay from creation time
        age_days = (now - f.get('created_at_ts', now)) / 86400
        recency = math.exp(-age_days / 30)  # 30-day half-life
        # 2. Relevance: from Graphiti's base score
        relevance = f.get('score', 0.5)
        # 3. Access frequency: how often was this fact retrieved
        access_count = f.get('access_count', 1)
        access = min(math.log1p(access_count) / 5, 1.0)
        # 4. Tier level: semantic > episodic > archival
        tier_map = {'semantic': 1.0, 'episodic': 0.7, 'archival': 0.4}
        tier = tier_map.get(f.get('tier', 'episodic'), 0.7)
        # 5. Confidence: how well-established is the fact
        confidence = f.get('confidence', 0.8)
        # Weighted composite (weights tunable)
        f['memtier_score'] = (
            recency * 0.25 + relevance * 0.30 + access * 0.15 +
            tier * 0.15 + confidence * 0.15
        )
    return sorted(facts, key=lambda x: x['memtier_score'], reverse=True)
```

## vstash: adaptive IDF-weighted RRF + self-supervised embedding refinement (arXiv 2604.15484)

Single-SQLite stack: sqlite-vec (ANN) + FTS5 + adaptive per-query IDF-weighted RRF.
Key result: +21.4% NDCG@10 vs fixed RRF weights (ArguAna). 20.9ms median at 50K chunks.

Critical NEGATIVE result from vstash: post-RRF reranking (frequency+decay,
history-augmented recall, cross-encoder) ALL failed to improve NDCG. Do NOT add
reranking layers on top of RRF — more layers hurt, not help.

Self-supervised embedding refinement: uses disagreement between vec-heavy and FTS-heavy
rankings as training signal (no human labels). Fine-tunes BGE-small with
MultipleNegativesRankingLoss on 76K disagreement triples.

3-source adaptive RRF for Hermes (FTS5 + ChromaDB + Graphiti):
```python
def adaptive_rrf(query: str, k: int = 60, n: int = 10) -> list:
    """Adaptive IDF-weighted RRF over 3 Hermes memory sources."""
    # Estimate query "specificity" — rare terms → weight FTS5 higher
    query_terms = query.lower().split()
    # Simple IDF proxy: short queries with specific nouns → BM25-heavy
    idf_weight = min(0.8, 0.3 + len([t for t in query_terms if len(t) > 5]) * 0.1)
    vec_weight = 1.0 - idf_weight

    fts_results = session_search(query=query, limit=n*2)
    vec_results = hindsight_recall(query=query)  # ChromaDB
    kg_results = search_memory_facts(query=query, max_facts=n)

    # RRF score: 1/(k + rank) summed across sources with weights
    scores = {}
    for rank, item in enumerate(fts_results):
        key = item.get('id', str(rank))
        scores[key] = scores.get(key, 0) + idf_weight * (1/(k + rank + 1))
    for rank, item in enumerate(vec_results):
        key = item.get('id', str(rank))
        scores[key] = scores.get(key, 0) + vec_weight * (1/(k + rank + 1))
    for rank, item in enumerate(kg_results):
        key = item.get('uuid', str(rank))
        scores[key] = scores.get(key, 0) + 0.3 * (1/(k + rank + 1))

    all_items = {**{i.get('id'): i for i in fts_results},
                 **{i.get('uuid'): i for i in kg_results}}
    return sorted(all_items.values(), key=lambda x: scores.get(x.get('id', x.get('uuid')), 0), reverse=True)[:n]
```

## agentmemory: Ebbinghaus time-decay + BM25+vector+KG tri-source (GitHub autosre-ai/agentmemory)

GitHub: github.com/autosre-ai/agentmemory (MIT, 2026)
Benchmark: 95.2% R@5 on LongMemEval-S — claimed SOTA for long-term agent memory recall.
Latency: BM25 (FTS5) ~0.5ms, Vector ~5ms, Hybrid ~8ms.

Key innovation: Ebbinghaus forgetting curve applied to memory weights:
```python
def ebbinghaus_weight(created_ts: float, access_ts: float = None) -> float:
    """Ebbinghaus forgetting curve: R = e^(-t/S) where S = stability."""
    import math, time
    t = (time.time() - created_ts) / 3600  # hours since creation
    # Stability S increases with each access (spaced repetition)
    S = 24 * (1 + (1 if access_ts else 0))  # base 24h, doubled if accessed recently
    return math.exp(-t / S)
```

Apply as a post-retrieval re-weighting before final ranking: multiply Graphiti fact scores
by Ebbinghaus weight. Recently accessed facts surface naturally; stale-never-accessed facts
decay out of top results without being deleted.

## ConfidenceBench: UNKNOWN confidence state for unverifiable facts (arXiv 2607.20526)

ConfidenceBench (Jul 2026, 15 frontier LLMs including Claude and GPT-4):
- Key finding: GPT-4 verbalized confidence ~62.7% AUROC — barely above chance
- "Unknowable" category: empirically verifiable but currently inaccessible facts
  (e.g., live prices, private states, future events)

Practical Graphiti pattern: tag facts with explicit confidence states to prevent
false confidence propagation (the "Spiral of Hallucination" from AUQ 2601.15703):
```python
CONFIDENCE_STATES = {
    'VERIFIED': 1.0,    # Cross-referenced with multiple sources
    'ASSERTED': 0.8,    # Single source, internally consistent
    'INFERRED': 0.6,    # Derived from other facts, not directly stated
    'UNCERTAIN': 0.4,   # Conflicting signals or low-confidence extraction
    'UNKNOWN': None,    # Empirically verifiable but currently inaccessible
}
# When adding Graphiti episodes, pass confidence via custom_extraction_instructions:
# "Tag each extracted fact with confidence: VERIFIED|ASSERTED|INFERRED|UNCERTAIN|UNKNOWN"
# Never propagate or combine UNKNOWN facts without explicit user acknowledgment.
```

## Code-as-graph pattern (FalkorDB reuse — avoids code-graph-rag infra)

code-graph-rag (vitali87/code-graph-rag, 3.3k stars) indexes codebases into a Memgraph
knowledge graph via Tree-sitter. Assessed 2026-08-10 and **declined** — cmake not available
on Fedora Silverblue without rpm-ostree layer, Memgraph + Qdrant would be two more always-on
containers, and there's no current large-monorepo querying need.

**If you later need AST-level code graph querying**, the same pattern works with the existing
FalkorDB instance instead of Memgraph:

```bash
# Tree-sitter bindings (no cmake needed — pre-built wheels)
uv add tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript
```

```python
# Parse file → extract entities → store in Graphiti group hermes-projects-<repo>
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
tree = parser.parse(source_bytes)
# Walk AST → extract function_definition, class_definition nodes
# Store each as a Graphiti episode: add_memory(name="func:<name>", episode_body="...", group_id="hermes-projects-myrepo")
```

Query with: `mcp__graphiti__search_memory_facts(query="functions that handle authentication", group_ids=["hermes-projects-myrepo"])`

Full decision record: `~/.hermes/decisions/code-graph-rag-assessment-2026-08-10.md`

## ENTLORE — KG Beats RAG for Latent Relations (arXiv:2608.10679)

Knowledge graph traversal outperforms flat RAG on multi-hop, cross-session relational queries by +23%.

**Routing rule:**
- Query has >1 named entity with an inferred relationship between them → use Graphiti MCP first
- Query is semantic similarity / "what do I know about X" → use Hindsight
- Flat RAG (web_extract or hindsight_recall alone) underperforms on latent (implicit) relations

**Application:** When a query chains concepts — "what papers did we discuss that relate to memory decay in agent systems?" — route to mcp__graphiti__search_memory_facts with entity-typed search, not hindsight_recall.

## Agentic Graph RAG — Query-Type Traversal Strategy (arXiv:2609.00829, Sweep 31) ★ HIGH

Empirical study across 3 agentic benchmarks: single-strategy graph retrieval degrades
when query types vary. Factual, procedural, and temporal queries each have a dominant
retrieval path; mixing strategies causes signal dilution.

**Query-type routing rules:**

| Query type | Signal words | Primary retrieval | Secondary |
|---|---|---|---|
| Factual | "what is", "define", "which", named entities + relationship | Graphiti search_memory_facts (2-hop) | Hindsight fallback |
| Procedural | "how to", "steps", "configure", "install", task verbs | Skill-first (`skill_view`) | Graphiti supplemental |
| Temporal | "when did", "latest", "since", "after", date references | Hindsight recall (recency-weighted) | Graphiti `valid_at` filter |
| Relational | "relates to", "connected to", "depends on", "chain" | Graphiti multi-hop (`center_node_uuid`) | Spreading activation |

**Evidence sufficiency check (required before answering):** <!-- why: prevents partial-evidence answers that look complete but miss key facts -->
Before returning a final answer to a relational or multi-hop query:
1. Count how many distinct evidence pieces support the answer (minimum 2 for factual, 1 for procedural)
2. If evidence count < minimum: run one more retrieval step with an expanded or reformulated query
3. Only then synthesize the answer

Do NOT answer multi-hop questions with a single Graphiti result — single-match confidence is low.

**Practical routing in Hermes sessions:**
```python
# Route before calling:
# Factual: mcp__graphiti__search_memory_facts(query=...)
# Procedural: skill_view(name=...) first, then graphiti supplement
# Temporal: hindsight_recall(query=...) with recency preference
# Relational: mcp__graphiti__search_memory_facts with center_node_uuid from prior result
```

**Reference**: arXiv:2609.00829, "Agentic Graph RAG: Query-Type Routing for Knowledge Graph Retrieval", Sep 2026.

## Pitfalls


- **MMR-style result diversification in retrieval** (Ruflo pattern): Graphiti `search_memory_facts`
  returns up to `max_facts` results ranked by similarity. If you're feeding results to an LLM
  for synthesis, consider de-duplicating semantically overlapping results before injection.
  Pattern: after the search call, cluster results by entity-pair overlap and keep only the most
  informative fact per cluster. This prevents the LLM from seeing the same relationship described
  5 different ways while missing facts about different entities.

  Simple Python filter:
  ```python
  # De-duplicate by (source_entity, target_entity) pair — keep highest-score per pair
  seen = {}
  for fact in search_results:
      key = (fact.get('source', ''), fact.get('target', ''))
      if key not in seen:
          seen[key] = fact
  diverse_facts = list(seen.values())
  ```

- **Per-agent group_id isolation** (MemOS pattern): when running parallel subagents via
  `delegate_task`, assign each subagent its own ephemeral group_id (e.g. `hermes-agent-<task-id>`)
  rather than sharing `hermes`. This prevents one subagent's episodic noise from polluting
  another's retrieval. Subagents can still query the shared `hermes` namespace alongside their own:
  ```python
  mcp_graphiti_search_memory_facts(query="...", group_ids=["hermes", "hermes-agent-task-42"])
  ```
  Discard the task-scoped group_id after the agent completes (let it expire naturally or
  delete via `clear_graph(group_ids="hermes-agent-task-42")`).

- **Delta updates avoid full re-indexing** (Ruflo graph-intelligence pattern): when adding
  new knowledge to the graph, prefer targeted `add_memory` episodes over bulk re-ingestion.
  Graphiti's entity deduplication handles incremental updates correctly — you don't need to
  delete-and-rebuild to incorporate new facts about existing entities. Re-ingesting unchanged
  content wastes tokens and may create duplicate/noise entities. If the graph has 0 episodes and 0 nodes, community builds, entity promotion, and search-backed cron jobs all silently do nothing useful. Verify first:
  ```python
  mcp_graphiti_get_episodes(max_episodes=5)    # "No episodes found" = empty
  mcp_graphiti_search_nodes(query="any term")  # "No relevant nodes found" = empty
  ```
  Defer Graphiti cron jobs until the graph has real content. Bootstrap with deliberate `add_memory` calls from active sessions — not bulk ingestion.

- **Gateway starts before Graphiti at login** — hermes-gateway.service may start before graphiti-mcp.service is ready, exhaust 3 connection retries, and give up. Graphiti tools become unavailable for the session. Fix: add `After=network-online.target graphiti-mcp.service` and `Wants=graphiti-mcp.service` to hermes-gateway.service `[Unit]`, then daemon-reload. Apply this to every persistent MCP sidecar, not just Graphiti.
- After `systemctl --user restart`, a stale Python process may hold port 8765 causing restart loops. Fix: `fuser -k 8765/tcp && systemctl --user restart graphiti-mcp.service`
- `uv sync` in ~/graphiti overwrites the venv copy of anthropic_client.py (temperature=None patch). The source copy at ~/graphiti/graphiti_core/llm_client/anthropic_client.py survives and must be re-synced manually into venv if uv sync is run.

- Episode processing is **async** — wait 20-30s after `add_memory` before searching
- **Ollama is no longer installed.** Graphiti embeddings now use OpenAI text-embedding-3-small. If you see embedding errors, check:
  1. `OPENAI_API_KEY` in ~/graphiti/mcp_server/.env is the real sk-proj-... key (not an Ollama placeholder)
  2. `OPENAI_API_URL` is `https://api.openai.com/v1` (NOT `http://localhost:11434/v1`)
  3. `EMBEDDER_MODEL` is `text-embedding-3-small`
  If the URL still points at Ollama, run the migration script or patch manually:
  ```python
  # ~/graphiti/mcp_server/.env — correct values (Aug 2026 migration):
  # OPENAI_API_KEY=<same key as ~/.hermes/.env OPENAI_API_KEY>
  # OPENAI_API_URL=https://api.openai.com/v1
  # EMBEDDER_MODEL=text-embedding-3-small
  ```
  After patching .env, restart graphiti-mcp.service and check logs for "Embedder: openai / text-embedding-3-small".

- **Vector dimension mismatch (768 vs 1536) after switching embedders**: FalkorDB vector indexes bake in the dimension at creation time. Switching from nomic-embed-text (768) to text-embedding-3-small (1536) causes "Vector dimension mismatch, expected 768 but got 1536" errors. Fix — since the graph may be empty, it's safe to drop and rebuild:
  ```bash
  CONTAINER=$(podman ps -q --filter ancestor=falkordb/falkordb)
  # List existing graphs
  podman exec $CONTAINER redis-cli GRAPH.LIST
  # Drop ALL — they'll rebuild with correct schema on first add_memory
  for graph in hermes graphiti_hermes l1 hermes-reasoning graphiti; do
    podman exec $CONTAINER redis-cli DEL $graph
  done
  systemctl --user restart graphiti-mcp.service
  # Verify: attempt add_memory — no "768" errors in journalctl
  ```
  Warning: this deletes all graph data. Only safe when the graph is empty or you have a backup.
- FalkorDB must be running. Check: `redis-cli -p 6379 ping`
- After `uv sync`, reapply the temperature patch to the venv copy
- The MCP endpoint redirects `/mcp/` → `/mcp` (307); curl needs `-L` flag
- `OPENAI_API_KEY` in `.env` is used for embeddings (text-embedding-3-small). Must be set correctly in ~/graphiti/mcp_server/.env.
- **Do NOT bulk-ingest the Obsidian vault.** Hindsight covers semantic recall; bulk ingestion produces noisy entity soup. Graphiti captures only incremental structured facts from sessions going forward.
- Default group_id for Hermes-stack facts is `"hermes"` — see Group ID taxonomy above.

## PSE Contamination Mitigations (arXiv:2608.07952, Sweep 12)

Persistent Semantic Entity Contamination: injected preferences and false entities persist at
100% across sessions at t=10 and compound 1.9× along a 4-stage pipeline (40% → 75%). All
24 tested LLMs are susceptible. The attack surface in this stack is:

- **Graphiti KG**: contaminated entity nodes propagate to every future query that touches them
- **l1-graphiti-write**: facts from web_extract or subagent outputs carry untrusted content into the graph
- **Cron `context_from`**: contaminated output from one cron run propagates to the next

**Mitigations implemented:**

1. **source_type tagging** (implemented Aug 2026 in l1-graphiti-write.py): every episode
   written to Graphiti includes `[source_type=internal|cron|external]` in the episode body.
   Trust weights: internal=1.0, cron=0.7, external=0.4. When retrieved facts are used for
   reasoning, prefer higher-trust-source facts when there is a conflict.

2. **Audit external-source nodes**: when a web_extract or subagent output is written to
   Graphiti, its node label will include `[source_type=external]`. If you observe a claim
   in retrieval that seems wrong, check its source_type tag first — external-tagged facts
   should be verified against the original source before acting on them.

3. **Skill files are write-protected**: only `skill_manage` can modify skills — subagents
   processing external content must never write directly to SKILL.md files. This is the
   highest-trust boundary in the stack.

4. **Per-subagent group_id isolation** (see Per-agent group_id pitfall above): subagents
   handling external content write to ephemeral group_ids, not the shared `hermes` namespace.
   This prevents external-content contamination of the main graph.

## Readable Entity Labels for Zero-Shot Graph Querying (arXiv:2607.18029, Sweep 12)

NLKGQ finding: human-readable entity names + semantic type annotations let LLMs generate
accurate graph queries zero-shot — more impactful than model choice or prompt engineering.

**Mandate for all Graphiti episodes written from this stack:**

When adding an episode via `add_memory`, structure the episode body so entity names are
self-describing rather than opaque IDs:

```
# Preferred — human-readable, type-annotated
[source_type=internal] Hermes skill 'arxiv' (type=skill, domain=research) has a ## Pitfalls
section covering export.arxiv.org CDN blocks and rate limits.

# Avoid — opaque, no type hint
[source_type=internal] arxiv pitfalls: CDN block, rate limit
```

The preferred form lets Graphiti extract a node `arxiv` with type `skill` and domain `research`,
enabling zero-shot queries like "what research skills have pitfall sections?" without fine-tuning.

**Entity naming rules:**
- Prefer full descriptive names over abbreviations (l1-graphiti-write script > l1gw)
- Always include a `type=` annotation when the entity type is not obvious from context
- For people, tools, files, scripts: use their full canonical name as it appears in the codebase
- For concepts: use the term as it would appear in a search query

## PSE Contamination Mitigations (arXiv:2608.10392) ★ HIGH — Sweeps 12/13

PSE = Persistent State Explosion. When Graphiti ingests high-volume episodic data (e.g. every
Hindsight fact, every cron run summary), the graph grows unbounded and query latency degrades
exponentially. Two contamination patterns to prevent:

**1. Episode flooding:** Writing every l1-extract.py fact as a separate episode creates thousands
of thin nodes. Graphiti merges near-duplicates but only within the same write batch.
Fix: the l1-gmemory-consolidation.py insight tier is the correct write unit — write cluster
summaries, not raw facts. Raw facts belong in Hindsight; only distilled insights go to Graphiti.

**2. Entity sprawl:** Generic entities (e.g. "agent", "skill", "memory") become hub nodes
with thousands of edges, making traversal expensive.
Fix: always qualify generic entities with a domain: "Hermes agent", "arxiv skill", "Graphiti memory".
The l1-graphiti-write.py POLE+O type annotations already do this — enforce them.

**Detection:** Run periodically:
```bash
curl -s http://127.0.0.1:8765/mcp  # check Graphiti node count via MCP status
```
If node count > 10x the number of distinct concepts you track, PSE is occurring.
Prune duplicate/unqualified entity nodes via `mcp__graphiti__delete_entity_edge`.

## Cue-Tag-Content Graph Nodes at Ingest (arXiv:2608.11982) ★ HIGH — Sweeps 12/13

Source: "Structured Memory Graphs for Long-Horizon Agents". At ingest time, decompose each
episode into three node types rather than storing as a monolithic text blob:

**Cue node:** The retrieval trigger — what query would surface this fact?
**Tag node:** Categorical labels (domain, type, trust tier, recency).
**Content node:** The actual fact text.

**Hermes implementation in l1-graphiti-write.py:**
The current episode body format already embeds cue-tag-content implicitly:
```
[type=fact] [trust=1.0] [source_type=session]  ← Tag
Hermes skill 'arxiv' has pitfall: CDN blocks    ← Content
```
The retrieval query ("what are arxiv pitfalls?") is the implicit Cue.

To make this explicit, add a `[cue: ...]` field to the episode body:
```
[type=fact] [trust=1.0] [source_type=session] [cue: arxiv pitfalls CDN blocks]
Hermes skill 'arxiv' has pitfall: CDN blocks from export.arxiv.org
```
This pre-seeds Graphiti's entity extractor with the intended retrieval signal, improving
recall by ~18% on domain-specific queries (paper result).

**Update l1-graphiti-write.py:** Add a `generate_cue(text)` function that extracts the
top 3-5 keywords from the fact text (stopword-filtered) and prepends `[cue: keywords]`
to the episode body. Already partially done via POLE+O entity hints — extend it.

## Trust-Tiered Librarian with `as_of` Timestamps (arXiv:2608.12984) ★ MED — Sweeps 13/15

Source: "Temporal Knowledge Graph Librarian for LLM Agents". Graphiti's bi-temporal model
(valid_at + created_at) supports point-in-time queries, but only if `as_of` is populated
at write time. Without it, all facts appear equally current regardless of when they were true.

Trust-Tiered Librarian Pattern (arXiv:2608.12984): ingest timestamped sources into a trust-tiered ontology. Each Graphiti episode should tag: trust_tier (authoritative | secondary | inferred), as_of (ISO timestamp of claimed validity). Authoritative sources (official docs, human-verified facts) get higher trust_tier than LLM-inferred entities. Raw tool output is T2 (operational) by default - only promote to T1 after a deterministic verifier (not the model) confirms accuracy. Allowing raw tool output at T1 creates a trust-bypass path against ATP untrusted-data rules. When a contradiction arises between two nodes, the higher trust_tier + more recent as_of wins. This is the 'Reconcile Once' pattern: reconciliation happens at ingest based on trust tier, not at query time.

**Three trust tiers for Hermes:**

| Tier | trust weight | Source types | Decay |
|------|-------------|--------------|-------|
| T1 (ground truth) | 1.5 | arXiv citations, Hermes docs, human-verified facts | none |
| T2 (operational) | 1.0 | session observations, skill patches, cron results | 90 days |
| T3 (ephemeral) | 0.7 | web_extract snippets, draft notes, unverified claims | 30 days |

**as_of field:** When writing to Graphiti via `add_memory`, include the valid date in the
episode body so the librarian can reconstruct the timeline:
```
[type=fact] [trust=1.0] [as_of=2026-08-18] [source_type=session]
Hindsight bank hermes-default contains 8210 facts as of 2026-08-18.
```
Facts without `as_of` are assumed valid_at=created_at (fine for timeless facts, wrong for
operational state facts like "bank contains N facts" or "port X is running").

**Claim graph:** For facts that contradict earlier facts, add `[supersedes: <prior_cue>]`:
```
[type=fact] [trust=1.0] [as_of=2026-08-18] [supersedes: pg0 postgres running at 5433]
pg0 postgres instance at port 5433 is DEFUNCT — libicuuc.so.70 missing, system has .so.77.
```
This lets Graphiti maintain a claim graph where outdated facts are traceable rather than
silently overwritten. Graphiti's dedup will merge near-duplicates; the supersedes tag
preserves the contradiction history for auditing.

**Implementation:** Update l1-graphiti-write.py to auto-inject `[as_of=YYYY-MM-DD]` from
today's date on every write, and detect T1/T2/T3 tier from source_type to set trust weight.
