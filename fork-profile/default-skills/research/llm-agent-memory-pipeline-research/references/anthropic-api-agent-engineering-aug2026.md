# Anthropic API + Agent Engineering — Aug 12 2026 Research Sweep

Multi-source sweep: Anthropic docs, HN, Arthur.ai FDE series, Langfuse, HuggingFace, LiteLLM, OpenTelemetry.
Topic focus: prompt caching, tool schema, latency, structured output, memory write quality,
skill routing, cost monitoring, error recovery, observability, config management, new libs.

---

## 1. PROMPT CACHING (Anthropic API)

**Automatic top-level `cache_control`** (⚡ LOW complexity)
- Source: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Pass `cache_control={"type": "ephemeral"}` at top level of `messages.create()`.
  System auto-applies breakpoint to last cacheable block; advances each turn automatically.
- Cache read cost = 0.10× base input price → **90% savings on cached tokens**
- Sonnet 4.6: $0.30/MTok cached vs $3/MTok base
- Works on all active Claude models (Sonnet 4.6, Haiku 4.5, Opus 4.x)

**1-hour TTL for system prompts** (⚡ LOW)
- Add `{"ttl": "1h"}` to the cache_control dict for static system prompts
- Standard 5-min TTL misses cache on cron jobs that restart every 30+ min
- Cost: 2× base on writes, pays back on 2nd read within 1 hour
- Hermes cron agents re-pay full system prompt cost today — this fixes it

**`max_tokens: 0` pre-warming** (⚡ LOW)
- Send a silent call with max_tokens=0 to seed cache before first real agent call
- No output produced, no output tokens billed
- Better than old `max_tokens: 1` workaround — no single-token output to discard
- Useful for cron agents: fire pre-warm call at cron start, real call hits warm cache

**Cache pricing table (Aug 2026)**:
| Model | Base | 5m Write | 1h Write | Cache Read |
|-------|------|----------|----------|------------|
| Sonnet 4.6 | $3/MTok | $3.75 | $6 | $0.30 |
| Haiku 4.5 | $1/MTok | $1.25 | $2 | $0.10 |
| Opus 4.6 | $5/MTok | $6.25 | $10 | $0.50 |

**Combining auto + explicit breakpoints**:
- Up to 4 explicit `cache_control` breakpoints per request
- Auto caching uses one of the 4 slots
- Pattern: explicit on system prompt (1h TTL) + auto on conversation history
- Order matters: tools → system → messages (prefix order for caching)

---

## 2. TOOL SCHEMA DESIGN

**`strict: true` on all tool definitions** (⚡ LOW)
- Source: https://docs.anthropic.com/docs/en/agents-and-tools/tool-use/strict-tool-use
- Enables grammar-constrained sampling of tool parameters
- Guarantees schema-compliant tool inputs every call — eliminates hallucinated fields
- Add to each tool dict: `{"name": "...", "strict": True, "input_schema": {...}}`
- Compatible with `output_config.format` simultaneously

**Named sub-fields as schema-level CoT** (⚡ LOW)
- Source: HN comment, Aug 2025 (mh-, story 44828884)
- Decompose outputs into more fields than seem necessary, with highly specific names
- E.g., instead of `{"suggestion": "..."}`, use `{"reasoning": "...", "concise_suggestion": "..."}`
- Named fields act as chain-of-thought scaffolding without explicit CoT prompting
- `description` field on each property is free steering — use it extensively
- Community reports 20–40% fewer hallucinated values

**Poka-yoke absolute paths** (LOW–MEDIUM)
- Source: Anthropic Building Effective Agents (SWE-bench section)
- Anthropic's SWE-bench team: Claude made systematic errors with relative file paths after `cd`
- Fix: require absolute paths in tool description + validate server-side
- Generalizable: constrain tool inputs so common mistakes become structurally impossible
- Prefer formats close to internet-natural text; avoid formats requiring accurate count-keeping (diffs)

**MCP tool output schemas (CodeAct pattern)** (MEDIUM)
- Source: MCP spec 2025-06-18+; HuggingFace blog (llchahn, Aug 2025); Anthropic Engineering
- Add `outputSchema` to MCP tool definitions → agents know return structure before calling
- Enables CodeAct: write precise code against known struct vs. exploratory print-inspect loops
- Anthropic Programmatic tool calling: tool results NOT added to context — only final code output is
- Reported: up to **98.7% token savings** in tool-heavy workflows
- For Hermes: extend graphiti MCP tools with typed output schemas

---

## 3. AGENT LOOP LATENCY

**Session-as-event-log + selective `getEvents()` loading** (MEDIUM)
- Source: https://www.anthropic.com/engineering/managed-agents (Apr 2026)
- Store full session as ordered event log outside context window (SQLite works)
- Selectively load positional slices: `getEvents(from, to)` by turn, not full history
- Harness transforms fetched events before injecting → can organize for high cache hit rate
- Anthropic result: **p50 TTFT dropped ~60%, p95 dropped >90%** with decoupled architecture
- Hermes session DB is structurally close — key change: feed only relevant slices, keep full log

**Lazy sandbox provisioning** (MEDIUM)
- Source: Anthropic Managed Agents (Apr 2026)
- Don't provision execution containers until needed via tool call
- Sessions that don't need a container right away don't wait for one
- Inference starts as soon as orchestration layer sees pending events
- This pattern alone drove the 60% p50 TTFT improvement

---

## 4. STRUCTURED OUTPUT / CONSTRAINED GENERATION

**`output_config.format` + Pydantic** (⚡ LOW)
- Source: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
- Replace manual JSON prompting with: `client.messages.parse(output_format=MyPydanticModel)`
- SDK auto-derives schema, validates response, returns typed `parsed_output`
- Constrained decoding → always valid JSON, no parse errors, no retries needed
- Works with `strict: True` tool use simultaneously
- `output_config.format` is the new stable param (was beta `output_format`)
- Incompatible with: citations, message prefilling

**Schema transformation pipeline (SDK)**:
1. Remove unsupported constraints (min/max/minLength) → move to `description`
2. Add `additionalProperties: false` to all objects
3. Filter string formats to supported list
4. Validate response against original schema with full constraints

**Batch processing discount applies** (LOW)
- Structured outputs work with Batch API → 50% cost discount
- Streaming also works with structured outputs

---

## 5. MEMORY WRITE QUALITY

**What makes a Hindsight entry actually useful later**:

From cross-source synthesis (no single paper — practitioner consensus):
1. **Named fields > prose blobs** — store `{subject, predicate, object, confidence, memory_type}` not a sentence. Retrieval engines match fields; they struggle with semantically dense prose.
2. **Include counterfactual** — "X was tried, failed because Y, Z worked instead." Hindsight without failure context is half the signal.
3. **Recurrence gate before writing** — only promote to Hindsight if the fact recurred across ≥2 sessions (from RecMem pattern in llm-agent-memory-pipeline-research main skill). Single-session facts bloat storage.
4. **`outcome_type` tag** — `preference|correction|discovery|failure` lets retrieval filter by signal type. Corrections and failures have highest utility at write time; preferences degrade fastest.
5. **Source session anchor** — `source_session_id` + `session_turn` enables reconsolidation and provenance. Without it, you can't detect drift or contradiction with earlier claims.
6. **Contradiction-first, not append-first** — before writing, query Hindsight for cosine > 0.85 matches. If found: flag contradiction, update `valid_to` on old, supersede. Append-only creates conflicting facts that confuse retrieval.

---

## 6. SKILL ROUTING

**LiteLLM complexity-tier auto-router** (MEDIUM)
- Source: LiteLLM v1.97.0-rc.1 (Aug 8 2026): `feat(auto-router): track turns per complexity tier`
- Router tracks per-turn counts by complexity tier, routes to Haiku vs Sonnet automatically
- No upfront manual classification — observable turn signals drive the routing
- Estimated savings: 30–60% cost reduction if 50%+ of turns qualify for Haiku routing
- Anthropic officially recommends routing easy/common to Haiku, hard/unusual to Sonnet

**Hybrid embedding + keyword routing** (MEDIUM):
- Pure keyword: fast, brittle to paraphrase
- Pure embedding: slow (embedding call), handles paraphrase well
- Hybrid (keyword gate first → embedding fallback): best of both; keyword handles 60–70% of cases; embedding handles the tail
- For Hermes skill routing: existing semantic skill routing uses embedding; add keyword pre-filter for common trigger phrases (saves ~2 embedding calls per matched keyword)

---

## 7. COST MONITORING

**CacheLens local cost proxy** (⚡ LOW)
- Source: https://github.com/stephenlthorn/cache-lens (HN Show HN, Mar 2026)
- Local HTTP proxy (Python/FastAPI/SQLite, ~3K LOC); set `ANTHROPIC_BASE_URL` to localhost
- Tees byte stream with zero added latency; records token usage, cost, cache hit rates
- Cacheability scorer via diff-based detection across calls (~85% multi-call accuracy)
- Prometheus `/metrics` endpoint; budget caps that BLOCK requests before overspend
- Identifies repeated prompt patterns and cache misses

**Inward circuit breaker on API spend** (⚡ LOW)
- Source: https://yingjiezhao.com/en/articles/Usage-Circuit-Breaker-for-Cloudflare-Workers (HN Show HN, Mar 2026)
- Monitor own API spend as a health signal; trip at 90% of budget, recover at 85% (hysteresis prevents oscillation)
- Fail-safe: if usage API is down, maintain last-known state (don't assume "everything fine")
- Alert dedup: one alert per resource per month, not one per check cycle
- Implementation: poll Anthropic usage API every 5 min, write state to SQLite, check on each call
- Pattern applies to any metered API (Anthropic, OpenAI)

---

## 8. ERROR RECOVERY

**Per-resource threshold circuit breaker** (LOW):
- Different resources have different overage costs → different trip thresholds
- E.g., cheap resources warn at 80%, expensive ones trip at 90%
- Key insight: not all resources are equally dangerous; configure warn-only for some

**Harness-as-cattle recovery pattern** (HIGH — from Managed Agents):
- Decouple harness from sandbox so harness can crash and restart independently
- Session log lives outside harness → harness restores via `wake(sessionId)` + `getSession(id)`
- Container failures become tool-call errors Claude can retry/handle
- No more "nurturing" stuck containers; failed harnesses become new fresh harnesses
- Security: credentials never held in sandbox; OAuth tokens in vault, accessed via proxy

---

## 9. AGENT OBSERVABILITY

**OpenInference 5-point instrumentation** (MEDIUM)
- Source: https://www.arthur.ai/blog/best-practices-for-building-agents-part-1-observability-and-tracing (Feb 2026)
- OpenInference > OTEL GenAI conventions for LLM: richer metadata, first-class RAG spans
- `pip install openinference-instrumentation-*` + 3 lines of setup code
- 5 mandatory instrumentation points:
  1. Every LLM call: prompts, completions, model config, token counts, cost
  2. Tool invocations: inputs, outputs, latency
  3. RAG retrieval: which docs returned, which NOT returned, why
  4. User/session metadata: user ID, session ID, domain identifiers
  5. Key decision points: manual spans at agent choice junctions

**LLM-as-Judge categorical scoring** (MEDIUM)
- Source: Langfuse blog (Apr 2026); LangSmith runtime controls
- Run lightweight Haiku judge on each production trace → categorical buckets (success/failure/partial/off-topic)
- "Rage click" detection: catch user frustration patterns before they accumulate
- <200ms overhead inline; Langfuse CI/CD integration triggers evaluators per deploy

**Key metrics to track**:
- TTFT (time to first token) per session
- Cache hit rate per call (from `response.usage.cache_read_input_tokens`)
- Tool call success rate / retry rate
- Cost per session and per skill invocation
- Skill load → used ratio (dead-weight detection signal)

---

## 10. CONFIG MANAGEMENT

**External prompt storage + versioning** (MEDIUM)
- Source: https://www.arthur.ai/blog/best-practices-for-building-agents-part-2-prompt-management (Feb 2026)
- Store prompts outside code with explicit versions + environment tags (dev/staging/prod)
- Rollback: any version can be promoted/demoted without code deploy
- Arthur pattern: teams that treat prompts as first-class artifacts ship faster with fewer regressions

**Conditional prompt templating** (MEDIUM):
- Replace monolithic static prompts with Jinja2 templates with conditional logic
- Include only relevant instruction blocks based on context (tools available, user role, DB dialect)
- Arthur customer example: SQL agent with dozens of DB types — only relevant dialect injected
- Result: smaller prompts + more precise generation + lower cost per request

**Regression testing via trace replay** (MEDIUM):
- Instrument prompt template assembly as spans in traces
- Replay historical traces against new prompt versions before promoting to prod
- Failure cases added to dataset → iterate until new version consistently passes them
- Without this, teams fear prompt iteration → slow improvement cycle

---

## 11. NEW PYTHON LIBS / TOOLS (Aug 2026)

**openinference-instrumentation**: OpenInference semantic conventions for OTel tracing; auto-instrumentation for LangChain, LlamaIndex, Google ADK, CrewAI. https://github.com/Arize-ai/openinference

**openlit**: OpenTelemetry-based LLM monitoring library; auto-instrumentation; standard OTel GenAI conventions. `pip install openlit; openlit.init()`. https://github.com/openlit/openlit

**LiteLLM v1.97.x**: Complexity-tier auto-router now tracks turns per tier; `apply_user_budget_to_team_keys` opt-in; websearch snippet restoration for Anthropic. https://github.com/BerriAI/litellm

**LLMSim** (Rust): OpenAI-compatible LLM API simulator for load testing; configurable TTFT + inter-token latency per provider profile; error injection (429/5xx). https://github.com/chaliy/llmsim

**CacheLens**: Local cost tracking proxy; zero-latency tee; cacheability scorer; budget caps; Prometheus endpoint. https://github.com/stephenlthorn/cache-lens

**Langfuse (May 2026 update)**: Code evaluators, CI/CD-triggered experiments, Langfuse MCP integration. https://langfuse.com

**smolagents** (HuggingFace): Lightweight CodeAct agent framework; pairs with MCP output schemas for single-step execution vs. multi-step exploratory patterns. https://huggingface.co/docs/smolagents

---

## QUICK WINS RANKED (lowest effort, highest impact)

| Priority | Technique | 1-line implementation |
|----------|-----------|----------------------|
| 1 | Auto cache_control | `cache_control={"type":"ephemeral"}` top-level |
| 2 | strict:true on tools | `"strict": True` in each tool dict |
| 3 | output_config.format | `client.messages.parse(output_format=MyModel)` |
| 4 | 1h TTL system prompt | `{"type":"ephemeral","ttl":"1h"}` on system block |
| 5 | max_tokens:0 pre-warm | pre-warm call before cron batch |
| 6 | Named output sub-fields | split response schema into named reasoning fields |
| 7 | CacheLens proxy | set ANTHROPIC_BASE_URL + run proxy |
| 8 | Spend circuit breaker | poll usage API, SQLite state, block on 90% |
