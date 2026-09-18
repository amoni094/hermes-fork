# PDF (ReportLab) — Full Recipe

## Page Template First
```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor, black, white

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm

doc = SimpleDocTemplate(
    "output.pdf",
    pagesize=A4,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=2 * cm,
    bottomMargin=2 * cm
)
```

## Style Sheets — Extend, Never Bare Hex Strings
ReportLab requires `Color` objects (from `reportlab.lib.colors`), not hex strings.
Using a raw string like `textColor='#1a1a2e'` raises AttributeError at render time.

```python
styles = getSampleStyleSheet()

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['Normal'],
    fontSize=11,
    leading=16,              # line height ≈ fontSize × 1.45
    spaceAfter=8,
    spaceBefore=4,
    textColor=HexColor('#222222'),  # CORRECT: Color object, not bare string
)

h1_style = ParagraphStyle(
    'CustomH1',
    parent=styles['Heading1'],
    fontSize=18,             # ≈ 1.6× body (rounds to 2× at larger body sizes)
    leading=22,
    spaceBefore=14,
    spaceAfter=6,
    textColor=HexColor('#1a1a2e'),   # CORRECT
)

caption_style = ParagraphStyle(
    'CustomCaption',
    parent=styles['Normal'],
    fontSize=8,              # 0.75× body
    leading=11,
    textColor=HexColor('#666666'),
)
```

## Custom Fonts — Register Before Use
If you use any font not in ReportLab's built-ins (Helvetica, Times, Courier),
register it or ReportLab silently substitutes and character metrics will be wrong,
causing text to overflow boxes without error:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Inter', '/path/to/Inter-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Inter-Bold', '/path/to/Inter-Bold.ttf'))
# Then use 'Inter' as fontName in ParagraphStyle
```

## Flowable Composition — Let Platypus Handle Page Breaks
Never manually calculate Y-positions for paragraph text. Use the flowable pipeline.
To prevent orphaned headings (heading at page bottom, content on next page), wrap
heading + first paragraph in `KeepTogether`:

```python
from reportlab.platypus import KeepTogether

CONTENT_WIDTH = PAGE_W - 2 * MARGIN  # usable width for colWidths calculations

story = []

# Prevent heading orphans — heading always stays with first content paragraph
story.append(KeepTogether([
    Paragraph("Section Title", h1_style),
    Spacer(1, 0.1 * inch),
    Paragraph("First paragraph of the section.", body_style),
]))
story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph("Subsequent paragraphs can flow freely.", body_style))

# Tables: colWidths must sum to <= CONTENT_WIDTH
col_widths = [CONTENT_WIDTH * 0.3, CONTENT_WIDTH * 0.35, CONTENT_WIDTH * 0.35]
# CONTENT_WIDTH = PAGE_W - 2 * MARGIN  (defined above in Flowable Composition section)
data = [["Header A", "Header B", "Header C"],
        ["Row 1a",   "Row 1b",   "Row 1c"]]
t = Table(data, colWidths=col_widths)
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), HexColor('#1a1a2e')),
    ('TEXTCOLOR',  (0,0), (-1,0), white),
    ('FONTSIZE',   (0,0), (-1,-1), 10),
    ('GRID',       (0,0), (-1,-1), 0.5, HexColor('#cccccc')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#f8f8f8'), white]),
]))
story.append(t)

doc.build(story)
```

## Running Headers / Footers (PDF)
For headers and footers on every page, use `onFirstPage` / `onLaterPages` callbacks:

```python
from reportlab.lib.units import cm

def add_header_footer(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(HexColor('#666666'))
    canvas.drawString(MARGIN, PAGE_H - 1.2*cm, "Document Title")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2*cm, f"Page {doc.page}")
    # Footer
    canvas.drawCentredString(PAGE_W / 2, 0.8*cm, "Confidential")
    canvas.restoreState()

doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
```

## Image Handling (PDF)
```python
from reportlab.platypus import Image as RLImage

# Pattern A — aspect ratio known: constrain both dimensions
img_known = RLImage('chart.png', width=CONTENT_WIDTH * 0.8, height=3 * inch)
story.append(img_known)

# Pattern B — aspect ratio unknown: specify only width; ReportLab scales height
img_unknown = RLImage('chart.png', width=CONTENT_WIDTH * 0.8)
story.append(img_unknown)

# Use one pattern per image; do not mix in the same call.
```
