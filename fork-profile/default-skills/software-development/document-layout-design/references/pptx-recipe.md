# PowerPoint (python-pptx) — Full Recipe

## CRITICAL: Use Slide Layouts and Placeholders — Never Freehand

The most common AI-agent mistake is adding arbitrary TextFrame shapes with hardcoded
positions. Use layout placeholders instead.

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

prs = Presentation()

# --- If starting from blank ---
slide_layout = prs.slide_layouts[1]  # "Title and Content" in default template
slide = prs.slides.add_slide(slide_layout)
title = slide.placeholders[0]
body  = slide.placeholders[1]
title.text = "Short Title"

# --- If loading an existing template, NEVER assume layout index ---
# Layout order varies by template. Always inspect first:
prs = Presentation("template.pptx")
for i, layout in enumerate(prs.slide_layouts):
    print(i, layout.name)  # find the right index before using it
```

## EMU Units — Correct Slide Dimensions

EMU (English Metric Units): 1 inch = 914,400 EMU, 1 cm = 360,000 EMU.

Standard widescreen slide: **10 inches wide × 7.5 inches tall**
(= 9,144,000 EMU × 6,858,000 EMU)

```python
from pptx.util import Inches, Cm

# Safe content zone: 0.5 inch margin on all sides
SAFE_LEFT   = Inches(0.5)
SAFE_TOP    = Inches(0.5)
SAFE_WIDTH  = Inches(9.0)   # 10 - 2*0.5
SAFE_HEIGHT = Inches(6.5)   # 7.5 - 2*0.5

# 2-column grid with gutter
COL_WIDTH  = Inches(4.25)   # (9.0 - 0.5 gutter) / 2
COL_GUTTER = Inches(0.5)
LEFT_COL   = SAFE_LEFT
RIGHT_COL  = SAFE_LEFT + COL_WIDTH + COL_GUTTER
```

## Text Overflow Prevention

python-pptx does NOT auto-reflow text out of shape bounds. Text silently overflows.
Estimate fit before writing; if unsure, use a smaller font size with a floor of 18pt
for body and 24pt for titles.

```python
from pptx.util import Pt
from pptx.oxml.ns import qn
from lxml import etree

def estimate_font_size(text, shape_height_emu, approx_chars_per_line=40,
                       min_pt=18, max_pt=36):
    """
    Estimate a font size that fits text within a shape's height.
    Returns a plain float (points); assign to font.size via Pt(result).
    shape_height_emu: shape.height in EMU (914400 per inch)
    min_pt: enforce a floor (18 for slides, 10 for print)
    max_pt: cap — usually 36 for body text
    Example:
        size = estimate_font_size(text, shape.height, min_pt=18)
        run.font.size = Pt(size)
    """
    lines = max(1, len(text) // approx_chars_per_line + 1)
    available_inches = shape_height_emu / 914400
    # ~72pt per inch, 80% fill factor for line spacing
    computed = (available_inches / lines) * 72 * 0.8
    return max(min_pt, min(computed, max_pt))

def get_autofit_type(shape):
    """
    Returns the autofit setting for a text-bearing shape.
    'noAutofit'  — text may overflow silently (default for freehand shapes)
    'spAutoFit'  — shape grows to fit text (can break layout)
    'normAutofit'— shrinks text to fit (what you usually want for placeholders)
    Returns None if shape has no text frame.
    """
    if not shape.has_text_frame:
        return None
    txBody = shape.text_frame._txBody
    bodyPr = txBody.find(qn('a:bodyPr'))
    if bodyPr is None:
        return None
    for child in bodyPr:
        tag = etree.QName(child).localname
        if tag in ('noAutofit', 'spAutoFit', 'normAutofit'):
            return tag
    return 'noAutofit'  # default when no child present

def check_overflow_risk(shape):
    """
    Returns True if the shape is configured for silent overflow.
    Call after adding text to any freehand shape.
    """
    return get_autofit_type(shape) == 'noAutofit'
```

Enable shrink-on-overflow (normAutofit) in the Slide Master — set it at master level,
not per-slide, so all placeholders inherit it.

## Dark-Theme Presentations (Chart vs Manual Shape)

When building dark-background slide decks, native python-pptx chart objects can be used
but with caveats. Chart backgrounds inherit from the slide master and may show white or
grey boxes behind the plot area on dark fills — this depends on the PowerPoint version
rendering the file. Manually drawn shapes give full color control and are always safe.

**Use `add_chart()` when:** the chart type genuinely benefits from native interactivity
(line charts, scatter, time series) and the white chart background is acceptable, or the
file will be rendered via LibreOffice Impress where theme inheritance is less aggressive.

**Use manually drawn shapes when:** bar charts, status grids, or any chart where
colored fill is the primary visual signal — shape rectangles are simpler and more
reliable on dark themes.

If using `add_chart()` on a dark slide, verify in PowerPoint that the plot area
background is not a white box. If it is, switch to the manual shape approach below.

Key decisions for dark-theme decks:

1. **Always start from a blank layout** (`prs.slide_layouts[6]`), then fill the slide
   background with `slide.background.fill.solid()` / `.fore_color.rgb = COLOR`.
   Never set background color via shape overlays — it fights with the background object.

2. **Draw bar charts as rectangles**, not `add_chart()`. This gives full color control:
   ```python
   # Horizontal bar: value-proportional width
   bar_w = chart_area_width * (value / scale_max)
   shape = slide.shapes.add_shape(1, chart_left, y, bar_w, bar_height)
   shape.fill.solid()
   shape.fill.fore_color.rgb = ACCENT_COLOR
   shape.line.fill.background()  # remove border
   ```

3. **Status grids (region × product)**: nest two loops — outer for rows, inner for cols.
   Draw a background rect first, then a colored "badge" rect, then text labels on top.
   All coords are computed as `base_x + col_index * col_width`, `base_y + row_index * row_height`.

4. **Suppress ALL shape borders**: always call `shape.line.fill.background()` after
   `shape.fill.solid()`. Omitting this leaves a faint default border visible on dark backgrounds.

5. **font_size must be int, not float**. `run.font.size = Pt(7.5)` raises a type error
   at validation; round or cast: `Pt(8)` or `Pt(int(computed_size))`.

6. **Widescreen dark decks**: set `prs.slide_width = Inches(13.33)` and
   `prs.slide_height = Inches(7.5)`. The standard 10×7.5 width is too narrow for
   multi-column data layouts; 13.33 in (≈ 1920px at 144 dpi) gives a genuine 16:9 canvas.

7. **Discovery of source files**: when building a presentation from prior research, do NOT
   rely solely on `session_search` — compacted sessions may not return file paths.
   Use `search_files(pattern="keyword", target="content", file_glob="*.md")` to find
   actual markdown files that contain the research. Run both in parallel.

See `references/dark-theme-pptx-pattern.md` for a full working scaffold.

## Post-Generation Validation

Run on every generated presentation before returning output.
Define a shared safe-zone margin constant to keep validation consistent with layout code:

```python
# Share this constant with your layout code (SAFE_LEFT etc.)
SAFE_MARGIN_EMU = int(914400 * 0.5)  # 0.5 inch

def check_overlaps(slide):
    """Returns list of overlap descriptions. Empty list = clean."""
    shapes = list(slide.shapes)
    issues = []
    for i, s1 in enumerate(shapes):
        for s2 in shapes[i+1:]:
            l1, t1 = s1.left, s1.top
            r1, b1 = s1.left + s1.width, s1.top + s1.height
            l2, t2 = s2.left, s2.top
            r2, b2 = s2.left + s2.width, s2.top + s2.height
            if l1 < r2 and r1 > l2 and t1 < b2 and b1 > t2:
                issues.append(f"OVERLAP: '{s1.name}' overlaps '{s2.name}'")
    return issues

def check_safe_zone(slide, prs, margin_emu=SAFE_MARGIN_EMU):
    """
    Returns shapes that extend outside the safe zone.
    Pass prs (Presentation object) so we can read slide dimensions correctly.
    """
    issues = []
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    for s in slide.shapes:
        if s.left < margin_emu:
            issues.append(f"SAFE ZONE: '{s.name}' too close to left edge")
        if s.top < margin_emu:
            issues.append(f"SAFE ZONE: '{s.name}' too close to top edge")
        if s.left + s.width > slide_w - margin_emu:
            issues.append(f"SAFE ZONE: '{s.name}' too close to right edge")
        if s.top + s.height > slide_h - margin_emu:
            issues.append(f"SAFE ZONE: '{s.name}' too close to bottom edge")
    return issues

def validate_presentation(prs):
    """
    Run full validation. Returns list of issue strings.
    Decision rule:
      - Empty list  → proceed to save/return
      - Non-empty   → log issues; if any OVERLAP or SAFE ZONE: fix before returning.
                      Do NOT silently ignore — raise ValueError or re-layout.
    """
    all_issues = []
    for i, slide in enumerate(prs.slides):
        for issue in check_overlaps(slide):
            all_issues.append(f"Slide {i+1}: {issue}")
        for issue in check_safe_zone(slide, prs):
            all_issues.append(f"Slide {i+1}: {issue}")
    return all_issues

# Usage pattern:
# issues = validate_presentation(prs)
# if issues:
#     raise ValueError("Layout validation failed:\n" + "\n".join(issues))
# prs.save("output.pptx")
```

### CRITICAL: Exempt structural chrome or you'll chase phantom warnings

The single biggest time-sink when running this validator on a branded deck is
**false positives from intentional chrome**. A naive safe-zone check flags every
header title, footer citation, and wordmark box as a violation because those
elements *intentionally* live in the top/bottom margins — and it flags the two
footer text runs (left note + right citation) as an "overlap" because they share
the footer band. On a 10-slide deck this produced **47 warnings, all false**,
before exemption. Build the exemptions in from the start:

1. **Name your chrome shapes.** When you create header/footer/wordmark textboxes,
   set `shape.name = "HDR_title"` / `"HDR_wordmark"` / `"FOOTER_note"` /
   `"FOOTER_cite"`. Then the validator can skip anything whose name starts with
   `HDR_` or `FOOTER_`.
2. **Exempt the header/footer bands geometrically** (belt-and-suspenders in case a
   shape is unnamed): treat any text whose `bottom <= HEADER_H` or whose
   `top >= slide_h - FOOTER_H` as structural chrome, not content — skip safe-zone
   and overlap checks for it.
3. **Exempt full-canvas slides.** Title / section-divider / conclusion slides use a
   full-bleed layout with no header/footer content rule. Keep an explicit set
   (e.g. `FULL_CANVAS_SLIDES = {1, 10}`) and skip the safe-zone check on those
   slide indices — text legitimately sits high/low there.
4. **Full-bleed rectangles and far-left stripes are already structural** — skip any
   shape with `width >= slide_w - 0.05` or (`left < 0.1 and width < 0.15`).

The goal is a validator that returns **zero warnings on a correct deck**, so a
non-zero count is always a real problem. A validator that cries wolf 47 times is
worse than no validator — you stop reading it. After exemptions, the only warnings
left in this session were 4 *genuine* ones: log-scale axis tick labels hanging off
the left safe zone, fixed by shifting the chart plot-left constant right (e.g.
`cx = 1.2 → 1.55`) so the outermost label starts inside the safe margin.

## Image Handling (PPTX)
- Always add images via `slide.shapes.add_picture(path, left, top, width, height)`,
  explicitly specifying both width AND height to avoid aspect ratio distortion.
- Keep images within the safe zone.
- Use one consistent image style per deck (photograph, line art, or icon — not mixed).
- Place images consistently (e.g. always right-half of slide, same size).
- Alt text in python-pptx requires direct XML manipulation (the library has no
  convenience wrapper). Use this pattern:
  ```python
  from lxml import etree
  from pptx.oxml.ns import qn

  pic = slide.shapes.add_picture(img_path, left, top, width, height)
  # Alt text lives on nvPicPr/nvPr as 'descr' attribute
  nvPr = pic._element.nvPicPr.nvPr
  nvPr.set('descr', 'Descriptive alt text here')
  ```
