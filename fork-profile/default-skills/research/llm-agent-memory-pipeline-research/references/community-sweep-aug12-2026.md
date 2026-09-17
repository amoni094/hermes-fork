# Community Sweep — Aug 12 2026 (Sweep 9)

Sources: GitHub releases, HN, LangChain blog, Anthropic blog, OpenAI blog, Reddit (blocked), Juejin/Zhihu (blocked), Zenn (off-topic).
Already-known techniques skipped: LangGraph compress_messages, MemOPD, ColluSkill/ChainGuard, SkillProx, CrystalMem, DREAM, CMI, PSE, CommitKV, Shapley routing, dual-gate dedup, EquiMem, 4-layer vuln model, ENTLORE KG>RAG, Regression Tax.

---

## 1. Turn Memory / Tool-Result Stripping
**Source:** Keen Code (https://github.com/mochow13/keen-code), HN Aug 10 2026  
**Applicability: High**

In a multi-turn agent loop, tool *results* are stripped from history after the current turn completes; only the tool *call trace* (function name + bounded inputs + success flag) is retained as a compact `TurnMemory` record attached to the assistant message. Full results are visible only within the same turn they're produced.

**Claimed benefit:** Context window fills at 20% the rate of comparable agents — "you will regularly see context window coming down from 20% to 1% at the beginning of a new agent turn." Cheap re-runnable tools (read_file, bash, web_fetch) are called again rather than kept in context.

**Why it's different from compress_messages:** compress_messages folds history via summarization; Turn Memory drops result *bodies entirely* (not summarized) while preserving the call trace as a structured object. This is lossless for the agent's ability to re-run; lossy only for reading back verbatim output.

**Implementation sketch for Hermes:**
- After each turn completes, walk message history and for all `tool_result` messages older than the current turn, replace content body with `{"stripped": true, "summary": "<bounded_input_echo>"}`.
- Write compact `TurnMemory` record alongside the assistant message: `{tool_name, key_inputs (bounded ~200 chars), outcome: success|error}`.
- On next turn, inject TurnMemory records as a compact sidebar table (not raw tool output).
- Gate behind config flag: `context.strip_old_tool_results: true`.
- Exception: never strip results from the current active turn (the agent needs them).

**Detailed docs:** https://mochow13.github.io/keen-code/docs/turn-memory.html

| Layer | Lifetime | Contents |
|-------|----------|----------|
| Provider-native active state | Current turn only | Full tool results, reasoning |
| TurnMemory | Attached to assistant message, persisted | Call name, bounded inputs, success flag |
| Session transcript | Persistent | Full UI/replay record (separate from model input) |

---

## 2. Skill-Driven MCP Discovery (Lazy Schema Loading via Skill Stubs)
**Source:** Keen Code, HN Aug 10 2026  
**Applicability: High**

Each MCP server gets an auto-generated skill stub in the skills catalog (frontmatter + tool table only, no full JSON schema). When the LLM decides it needs a server, it reads the generated `SKILL.md` for the tool list, then reads the specific `schemas/<tool>.json` before calling `call_mcp_tool`. No full schema pre-loading into system prompt.

**How Keen generates stubs:**
```
~/.keen/skills/mcp:github/
├── SKILL.md          # frontmatter + tool table (concise)
├── .keen-generated-mcp.json  # metadata (server, tool_count, last_refresh)
└── schemas/
    ├── create_issue.json
    └── list_issues.json
```

**Why this extends the Tool Attention pattern (already in hermes-context-hygiene):**  
Tool Attention (arXiv:2604.21816) requires middleware; this is a pure file-system pattern that maps directly to Hermes's skill architecture. Auto-generating `mcp:<server>` skill stubs removes MCP schemas from the system prompt by default — the LLM reads them on demand via `skill_view()`.

**Implementation sketch for Hermes:**
- On MCP server connect/discover, write `~/.hermes/skills/mcp:<server>/SKILL.md` (tool table) and `schemas/<tool>.json` per tool.
- The system prompt skill index then shows only the skill stub (trigger + description line). Full schemas loaded on demand.
- ~3 extra `skill_view()` calls per novel tool; saves hundreds of tokens per turn as MCP server count grows.
- Mutation guard: tool names attempting path traversal are rejected. Cap tool table at 1000 rows. Truncate long descriptions.

**Detailed docs:** https://mochow13.github.io/keen-code/docs/mcp-skills.html

---

## 3. Deterministic CI-Testable Agent Memory (Remembrane / SQLite)
**Source:** HN post by `satyasairay`, Aug 11 2026  
**Applicability: Med**

Single-file SQLite agent memory store. Key novel property: recall is **deterministic** (no stochastic embedding variance), enabling unit tests that assert what an agent remembers — runnable in CI. Scores by: semantic similarity + recency + importance + historical-usefulness (all configurable). Every result surfaces its own score breakdown (not a black box). Every write is journaled (snapshot + diff support). Built-in contradiction heuristic (candidates to review, not ground truth). Exposes MCP server + LangChain/CrewAI adapters.

**What's new vs. Hermes current stack:**
- **Testability**: Graphiti and Hindsight don't expose a CI-testable deterministic recall API. Adding this to the memory layer allows regression-testing memory quality, not just correctness of writes.
- **Score transparency**: the "score breakdown" debug output pattern is independently adoptable — wrap Graphiti queries to return component scores alongside results.
- **Contradiction flag as candidates**: the heuristic (not ground truth) framing is the right mental model — already matches our NLI-based interference gate, but Remembrane makes it explicit in the API surface.

**Implementation signal for Hermes:** Add a `memory_debug: true` flag to Graphiti memory queries that returns score components (semantic sim, recency weight, importance, usefulness history). Build a test harness that seeds a Graphiti graph, runs queries, and asserts specific nodes are returned — forming a CI-runnable memory regression suite.

**Limits noted by author:** lexical embedder by default (plug in sentence-transformers for semantic); ~50K item ceiling before outgrowing the design; CrewAI adapter is helper, not drop-in.

---

## 4. Policy-Gated Agent Browser + Persistent Element Location Memory (Pickle)
**Source:** https://picklebrowser.com | HN Aug 11 2026  
**Applicability: Med**

Browser purpose-built for agents: pages load as compact structured data (32× token reduction vs raw HTML claimed). Policy gates block domains or require approval for sensitive actions. Memory of page element locations persists between sessions — agents don't re-discover buttons on revisit. Auto-routes to step-by-step planning mode for weaker models.

**What's new vs. Hermes current stack:**
- `web_extract` already returns structured markdown; `browser_snapshot` returns AX trees — the extraction angle is covered.
- **Novel: persistent element location cache** — keyed by URL + element role/label, survives sessions.
- **Novel: per-action approval policies** — typed action classes (purchase, form_submit) require approval; maps to Hermes's existing computer_use approval gates but more granular.
- **Novel: model-strength-adaptive planning** — weaker models get step-by-step restrictions.

**Implementation sketch for Hermes:**
- Add an element-location cache to `browser_snapshot` results persisted to `~/.hermes/browser_memory.json`, keyed by `{url, element_role, element_label}`. On revisit, inject known positions as hints.
- Expose a config block: `browser.block_domains: [...]`, `browser.require_approval_for: [purchase, form_submit]`.

---

## 5. Switchyard Benchmark-Driven Model Routing
**Source:** LangChain Blog, Aug 11 2026 (partner post by S. Tangedipalli, K. Singh)  
**Applicability: Med**

Benchmark that classifies which subtasks within an agentic workflow can be downgraded to smaller/cheaper models without quality loss, generating empirically-grounded routing thresholds rather than heuristic rules.

**What's new vs. Hermes current stack:**
- `claude-routing-hierarchy` skill covers what models are wired; Switchyard adds the *evaluation methodology* — measure per-task-type quality thresholds empirically, then derive routing rules from data.
- This is the "EDD applied to routing" pattern: instrument tool calls with model + outcome metrics, build per-task-category evals, derive thresholds.

**Implementation signal for Hermes:** Instrument Hermes subagent calls to log `{task_type, model, outcome_quality}`. After N sessions, compute per-category routing thresholds. Update `claude-routing-hierarchy` from measured data rather than best guess.

---

## 6. AutoGen Linear Memory Mode (append-only)
**Source:** AutoGen python-v0.7.5, Sep 30 2026  
**Applicability: Med**

`linear memory` support added to `RedisMemory`: append-only log ordering for agent memory rather than vector-similarity retrieval. Designed for audit trail use cases where temporal ordering matters more than semantic proximity.

**What's new vs. Hermes current stack:**
- Hermes uses Graphiti (bi-temporal graph) and Hindsight (vector). Neither exposes a pure "linear/append-only" mode for audit.
- Linear memory is useful for: subagent audit trails, tool call ledgers, regulatory-style "what did the agent do and in what order?" queries.

**Implementation signal for Hermes:** Add a `linear_mode: true` option to session memory logging that writes facts as a timestamped append-only log (`~/.hermes/audit/<session_id>.jsonl`) separate from the semantic memory pipeline. This is the existing task ledger pattern (`hermes-observability-and-task-ledger`) but with explicit memory semantics.

---

## 7. Agent-as-Tool Wrapper Pattern (formalized)
**Source:** AutoGen python-v0.7.4 / python-v0.7.1, Aug 19 2026  
**Applicability: Med**

Encapsulating a full agent behind a single tool interface (`AgentTool` / `TeamTool`) for parent orchestrators. Documented limitations around parallel tool calls for these wrapper types.

**What's new vs. Hermes current stack:**
- Hermes subagents already work this way via `delegate_task`. The AutoGen formalization adds the **parallel tool call limitation** as an explicit documented pitfall: parent agents should not issue multiple AgentTool calls in parallel if the wrapped agents share mutable state.
- This maps to the Hermes pattern in `hermes-agent-sync` — idempotent application of parallel agent outputs.

**Implementation signal for Hermes:** Document in `hermes-agent-sync` that parallel subagent delegation works only when subagents have independent write surfaces. Shared-state subagents must be serialized.

---

## Non-English / Other Sources

- **Reddit** (r/LocalLLaMA, r/MachineLearning): JSON API returned empty — bot-detection without auth headers. No data.
- **Juejin**: Login/category-selection wall rendered — no articles accessible.
- **Zhihu**: Not attempted (same wall expected).
- **Zenn**: API returns articles but current batch (Aug 12) is all off-topic (iOS app review, SSH, yaw estimation). No agent-memory articles surfaced.
- **OpenAI Research**: Page JS-rendered, no content extractable.
- **Anthropic Research**: Latest post Aug 10 (Riemann hypothesis bounds) — pre-cutoff, pure science, not agent architecture.
- **LangChain Blog**: Latest Aug 11 (Switchyard, captured above). LangSmith LLM Gateway (Jul 30) is infrastructure, no new algorithm.

---

## Release Summary: What's Already Known / Not Novel

| Release | Date | Verdict |
|---------|------|---------|
| LangGraph 1.2.11 | Aug 11 | Bug fixes + trace_policy; no novel architecture |
| mem0 v2.0.18 | Aug 11 | Bug fixes only (URL-encoding, filter validation) |
| crewAI 1.15.14 | Aug 8 | Pre-cutoff; project_id scoping only |
| AutoGen 0.7.1 | Jul 28 | Pre-cutoff; RedisMemory introduced |
| AutoGen 0.7.2 | Aug 7 | Pre-cutoff; approval_func, parallel_tool_call flag |
| AutoGen 0.7.3 | Aug 19 ✅ | anyOf/oneOf schema typing, RedisStore serialization fix |
| AutoGen 0.7.4 | Aug 19 ✅ | Agent-as-Tool formalized (see #7 above) |
| AutoGen 0.7.5 | Sep 30 ✅ | Linear memory (see #6 above) |
