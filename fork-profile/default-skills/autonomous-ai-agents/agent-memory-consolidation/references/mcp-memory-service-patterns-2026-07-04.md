# mcp-memory-service Architecture Patterns (2026-07-04)

Source: doobidoo/mcp-memory-service v11.3.3 (Codeberg, July 2026)
Discovered via: web_extract → Codeberg blocked → DeepWiki fallback → PyPI README

## What it is

Production-grade MCP memory backend (Python, Apache-2.0). SQLite-vec local storage,
ONNX embeddings (sub-5ms semantic search, no cloud cost), typed knowledge graph,
REST API + MCP transport. v11.3.3 released 2026-07-01, actively maintained.

PyPI: https://pypi.org/project/mcp-memory-service/
Codeberg: https://codeberg.org/doobidoo/mcp-memory-service

---

## Patterns worth borrowing

### 1. NLI-based contradiction detection (RFC #732/#1027)

Before writing a new memory, run it through an NLI (Natural Language Inference)
classifier against existing memories in the same entity/topic domain. The classifier
outputs ENTAIL / NEUTRAL / CONTRADICT. Only CONTRADICT fires a merge-or-reject gate.

Key insight: simple semantic similarity finds *related* memories but not *opposing*
ones. NLI explicitly surfaces contradiction. A memory "user prefers dark mode" and
"user prefers light mode" have high cosine similarity but opposite meaning.

Practical approximation without a local NLI model:
- Before writing entry E, run session_search or mcp_graphiti_search_memory_facts
  on the same entity/topic
- Present both the new fact and the existing fact to the LLM with a binary question:
  "Does the new fact contradict the existing one? Y/N + brief reason"
- If Y: prepare a REPLACE, not ADD

The project implements this as an async scorer with ONNX; we approximate with a
focused LLM query. Slower but zero infrastructure cost.

### 2. Session-end consolidation gated on substantive content

Commit message (2026-06-22): "fix(hooks): gate session-end consolidation on
substantive content"

Pattern: before running consolidation at session end, check whether the session
actually produced content worth consolidating. If the session was: idle chatter,
simple factual Q&A, task routing with no novel tool use, or one-turn answers —
skip consolidation entirely.

Heuristic gate (adapt to Hermes):
- Did the session involve 5+ non-trivial tool calls?
- Was there any user correction, workflow surprise, or multi-step debugging?
- Was new environmental knowledge discovered (API quirk, tool behaviour, config gap)?
If none of the above: skip. The signal-to-noise of forcing consolidation on idle
sessions is negative — you generate noise entries that dilute attention.

Already partially encoded in agent-memory-consolidation "When to run" section.
The new insight: this should be a hard gate, not a guideline. Default = skip.

### 3. Multi-agent shared memory via sentinel tags

Pattern: agents tag memories with a sentinel string (e.g. `msg:cluster:agent-id`).
Other agents filter on that tag to receive cross-agent signals. The memory service
becomes the coordination layer with zero additional protocol infrastructure.

Hermes relevance: in multi-subagent runs, the orchestrator could write sentinel-tagged
entries to Graphiti that worker summaries read back. Simpler than a custom bus.

### 4. Memory quality scoring (async, per-entry)

Each memory gets scored on three axes: relevance, freshness, specificity.
Low-scoring memories decay (score drops on each retrieval miss, pruned at threshold).

Hermes approximation: at consolidation time, score each *existing* entry on:
- Freshness: has it been referenced or useful in the last N sessions?
- Specificity: is it a concrete fact or a vague generality?
- Uniqueness: does another entry already capture the same idea?
Low-scoring entries are prune candidates, not just new-entry gates.
Current Hermes consolidation only gates new entries, doesn't prune stale ones.

### 5. Typed knowledge graph edges

Edge types: causes, fixes, contradicts, depends_on, supersedes
These are more precise than plain vector proximity. A "fixes" edge between
"bug X" and "workaround Y" survives semantic drift in the embedding space.

Graphiti (already in use) supports typed edges natively. We underuse this —
most Graphiti writes are plain text episodes without explicit edge typing.
When adding a fact that is clearly a fix, workaround, or dependency relationship,
use mcp_graphiti_add_triplet with an explicit edge_name rather than mcp_graphiti_add_memory.

---

## Codeberg scraping note

Codeberg actively detects and blocks AI scrapers (returns git-manual gibberish
instead of page content). Fallback path that worked:
1. web_extract on raw Codeberg URLs → blocked
2. web_search with site:codeberg.org to surface the project
3. DeepWiki (deepwiki.com/<owner>/<repo>) for architecture overview
4. PyPI page for feature descriptions and changelog (if package is published)
5. GitHub mirror search (q-qp-p/doobidoo-mcp-memory-service) for README fragments
