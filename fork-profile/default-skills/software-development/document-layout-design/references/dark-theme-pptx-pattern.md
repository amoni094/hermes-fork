# Dark-Theme PPTX Pattern — Working Scaffold

Sourced from: Parkinson's Disease Therapies deck (2026-07-03, 5 slides, 13.33×7.5 in).

## Palette setup

```python
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx import Presentation

DARK_BG    = RGBColor(0x14, 0x1E, 0x30)  # near-black navy — slide body bg
MID_BG     = RGBColor(0x1E, 0x2D, 0x40)  # slightly lighter — content slides
ACCENT1    = RGBColor(0x00, 0xA8, 0xE8)  # cyan-blue
ACCENT2    = RGBColor(0x48, 0xCA, 0x9D)  # mint green
ACCENT3    = RGBColor(0xF5, 0xA6, 0x23)  # amber
ACCENT4    = RGBColor(0xE8, 0x5D, 0x5D)  # coral red
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xB0, 0xBD, 0xCC)
DARK_GREY  = RGBColor(0x44, 0x55, 0x66)

W = Inches(13.33)  # widescreen — better than 10 in for multi-column layouts
H = Inches(7.5)
```

## Boilerplate helpers

```python
def new_prs():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs

def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])  # truly blank layout

def fill_slide_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_rect(slide, left, top, width, height, fill_color):
    """Borderless filled rectangle."""
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()  # REQUIRED on dark bg — removes default border
    return shape

def add_text(slide, text, left, top, width, height,
             font_size=18, bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, italic=False):
    """Add a textbox. font_size must be int."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(int(font_size))   # int cast: Pt(float) raises TypeError
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox
```

## Standard content slide header

```python
def content_slide_header(prs, title_text, accent_color):
    slide = blank_slide(prs)
    fill_slide_bg(slide, MID_BG)
    # Dark top bar
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.85), DARK_BG)
    # Left accent stripe
    add_rect(slide, Inches(0), Inches(0.85), Inches(0.07), H - Inches(0.85), accent_color)
    add_text(slide, title_text,
             Inches(0.3), Inches(0.12), Inches(12), Inches(0.6),
             font_size=26, bold=True, color=WHITE, align=PP_ALIGN.LEFT)
    return slide
```

## Horizontal bar chart (manual rectangles)

```python
def draw_bar_chart(slide, chart_left, chart_top, chart_width,
                   bars, scale_max, bar_height=Inches(0.5), gap=Inches(0.55)):
    """
    bars: list of (label, value, color, note_text)
    Returns y_offset after last bar (for placing caveat boxes etc.)
    """
    y = chart_top
    for label, value, color, note in bars:
        bar_w = chart_width * (value / scale_max)
        add_rect(slide, chart_left, y, bar_w, bar_height, color)
        # Value label inside bar
        add_text(slide, f"+{value} h/day",
                 chart_left + Inches(0.1), y + Inches(0.08),
                 bar_w - Inches(0.1), bar_height - Inches(0.15),
                 font_size=15, bold=True, color=WHITE)
        # Drug name to right of bar
        add_text(slide, label,
                 chart_left + bar_w + Inches(0.15), y + Inches(0.02),
                 Inches(2.0), Inches(0.35),
                 font_size=13, bold=True, color=WHITE)
        # Note below drug name
        add_text(slide, note,
                 chart_left + bar_w + Inches(0.15), y + Inches(0.3),
                 Inches(3.5), Inches(0.3),
                 font_size=9, color=LIGHT_GREY)
        y += bar_height + gap
    return y
```

## Status grid (regions × products)

```python
def draw_status_grid(slide, grid_left, grid_top,
                     regions, products, product_colors,
                     data, col_w_region, col_w_drug, row_h,
                     status_colors):
    """
    data: list of lists [drug_idx][region_idx] = (status_label, detail, color_key)
    status_colors: dict mapping color_key → RGBColor
    """
    # Header row
    x = grid_left + col_w_region
    for d_label, d_color in zip(products, product_colors):
        add_rect(slide, x, grid_top, col_w_drug, row_h * 0.7, d_color)
        add_text(slide, d_label,
                 x + Inches(0.08), grid_top + Inches(0.1),
                 col_w_drug - Inches(0.15), row_h * 0.6,
                 font_size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        x += col_w_drug

    even_bg = RGBColor(0x1A, 0x28, 0x3C)
    odd_bg  = RGBColor(0x22, 0x34, 0x4E)

    for r_idx, region in enumerate(regions):
        y = grid_top + row_h * 0.7 + row_h * r_idx
        bg = even_bg if r_idx % 2 == 0 else odd_bg
        # Region label column
        add_rect(slide, grid_left, y, col_w_region, row_h, DARK_BG)
        add_text(slide, region,
                 grid_left + Inches(0.08), y + Inches(0.12),
                 col_w_region - Inches(0.1), row_h - Inches(0.1),
                 font_size=11, bold=True, color=LIGHT_GREY)
        # Drug cells
        x = grid_left + col_w_region
        for d_idx in range(len(products)):
            status, detail, color_key = data[d_idx][r_idx]
            cell_color = status_colors.get(color_key, DARK_GREY)
            add_rect(slide, x, y, col_w_drug, row_h, bg)
            # Status badge
            badge_w = Inches(1.15)
            add_rect(slide, x + Inches(0.08), y + Inches(0.1), badge_w, Inches(0.3), cell_color)
            add_text(slide, status,
                     x + Inches(0.09), y + Inches(0.12),
                     badge_w - Inches(0.05), Inches(0.27),
                     font_size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
            add_text(slide, detail,
                     x + Inches(1.3), y + Inches(0.1),
                     col_w_drug - Inches(1.4), row_h - Inches(0.15),
                     font_size=9, color=LIGHT_GREY)
            x += col_w_drug
```

## Common pitfalls for dark-theme PPTX

- `shape.line.fill.background()` MUST be called after every `shape.fill.solid()`.
  Without it a thin default border appears on dark backgrounds.
- `Pt(float)` raises `TypeError` at type-check time; always cast: `Pt(int(n))`.
- `prs.slide_width` / `prs.slide_height` live on the `Presentation` object, not on
  the slide. Pass `prs` to any function that needs canvas dimensions.
- Native `add_chart()` produces charts with white/grey backgrounds that don't match dark
  slides. Draw bars as rectangles instead.
- When discovering source files for content: run `search_files(pattern, target="content")`
  in parallel with `session_search`. Session history may be compacted; file content search
  is more reliable for finding actual research documents.
