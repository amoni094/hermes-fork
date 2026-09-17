# Skill Size Extraction — Operational Workflow

Validated Aug 2026 during the `comparative-religion-corpus` 74KB→39KB refactor.

## Tool Sequence

### Step 1 — Parallel reads (batch in one turn)
```
read_file(path=SKILL.md, offset=1, limit=2000)        # get total_lines + section headings
search_files(path=references/, pattern='*', target='files')  # inventory existing refs
```
Both are independent — fire simultaneously. The line count tells you how many
read_file chunks you'll need (each chunk is up to 2000 lines).

### Step 2 — Read target sections
Page through the file in 2000-line chunks using offset/limit.
You only need to read sections you plan to extract — not the whole file.

### Step 3 — Check before extracting
For each candidate section, check whether a references/ file already covers it:
- If YES: replace inline with a pointer only. Do NOT rewrite the references/ file.
- If NO: write the full extracted content to references/[name].md via write_file.

Duplicate content in references/ is as bad as duplicate content inline.

### Step 4 — Extract and replace
**Use the `patch` file-edit tool** (not skill_manage) for find-and-replace on SKILL.md:
```python
patch(mode='replace',
      path='/path/to/SKILL.md',
      old_string='## Section Name\n\n<full section content...>',
      new_string='## Section Name\n\n<1-sentence summary>: see `references/file.md`.')
```
The `patch` tool uses fuzzy matching — include the `##` heading + first paragraph as
old_string context to make the match unique. Multi-hundred-line old_strings work fine.

### Step 5 — Track progress
After each replacement: `terminal("wc -c /path/to/SKILL.md")`
Target: under 50KB (51,200 bytes) for comfortable headroom.

### Step 6 — Serial execution order
Each patch depends on the prior file state (find-and-replace is positional).
Plan all replacements upfront from a single read, then fire in sequence.
Do NOT re-read between patches unless the file state is uncertain.

## Pointer format (replace each extracted section with this)

```markdown
## [Section Name]

<One-sentence description of what the section covers.>
See `references/[filename].md`.
```

For pitfall catalogues, keep a 5-bullet quick index inline:
```markdown
## ChromaDB Pitfalls (chromadb 1.5.x)

See `references/chromadb-pitfalls.md` for full details. Quick index:

- **Short pitfall name** (§N): one-line fix
- ...
```

## Size thresholds (from hermes-skill-library-consolidation-audit main body)

- < 30KB: healthy
- 30–50KB: monitor (check if any section > 5KB is a knowledge bank, not procedure)
- 50–80KB: extract now
- > 80KB: urgent (writes may fail)

## What belongs in references/ vs inline

| Extract to references/ | Keep inline |
|------------------------|-------------|
| Stats tables, counts, chunk inventories | Numbered procedural steps |
| Project layout file trees | Quick-reference checklists |
| Large pitfall narratives with code | Single-command snippets |
| Paper lists, annotated source catalogues | 5-bullet pitfall summaries (with pointer to full) |
| Full code recipes > 50 lines | Trigger conditions |
| Content already partially in an existing refs/ file | Section headers and orientation prose |
