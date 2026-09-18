# Tracked Changes Recipe — python-docx OOXML

Pattern established 2026-07-08 building the NAB LIP gap-analysis update
(framework-v1.1-tracked-changes.docx, 14 gap findings, 42 w:ins elements).

## Core helpers

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import RGBColor

REV_ID = [100]   # module-level mutable counter; must be unique across the whole document

def next_id():
    REV_ID[0] += 1
    return str(REV_ID[0])

TC_AUTHOR = "Gap Analysis v1.0 (2026-07-08)"
TC_DATE   = "2026-07-08T00:00:00Z"

def make_ins_run(paragraph, text, size=10.5, color=None, bold=False, italic=False):
    """
    Append a w:ins-wrapped run to `paragraph`.
    `color`: RGBColor — use color[0], color[1], color[2] (tuple index), NOT .red/.green/.blue.
    """
    ins = OxmlElement('w:ins')
    ins.set(qn('w:id'), next_id())
    ins.set(qn('w:author'), TC_AUTHOR)
    ins.set(qn('w:date'), TC_DATE)

    r_el = OxmlElement('w:r')
    rPr  = OxmlElement('w:rPr')

    # Font family — set all four attributes or rendering engines fall back silently
    rFonts = OxmlElement('w:rFonts')
    for attr in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rFonts.set(qn(attr), 'Open Sans')   # substitute your brand font here
    rPr.append(rFonts)

    # Size (half-points)
    for tag in ('w:sz', 'w:szCs'):
        el = OxmlElement(tag)
        el.set(qn('w:val'), str(int(size * 2)))
        rPr.append(el)

    if bold:   rPr.append(OxmlElement('w:b'))
    if italic: rPr.append(OxmlElement('w:i'))

    # Color — RGBColor is a tuple subclass; index with [0],[1],[2]
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


def make_del_run(paragraph, text, size=10.5, color=None, bold=False):
    """
    Append a w:del-wrapped run. Note: uses w:delText, NOT w:t — Word rejects w:t inside w:del.
    """
    del_el = OxmlElement('w:del')
    del_el.set(qn('w:id'), next_id())
    del_el.set(qn('w:author'), TC_AUTHOR)
    del_el.set(qn('w:date'), TC_DATE)

    r_el = OxmlElement('w:r')
    rPr  = OxmlElement('w:rPr')
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size * 2)))
    rPr.append(sz)
    if bold: rPr.append(OxmlElement('w:b'))
    if color is not None:
        c_el = OxmlElement('w:color')
        c_el.set(qn('w:val'), f'{color[0]:02X}{color[1]:02X}{color[2]:02X}')
        rPr.append(c_el)
    r_el.append(rPr)

    t_el = OxmlElement('w:delText')   # NOT w:t
    t_el.set(qn('xml:space'), 'preserve')
    t_el.text = text
    r_el.append(t_el)
    del_el.append(r_el)
    paragraph._p.append(del_el)
    return del_el


def mark_paragraph_as_inserted(paragraph):
    """
    Mark the paragraph change-mark itself as inserted (shows the paragraph as tracked-new in Word).
    Add this on top of make_ins_run calls to track that the paragraph is entirely new.
    """
    pPr = paragraph._p.get_or_add_pPr()
    ins_ppr = OxmlElement('w:ins')
    ins_ppr.set(qn('w:id'), next_id())
    ins_ppr.set(qn('w:author'), TC_AUTHOR)
    ins_ppr.set(qn('w:date'), TC_DATE)
    ins_ppr.append(OxmlElement('w:rPr'))
    pPr.append(ins_ppr)


def add_amber_annotation(doc, finding_id, note_text):
    """
    Insert an amber-shaded annotation paragraph fully tracked as inserted.
    Amber fill: FFF3CD (light amber — visible but not garish).
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(10)
    p.paragraph_format.left_indent  = Inches(0.3)
    p.paragraph_format.line_spacing = 1.12

    # Amber background shading
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'FFF3CD')
    pPr.append(shd)

    mark_paragraph_as_inserted(p)

    # Lead: bold amber finding ID
    AMBER = RGBColor(0xE9, 0x60, 0x0E)
    DARK  = RGBColor(0x1A, 0x1A, 0x1A)
    make_ins_run(p, f"[{finding_id}] ", size=10.0, color=AMBER, bold=True)
    make_ins_run(p, note_text,           size=10.0, color=DARK)
    return p
```

## Anchor-triggered dispatch with deduplication

```python
# Annotations keyed by anchor text that appears in the source document.
# Each value is a list of (finding_id, note_text) tuples.
ANNOTATIONS = {
    "4.4 The registry as control plane": [
        ("F1 [HIGH]", "Gap F1 ..."),
    ],
    "Central holdout injection": [
        ("F3 [HIGH]", "Gap F3 ..."),
    ],
    # ... etc.
}

# In your main parse loop:
emitted = set()   # prevents duplicate annotations if the anchor appears more than once

def dispatch_annotations(text, doc, emitted):
    for anchor, items in ANNOTATIONS.items():
        if anchor in text:
            for (fid, note) in items:
                if fid not in emitted:
                    add_amber_annotation(doc, fid, note)
                    emitted.add(fid)

# Call after rendering each content element type (heading, bullet, body para):
dispatch_annotations(stripped_line, doc, emitted)

# For table blocks — anchors inside table rows won't fire on per-line calls,
# because the table parser consumes lines as a block. Scan the whole block:
all_table_text = ' '.join(table_lines)
dispatch_annotations(all_table_text, doc, emitted)
```

## Verification after build

```python
from docx import Document
from docx.oxml.ns import qn

doc = Document('output.docx')

ins_count = len(doc.element.body.findall('.//' + qn('w:ins')))
del_count = len(doc.element.body.findall('.//' + qn('w:del')))

amber_paras = []
for p in doc.paragraphs:
    pPr = p._p.find(qn('w:pPr'))
    if pPr is not None:
        shd = pPr.find(qn('w:shd'))
        if shd is not None and shd.get(qn('w:fill')) == 'FFF3CD':
            ins_texts = []
            for ins in p._p.findall('.//' + qn('w:ins')):
                for t in ins.findall('.//' + qn('w:t')):
                    if t.text: ins_texts.append(t.text)
            amber_paras.append(''.join(ins_texts)[:60])

print(f"w:ins elements: {ins_count}")
print(f"w:del elements: {del_count}")
print(f"Amber annotation paragraphs: {len(amber_paras)}")
for a in sorted(amber_paras):
    print(f"  {a!r}")

# Check author consistency
authors = {ins.get(qn('w:author'))
           for ins in doc.element.body.findall('.//' + qn('w:ins'))}
print(f"TC authors: {authors}")   # should be a single-element set
```

## Inline-suffix pattern (synthesised approach)

Instead of floating annotation paragraphs, append gap findings directly to the tail of
the relevant body paragraph. Gives the reader a single coherent paragraph to read/accept.

```python
def gap_inline_suffix(para, fid, severity, text):
    """
    Append a gap finding as an inline w:ins suffix to an existing body paragraph.
    fid: 'F3'  severity: 'HIGH' | 'MEDIUM' | 'LOW'
    """
    sev_colors = {'HIGH': NAB_RED, 'MEDIUM': NAB_AMBER, 'LOW': NAB_EMERALD}
    col = sev_colors.get(severity, NAB_AMBER)
    _ins_run(para, f" [{fid}] ", size=9.5, bold=True, color=col)
    _ins_run(para, text, size=10.5, color=NAB_SLATE)
```

Call immediately after adding the last run to the relevant body paragraph:
```python
p = body(doc, 'Central holdout injection. ...')
gap_inline_suffix(p, 'F3', 'HIGH', 'Holdout contamination note ...')
```

Placement taxonomy when synthesising 14+ findings across a document:
- **Inline suffix**: finding qualifies a specific sentence; label is short e.g. `[F3]`.
- **Standalone tracked paragraph**: finding spans multiple sub-issues or quotes at length.
  `mark_paragraph_as_inserted` + shade `FFF8E8` (lighter than amber `FFF3CD`).
- **Batched tracked paragraph**: 3+ findings all require additions to the same section/table.
  List as bullet points keyed by finding ID inside a single new paragraph.

## String quoting pitfall

Em-dashes (U+2014) inside single-quoted Python string literals cause a SyntaxError
when the same string also contains an apostrophe — Python reads the `'` as the closing
quote and then hits the `—` as unexpected input.

```python
# BROKEN — Python sees single-quote in "don't" as closing the string
bullet(doc, '**P4: Reuse, don't reinvent** — one harness ...')

# FIX 1: double-quoted string
bullet(doc, "**P4: Reuse, don't reinvent** \u2014 one harness ...")

# FIX 2: escape the apostrophe
bullet(doc, '**P4: Reuse, don\'t reinvent** \u2014 one harness ...')

# FIX 3: use \u2014 even inside double-quoted strings (works in f-strings too)
_ins_run(p, f"[{fid} \u2014 {severity}] ", bold=True, color=col)
```

The linter may report `SyntaxError: invalid character '—' (U+2014)` as the error
message even though the root cause is the apostrophe, because by the time the parser
reaches the em-dash it is already in an unexpected tokenization state.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `color.red` / `color.green` | `AttributeError` at runtime | Use `color[0]`, `color[1]`, `color[2]` — RGBColor is a tuple |
| `w:t` inside `w:del` | Word schema validation error | Use `w:delText` inside `w:del`, `w:t` only inside `w:ins` |
| Duplicate `w:id` values | Word silently drops some revision marks | Use a module-level counter; always call `next_id()` |
| Anchor only checked in body-paragraph branch | Annotations for table-row anchors never fire | Also scan `' '.join(table_lines)` after rendering each table block |
| Same finding emitted twice | Duplicate amber para in output | Track emitted finding IDs in a `set()`; skip if already seen |
| Paragraph background shading without `pPr` ins mark | Word shows amber background but no "inserted paragraph" bar | Call `mark_paragraph_as_inserted()` in addition to shading |
