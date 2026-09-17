# UCB Pharma Branding — Validated Palette & Layout

Used in: Parkinson's Disease Therapies 2026 deck (parkinsons_therapies_2026.pptx, July 2026)
and FcRn Inhibitors RLZ vs Efgartigimod deck (July 2026, v1 dark-canvas + v2 white-canvas
Medical Affairs revision). Use this as the authoritative reference for any UCB Medical
Affairs presentation work.

**IMPORTANT — colour correction (July 2026):** the original `UCB_NAVY` value below
(`0x00,0x20,0x60`) was a best-effort visual approximation, never verified against an
official source. It has since been superseded by a value verified directly from
`ucb.com`'s live theme CSS (`.primary` / `.blue-dark` classes — see Verification section
below). **Use `UCB_NAVY = 0x00,0x14,0x89` (`#001489`) going forward.** The old value is
kept in history only for provenance; do not reuse it.

---

## Colour Palette (python-pptx RGBColor)

```python
from pptx.dml.color import RGBColor

UCB_NAVY      = RGBColor(0x00, 0x14, 0x89)   # VERIFIED brand navy (#001489) — see below
UCB_ORANGE    = RGBColor(0xEE, 0x80, 0x00)   # VERIFIED brand orange (#ee8000) — .orange class
UCB_BLUE      = RGBColor(0x00, 0x58, 0xA5)   # Unverified secondary blue — used in v1 dark deck only
UCB_LIGHT_BLU = RGBColor(0x00, 0x9F, 0xD8)   # Unverified — CREXONT drug accent (v1 deck)
UCB_GREEN     = RGBColor(0x43, 0xB0, 0x2A)   # Unverified — VYALEV drug accent (v1 deck)
```

### Verification method (July 2026, RLZ vs Efgartigimod deck)
Confirmed by pulling `ucb.com`'s live Drupal theme CSS bundles (linked from the page
`<head>`) and grepping for hex colors bound to semantically meaningful classes:
```bash
curl -s https://www.ucb.com/ -A "Mozilla/5.0" -o /tmp/ucb.html
grep -oE 'href="[^"]*\.css[^"]*"' /tmp/ucb.html   # theme CSS bundle paths
# fetch each bundle, concatenate, then:
grep -oE '#[0-9a-fA-F]{6}' /tmp/ucb_all.css | sort | uniq -c | sort -rn | head -20
# 261 occurrences of #001489, bound to `.primary{background-color:#001489}` and
# `.blue-dark{background-color:#001489}` — far stronger signal than raw frequency
# alone. #ee8000 confirmed the same way via `.orange{...}`.
```
This is a general technique — see the "Brand Colour Verification" section of the
parent SKILL.md for the reusable pattern beyond UCB.

## Supporting Neutrals

```python
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xB0, 0xBD, 0xCC)
DARK_GREY  = RGBColor(0x44, 0x55, 0x66)
MID_BG     = RGBColor(0x0A, 0x18, 0x38)   # Slide body background (navy-derived)
```

## Drug-to-Colour Mapping

| Drug | Colour | Rationale |
|------|--------|-----------|
| CREXONT (IPX203) | UCB_LIGHT_BLU | Unverified — used in v1 dark-canvas deck only |
| VYALEV / Produodopa | UCB_GREEN | Unverified — used in v1 dark-canvas deck only |
| ONAPGO (SPN-830) | UCB_ORANGE | Verified brand orange |
| Rozanolixizumab (RLZ) | UCB_NAVY (`#001489`, verified) | Two-drug comparison decks: UCB's own agent = verified brand navy |
| Efgartigimod | UCB_ORANGE (verified) | Two-drug comparison decks: comparator = verified brand orange |
| Risk/alert cells | `RGBColor(0xC8, 0x30, 0x2A)` | Not branded — standard alert red |

For **two-drug comparison decks** (e.g. FcRn inhibitors RLZ vs efgartigimod,
July 2026), UCB's own agent uses the verified brand navy and the comparator uses
the verified brand orange, applied consistently across every bar, table header, and
legend. Add a colour-legend strip on the title slide so the mapping is explicit
before the first chart. (v1 of the RLZ/efgartigimod deck used the older unverified
`UCB_BLUE`; v2 corrected this to verified `UCB_NAVY` — prefer v2's palette for any
new UCB two-drug deck.)

## Layout Conventions

Two validated layout styles exist depending on audience — pick based on who reads it:

### Style A — Dark-canvas / specialist audience (v1, Parkinson's deck)
- Full-width navy bar (`UCB_NAVY`), height `Inches(0.82)`, on a dark (`MID_BG`) slide body
- Left orange stripe: width `Inches(0.06)`, same height as header
- Accent left-edge stripe (below header): `Inches(0.06)` wide, colour varies by slide topic
- Denser text acceptable; scientific/technical audience expected to parse detail on-slide

### Style B — White-canvas / generalist audience (v2, FcRn Medical Affairs revision)
- **White slide background** throughout (not dark) — reads as an executive briefing,
  not a technical poster
- White header band with a thin navy hairline rule underneath, plus a short orange tab
  on the left edge (not a full navy header bar)
- Every content slide carries a navy "KEY TAKEAWAY" strip near the bottom (accent bar +
  label + one plain-language sentence) — see the "Audience-Calibrated Density" section
  of the parent SKILL.md for the full pattern and the word-count validator to enforce it
- Body text cut hard vs Style A; mechanistic jargon translated to plain language on-slide,
  full technical detail kept in speaker notes only
- Use Style B whenever the requesting stakeholder is Medical Affairs, a cross-functional
  reviewer, or explicitly asks to "simplify" / "make this less technical"

### UCB wordmark
- Style A (dark deck): right-aligned solid navy box, white "UCB" text, 22pt bold, centred
- Style B (white deck): right-aligned solid navy box with white "UCB" text still works,
  or invert (white box, navy border/text) on a navy title band — either verified as
  legible in the v2 deck

### Footer bar (every slide)
```python
# Style A (dark canvas) footer
def ucb_footer(slide, extra=""):
    add_rect(slide, Inches(0), H - Inches(0.38), W, Inches(0.38), UCB_NAVY)
    add_rect(slide, Inches(0), H - Inches(0.38), Inches(0.6), Inches(0.38), UCB_ORANGE)
    footer_text = "UCB Internal — Medical Affairs · Parkinson's Portfolio Review 2026"
    if extra:
        footer_text += f"  |  {extra}"
    add_text(slide, footer_text,
             Inches(0.7), H - Inches(0.36), W - Inches(1.2), Inches(0.32),
             font_size=8, color=LIGHT_GREY, align=PP_ALIGN.LEFT)
    add_text(slide, "UCB",
             Inches(0), H - Inches(0.36), Inches(0.65), Inches(0.32),
             font_size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Style B (white canvas) footer — thin grey rule instead of solid navy bar,
# small orange square instead of full-width orange stripe
def ucb_footer_white(slide, extra=""):
    add_rect(slide, Inches(0), H - Inches(0.36), W, Inches(0.02), RGBColor(0xD0,0xD3,0xD4))
    add_rect(slide, Inches(0.22), H - Inches(0.28), Inches(0.16), Inches(0.16), UCB_ORANGE)
    add_text(slide, "UCB Internal — Medical Affairs" + (f"  |  {extra}" if extra else ""),
             Inches(0.5), H - Inches(0.33), W - Inches(1.2), Inches(0.33),
             font_size=9, color=RGBColor(0x4B,0x4F,0x54), align=PP_ALIGN.LEFT)
```

### Table row alternation
```python
# Style A (dark canvas)
bg_even = RGBColor(0x0E, 0x22, 0x48)
bg_odd  = RGBColor(0x16, 0x2E, 0x5C)

# Style B (white canvas)
bg_even = RGBColor(0xFF, 0xFF, 0xFF)
bg_odd  = RGBColor(0xF6, 0xF7, 0xF7)   # near-white alt row
```

## Source
`#001489` (navy) and `#ee8000` (orange) verified directly from ucb.com's live theme
CSS (July 2026) — see the Verification method above. Layout conventions and the
unverified secondary palette (light blue, green) are reverse-engineered from UCB's
public brand presence and annual/investor materials; treat those as best-effort until
similarly verified.
