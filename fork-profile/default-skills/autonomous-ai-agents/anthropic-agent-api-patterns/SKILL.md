---
name: anthropic-agent-api-patterns
version: 1.0.0
description: "Use when building agentic loops on Anthropic API (Aug 2026)."
triggers:
  - "effort parameter"
  - "task budget anthropic"
  - "anthropic memory tool"
  - "fable 5 refusal"
  - "stop_reason refusal"
  - "mid-conversation system message"
  - "mid-conversation tool changes"
  - "server-side compaction"
  - "output_config effort"
  - "task-budgets-2026-03-13"
  - "memory_20250818"
  - "initializer coder pattern"
  - "run-cache pattern"
  - building an agentic loop on Anthropic API
  - controlling token spend or effort in an Anthropic API loop
  - handling mid-conversation system message changes on Anthropic API
  - server-side compaction or context window management with Anthropic
  - tool schema changes mid-conversation on Anthropic
related_skills:
  - claude-routing-hierarchy
  - autonomous-agent-loop-design
  - harness-first-agent-design
  - hermes-memory-surface-selection
  - fable-orchestrate
---

# Anthropic Agent API Patterns (Aug 2026)

First-party Anthropic API controls that directly affect agentic loop design.
All items confirmed GA or beta as of August 2026.

---

## 1. `effort` Parameter — Loop-Aware Token-Spend Control (GA)

Pass `output_config={"effort": "<level>"}` on every API call. Affects ALL tokens:
text, tool calls, AND thinking. No beta header required.

| Level | Hermes use case |
|-------|-----------------|
| `low` | Leaf subagents, high-volume simple tasks |
| `medium` | **Recommended default for Sonnet 4.6** — avoids unexpected latency |
| `high` | Default (= omitting effort); complex reasoning |
| `xhigh` | Demanding coding/agentic (Opus 5, Sonnet 5, Fable 5) |
| `max` | Frontier problems; set `max_tokens >= 64k` |

**Key loop effect:** lower effort → fewer tool calls per turn. Primary lever for
controlling loop cost without changing model tier.

**Cache invariant (critical):** hold effort constant within a session that uses prompt
caching. Changing `effort` between turns invalidates the cache prefix. Pick once at
session start; vary across workloads, not within a conversation.

**Sonnet 4.6:** explicitly set `effort: "medium"` — the implicit `high` default causes
unexpected latency.

**At `xhigh`/`max` on Fable 5/Mythos 5:** `thinking: {"type": "disabled"}` returns 400.
Use effort level to control thinking depth instead.

---

## 2. Task Budgets — Advisory Loop-Level Token Cap (beta: `task-budgets-2026-03-13`)

`task_budget: {tokens: N}` gives Claude an advisory total-token target for the entire
agentic loop (not per-request). Claude self-regulates: prioritizes, skips low-value
tool calls, summarizes near budget. Complements `effort`. Supported: Fable 5, Mythos 5,
Opus 5, Sonnet 5.

**For Hermes cron agents:** set `task_budget.tokens = 2x expected spend` as a circuit
breaker against runaway loops that burn 10x expected tokens.

```python
response = client.messages.create(
    model="claude-opus-5",
    max_tokens=64000,
    task_budget={"tokens": 100000},
    output_config={"effort": "xhigh"},
    extra_headers={"anthropic-beta": "task-budgets-2026-03-13"},
    messages=[...]
)
```

---

## 3. Native Memory Tool (`memory_20250818`) — GA

Claude CRUDs files in a `/memories` directory across sessions. Claude requests
operations; your app executes them. No beta header required.

**Enable:** `tools=[{"type": "memory_20250818", "name": "memory"}]`

**Python SDK drop-in:**
```python
from anthropic.tools import BetaLocalFilesystemMemoryTool
memory = BetaLocalFilesystemMemoryTool(base_path="./memory")
runner = client.beta.messages.tool_runner(
    model="claude-opus-5", tools=[memory], max_tokens=1024, messages=[...]
)
final_message = runner.until_done()
```

**Commands:** `view`, `create`, `str_replace`, `insert`, `delete`.

**Security:** implement path traversal protection — reject any path escaping `/memories`.

**Hermes surface selection:** 3rd memory surface alongside Hindsight and Graphiti.
Best for: structured project-state files agents need verbatim across sessions (progress
logs, feature checklists). NOT for: relationship graphs (use Graphiti), semantic recall
(use Hindsight), stable one-line facts (use MEMORY.md).

**For long-running loops — pair with compaction:**
- Compaction handles active context automatically (server-side, transparent)
- Memory tool preserves critical state that must survive compaction's lossy summary

---

## 4. Server-Side Compaction

When conversation approaches context limit, API auto-summarizes older turns server-side.
Transparent to client code; no special handling needed.

Write critical state to memory files before the conversation gets long; let compaction
handle the rest. Memory tool + compaction = recommended long-running-agent stack.

---

## Programmatic Tool Calling — Code Stubs Beat JSON (arXiv:2608.06370, Aug 2026)

PTC (typed Python stubs, chained in code) outperforms JSON tool-call format in 11/14 models.
GPT-5.6: +10.6% over JSON. More importantly: stable under context rot (long inputs degrade
JSON accuracy by 2.3%; code stubs hold). Implications for Hermes subagent design:

- When chaining multiple tool calls in a delegate_task goal, describe them as pseudo-code
  steps (e.g. `read_file(path) → patch(path, old, new) → terminal("pytest ...")`) rather
  than numbered JSON blocks. The model follows code-shaped instructions more reliably.
- For long-context subagent prompts (>50K tokens), code-style chaining is specifically more
  robust — JSON schemas degrade under context rot; code stubs don't.
- This does NOT mean passing actual code to the agent — describe the steps in code syntax
  as part of the goal string.

## 5. Fable 5 Refusal Handling — Required for Any Fable 5 Route

- HTTP **200** with `stop_reason: "refusal"` — NOT an error; check explicitly
- Response reports which classifier triggered
- **Mythos 5 has no classifiers** — no refusal handling needed there
- Not billed for input tokens if refused before any output generated

```python
response = client.messages.create(
    model="claude-fable-5",
    fallbacks={"mode": "default"},  # server-side auto-retry on refusal
    messages=[...]
)
if response.stop_reason == "refusal":
    handle_persistent_refusal(response)
else:
    process_content(response.content)
```

**Fallback credit:** API refunds prompt-cache cost on retry — you don't pay twice.

---

## 6. Mid-Conversation System Messages (GA, Opus 4.8+, Fable 5)

Inject operator-level instructions mid-session as `{"role": "system"}` in messages
array — preserves the top-level `system` prompt cache prefix.

- Priority: later system messages > earlier > top-level `system` field
- Must follow a user turn or assistant turn ending in a server tool result
- **Never inject untrusted content** — gets operator-level authority

For Hermes role pipelines: inject skill-specific system prompts on topic shift without
resetting conversation state.

---

## 7. Mid-Conversation Tool Changes (beta: `mid-conversation-tool-changes-2026-07-01`)

**Supported: Opus 5, Fable 5, Opus 4.8 ONLY — NOT Sonnet 5.**

Add/remove offered tools mid-conversation via `tool_addition`/`tool_removal` blocks
inside a system-role message. Declare all tools in `tools` upfront with
`defer_loading: true` for tools to withhold initially. Cache stays intact.

Use for: progressive tool reveal, expensive-capability gating, role-based restriction.

---

## 8. Initializer+Coder Two-Agent Harness (Anthropic Engineering)

For multi-context-window software tasks. Prevents four major failure modes.

### Phase 1 — Initializer agent (runs once)

Before any substantive work, writes:
1. **`feature_list.json`** — all features with `"passes": false`. Use JSON not Markdown
   (models corrupt Markdown checklists; JSON structure is more resilient).
   Agents update ONLY the `passes` field — never remove or edit descriptions.
2. **`claude-progress.txt`** — running log of done + what's next
3. **`init.sh`** — launch dev server + run baseline end-to-end test
4. Initial git commit

### Phase 2 — Coding agent (every subsequent session)

Always in this order:
1. Read `claude-progress.txt` + `git log --oneline -20`
2. Run `init.sh` — verify baseline BEFORE touching any code
3. Read `feature_list.json` — pick ONE highest-priority `passes: false` feature
4. Implement that ONE feature
5. Mark `passes: true` ONLY after end-to-end verification (not unit tests — use
   browser automation or equivalent human-style testing)
6. Commit with descriptive message
7. Update `claude-progress.txt` with done + what's next

| Failure mode | Fix |
|---|---|
| Agent declares victory early | Feature list defaults passes:false; read it each session |
| Leaves env with bugs | Run init.sh at start; update progress.txt at end |
| Marks done without testing | Explicit verification steps; passes:true only post-E2E |
| Wastes time figuring out how to run the app | init.sh — read and run it |

---

## 9. Run-Cache Pattern (a16z, Aug 2026)

For repeatedly-run workflows:
1. Agent executes in full agentic mode
2. System caches successful execution as deterministic code
3. Subsequent runs: deterministic code — no LLM cost
4. On breakage: LLM returns to diagnose, fix, re-cache

Cost per run falls over workflow lifetime. Validated at scale in production enterprise
deployments (a16z, Aug 12 2026). Hermes application: any cron workflow that runs
the same task repeatedly.

---

## 10. Accessibility Tree Over Screenshots for Lower Latency

Production teams have cut computer-use latency by grounding on the accessibility tree
instead of screenshot loops (a16z, Aug 2026).

In Hermes: use `mode='ax'` in `computer_use` when the task can resolve from structured
element data. Reserve `mode='vision'` for visual inspection and layout verification.

---

## Pitfalls

- **`effort` invalidates cache mid-session:** pick once at session start.
- **Fable 5 refusals are HTTP 200:** check `stop_reason` explicitly before processing content.
- **`thinking: disabled` is 400 at xhigh/max on Fable 5/Mythos 5.** Use effort to control thinking.
- **Task budgets are advisory.** Claude may exceed if the task genuinely needs it.
- **Memory tool is client-side.** Missing handler = silent failures on memory calls.
- **System messages get operator authority.** Never inject untrusted web/tool content there.
- **Tool changes: NOT on Sonnet 5.** Only Opus 5, Fable 5, Opus 4.8.
- **Feature checklists: use JSON, not Markdown.** JSON is more resilient to agent corruption.
## Dreams API — Async Memory Consolidation (Anthropic beta, Aug 2026)

Async job: reads a memory store + 1–100 session transcripts → produces a new deduped,
contradiction-resolved memory store. Input store is never modified. Review before activating.

```python
dream = client.beta.dreams.create(
    inputs=[
        {"type": "memory_store", "memory_store_id": store_id},
        {"type": "sessions", "session_ids": [s_a, s_b, ...]},
    ],
    model="claude-sonnet-4-6",
    instructions="Focus on coding-style preferences; ignore one-off debugging notes.",
)
# Poll: dream.status: pending → running → completed/failed/canceled
# On complete: dream.outputs[0].memory_store_id = new consolidated store
```

Limits: 100 sessions/dream, 4096-char instructions. Supported models: opus-5, fable-5,
opus-4-8, sonnet-5, sonnet-4-6. Errors: `timeout`, `input_memory_store_too_large`,
`input_session_unavailable`. Billing: standard token rates.

Hermes nightly pattern: pass last 50–100 session IDs + current memory store.
Complements local l1-gmemory-consolidation.py (Hindsight→Graphiti); this operates on
Anthropic-managed stores separately. Don't auto-swap stores without human review.

## Managed Memory Stores (Anthropic beta, Aug 2026)

Server-side persistent `memory_store` resources. Attach multiple stores per session for
layered memory (user-prefs store, project store, skills store). Complement Hindsight —
use managed stores for cloud-sync, Hindsight for local dense-search.

**Hermes position:** Currently on local Hindsight + Graphiti. Evaluate when beta stabilises; don't migrate until GA.

## Managed Agents Crash Recovery Pattern (Anthropic blog, Aug 2026)

"Nothing in the harness needs to survive a crash." Session log is external and durable.
Recovery: `wake(sessionId)` + `getSession(id)` → resume from last event.

**Hermes analogue:** Any multi-step agentic cron must write durable state (Hindsight or
a file) after EACH step, not only on completion — so a mid-run crash resumes cleanly.

## lance-bundle — Portable Embedded RAG Corpora (Aug 2026)

`pip install lance-bundle` — packages embedding vectors + ONNX model into a single portable
.zip (LanceDB + ONNX). No server, no re-embedding at load time.

**Hermes use:** pre-built domain corpora (religion KG, trading research) as lance-bundle
zips — survives reinstalls, no separate embedding infra. Evaluate as alternative to local
ChromaDB collections.

## Reference files

- `references/anthropic-agent-api-aug2026.md` — Anthropic Agent API Sources — August 2026
