# Memory surface matrix

| Need | Best surface | Why |
|---|---|---|
| Stable preference or environment fact | Hermes durable memory | Small, durable, auto-injected |
| Prior chat decision / debugging history | `session_search` | Exact conversational provenance |
| Curated vault/doc knowledge | Obsidian / `read_file` + `session_search` | qmd DISABLED — do not call `mcp_qmd_*` |
| Episodic/cross-session fact recall | Hindsight (`hindsight_recall` / `hindsight_reflect`) | Semantic recall without bloating durable memory |
| Entity/relationship queries | Graphiti (`mcp_graphiti_*`) | Structured graph for temporal facts and entity links; fall back to `session_search` if Graphiti is down |
| Large external/project archive recall | `session_search` + Hindsight | MemPalace and qmd are both DISABLED |

## Routing examples

- User preference, style, timezone, recurring convention
  - save to Hermes durable memory
- "What did we decide earlier?"
  - use `session_search`
- "Open the note/page/doc about X"
  - Obsidian path via `read_file`, or `session_search` / Hindsight (qmd DISABLED)
- "Search this imported archive / broad memory corpus"
  - `session_search` + Hindsight (MemPalace and qmd DISABLED)
- "What do I know about entity X across sessions?"
  - use `hindsight_recall` or `hindsight_reflect`
- "What is the relationship between X and Y?"
  - use Graphiti if populated, otherwise `session_search`

## Practical stance
- Prefer the smallest, most canonical retrieval surface.
- Prefer Obsidian files / `read_file` for maintained local vault notes. Do not route to qmd (disabled).
- MemPalace and qmd are both DISABLED — do not call either; use `session_search` + Hindsight + Obsidian `read_file`.
- Prefer `session_search` before asking the user to restate prior chat context.
- Hindsight is for episodic/semantic recall that hasn't graduated to durable memory yet.
