# External memory/agent-tool evaluation framework

Use this when asked to evaluate a new external tool (GitHub repo, blog post, Reddit post)
against the existing Hermes memory stack. Produces a clear yes/no/partial verdict fast.

## The 3 questions (in order)

1. **Coverage gap** — Does it do something the current stack cannot?
   - Current stack covers: semantic recall (Hindsight), entity/relationship graph (Graphiti),
     structured notes (MemPalace+Obsidian+QMD), code search (search_files/read_file),
     session recall (session_search), reasoning traces (hermes-reasoning group in Graphiti).
   - If the tool's core capability maps 1:1 to an existing layer → skip.

2. **Fit** — Even if it adds something new, does it fit the actual workflow?
   - Hooks that only fire in Claude Code don't help a Hermes CLI workflow.
   - Tools designed for 100k+ LOC codebases don't add value on small personal projects.
   - A 4th MCP server is a maintenance cost — require a clear benefit to justify it.

3. **Implementation cost vs. extractable pattern** — Can you get the value without the tool?
   - Often the real lesson is a *pattern* (e.g., "semantic entry point → graph traversal")
     that the current stack already implements. Capture the pattern; skip the tool.
   - If the pattern is already present, note it as validation, not a gap.

## Output format

State per tool:
- What it actually does (1-2 sentences, concrete)
- Gap analysis: what it adds vs what the stack already covers
- Fit check: any blockers specific to this workflow
- Verdict: implement / skip / note pattern only
- If skip: what the closest existing stack equivalent is

## Evaluated tools (session log)

### TencentDB Agent Memory (github.com/TencentCloud/TencentDB-Agent-Memory) — July 2026
- **What**: Hermes memory provider plugin. Two systems: (1) L0-L3 memory pyramid —
  LLM-extracted atomic facts (L1), scenario blocks (L2), user persona (L3) distilled from
  raw conversations; (2) Mermaid canvas symbolic short-term memory — offloads verbose tool
  logs to `refs/*.md`, keeps only a compact Mermaid graph in context; agent drills into raw
  content via `node_id` on demand. SQLite+sqlite-vec backend, hybrid BM25+vector+RRF retrieval.
  Claims: -61% tokens on WideSearch, -33% on SWE-bench, PersonaMem 48%→76%.
- **Gaps addressed locally (2026-07-09)**:
  1. **Mermaid canvas offloading** — implemented: `canvas-offload.py` at `~/.hermes/scripts/`. See `symbolic-context-offload` skill.
  2. **Structured atomic fact extraction** — implemented: `l1-extract.py` (qwen3:8b) + `l1-promote.py` (llama3.2:3b) + 3 cron jobs. Facts → staging.md → Hindsight automatically.
  3. **Progressive persona distillation (L2/L3)** — not implemented. L3 user persona still relies on manual MEMORY.md/USER.md curation.
  4. **White-box artifacts** — partial: memory-facts/YYYY-MM-DD.md is human-readable; canvas refs are plain text.
- **Fit**: High. Plugin installed (`~/.memory-tencentdb/`); symlinked as Hermes plugin. Not active — hindsight is active provider.
- **Verdict**: **Installed, not active.** The local scripts cover gaps 1+2 without switching providers. Activate full plugin only if L2/L3 persona distillation becomes a priority — requires env vars in `~/.hermes/.env`. See `tencentdb-agent-memory` skill.
- **Key pitfalls**: env var naming split (plugin `MEMORY_TENCENTDB_*` vs gateway `TDAI_LLM_*`); BM25 tokenizer defaults to Chinese — add `"bm25": {"language": "en"}` before activating; circuit breaker trips on 5 gateway failures.

### GraphMind (github.com/aouicher/graphmind) — July 2026
- **What**: Rust binary, AST-based code structure graph (functions, call chains, blast radius,
  dead code), 25 MCP tools, semantic embeddings, persistent per-project memory.
- **Gap**: Genuine gap — structural code graph (AST/call chains) not covered by any stack layer.
- **Fit blocker**: Built for Claude Code hook system; hooks only fire in Claude Code sessions,
  not Hermes CLI. Personal repos are small — token savings matter less.
- **Verdict**: Skip for now. Revisit if Claude Code usage increases or repos grow to 50k+ LOC.
- **Pattern extracted**: 3-layer discipline (structural graph → persistent memory → raw files)
  is already the Hermes default via search_files/QMD → Hindsight/Graphiti → read_file.

### graphthulhu (github.com/skridlevsky/graphthulhu) — July 2026
- **What**: Go binary, MCP server giving agents read-write access to Obsidian/Logseq vault
  via typed pages + [[wiki links]] + properties. 37 MCP tools. "Daily notes as scratch,
  graph as curated long-term memory."
- **Gap**: None. Typed structured pages + links is exactly what MemPalace + Obsidian QMD + Graphiti
  already provide, and more automatically (Graphiti extracts entities vs manual page writing).
- **Fit blocker**: Redundant layer over existing Obsidian+QMD+MemPalace integration.
- **Verdict**: Skip entirely.
- **Pattern noted**: "Daily files are scratch, graph is curated memory, periodic heartbeat promotes
  important stuff" — already the Hermes convention (sessions → Graphiti/Hindsight/MemPalace).

### pauliusztin Reddit posts (r/AI_Agents + r/learnmachinelearning) — July 2026
- **What**: 3 mistakes building KG memory: (1) over-engineered ontology, (2) conflating
  resolution with deduplication, (3) no reasoning memory layer.
- **Gap**: Mistakes 1-2 already handled by Graphiti's automatic extraction. Mistake 3 was a
  genuine gap — reasoning traces not stored.
- **Verdict**: Partially implemented — added `hermes-reasoning` Graphiti group for per-task
  traces (Strategy/Tools/Outcome/Lesson format, significant tasks only, <10 sentences).
- **Crosspost note**: The r/learnmachinelearning post is the same article as r/AI_Agents;
  don't re-evaluate crossposted content.

### Curion (github.com/geanatz/curion) — July 2026
- **What**: Project-local memory MCP server (TypeScript, SQLite at `.curion/`). Two tools:
  `remember(text)` / `recall(text)`. Structured status responses (`saved`, `answered`,
  `weak_match`, `no_memory`, `rejected`, `provider_error`, `clarification_needed`).
  Raw input is never persisted — only LLM-normalized summaries land in the store.
  Supports a `isPrivate: true` project flag that excludes a project from cross-project
  semantic retrieval. Pluggable OpenAI-compatible or Anthropic providers. Optional
  semantic retrieval layer.
- **Gap**: Project-scoped memory (per-repo `.curion/`, ships with contributors via git config)
  is genuinely absent from the Hermes stack. Hindsight/Graphiti are user-global, not repo-local.
  The `clarification_needed` forwarding contract (agent must ask the user a specific question
  verbatim before retrying) is a design pattern not captured anywhere in the current stack.
  The `isPrivate` flag for cross-project search exclusion is also novel.
- **Fit blocker**: The Hermes workflow is global/user-scoped, not repo-scoped. Adding a 4th
  MCP server for project-level SQLite adds fragmentation and maintenance cost with limited
  benefit on personal single-user projects where repo isolation is unneeded.
- **Verdict**: Skip tool. Extract 3 patterns:
  1. **Status-discriminated responses**: MCP tools should return a `status` field
     (`saved` / `answered` / `weak_match` / `no_memory` / `rejected` / `provider_error`)
     so callers can branch precisely rather than parsing prose.
  2. **`clarification_needed` forwarding**: When a memory tool can't answer reliably, it
     can return a `clarification_needed: { question: "..." }` block that the agent must
     forward verbatim to the user — forces explicit escalation rather than hallucinated recall.
  3. **Normalize-before-persist discipline**: Never store raw user input. Pass through a
     controller that normalizes, extracts summary + metadata (kind, confidence, safety flags,
     timestamps). This is what separates a memory store from a raw log.
- **Existing coverage**: Hindsight covers semantic recall; Graphiti covers structured facts;
  the normalize-before-persist pattern maps to Hermes durable memory's 3-axis filter.

### Reddit: "Building an orchestrator for Hermes Agent: Kanban, delegate_task, or a separate workflow layer?" (r/hermesagent, Jul 2026)
- **What**: Design post proposing a 6-phase orchestrator (intake → planning → execution →
  handoff → review loop → synthesis) with specialist roles (researcher/builder/reviewer/
  synthesizer). Notable reply from `Putrid_Assistant_557` who built `Smithers` — a durable
  workflow runtime with Hermes MCP integration — articulating a clean 4-layer architecture split.
- **Gap**: 4 patterns absent from the stack:
  1. **Task intake classifier** — gate that decides delegate_task vs Kanban vs cron vs simple
     before choosing a pipeline shape.
  2. **Structured handoff schema** — typed 5-field handoff (what_done / evidence / files_changed /
     unresolved_issues / confidence) for inter-agent artifact passing.
  3. **Review loop branching** — named outcomes: retry-same / replan / decompose-further /
     ask-human / accept-partial with explicit retry cap (max 2 retry-same before escalating).
  4. **Putrid_Assistant_557 layer model** — Hermes = intent interpreter, Skill = escalation
     trigger, MCP = integration boundary, Runtime = state/retries/approvals/resumability.
- **Fit blocker**: None. Post is specifically about Hermes CLI orchestration.
- **Verdict**: Skip Smithers tool (external workflow runtime; adds infra for minimal gain on
  personal-scale work). Extract 4 patterns into `hermes-role-pipelines`.
- **Existing coverage verified**: Specialist roles, delegate_task discipline, Kanban swarm,
  artifact handoff, topology memory — all already present. New sections fill the named gaps only.

### taOS + taOSmd (github.com/jaylfc/taOS) — July 2026
- **What**: Self-hosted AI agent OS (Python/TypeScript). A complete platform: full browser-based
  web desktop shell, 40 bundled apps, 109 catalog app catalog, 17 agent frameworks (Hermes is
  one of 17), distributed compute cluster manager, LLM proxy (LiteLLM) with per-agent virtual
  API keys + budget limits, 47 MCP plugins, 7-connector Channel Hub (owns bot tokens so agents
  can switch frameworks without rewiring), and taOSmd — a standalone memory system (temporal KG
  + hybrid vector search + zero-loss archive + "Librarian" intent-aware retrieval routing layer).
  taOSmd benchmarks at 97.0% end-to-end judge accuracy on LongMemEval-S (retrieve→generate→judge),
  vs MemPalace's 96.6% Recall@5 (retrieval only — not comparable metrics).
  Uses qmd as its embedding/reranker/query-expansion backend.
- **Gap (real, but workflow-incompatible)**:
  - taOSmd's "Librarian" layer automates retrieval routing (intent parse → surface classification
    → query expansion → execute) as infrastructure, not as agent skill knowledge.
  - Per-agent virtual API keys with individual budget+rate limits are absent from the Hermes stack.
  - Contradiction detection in memory (taOSmd does it automatically) is not explicit in Hermes stack.
- **Fit blocker**: Hard architectural mismatch. taOS is designed to be the OS that *hosts*
  agents; adopting it would invert the hierarchy — Hermes becomes a worker inside taOS rather
  than the primary surface. Not an upgrade on single-machine personal CLI use. Requires a
  dedicated server process and persistent web UI. 410 stars / 31 forks — real active project
  but a completely different scale and operating model.
- **Verdict**: Skip. Do not install or integrate. Extract 1 pattern.
- **Pattern extracted**: Librarian pattern — in multi-agent pipelines, treat retrieval routing
  as a named pipeline stage (intent parse → classify → expand → execute) rather than per-agent
  ad-hoc logic. Added to `hermes-memory-surface-selection` Self-Route gate section.
- **Benchmark note**: taOSmd vs MemPalace comparison is not apples-to-apples (end-to-end judge
  vs Recall@5). When evaluating memory system claims, always confirm which measurement was
  used: retrieval-only recall vs full retrieve+generate+judge accuracy.

## Recurring "skip" signals

These patterns reliably indicate a tool is not worth adding:
- "Replaces vector memory with graph" → you already have both
- "Persistent memory for AI sessions" → you already have three layers of this
- "Works great with Claude Code [hooks]" → you use Hermes CLI, not Claude Code
- "No database needed, just markdown files" → your Obsidian vault already does this
- "Add RAG on top of the graph" → Hindsight + Graphiti is already this architecture
- The "what finally worked" in the post describes your baseline setup
