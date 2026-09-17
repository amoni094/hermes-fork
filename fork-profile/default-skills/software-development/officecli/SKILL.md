---
description: 'Use when: creating, inspecting, or modifying Office documents (.docx, .xlsx, .pptx). Use the officecli CLI tool
  to analyze, proofread, find issues, add charts, or modify Office docs.'
name: officecli
triggers:
- Use the officecli CLI tool to create, inspect, or modify Office documents
- Batch processing or automation of .docx, .xlsx, or .pptx files via CLI
- AI-friendly CLI document editing without a Python/programmatic generation approach
- Legal document creation, editing tracked changes, or form fields in Word via CLI
counter_triggers:
- For Python programmatic .docx generation use the docx skill
- For Python programmatic .xlsx generation use the xlsx skill
- For professional layout with ReportLab/python-pptx use document-layout-design
related_skills:
  - docx
  - xlsx
  - pdf
---


# officecli

AI-friendly CLI for .docx, .xlsx, .pptx. Single binary, no dependencies, no Office installation needed.
Binary: ~/.npm-global/bin/officecli (installed via npm install -g @officecli/officecli)

## Install

If `officecli` is not installed:

```bash
# macOS / Linux
curl -fsSL https://d.officecli.ai/install.sh | bash

# Windows (PowerShell)
irm https://d.officecli.ai/install.ps1 | iex
```

Verify with `officecli --version`. If still not found after install, open a new terminal.

---

## Strategy

**L1 (read) → L2 (DOM edit) → L3 (raw XML)**. Always prefer higher layers. Add `--json` for structured output.

**Before doc work, check Specialized Skills** (bottom of this file). Fundraising decks, academic papers, financial models, dashboards, and Morph animations need their own skill loaded first — `load_skill` once, then proceed.

---

## Help System (IMPORTANT)

**When unsure about property names, value formats, or command syntax, ALWAYS run help instead of guessing.** One help query beats guess-fail-retry loops.

`officecli help` ≡ `officecli --help`, and `officecli <cmd> --help` ≡ `officecli help <cmd>` — same content.

```bash
officecli help                                  # All commands + global options + schema entry points
officecli help docx                             # List all docx elements
officecli help docx paragraph                   # Full schema: properties, aliases, examples, readbacks
officecli help docx set paragraph               # Verb-filtered: only props usable with `set`
officecli help docx paragraph --json            # Structured schema (machine-readable)
```

Format aliases: `word`→`docx`, `excel`→`xlsx`, `ppt`/`powerpoint`→`pptx`. Verbs: `add`, `set`, `get`, `query`, `remove`. MCP exposes the same schema via the single `command` string param: `{"command":"help docx paragraph"}` (not a structured `{"format":...,"type":...}` object — the MCP tool has exactly one param, `command`, and passes it through to the CLI verbatim).

---

## Performance: Resident Mode

**Every command auto-starts a resident on first access** (60s idle timeout) — file-lock conflicts are automatically avoided. Explicit `open`/`close` is still recommended for longer sessions (12min idle):
```bash
officecli open report.docx       # explicitly keep in memory
officecli set report.docx ...    # no file I/O overhead
officecli close report.docx      # save and release
```

Opt out of auto-start: `OFFICECLI_NO_AUTO_RESIDENT=1`.

**Flush only at the non-officecli boundary.** officecli's own reads (`get`/`query`/`view`/`dump`) always see your latest edits, so you never need to save mid-workflow. Run `save` (keeps the resident) or `close` (flush + release) only **before a non-officecli program reads the file** — python-docx/openpyxl, Word, a renderer, delivery/upload. (Idle sessions auto-flush within seconds; `OFFICECLI_RESIDENT_FLUSH=each` makes every mutation flush before returning.)

---

## Quick Start

**PPT:**
```bash
officecli create slides.pptx
officecli add slides.pptx / --type slide --prop title="Q4 Report" --prop background=1A1A2E
officecli add slides.pptx '/slide[1]' --type shape --prop text="Revenue grew 25%" --prop x=2cm --prop y=5cm --prop font=Arial --prop size=24 --prop color=FFFFFF
```

**Word:**
```bash
officecli create report.docx
officecli add report.docx /body --type paragraph --prop text="Executive Summary" --prop style=Heading1
officecli add report.docx /body --type paragraph --prop text="Revenue increased by 25% year-over-year."
```

**Excel:**
```bash
officecli create data.xlsx
officecli set data.xlsx /Sheet1/A1 --prop value="Name" --prop bold=true
officecli set data.xlsx /Sheet1/A2 --prop value="Alice"
```

---

## L1: Create, Read & Inspect

```bash
officecli create <file>               # Create blank .docx/.xlsx/.pptx (type from extension)
officecli view <file> <mode>          # outline | stats | issues | text | annotated | html
officecli get <file> <path> --depth N # Get a node and its children [--json]
officecli query <file> <selector>     # CSS-like query
officecli validate <file>             # Validate against OpenXML schema
```

### view modes

| Mode | Description | Useful flags |
|------|-------------|-------------|
| `outline` | Document structure | |
| `stats` | Statistics (pages, words, shapes) | |
| `issues` | Formatting/content/structure problems | `--type format\|content\|structure`, `--limit N` |
| `text` | Plain text extraction | `--start N --end N`, `--max-lines N` |
| `annotated` | Text with formatting annotations | |
| `html` | Static HTML snapshot — same renderer as `watch`, no server needed | `--browser`, `--page N` (docx), `--start N --end N` (pptx) |
| `screenshot` / `svg` / `pdf` / `forms` | PNG via headless browser / SVG (pptx slide) / PDF via exporter plugin / form-fields JSON via format-handler plugin | `-o`, `--screenshot-width/-height`, pptx `--grid N` |

Use `view html` for one-shot snapshots (CI artifacts, archival, diffing); use `watch` when you need live refresh or browser-side click-to-select.

### get

Any XML path via element localName. Use `--depth N` to expand children. Add `--json` for structured output. Default text output is grep-friendly: `path (type) "text" key=val key=val ...`

```bash
officecli get report.docx '/body/p[3]' --depth 2 --json
officecli get slides.pptx '/slide[1]' --depth 1          # list all shapes on slide 1
officecli get data.xlsx '/Sheet1/B2' --json
```

### Stable ID Addressing

Elements with stable IDs return `@attr=value` paths instead of positional indices. Prefer these in multi-step workflows — positional indices shift on insert/delete, stable IDs do not.

```
/slide[1]/shape[@id=550950021]                    # PPT shape
/slide[1]/table[@id=1388430425]/tr[1]/tc[2]       # PPT table
/body/p[@paraId=1A2B3C4D]                         # Word paragraph
/comments/comment[@commentId=1]                    # Word comment
```

PPT also accepts `@name=` (e.g. `shape[@name=Title 1]`), with morph `!!` prefix awareness. Elements without stable IDs (slide, run, tr/tc, row) fall back to positional indices.

### query

CSS-like selectors: `[attr=value]`, `[attr!=value]`, `[attr~=text]`, `[attr>=value]`, `[attr<=value]`, `:contains("text")`, `:empty`, `:has(formula)`, `:no-alt`. Boolean `and`/`or` supported across `query`/`set`/`remove`: `cell[value>5000 or value<100]`, `cell[(type=Number or type=Date) and value>0]`. Excel row-by-column-name: `Sheet1!row[Salary>5000]`. `set` accepts selectors and Excel-native paths (parity with `get`/`query`). Bare unscoped selectors rejected on `set`/`remove`.

```bash
officecli query report.docx 'paragraph[style=Normal] > run[font!=Arial]'
officecli query slides.pptx 'shape[fill=FF0000]'
```

---

## Watch & Interactive Selection

Live HTML preview that auto-refreshes on every file change.

```bash
officecli watch <file> [--port N]      # Start preview server (default port 26315)
officecli unwatch <file>               # Stop
officecli goto <file> <path>           # Scroll watching browser(s) to element
```

### `get <file> selected` — read what the user clicked

```bash
officecli get <file> selected [--json]
# User clicks shapes in the browser, then asks "make these red"
PATHS=$(officecli get deck.pptx selected --json | jq -r '.data.Results[].path')
for p in $PATHS; do officecli set deck.pptx "$p" --prop fill=FF0000; done
```

---

## L2: DOM Operations

### set — modify properties

```bash
officecli set <file> <path> --prop key=value [--prop ...]
```

**Value formats:**

| Type | Format | Examples |
|------|--------|---------|
| Colors | Hex (with/without `#`), named, RGB, theme | `FF0000`, `#FF0000`, `red`, `rgb(255,0,0)`, `accent1`..`accent6` |
| Spacing | Unit-qualified | `12pt`, `0.5cm`, `1.5x`, `150%` |
| Dimensions | EMU or suffixed | `914400`, `2.54cm`, `1in`, `72pt`, `96px` |

### find — format or replace matched text

```bash
# Format matched text
officecli set doc.docx '/body/p[1]' --find weather --prop bold=true --prop color=red
# Replace text
officecli set doc.docx / --find draft --replace final
# Tracked Find&Replace
officecli set doc.docx / --find draft --replace final --prop revision.author=Alice
```

### add — add elements or clone

```bash
officecli add <file> <parent> --type <type> [--prop ...]
officecli add <file> <parent> --type <type> --after <path> [--prop ...]
officecli add <file> <parent> --type <type> --before <path> [--prop ...]
officecli add <file> <parent> --from <path>    # clone existing element
```

### move, swap, remove

```bash
officecli move <file> <path> [--to <parent>] [--index N] [--after <path>] [--before <path>]
officecli swap <file> <path1> <path2>
officecli remove <file> '/body/p[4]'
```

### batch — multiple operations in one save cycle

```bash
echo '[
  {"command":"set","path":"/Sheet1/A1","props":{"value":"Name","bold":"true"}},
  {"command":"set","path":"/Sheet1/B1","props":{"value":"Score","bold":"true"}}
]' | officecli batch data.xlsx --json
```

---

## L3: Raw XML

```bash
officecli raw <file> <part>                          # view raw XML
officecli raw-set <file> <part> --xpath "..." --action replace --xml '<w:p>...</w:p>'
officecli add-part <file> <parent>                   # create new document part (returns rId)
```

`raw-set` actions: `append`, `prepend`, `insertbefore`, `insertafter`, `replace`, `remove`, `setattr`.

---

## Common Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| `--name "foo"` | Use `--prop name="foo"` — all attributes go through `--prop` |
| Unquoted `[N]` paths in zsh/bash | Always quote: `'/slide[1]'` or `"/slide[1]"` (shell glob-expands brackets) |
| PPT `shape[1]` for content | `shape[1]` is typically the title placeholder. Use `shape[2]+` for content shapes |
| `/shape[myname]` | Name indexing not supported. Use numeric index or `@name=` (PPT only) |
| Guessing property names | Run `officecli help <format> <element>` to see exact names |
| Modifying an open file | Close the file in PowerPoint/WPS first |
| `\n` in shell strings | Use `\\n` for newlines in `--prop text="..."` |
| `$` in shell text | `--prop text="$15M"` strips `$15`. Use single quotes: `--prop text='$15M'`, or heredoc batch |
| `validate` shows 100s of errors | Compare count against source doc, not zero — tcW/ins errors are inherent to officecli's serialiser; see references/tracked-changes-docx.md |
| Row add props silently dropped | `add --type row` accepts no props except position anchors; set cells individually afterward |
| Subagent runs out of iterations on large consolidations | Cap subagent scope at ~8 find-replace+insert operations. For 10+ findings, split into sequential delegations (e.g. findings 1–7 → verify → findings 8–14) rather than one monolithic prompt |
| New paraId not contiguous | Never compute next paraId by incrementing; capture the path returned by each `add` call and chain off that |

---

## Specialized Skills

`officecli load_skill <name>` — output is a SKILL.md, follow its rules.

**Loading rule**:
- Pick the most specific match in "When to use"; if none fits, load the format default (`word` / `pptx` / `excel`).
- Scenes already contain the format default's rules — load **one** skill per artifact, never stack.
- Loaded rules persist across turns; don't re-load each reply.
- Two distinct artifacts → two separate loads.

### Word (.docx)
| Name | When to use |
|------|-------------|
| `word` | Reports, letters, memos, proposals, generic documents |
| `academic-paper` | Journal / conference / thesis: APA / Chicago / IEEE / MLA citations, equations, SEQ + PAGEREF cross-refs, multi-column journal layout, bibliography |

### PowerPoint (.pptx)
| Name | When to use |
|------|-------------|
| `pptx` | Generic decks: board reviews, sales decks, all-hands, product launches |
| `pitch-deck` | Fundraising only — seed / Series A-C / SAFE / convertible / strategic raise |
| `morph-ppt` | Cinematic Morph-animated presentations |
| `morph-ppt-3d` | 3D Morph: GLB models, camera moves, depth |

### Excel (.xlsx)
| Name | When to use |
|------|-------------|
| `excel` | Generic workbooks, formulas, pivots, trackers |
| `financial-model` | Financial models, scenarios, projections |
| `data-dashboard` | CSV/tabular data → KPI / analytics / executive dashboards with charts and sparklines |

---

## Notes

- Paths are **1-based** (XPath convention): `'/body/p[3]'` = third paragraph
- `--index` is **0-based** (array convention): `--index 0` = first position
- **Excel exception**: for `add --type row` and `add --type col`, `--index N` is **1-based** (matches OOXML RowIndex)
- After modifications, verify with `validate` and/or `view issues`
- **When unsure**, run `officecli help <format> <element>` instead of guessing

## Tracked Changes — Key Mechanics and Pitfalls

**Two mutually exclusive revision property namespaces** (NEVER mix in one call):
- **Create namespace:** `revision.type=ins|del`, `revision.author=NAME`, `revision.date=...`, `revision.id=N` — use with `add`, `set`
- **Act namespace:** `revision.action=accept|reject` — use with `set /revision[…]`

**Author-stamped find-and-replace:**
```bash
officecli set doc.docx '/body/p[@paraId=XXXX]' --find "old text" --replace "new text" --prop revision.author="Pass v1.1"
```

**Accept all revisions by one author** (always `query` first — author string often includes a date suffix):
```bash
officecli query doc.docx 'revision'
officecli set doc.docx '/revision[@author="Pass v1.0 (2026-07-08)"]' --prop revision.action=accept
```

**paraId non-contiguity after `add`:** officecli assigns new `@paraId` values non-sequentially. NEVER compute the next `paraId` by incrementing — always capture the returned path from the `add` output and use that as the next `--after` anchor.

**officecli validate baseline noise:** `validate` always reports `tcW-inside-tcPr` and `ins-inside-pPr` errors on docs touched by officecli — these are serialization artefacts, not your errors. Compare error count against source, not zero:
```bash
officecli validate source.docx 2>&1 | grep -c error  # baseline
officecli validate output.docx 2>&1 | grep -c error  # must be ≤ baseline
```

**Table row-add:** `add --type row` accepts NO `cells`, `font`, `size`, `revision.author`, or `revision.type` props — add bare row, then `set` each cell individually. Tracked-change attribution only works on paragraph-level insertions.

**Footnotes:** no revision props — they are silently dropped with WARNING + exit 2.

**Multi-version consolidation (accept-then-re-annotate recipe):**
1. `query doc 'revision'` — read exact author strings
2. Accept all old revisions by author
3. `view text --start N --end M` — read stable `@paraId` IDs
4. Replace annotation text paragraph-by-paragraph with `--find`/`--replace`/`revision.author`
5. Insert new paragraphs with `revision.type=insert` + `revision.author`
6. Add footnotes without revision props

See `references/tracked-changes-docx.md` for full reference with governance document examples.

## Reference files

- `references/officecli-tracked-changes.md` — officecli — Tracked-Change Consolidation Workflow for .docx
