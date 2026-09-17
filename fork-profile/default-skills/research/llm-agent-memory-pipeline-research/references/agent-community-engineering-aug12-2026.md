# Agent Engineering Community Findings — Aug 12 2026

Non-arXiv sources: engineering blogs, GitHub tutorials, community posts.
Complements the arXiv sweeps in agent-improvement-aug12-2026-sweep*.md.

---

## 1. Anthropic Dreams API — Managed Async Memory Consolidation

**Source:** https://platform.claude.com/docs/en/managed-agents/dreams

Async job: `client.beta.dreams.create(inputs=[memory_store, sessions], model, instructions)`
→ new reorganized memory store (deduped, contradiction-resolved, insight-surfaced).
Input never modified; output is a reviewable separate store.

- 100 sessions/dream max; 4096-char instructions
- Billing: standard token rates, linear with session count
- Supported: claude-sonnet-4-6 (current Hermes model) ✓
- Errors: `timeout`, `input_memory_store_too_large`, `input_session_unavailable`

**Hermes mapping:** directly replaces manual `agent-memory-consolidation` cron for
managed-agent deployments. For local Hermes: fire nightly from cron with last 50–100
session IDs, swap output store into next session's resources[].

---

## 2. Anthropic Managed Memory Stores — Layered Cloud Memory

**Source:** https://platform.claude.com/docs/en/managed-agents/memory

Multiple `memory_store` resources attachable per session, each with independent
Dreams consolidation schedule. Domain partitioning pattern:
- `prefs_store`: user style/preference facts (dream weekly)
- `project_store`: per-project state (dream per-sprint)
- `skills_store`: skill catalog knowledge (dream monthly)

Complements local `memory_20250818` tool. Use managed stores for cloud-synced
long-term memory; local tool for session-local working files.

---

## 3. Anthropic Managed Agents — Stateless Harness Pattern

**Source:** https://www.anthropic.com/engineering/managed-agents

Core design: session state lives in server-side append-only log external to harness.
Recovery: `wake(sessionId)` + `getSession(id)` → resume from last event.
"Nothing in the harness needs to survive a crash."

**Hermes gap:** Hermes SQLite session log IS the right substrate. Missing: a clean
`wake(session_id)` bootstrap path that reads the log and reconstructs context from it.
Currently a crash requires manual session recovery.

---

## 4. LangChain Wiki Memory Pattern

**Source:** https://www.langchain.com/blog/wiki-memory

Instead of storing conversation turns verbatim, agent maintains a structured markdown
wiki (sections, headers, cross-references) updated after each session. On next session,
the wiki is loaded as structured context rather than retrieved by similarity.

**Hermes adaptation:** nightly cron that:
1. Reads recent Hindsight facts grouped by entity
2. Merges into a sectioned `~/.hermes/memories/WIKI.md` (Skills | Tools | Projects | User)
3. Injects WIKI.md as structured context rather than doing per-turn similarity search

Benefits over flat vector store: navigable, editable by human, no embedding drift,
zero retrieval latency (already in context).

---

## 5. LangChain Memory Portability Manifesto ("Your Harness, Your Memory")

**Source:** https://www.langchain.com/blog/your-harness-your-memory
**Author:** Harrison Chase (LangChain CEO)

"As soon as there is any state associated, it's much harder to switch [harnesses].
Because this memory matters. And if you switch, you lose access to it."

Key recommendation: BYOM (Bring Your Own Memory) — store in open formats (SQLite, S3,
Postgres, filesystem) so state survives harness changes.

**Hermes status:** already compliant (SQLite + filesystem). Missing: a documented open
memory schema so Hindsight exports can be inspected/migrated/versioned independently.
A `hermes memory export --format=json` command would close this gap.

---

## 6. Electric Agents — Durable Stream as Agent Identity

**Source:** https://electric.ax/blog/2026/04/29/introducing-electric-agents
**Code:** https://github.com/electric-sql/electric/tree/main/packages/agents-runtime

"The agent is the durable stream. Everything else is a projection or a subscriber."
Agent identity lives in the append-only log; model is just current subscriber.

All capabilities become projections over one primitive:
- memory = compressed projection
- context = filtered projection
- fork = branch the stream at any historical point
- HITL = write to user's inbox stream

**Multi-player by default:** agent state in Postgres/SQLite/file is not multi-player.
Electric's durable stream substrate makes all agents addressable, observable, forkable.

**Hermes partial alignment:** SQLite session log is already append-only. Missing: live
multi-subscriber projection (other agents/supervisor can't observe Hermes session in
real time). A `hermes session stream --follow <id>` command + SSE endpoint would close gap.

---

## 7. Composable Agent Ladder (SQLite-on-S3 / Lambda Pattern)

**Source:** https://github.com/equationalapplications/sqlite-s3-agent-tutorial/blob/main/docs/12-composable-agents.md

6-rung ladder for composable cloud agents:
1. **Spin up → work → exit** (stateless compute, state in S3)
2. **To-do list** (work queue in same SQLite file)
3. **Delegation hierarchy** (orchestrator + sub-agents, recursive fan-out)
4. **Intent queue** (sub-agents emit intents; single coordinator applies to master object)
5. **EC2 escape hatch** (for tasks exceeding Lambda's 15-min ceiling)
6. **Tiered memory + KG** (namespaced entityId memory with typed edges, scoped permissions)

**Key pattern (Rung 4) for Hermes:**
Sub-agents write typed intents to a queue; a pinned coordinator applies them atomically.
Prevents concurrent write collisions without serializing all sub-agent work.

```sql
-- Intent queue table (add to Hermes cron SQLite DB)
CREATE TABLE IF NOT EXISTS agent_intents (
    id INTEGER PRIMARY KEY,
    agent_id TEXT NOT NULL,
    intent_type TEXT NOT NULL,  -- 'memory_write' | 'skill_patch' | 'graphiti_add'
    payload TEXT NOT NULL,      -- JSON
    created_at TEXT DEFAULT (datetime('now')),
    applied_at TEXT,
    status TEXT DEFAULT 'pending'
);
```

**Concurrency lock (Rung 1 safety):**
```python
# At cron agent startup — prevent double-invocation
conn.execute("INSERT OR IGNORE INTO agent_locks VALUES (?, datetime('now'))", [agent_name])
if conn.changes() == 0:
    sys.exit(0)  # Another instance is running
```

**Hermes memory reference:** `@equationalapplications/core-llm-wiki` package implements
namespaced weighted tiered memory (entityId scoping, tierWeights, typed edges) that maps
directly to Hermes's 3-tier memory with explicit weight control.

---

## 8. Cloudflare Project Think — Agents as Third-Wave Infrastructure

**Source:** https://blog.cloudflare.com/project-think/

"Third wave" framing (chatbots → coding agents → agents as infrastructure):
- Durable, distributed, structurally safe, serverless
- Agents that run on the internet, survive failures, cost nothing idle
- Security through architecture, not behavior instructions

**Structural safety principle (directly applicable to Hermes):**
Dangerous actions must be architecturally impossible, not just instructed-against.
Permission boundaries must be code (allow/deny lists), not system prompt sentences.

Hermes gap: audit which tools are always-available vs explicitly gated per session.
Move high-risk tools (terminal with broad workdir, file writes) to session-gated
opt-in rather than default-available.

---

## 9. Harness Variance > Model Variance (Antigma Terminal-Bench 2.1)

**Source:** https://antigma.ai/blog/2026/08/04/harness-matter

Fixed model, 5 harnesses (Ante, Ante-short, Pi, OpenCode, Hermes), 10 tasks:

| Harness | Pass | Cost/pass | Time/task | Tool calls | Avg mem |
|---------|------|-----------|-----------|------------|---------|
| Ante | 10/10 | $0.0359 | 438s | 30.8 | — |
| Ante-short | 9/10 | $0.0295 | 370s | 25.1 | 118 MiB |
| Hermes | 7/10 | $0.0749 | 694s | 36.2 | 847 MiB |

Ante-short vs Hermes: 2.5× cheaper/pass, 1.9× faster, 31% fewer tool calls.
Binary: Ante 34 MiB, Hermes 618 MiB (18× difference).

Key levers to close the Hermes gap:
- Short-prompt profile (load only semantically-matched skills, strip prose)
- Reduce default tool set per session (fewer MCPs enabled by default)
- The 36.2 vs 25.1 tool calls/task gap (~11 calls) is the primary efficiency target

**Short-prompt pattern:** Ante's `--short-prompt` flag removed decorative system prompt
prose → 18% cost, 16% speed, 19% tool-calls savings at cost of 1 task out of 10.

---

## 10. LlamaIndex Retrieval Harness — Eval-Driven Skill Improvement Loop

**Source:** https://www.llamaindex.ai/blog/announcing-retrieval-harness
**Related:** https://www.llamaindex.ai/blog/building-a-better-liteparse-skill-with-evals

Continuous eval loop that improves a skill by running evals against ground-truth
examples and feeding failures back into skill refinement — not a one-shot eval
but a running background improvement process.

**Hermes mapping:** pair with `skillopt-continuous-improvement` and `evaluation-driven-development`.
The innovation is the automation of the feedback loop:
1. Skill executes on real tasks (instrumented)
2. Failures are extracted (SKILL.md patch candidates)
3. Patch is auto-proposed, human-approved via skillspector_guard
4. Repeat on next cron cycle

---

## 11. LlamaIndex ExtractBench — Document Extraction Quality Baseline

**Source:** https://www.llamaindex.ai/blog/introducing-extractbench

Benchmark: 14 systems × 370 documents (long filings, scans, handwriting).
Metrics: completeness, accuracy, grounding, cost/page.

**Methodology applicable to Hermes:** completeness + grounding metrics for evaluating
skill execution quality on document tasks. Adapt: did the agent extract all required
fields (completeness)? Is each extracted value traceable to source text (grounding)?
This is the `grounded-citations` + `evaluation-driven-development` evaluation pattern.

---

## Cross-References

- `anthropic-agent-api-aug2026.md` — Dreams API, Managed Memory Stores, Managed Agents details
- `agent-runtime-aug2026-sweep.md` — arXiv papers on agent error recovery, multi-agent coordination
- `agent-improvement-aug12-2026-sweep8.md` — arXiv papers sweep 8 (same date)
