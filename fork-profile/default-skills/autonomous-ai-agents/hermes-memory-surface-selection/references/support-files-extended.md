## Support files (continued)
- `references/external-tool-evaluation-framework.md` — 3-question framework for evaluating new external memory/agent tools against the stack. Includes session log of evaluated tools (GraphMind, graphthulhu, pauliusztin posts, Curion, r/hermesagent orchestrator thread, taOS+taOSmd, TencentDB Agent Memory) with verdicts and extracted patterns. Load this before spending time on a new tool proposal.
- `references/hindsight-daemon-recovery.md` — mid-session recovery script for Hindsight daemon startup failures (missing API key pattern).

### Wiki Memory Layer (LangChain Wiki Memory Pattern, Aug 2026)

A fourth retrieval surface: **pre-computed domain knowledge files** — distinct from Hindsight (vector), session_search (FTS5 transcript), and MEMORY.md (persistent facts).

Use wiki memory when:
- Domain has recurring structure the agent re-discovers from scratch each session (project codebase, research corpus, property search, trading rules)
- Raw source material is too large to inject as context but needs structured navigation
- Domain knowledge changes slowly and can be maintained incrementally

Implementation pattern (no new infrastructure required):
- Location: `~/.hermes/wiki/<domain>/` YAML-frontmatter `.md` files (same format as skills)
- Create/update: call Claude with "given these raw logs/docs, upsert these wiki pages"
- Search: FTS5 on wiki files using existing session_search infrastructure
- Inject: top-3 page summaries as a system prompt context block on session start for known domains
- Format: headers + bullet facts + cross-refs (NOT prose narrative — agent-readable, not human-readable)
- Source: https://www.langchain.com/blog/wiki-memory

Domains worth a wiki: `ppor` (property search), `religion-kg` (corpus structure/schema), `trading` (strategy rules/limits)

### Aug 2026: New Memory Surfaces + Patterns

### Anthropic Native Memory Tool (beta)
`BetaLocalFilesystemMemoryTool(base_path="~/.hermes/agent-memory/")` — filesystem-backed
cross-session memory built into the Anthropic SDK. Best for: cross-session project state
that must survive context compaction, when Hindsight or Graphiti are unavailable.
Use alongside (not instead of) Hindsight for long-term structured facts.
Caveat: beta API, may change; test before relying on it for production agentic loops.

### Dual-Gate Dedup (arXiv:2608.10216)
Cosine similarity alone is unreliable as a memory dedup gate — false-merge rate 12-18%.
**Hermes:** Always combine cosine > 0.85 AND LLM entailment check before merging any Hindsight entry.
Never merge on cosine alone. This applies to all hindsight_retain calls that might duplicate existing facts.

### ENTLORE: KG > RAG for Latent Relations (arXiv:2608.10679)
Knowledge graph traversal outperforms flat RAG for multi-hop, cross-session relational queries by +23%.
**Routing rule:** If query has > 1 named entity with an inferred relationship between them → use Graphiti MCP.
If query is semantic similarity / "what do I know about X" → use Hindsight. Flat RAG underperforms
on latent (implicit) relations that are inferable but not stated.


SQLite-backed append-only fact ledger with MCP interface. Key properties:
- Immutable transcripts with provenance tracking (each fact has source + timestamp)
- Exposes as MCP server for tool-call access
- Lightweight alternative to Graphiti when you need auditability but not graph traversal
Hermes use case: audit trail for autonomous agent decisions across sessions.
Repo: github.com/[see references] — evaluate via external-tool-evaluation-framework.md

### `nox-agent-kit` pattern (GitHub, Aug 2026)
Provides: scoped memory (per-task isolation), provider failover (Anthropic → OpenAI on error),
permissioned tool execution (tool whitelist per agent role).
Hermes relevance: provider failover pattern is useful — implement as: if Anthropic API returns
5xx, retry with same prompt using fallback model (claude-sonnet-4-6 → claude-haiku-4-5 as last resort).
Note: Hermes uses Anthropic-only routing; cross-provider fallover (gpt-4o etc.) is not available.

### lance-bundle (PyPI, Aug 2026)
Portable ONNX+LanceDB embedding bundles — pack a vectorstore + its embedding model as a
single distributable artifact registered on HuggingFace Hub.
Hermes relevance: for the religion KG and knowledge-corpus-architecture, enables portable
embedding snapshots. Evaluate when corpus needs to be shared or checkpointed.

### RUMBA benchmark (SberDevices/Habr, Russian, Aug 2026)
Source: https://habr.com/ru/companies/sberbank/articles/1060432/
Russian-language long-term memory evaluation benchmark: 90+ conversation turns,
tests retention, temporal ordering, and contradiction detection across sessions.
Key finding: most LLMs degrade sharply after 30 turns even with explicit memory tools.
Hermes implication: Hindsight + compaction is the right architecture; do not rely on
in-context memory for multi-session state beyond ~30 turns. Use hindsight_retain proactively.
