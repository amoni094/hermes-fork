# Document Layout API Pitfalls

Surfaced across 6 adversarial review passes on the document-layout-design skill (2026-07-03).
These are silent failures and wrong API calls that are easy to introduce and hard to spot.

---

## python-pptx

### Text overflow detection
`has_text_overflow()` as naively implemented always returns True or False depending on
implementation — there is no built-in text overflow detection in python-pptx.
The correct approach inspects the XML autofit element:

```python
from pptx.oxml.ns import qn

def get_autofit_type(shape):
    """Returns 'noAutofit', 'spAutoFit', 'normAutofit', or None."""
    if not shape.has_text_frame:
        return None
    txBody = shape.text_frame._txBody
    bodyPr = txBody.find(qn('a:bodyPr'))
    if bodyPr is None:
        return None
    for tag in ('a:noAutofit', 'a:spAutoFit', 'a:normAutofit'):
        if bodyPr.find(qn(tag)) is not None:
            return tag.split(':')[1]
    return None
```

Shapes with `noAutofit` AND overflowing text will clip silently. Shapes with `spAutoFit`
expand beyond their defined bounds and may overlap adjacent shapes.

### Slide safe zone
Standard widescreen (16:9): 10 in wide × 7.5 in tall.
Safe zone with 0.5 in margins each side: `Inches(9.0)` wide, `Inches(6.5)` tall.
`Inches(12.33)` is not a real dimension — never use it.

### Slide dimensions access
`slide.shapes.parent` is the slide itself, NOT the presentation.
Slide dimensions live on the Presentation object:
```python
prs.slide_width   # correct
prs.slide_height  # correct
slide.shapes.parent.slide_width  # AttributeError
```
Always pass `prs` explicitly to any validation function that needs dimensions.

### Alt text on pictures
`pic.name` is the shape's internal XML name — it is NOT the PowerPoint alt text field.
Setting it does NOT set alt text. The correct path:
```python
nvPr = pic._element.nvPicPr.nvPr
nvPr.set('descr', 'Descriptive alt text here')
```

### Font embedding
python-pptx provides NO font embedding API. Options:
- Use a template `.pptx` that already has fonts embedded (open in PowerPoint → Embed Fonts → Save)
- Post-process the `.pptx` zip: add TTF files to `ppt/fonts/` and update `[Content_Types].xml`
Do NOT generate from a blank `Presentation()` and expect custom fonts to be embedded.

### Chart legend position — use XL_LEGEND_POSITION enum, never integer literals
`chart.legend.position = 4` raises `ValueError: 4 is not a valid XL_LEGEND_POSITION`
at runtime. The enum values are negative integers that do not match intuitive indices.
Always import and use the enum:

```python
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

chart.legend.position = XL_LEGEND_POSITION.RIGHT   # correct
chart.legend.position = -4152                        # works but fragile — prefer enum
chart.legend.position = 4                            # ValueError at runtime
```

Available positions: `BOTTOM (-4107)`, `CORNER (2)`, `CUSTOM (-4161)`,
`LEFT (-4131)`, `RIGHT (-4152)`, `TOP (-4160)`.

Same applies to any python-pptx chart enum (`XL_CHART_TYPE`, `XL_TICK_MARK`, etc.) —
integer literals are never safe. Always import from `pptx.enum.chart`.

### Pt() requires int, not float
`run.font.size = Pt(7.5)` raises `TypeError` at type-check / linter time
(Pyright: "float is not assignable to int"). Always pass an integer:
```python
run.font.size = Pt(8)           # correct
run.font.size = Pt(int(val))    # correct — when value is computed
run.font.size = Pt(7.5)         # TypeError — even though it works at runtime in some versions
```
This surfaces as a Pyright error in `write_file` lint output; treat it as a real error.

### shape.line.fill.background() — required on dark backgrounds
After `shape.fill.solid()`, always call `shape.line.fill.background()` to suppress
the default shape border. On dark slide backgrounds a 0.75pt default border is
clearly visible and looks like an artifact. Omitting this is the most common dark-theme bug.

### Template loading — never assume layout index
```python
# WRONG — layout indices differ between templates
slide = prs.slides.add_slide(prs.slide_layouts[1])

# CORRECT — inspect layouts by name first
for i, layout in enumerate(prs.slide_layouts):
    print(i, layout.name)
# then use the confirmed index or name match
```

---

## python-docx

### RGBColor is a tuple subclass — no .red/.green/.blue attributes
`docx.shared.RGBColor` is a subclass of `tuple`, not a namedtuple or dataclass.
It has NO `.red`, `.green`, `.blue` attributes. Accessing them raises `AttributeError`
at runtime (the error message is confusingly `'RGBColor' object has no attribute 'red'`).

```python
from docx.shared import RGBColor
c = RGBColor(0x00, 0x20, 0x60)

# WRONG — AttributeError at runtime
hex_col = f"{c.red:02X}{c.green:02X}{c.blue:02X}"

# CORRECT — index like a tuple
hex_col = f"{c[0]:02X}{c[1]:02X}{c[2]:02X}"
```

This matters whenever you build OOXML XML fragments manually (e.g. `w:shd`, `w:left` border
colour, paragraph shading) because those elements require a raw hex string, not an
`RGBColor` object. The pattern arises in every branded-document task that sets cell
backgrounds, left-border stripes, or paragraph fill colours via direct XML manipulation.

Note: when assigning to `run.font.color.rgb` or `cell.font.color.rgb`, you pass the
`RGBColor` object directly — python-docx handles the conversion internally. The raw
hex string is only needed when you build `w:shd`/`w:left`/etc. XML elements yourself.

### Table column widths — silent failure
Setting `cell.width` alone is insufficient. Word recalculates widths on open unless
you also force fixed layout. Required pattern:
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def create_fixed_table(doc, rows, cols, col_widths_inches):
    table = doc.add_table(rows=rows, cols=cols)
    tbl = table._tbl
    tblPr = tbl.tblPr

    # Force fixed layout
    tblLayout = OxmlElement('w:tblLayout')
    tblLayout.set(qn('w:type'), 'fixed')
    tblPr.append(tblLayout)

    # Set cell widths via python-docx API only (NOT raw XML + API — double write corrupts)
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            cell.width = Inches(col_widths_inches[i])
    return table
```
Do NOT set `cell.width` AND manually append a `w:tcW` XML element — that produces two
`w:tcW` children on the same `w:tcPr`, which is invalid OOXML.

### Paragraph.clear() does not exist
`paragraph.clear()` will raise `AttributeError`. To clear a paragraph's runs:
```python
from docx.oxml.ns import qn
for r in para._p.findall(qn('w:r')):
    para._p.remove(r)
```

### "List Number" style shares ONE counter across the whole document
`doc.add_paragraph(style="List Number")` uses Word's built-in numbered-list
style, which is bound to a single shared `numId`/counter for the ENTIRE
document — not one counter per list. If the document has two separate
numbered lists (e.g. a "6 input files" list in §1 and a later "3 remediation
steps" list in §4), the second list's Word-displayed numbers continue from
where the first left off (starts at "7." instead of "1.") even though each
`add_paragraph` call looks independent in code and the paragraph text is
correct. This is invisible to structural checks — `python-docx` reports the
paragraph text and style name correctly; only a rendered view shows the wrong
number.

Two fixes, in order of preference:
1. **Render literal numbers as text**, sidestepping Word's list-counter model
   entirely — most reliable when the source content already carries explicit
   numbers (e.g. numbered markdown source being converted to docx):
   ```python
   def add_numbered(doc, number, text):
       p = doc.add_paragraph()
       p.paragraph_format.left_indent = Inches(0.28)
       p.paragraph_format.first_line_indent = Inches(-0.28)  # hanging indent
       r = p.add_run(f"{number}.\t")
       # ... then add the rest of the text as further runs
       return p
   ```
2. If you need Word's native auto-numbering (e.g. for a list the user will
   extend/reorder in Word later), each independent list needs its OWN
   `numId` via direct XML manipulation — `doc.add_paragraph(style="List
   Number")` alone is not sufficient once there's more than one numbered list
   in the same document.

### Setting a run's font via rFonts XML — must set ascii/hAnsi/cs, not just eastAsia
A helper that manually builds a `w:rFonts` element to force a specific font
name (bypassing `run.font.name` alone, e.g. to guarantee LibreOffice honors
it) is easy to write incompletely — setting only `w:eastAsia` has no effect
on Latin-script text at all. The element needs `w:ascii` and `w:hAnsi` (and
usually `w:cs` for complex-script fallback) to actually change what Word/
LibreOffice renders for normal English text:
```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_run_font(run, name):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), name)   # required — Latin text
    rFonts.set(qn('w:hAnsi'), name)   # required — Latin text, high-ANSI
    rFonts.set(qn('w:cs'), name)      # complex-script fallback
    rFonts.set(qn('w:eastAsia'), name)  # only affects CJK text — insufficient alone
```
Also remember: `run.font.name = "X"` alone does nothing if the font named
isn't installed on the rendering machine — the renderer silently substitutes
a fallback (often a serif font) with no error or warning. If brand fidelity
matters and the declared font isn't installed locally, either install it,
or pick a real installed sans-serif substitute and say so explicitly rather
than declaring a font you can't verify renders correctly (see "Rendered
Visual Verification" in the main SKILL.md — check installed fonts with
`fc-list | grep -i "font name"` before trusting a font declaration).

### Landscape section — order matters
Set orientation BEFORE setting page dimensions:
```python
from docx.enum.section import WD_ORIENT
section.orientation = WD_ORIENT.LANDSCAPE   # step 1
section.page_width  = Inches(11)             # step 2
section.page_height = Inches(8.5)            # step 3
```
Reversing the order may leave portrait layout despite the landscape flag.

### Running header page number field
The standard three-run pattern (begin / instrText / end) works inside a single run's `_r`:
```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

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
```

---

## ReportLab

### Color — must use HexColor, never string literals
```python
# CRASHES at runtime — 'color' expects a Color object
style = ParagraphStyle('body', textColor='#1a1a2e')

# CORRECT
from reportlab.lib.colors import HexColor
style = ParagraphStyle('body', textColor=HexColor('#1a1a2e'))
```

### Two image patterns — do NOT assign to same variable
```python
# WRONG — second assignment silently overwrites first
img = RLImage('chart.png', width=W*0.8, height=3*inch)
img = RLImage('chart.png', width=W*0.8)

# CORRECT — use distinct names, append separately
img_known   = RLImage('chart.png', width=W*0.8, height=3*inch)   # aspect ratio known
img_unknown = RLImage('chart.png', width=W*0.8)                   # ReportLab scales height
```

### Orphaned headings — use KeepTogether
```python
from reportlab.platypus import KeepTogether, Paragraph, Spacer

# Prevents heading ending up at page bottom, content on next page
story.append(KeepTogether([
    Paragraph("Section Title", heading_style),
    Spacer(1, 6),
    Paragraph("First paragraph of section...", body_style),
]))
```

### CONTENT_WIDTH definition
Always define before use; it is not provided by ReportLab automatically:
```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
LEFT_MARGIN = RIGHT_MARGIN = MARGIN
CONTENT_WIDTH = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN
```
If left and right margins differ, compute explicitly rather than `PAGE_W - 2 * MARGIN`.

### Custom font registration
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('CustomFont', '/path/to/font.ttf'))
pdfmetrics.registerFont(TTFont('CustomFont-Bold', '/path/to/font-bold.ttf'))
pdfmetrics.registerFontFamily(
    'CustomFont',
    normal='CustomFont',
    bold='CustomFont-Bold',
)
# Then use 'CustomFont' as the fontName in ParagraphStyle
```
