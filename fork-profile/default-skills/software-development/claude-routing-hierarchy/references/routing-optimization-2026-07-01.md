# Routing Optimization Session — 2026-07-01

> **SUPERSEDED — do not use as current state.** This session referenced Groq and
> Google Gemini as live providers and cited models (`sonnet-4-6`, `opus-4-8`,
> `fable-5`) that do not exist in the current config. Verified live state
> (2026-07-05/06) is in the parent `claude-routing-hierarchy/SKILL.md`: only
> Anthropic (claude-sonnet-5, single tier), OpenAI, Cerebras, SambaNova, and
> Mistral are configured. Groq and Gemini have no API key and are NOT in the
> routing chain. Kept for historical record only.

## Changes made this session

### Delegation tier clarified (user correction)
User explicitly defined a three-tier model ladder. Prior config had Opus as delegation default, which was slow.

| Tier | Model | Trigger |
|------|-------|---------|
| Default workers | sonnet-4-6 | All delegate_task calls unless overridden |
| Escalation | opus-4-8 | User explicitly asks, OR: research tasks, 3+ agent fan-out, arch/security, conflicting-result synthesis |
| Max reasoning | fable-5 | User says "use fable" — single prompt only, never a session pin |

Config change: `hermes config set delegation.model claude-sonnet-4-6`

### Fallback chain reordered (speed optimization)
Old: gemini → groq → sambanova → cerebras
New: groq → gemini → cerebras → sambanova

Rationale: Groq has lowest latency (~320 tok/s). Gemini second for large-context safety net. Cerebras third for high-RPD short tasks. SambaNova last (20 RPD, quality reserve).

### Auxiliary slots moved off Gemini (speed)
Three slots were on Gemini unnecessarily — no multimodal or long-context requirement:

| Slot | Before | After | Why |
|------|--------|-------|-----|
| title_generation | gemini/gemini-2.5-flash | cerebras/gpt-oss-120b | Trivially short; cerebras is fastest |
| skills_hub | gemini/gemini-2.5-flash | groq/llama-3.3-70b | No multimodal needed; groq faster |
| profile_describer | gemini/gemini-2.5-flash | groq/llama-3.3-70b | One-off; no reasoning depth needed |

Gemini retained only for: kanban_decomposer (may include images), curator (may be long-context).

### MCP auxiliary added
New: `auxiliary.mcp` → groq/llama-3.3-70b-versatile (was unset/auto)

## Opus-for-research delegation pattern
To use Opus for a single research/analysis task without changing session defaults:
```
delegate_task(
  goal="...",
  context="...",
  toolsets=["web", "terminal"],
  # No model override field in delegate_task — Opus used via delegation config temp-override
)
```

Note: As of this session, delegate_task does not accept a per-call model override field directly in the tool schema visible to the agent. To use Opus for a specific task, temporarily set `delegation.model` in config, dispatch, then restore — OR accept that the background subagent runs on the configured delegation model (sonnet-4-6 by default).

The Opus research task dispatched this session used the configured delegation.model at dispatch time. Verify actual model used by checking the task ledger.

## Key insight: Cerebras vs Groq split
- Cerebras: highest RPD (14.4K), fastest tok/s (~2600), but HARD 8K context cap. Use for all classification/labeling/short-output tasks.
- Groq: lower RPD (1K), still fast (~320 tok/s), 131K context. Use for tasks that might exceed 8K (code review snippets, skill hub queries, MCP routing).
- Never use Cerebras for anything that might send >8K tokens — it silently truncates or errors.
