# officecli — Word Tracked-Changes Quick Reference

**Session source:** NAB LIP AI Governance Framework v1.1 → v1.2, July 2026.

## Core mechanics

### Two mutually exclusive revision property namespaces

| Namespace | Props | Purpose | Used with |
|-----------|-------|---------|-----------|
| Create | `revision.type=ins\|del`, `revision.author=NAME`, `revision.date=...`, `revision.id=N` | Create a new w:ins / w:del marker | `add`, `set` |
| Act | `revision.action=accept\|reject` | Accept or reject an existing marker | `set /revision[…]` |

**Never mix the two in one call** — the CLI rejects it as ambiguous.

### Author-stamped find-and-replace

```bash
# Replace old text with new text (tracked del+ins pair):
officecli set doc.docx '/body/p[@paraId=XXXX]' \
  --find "old annotation text" \
  --replace "clean governance prose" \
  --prop revision.author="Gap Analysis v1.1"

# Delete old text (tracked del only, empty replace):
officecli set doc.docx '/body/p[@paraId=XXXX]' \
  --find " [F11] annotation text..." \
  --replace "" \
  --prop revision.author="Gap Analysis v1.1"
```

### Tracked paragraph insertion

```bash
officecli add doc.docx /body --type paragraph \
  --after '/body/p[@paraId=XXXX]' \
  --prop text="New paragraph content." \
  --prop revision.author="Gap Analysis v1.1" \
  --prop revision.type=insert
```

### Accept / reject existing revisions

```bash
# Always query first — author string often includes date suffix:
officecli query doc.docx 'revision'

# Accept all by one author:
officecli set doc.docx '/revision[@author="Gap Analysis v1.0 (2026-07-08)"]' \
  --prop revision.action=accept
```

### Footnotes — NO revision props

```bash
# Correct (no revision props — they are silently dropped with WARNING + exit 2):
officecli add doc.docx '/body/p[@paraId=XXXX]' --type footnote \
  --prop text="Citation text here."
```

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| `revision.action` + `revision.type` in same call | Mutually exclusive — never mix |
| `@author` selector doesn't match | Run `query revision` first; date suffix is common |
| Positional `p[N]` breaks after accept/reject | Use `@paraId=` from `view text` output |
| `"comment"` key in batch JSON | Not valid — omit it or batch errors |
| Footnote revision props ignored | Expected — footnotes carry no tracked-change markers |
| Error: "matched run is already inside a revision wrapper" | Accept the existing revision first, then find-replace |

## officecli validate — expected baseline noise

`officecli validate` always reports schema errors on docs touched by officecli itself.
The `tcW`-inside-`tcPr` errors and `ins`-inside-`pPr` errors are artefacts of how
officecli serialises table/run properties — they appear on every table in the document
and are **not introduced by your edits**.

**Correct interpretation:** compare error count against the source file, not against zero.

```bash
officecli validate source.docx 2>&1 | grep -c error   # baseline
officecli validate output.docx 2>&1 | grep -c error   # must be ≤ baseline
```

If output > source, you introduced real new errors. If output ≤ source, document is clean
for Word. A single dangling `footnoteReference` semantic error may also be pre-existing.

## paraId non-contiguity after `add`

officecli assigns new `@paraId` values that are NOT sequential from the previous one.
The gap is unpredictable (e.g. `00100303` → `00100305`, not `00100304`).

**Never** compute the next paraId by incrementing — always capture the returned path:

```bash
# Correct:
RESULT=$(officecli add doc.docx /body --type paragraph --after '/body/p[@paraId=00100260]' \
  --prop text="Item 8...")
NEW_ID=$(echo "$RESULT" | grep -oP '(?<=@paraId=)[A-F0-9]+')

# Or chain anchors off the output path:
# "Added paragraph at /body/p[@paraId=00100303]"
# Next --after uses 00100303, not 00100304
```

## Table row-add: strip all unsupported props

`officecli add ... --type row` only accepts bare add — no `cells`, `font`, `size`,
`revision.author`, or `revision.type` props. All are silently dropped with WARNING + exit 2.

```bash
# Correct — add bare row, then set each cell:
officecli add doc.docx '/body/tbl[5]' --type row --after '/body/tbl[5]/tr[4]'
officecli set doc.docx '/body/tbl[5]/tr[5]/tc[1]' --prop text="SR 11-7 / Model Validation"
officecli set doc.docx '/body/tbl[5]/tr[5]/tc[2]' --prop text="..."
```

Similarly, `revision.author` on table rows is unsupported — tracked-change attribution
only works reliably on paragraph-level insertions (`add --type paragraph`).

## Multi-version consolidation (accept-then-re-annotate) recipe

1. `officecli query doc.docx 'revision'` — read exact author strings
2. Accept all v1.0 revisions: `set '/revision[@author="…"]' --prop revision.action=accept`
3. `view doc.docx text --start N --end M` — read `@paraId` stable IDs
4. Replace annotation text paragraph-by-paragraph with `--find … --replace … --prop revision.author="v1.1"`
5. Insert new paragraphs with `revision.type=insert` + `revision.author`
6. Add footnotes without revision props

## Footnote-vs-prose decision rule (for governance documents)

Move to **footnotes**: arXiv IDs, regulatory section numbers (APRA CPS 230 §36),
institute naming caveats, comparative-context notes (EU AI Act not binding on AU entity),
vendor-assumption caveats.

Keep in **running prose**: the substantive requirement, the control, the open-value item.
