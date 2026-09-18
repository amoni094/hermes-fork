---
name: anthropic-api-cost-optimization
description: "Use when cutting Anthropic API costs via caching or schemas."
version: 1.0.0
triggers:
  - "reduce API costs"
  - "prompt caching"
  - "cache_control"
  - "cache hit rate"
  - "token savings"
  - "API cost monitoring"
  - "structured output anthropic"
  - "output_config.format"
  - "strict tool use"
  - "circuit breaker API spend"
  - "LLM cost"
  - "cache miss"
  - "budget guard"
related_skills:
  - hermes-observability-and-task-ledger
  - hermes-context-hygiene
  - claude-routing-hierarchy
---

# Anthropic API Cost Optimization

> Verified Aug 2026 against live Anthropic docs. All patterns apply to Hermes running
> claude-sonnet-4-6 + claude-haiku-4-5 via direct API.

## Quick Wins (LOW complexity — implement immediately)

### 1. Automatic top-level `cache_control`

Add ONE field to every `messages.create()` call:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},   # ← add this
    system="...",
    messages=[...]
)
```

- Cache reads cost **0.10× base input price** → 90% savings on cached tokens
- System auto-applies breakpoint to last cacheable block, advances each turn
- Sonnet 4.6: $0.30/MTok cached vs $3/MTok base
- Works on all active models (Sonnet 4.6, Haiku 4.5, Opus 4.x)

Track hits via `response.usage.cache_read_input_tokens` vs `cache_creation_input_tokens`.

### 2. 1-hour TTL for static system prompts

```python
system=[{
    "type": "text",
    "text": "You are...",
    "cache_control": {"type": "ephemeral", "ttl": "1h"}  # ← 1h for system prompt
}]
```

- Standard 5-min TTL misses cache when cron agents restart every 30+ min
- Cost: 2× base on writes; pays back on 2nd read within 1 hour

### 3. `max_tokens: 0` pre-warming

```python
# Call before agent loop (cron start, batch start)
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=0,           # ← zero: no output, no output tokens billed
    system=[{"type": "text", "text": SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
    messages=[{"role": "user", "content": "ping"}]
)
# First real call immediately hits warm cache
```

Better than old `max_tokens: 1` — no token to discard, intent clear.

### 4. `strict: True` on all tool definitions

```python
tools = [{"name": "my_tool", "strict": True, ...}]
```

- Grammar-constrained sampling → schema-compliant every call
- Eliminates hallucinated fields, retry loops
- Compatible with `output_config.format` simultaneously

### 5. `output_config.format` + Pydantic (replaces manual JSON prompting)

```python
from pydantic import BaseModel
from anthropic import Anthropic

class MyOutput(BaseModel):
    reasoning: str
    answer: str
    confidence: float

response = Anthropic().messages.parse(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{"role": "user", "content": "..."}],
    output_format=MyOutput,     # SDK derives schema + validates
)
result = response.parsed_output  # typed MyOutput instance
```

- Constrained decoding → always valid, no parse errors, no retries
- Eliminates retry cost (each retry = 100% token overhead)
- `output_config.format` is the stable param (replaces beta `output_format`)
- Incompatible with: citations, message prefilling

### 6. Named sub-fields as schema-level CoT (⚡ HIGH ROI, LOW effort)

Instead of `{"suggestion": "..."}`, use:
```json
{"reasoning": "...", "concise_suggestion": "...", "confidence": "high|medium|low"}
```

- Named fields act as CoT scaffolding without explicit CoT prompting
- Use `description` field on each property — free steering
- Reported: 20–40% fewer hallucinated values

### 7. Poka-yoke tool inputs

From Anthropic SWE-bench team: Claude made systematic errors with relative file paths.
Fix: require absolute paths in description + validate server-side. General principle:
constrain tool inputs so common mistakes are structurally impossible.

---

## Pricing Reference (Aug 2026)

| Model | Base Input | 5m Cache Write | 1h Cache Write | Cache Read |
|-------|-----------|----------------|----------------|------------|
| Sonnet 4.6 | $3/MTok | $3.75 | $6 | $0.30 |
| Haiku 4.5 | $1/MTok | $1.25 | $2 | $0.10 |
| Opus 4 | $15/MTok | $18.75 | $30 | $1.50 |

Batch API: 50% discount, compatible with structured outputs and prompt caching.

---

## Cost Monitoring

### CacheLens local cost proxy
```bash
pip install cache-lens
# Set ANTHROPIC_BASE_URL=http://localhost:8080 in Hermes .env
```

- Zero-latency stream tee; cacheability scorer (~85% multi-call accuracy)
- Budget caps that **block** requests before overspend
- Prometheus `/metrics` endpoint; identifies repeated prompt patterns
- Source: https://github.com/stephenlthorn/cache-lens

### Inward circuit breaker on API spend

```python
def check_budget_breaker():
    ratio = get_anthropic_usage_this_month() / MONTHLY_BUDGET
    if ratio >= 0.90: set_breaker_state("OPEN")
    elif ratio <= 0.85: set_breaker_state("CLOSED")  # hysteresis
    return get_breaker_state()
```

- Trip at 90%, recover at 85% (hysteresis prevents oscillation)
- Fail-safe: if usage API is down, maintain last-known state
- Alert dedup: one alert per resource per billing period
- Source: https://yingjiezhao.com/en/articles/Usage-Circuit-Breaker-for-Cloudflare-Workers

---

## Caching Architecture

### Explicit + auto combined (recommended for Hermes)

```python
messages.create(
    cache_control={"type": "ephemeral"},   # auto: conversation history (5m TTL)
    system=[{
        "type": "text",
        "text": LARGE_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral", "ttl": "1h"}  # explicit: system (1h TTL)
    }],
    messages=conversation_history
)
```

### Caching tool definitions

```python
# Place cache_control on the LAST tool
tools = [
    {"name": "tool_a", ...},
    {"name": "tool_b", ..., "cache_control": {"type": "ephemeral"}}  # caches all above
]
```

---

## MCP Output Schemas (MEDIUM complexity, very HIGH impact)

MCP spec 2025-06-18+ added `outputSchema` for tools. Enables CodeAct pattern:
agents know return structure before calling → single-step programs vs. exploratory loops.

Anthropic Programmatic tool calling: tool results NOT added to context window.
**Reported: up to 98.7% token savings in tool-heavy workflows (unverified HuggingFace blog claim — treat as illustrative upper bound, not a benchmarked result).**

For Hermes: add typed return schemas to graphiti MCP tools.
Source: https://huggingface.co/blog/llchahn/ai-agents-output-schema

---

## RACS: Stability-Rank Ordering and Prefix-Drift Detection (github:davccavalcante/racs, Sweep 16)

RACS formalizes what should already be intuitive but often isn't enforced: context blocks should
be ordered most-stable-first to maximize provider-side prefix cache hits.

**Stability-rank ordering (order context blocks by mutation frequency):**

| Rank | Block | Mutation frequency | Position in prompt |
|---|---|---|---|
| 1 (most stable) | System prompt | Never changes mid-session | TOP — always first |
| 2 | Persona / role | Changes only on explicit task switch | After system prompt |
| 3 | Loaded skills | Changes only when a new skill is loaded | After persona |
| 4 | Injected memories | Changes per-turn if new facts arrive | After skills |
| 5 (least stable) | Conversation history | Changes every turn | BOTTOM — always last |

**Note for racs-prefix-tracker.py:** The script tracks system_prompt, skills, and memories as the drift-monitored set. However, memories changes per-turn when new Hindsight facts arrive, generating expected drift events. Treat memories drift as informational only. Only system_prompt and skills drift indicate unexpected cache breaks worth investigating.

This is the ordering Hermes already uses structurally (system > memory > tools > conversation).
RACS makes it explicit and adds two new mechanisms:

**Prefix-drift detection:**
When assembling the prompt, compare the current prefix hash against the previous turn's prefix hash.
If the hash changed for blocks ranked 1–3 (system, persona, skills), log a `prefix_drift` event —
these changes break the provider-side cache and incur re-computation cost. Flag the cause:
- System prompt edit → intentional, expected
- Skill loaded mid-session → expected, note it
- Memory injection changed stable section content → investigate; may indicate memory write-path bug

In Hermes: compare prompt hashes across turns manually using racs-prefix-tracker.py.
Note: `hermes config set context.log_prefix_drift` is not a supported config key.
The script at ~/.hermes/scripts/racs-prefix-tracker.py is the current implementation;
it must be called manually from execute_code or a cron script.

**RACS prefix-drift logging (`racs-prefix-tracker.py`):**
The Anthropic API returns `cache_read_input_tokens` when prompt caching is active. Unexpected
drops to zero indicate a prefix-drift event where a stable block changed and broke the cache.
Hash stable context blocks per turn and log those events with
`~/.hermes/scripts/racs-prefix-tracker.py` (`track_turn(session_id, turn_num, blocks)`).
Blocks = `{system_prompt, skills, memories, history}`; only the first three are drift-tracked.
Logs: `~/.hermes/logs/prefix-drift.jsonl`. Report: `python3 ~/.hermes/scripts/racs-prefix-tracker.py --report`.

**TTL keep-warm scheduling:**
Anthropic's prompt cache TTL is 5 minutes (ephemeral) or 1 hour (extended). For long-running
sessions or cron jobs with infrequent turns, schedule a lightweight "keep-warm" ping before TTL
expiry to preserve the cached prefix. For cron jobs that run every 30+ minutes: add a no-op
heartbeat turn at the 4-minute or 55-minute mark to refresh the TTL.

**Practical ordering rule for delegate_task context packets:**
When building a context packet for a subagent, put the most stable content first:
```
context = f"""
{SYSTEM_INSTRUCTIONS}       # never changes — rank 1
{loaded_skill_content}      # changes per task type — rank 3
{prior_findings_summary}    # changes per batch — rank 4
{conversation_excerpt}      # changes per turn — rank 5 (keep minimal)
"""
```

## Anthropic Batch API — 50% Cost Reduction for Non-Latency Tasks (agent-improvements-2026-08.md)

For any task where the user doesn't need an immediate response, use the Batch API:
- 50% cheaper than synchronous Messages API
- Accepts up to 10,000 requests per batch
- Results available within 24 hours (usually <1 hour)
- Same models, same tool use, same output quality

**Hermes use cases:**
- l1-promote.py Hindsight writes (currently synchronous, could batch overnight)
- Bulk skill analysis/scoring (SkillOpt, RUMBA eval runs)
- Overnight research synthesis across many documents
- Any cron job where output is consumed next session, not immediately

```python
batch = client.messages.batches.create(
    requests=[
        {"custom_id": f"item-{i}", "params": {
            "model": "claude-haiku-4-5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }}
        for i, prompt in enumerate(prompts)
    ]
)
# Poll: client.messages.batches.retrieve(batch.id)
# Results: client.messages.batches.results(batch.id)
```

**Routing rule:** use Batch API when: cron job, no user waiting, result consumed >1 min from now.
Do NOT use for: interactive tasks, streaming, tool-use loops requiring real-time routing.

## ReCache — Resource-Wise KV Block Caching Per Tool/Skill (Sweep 20) <!-- why: mid-session skill injection in the middle of a stable prefix invalidates downstream cache; append-only stable order preserves it -->

Tool schemas and skill bodies should be cached as independent KV blocks at session start, assembled from cache for subsequent turns. Mid-session skill injection in the middle of a stable prefix invalidates everything downstream.

Hermes application:
1. Load skills in a fixed stable order at session start; append new skills AFTER the current stable prefix
2. Avoid dynamic content (timestamps, session IDs) inside the stable prefix blocks
3. When context compression fires and skill bodies are evicted, re-inject at the END of the new prefix — not interleaved with system prompt or tools
4. Pairs with RACS prefix ordering: system → skills → memories → conversation history (most → least stable)

**1. RACS Stability-rank ordering:**
Order prompt sections by stability (least-likely to change → most-likely to change):
```
[Most stable]    System prompt + tool schemas       ← cache with ttl=1h
[Stable]         Injected skill content              ← cache with ttl=5m
[Semi-stable]    Memory / Hindsight injections       ← cache with ttl=5m
[Volatile]       Current conversation turn           ← never cached
[Most volatile]  Tool results                        ← never cached
```
Violating this order (e.g. putting memory before tools schemas) causes cache misses because
the prefix changes every turn. RACS shows this accounts for ~40% of unnecessary cache misses.

**Hermes implication:** The system prompt + tool list is already the most stable prefix and
Anthropic auto-caches it. The risk is injected skill content appearing AFTER memory injections
in the context — if memory injections vary per turn, they break the skill cache slot.
Keep skill injections before memory injections in context order.

**2. Prefix-drift detection:**
If `cache_read_input_tokens` drops suddenly across consecutive calls (same session, same tools),
a prefix drift occurred — something changed upstream of the cached block.
Common causes: skill injection order changed, memory injection added new content, tool schema
updated mid-session. Debug by checking which prefix block changed length since last call.

**3. TTL keep-warm scheduling:**
For cron jobs that call Anthropic on a fixed schedule (e.g. every 30m), the 5-minute cache TTL
means the cache is cold by the time the next call arrives. Options:
- Use `ttl: "1h"` cache_control on stable blocks when the cron interval > 5 min.
- Or: fire a cheap pre-warm call (e.g. `max_tokens: 1`) 4 minutes before the scheduled cron
  to reset the TTL. The pre-warm costs ~$0.001 but saves the full cache miss on the main call.
- RACS recommends keep-warm only for calls with > 10K cached tokens (savings > cost threshold).

**Pitfall:** Keep-warm calls must have byte-identical prefix to the main call. Any difference
(even whitespace) produces a cache miss and wastes the keep-warm cost. Test with
`cache_read_input_tokens > 0` in the keep-warm response before relying on it.

## Pitfalls

- **JSON parsing from text-prompt LLM output**: when using haiku-4-5 (or any model) with
  a prompt that asks for JSON but WITHOUT `output_config.format`/Pydantic, the model
  sometimes embeds unescaped quotes inside string values. Bare `json.loads(raw)` fails.
  Use `json.JSONDecoder().raw_decode(raw, idx=raw.find('{'))` as primary parser; fall back
  to `json.loads(raw[raw.find('{'):raw.rfind('}')+1])` on `JSONDecodeError`. Also strip
  markdown fences first: `re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)`.
  Prefer `output_config.format` when the output schema is known — grammar-constrained
  decoding eliminates this problem entirely.

- **Cache miss on cron**: use `ttl: "1h"` not default 5m when cron interval > 5 min.
- **Cache breaks silently**: requires byte-identical prefix. If `cache_read_input_tokens`
  is consistently 0, something changed the prefix upstream.
- **4-slot limit**: max 4 explicit `cache_control` breakpoints per request. Auto caching
  uses one slot. Budget: system (1h) + tools + auto = 3 explicit slots consumed.
- **Structured outputs + citations incompatible**: returns 400 error.
- **`max_tokens: 0` rejected with stream/structured output**: pre-warm call must be plain.
- **Tool count overprovisioning**: keep under 10 active tools per session, 80 total.

## Cache Placement Discipline — Fan-out Preamble Rule

For rules 1–4 (stable prefix ordering, volatile bytes above the fold, mid-session changes as appended messages, tool surface stability), see the RACS and ReCache sections above — they cover these fully with Anthropic-specific TTL guidance.

One additional rule for parallel fan-outs not covered by RACS/ReCache:

**Rule 5 — Fan-outs share a byte-identical preamble.** Sibling prompts lead with the same shared bytes; unit-specific content appended after. Stagger dispatch so the first request writes the cache entry the siblings then read. If siblings fire simultaneously, each pays the cache-write cost independently.

Evidence boundary: cache hit and creation counters are provider telemetry. Never claim a hit rate, saving, or "cache-safe" as observed fact without the host's usage counters.

<!-- why: fan-out preamble stagger is the one rule not covered by the RACS/ReCache sections above; the others are already present with better Anthropic-specific detail -->

## References

- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Structured outputs: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
- Strict tool use: https://docs.anthropic.com/docs/en/agents-and-tools/tool-use/strict-tool-use
- Building effective agents (tool design): https://www.anthropic.com/engineering/building-effective-agents
- Full Aug 2026 sweep: `llm-agent-memory-pipeline-research/references/anthropic-api-agent-engineering-aug2026.md`

## TALE — Token-Allocated Length Enforcement (prompt budget hints)

TALE adds a budget-hint comment at the top of any long prompt: `# BUDGET: ~N tokens`. The
model uses it as a soft cap to self-trim completions early. Useful when:
- sending bulk prompts to Batch API where completion length is unpredictable
- feeding long chain-of-thought prompts where reasoning output inflates cost

Pattern: prepend `# OUTPUT BUDGET: ~{N} tokens\n` before the main prompt body. N is
typically 25–40% of the context window used. TALE does NOT truncate mechanically — it's
a signal; models vary in compliance. Pair with `max_tokens` hard cap for reliability.

## LLMLingua-2 — Prompt Compression for Long Context

LLMLingua-2 (Microsoft, 2024) compresses input prompts 2–5× with <5% quality loss by
removing semantically redundant tokens. Worth applying to long reference documents sent as
context in skill-audit sweeps or research synthesis runs. Not built into Hermes; invoke via
the `llmlingua` Python package as a preprocessing step before expensive batch calls.

## Theory-Grounded Cost Optimization

### Occam Factor / Marginal Likelihood for Model Upgrade Decisions (MacKay Ch 28)

**Theory:** The marginal likelihood of a model includes an "Occam factor" that penalizes model complexity: P(data|model) = likelihood × Occam_penalty. A more complex model must improve likelihood enough to overcome this penalty. MacKay Ch 28 shows that the penalty scales with the number of additional parameters.

**Hermes rules:**
- Prefer a cheaper model when the marginal likelihood improvement from upgrading does not exceed the Occam penalty for added complexity.
- Concrete rule: if task success rate improves < 5% on an upgrade from a cheaper to a more expensive model, stay on the cheaper model — the marginal gain does not justify the complexity cost.
- Benchmark before committing: run 10 representative tasks on both models; if delta < 5%, the Occam factor dominates — the upgrade is not justified.

**Citation:** David MacKay — *Information Theory, Inference, and Learning Algorithms*, Ch 28 (Model Comparison and Occam's Razor).

### Newton Decrement Stopping for Parameter Tuning (Boyd Ch 9.4)

**Theory:** Newton's method for convex optimization has a stopping criterion based on the Newton decrement: λ²/2, where λ = ‖∇f(x)‖_{H⁻¹} is the Newton step length in the Hessian norm. When λ²/2 < ε, the gap to the optimum is bounded by ε — further iterations yield negligible improvement.

**Hermes rules:**
- When iterating cache prefix lengths, prompt budget parameters, or other continuous optimization parameters, stop when the Newton decrement λ²/2 < 0.001.
- Practical proxy: stop when marginal cache hit rate improvement per iteration < 0.1% (three consecutive measurements).
- Do NOT run more tuning iterations after this threshold — the remaining gain is below noise level.

**Citation:** Boyd & Vandenberghe — *Convex Optimization*, Ch 9.4 (Newton's Method — Newton decrement stopping criterion).
