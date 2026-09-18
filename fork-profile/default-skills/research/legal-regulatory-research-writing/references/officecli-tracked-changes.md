# officecli — Tracked-Change Consolidation Workflow for .docx

**Session source:** NAB LIP AI Governance Framework v1.1 → v1.2 consolidation, July 2026.

This recipe replaces the python-docx OOXML approach for gap-analysis → tracked-changes Word deliverables.
Binary: `~/.npm-global/bin/officecli`

---

## The pattern: accept-then-re-annotate

When a document has existing tracked changes (v1.0 pass) and you need to produce a new,
cleaner revision pass (v1.1 consolidated prose), the workflow is:

### Step 1 — Inspect existing revisions

```bash
officecli query doc.docx 'revision'
```

This lists all `w:ins` / `w:del` / `w:moveFrom` / `w:moveTo` markers with their stored
author strings (which often include a date suffix, e.g. `"Gap Analysis v1.0 (2026-07-08)"`)
and native paragraph paths. You MUST read the exact author string before the accept step.

### Step 2 — Accept all prior tracked changes

```bash
officecli set doc.docx '/revision[@author="Gap Analysis v1.0 (2026-07-08)"]' \
  --prop revision.action=accept
```

This makes all prior annotation text plain content — the clean working base for the new pass.

### Step 3 — Read the document structure

```bash
officecli view doc.docx outline         # Section headings + paragraph numbers
officecli view doc.docx text --start N --end M   # Read paragraphs N..M with @paraId paths
```

The `text` view shows stable `@paraId` addresses like `[/body/p[@paraId=001000A4]]`.
Use these for all subsequent addressing — NOT positional `p[N]`, which shifts after accept/reject.

### Step 4 — Replace old annotation text with clean governance prose

For annotation text embedded INSIDE an existing paragraph:

```bash
officecli set doc.docx '/body/p[@paraId=001000A4]' \
  --find "[F1 — HIGH] Gap F1: The registry as described..." \
  --replace "Registration and runtime enforcement are distinct control-plane functions..." \
  --prop revision.author="Gap Analysis v1.1"
```

For annotation text you want to DELETE entirely from a paragraph:

```bash
officecli set doc.docx '/body/p[@paraId=00100024]' \
  --find " [F11] Note: every binding law..." \
  --replace "" \
  --prop revision.author="Gap Analysis v1.1"
```

For a STANDALONE annotation paragraph to be replaced wholesale:

```bash
# Replace entire paragraph content via --find on its full text + --replace with clean text
officecli set doc.docx '/body/p[@paraId=001000A4]' \
  --find "[F1 — HIGH] Gap F1: ..." \
  --replace "Registration and runtime enforcement are distinct..." \
  --prop revision.author="Gap Analysis v1.1"
```

### Step 5 — Insert genuinely new paragraphs

```bash
officecli add doc.docx /body --type paragraph \
  --after '/body/p[@paraId=XXXX]' \
  --prop text="New governance prose here." \
  --prop revision.author="Gap Analysis v1.1" \
  --prop revision.type=insert
```

### Step 6 — Add footnotes (plain additions, no revision props)

```bash
officecli add doc.docx '/body/p[@paraId=XXXX]' --type footnote \
  --prop text="Regulatory citation: APRA CPS 230 §36..."
```

**IMPORTANT:** `--prop revision.author` and `--prop revision.type` are NOT accepted by
`add --type footnote`. They are silently dropped with a WARNING + exit code 2.
Footnotes are always plain content — this is correct behaviour, not a bug.

---

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| `--prop revision.action` + `--prop revision.type` in same call | Mutually exclusive namespaces — never mix them. `revision.type` creates; `revision.action` acts on existing. |
| `@author` selector doesn't match | Run `query revision` first; the stored string often includes ` (2026-07-08)` date suffix |
| Positional `p[N]` breaks after accept | Use `@paraId=` stable IDs from `view text` output |
| `"comment"` field in batch JSON | Not a valid field — omit it entirely or `batch` errors |
| Footnote revision props ignored | Expected — footnotes don't carry tracked-change markers; add without those props |
| `find` fails on annotation already inside a revision wrapper | The annotation text is inside a `w:ins` from a prior author — accept it first (Step 2), then find-replace |

---

## Jurisdiction-framing rule for gap-analysis findings

When replacing an annotation paragraph with governance prose, always lead with the
**Australian operative obligation** (APRA CPS 230, Privacy Act NDB, Corporations Act s.912D)
as the binding anchor. International frameworks (DORA, EU AI Act, UK CTP) may be cited
in a footnote as comparative context only — never as the primary operative citation for
an AU-domiciled entity like NAB.

## Annotations that belong in footnotes vs. running prose

Move to **footnotes** (not inline):
- arXiv / paper citations with IDs
- Regulatory section numbers (APRA CPS 230 §36, CPG 235)
- Institute naming notes / caveats (e.g. "US AISI renamed to CAISI in 2025")
- Comparative-context notes ("EU AI Act not operatively binding on NAB but informative")
- Vendor-assumption caveats ("no public kill-switch API documented — verify with vendor")

Keep as **running prose**:
- The substantive governance requirement itself
- The risk or control being added
- The open-value items and their §17 item numbers
