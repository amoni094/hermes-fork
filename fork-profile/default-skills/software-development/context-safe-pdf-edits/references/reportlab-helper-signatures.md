# ReportLab helper signatures — NAB wireframe script

Source: `/var/home/rainbow/build_nab_wireframes.py`

## Core helpers (as of 2026-07-03)

```
def wrap(x, y, s, size, w, font="Helvetica", color=CHARCOAL, leading=None)
def divider(x, y, w, color=BORDER, lw=1)
def browser_frame(x, y, w, h, url, nav_items=None, active=0) -> inner_y
def field(x, y, w, label, placeholder="", h=30, required=False, help_txt="")
def dropdown(x, y, w, label, value, h=30, required=False)
def button(x, y, w, s, primary=True, h=28)
def checkbox(x, y, label, checked=False)         # NO max_width, NO wrap
def radio_group(x, y, label, options, selected=0)
def pill(x, y, s, bg=RED, fg=WHITE, size=7.5) -> width
def rect(x, y, w, h, fill=None, stroke=None, lw=1, radius=0)
def text(x, y, s, size=9, font="Helvetica", color=CHARCOAL)
def ctext(x, y, s, size=9, font="Helvetica", color=CHARCOAL)   # centered on x
def rtext(x, y, s, size=9, font="Helvetica", color=CHARCOAL)   # right-aligned at x
```

## Page geometry constants
```
PW = 620   # page width
PH = 877   # page height (A4 approx at 72dpi)
M  = 36    # margin
```

## Useful derived values
```
full_browser_w = PW - 2*M          # 548
full_browser_h = PH - 148          # 729 — leaves room for header + footer
inner_w        = full_browser_w - 40  # 508 — inner usable content width
col2_x         = M + inner_w//2 + 14  # right column start for 2-col form layout
col_w          = inner_w//2 - 14      # each column width in 2-col layout
```

## Checkbox with wrapping label — manual pattern
```python
rect(_cx, _cby, 11, 11, fill=WHITE, stroke=BORDER, lw=1, radius=2)
if _chk:
    set_stroke(RED); c.setLineWidth(1.5)
    c.line(_cx+2, _cby+5, _cx+4.5, _cby+2.5)
    c.line(_cx+4.5, _cby+2.5, _cx+9, _cby+9)
wrap(_cx+17, _cby+2, _lbl, 8, col_width-20, color=CHARCOAL)
# row spacing: _cby -= 46  (generous to avoid collision on 2-line wraps)
```

## Named personas used in wireframe examples
- L. Eyelander — Sourcing/submitter side (NOT legal). Correct replacement for S. Hoare.
- Kelsey Montgomery / K. Montgomery — Legal (primary lawyer)
- Bettina Collins / B. Collins — Legal (triage queue)
- Lauren Faba / L. Faba — Legal (product/comms log)
- S. Hoare is from LEGAL, not sourcing — do not use as a sourcing persona.
- Do NOT use A. Monin or generic "S. Manager"

## Logo embed — real NAB brand assets
NAB logo is NOT a ★ unicode star + "nab" text. It is a 7-pointed red star with
two overlapping dark-red arrow slashes through the upper-right, plus the stacked
wordmark "national australia bank" in bold black lowercase sans-serif.

Real PNGs (1548×734 RGBA, transparent bg):
- Light (black text): `/var/home/rainbow/nab_logo.png`
- Dark (white text):  `/var/home/rainbow/nab_logo_dark.png`
Source: companieslogo.com/img/orig/NAB.AX_BIG*.png

drawImage anchor pattern:
```python
c.drawImage(img_path, x, y - h + 4, width=w, height=h, mask="auto", preserveAspectRatio=True)
```
where h = w * (734/1548). At scale=1.0 render at 110pt wide (~52pt tall).

Persona appears in multiple places per wireframe page — always grep for all before patching:
    grep -n 'Hoare\|Monin\|Eyelander\|name' build_nab_wireframes.py
Check: msgs list (chat), events list (audit trail), qrows list (triage queue).

## Inline section title page pattern
When you need to append content (key recs, matrix table) to a section-title page,
replace the `section_title(N, ...)` call with this inline block (own the showPage):

```python
set_fill(WHITE); c.rect(0, 0, PW, PH, fill=1, stroke=0)
set_fill(RED); c.rect(0, 0, 150, PH, fill=1, stroke=0)
ctext(75, PH/2 + 20, "N", size=140, font="Helvetica-Bold", color=WHITE)
ctext(75, PH/2 - 40, "INITIATIVE", size=12, font="Helvetica-Bold", color=WHITE)
logo(200, PH - 60, scale=1.0)
text(200, PH/2 + 60, "Section Title Here", size=30, font="Helvetica-Bold", color=CHARCOAL)
wrap(200, PH/2 + 30, "Subtitle text...", 13, PW - 200 - M, color=MGREY, leading=17)
_bullets = ["bullet 1", "bullet 2"]
yy = PH/2 - 10
for b in _bullets:
    set_fill(RED); c.setFont("Helvetica-Bold", 11); c.drawString(200, yy, "\u2192")
    yy = wrap(218, yy, b, 10.5, PW - 218 - M, color=CHARCOAL, leading=14)
    yy -= 8
# append key recs, matrix table, etc. here
key_recs(200, yy - 4, PW - 200 - M, "Key Recommendations — X", [...])
page_footer("")
c.showPage()  # you own this now — do not call section_title() above
```

## Section title page cover chip row (page 1)
Four initiatives; adjust cw and gap for four items:
```python
chips = ["1  Commercial Intake Form", "2  Priority Classification",
         "3  Communication Log", "4  Knowledge Management"]
cw = 196; gap = 16
total = cw * 4 + gap * 3; sx = (PW - total) / 2
```
