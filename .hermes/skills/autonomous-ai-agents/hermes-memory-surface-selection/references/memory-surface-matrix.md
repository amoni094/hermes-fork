# Memory surface matrix

| Need | Best surface | Why |
|---|---|---|
| Stable preference or environment fact | Hermes durable memory | Small, durable, auto-injected |
| Prior chat decision / debugging history | `session_search` | Exact conversational provenance |
| Curated vault/doc knowledge | qmd | Canonical local documents with path/heading retrieval |
| Large external/project archive recall | MemPalace | Richer adjunct retrieval without bloating core memory |

## Routing examples

- User preference, style, timezone, recurring convention
  - save to Hermes durable memory
- "What did we decide earlier?"
  - use `session_search`
- "Open the note/page/doc about X"
  - use qmd
- "Search this imported archive / broad memory corpus"
  - use MemPalace

## Practical stance
- Prefer the smallest, most canonical retrieval surface.
- Prefer qmd over MemPalace for maintained local notes.
- Prefer MemPalace over stuffing large material into Hermes durable memory.
- Prefer `session_search` before asking the user to restate prior chat context.
