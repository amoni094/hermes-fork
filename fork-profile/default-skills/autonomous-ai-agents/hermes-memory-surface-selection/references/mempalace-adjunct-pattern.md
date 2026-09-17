# MemPalace adjunct pattern

Use this pattern when evaluating MemPalace or a similar MCP-exposed memory system.

## Recommendation
Treat MemPalace as an adjunct retrieval layer, not a replacement for Hermes built-in durable memory.

## Why
- Hermes durable memory is optimized for a small set of stable facts that should auto-influence future chats.
- `session_search` already covers prior-conversation recall well.
- qmd is a better canonical surface for curated local notes and vault pages.
- MemPalace is strongest when used for broader archive/project recall that should stay outside Hermes core prompt memory.

## Practical routing
- Stable user/environment fact -> Hermes durable memory
- Prior Hermes conversation -> `session_search`
- Maintained local note/doc -> qmd
- Broad imported archive or exploratory recall -> MemPalace

## Integration note
If Hermes needs a stable local launcher path, a wrapper script that execs
`uvx --from mempalace mempalace-mcp "$@"`
is a clean stdio-MCP entrypoint.

## Anti-pattern
Do not respond to a promising external memory system by immediately merging it into Hermes core memory or context-compression behavior. Prefer MCP first, then deepen only if MCP is insufficient.
