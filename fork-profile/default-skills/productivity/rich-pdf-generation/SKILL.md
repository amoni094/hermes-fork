---
name: rich-pdf-generation
description: >
  Use when generating polished PDFs with tables, colour schemes, graphs, multi-page layout, headers/footers, TOC, and font embedding. ReportLab/Platypus-first; HTML→PDF via WeasyPrint as second path. Includes matplotlib/seaborn chart embedding patterns.
platforms: [linux, macos, windows]
triggers:
  - Task requires a polished multi-page PDF with tables, charts, colour scheme, and professional layout
  - User asks for a visually designed report, brief, or document (not just plain text-to-PDF)
  - Generating branded or designed PDFs beyond simple reportlab/fpdf output
related_skills:
  - pdf
  - document-layout-design
---

# Rich PDF Generation

Use when the task is to produce a professional PDF with any of:
- Formatted tables (zebra striping, colour headers, conditional cell colour, merged cells)
- Embedded charts/graphs (bar, line, pie, scatter, heatmap via matplotlib/seaborn)
- Colour schemes and brand palettes applied consistently across tables and charts
- Multi-page layout with headers, footers, page numbers, and table of contents
- Font embedding and full Unicode support

Complements the `research-document-output` skill (Excel + PowerPoint path).
This skill covers the **PDF** output target specifically.

---

## Library Decision Tree

```
Need rich tables + charts + colour control?
  └─ Use ReportLab/Platypus  (pip install reportlab)

Need HTML/CSS template → PDF? (CSS layout, Jinja2, invoices)
  └─ Use WeasyPrint           (pip install weasyprint)  ← needs system pango/cairo

Need simple, low-dep PDFs with modern table API?
  └─ Use fpdf2                (pip install fpdf2)       ← pure-Python, good on Silverblue

Need JS-driven live charts (Plotly/Chart.js/D3) in PDF?
  └─ Use Playwright/Chromium  (pip install playwright && playwright install chromium)

Need chart-only multi-page vector PDF?
  └─ matplotlib.backends.backend_pdf.PdfPages (zero extra deps)

Need to embed charts in any PDF lib?
  └─ matplotlib → BytesIO PNG → embed as image in PDF
  └─ OR: matplotlib → SVG → svglib.svg2rlg() → ReportLab Drawing (vector, best quality)
```

**Default recommendation: ReportLab + matplotlib for tables+charts.**
fpdf2 is the best zero-friction pick on Fedora Silverblue (pure Python, no system libs).
WeasyPrint is ideal when you already have an HTML/CSS design.
Avoid pdfkit/wkhtmltopdf — deprecated and unmaintained.
borb is AGPL-3.0 — requires a paid license for commercial/closed-source use.

**Silverblue/system-Python note:** WeasyPrint needs pango/cairo system libs.
Install them via `rpm-ostree install pango cairo` or run WeasyPrint inside a toolbox.
ReportLab, fpdf2, and matplotlib are pure-Python (+ Pillow) — cleanest on Silverblue.

---

## Quick Reference

| Task | Approach |
|------|----------|
| Rich PDF with tables + charts | ReportLab Platypus + matplotlib |
| HTML template → PDF | WeasyPrint + Jinja2 |
| Simple PDF, no layout complexity | fpdf2 |
| Chart as PDF element | matplotlib → BytesIO → Image() |
| Zebra table | TableStyle ROWBACKGROUNDS |
| Colour header row | TableStyle BACKGROUND row 0 |
| Merge cells | TableStyle SPAN |
| Repeat header on new page | Table(repeatRows=1) |
| Page numbers / header/footer | BaseDocTemplate + PageTemplate + Frame |
| Table of contents | TableOfContents flowable |
| Embed custom font | TTFont + pdfmetrics.registerFont |

---

## Install

```bash
# If inside a venv:
pip install reportlab matplotlib seaborn pillow weasyprint fpdf2 jinja2

# No venv / Fedora Silverblue (system Python, no pip):
uvx --with reportlab --with matplotlib --with pillow --with seaborn python3 your_script.py

# Run the demo script directly:
uvx --with reportlab --with matplotlib --with pillow \
  python3 ~/.hermes/skills/productivity/rich-pdf-generation/scripts/demo_pdf.py
```

No system deps needed for ReportLab. WeasyPrint requires `libpango` on Linux:
```bash
# Fedora/RHEL
sudo dnf install pango
# Ubuntu/Debian
sudo apt install libpango-1.0-0 libpangoft2-1.0-0
```

---

## ReportLab / Platypus Patterns

### 1. Document Setup with Headers/Footers

```python
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PAGE_W, PAGE_H = A4
MARGIN = 2*cm

def header_footer(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.HexColor("#1a1a2e"))
    canvas.drawString(MARGIN, PAGE_H - 1.2*cm, "My Report")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2*cm, "Confidential")
    # Footer with page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(PAGE_W/2, 0.8*cm, f"Page {doc.page}")
    canvas.restoreState()

frame = Frame(MARGIN, MARGIN + 0.5*cm, PAGE_W - 2*MARGIN, PAGE_H - 2*MARGIN - 1.5*cm)
template = PageTemplate(id="main", frames=[frame], onPage=header_footer)
doc = BaseDocTemplate("output.pdf", pagesize=A4, pageTemplates=[template])
```

### 2. Colour Palette (apply consistently to tables + charts)

```python
# Define once, reuse everywhere
PALETTE = {
    "primary":    "#16213e",   # dark navy
    "secondary":  "#0f3460",   # mid navy
    "accent":     "#e94560",   # red-coral accent
    "light":      "#a8dadc",   # muted teal
    "bg_alt":     "#f1faee",   # off-white row alt
    "text":       "#1d3557",   # body text
    "header_fg":  "#ffffff",   # table header text
}

def hex_color(h):
    h = h.lstrip("#")
    return colors.HexColor(f"#{h}")
```

### 3. Table with Zebra Striping, Colour Header, Merged Cells

```python
from reportlab.platypus import Table, TableStyle

data = [
    ["Region", "Q1", "Q2", "Q3", "Q4", "Total"],   # header
    ["North",  120,   145,  130,  160,  555],
    ["South",  98,    112,  105,  130,  445],
    ["East",   200,   180,  215,  225,  820],
    ["West",   85,    95,   90,   110,  380],
    ["TOTAL",  503,   532,  540,  625,  2200],       # summary row
]

col_widths = [3.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm]

table = Table(data, colWidths=col_widths, repeatRows=1)
table.setStyle(TableStyle([
    # Header row
    ("BACKGROUND",    (0, 0), (-1, 0),  hex_color(PALETTE["primary"])),
    ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
    ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0, 0), (-1, 0),  10),
    ("BOTTOMPADDING", (0, 0), (-1, 0),  8),
    ("TOPPADDING",    (0, 0), (-1, 0),  8),
    # Zebra rows (even rows = alternate bg)
    ("ROWBACKGROUNDS", (0, 1), (-1, -2),
        [colors.white, hex_color(PALETTE["bg_alt"])]),
    # Summary / total row
    ("BACKGROUND",    (0, -1), (-1, -1), hex_color(PALETTE["secondary"])),
    ("TEXTCOLOR",     (0, -1), (-1, -1), colors.white),
    ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
    # Grid
    ("GRID",          (0, 0),  (-1, -1), 0.5, colors.lightgrey),
    ("LINEABOVE",     (0, -1), (-1, -1), 1.5, hex_color(PALETTE["accent"])),
    # Alignment — numbers right, labels left
    ("ALIGN",         (1, 0),  (-1, -1), "RIGHT"),
    ("ALIGN",         (0, 0),  (0, -1),  "LEFT"),
    # Padding
    ("LEFTPADDING",   (0, 0),  (-1, -1), 6),
    ("RIGHTPADDING",  (0, 0),  (-1, -1), 6),
    ("TOPPADDING",    (0, 1),  (-1, -1), 5),
    ("BOTTOMPADDING", (0, 1),  (-1, -1), 5),
]))

# Merge cells example: span first row cols 1-4 under "Quarterly"
# table.setStyle(TableStyle([("SPAN", (1, 0), (4, 0))]))
```

### 4. Embed Matplotlib Chart as PDF Image

Two paths — raster (simple) or vector (best quality for print):

**Raster (PNG, good for most cases):**
```python
import io
import matplotlib
matplotlib.use("Agg")   # MUST set Agg in headless/server code (no display)
import matplotlib.pyplot as plt
from reportlab.platypus import Image

def chart_to_image(fig, width_cm=14, height_cm=8, dpi=150):
    """Render matplotlib fig to a ReportLab Image flowable.
    dpi: 150 for screen/web, 300 for print-ready PDFs.
    figsize controls physical size; dpi controls resolution (pixels = inches * dpi).
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)   # ALWAYS seek(0) before passing to Image() or you get blank output
    from reportlab.lib.units import cm
    return Image(buf, width=width_cm*cm, height=height_cm*cm)

**Vector (SVG via svglib — best for print, fully scalable):**
```python
# pip install svglib
from svglib.svglib import svg2rlg

def chart_to_vector(fig):
    """Returns a ReportLab Drawing flowable (vector, no rasterisation)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    buf.seek(0)
    drawing = svg2rlg(buf)
    return drawing   # add directly to story: elements.append(drawing)

# Chart-only multi-page PDF (zero extra deps beyond matplotlib):
from matplotlib.backends.backend_pdf import PdfPages
with PdfPages("charts.pdf") as pp:
    for fig in figures:
        pp.savefig(fig, bbox_inches="tight")
        plt.close(fig)
```

**Plotly charts (requires kaleido):**
```python
# pip install plotly kaleido
import io
import plotly.graph_objects as go
from reportlab.platypus import Image

fig = go.Figure(data=[go.Bar(x=cats, y=vals)])
# scale=2-3 ≈ retina/print quality; format can also be "svg" or "pdf"
img_bytes = fig.to_image(format="png", scale=3)
buf = io.BytesIO(img_bytes)
buf.seek(0)
img_flowable = Image(buf, width=14*cm, height=8*cm)
# Note: kaleido ships its own Chromium (~200MB) — large install but works offline
```

**Memory pitfall:** always `plt.close(fig)` in loops or you'll leak figures and exhaust RAM.
**PDF file size pitfall:** many high-DPI PNGs bloat the output — use vector (SVG path) for line/bar charts; raster for heatmaps/scatter with dense data.

def make_bar_chart(data: dict, palette: dict, title="") -> plt.Figure:
    """data = {"categories": [...], "series": [{"name": ..., "values": [...]}]}"""
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    cats = data["categories"]
    x = range(len(cats))
    bar_colors = [palette["primary"], palette["secondary"],
                  palette["accent"], palette["light"]]
    for i, series in enumerate(data["series"]):
        offset = i * 0.8 / max(len(data["series"]), 1)
        ax.bar([xi + offset for xi in x], series["values"],
               width=0.7/len(data["series"]),
               label=series["name"],
               color=bar_colors[i % len(bar_colors)])

    ax.set_xticks(list(x))
    ax.set_xticklabels(cats)
    ax.set_title(title, fontsize=13, fontweight="bold",
                 color=palette["text"], pad=12)
    ax.legend(frameon=False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    return fig

# Usage:
fig = make_bar_chart(chart_data, PALETTE, title="Quarterly Revenue by Region")
img_flowable = chart_to_image(fig, width_cm=14, height_cm=8)
plt.close(fig)
elements.append(img_flowable)
```

### 5. Table of Contents

```python
from reportlab.platypus import TableOfContents
from reportlab.lib.styles import ParagraphStyle

toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle(name="TOC1", fontSize=12, leading=16,
                   textColor=hex_color(PALETTE["primary"]),
                   leftIndent=0),
    ParagraphStyle(name="TOC2", fontSize=10, leading=14,
                   textColor=hex_color(PALETTE["text"]),
                   leftIndent=20),
]
elements.append(toc)

# Headings must use doc.notify("TOCEntry", (level, text, pageNum)):
# Wrap heading paragraphs with a bookmark to register with TOC:
from reportlab.platypus import Paragraph
heading_style = ParagraphStyle("H1", fontSize=14, fontName="Helvetica-Bold",
                                textColor=hex_color(PALETTE["primary"]),
                                spaceAfter=8)
def heading(text, level=0):
    anchor = text.lower().replace(" ", "_")
    return Paragraph(f'<a name="{anchor}"/>{text}', heading_style)
```

### 6. Long Tables Across Pages

Use `LongTable` (not `Table`) for tables that may span multiple pages.
Set `repeatRows=1` to repeat the header row on every page.

```python
from reportlab.platypus import LongTable

table = LongTable(data, colWidths=col_widths, repeatRows=1)
```

### 7. Custom Font Embedding

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register TTF — fonts are auto-subset and embedded (full Unicode, not limited to 256 chars)
pdfmetrics.registerFont(TTFont("Inter", "/path/to/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Inter-Bold", "/path/to/Inter-Bold.ttf"))
pdfmetrics.registerFontFamily("Inter",
    normal="Inter", bold="Inter-Bold",
    italic="Inter-Italic", boldItalic="Inter-BoldItalic")
# registerFontFamily makes <b>/<i> Paragraph markup resolve to the right variant
# Then use: ParagraphStyle(..., fontName="Inter")
```

System fonts on Linux: `/usr/share/fonts/` or `~/.local/share/fonts/`.
DejaVu Sans ships with ReportLab as a built-in fallback — good Unicode coverage.

**Unicode best-practice:**
- The 14 built-in PDF fonts (Helvetica, Times-Roman, Courier...) only cover Latin-1.
  Any accented/€/™/non-Latin character beyond that requires a registered TTF.
- Best TTF choices for broad Unicode: **DejaVu Sans** (most Linux systems) or **Noto** families (best CJK/emoji/script coverage).
- Never rely on system-installed fonts — ship font files inside your app/package and register by absolute path.
- Debug missing glyphs: `import reportlab.rl_config; reportlab.rl_config.warnOnMissingFontGlyphs = 1`
- For CJK (Chinese/Japanese/Korean): `from reportlab.pdfbase.cidfonts import UnicodeCIDFont; pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))` — no CMap files needed since ReportLab 2.0.
- Match matplotlib's `plt.rcParams["font.family"]` to the embedded font for visual consistency across charts and tables.

---

## WeasyPrint Path (HTML → PDF)

Best for: template-driven reports, reusing existing CSS/HTML design, responsive layout.

```python
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

env = Environment(loader=FileSystemLoader("templates/"))
tmpl = env.get_template("report.html")
html_str = tmpl.render(data=my_data, palette=PALETTE)

HTML(string=html_str).write_pdf(
    "output.pdf",
    stylesheets=[CSS(string="""
        @page { size: A4; margin: 2cm; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #16213e; color: white; padding: 8px; }
        tr:nth-child(even) td { background: #f1faee; }
        td { padding: 6px 8px; border-bottom: 1px solid #ddd; }
    """)]
)
```

Charts: render matplotlib to PNG files → reference as `<img src="chart.png">` in template.

---

## fpdf2 Path (Simple, Zero System Deps)

fpdf2 has a modern `table()` context manager (added in 2.7.0, mature in 2.8.x).
Good choice on Fedora Silverblue — pure Python, no system libs needed.

```python
from fpdf import FPDF, FontFace
from fpdf.enums import TableBordersLayout

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(22, 33, 62)
        self.cell(0, 8, "My Report", align="L")
        self.ln()

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

pdf = PDF()
pdf.add_page()
pdf.set_font("Helvetica", size=11)

# Styled header row
headings_style = FontFace(emphasis="BOLD", color=255, fill_color=(16, 33, 62))

with pdf.table(
    col_widths=(40, 20, 20, 25),
    headings_style=headings_style,
    line_height=7,
    text_align="CENTER",
    borders_layout=TableBordersLayout.MINIMAL,
    num_heading_rows=1,   # repeat this many rows as headers on page break
) as table:
    for i, row_data in enumerate(data):
        row = table.row()
        fill = FontFace(fill_color=(241, 250, 238)) if i % 2 == 0 else None
        for item in row_data:
            row.cell(str(item), style=fill)

# Conditional banding via callable (e.g. highlight negatives):
def highlight_negative(row_idx, col_idx):
    val = data[row_idx][col_idx]
    return isinstance(val, (int, float)) and val < 0

# Pass as cell_fill_mode= with a fill colour set separately
# (see fpdf2 docs — the callable controls WHICH cells; FontFace sets colour)

# Embed PNG chart:
import io
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
buf.seek(0)
pdf.image(buf, x=10, w=180)   # w in mm on the page

pdf.output("output.pdf")
```

---

## Conditional Cell Colouring

```python
# In TableStyle: highlight cells where value exceeds threshold
def build_conditional_style(data, col_idx, threshold, hi_color, lo_color):
    styles = []
    for row_idx, row in enumerate(data[1:], start=1):  # skip header
        val = row[col_idx]
        if isinstance(val, (int, float)):
            color = hex_color(hi_color) if val >= threshold else hex_color(lo_color)
            styles.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), color))
    return styles

table.setStyle(TableStyle(
    base_styles +
    build_conditional_style(data, col_idx=4, threshold=200,
                            hi_color="#52b788", lo_color="#e63946")
))
```

---

## Colour Scheme Tips

- **RGB for screen-target PDFs** (web delivery): use `colors.HexColor("#rrggbb")`
- **CMYK for print PDFs**: `colors.CMYKColor(c, m, y, k)` — values 0.0–1.0 (NOT 0–100)
  - Set `colorSpace="CMYK"` on the doc to auto-convert internal blacks/greys
  - RGB bitmaps embedded in a CMYK doc are NOT auto-converted — pre-convert images in ImageMagick if colour-critical
- **Spot colours (Pantone)**: `colorSpace="SEP"` or `"SEP_CMYK"` + `spotName="PANTONE 288 CV"` — CMYK values are on-screen preview only; guarantees brand consistency on press
- **Bleed for print**: extend colour 3mm/8pt beyond page edge + enable `useCropMarks` to avoid white edges after cutting
- **Consistent palettes**: define a single palette dict of named `Color`/`CMYKColor` objects — reuse the SAME objects in `TableStyle` AND matplotlib (`ax.plot(color=PRIMARY.hexval())`). Never hardcode the same hex twice.
- **Contrast**: WCAG AA minimum 4.5:1 for body text on coloured cells; don't encode meaning by colour alone (add symbols/labels for conditional formatting)
- **Seaborn palettes for charts**: `sns.color_palette("muted")` or `sns.color_palette("deep")` — export as hex list and cross-reference your PALETTE dict
- **Avoid pure black (#000000) backgrounds** — use #1a1a2e or similar near-black for professional appearance
- **Chart/table colour parity**: set `plt.rcParams["font.family"]` to match the embedded PDF font; feed shared palette hex into matplotlib `color=`, `cmap`, and `rcParams` so charts are visually consistent with tables

---

## Chart Types and When to Use

| Chart | Library call | Best for |
|-------|-------------|----------|
| Bar/column | `ax.bar()` | Categorical comparisons |
| Grouped bar | `ax.bar()` + offset x | Multiple series by category |
| Line | `ax.plot()` | Trends over time |
| Area | `ax.fill_between()` | Cumulative trends |
| Pie/donut | `ax.pie()` | Part-to-whole (≤6 slices) |
| Scatter | `ax.scatter()` | Correlation / distribution |
| Heatmap | `sns.heatmap()` | Matrix / correlation |
| Box/violin | `sns.boxplot()` | Distribution comparison |

Always: `fig.tight_layout()`, `dpi=150` minimum for PDF embed, `bbox_inches="tight"`.

---

## Full Document Assembly Pattern

```python
from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

elements = []

# 1. Cover / title page
elements.append(Paragraph("Report Title", title_style))
elements.append(Spacer(1, 0.5*cm))
elements.append(Paragraph("Subtitle · Date", subtitle_style))
elements.append(PageBreak())

# 2. Table of contents (populated after build)
elements.append(toc)
elements.append(PageBreak())

# 3. Section 1
elements.append(heading("Section 1: Overview"))
elements.append(Paragraph(body_text, body_style))
elements.append(Spacer(1, 0.3*cm))
elements.append(table)
elements.append(Spacer(1, 0.5*cm))

# 4. Charts section
elements.append(heading("Section 2: Trends"))
fig = make_bar_chart(chart_data, PALETTE, title="Revenue by Region")
elements.append(chart_to_image(fig, 14, 8))
plt.close(fig)

# 5. Build
doc.multiBuild(elements)  # multiBuild required for TOC; build() for no TOC
```

Use `doc.multiBuild(elements)` (not `doc.build()`) when a TableOfContents
flowable is present — it renders the PDF twice to resolve page numbers.

---

## Pitfalls

**multiBuild vs build** — TOC requires `doc.multiBuild()`. Using `doc.build()`
with a TOC produces a blank TOC. Also use `multiBuild` for "Page X of Y" footers
(total page count unknown until the first pass completes).

**Page X of Y pattern:**
```python
# Two-pass build with a canvas subclass that records total pages:
from reportlab.platypus import BaseDocTemplate

class TwoPassDoc(BaseDocTemplate):
    def handle_documentBegin(self):
        self._saved_page_count = 0
        super().handle_documentBegin()
    def handle_pageEnd(self):
        self._saved_page_count += 1
        super().handle_pageEnd()

def footer_with_total(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    total = getattr(doc, "_saved_page_count", "?")
    canvas.drawCentredString(PAGE_W/2, 0.8*cm, f"Page {doc.page} of {total}")
    canvas.restoreState()
# Call doc.multiBuild(story) — first pass counts pages, second renders totals.
```

**LongTable vs Table** — For tables spanning multiple pages, use `LongTable`
(not `Table`). `Table` tries to fit everything on one page and breaks layout.

**ROWBACKGROUNDS vs BACKGROUND** — `ROWBACKGROUNDS` takes a list of colours
and cycles through rows automatically. `BACKGROUND` sets a single cell range.
Don't mix them on the same rows — `BACKGROUND` wins last if they overlap.

**SPAN and grid lines** — After `SPAN`, `GRID` still draws lines through the
merged area. Add `("LINEAFTER", ..., colors.white)` to blank out inner borders.

**Chart DPI** — Below 100 DPI charts look blurry in print. Use 150 for screen,
300 for print-ready PDFs. Higher DPI = larger file.

**BytesIO reuse** — Always `buf.seek(0)` after writing to a BytesIO before
passing to `Image()`. Omitting this produces blank images.

**WeasyPrint + system fonts** — WeasyPrint resolves CSS `font-family` from
system fonts via fontconfig. Run `fc-list` to verify the font is registered.

**fpdf2 tables** — fpdf2's table() context manager is good for basic tables.
Use ReportLab for any table with complex conditional colouring, merged cells, or long-table page splitting.

**borb licensing** — borb is AGPL-3.0. Any closed-source or commercial use requires a paid license. Avoid unless you're sure of your licence constraints.

**kaleido install size** — kaleido ships its own Chromium (~200MB). Worth it for Plotly charts but slow first install. Alternative: render Plotly to SVG and convert via svglib, or save Plotly HTML and screenshot with Playwright.

**Playwright fallback (JS charts → PDF):**
```bash
# For Chart.js / D3 / Highcharts that can't be reproduced in matplotlib:
pip install playwright && playwright install chromium
```
```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("file:///path/to/chart.html")
    page.wait_for_timeout(1000)   # let JS render
    page.screenshot(path="chart.png", full_page=True)
    browser.close()
# Then embed chart.png in the PDF via ReportLab Image() or fpdf2 pdf.image()
```

**reportlab HexColor** — Always prefix with `#`: `colors.HexColor("#1a1a2e")`.
Without the `#` it silently produces black.

**Page size units** — ReportLab uses points (1 pt = 1/72 inch). Import `cm`
from `reportlab.lib.units` and multiply: `2*cm` = 2 centimetres.

**File handle** — `doc.multiBuild(elements)` writes to the filename passed at
`BaseDocTemplate(filename, ...)`. Don't re-open the file during build.
