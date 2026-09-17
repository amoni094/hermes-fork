---
name: hermes-memory-surface-selection
version: 3.2.0
related_skills:
  - agent-memory-consolidation
  - graphiti-mcp-setup
  - hermes-context-hygiene
  - obsidian-research-ingestion
  - hermes-memory-capture-and-bridge
triggers:
  - Deciding where information should live or which retrieval surface to query
  - Choosing between memory tool, session_search, Graphiti, and Hindsight (QMD and MemPalace are disabled)
  - Routing a retrieval or storage decision across Hermes memory surfaces
  - Determining if a fact belongs in durable memory vs transcript vs knowledge graph
description: >
  Use when choosing memory surface, detecting stale/conflicting facts (TEPA), or applying conflict resolution order. Durable vs Hindsight vs session_search routing; STALE domain classification. qmd disabled. MemPalace disabled.
created_by: agent
---

# Hermes memory surface selection

Use this when deciding where information should live in a Hermes-centered workflow, or which retrieval surface to query first.

## Scatter-Gather Anti-Pattern + Memory-First Design (Zenn.dev/JP, Aug 2026) <!-- rationale: names the core cost of multi-source API fan-out at inference time; establishes the heuristic for pre-integrating into KG vs dynamic collection -->

**Scatter-gather problem** — when an agent fans out to multiple external APIs per inference turn to assemble context, three concrete costs compound:
1. **Latency gate**: the slowest API gates the entire response — even if 9 of 10 calls return in 100ms, one 2s call delays the whole answer
2. **Token waste**: context is rebuilt from zero every turn; no reuse of prior assembly work
3. **Accuracy degradation**: cross-system relationships must be inferred ad-hoc each turn, producing inconsistent bridging

**Memory-first design fork** (vs. inference-time scatter-gather):
- **Inference-time data collection**: agent routes to external APIs dynamically per query (MCP/RAG pattern). Use when: data changes frequently, queries are unpredictable, integration cost is low.
- **Pre-integrated memory**: relational data integrated into a KG (Graphiti) before inference begins, so the LLM reasons over unified facts. Use when: data is stable, queries are known-type, relationships matter.

**Decision gate** (add to Self-Route gate):
```
Is the data stable and relational? → pre-integrate into Graphiti before inference (memory-first)
Is the data dynamic or one-off? → scatter-gather at inference time (acceptable)
Are 3+ APIs needed per query? → always pre-integrate (scatter-gather threshold exceeded)
```

Reference: Zenn.dev/knowledge_graph/articles/kg-agent-memory-first-design (JP, Aug 2026).

## Flat-File Memory Threshold + Mandatory Rule Placement (Habr/RU, Aug 2026) <!-- rationale: vector stores break even at 10K+ docs; below that markdown + native retrieval is strictly better; mandatory rules must not be in probabilistic retrieval -->

Practitioner result from an 8-agent portfolio (135 memory entries): vector stores break even vs markdown + model-native retrieval at approximately **10,000 documents**. Below that threshold, markdown is strictly superior due to:
1. **Infrastructure tax**: two additional services (embedding model + vector store) to operate and repair
2. **Competing truth sources**: second retrieval system rivals the harness for source of truth
3. **Wrong pain attribution**: practitioners buy vector search for retrieval accuracy, but the real bottleneck is session-start context budget (fixed by sub-indexing, not by a vector store)

**Hermes application**: Hindsight (vector) is justified for Hermes because sessions number in the hundreds — still well below 10K. But the infrastructure tax concern validates the existing design: Hindsight runs as a local service rather than a managed external store.

**Critical mandatory-rule placement rule**: guardrails and hard constraints (never-do-X rules) must live in **project instructions** (MEMORY.md / AGENTS.md / skill bodies), NOT in probabilistic retrieval memory. A mandatory rule that is only retrievable probabilistically will fail exactly when it matters most — under novel query shapes or adversarial conditions where retrieval might not surface it.

Hermes translation: absolute constraints (never push to production without test pass, never delete without backup, never send email without confirmation) must be in:
- MEMORY.md `[procedural]` sections (always-injected), OR
- Skill bodies as explicit guardrails, OR
- AGENTS.md hard rules

Never rely on `hindsight_recall` alone for a rule that must never be violated. Probabilistic retrieval ≠ reliable rule enforcement.

Reference: Habr/RU, "Flat Files vs Vector Bases", Aug 2026; 135-entry portfolio analysis.

## OpenAI 3-Cost Memory Taxonomy (OpenAI Agents SDK beta, Aug 2026) <!-- rationale: provides a principled framing for which memory tier to route to based on whose cost dominates -->

Three-cost taxonomy for memory value — route each write to the tier that addresses the dominant cost:

| Cost type | What it reduces | Primary Hermes surface |
|---|---|---|
| **Agent cost** | Less exploration on repeat tasks (fewer tool calls re-deriving known facts) | MEMORY.md procedural + skill bodies |
| **User cost** | Corrections/preferences persist across sessions (user doesn't re-state) | MEMORY.md user preferences + Hindsight |
| **Context cost** | User needs fewer words to resume (agent already knows context) | session_search + Hindsight episodic |

When writing a new memory entry, ask: which cost is this primarily reducing? That determines where it goes and how high-priority it is:
- Agent-cost facts (tool quirks, known workarounds, environment facts) → MEMORY.md `[factual]` or skill pitfalls
- User-cost facts (preferences, corrections, style) → USER.md `[preference]` or `[correction]`
- Context-cost facts (project state, session continuity) → Hindsight episodic (not durable)

Reference: OpenAI Agents SDK beta, Sandbox Agent Memory design, Aug 2026.

## ForeDreamer — Dual-Memory Temporal Architecture (arXiv:2608.20920, Aug 2026) <!-- rationale: formalises the episodic/semantic split as a temporal-horizon boundary; applies to choosing between Hindsight and Graphiti -->

ForeDreamer introduces a dual-memory architecture for future event prediction: a short-term **episodic store** (recent, high-fidelity, fast decay) and a long-term **semantic store** (stable patterns, slow accumulation). The two stores are jointly trained but separately retrieved depending on the query's temporal horizon.

**Key finding applicable to Hermes surface selection:**
- Queries about *recent* state (current config, today's decisions, this session's actions) → favour **Hindsight** (episodic, fast, recent)
- Queries about *stable patterns* (user preferences, recurring tool quirks, cross-session conventions) → favour **MEMORY.md / Graphiti** (semantic, stable, cross-session)
- The **temporal horizon of the query** is the primary routing signal — not the query content alone

**Practical gate (add to Self-Route gate, before existing steps):**

| Query temporal horizon | Primary surface |
|---|---|
| "Right now / today / this session" | Hindsight episodic recall |
| "Usually / generally / always / preference" | MEMORY.md or Graphiti entity nodes |
| "Last week / prior session / few months ago" | session_search |
| "Relationship between X and Y over time" | Graphiti temporal edges |

**Dual-store consolidation trigger:** when the same fact appears in Hindsight 3+ times across sessions with similar phrasing → it has crossed the horizon boundary from episodic to semantic → promote to MEMORY.md or Graphiti. This is the ForeDreamer episodic→semantic graduation criterion, matching the existing consolidation policy.

Reference: arXiv:2608.20920, "ForeDreamer: A Self-Evolving Dual-Agent Memory Architecture for Future Event Prediction", Aug 2026.

## Open Memory Spec — Typed Grain Model + No-Delete Constraint (OMS/CAL, HN Aug 2026)

The Open Memory Specification (memorygrain.org, github.com/openmemoryspec/oms) introduces two structurally distinct patterns:

**Typed grain model** — 10 first-class memory types beyond raw key-value or vector embeddings:
Belief, Event, State, Workflow, Action, Observation, Goal, Reasoning, Consensus, Consent.
The type determines trust, mutability, and expiry semantics. A Consent grain (user permission grant) has different immutability than an Observation (tool output). Belief grains carry explicit confidence levels and source attribution.

**CAL (Context Assembly Language) — structural append-only**: the grammar has no destructive operations. Deletions are impossible at the language level, not just by convention. This eliminates accidental memory overwrite bugs and makes every context assembly deterministic and replayable. Token-budget-aware assembly: CAL programs specify budget limits and the assembler truncates by priority, not by recency.

**Hermes translation**:
- Hermes already approximates this with tiered surfaces (MEMORY.md, session_search, Hindsight, Graphiti). The OMS grain type maps:
  - Belief → Hindsight retained facts (with confidence tag)
  - Consent → MEMORY.md entries tagged `user-confirmed`
  - Event → session_search (immutable transcript)
  - Workflow → skills
- The no-delete principle reinforces the existing rule: never remove a skill or memory without replacing it or documenting it was absorbed. Soft-deprecation (tag as `superseded`) over hard delete.

Reference: memorygrain.org, github.com/openmemoryspec/oms, HN Show HN Aug 2026.

---

## Goal
Keep durable facts small and high-signal in Hermes memory, use transcript search for prior conversations, and use Hindsight for episodic/cross-session semantic recall. Both qmd and MemPalace are disabled — route vault/project retrieval to `session_search`, Hindsight, or Obsidian files via `read_file`.

---

## Memory Policy Dominates Model Capability — Revalidate on Model Swap (AgingBench, Aug 2026)

AgingBench (arXiv:2605.26302): memory policy alone drove a **4.5× spread in agent half-life**. Upgrading Sonnet 4.6 → Opus 4.7 *dropped* PyTest pass rate by 15% in long-horizon sessions because the stronger model handled memory compression differently.

Rule: any model upgrade must be validated against the existing memory/compression policy on a real task sample before deployment. Do not assume a stronger model performs better on long-horizon tasks with an existing memory harness.

---

## Execution-Trace Memory + Attribution Namespacing (Memori, Aug 2026)

Two patterns from MemoriLabs/Memori (16.1k stars, explicit Hermes support):

1. **Memory from execution traces**: extract structured facts from *tool-call sequences* — what tools were called, in what order, with what results — not just from prose output. Implicit knowledge ("agent needed 3 retries → source is unreliable") that never appears in prose can still be captured. After a delegate_task completes, call `hindsight_retain` with the task's tool-call sequence summary, not just the final answer.

2. **Attribution namespacing**: tag memories with the profile, agent role, and task domain that generated them. Don't let subagent-generated facts overwrite user-session facts without a trust-tier check. Maps to: Graphiti `group_id` scoping + Hindsight bank selection.

---

## Rejected-Alternatives as a Distinct Memory Type (CommitLore, HN Aug 2026)

Conventional memory records what was decided. Rejected-alternatives memory records what was *considered and rejected* — without it, agents re-propose already-ruled-out alternatives ("groundhog day" loops).

When writing a Hindsight fact about a decision, add a companion entry tagged `["decision", "rejected-alternative"]` listing what was ruled out and why. When patching a skill, add `<!-- rejected-alts: [alt: reason] -->` comments so future passes know what was tried.

---

## MEMORY.md Injection Attack Surface (Memanto v0.2.15, Aug 2026)

Crafted Markdown in agent-written memory can inject instructions that execute when that memory is read back as context. Hermes: when writing to Hindsight/memory from tool output or web content, use structured fact format (entity/relation/fact) rather than raw-quoted text blocks. Never paste large unvalidated external text directly into a memory entry.

---

## Goldfish Syndrome — Validation of 3-Tier Design (CyberLeninka/RU, 2026)

Peer-reviewed Russian experimental validation: neither long context nor RAG-only provides durable working memory across session restarts (fact retention = 0 for both). The 3-tier agent-controlled architecture (session_search/Graphiti/skills+files in Hermes) achieves near-1.0 fact retention. Key principle: the *agent* initiates writes and decides what to retrieve — passive background injection does not substitute.

---

## Stage Separability for Retrieval Stack Decisions (CyberLeninka/RU, 2026)

Before adding a retrieval stage (e.g. Graphiti on top of session_search), measure Cohen's d between relevant/non-relevant score distributions. d > 0.5 = meaningful; d < 0.2 = redundant. Spearman correlation between adjacent stages detects when a new stage is just rescaling the same ranking. Only add stages that pass separability.

---

## Default decision order

**Retrieval surfaces** (query these to get information):
1. Hermes durable memory (`memory` tool) — stable preferences, env facts
2. `session_search` — **always-on**; prior conversation facts, FTS5 over `state.db` (not `sessions.db`)
3. ~~qmd (`mcp_qmd_*`)~~ — **DISABLED** (config `enabled: false`; Iris Xe VRAM constraint). Fall back to `session_search` for any task that would have used qmd.
4. Hindsight (`hindsight_recall` / `hindsight_reflect`) — **ENABLED** (local daemon `:9177`, cloud embeddings `text-embedding-3-small` 1536d) — episodic/cross-session semantic recall
5. Graphiti MCP (`mcp_graphiti_*`) — **ENABLED** (local MCP); entity/relationship queries; **graceful degrade**: if tools return connection error, fall back to `session_search` immediately (do not retry more than once)
6. ~~MemPalace~~ — **DISABLED**; qmd also disabled; use session_search + Hindsight for all local recall

**Write-path tools** (NOT retrieval surfaces — they feed the surfaces above):
7. `canvas-offload.py` — in-session tool output offload; compression+traceability; feeds session_search indirectly via disk refs
8. `l1-extract.py` — end-of-session fact extraction; feeds Hindsight (and eventually durable memory)
9. `memory_tencentdb` — installed, not yet active; adds L0-L3 pyramid + automated canvas offloading

> ⚠️ canvas-offload and l1-extract are write-path tools, not retrieval surfaces. Do not query them for information — use enabled retrieval surfaces 1, 2, 4, 5 (3 qmd and 6 MemPalace are disabled).

Choose the smallest surface that can answer the question well.

## Retrieval Strategy as Pluggable Skill (arXiv:2605.03989)

Retrieval strategy (which surface to query, how to rank results) is a skill not a hardcoded table.

When the default surface table produces poor recall, load a domain-specific retrieval strategy skill rather than patching the table.

The current surface table (hindsight -> session_search -> skill_view priority order) is the default; override per task class by loading a retrieval skill that re-orders the priority.

### memory_tencentdb status (2026-07-09)
Plugin installed at `~/.memory-tencentdb/`; symlinked as Hermes plugin; `hermes memory status` shows it.
Active provider is still **hindsight**. To activate:
1. Add to `~/.hermes/.env` (write-protected; edit manually):
   ```
   MEMORY_TENCENTDB_GATEWAY_HOST=127.0.0.1
   MEMORY_TENCENTDB_GATEWAY_PORT=8420
   TDAI_LLM_BASE_URL=https://api.anthropic.com/v1
   TDAI_LLM_MODEL=<configured cheap completion model; see tencentdb-agent-memory>
   TDAI_LLM_API_KEY=<same as ANTHROPIC_API_KEY>
   ```
2. Optionally add `"bm25": {"language": "en"}` to `~/.memory-tencentdb/memory-tdai/tdai-gateway.json` (defaults to Chinese tokenizer).
3. Set `memory.provider: memory_tencentdb` in config.yaml only after step 1 is done — circuit breaker trips on 5 consecutive gateway failures.
4. Verify: `curl http://127.0.0.1:8420/health` → `{"status":"ok"}` (gateway auto-starts on first Hermes turn).

**Env var naming split (pitfall):** plugin-side uses `MEMORY_TENCENTDB_*`; gateway process reads `TDAI_LLM_*`. Both must be set.
See `tencentdb-agent-memory` skill for full install guide and troubleshooting.

## Use Hermes durable memory for
- Stable user preferences
- Long-lived environment facts
- Recurring conventions the user should not have to repeat
- Small declarative facts that will still matter in weeks

Do not use Hermes durable memory for:
- task progress
- large notes
- bulk transcripts
- changing research findings
- raw document storage

## DREAM Intent Classification — Write Gate (arXiv:2608.09408, Aug 2026)

**Before calling `memory()`, `hindsight_retain()`, or any persistent write**, classify the fact at one of three intent levels:

| Level | Scope | Where to write | Examples |
|---|---|---|---|
| L0 Immediate | This tool call | Discard after acting | API response payload, ephemeral file path |
| L1 Session | This conversation | `session_search` context (implicit, via transcript) | Decision made today, temporary preference |
| L2 Long-term | Stable across weeks | `memory()` or `hindsight_retain()` | User preference, env fact, recurring convention |

**Rule:** Only L2 facts go to persistent memory. L1 facts live in the session transcript and are recoverable via `session_search`. L0 facts are acted on and discarded.

**Prevents:** MEMORY.md bloat from session-specific details (HIGH finding in every adversarial audit). If a fact will be stale in 7 days, it is L1 at best.

**Muscle Memory corollary (arXiv:2608.08995):** When a recurring user pattern appears >5 times with similar structure (e.g., same research workflow, same query shape, same tool sequence), it is an L2 *procedure*, not just a fact. Create a specialist skill via `skill_manage(action='create')` rather than cramming it into MEMORY.md. This is the "compile, don't retrieve" principle: 88.9% win rate vs standard retrieval, 22.8% of original profile token cost.

## Self-Route gate (run before any retrieval)

Classify the query before invoking any surface:

  A) Self-contained — answerable from current session → skip retrieval entirely
  B) Factual/temporal — "what command did I use", "what did I decide" → session_search
  C) Relational — "how do X and Y relate", "what changed since" → Graphiti
  D) Document/note — research notes, vault content → session_search + Hindsight (qmd DISABLED)

If ambiguous, add a routing prefix: "Classify this query as A/B/C/D in one word."

**Librarian pattern** (from taOSmd / taOS, Jul 2026):
In automated or multi-agent pipelines, treat retrieval routing as an explicit pipeline
stage rather than agent knowledge. Before any memory query, run a micro-pass:

  1. Parse intent: what is the query actually asking for? (fact / relationship / document / session)
  2. Classify: map to surface (A/B/C/D above)
  3. Expand query if needed: for complex/multi-hop questions, generate 2-3 variant phrasings
     or targeted clues before executing the search (see MemoRAG clue pre-pass below)
  4. Execute on the selected surface

In Hermes CLI sessions this is done manually by loading this skill and applying the gate.
In multi-agent pipelines with a retrieval step, make this a named stage in the pipeline
rather than ad-hoc per-agent logic — one retrieval agent applies the Librarian pass
centrally rather than each worker running its own uncoordinated query.

### MemoRAG clue pre-pass (for type C queries)

Before firing a Graphiti relational query on a complex or multi-hop question ("what
did we decide about X", "how does Y relate to Z", "what changed between sessions"),
generate explicit memory clues first:

  Prompt: "Given this question: <Q>, list 3-5 specific clues — entity names,
  timeframes, or relationship types — that would identify the most relevant stored facts."

Then use each clue as a separate targeted `mcp_graphiti_search_memory_facts` call.
This is structurally different from HyDE (hypothetical answer doc → embed → search);
MemoRAG clues are search directives that surface relational facts HyDE misses.
Cost: ~300 tokens. Skip for direct factual lookups where a search term is obvious.
(MemoRAG, arXiv:2409.05591, WebConf 2025)
~20 token overhead; saves thousands in unnecessary RAG injection.
(Self-Route, arXiv:2407.16833, EMNLP 2024)

## 3-Signal Context Locality (arXiv:2609.00148)

Before buying context from a retrieval surface, check locality. Three signals:

1. Before any `hindsight_recall` or `session_search` call: **scan the last 5 tool results** for the answer first.
2. Before any `read_file` on a path **already read this turn**: use cached content; do not re-read.
3. Before any `web_extract` on a URL **already extracted this turn**: skip and use the prior result.

**Re-buy** = redundant retrieval of data already in context. Target re-buy rate **≤ 10% per session**.

When skipping a redundant retrieval, **log the re-buy event** (which surface was skipped, which prior result was reused). High re-buy is a compaction-survival failure, not a missing-memory problem. Complements Self-Route class A (skip retrieval when session-local).

## Use `session_search` for
- "What did we decide about X?"
- finding prior attempts, errors, or resolutions from old chats
- recovering context before asking the user to repeat themselves
- reconstructing continuity when the user asks "where did we get to", especially after context compaction or interrupted multi-step work

Prefer this before adding new durable memory when the fact may already exist in prior session history.

## `session_search` continuity reconstruction pattern
When the user asks where prior work stopped:

1. Run a narrow discovery query for the topic.
2. Open the best matching session by `session_id`.
3. If the session contains compaction summaries, treat them as leads and corroborate with nearby turns.
4. Summarize: what was discovered, what was changed, what remained pending.
5. Preserve important distinctions (e.g. "Hermes-side integration" vs "upstream product installed and running").

### Verify claimed completions against real artifacts before resuming
A compaction summary's "Completed Actions" list is a self-report from a prior turn, not
proof. It can describe work on the *wrong topic entirely* (e.g. the summary says a skill
was patched, but the user actually meant a different session about an unrelated proposal
document) and it can claim a deliverable exists that was never actually written.

Before treating a compacted summary as ground truth and resuming from it:
1. If the summary claims a file/document/artifact was produced, check the filesystem for
   it directly (`search_files`) rather than trusting the "Active State" / "Relevant Files"
   section. An empty search result means the claimed work never landed on disk.
2. If the user says "no, I meant X" after a summary-driven guess, treat that as a hard signal
   the compaction picked the wrong session — re-run discovery with the user's own words
   before re-reading the same session again.
3. Once the right session is found, scroll to the actual message content (not just the
   summary) to recover the real task state: what was transcribed/decided, and — critically —
   whether the task was ever asked to completion or died mid-step (e.g. stopped right after
   a data-gathering phase, before any synthesis/output phase ran).

### Install-status and Firefox history patterns
See `references/install-inventory-pattern.md` for full detail on:
- inventory classification buckets
- Firefox `places.sqlite` lookup
- provenance discipline (explicitly requested vs merely browsed)

## Use `session_search` or Hindsight for local knowledge (qmd disabled)

qmd is currently disabled (config `enabled: false`). When the skill previously said "use qmd for curated local notes", route those queries to `session_search` (FTS5 for exact terms) or `hindsight_recall` (semantic/episodic) instead. Do not attempt to call `mcp_qmd_*` tools — they will fail silently.

When qmd is re-enabled, it covers:
- curated local notes and documents
- Obsidian/vault-style knowledge bases
- page/heading/path-oriented retrieval
- workflows where the canonical answer should live in a maintained document



## MemPalace — DISABLED (config enabled: false). QMD also disabled (Iris Xe VRAM).
Both disabled — route all vault/archive recall to `session_search` + `hindsight_recall`. Do not call `mcp_qmd_*` or MemPalace tools.

## Use Graphiti for
- "What tools does project X use?" — entity/relationship queries
- "How does component A connect to component B?" — typed graph traversal
- Incrementally capturing structured relationship facts from sessions
- Temporal facts: when was something added, what changed

Do NOT use Graphiti for:
- Bulk historical ingestion (433+ vault notes → noisy entities; Hindsight covers semantic recall)
- Simple key-value preferences (use durable memory instead)
- Full-text recall (use Hindsight or session_search)

Graphiti group_id convention: use `hermes` for Hermes-stack facts, `hermes-reasoning` for reasoning/planning artifacts.

### Graphiti advanced retrieval patterns (activate these — they are underused)

**1. Graph-neighborhood retrieval (center_node_uuid)**
When you already know the relevant entity (e.g. from a prior `search_nodes`), pass its uuid as `center_node_uuid` in `search_memory_facts`. This biases results toward edges touching that node, surfacing related facts that a pure semantic query would miss.

Pattern:
```python
# Step 1: find the entity node
nodes = mcp_graphiti_search_nodes(query="Graphiti", group_ids="hermes")
node_uuid = nodes[0]["uuid"]

# Step 2: retrieve neighborhood facts, biased to that node
facts = mcp_graphiti_search_memory_facts(
    query="embeddings configuration",
    center_node_uuid=node_uuid,
    group_ids="hermes",
    max_facts=8
)
```

Use when: you know the topic entity and want all related facts, not just the closest semantic matches.

**2. Community summaries (build_communities)**
Run `mcp_graphiti_build_communities(group_ids="hermes")` periodically (e.g. after a major work session or memory consolidation pass). This clusters densely-connected entities into higher-level summaries that are themselves queryable.

Trigger: after adding 5+ new episodes in a session, or at the start of a new project arc.
Note: the graph needs sufficient node/edge density (typically 10+ nodes) before Graphiti produces non-empty communities.

**3. Saga tracking for session arcs**
Use `saga=` in `add_memory` to group related episodes under a named arc. Then call `mcp_graphiti_summarize_saga` to get a running narrative across that arc. Useful for multi-session work on a single project.

Pattern:
```python
# Opening episode
mcp_graphiti_add_memory(
    name="Session start",
    episode_body="...",
    group_id="hermes",
    saga="project-arc-YYYY-MM-DD"
)

# Later: get arc summary
mcp_graphiti_summarize_saga(saga_name="project-arc-YYYY-MM-DD", group_id="hermes")
```

Note: the saga episode is processed asynchronously — wait a few seconds before calling summarize_saga or it will report not found. One saga per major project arc is enough; don't create a saga per session.

## Local symbolic memory scripts

These are **write-path** tools that compress context and stage facts for promotion — they are not retrieval surfaces.

### canvas-offload.py
**When to use:**
- Long agentic loops (5+ tool calls) where raw outputs bloat context
- More than 3 large tool outputs accumulated in session
- Traceability needed: you must be able to re-inspect exact tool output later
- Prefer over `/compress` when drill-down into a specific operation will be needed

**When to use `/compress` instead:**
- Clean task break — no need to drill back into individual tool outputs
- One-off context reduction where losing raw output is acceptable

**What it produces:** `~/.hermes/canvas/<session_id>/canvas.md` (Mermaid graph) + `refs/<node_id>.md` (raw blobs). Canvas must be explicitly injected into context — it is not automatic.

**Upward connection:** canvas refs are readable by the agent on demand; they do not flow to Hindsight or durable memory automatically. They inform `session_search` indirectly through the session record.

### l1-extract.py
**When to use:**
- End of a session with 5+ substantive turns
- Periodic cron to build cross-session knowledge base
- Before closing a session where facts should survive beyond session_search

**What it produces:** `~/.hermes/memory-facts/YYYY-MM-DD.md` — raw atomic facts, human-readable.

**Promotion path:** `l1-extract.py → memory-facts/ → l1-promote.py → staging.md → l1-hindsight-promote cron → Hindsight`. Manual: `hindsight_retain(content="...", context="l1-extract", tags=["l1"])` for facts scoring ≥2. See `symbolic-context-offload` skill for full detail.

### Graphiti graceful degradation
If any `mcp_graphiti_*` call returns a connection error:
1. Fall back to `session_search` for the same relational query.
2. Do not retry Graphiti more than once per session.
3. Note the outage; Graphiti needs manual start (`hermes memory status` will show it offline).

---

## Memory Portability on Model Upgrade (arXiv:2609.05339)

KG-fixed memory transfers reliably across model upgrades (±0.002 accuracy delta). Compressed NOTES degrade 9-13pp on model swap. RAG degradation on upgrade is 81% retrieval-driven. Always retain raw source histories alongside summaries. Direction-specific migration testing is required.

- **Prefer KG-fixed schema over compressed NOTES for long-lived facts** — facts that must survive model version changes belong in Graphiti (KG-fixed), not in compressed NOTES entries. NOTES lose 9-13pp accuracy on model swap — treat them as volatile, not durable.
- **Always keep raw source text alongside any compressed summary** — store a `source_text` field (truncated to 500 chars) alongside every compressed note. This enables memory repair after model upgrades without re-generating from scratch.
- **On any model upgrade: test memory retrieval accuracy in both directions** — test upgrade direction (old model → new model) AND downgrade direction (new → old) before going live. Accuracy deltas differ per direction.
- **Embed `model_version` tag in Graphiti episode metadata** — so stale embeddings generated under a prior model version can be identified and reprocessed after a model swap. Pattern: `metadata={"model_version": "claude-sonnet-4-6"}` in `mcp_graphiti_add_memory` calls.
- **NOTES (compressed summaries) are volatile, not durable** — they lose 9-13pp accuracy on model swap. Any fact critical enough to influence future reasoning should be in KG-fixed Graphiti, not in a Hindsight compressed note.
- **RAG degradation on upgrade is 81% retrieval-driven** — when switching models, re-embed your Hindsight/ChromaDB index after the switch. Do not assume old embeddings remain valid under a new model's embedding space.

Reference: arXiv:2609.05339, "Memory Portability on Model Upgrade", 2026.

## Memory Retention Policy

- **Reuse-weighted retention (ECHO, arXiv:2606.31650)**: memory facts that are retrieved frequently (access_count >= 2 in lifecycle.db) earn +7d TTL per access above threshold, capped at +28d. Frequently-used facts should not expire on a fixed calendar schedule.

- **Probing gate before memory retention (arXiv:2609.11060, Environment-Probing Curation):** Before retaining a new memory fact about a concrete artifact (file path, config key, API endpoint, version string), verify the fact is still current via a read-only check. Stale facts about changed environments cause 2.3x higher task failure rate. Check: `os.path.exists(path)` for file paths; `git ls-remote` for repo URLs; `hermes config get` for config keys. Only retain if probe confirms currency. Facts about abstract patterns (e.g. "use X approach for Y task type") do not require probing — only facts about concrete, changeable world state.

- **Event-centric clustering before bulk retrieval (MemForest, arXiv:2609.08273):** When `fuse_results` returns >10 items for a query, check if multiple results share the same time window (±24h) and topic cluster. If yes, reduce to the most-accessed representative per cluster before presenting. This prevents the context from being dominated by correlated memories about the same event.

- Robust Trust weighting (arXiv:2602.09490): _TRUST_WEIGHTS {internal:1.0, cron:0.85, external:0.70} are p-alignment probabilities; trust-region radius = p/(1-p); updating requires evidence that a source class has systematically drifted, not just one bad result.

## Unified Gateway: Joint Routing + Cache (arXiv:2609.06940)
For each Hermes tool call: treat model selection and memory-cache lookup as a JOINT decision, not sequential.
Taxonomy:
  ROUTE        — send to model; no cache available or cache confidence too low
  CACHE-HIT    — serve from recall-experience-cache.json (cosine>0.85, age<3600s)
  CACHE-MISS-POPULATE — route to model AND write experience-edge entry
  EVICT        — drop entries when cache >100 entries (LRU)
Optimisation objective: min(latency + 0.3*cost) subject to quality >= threshold
Hermes mapping: 'routing' = model selection via claude-routing-hierarchy skill; 'cache' = recall-experience-cache.json (VikingRAG); joint decision point = unified-recall.py main() before Hindsight/Graphiti calls.

---

## Memory stack health check
```bash
hermes memory status                              # active provider + plugin list
curl -s --max-time 3 http://127.0.0.1:8765/mcp/; echo "exit:$?"  # Graphiti: exit 0=up, refused=down
systemctl --user is-active graphiti-mcp.service  # Graphiti service state
ss -tlnp | grep 8765                             # Graphiti port listener
tail -20 ~/.hermes/logs/hindsight-embed.log      # Hindsight daemon: look for "started successfully" vs ValueError
python3 ~/.hermes/scripts/l1-extract.py --show   # today's l1 facts
ls ~/.hermes/canvas/                              # canvas sessions on disk
cat ~/.hermes/memory-facts/INDEX.md              # extraction history
```

Note: `curl` to the Graphiti MCP endpoint returns an empty body (exit 0) when the server is up — that's expected. Connection refused = server is down.

---

## FAMA — Forgetting-Aware Memory Accuracy (ACL 2026.findings-acl.1337)

Memory agents lose value when they retrieve STALE or INVALIDATED facts and treat them as
current. FAMA penalizes this explicitly.

**Classify each recalled fact before acting on it:**
- `preference` (stable) — low staleness risk; can use directly
- `config_value` (may change) — check against live config before acting
- `event` (stable but may be superseded) — cross-check session_search for newer events

**Invalidation discipline:**
- When a newer fact supersedes an existing memory entry, add: `Invalidated by: <date> <what>`
- memory tool: remove + add atomically in one batch op; never just add a contradiction

**Staleness audit (after ~30 turns):** `hindsight_reflect("is X still accurate?")` for volatile facts.

## Wiki Memory Layer — 4th Retrieval Surface (LangChain blog, Aug 2026)

Distinct from Hindsight (vector), session_search (FTS5), and MEMORY.md (persistent facts).
Use for pre-computed domain knowledge the agent re-discovers from scratch each session.

Implementation — no new infrastructure needed:
- Location: `~/.hermes/wiki/<domain>/` YAML-frontmatter `.md` files
- Format: headers + bullet facts + cross-refs (agent-readable, not prose narrative)
- Create/update: `"given these raw logs/docs, upsert these wiki pages"`
- Search: FTS5 on wiki files alongside existing session_search
- Inject: top-3 page summaries at session start for known domains

Domains worth a wiki: `ppor` (property search), `religion-kg` (corpus schema), `trading` (rules)

## Anthropic Native Memory Tool — BetaLocalFilesystemMemoryTool (Anthropic SDK beta, Aug 2026)

`BetaLocalFilesystemMemoryTool(base_path="~/.hermes/agent-memory/")` — filesystem-backed
cross-session memory in the Anthropic SDK. Best for: cross-session project state that must
survive context compaction when Hindsight/Graphiti are unavailable. Use alongside (not
instead of) Hindsight for long-term structured facts. Beta — may change; test before relying on in production.

## LLMA-Mem — Non-Monotonic Team Scaling (arXiv:2606.06447)

Multi-agent teams with poor memory topology perform WORSE than solo agents with good memory.
Small team + good memory > large team + bad memory.

**Memory topology quality gate — run before delegate_task fan-out:**
1. Does the existing agent have the right facts at each step? (check Hindsight/session_search first)
2. Can a single agent answer this if memory is better-organized?
3. Only add a subagent if genuinely parallelizable AND memory is already well-organized
4. Pre-commit shared facts to Graphiti group_id or Hindsight BEFORE dispatch

## Decision rules
- If the fact should auto-influence future chats and fits in one compact sentence, save it to Hermes durable memory.
- If the answer probably exists in a past Hermes conversation, use `session_search` first.
- If the answer belongs to a maintained local document or vault note, use session_search / Hindsight / Obsidian files directly (qmd DISABLED).
- If the fact is episodic/cross-session and not yet in durable memory, use `hindsight_recall`.
- If the query involves entity relationships or temporal graph facts, use Graphiti (fall back to session_search if Graphiti is down).
- If context is bloating from large tool outputs and traceability matters, use canvas-offload.py.
- If the session is ending and facts should survive, run l1-extract.py then promote ≥2-scoring facts to Hindsight.
- MemPalace and qmd are both disabled; route vault recall to session_search, Hindsight, or Obsidian files via read_file.

## AMD — Agent Memory Distillation, three memory types (arXiv:2608.07169, Sweep 12)

**Source:** Agent Memory Distillation (AMD), arXiv:2608.07169 — not "Adaptive Memory Distribution".

AMD distills teacher trajectories into three student memory types injected at different points:

| Tier | Content | When injected | Why |
|------|---------|---------------|-----|
| Workflow memory | Task-class procedures, skill templates | Task START (proactive) | Available before any tool call |
| Subtask memory | Step-specific instructions and context | Each subtask START (proactive) | Reduces mid-task context search |
| Function memory | Tool-specific parameters, API quirks | Tool ERROR (reactive) | Only loaded when error occurs |

**Key finding:** +27.2pp AppWorld, +11.2pp BFCL, +3.4pp ToolSandbox vs no memory. Reactive function-memory injection avoids bloating context with rarely-needed tool-call details until an error occurs.

**Hermes implementation:**
- Workflow memory = skill loading at task start (already implemented via skill_view triggers)
- Subtask memory = session context injected per subtask in delegate_task context field (improve this)
- Function memory = load tool-specific references only after a tool error occurs

AMD injection gating: default to L0 (skill_view results only); escalate to L1 after 1+ tool errors this session; escalate to L2 after 3+ tool errors. Policy hook: `unified-recall.py:get_injection_tier` (s19-amd).

Same paper (`arXiv:2608.07169`) is mapped in `agent-memory-consolidation` as Proactive (this skill) / Reactive (`hindsight_recall`) / Skill (skill-authoring). That is the *promotion-loop* mapping. This table is the *in-task injection* mapping (workflow / subtask / function). Do not treat the two 3-tier namings as competing procedures for the same action.

**Apply this to delegate_task task design:**
```
# WRONG: front-load everything
context="Here is everything about web_extract, browser tools, all known pitfalls..."

# RIGHT: adaptive injection
context="For web extraction: use web_extract by default. If it fails with bot-block, load 
the anti-bot fallback from domain-research-synthesis skill's pitfall section."
```


*LLMA-Mem: Non-Monotonic Team Scaling (arXiv:2606.06447) — see references/llma-mem-research.md.*
## MEMTIER 5-Signal Retrieval Weighting (arXiv:2605.03675, Aug 2026)

MEMTIER (Sidik & Rokach, under review) showed +33pp accuracy (LongMemEval-S: 0.050→0.382)
on a 6GB GPU by using a five-signal weighted retrieval scoring function instead of
single-signal cosine similarity. The five signals and their relative weights:

| Signal | What it measures | Weight (approximate) |
|--------|-----------------|---------------------|
| Semantic similarity | Embedding cosine distance | 0.30 |
| Recency | Time since episode was created | 0.25 |
| Relevance (BM25) | Keyword overlap with query | 0.20 |
| Importance | Tagged importance at write time | 0.15 |
| Usage frequency | How often this entry has been retrieved | 0.10 |

**PPO-based adaptation**: MEMTIER learns to adjust weights based on task outcomes.
Hermes approximation: manually increase the recency weight (→0.35) for time-sensitive
queries (current config, recent decisions); increase semantic weight (→0.45) for
conceptual/abstract queries; increase BM25 weight (→0.30) for queries with specific
entity names or technical terms (adapts the vstash adaptive IDF rule below).

**Cognitive weight decay**: MEMTIER applies attention-based decay to retrieval weights —
entries that were relevant but never acted upon decay faster than entries that triggered
decisions. In Hermes terms: if a Hindsight entry was recalled in a session but didn't
influence any action, treat it as a lower-signal entry on the next recall.

**Async consolidation daemon**: MEMTIER runs a background daemon that promotes
episodic → semantic tier asynchronously. Hermes equivalent: the l1-promote.py cron.
The key finding is that synchronous promotion during the agent loop degrades latency
significantly; the async model is correct for production use.

## vstash: local-first hybrid retrieval with adaptive IDF-weighted RRF (arXiv 2604.15484)

vstash (Jayson Steffens, independent researcher): pure SQLite stack for hybrid retrieval.
- sqlite-vec (ANN vector search) + FTS5 (BM25 keyword) + adaptive per-query IDF RRF
- Self-supervised embedding refinement on disagreement triples (no human labels)
- **+21.4% NDCG@10** (ArguAna); **+19.5% NDCG@10** fine-tuned BGE-small (NFCorpus)
- 20.9ms median at 50K chunks — same latency class as Hermes session_search

Hermes surface selection update for hybrid queries:

When to use which surface for retrieval:

| Query type | Recommended surface | Why |
|------------|--------------------|----|
| Specific entity/name/date | session_search (FTS5) | BM25 handles specific terms better than dense vectors |
| Conceptual/semantic query | hindsight_recall (ChromaDB) | Dense vectors handle paraphrase/concept |
| Both specific + conceptual | vstash-style adaptive RRF | Weight FTS5 higher for rare query terms |
| KG relationship query | graphiti search_memory_facts | Structured entity-edge traversal |
| Multi-hop / connected facts | graphiti + KG2RAG expansion | Traverse KG neighborhood for related facts |

Adaptive IDF weight rule (from vstash):
- Count query terms with len > 5 characters (proxy for specificity)
- idf_weight = 0.3 + n_specific_terms * 0.1, capped at 0.8
- vec_weight = 1 - idf_weight
- Short specific queries (e.g. "MemOS group_id API") → idf_weight 0.8, vec_weight 0.2
- Long conceptual queries → idf_weight 0.3, vec_weight 0.7

NEGATIVE result from vstash: post-RRF reranking (frequency+decay, cross-encoder,
history-augmented recall) ALL failed to improve NDCG. Do not add reranking on top of
adaptive RRF — the gains disappear and you pay extra latency.

## MemOS L1→L4 tiered memory promotion (MemTensor pattern)

MemOS defines a 4-tier hierarchy with explicit promotion rules between tiers. Apply this
discipline to keep Graphiti/Hindsight lean and prevent tier-confusion.

| Tier | What it holds | Hermes surface | Promotion trigger |
|---|---|---|---|
| L1 traces | Raw episode logs, tool outputs, conversation turns | session_search | Any session event |
| L2 policies | Derived rules from repeated L1 patterns | Hindsight (tagged `policy`) | Same pattern in 3+ L1 episodes |
| L3 world model | Synthesized entity/relationship facts | Graphiti (group `hermes`) | Fact confirmed in 2+ sessions |
| L4 skills | Crystallized procedures and workflows | SKILL.md files | Pattern stable, reused 3+ times |

**Promotion discipline:**
- L1→L2: when a pattern appears in 3+ raw episodes, extract the rule and retain in Hindsight
- L2→L3: when a policy has been relied upon in 2+ distinct sessions, write to Graphiti
- L3→L4: when a procedure is stable and reused 3+ times, patch or create a SKILL.md
- Demotion: when a L3 fact has not been recalled in 90+ days, demote to L2 (Hindsight)

**Why this matters:** Conflating tiers wastes tokens. A raw episode in MEMORY.md
(L1 in L4 position) inflates the always-injected budget. A stable procedure only in
Hindsight (L4 in L2 position) forces re-derivation on every session.

**FTS5 + vector hybrid retrieval (MemOS pattern):**
MemOS uses FTS5 full-text search alongside vector similarity to improve recall.
Keyword search catches entity names, dates, exact phrases that semantic search misses.
In Hermes: `session_search` already uses FTS5; Graphiti uses vector. When retrieval
quality is low on a factual query with specific entity names, run BOTH:
```python
# Parallel: FTS5 for exact matches + Graphiti for semantic/relational
session_results = mcp_session_search(query="exact entity name")  # FTS5
graph_results = mcp_graphiti_search_memory_facts(query="entity context")  # vector+graph
# Merge: prefer Graphiti for relationships, session_search for verbatim facts
```

## Letta MemFS memory partitioning (load-tier discipline)

Letta/MemGPT's MemFS pattern introduces a clean three-tier memory loading discipline
that maps well onto this stack. Apply these tiers when deciding how memory should be
structured for a complex multi-session project:

| MemFS tier | Load behavior | Hermes equivalent |
|---|---|---|
| `system/` | Always loaded, every turn | MEMORY.md / USER.md (durable memory) |
| `reference/` | Load on demand (agent calls `load_memory(path)`) | Hindsight recall on explicit query |
| `archival/` | Search-only, never directly loaded | session_search / Graphiti / ChromaDB corpora |

**Key discipline from MemFS:**
- `system/` must stay small — it is in-context every turn, so every byte costs tokens.
  Mirrors the 3-axis importance filter already in place for MEMORY.md.
- `reference/` is loaded only when the agent explicitly needs it — not speculatively.
  Applying this to Hermes: don't pre-load Hindsight entries at session start; call
  `hindsight_recall` only when the question specifically requires it.
- `archival/` is never "loaded" — it is only searched. Do not inject Graphiti episodes
  or ChromaDB chunks into context directly; always search and inject only the top-k results.

**Agentic memory access tools** (Letta pattern, applicable here):
The agent itself decides when to call memory tools rather than having them auto-injected.
In Hermes terms: `hindsight_recall`, `mcp_graphiti_search_memory_facts`, and `session_search`
are already gated tools — call them when the task requires them, not pre-emptively every turn.

**Per-agent memory partitioning** (MemOS pattern):
When running parallel subagents (delegate_task fan-out), give each subagent its own
Graphiti group_id rather than sharing `hermes`. This prevents episodic noise from one
agent's run polluting another agent's retrieval:
```python
# Each subagent uses its own namespace
mcp_graphiti_add_memory(episode_body="...", group_id="hermes-agent-research-2026-07-28")
# World-model facts still go to the shared namespace
mcp_graphiti_add_memory(episode_body="...", group_id="hermes")
```
Read-access to the shared namespace is additive: subagents can query both their own
group_id AND `hermes` in the same call: `group_ids=["hermes", "hermes-agent-research-2026-07-28"]`.

## Project-scoped memory and the clarification_needed pattern

Hermes memory surfaces are user-global. When a task involves project-local context
(design decisions, conventions, architecture choices tied to a specific repo), the
closest fit is:
- **QMD / Obsidian** for curated project notes (manually maintained)
- **Graphiti** with a project-specific group_id for structured entity/relationship facts
  (established group_ids: `hermes`, `hermes-reasoning`, `hermes-projects-*`, and ephemeral
  `hermes-agent-<task-id>` for parallel fan-outs — see `graphiti-mcp-setup` Group ID taxonomy)
- **Hindsight** with project-scoped tags for episodic facts

There is no `.curion/`-style per-repo private store in this stack. This is intentional:
single-user personal workflows don't need contributor-portable repo-local isolation.

**Clarification_needed forwarding contract** (pattern from Curion, extractable):
When a memory retrieval is uncertain or the stored facts are insufficient to answer
reliably, the correct agent behavior is to surface a `clarification_needed` signal
and forward a specific question verbatim to the user rather than guessing or hallucinating.

In practice in Hermes:
- If `hindsight_recall` / `graphiti_search_memory_facts` return `weak_match` or empty,
  do NOT synthesize an answer from weak signals. State uncertainty explicitly.
- If the user is the only reliable source for a fact, ask them directly rather than
  pretending the memory layer has it.
- When writing a Hermes skill that wraps a memory lookup, consider including an explicit
  "no-answer path" that asks the user rather than defaulting to a best-guess.

**Normalize-before-persist discipline** (pattern from Curion, extractable):
Never write raw user input or raw tool output into durable memory. Pass through a
normalizing step first: extract the meaningful summary, assign metadata (topic, confidence,
source, timestamp), then write the compact form. Raw transcripts belong in session_search,
not in durable memory. This is what the 3-axis filter already enforces — the pattern name
to remember is "normalize before persist."


*Session-Settled Decisions pattern — see references/session-settled-decisions.md.*
## Hindsight write discipline, TTL, and cross-stack dedup

Hindsight is not a free dump surface. Entries with low signal degrade relevance injection quality.

**Before writing to any memory surface, check for cross-stack duplication:**
1. Is this fact already in MEMORY.md / USER.md? → do not duplicate in Hindsight.
2. Is this an entity relationship or temporal fact? → Graphiti is the right store; skip Hindsight.
3. Is this a session-specific outcome (PR number, commit SHA, build result, ouroboros job ID)? → session_search covers it; skip all stores.
Only write to Hindsight if the fact survives the above and scores 2+ on the 3-axis filter below.

**Write filter (3-axis score — same as durable memory):**
Apply the Recency/Utility/Uniqueness filter before calling `hindsight_retain`.
Threshold: score ≥ 2. Entries scoring 0–1 should be dropped, not staged.
Hindsight is for "high-importance but single-session" facts waiting to cross the falsification
gate into durable memory — not for raw episode transcripts or task outputs.

**TTL / pruning:**
Hindsight has no auto-expiry. Manually prune when:
- A Hindsight entry has graduated to durable memory (no longer needs staging)
- A fact it describes was superseded (config changed, service removed, PR closed)
- The bank grows noisy — check relevance quality on a few searches as a signal

No formal schedule required; prune reactively when you notice staleness. Add pruning as
a step in the agent-memory-consolidation flow for complex multi-session tasks.

**Categories that should never be in Hindsight (prune on sight):**
- PR/issue/commit/job IDs and their outcomes (covered by session_search)
- Build results, test pass/fail counts, Ouroboros session artifacts
- Temporary config states that were reverted the same session
- Any entry that duplicates MEMORY.md or a Graphiti entity verbatim
- Tool version pinnings for one-off installs not part of the permanent stack

## Importance-weighted write filter (when to write to durable memory)

Before saving anything to Hermes durable memory, score it on three axes:

**Recency** — Will this fact be relevant in 30+ days? (score 0=no, 1=yes)
**Utility** — If missing, would the agent be forced to re-ask the user or re-discover it? (0=no, 1=yes)
**Uniqueness** — Is this fact not already captured elsewhere in memory or an active skill? (0=no, 1=yes)

Write threshold: total score ≥ 2. Anything scoring 0 or 1 should go to session notes (Hindsight or Obsidian) instead, or be skipped entirely.

Examples:
- "User prefers DD/MM/YYYY" → Recency 1, Utility 1, Uniqueness 1 → write
- "API call succeeded this time" → Recency 0, Utility 0, Uniqueness 0 → skip
- "Current PR is #847" → Recency 0 → skip (stale in 7 days)
- "Firecrawl runs at port 3002" → Recency 1, Utility 1, Uniqueness 1 → write

This mirrors the multi-signal scoring from Generative Agents (2023) and ExpeL (2024): recency × relevance × importance weighting prevents both under-storing (missing critical facts) and over-storing (memory bloat that dilutes attention).

## Episodic → semantic consolidation policy

Episodic records (session history, individual task outcomes) should graduate to semantic (durable) memory when a pattern repeats across 2+ independent sessions. Do NOT promote on a single observation — this is the falsification gate.

Signs a pattern is ready for promotion:
- The same correction was applied in 2+ separate sessions
- The same tool quirk was encountered and worked around 2+ times
- The user expressed the same preference in different contexts
- A procedure succeeded the same way on 2+ different tasks

When promoting, synthesize the episodic raw form into a compact semantic form:
- Episodic: "In session X, API call to Y failed unless timeout=30 was set. Same in session Z."
- Semantic (durable memory): "Tool Y: always set timeout=30 or calls fail silently."

Never write the episodic form into durable memory. Compress it first.

## Contradiction and staleness detection

Before writing a new durable memory entry, check whether it conflicts with an existing one:
1. Scan current MEMORY.md and USER.md for the same entity/topic.
2. If a conflicting entry exists, resolve it: update the old entry rather than appending a contradiction.
3. For facts with implicit expiry (software versions, port numbers, PR/issue numbers), add a mental TTL: if older than ~90 days and not verified recently, treat as suspect.

When a fact is found stale or contradicted during a task, retract/supersede the old entry (keep a trail; see ChronoMem below) rather than leaving two live contradictory facts or silently deleting with no audit trail.

## ChronoMem — Versioned Rollback, Not Forward-Only Overwrite (arXiv:2607.27773) <!-- why: after later facts land, silent overwrite of an earlier entity loses inspect/revert; user correction is rollback of a version, not a new topic write -->

Agent memory that only accumulates, consolidates, and overwrites is brittle under
corrections, concept drift, and poisoning: once later facts have been written, there is
no principled way to inspect or revert the prior state (ChronoMem).

**Hermes rule — treat user/operator correction as rollback of a version:**
1. If the user says a stored fact is wrong, retract *that write* (entity + timestamp),
   do not append a second fact on the same topic and do not globally rewrite the topic.
2. Keep the superseded text marked retracted (do not silently delete without a trail) so
   a later "undo the undo" or audit can find it.
3. After other facts have been written on related entities, do not overwrite the old
   row in place — `memory(action='replace')` the specific contradicted span only.
4. Never revive a retracted fact from raw session logs without a fresh user confirm.

Do not add a snapshot database. This is a write-discipline rule, not a new memory store.

## Implicit-Association Blind Spot (arXiv:2607.24368, InMind benchmark, Jul 2026)

Vector retrieval systems — including Hindsight — have a structural failure mode on indirect queries:
when the query "macaron recipe" should surface a stored "tree-nut allergy" fact (via almond flour),
retrieval misses it because the texts share no cue the retriever can see. Six tested memory systems
reached at most 14.4% on indirect queries, even when they recalled the same facts directly at 100%.

**Hermes mitigation — two-level visibility strategy:**

1. **Always-visible tier** (MEMORY.md / USER.md): stable, domain-crossing facts that would be
   missed by indirect retrieval — user constraints, permanent preferences, cross-domain rules.
   The 3-axis importance filter (Recency/Utility/Uniqueness) should bias toward writing facts
   here when they have implicit cross-domain effects (e.g. dietary restrictions, security
   constraints, hardware limits).

2. **Retrieved tier** (Hindsight): task-specific, session-specific, or time-bounded facts.
   When doing a domain-specific task, supplement `hindsight_recall(query)` with *adjacent*
   broader searches — e.g. for a cooking task, also search "food allergy preferences" explicitly,
   not only "macaron recipe".

3. **Routing heuristic**: before a high-stakes action, run 2-3 Hindsight recall queries with
   different angles on the task (not just the literal goal) to surface indirect associations.
   Add this step to ATP pre-checks (mnemosyne-atp-safety Step 1).

## Self-Knowledge Query Expansion for Memory Retrieval (arXiv:2608.11030, Aug 2026)

Standard vector retrieval fails on implicit associations (InMind benchmark, see above).
A complementary fix: before calling `hindsight_recall(query)`, expand the query by extracting
entity types and related concepts from the literal query text.

**Pattern (Self-Knowledge RAG):**
1. Take the task goal: "write a macaron recipe"
2. Extract entities: food item → macaron → ingredients → almond flour, sugar, eggs
3. Expand query pool: ["macaron", "almond flour", "nut allergy", "baking constraints", "food preferences"]
4. Run `hindsight_recall()` for each expanded term; union results; deduplicate
5. Present the expanded recall to the model before generating the response

**Hermes implementation:**
- For high-stakes tasks (anything involving user health, finance, security, or irreversible actions),
  run a haiku query-expansion call first: "Extract 3-5 entity types and related concepts from: [goal]"
  then run `hindsight_recall()` with each expanded term.
- For routine tasks, single `hindsight_recall(goal)` is sufficient.
- The Graphiti KG already stores entity relationships and is better suited to bridging implicit
  associations than flat Hindsight recall — prefer Graphiti entity graph traversal when an
  implicit connection is suspected (e.g. user profile → constraints → current task domain).

**Source:** InMind benchmark — 125 tasks, 10 life domains, expert-verified, with controls separating
"never stored" / "lacking bridging knowledge" / "stored but never surfaced". The failure is in the
query-conditioned retrieval interface, not in the underlying model capability.

## HyMem Four-Layer Isolation (arXiv:2608.15703)

HyMem separates context into four isolation layers. Information flows **upward only** when retrieval triggers fire. Prevents cross-contamination between layers.

**Layer definitions:**
| Layer | Scope | Hermes surface |
|---|---|---|
| **Transient** | Current turn working memory — discarded after the turn | `working_memory.py` / in-context scratch |
| **Episodic** | Recent session facts — survives across turns, not sessions | `session_search` + Hindsight |
| **Semantic** | Long-term KG facts — stable across sessions | Graphiti (long-term) |
| **Procedural** | Skill harnesses and stable workflows — stable indefinitely | Skill library (`SKILL.md` files) |

**Isolation rules:**
- Never write episodic content (session outcomes, task names, dates, user names) directly into skill text — that belongs in episodic, not procedural.
- Never let skill text pollute the episodic store — skills are procedures, not facts about what happened.
- Graphiti facts must not contain raw tool outputs — summarize and normalize before storing in the semantic layer. (Exception: the `source_text` metadata field on Graphiti episodes may hold raw source text truncated to 500 chars for post-upgrade memory repair — this is metadata, not `episode_body`, and is not processed by the KG extractor. See Memory Portability § source_text_raw.)

**Upward promotion triggers:**
- Transient → Episodic: when a fact survives more than 1 turn and is referenced again — call `hindsight_retain`.
- Episodic → Semantic: when a fact recurs across 2+ independent sessions — write to Graphiti with the entity/relationship schema.
- Semantic → Procedural: **only via an explicit `skill_manage` call** — never automatically.

**Contamination check — run before any skill patch:**
If a skill body contains session-specific data (specific dates, task instance names, individual user names, PR numbers, commit SHAs), remove it — that data belongs in the episodic layer (Hindsight/session_search), not in procedural skill text. Skills must be reusable across sessions and users.

Reference: arXiv:2608.15703, "HyMem: Hierarchical Memory for Long-Horizon Agents", 2026.

---

## Priority and trust
- Canonical user/profile facts: Hermes durable memory
- Canonical workspace knowledge docs: Obsidian vault / local files via read_file (qmd DISABLED)
- Historical conversation evidence: `session_search`
- Supplemental/archive/project retrieval: session_search + Hindsight (qmd and MemPalace both DISABLED)

## Cache layout and memory discipline are the same concern

Prompt caching (see `hermes-context-hygiene`) and memory write discipline share a root:
both are about keeping the stable prefix small and high-signal.

Alignment rule: anything you write to Hermes durable memory lands in the always-in-prompt
layer (MEMORY.md / USER.md). Every byte there is re-sent on every turn and participates
in the cached prefix. Bloated durable memory = smaller effective cache + higher per-turn cost.

Implication: the 3-axis importance filter is also a cache-budget filter. A memory entry
scoring < 2 not only lacks long-term value — it actively degrades prompt cache hit rates
by enlarging the volatile-content zone of the prefix.

Cross-reference: `hermes-context-hygiene` → Prompt Caching Rules → "Static content at
the top". Durable memory occupies that top zone. Keep it minimal.

For topology-aware memory collection in multi-agent runs, see `harness-first-agent-design`
→ Memory Architecture in Multi-Agent Systems.

## Prompt-resident memory budget tuning
When the task is to optimize Hermes memory for usefulness vs token spend, treat `MEMORY.md` and `USER.md` as the small always-in-prompt layer, and the configured memory provider (for example Hindsight) as the broader adaptive recall layer.

Recommended workflow:
1. Inspect current config values for `memory.memory_char_limit` and `memory.user_char_limit`.
2. Inspect the actual current sizes of `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`.
3. If either file is saturated or over limit, prefer a modest increase that restores headroom rather than a large budget jump.
4. Keep the always-injected layer compact; rely on the external memory provider for broader recall.
5. Verify the change with `hermes config check` after updating settings.

Important pitfall:
- Do not try to edit `~/.hermes/config.yaml` with generic file patching tools when Hermes blocks security-sensitive config writes. Use `hermes config set memory.memory_char_limit ...` and `hermes config set memory.user_char_limit ...`, then verify on disk.

Heuristic:
- Aim for some breathing room instead of exact saturation. A modest buffer is enough; if files keep filling up, prune/compress entries first and only then raise limits again.

When sources disagree:
1. live files / current system state
2. explicit user instruction
3. Hermes durable memory for user preferences and stable facts
4. session history (`session_search`)
5. Hindsight episodic recall
6. ~~qmd~~ / ~~MemPalace~~ — both DISABLED (Iris Xe VRAM). Do not call either.

## Token-pressure / compression handling
When the user explicitly flags context pressure, prompt size, or compression concerns during an investigation:
- switch immediately to the lowest-context path that still completes the task
- prefer direct-source inspection and the minimum number of tool calls needed for verification
- avoid rehashing prior findings unless they are required for the next action
- if slash-command compression is not invokable from the current tool surface, say that briefly and continue with a minimal-context execution path rather than debating it
- summarize only the delta and the current blocker/result

Compression trigger discipline for long sessions:
- treat large `session_search` payloads as a compression boundary
- treat broad repo-wide `search_files` sweeps as a compression boundary
- treat multi-file patch/documentation passes as a compression boundary
- treat task-family switches after heavy tool use as a compression boundary
- if `/compress` is not invokable from the active tool surface, state that briefly and explicitly recommend `/compress` at that point instead of silently continuing

## Hermes memory/compression validation
See `references/memory-compression-validation.md` for the full layered check procedure.

Key point: separate config from runtime evidence. "Compression enabled" ≠ "compression has fired."


## CTX file shadow-copy anti-pattern

CTX files (`CTX-now.md`, `CTX-systems.md`, `CTX-projects.md`) are bootstrap orientation
surfaces — not a second copy of durable memory.

**Anti-pattern (causes drift):** copying USER.md preferences verbatim into CTX-now.md.
The CTX copy drifts on every update to USER.md. Two copies = two maintenance targets =
guaranteed inconsistency over time.

**Correct pattern:** one-line pointer in CTX-now.md:
```
## Operating Preferences (stable)
- See ~/.hermes/memories/USER.md for full preference set (injected every turn).
- TL;DR: concise, local-first, token-efficient; worktree isolation default; run repo preflight before commits.
```

**Apply the same principle to CTX-systems.md:**
- Cron job lists: keep them in CTX-systems (it's a system inventory file) but audit against
  `cronjob(action='list')` — the live list is the source of truth, not the CTX file.
- Memory stack description must match live config: qmd and MemPalace are disabled. Do not write "MemPalace active" into CTX or MEMORY.md.

**Audit signal:** if CTX-now.md has more than 3 lines under "Operating Preferences",
it is probably shadowing USER.md — prune it.

## Typed memory annotations and staleness detection

### Session-settled taxonomy + annotation pattern
Classify every durable memory at write time:
- session-settled: a decision or preference that emerged from a specific session context
- directive: an explicit standing instruction from the user (annotate with directive: true)
- unlabeled: facts without clear provenance class (audit for reclassification quarterly)
Use hindsight_retain() with metadata type field. Session-settled facts: apply volatility_class: volatile. Directives: apply volatility_class: stable.

### Memory type tags (arXiv:2606.24775 agent-native taxonomy)

Each entry in `MEMORY.md` is prefixed with a type tag at the start of its content
(after the `§` separator). Apply the tag inline: `[tag] <entry text>`.

| Tag | Meaning | Examples |
|-----|---------|---------|
| `[factual]` | Stable declarative facts about the environment, tools, or state | API keys, installed/uninstalled tools, port numbers, model names |
| `[procedural]` | Step-by-step policies, workflows, or recurring agent behaviours | Safety rules, escalation policy, loop patterns, update protocols |
| `[preference]` | User or agent style/convention preferences | Output format, tone, display units, security posture |
| `[correction]` | Overrides a previously wrong or stale fact; negates a prior entry | "Use X not Y (corrects 2025-11-01 entry)", supersedes notes |
| `[reference]` | Pointers to external resources, scripts, GitHub repos, dashboards | Script paths, cron IDs, dashboard URLs, external KG links |

**Default:** when the type is unclear, use `[factual]` as a safe default.

**Supersedes notation:** when an entry clearly replaces a prior one, append
`(supersedes: <brief-ref>)` to the **superseding** entry only. Only use where
the replacement is unambiguous. Do not modify the superseded entry.

### RUMBA+FAMA combined staleness audit trigger
Trigger a memory staleness audit when session turn count exceeds 30. Apply RUMBA scoring (recency, uniqueness, materiality, behavioral-impact, accuracy) combined with FAMA forgetting curve assessment:
- Score each active memory on 5 RUMBA dimensions (0-2 each; max 10)
- Apply FAMA exponential decay: score x exp(-lambda x days_since_access); lambda=0.1 for volatile, 0.02 for stable
- Memories below combined threshold 2.5 are candidates for pruning
Run audit before any large delegation batch to prevent stale facts from polluting subagent context.

### Staleness detection script (arXiv:2608.07440 Blast Radius eviction)

Script location: `~/.hermes/scripts/memory-staleness.py`

Run: `python3 ~/.hermes/scripts/memory-staleness.py`

What it does:
- Parses each `§`-separated section in `MEMORY.md`
- Extracts `[type tag]` if present
- Extracts dates (ISO `YYYY-MM-DD` and `Month YYYY` patterns)
- Flags sections whose newest date is older than 30 days as **STALE candidate**
- Checks every `/var/home/` or `~/` path with `os.path.exists()`; missing paths → **STALE**
- Sections with no dates and no paths → **UNKNOWN**
- Prints a compact per-section report:
  `§NN  [tag]  ACTIVE/STALE/UNKNOWN  <reason>`

Output columns: section number · type tag · status · reason · 80-char preview.

**When to run:**
- Before a memory consolidation pass (`agent-memory-consolidation` skill)
- After a tool is uninstalled or a dashboard moved
- Nightly cron alongside `l1-extract.py` to catch drift early
- Any time MEMORY.md hasn't been audited in 30+ days

**Acting on the report:**
- **STALE (date):** verify the fact is still current; update or evict the entry
- **STALE (missing path):** the path was removed or renamed; update or drop the entry
- **UNKNOWN:** no date or path found; consider adding a date annotation so future runs can age it properly

## GitOfThoughts: Memory Only Helps for Near-Identical Problems (arXiv:2606.14470, Sweep 15)

Sobering empirical result across 5 memory backends: memory only improves performance when
cosine similarity to past problems is **>0.8**. Below that threshold, memory makes no
measurable difference — and can actively mislead.

**What does work for novel tasks: self-consistency.**
Generate multiple answer paths and pick the most common. This was the ONLY reliable
improvement on novel problems across all memory backends tested.

**Hermes implications:**
- Don't over-engineer memory retrieval for tasks with no close historical analogues.
  A novel research task, a first-of-kind architecture design, a new debugging scenario —
  these won't benefit from Hindsight or Graphiti retrieval unless there's a near-identical
  prior case (check: `hindsight_recall` returns ≥0.80 similarity? If not, skip retrieval).
- For novel tasks, instead invest in: spawning 2-3 delegate_task variations and having
  the parent pick the most consistent output (self-consistency without fine-tuning).
- Git-backed memory (GitOfThoughts) wins for **auditability and merge-ability** of
  knowledge across sessions — not for retrieval accuracy. The value is in the audit trail,
  not the retrieval quality. Hermes session_search provides the equivalent via state.db FTS5.

**When to skip retrieval:**
```
if task_similarity_to_prior < 0.80:
    # Skip hindsight_recall — invest in self-consistency instead
    # Spawn 2-3 delegate_task variants → pick most-common answer
else:
    # Retrieval will help; use standard surface-selection decision order
    hindsight_recall(query)
```

**Note:** the 0.80 threshold is from GitOfThoughts's empirical result on their benchmark.
Treat it as a directional guide, not a precise cutoff for Hermes's different task mix.

## MRMS Contradiction Detection Before Context Projection (arXiv:2607.04617, Sweep 15)

MRMS establishes a layered memory substrate where the **graph layer** (not the vector layer)
is responsible for contradiction detection and supersession resolution *before* any memory
chunk is projected into model context.

**Key architectural rule from MRMS:**
- Structured records → govern **eligibility** (what can be recalled)
- Vectors → handle **recall** (what is semantically relevant)
- Graph → handle **contradiction/supersession** (what is still valid, not overwritten)

The graph layer must run *before* context projection, not after. Returning contradictory
memories and letting the LLM resolve them in context is expensive and error-prone.

**Hermes implementation of this pattern:**
Before projecting Hindsight recall results into context, apply a lightweight contradiction
check using Graphiti:
```
1. hindsight_recall(query) → candidate facts
2. For each candidate with a named entity: mcp_graphiti_search_memory_facts(entity)
   → check if graph shows a newer/superseding fact
3. If graph fact has a later timestamp and describes the same entity+property:
   prefer graph fact; mark Hindsight fact as superseded
4. Only project non-superseded facts into context
```
This is the intended design of the Hermes memory stack (Hindsight + Graphiti in parallel)
but MRMS makes explicit that contradiction resolution is the graph's specific job.

### MemoryOS topic-continuity flush trigger
Trigger a memory flush and consolidation pass when ALL hold:
- session_tokens > 0.7 x MAX_CONTEXT AND
- topic_shift > 0.6 (cosine distance between last 3 turns and first 3 turns of session)
Estimate topic_shift as: 1 - cosine(embed(first_3_turns), embed(last_3_turns))
Without topic-shift gating, consolidation either fires too early (interrupts flow) or too late (loses context).

## MemPalace Adjunct Anti-Pattern (references/mempalace-adjunct-pattern.md)

Do NOT respond to a promising external memory system by immediately merging it into Hermes
core memory or context-compression behaviour. Prefer MCP-first integration.

**Current config:** MemPalace and qmd are both `enabled: false`. Do not call MemPalace or
`mcp_qmd_*` tools. Route as:
- Stable user/env fact -> Hermes durable memory
- Prior Hermes conversation -> session_search
- Maintained local note/doc -> Obsidian vault via read_file
- Broad imported archive or exploratory recall -> session_search + Hindsight (not MemPalace)

If MemPalace is ever re-enabled, treat it as an adjunct MCP layer only — never merge
external memory systems into core context-compression behaviour by default.

## MCB — Memory-Clarification Boundary Policy (arXiv:2608.19564, Sweep 20) <!-- why: incorrect durable writes silently distort future behavior; clarification recall is near-zero without explicit policy -->

MCB benchmark (Li et al., Aug 2026): 140 scenarios testing whether interaction-derived information should be persisted, kept in-context only, re-verified, or clarified with the user. Key findings:
- Models verify changing facts more reliably than they ask for clarification (clarification recall stays at 0.333 even with few-shot prompting)
- Few-shot policy prompting raises overall accuracy 0.557 → 0.771 (Holm p=0.002)
- Erroneous persistence drops from 0.243 → 0.100 with explicit policy

Four-action decision at every candidate memory write:
1. PERSIST — fact is stable, user-stated, high-confidence: write to Hindsight
2. CONTEXT-ONLY — fact is turn-specific or likely to change: keep in working context only
3. VERIFY — fact may be outdated or partially contradicts existing memory: re-fetch or re-confirm before writing
4. ASK — fact is ambiguous and clarification is low-cost: ask the user before writing

Hermes mandate: before any Hindsight write, run the four-action check mentally:
- Is this fact stable across sessions? (PERSIST)
- Is this fact specific to this task instance? (CONTEXT-ONLY)
- Does this fact contradict an existing memory? (VERIFY first)
- Is this an inference rather than a stated fact? (ASK if consequence is high)

Most common error: persisting inferences as facts. Write the inference as a working hypothesis (context-only) until confirmed across 2+ independent sessions.


- **Hindsight daemon fails with "LLM API key is required. Set HINDSIGHT_API_LLM_API_KEY":** The daemon reads `HINDSIGHT_LLM_API_KEY` from `~/.hermes/.env` and copies it into `~/.hindsight/profiles/hermes.env` as `HINDSIGHT_API_LLM_API_KEY`. Even if `llm_provider: anthropic` is in `~/.hermes/hindsight/config.json`, the daemon will NOT fall back to `ANTHROPIC_API_KEY`. Fix: `echo 'HINDSIGHT_LLM_API_KEY=<your anthropic key>' >> ~/.hermes/.env`. For **mid-session recovery** without restarting Hermes, also patch the profile env directly (Python one-liner to replace the empty value in `~/.hindsight/profiles/hermes.env`), then wait ~30s — `ensure_running()` times out in the foreground but the daemon continues starting in the background. Verify: `ss -tlnp | grep 9177` (port up) + `tail ~/.hindsight/profiles/hermes.log` (`Application startup complete.`). Diagnose key presence: check `~/.hindsight/profiles/hermes.env` for `HINDSIGHT_API_LLM_API_KEY=[EMPTY]`. See `references/hindsight-daemon-recovery.md` for the full recovery script.
- Do not dump large blobs into Hermes memory.
- Do not save stale task artifacts as durable memory.
- Do not use MemPalace or qmd (both DISABLED). Prefer session_search + Hindsight + Obsidian files for curated local notes.
- Do not treat compressed session summaries as canonical memory.
- Do not respond to user token-pressure warnings with a long explanation of why compression is difficult; shorten the path instead.
- CTX files shadow USER.md and drift — see CTX file shadow-copy anti-pattern above.
- read_file dedup suppression: if read_file returns "unchanged since last read" and withholds content, use `cat` via terminal instead to get current bytes.

## External domain corpora (e.g. ~/Religion)

When building or querying large external knowledge corpora (not the Hermes agent
context surfaces above), use the `knowledge-corpus-architecture` skill. Key decisions:
- Separate collections by epistemic function (primary sources / analytical commentary / raw originals)
- Embed with text-embedding-3-small (same model as Hindsight — consistency matters)
- Separate ChromaDB clients per collection (avoid cross-collection Rust compaction bug)
- Build a knowledge graph alongside the vectorstore at ingest time (not retroactively)

The Religion DB (~/Religion) is the reference implementation and is queryable via:
  cd ~/Religion && python3 scripts/query_corpus.py "your query"

## RippleMem — Associative Graph-Neighbor Retrieval (arXiv:2608.13334, Aug 2026) <!-- why: prevents flat vector search from missing related facts that are connected via graph neighborhood but not semantically close to the query -->

RippleMem introduces associative "ripple" traversal: starting from a seed retrieval node, it propagates recall through neighborhood edges weighted by recency × relevance. Results: +11.87% accuracy on long-horizon tasks vs vanilla RAG; ~30× reduction in graph traversal cost via structural pruning.

**Retrieval query type gate:**
- **Referential queries** ("same project as last week", "the config we discussed") → prefer graph-neighbor expansion (Graphiti `center_node_uuid`); ripple propagation finds related context vanilla search misses
- **Factual queries** ("what was the exact command", "which port") → prefer Hindsight vector retrieval; ripple adds noise

**Chained retrieval approximation in Hindsight:** Ripple can be approximated without graph infrastructure by performing a second-pass retrieval using the first-pass results as new query embeddings. Use the top-1 first-pass result's text as the query for a second `hindsight_recall()` call — surface any additional related facts.

**After-consolidation edge weighting:** in `agent-memory-consolidation`, after each consolidation pass, update edge weights between consolidated nodes using a recency × co-occurrence score to prime the graph for associative retrieval.

## MobileMem — Temporal Hot/Cold Tiering for Year-Scale Episodes (arXiv:2608.13606, Aug 2026) <!-- why: prevents flat FTS5 index bloat from year-old sessions with no reference hits -->

MobileMem's two-tier adaptive migration policy for long-duration episodic storage:
- **Hot tier:** recent episodes, compressed with lightweight summaries, FTS5-indexed
- **Cold tier:** older episodes, full detail preserved but not indexed; summary-only retrieval
- **Migration trigger:** recency + frequency × importance — when a session's combined score drops below threshold, it moves to cold

**Hermes temporal tiering policy (session_search / Hindsight routing):**
- Sessions with zero reference hits in the last 30 days → hot→cold (summary-only in FTS5)
- Sessions older than 60 days AND low retrieval frequency → cold archive; Hindsight vectors mean-pooled to cluster representation
- Cold-tier retrieval: route to session_search with `detail='compact'` rather than full FTS5 scan

**Memory surface routing gate:** when query's last-session reference is >30 days ago and not a unique-fact lookup → route to cold-archive summary retrieval before running full FTS5 scan.

**Consolidation tagging:** during agent-memory-consolidation, tag each episodic node with `last_accessed` + `access_frequency` to enable future migration scoring.

## Portable Agent Memory Protocol — Provenance Edges for Cross-Agent Transfer (arXiv:2605.11032, May 2026) <!-- why: prevents memory handoff corruption between parallel agents by adding tamper-evidence and capability-based scoped disclosure -->

Open protocol for transferring persistent memory across heterogeneous agents: Merkle-DAG provenance graph for tamper-evidence, capability-based access control for scoped disclosure, injection-resistant rehydration. Demonstrated across GPT-4, Claude, Gemini, Llama (54 passing tests, Apache 2.0 Python SDK).

**5-component structured memory model:** episodic / semantic / procedural / working / identity — each component has a defined serialization and transfer contract.

**Hermes handoff pattern:**
- When terminating a session or handing off to a subagent: serialize episodic/procedural memory as a Portable Agent Memory bundle (structured 5-component model) rather than raw context paste
- Consolidated memory should maintain **provenance edges** (source episode IDs) so the Merkle-DAG can be reconstructed for export
- Before accepting external memory (from subagent output, web_extract, or cron context_from): run injection-resistant rehydration — verify the content against independently-verifiable facts before adding to Hindsight

**Parallel agent memory isolation (reinforces existing pattern):** each parallel subagent uses its own Graphiti `group_id`; the provenance edges allow the orchestrator to reconstruct which facts came from which agent and verify them independently.

## Task-scoped retrieval (arXiv:2609.08180) ★ HIGH

When injecting retrieved memories into context, apply task-relevance filtering — only include facts that are causally necessary for the current task type. Full user profile injection is inefficient and degrades accuracy by introducing irrelevant facts that compete for model attention.

Query the retrieval surface (Hindsight, Graphiti, `session_search`) with **task-class tags**, not open-ended profile queries. Pair with `agent-memory-consolidation` minimal-sufficient selection: extraction tags `task_class:<slug>`; inject filters on that tag.

<!-- why: open-ended profile injection wastes tokens and dilutes attention with facts that cannot change the current decision -->

## Retrieval Query Type Decision Table (updated)
- "Remember I prefer concise answers" → Hermes durable memory
- "What did we do last week for MCP auth?" → `session_search`
- "Find the note about local retrieval routing" → session_search / Obsidian path via read_file (qmd DISABLED)
- "Search a broad imported archive of project notes" → knowledge-corpus-architecture / session_search (MemPalace DISABLED)

## External tool evaluation: 3-question fast triage
When asked to evaluate a new memory/agent tool against the existing Hermes stack:

1. **Coverage gap** — Does it do something the current stack cannot?
   Current stack: semantic recall (Hindsight, local daemon + cloud embeddings), entity/relationship graph (Graphiti MCP enabled), structured notes (Obsidian; QMD disabled), code search (search_files/read_file), session recall (session_search / state.db FTS, always-on), reasoning traces (hermes-reasoning Graphiti group). MemPalace disabled.
   If core capability maps 1:1 → skip.

2. **Fit** — Does it fit this workflow? Hooks only for Claude Code? Designed for 100k+ LOC codebases? A 4th MCP server is a maintenance cost — require clear benefit.

3. **Pattern vs tool** — Can you get the value without installing it?
   Often the lesson is a pattern the current stack already implements. Capture the pattern; skip the tool.

Output per tool: what it does (2 sentences) → gap analysis → fit check → verdict (implement/skip/note pattern only) → closest stack equivalent if skipped.

Recurring skip signals (do not add a layer):
- "Replaces vector memory with graph" / "persistent memory for AI sessions" / "add RAG on the graph" — Hindsight + Graphiti already cover this.
- "Works great with Claude Code hooks" — Hermes CLI will not fire those hooks.
- "No database, just markdown" — the Obsidian vault already does this.
- When comparing memory-system claims, confirm the metric: retrieval-only Recall@K is not end-to-end retrieve→generate→judge accuracy.

Dual-gate / KG routing (from `references/support-files-extended.md`):
- Never merge Hindsight entries on cosine alone. Require cosine >= 0.92 pre-screen AND an LLM entailment check (the implemented `l1-promote.py` dual gate).
- Query has >1 named entity with an inferred relationship → Graphiti. Semantic "what do I know about X" → Hindsight. Flat RAG underperforms latent relations.
- Do not rely on in-context memory past ~30 turns even with explicit memory tools (RUMBA); write to Hindsight proactively.

## Support files
- `references/memory-surface-matrix.md` — compact comparison table and routing examples.
- `references/mempalace-adjunct-pattern.md` — concise decision pattern for treating MemPalace-style MCP systems as adjunct retrieval layers.
- `references/external-tool-evaluation-framework.md` — 3-question tool triage plus session log of evaluated tools (GraphMind, graphthulhu, Curion, taOS, TencentDB) with verdicts.
- `references/support-files-extended.md` — Wiki-memory pointer, Dual-Gate Dedup, ENTLORE routing, RUMBA 30-turn finding, skip-signal catalog.


*FAMA — Forgetting-Aware Memory Accuracy (ACL 2026.findings-acl.1337) — see references/fama-forgetting-research.md.*

### Memory tool unavailable vs memory disabled: diagnostic
Symptom: memory tool returns tool unavailable or hindsight_retain fails silently.
Diagnosis steps:
1. Check: `hermes doctor` - look for memory tool in tool list
2. Check: `grep -A5 'memory:' ~/.hermes/config.yaml` - confirm enabled: true
3. Check: Hindsight daemon running: `curl -s http://localhost:9177/health | jq .status`
Distinguish: tool unavailable (config/daemon issue) vs memory disabled (config intent) vs session-path mismatch (tool loaded but wrong bank). Tool unavailable != memory disabled.

## Memory-Store Failure Pitfalls (references/memory-compression-validation.md)

- **Separate config from runtime evidence**: never store transient runtime observations (API
  latencies, tool-call counts from a single session) as durable config facts. They pollute
  future retrieval with outdated numbers.
- **Store unavailable → fail open, not closed**: if Hindsight or Graphiti is unreachable,
  write to session notes (session_search recoverable) rather than dropping the fact silently.
- **On-disk fallback store**: if the primary memory API fails, write facts to
  ~/.hermes/memory-facts/YYYY-MM-DD.md as an offline staging file; l1-promote.py will pick
  it up on next run.

---

## Cognitive Trap Gate — Memory-Induced Reasoning Fixation (Sweep 21: MemTrapBench / AdaptiveMem)

Counter-intuitive finding: faithfully stored and accurately retrieved memories can still
distort current-task reasoning. Two trap types:
- **Reasoning Fixation**: retrieved memory locks agent into wrong approach even when
  current evidence points elsewhere
- **Belief Distortion**: retrieved memory overrides correct inference from current context

ALL evaluated memory strategies underperformed the no-memory baseline on MemTrapBench.
Traps are systematic, not edge cases.

**AdaptiveMem mitigation:** add an inference-time apply/skip gate before injecting memory:
  "Given the current task and retrieved memory, should this memory be applied?
   Reasoning: [relevance, potential trap risk]
   Decision: apply / skip / partial-use"

**Hermes pattern:**
- When using hindsight_recall or mcp__graphiti__search_memory_facts, explicitly evaluate
  whether the retrieved fact is applicable to the current task before incorporating it
- Higher trap risk: retrieved memory >3 sessions old AND current task type differs
  from source task type — state "I'm applying this cautiously" or skip entirely
- Memory surface decision should be explicit, not assumed; treat retrieved memory as
  a suggestion, not ground truth

## Post-Task Memory Write Tiebreaker (coherence audit 2026-08-30)

**Write-time admission gate (arXiv:2607.22962 ConsistencyGate; arXiv:2608.22215 DLAM analog):**
Do NOT store-all to Hindsight / Graphiti, especially post-compression. Compression invents
implicit facts. Gate every memory write into one of three classes before writing:

  non-write : already known, parametrically correct, or low-signal — discard
  write-new  : new fact not contradicted by existing memory — store
  write-update: later evidence that implicitly invalidates an earlier fact — store + flag
               the prior entry as potentially stale (call hindsight_retain with a supersedes note)

Don’t drop the external copy (Hindsight entry) until a recall probe confirms the fact is
recoverable. Cost is on implicit facts post-compression, not all writes.

**Implicit conflict (STALE gap, arXiv:2605.06527):**
Retrieval + action are decoupled. A recall can return both the old and new fact; the model
may still act on the stale one (premise resistance). When hindsight_recall returns facts
>3 sessions old contradicted by a newer entry:
  1. Explicitly compare old vs new before acting
  2. State which you’re using and why
  3. Mark the old fact as superseded via a follow-up hindsight_retain call

**SkillDAG conflict edges (arXiv:2606.03056):**
Skill selection is structural, not cosine-only. When the task description triggers multiple
skills, check for conflict edges before loading both:
  - Global “always-on X” vs local “don’t load X” = explicit conflict; resolve by specificity
    (local wins over global)
  - Skills with contradictory advice on same decision (e.g. two skills give different model
    names for same task) = flag, load the one with more recent last_validated date
  - Duplicate skills (same trigger, same outcome) = load only the more specific one

This is a manual conflict check until Hermes has a structural skill router.

Two global skills both trigger at task end and both write to durable memory:
- `agent-memory-consolidation`: consolidates session facts into Hindsight/MEMORY.md
- `hermes-memory-capture-and-bridge`: captures cross-session knowledge and routes to right surface

Conflict: if both fire on the same session end, they may write duplicate or contradictory facts.

Tiebreaker rules:
1. `agent-memory-consolidation` fires FIRST for routine session-end extraction (facts, preferences,
   environment state). It uses the full session transcript.
2. `hermes-memory-capture-and-bridge` fires SECOND only when explicitly triggered or when
   cross-session bridging is needed (connecting current session to a prior session's findings).
3. Never call both in the same session end without checking if the other already wrote.
   Check: `hermes sessions list --last 1` to see if extraction already ran.

Runtime reality: neither is automatically wired to `on_session_end` in Hermes source.
Both are agent-facing skills (loaded by the agent on request), not hooks. The conflict
is about agent-level instructions, not runtime execution order.
- `skill_selection_from_wm: true` in config is NOT enforced at runtime (config-only key,
  zero matches in hermes-agent source). Agent must explicitly choose based on this skill.

## TEPA Memory Conflict Detection (arXiv:2608.07429)

Semantic conflict: two hindsight facts that assert contradictory values for the same entity
(e.g., 'config port is 8080' and 'config port is 8443' with different timestamps).

Conflict detection heuristic (no automated revocation — requires hindsight enumerate-all API):
1. When writing a new fact via hindsight_retain, scan MEMORY.md and recent hindsight_recall
   results for the same entity. If an earlier fact contradicts the new one, use memory.replace()
   to update MEMORY.md AND note the conflict in the hindsight_retain content.
2. When a tool result contradicts an injected MEMORY.md fact, prefer the tool output —
   BUT only if the result is a fresh live world probe (e.g., terminal(), read_file() with no
   offset bias). hindsight_recall is memory retrieval, NOT a world probe — do not treat a
   fresh hindsight query as evidence against MEMORY.md. Cached/partial/injected results
   (execute_code with stale kernel state, compaction summaries, session_search replays)
   may themselves be stale: cross-check before overwriting durable memory. STALE
   (arXiv:2605.06527) shows agents fail precisely when they trust replayed context as
   fresh. Schedule memory.replace() with the corrected value only after confirming.
3. Do not accumulate both the old and new version of a fact. Contradiction accumulation
   causes the Lost-in-the-Middle problem: the model averages them rather than choosing.
   Citation: Liu et al. 2023 (arXiv:2307.03172) for Lost-in-the-Middle; not 2604.11462.

Conflict resolution order (strongest wins):
  tool_output > hindsight_retain (this session) > MEMORY.md > old hindsight facts

Staleness by domain (STALE arXiv:2605.06527):
  system-state facts: stale after reboot/update (verify before use)
  user preference facts: stable until user explicitly changes them
  project decision facts: stable until user explicitly overrides
  environmental facts (IP, port, path): verify if > 7 days old

## Non-Enforced Config Keys (config-theater warning)

The following config keys exist in config.yaml but have zero matches in hermes-agent runtime source.
Do NOT rely on them as enforcement mechanisms. Treat as overlay documentation only:
- `memory.working_memory.skill_selection_from_wm` — no runtime router; agent must choose manually
- `memory.working_memory.constraint_binding_required` — not enforced in source
- `loop_harness.*` — sweep-29 overlay; no loop_harness implementation in hermes-agent/**/*.py
- `tool_result_cache.*` — config-only; caching not implemented for these tool categories
- `information_flow_control.enabled`, `nl_permission_policies.enabled`, `ledger_orchestration.enabled`
  — sweep-29 overlays, all disabled AND unwired; actual control is `approvals.mode`

For real enforcement, rely on: `tool_loop_guardrails.hard_stop_enabled`,
`approvals.mode`, `delegation.child_timeout_seconds`, `agent.session_stall_timeout`.

