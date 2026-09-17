# Word Documents (python-docx) — Full Recipe

## Set Margins First, Always
```python
from docx import Document
from docx.shared import Inches, Pt

doc = Document()
section = doc.sections[0]
section.top_margin    = Inches(1)
section.bottom_margin = Inches(1)
section.left_margin   = Inches(1.25)
section.right_margin  = Inches(1.25)
```

## Use Named Styles — Never Ad Hoc Formatting
Never set font size/bold/color directly on a paragraph run without a named style.
Ad hoc formatting breaks document-level consistency and prevents theme changes.

```python
# CORRECT: use the style hierarchy
heading = doc.add_heading('Section Title', level=1)  # Heading 1 — hooks into theme
body_para = doc.add_paragraph('Body text here.')      # Normal style

# WRONG: manual formatting is a fake heading that breaks hierarchy
p = doc.add_paragraph()
run = p.add_run('Section Title')
run.bold = True
run.font.size = Pt(16)  # bypasses theme, creates inconsistency, violates H1/H2/Body hierarchy
```

Custom styles: define once on the document, apply by name everywhere:
```python
from docx.shared import RGBColor
from docx.oxml.ns import qn

# Modify existing style rather than creating ad hoc formatting
style = doc.styles['Heading 1']
style.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)
style.font.size = Pt(16)
# All Heading 1 paragraphs now pick this up automatically
```

## Paragraph Spacing — Explicit and Consistent
```python
from docx.shared import Pt, Inches

para = doc.add_paragraph('Content here.')
fmt = para.paragraph_format
fmt.space_before  = Pt(6)
fmt.space_after   = Pt(6)
fmt.line_spacing  = 1.15   # or 2.0 for academic double-spacing

# Hanging indent for reference/bibliography lists
ref = doc.add_paragraph('Smith, J. (2023). ...')
ref.paragraph_format.left_indent        = Inches(0.5)
ref.paragraph_format.first_line_indent  = Inches(-0.5)  # negative = hanging
```

## Tables: Style + Explicit Column Widths + Fixed Layout
python-docx table widths are unreliable unless you both set cell widths AND force
a fixed table layout (otherwise Word recalculates on open):

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches

def create_fixed_table(doc, rows, cols, col_widths_inches):
    """
    Create a table with fixed column widths that Word won't re-flow.
    col_widths_inches: list of widths, one per column. Sum should fit page width.
    """
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Table Grid'

    # Force fixed layout so Word respects our widths
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblLayout = OxmlElement('w:tblLayout')
    tblLayout.set(qn('w:type'), 'fixed')
    tblPr.append(tblLayout)

    # Set column widths using python-docx's API only (avoid double-writing w:tcW)
    for col_idx, width in enumerate(col_widths_inches):
        for row in table.rows:
            cell = row.cells[col_idx]
            cell.width = Inches(width)  # python-docx writes w:tcW internally

    return table
```

## Multi-Section Documents
For documents with different headers/footers per section (e.g. landscape appendix),
order matters — set orientation BEFORE dimensions:
```python
from docx.enum.section import WD_ORIENT
from docx.shared import Inches

# Add a section break (landscape appendix example)
new_section = doc.add_section()
# Step 1: set orientation first
new_section.orientation = WD_ORIENT.LANDSCAPE
# Step 2: then swap dimensions (python-docx needs explicit values after rotation)
new_section.page_width  = Inches(11)
new_section.page_height = Inches(8.5)
# Unlink header/footer from previous section so you can customize
new_section.header.is_linked_to_previous = False
new_section.footer.is_linked_to_previous = False
```

## Running Headers and Footers (DOCX)
Add page-number and document-title running headers using the header paragraph:
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def add_page_number(run):
    fldChar_begin = OxmlElement('w:fldChar')
    fldChar_begin.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.text = 'PAGE'
    fldChar_end = OxmlElement('w:fldChar')
    fldChar_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar_begin)
    run._r.append(instrText)
    run._r.append(fldChar_end)

# Add a running header: left = doc title, right = page number
header = doc.sections[0].header
hdr_para = header.paragraphs[0]
# Clear existing runs by removing all child 'w:r' elements
from lxml import etree
for r in hdr_para._p.findall(qn('w:r')):
    hdr_para._p.remove(r)
hdr_para.style = doc.styles['Header']  # uses Header style for spacing

# Add title text run
title_run = hdr_para.add_run("Document Title")
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.shared import Inches
pf = hdr_para.paragraph_format
pf.tab_stops.add_tab_stop(Inches(6.0), WD_TAB_ALIGNMENT.RIGHT)
run = hdr_para.add_run('\t')  # tab to right
add_page_number(run)
```

## Image Handling (DOCX)
```python
from docx.shared import Inches

# Always specify width; let python-docx maintain aspect ratio automatically
doc.add_picture('chart.png', width=Inches(5.5))
# Do NOT set both width and height unless you've verified the aspect ratio
```

## Converting an Existing Markdown Document to DOCX When Pandoc Isn't Installed

Don't assume pandoc is available (`which pandoc`). On a fresh/minimal
environment it frequently isn't, and installing it may not be desired mid-task.
**Check `scripts/md_to_docx.py` in this skill first** — it's a reusable, tested
converter; running it directly is faster and less error-prone than rewriting the
same parser inline from scratch (this has happened more than once — a fresh inline
script gets written because the skill wasn't loaded/consulted before starting the
conversion). If python-docx is already available and this script doesn't fit, write
the conversion directly rather than blocking on pandoc: a compact parser that walks
the markdown line-by-line handling `#`-headers
(mapped to `add_heading(level=...)`), `**bold**`/`` `code` `` inline spans, `-` bullets
(`List Bullet` style), `1.` numbered items (`List Number` style), and bare `*italic*`
lines (e.g. a closing colophon) covers the vast majority of synthesis/report documents
without needing a full CommonMark implementation. See `scripts/md_to_docx.py` for a
working, reusable version — pass it `--src` and `--out` paths.

After conversion, always verify structurally before treating it as done — do not just
confirm the file exists:
```python
import docx
d = docx.Document(out_path)
heads = [p.text for p in d.paragraphs if p.style.name.startswith('Heading')]
# Compare this list against the '#'-lines from the source markdown — same count,
# same order, same nesting (H1 vs H2 vs H3). A mismatch means the parser mis-handled
# a header (e.g. a '#' inside a code span or a line starting with '#' that wasn't
# actually a heading).
bold_present = any(r.bold for p in d.paragraphs for r in p.runs)
word_count = len(' '.join(p.text for p in d.paragraphs).split())
# word_count should be in the same ballpark as the source markdown's word count —
# a big drop means content silently got skipped by an unhandled markdown construct.
```

## Tracked Changes (w:ins / w:del) in python-docx

python-docx has no native tracked-changes API. When you need to emit a DOCX with
revision markup (e.g. a gap-analysis update where each annotation must be
accept/reject-able in Word), build the OOXML directly.

Core pattern — tracked insertion wrapping a run:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

REV_ID = [100]   # mutable counter for unique w:id values

def next_id():
    REV_ID[0] += 1
    return str(REV_ID[0])

def make_ins_run(paragraph, text, author, date, size=10.5, bold=False, color=None):
    """Append a w:ins-wrapped run to paragraph. color is an RGBColor or None."""
    ins = OxmlElement('w:ins')
    ins.set(qn('w:id'), next_id())
    ins.set(qn('w:author'), author)
    ins.set(qn('w:date'), date)       # e.g. "2026-07-08T00:00:00Z"

    r_el = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    # Font
    rFonts = OxmlElement('w:rFonts')
    for attr in ('w:ascii', 'w:hAnsi', 'w:cs'):
        rFonts.set(qn(attr), 'Open Sans')
    rPr.append(rFonts)
    # Size
    for tag in ('w:sz', 'w:szCs'):
        el = OxmlElement(tag)
        el.set(qn('w:val'), str(int(size * 2)))
        rPr.append(el)
    if bold:
        rPr.append(OxmlElement('w:b'))
    # Color — RGBColor is a tuple subclass; use [0],[1],[2] NOT .red/.green/.blue
    if color is not None:
        c_el = OxmlElement('w:color')
        c_el.set(qn('w:val'), f'{color[0]:02X}{color[1]:02X}{color[2]:02X}')
        rPr.append(c_el)
    r_el.append(rPr)

    t_el = OxmlElement('w:t')
    t_el.set(qn('xml:space'), 'preserve')
    t_el.text = text
    r_el.append(t_el)
    ins.append(r_el)
    paragraph._p.append(ins)
    return ins

def make_del_run(paragraph, text, author, date, size=10.5):
    """Append a w:del-wrapped run to paragraph (uses w:delText, not w:t)."""
    del_el = OxmlElement('w:del')
    del_el.set(qn('w:id'), next_id())
    del_el.set(qn('w:author'), author)
    del_el.set(qn('w:date'), date)
    r_el = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size * 2)))
    rPr.append(sz)
    r_el.append(rPr)
    t_el = OxmlElement('w:delText')
    t_el.set(qn('xml:space'), 'preserve')
    t_el.text = text
    r_el.append(t_el)
    del_el.append(r_el)
    paragraph._p.append(del_el)
    return del_el
```

To mark a whole new paragraph as inserted (so Word shows the paragraph itself as
tracked-added, not just its runs), also add a `w:ins` inside `w:pPr`:

```python
def mark_paragraph_as_inserted(paragraph, author, date):
    pPr = paragraph._p.get_or_add_pPr()
    ins_ppr = OxmlElement('w:ins')
    ins_ppr.set(qn('w:id'), next_id())
    ins_ppr.set(qn('w:author'), author)
    ins_ppr.set(qn('w:date'), date)
    ins_ppr.append(OxmlElement('w:rPr'))
    pPr.append(ins_ppr)
```

**w:id uniqueness**: every `w:ins` and `w:del` element in the document must have a
distinct `w:id`. Use a module-level counter (see `REV_ID` above) and increment it for
each element. Duplicate IDs cause Word to silently discard revision marks.

**Annotation deduplication**: when annotations are triggered by anchor-text scanning
across the document (e.g. a finding F3 whose anchor text appears in both §6 and §9),
track which findings have already been emitted with a set and skip duplicates:

```python
emitted = set()
for anchor, annotations in ANNOTATIONS.items():
    if anchor in paragraph_text:
        for (fid, note_text) in annotations:
            if fid not in emitted:
                add_annotation_paragraph(doc, fid, note_text)
                emitted.add(fid)
```

**Table row anchors**: anchors for findings in GFM table rows won't fire when you only
check body paragraph text. Concatenate all lines of each table block and scan the
concatenation:

```python
all_table_text = ' '.join(table_lines)
for anchor, annotations in ANNOTATIONS.items():
    if anchor in all_table_text:
        ...
```

**Two annotation placement modes** — choose based on how tightly the gap finding
binds to existing text:

1. **Inline suffix** — gap text appended to an existing body paragraph as a `w:ins`
   tail: `_ins_run(para, " [F3] " + note, ...)`. Best when the finding directly
   qualifies a specific sentence. The finding ID is visible mid-paragraph, so keep
   the label short (e.g. `[F3]`, not `[F3 — HIGH — Gap analysis note]`).
2. **Standalone tracked paragraph** — a new paragraph fully marked as inserted
   (`mark_paragraph_as_inserted`) after the relevant section body. Use when the
   finding spans multiple issues or quotes extensively. Shade with `FFF8E8` (lighter
   than amber `FFF3CD`) to distinguish synthesised-inline from prior floating-note style.
3. **Batched regulatory-map paragraph** — when several findings all require additions to
   the same table/section, combine them into one tracked paragraph with bullet points
   keyed by finding ID. Avoids fragmenting a §12-style table with individual micro-notes.

**Python string quoting pitfall**: never use single-quoted string literals that contain
both em-dashes (U+2014) and apostrophes (don't, it's, etc.). Python's parser sees the
apostrophe as the closing quote and then hits the `—` as a SyntaxError. Use one of:
- Double-quoted string: `"don't reinvent — one harness"`
- Unicode escape for the dash: `'don\'t reinvent \u2014 one harness'`
- Raw escape inside f-string: `f"[{fid} \u2014 {sev}] "`

See `references/tracked-changes-recipe.md` for the full working implementation used
to build the NAB LIP gap-analysis update documents (floating-note style v1.1, and
synthesised-inline style v1.1-synthesised).

## Gap-Analysis Integration: Consolidating Review Findings into Governance Documents

When the task is "integrate gap-analysis findings into a governance document as tracked changes" — a recurring pattern for NAB LIP and similar compliance-document workflows — the approach is distinct from greenfield generation:

**Editorial standard (non-negotiable for this user):**
- NEVER retain review labels (F1/F2/F3, HIGH/MEDIUM/LOW) in the consolidated output. Findings are re-voiced as clean governance prose that reads as if it were always part of the document.
- Severity tiers and finding IDs are internal tracking tools, not document content. A consolidated document that still contains [F3 HIGH] labels is not consolidated — it is annotated.
- Footnotes carry substantive notes, caveats, and explanatory asides — not only bibliographic references. If content would interrupt reading flow but is important (regulatory citations with section numbers, methodology caveats, comparative-context notes about non-binding frameworks, kill-switch verification assumptions), put it in a footnote. Footnotes are prose-quality, not terse.

**When to delegate to a stronger model:**
For documents with 10+ findings to integrate, each requiring careful synthesis and section-appropriate voice, delegate to `claude-opus-4-5` or `claude-opus-4-8` via `delegate_task`. The orchestrating agent's job is to:
1. Read the base document structure (`officecli view outline` + `officecli view text`)
2. Read the tracked-changes/annotations document (same)
3. Build a self-contained context packet: full finding substance, target section for each, open-value additions for any decisions section, table-row additions
4. Delegate with explicit instructions on voice, footnote philosophy, and tracked-change author

Do NOT attempt to apply 14+ tracked-change insertions in a single orchestrating session — context cost and error rate make direct orchestrator application worse than delegation.

**Tracked-change author convention for NAB LIP work:**
- v1.0 gap analysis → author: "Gap Analysis v1.0"
- v1.1 consolidated → author: "Gap Analysis v1.1"
Keep the author string versioned so reviewers can see which pass each tracked change came from.

**Output file naming convention for NAB LIP framework docs:**
- Base document: `framework-vN.M-synthesised.docx`
- Tracked-changes document (annotations inline): `framework-vN.M-tracked-changes.docx`
- Consolidated output (findings integrated as prose): `framework-vN.(M+1)-consolidated.docx`

---

## Editing/Restructuring an EXISTING Large DOCX (not greenfield generation)

When the task is "remove these sections, rewrite that one, add a new section" on an
existing multi-page docx — as opposed to building a new document from scratch — a
single monolithic script that reconstructs the whole file from memory risks silently
dropping existing tables/styles and blows up your context if the doc is long. Use a
chunked, chained-script pattern instead:

1. **Inspect existing structure programmatically first** — don't rely on memory of
   what the doc contains. Dump paragraph styles and table contents to disk before
   touching anything:
   ```python
   from docx import Document
   import json
   d = Document('existing.docx')
   print(len(d.paragraphs), len(d.tables))
   print({p.style.name for p in d.paragraphs})  # confirm which named styles are in use
   tables = [[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
   json.dump(tables, open('/tmp/tables.json', 'w'), indent=2)  # reuse verbatim, don't retype
   ```
2. **Back up the original** (`cp existing.docx existing_backup.docx`) before any
   overwrite — you cannot recover a destructive `.save()` over the original path.
3. **Chain build scripts, one per major section/pass**, each loading the previous
   script's saved output and appending to it: `build1.py` creates `part1.docx` (title
   + early sections), `build2.py` opens `part1.docx` and appends the next block →
   `part2.docx`, and so on. The final script saves to the real destination path. This
   keeps each script small enough to review and re-run independently if one pass has
   an error, without re-generating the whole document.
4. **Verify the final structure before declaring done** — reopen the saved file and
   print the heading list (`[p.text for p in d.paragraphs if p.style.name in
   ('Title','Heading 1','Heading 2')]`). Confirm removed sections are actually gone
   and new sections landed in the right place — don't just trust that the script ran
   without error.

## PITFALL: heading lookup-by-text-only silently matches the wrong paragraph

If the document has a Table of Contents (a `List Bullet`/TOC-style paragraph list
mirroring each heading's exact text), a helper that finds an insertion point by text
match alone will match the FIRST paragraph with that text — which is very often the
TOC entry, not the real heading. `insert_paragraph_before()` then silently succeeds
against the wrong node and your new section lands at the top of the document under
"Contents" instead of where you intended, with the script reporting success. Symptom
looks like nothing went wrong until you inspect the actual heading list.

Always filter by BOTH text and style when locating a heading to anchor edits to:
```python
def find_heading(doc, text, style='Heading 1'):
    for p in doc.paragraphs:
        if p.text.strip() == text and p.style.name == style:
            return p
    raise ValueError(f"heading not found: {text} ({style})")
```
Never match on `p.text.strip() == text` alone when the document has a TOC, an index,
or any other place the same string legitimately appears twice. After inserting,
re-run the step-4 heading-list verification and confirm the new content is nested
under the correct parent section, not merely "present somewhere in the file."

## PITFALL: renumbering cross-reference tokens after a section removal/reorder

When a document has internal cross-references (e.g. "§2.1", "see §4.3 above") and you
remove or reorder a section, every reference to a renumbered section must be updated
too — not just the headings and TOC. A naive find-and-replace script that special-cases
a few known paragraphs (e.g. "if this paragraph contains X, do a custom replace, then
`continue`") will silently skip the GENERIC renumbering pass for that same paragraph —
so any OTHER stale token sharing that paragraph goes unfixed. This produced exactly this
bug across two separate passes in one session: paragraphs that got a special-cased fix
for one token still had a second, different stale token (e.g. old `§2.4` when the correct
new value was `§1.4`) that the `continue` skipped.

Correct approach:
1. Do the section removal/reorder first, then dump every paragraph (index + style +
   text) to a file and grep for the reference-token pattern (e.g. `§\d+(?:\.[\dA-Z]+)?`).
2. Build an explicit **old-heading-number → new-heading-number** map from the actual
   before/after heading lists (not from assumptions about a fixed offset — a merged or
   deleted subsection can break simple "subtract 1" arithmetic).
3. Apply the map with a single generic regex substitution pass over all paragraphs.
   Avoid short-circuiting per-paragraph special cases with `continue`/early-return; if a
   paragraph needs a special-case fix, apply it AND still run the generic pass on the
   same paragraph, or explicitly re-scan that paragraph after the special case.
4. Re-dump and re-grep after the pass. Build the final heading-number set (from actual
   `Heading 1`/`Heading 2` paragraphs) and check every remaining reference token against
   it — any token whose top-level number isn't in that set (and isn't legitimately
   referencing a different external document's own numbering — check for that context
   before "fixing" it) is a bug to chase down individually. Don't assume one clean pass
   caught everything; re-verify with the same grep sweep, not just a visual skim.
5. Also check surrounding prose for stale mentions of the removed section by keyword
   (e.g. "verification", "source-verified") rather than only by `§` token — a paragraph
   can reference a deleted section in prose without using the numbered-reference syntax
   at all (e.g. a metadata line like "Reviewed by: ... (source-verified citations)"
   referencing a citation-verification section that no longer exists).

## PITFALL: a valid-looking cross-reference can be wrong FROM THE START, not just stale

Distinct from the renumbering bug above: a `§N.M` token can point at a section number
that genuinely exists in the current document, yet still be the wrong citation — the
number was miscopied or miscounted when originally written, and nothing about a
section-existence check catches it. Found in one session: three separate mentions of
a training-data-leakage/privilege-in-training-data claim all cited "§5.6", but §5 item
6 was actually an unrelated conformal-prediction topic; the correct target (§5 item 4)
covered the right subject matter. A pure "does this number exist" grep sweep (the
renumbering-pitfall check above) reports this as clean — the fix requires a *content*
check, not just an existence check:

1. For every internal cross-reference token, open the target section and confirm its
   actual subject matter matches what the citing sentence claims it supports. Don't
   stop at "the section exists."
2. This is cheapest to do while you're already reading each section closely (e.g.
   during a consolidation/synthesis pass) — flag any citation whose surrounding
   sentence describes topic A while the target section is about topic B.
3. When you find one instance of a topic being miscited, grep for all other mentions
   of that same topic/claim in the document — a wrong pointer written once during
   drafting is often copy-pasted to every other place the same claim recurs (this
   session: 3 occurrences of the same wrong §5.6 pointer for the same claim).
