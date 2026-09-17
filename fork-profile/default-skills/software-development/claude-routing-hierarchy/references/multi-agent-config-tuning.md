# Multi-Agent Config Tuning — Verified Thresholds

> **Model reference note:** `claude-opus-4-8` in the line below is from an older
> planning draft and does not exist in the current config. Delegation model is
> `claude-sonnet-5` (verified live, see parent SKILL.md). The compression/retry/
> loop-safety threshold recommendations below are otherwise still applicable.

**Basis:** Holistic Hermes audit (2026-06-30 20:16–20:23, orchestrated by claude-opus-4-8).


## Compression & Context

When delegating in parallel waves (e.g., 3 subagents returning findings simultaneously):

| Setting | Old | New | Rationale |
|---------|-----|-----|-----------|
| `compression.target_ratio` | 0.2 | 0.33 | 0.2 over-compresses multi-agent context; loses synthesis fidelity. 0.33 preserves decision signal in fan-out merges. |
| `compression.protect_last_n` | 20 | 32 | Single fan-out wave can produce 25–30 messages (agent starts, agent progress, agent finishes, parent synthesizes); 20 evicts too early. |
| `auxiliary.compression.max_tokens` | 2048 | 4096 | Avoid truncated summaries on large 128k sessions; aux compression is where synthesis/routing lives. |
| `prompt_caching.cache_ttl` | 5m | 1h | 5m evicts cache between 30m delegation waves (dispatch→wait→results→synthesize→next wave). 1h keeps cache warm across full session. |

## Retry & Discovery

Long fan-out chains experience transient failures:

| Setting | Old | New | Rationale |
|---------|-----|-----|-----------|
| `agent.api_max_retries` | 1 | 3 | Single retry insufficient for 429/5xx in long chains. 3 allows temporary spikes without cascade failure. |
| `mcp_discovery_timeout` | 0.5 | 3 | qmd `connect_timeout: 45` but 0.5s intermittently drops knowledge base. Misalignment burns retries. 3s ensures qmd is reachable. |

## Loop Safety

Runaway loops in multi-agent context:

| Setting | Old | New | Rationale |
|---------|-----|-----|-----------|
| `tool_loop_guardrails.hard_stop_enabled` | false | true | Warn-only does not stop runaway loops. Hard stop enforces termination and prevents cascade. |

## Application Pattern

**When to apply:** Delegation sessions with 3+ parallel subagents OR >30m session duration with intermediate synthesis steps.

**When NOT to apply:** Simple single-agent work, brief <5m sessions, local-only operations.

**Verification:** Monitor in live use:
- Compression ratio 0.33 token savings vs. synthesis fidelity (watch synthesis quality in merged findings)
- Cache hit rate under load (check `prompt_caching.cache_ttl` effectiveness in logs)
- Retry counts on delegation (should drop after config; if still high, re-check network/MCP health)

## Related Skills

- `hermes-agent-sync` — structured findings merge that benefits from tuned compression
- `hermes-context-packet` — spawn packet assembly; relies on compression.protect_last_n to preserve context
- `hermes-role-pipelines` — orchestration patterns that depend on these thresholds
