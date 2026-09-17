---
name: document-layout-design
triggers:
  - User wants to generate a professional PDF, PowerPoint, or Word document
  - Task requires a designed visual layout (not just plain markdown output)
  - User asks for a report, slide deck, or formatted document with layout control
  - Building a ReportLab, python-pptx, or docx document programmatically
  - Integrating gap-analysis findings into a governance document as tracked changes
  - Consolidating review annotations into clean prose in a Word document
description: >
  Use when designing and generate professional PDFs, PowerPoints, and Word documents programmatically. Covers layout discipline, typography hierarchy, spacing, alignment, density control, and common AI agent failure modes. Load before any task involving python-pptx, python-docx, ReportLab, or similar libraries.
tags: [pdf, pptx, docx, layout, typography, python-pptx, reportlab, python-docx, formatting]
related_skills:
  - pdf
  - docx
  - context-safe-pdf-edits
---

# Document Layout Design — AI Agent Best Practices

## Format Selection (decide before writing code)

| Goal | Format |
|---|---|
| Narrative, visual communication, presenting to an audience | PPTX |
| Dense prose, regulatory docs, editable reports | DOCX |
| Archival, distribution, fixed layout (receipts, forms, certificates) | PDF |

Never default to PPTX for prose-heavy content — if the content is inherently dense
(long paragraphs, many data rows), use DOCX even if delivery is "a presentation,"
and convert manually. Never use PDF when the user needs to edit the output.

Note: if you're presenting dense content to an audience, PPTX density rules will
conflict. In that case: simplify the content first, then apply PPTX rules. If
content cannot be simplified to slide density limits, use DOCX and deliver as a
printed handout alongside a minimal PPTX deck.

---

## Core Insight

LLMs reliably handle content quality but consistently underperform on structural
and stylistic document quality. The highest-failure dimensions are:
- whitespace allocation
- field/element alignment
- visual hierarchy (heading vs body distinction)
- text density per slide/section
- consistency throughout the document

Evidence: specialized document-quality evaluators (e.g. Microsoft DocReward, 2025)
outperform general-purpose LLMs on structure/style judgment by a substantial margin.
Self-review is unreliable for layout quality. Use explicit rules and post-generation
checks instead — not prompting the model to "review its own layout."

---

## Universal Rules (all formats)

### Typography: 4-Level Hierarchy
Every document must use exactly 4 levels — no more, no less:

| Level | Role | Size vs body |
|---|---|---|
| H1 | Section / slide title | 2x body |
| H2 | Subsection or callout | 1.5x body |
| Body | Content text | baseline |
| Caption | Source citations, footnotes | 0.75x body |

If something "feels like a heading," make it formally a heading at the correct level.
Never bold + enlarge body text as a fake heading — it violates this hierarchy AND
breaks programmatic styling (named styles in DOCX, placeholder inheritance in PPTX).

### Whitespace = Signal
- Leave 20-30% of each page/slide empty. This is not waste — it creates reading flow.
- If something feels cramped: delete content first, resize second.
- Never shrink font below: 10pt body (print) / 18pt slide body.
- Increase paragraph spacing BEFORE increasing margins. Margins are structural;
  paragraph spacing is content-level.
- Rule: if you can't remove anything from a slide, the layout isn't done.

### Alignment — Never Mixed Within a Semantic Level
Standard professional layouts mix alignment across levels (left body, center title,
right page numbers). What is forbidden: inconsistent alignment within the same level.
- Body text: always left-aligned
- Slide/page titles: center or left, pick one, apply everywhere
- Page numbers / running headers: right-aligned
- Table cell content: pick left or center, apply consistently within the table

### Consistency Beats Novelty
Same font family throughout. Same color palette (3 colors: primary 60%, accent 30%,
neutral 10%). Same table style. Same margin/padding grid. Variation signals error.

### Slide Density Rules (PPTX only)
- 6 words or fewer in the slide title (default rule; data/reference slides may exceed)
- 30 words of body text per slide is a soft ceiling — the intent is "readable in 10
  seconds." Data tables, API reference slides, and comparison slides legitimately exceed
  this. When in doubt: split into two slides rather than shrink text.
- At most 6 bullet points; 3-4 is better
- One visual structure (table, chart, grid) per slide
- If prose content exceeds slide limits: use DOCX, not smaller fonts

---

## PowerPoint (python-pptx)

Full recipe + code: `references/pptx-recipe.md`

- **Never freehand**: always use slide layout placeholders (`slide.placeholders[0/1]`), never add raw TextFrame shapes with hardcoded EMU positions
- **Safe zone**: 0.5-inch margin; widescreen = 10×7.5 in (or 13.33×7.5 for 16:9 data decks); all shapes must pass `check_overlaps()` + `check_safe_zone()` before save
- **Dark themes**: set `slide.background.fill.solid()` first; draw bars as rectangles not `add_chart()`; suppress borders with `shape.line.fill.background()`; font sizes must be int not float

See also: `references/dark-theme-pptx-pattern.md` for full working scaffold.

---

## Word Documents (python-docx)

Full recipe + code: `references/docx-recipe.md`

- **Styles over ad hoc**: always `doc.add_heading(level=N)` and named styles; never `run.bold=True` + `run.font.size=Pt(16)` as fake headings
- **Fixed table layout**: call `create_fixed_table()` with explicit `col_widths_inches`; set `tblLayout type='fixed'` or Word re-flows on open
- **Tracked changes**: python-docx has no native API — build `w:ins`/`w:del` OOXML directly; every element needs a unique `w:id`; see `references/tracked-changes-recipe.md` for full helpers
- **Editing existing docs**: inspect structure first (`len(d.paragraphs)`, dump styles), back up original, chain build scripts per section, verify heading list after each pass
- **TOC pitfall**: when locating headings by text, always filter on BOTH text AND style — TOC entries share exact heading text and `insert_paragraph_before()` silently matches the wrong one

---

## PDF (ReportLab)

Full recipe + code: `references/pdf-reportlab-recipe.md`

- **Color objects required**: use `HexColor('#1a1a2e')` — bare hex strings like `textColor='#1a1a2e'` raise AttributeError at render time
- **Platypus flowables**: never calculate Y-positions manually; wrap heading + first paragraph in `KeepTogether` to prevent orphaned headings
- **Custom fonts**: register with `pdfmetrics.registerFont(TTFont(...))` before use or ReportLab silently substitutes (metrics wrong → overflow without error)
- **Headers/footers**: use `onFirstPage` / `onLaterPages` callbacks; `CONTENT_WIDTH = PAGE_W - 2 * MARGIN` for table `colWidths`

---

## Brand Colour Verification — Don't Trust Aggregator Sites

Third-party "brand color" sites (brandcolorcode.com and similar) are frequently wrong
or stale — they scrape old marketing collateral, not the live brand system. If a task
requires an exact brand hex (client decks, pharma/regulated-industry work, any deliverable
where color accuracy is checked), verify against the live site's own CSS instead of
trusting an aggregator or your own memory of "roughly navy-ish":

```bash
curl -s https://www.example-brand.com/ -A "Mozilla/5.0" -o /tmp/site.html
# Find the theme CSS bundle(s) linked in the page
grep -oE 'href="[^"]*\.css[^"]*"' /tmp/site.html
# Fetch each CSS bundle, then look for hex colors tied to semantically
# meaningful class names — .primary, .brand, .accent, .btn-primary are far
# more reliable signals than "most frequent hex in the file"
curl -s "https://www.example-brand.com/<css-path>" -A "Mozilla/5.0" >> /tmp/site_all.css
grep -oE '#[0-9a-fA-F]{6}' /tmp/site_all.css | sort | uniq -c | sort -rn | head -20
grep -B2 -A2 '#YOURHEX' /tmp/site_all.css   # confirm it's bound to .primary/.brand, not incidental
```

A hex that appears repeatedly AND is bound to a class like `.primary`/`.blue-dark`/
`.brand-color` is far stronger evidence than raw frequency alone or a third-party
aggregator's guess. Record the verified value with its source (site + CSS class) in
the relevant `references/<brand>.md` file so future sessions don't have to re-derive
it — and if an existing reference file admits "best-effort approximation, official
brand book not consulted," treat that as a standing invitation to re-verify and correct
it the next time that brand comes up.

## Audience-Calibrated Density: Specialist vs Generalist Decks

The correct slide density and background depend on who is actually reading the deck,
not just the format. A dense/dark "scientific poster" style deck built for a specialist
audience will get bounced back for a generalist audience (e.g. Medical Affairs, exec
summary, cross-functional review) — the ask is usually "same facts, radically less text,
plain-language jargon, white/light background instead of dark theme."

When a stakeholder asks you to simplify a technical deck for a non-specialist audience,
apply all of these together, not just font/color tweaks:

1. **Switch background** from dark/navy-canvas to white/light — dark scientific-poster
   themes read as dense and technical even when the text is short; white reads as an
   executive/briefing document.
2. **Cut body text hard.** Halve or better the word count vs a specialist version.
   Translate mechanistic jargon into plain language in the visible text (keep the full
   technical detail in speaker notes, not on the slide) — e.g. "recycling checkpoint"
   on-slide, "Rab11 recycling endosome" in notes.
3. **Add an explicit "key takeaway" line to every slide.** A generalist reader should be
   able to get the point from the takeaway alone without parsing the supporting chart/
   bullets. Style it as a distinct, consistently-placed strip (accent-colored bar +
   label + one sentence) so it reads as a deliberate structural element, not a stray bullet.
4. **Enforce the cut with an automated check, not a promise to "try to be brief."**
   Extend the validator to sum word counts of all non-structural text per slide and warn
   above a budget (e.g. 130 words excluding header/footer/takeaway chrome):
   ```python
   def _word_count(text):
       return len(text.split())

   # inside your per-shape validation loop:
   if has_text and not is_structural:
       slide_word_total += _word_count(shp.text_frame.text)
   # after the loop, per slide:
   WORD_BUDGET = 130
   if slide_word_total > WORD_BUDGET:
       warnings.append(f"Slide {idx}: wordiness {slide_word_total} words exceeds budget")
   ```
   This catches slides that look fine individually but are still too text-heavy for the
   stated audience — treat wordiness warnings with the same seriousness as bounds/overlap
   warnings, not as noise to ignore.

## Citation / Reference Verification for Formal and Regulatory Documents

When a document cites external authorities — academic papers, statutes, case law,
regulatory standards, vendor benchmarks — verify every citation resolves and says
what you're about to claim it says BEFORE drafting, not after. This matters most for
legal/regulatory/compliance critiques, board papers, and any deliverable where a
wrong or fabricated citation is a credibility (or legal) risk, not just a typo.

Workflow that worked well:
1. Extract the list of claimed sources/citations from the source material first
   (e.g. arXiv IDs, case names, standard numbers like "APRA CPS 230" or "ASIC RG 78").
2. Batch-verify in parallel: one `web_search` per distinct source to find the
   canonical URL, then `web_extract` on the shortlist to confirm the abstract/holding/
   clause actually matches the claim being made. Do this as parallel tool calls in a
   single turn, not one-by-one serial round-trips — these are independent lookups.
3. Prefer primary sources over secondary summaries when available: arXiv abstract
   page over a blog recap; hcourt.gov.au judgment over a law-firm summary; apra.gov.au/
   asic.gov.au standard page over a consultancy's explainer. Secondary sources are fine
   as corroboration but the primary source is the citation of record.
4. If the source material itself admits a claim was later "refuted on verification"
   or similarly walked back, treat that as a load-bearing fact for the critique, not
   a footnote to skip — proposals that pre-emptively flag their own weak citations are
   telling you where the real risk is.
5. Only after every citation is confirmed to resolve and match, proceed to drafting.
   Retrofitting citations after the prose is written tends to produce mismatches
   between what was claimed and what the source actually says.
6. Use a **three-tier status**, not a binary verified/unverified, when reporting results
   to the reader: `Verified` (primary source confirmed, characterization matches),
   `Not independently re-verified` (a plausible, real-sounding citation — e.g. a specific
   statute section number or a named client alert — that you did not have time/access
   to individually confirm; say so rather than silently asserting it), and `Unverified`
   (searched for and could not locate/confirm at all). This distinction matters most for
   legal/regulatory critiques: silently treating "plausible" as "confirmed" is how
   fabricated-sounding-but-wrong pinpoint citations slip through. Put the verification
   table directly in the deliverable (not just in your own working notes) so the reader
   can see exactly which claims you stand behind.
7. When the deliverable includes your own newly-authored analytical content (a proposed
   architecture, a new recommendation, a novel framework) layered on top of a critique
   of someone else's document — not just verified facts about the source — run an
   explicit adversarial pass over your OWN new material before finalizing, checking it
   against the very risks the source document already raised. Two concrete failure
   modes to check for every time: (a) does your new proposal quietly reopen a risk the
   source document flagged and mitigated (e.g. a "let's federate/share more broadly"
   idea reopening a scoping/privilege boundary the source deliberately drew)?, and
   (b) does a new technical mechanism you're proposing (e.g. richer retrieval, deeper
   traversal) make an existing named risk (e.g. aggregation/mosaic disclosure) worse
   rather than better by construction? Resolve each hit in place with a concrete
   constraint (not a caveat sentence) and log it in an adversarial-self-review section
   so the reader can see what was checked and how it was fixed — this is distinct from
   verifying the source's citations; it's verifying your own added claims don't
   undermine the source's already-correct risk analysis.
8. When the critique itself assigns severity ratings (High/Medium/Low) to findings in a
   generated DOCX, use a small color-coded helper so severity is visually scannable, not
   just textual:
   ```python
   from docx.shared import RGBColor
   def add_sev(doc, text, sev):
       p = doc.add_paragraph()
       r = p.add_run(f"[{sev}] ")
       r.bold = True
       colors = {'High': RGBColor(0xC0,0x00,0x00),
                 'Medium': RGBColor(0xB8,0x86,0x00),
                 'Low': RGBColor(0x1a,0x7a,0x1a)}
       r.font.color.rgb = colors.get(sev, RGBColor(0,0,0))
       p.add_run(text)
       return p
   ```
   Keep the color mapping consistent across the whole document (red=High, amber=Medium,
   green=Low) — don't invent new severities or colors mid-document.
9. **Post-synthesis fabrication quarantine check.** When the deliverable synthesizes
   multiple upstream research files that themselves already identified specific
   fabricated/non-existent sources (a common pattern in multi-pass research chains —
   an earlier draft cited something, a later verification pass found it doesn't exist),
   the finished document needs an explicit "excluded as fabricated" section listing
   those names, AND a grep-verification pass confirming they appear ONLY inside that
   section — never reintroduced as live, seemingly-legitimate citations elsewhere in
   the document. This is a distinct check from step 2-5 above (verifying real citations
   resolve): it's a regression check that already-debunked sources didn't creep back in
   during synthesis. Run it with a single search across the finished document for each
   known-fabricated name/ID before declaring the document done:
   ```
   search_files(pattern="Name1|Name2|Fabricated Dataset Name|Standard:2026",
                path="path/to/synthesis.md")
   ```
   Every match should fall inside the "excluded as fabricated" section (or an explicit
   "sources requiring further verification" section, if you also maintain a distinct
   tier for real-but-unverified sources — see step 6's three-tier status). A match
   anywhere else means a fabricated source was reintroduced as if it were live
   evidence — treat that as a hard defect, not a stylistic note.

## Rendered Visual Verification — Structural Checks Are Not Enough

Structural validation (heading list matches source, word count in the same
ballpark, table cell counts correct) catches content-loss bugs but is BLIND to
a whole class of bugs that only show up when the document is actually
rendered and looked at. Two real examples from one session, both invisible to
`python-docx`-level structural checks and only caught by rendering to an image
and inspecting it:

- A numbered list rendered as "5. 6." instead of "1. 2." because Word's
  built-in `List Number` style shares ONE counter across the whole document —
  see the pitfall below. `python-docx` reports the paragraph text and style
  correctly; nothing about the object model flags the wrong displayed number.
- A declared custom font (e.g. a corporate brand font) wasn't installed
  locally, so LibreOffice/Word silently substituted a default serif font at
  render time. `python-docx` reports `run.font.name == "Source Sans Pro"`
  correctly — the substitution only happens in the rendering engine, so
  reading the object model back tells you nothing is wrong when something is.

**Always add a rendered-visual-inspection pass for any document where layout
or brand fidelity matters**, on top of (not instead of) structural checks:

```bash
# If a bare binary isn't found, check for a flatpak install before concluding
# LibreOffice is unavailable — it is commonly present as a flatpak even when
# `which libreoffice` / `which soffice` return nothing:
flatpak list 2>/dev/null | grep -i libre
# Convert docx/pptx to PDF for inspection (headless, no GUI needed):
flatpak run org.libreoffice.LibreOffice --headless --convert-to pdf your_file.docx
# Render specific pages to PNG for vision inspection:
pdftoppm -png -r 120 -f 1 -l 1 your_file.pdf page1
```

Then load 2-4 representative pages (cover/title page, a page with a numbered
or bulleted list, a page with the heaviest custom formatting) through the
vision tool and specifically ask about: font (serif vs the sans-serif you
intended), list numbering (does it restart where expected), color-coding
consistency, and header/footer bar rendering. Do this BEFORE declaring the
document done — a docx that "opens fine and has the right structure" can
still look visibly wrong to the recipient.

## Diagnostic Guide (post-failure iteration)

When a generated document has layout issues, identify the failure category first:

| Symptom | Likely cause | Fix |
|---|---|---|
| Text cut off / invisible | PPTX overflow (`noAutofit`), PDF clipping | Check `get_autofit_type()`; reduce font or split content |
| Shapes overlapping | Freehand placement with wrong EMU values | Run `check_overlaps()`; switch to layout placeholders |
| Columns misaligned | Word table auto-layout | Use `create_fixed_table()` with explicit widths |
| Font looks wrong / spacing off | Unregistered custom font in PDF | Register via `pdfmetrics.registerFont()` |
| Heading same size as body | Ad hoc bold/size instead of named style | Switch to `add_heading()` or named style |
| Inconsistent spacing between sections | Mixed ad hoc `space_after` values | Define spacing on named style, not per-paragraph |
| Right-edge content clipped | Safe zone violation | Run `check_safe_zone()`; move shapes inward |
| Different look on projector | Low contrast, small fonts | Check all fonts ≥ 18pt body, contrast ratio ≥ 4.5:1 |

---

## Pre-Delivery Checklist

### Layout / Structural
- [ ] No text overflows shape bounds — run `get_autofit_type(shape)` (defined in
  pptx-recipe.md Text Overflow Prevention section) for freehand shapes; result should not be `'noAutofit'`
- [ ] No shape overlaps — `check_overlaps()` returns empty list
- [ ] All elements within safe zone — `check_safe_zone()` returns empty list
- [ ] Consistent margins across all slides/pages (not per-slide overrides)
- [ ] Rendered a PDF/image preview (see "Rendered Visual Verification" above)
  and visually confirmed font, list numbering, and color-coding — do not rely
  on structural checks (heading list, word count) alone

### Typography
- [ ] Maximum 2 font families in use
- [ ] H1 > H2 > Body > Caption in size (no inversions)
- [ ] Body font ≥ 10pt (print) / ≥ 18pt (slide)
- [ ] Title font ≥ 24pt (slide), ≥ 14pt (print H1)
- [ ] Consistent alignment within each semantic level
- [ ] No color used purely for decoration (color should encode meaning)
- [ ] Custom fonts registered (PDF via `pdfmetrics.registerFont()`). For PPTX:
  python-pptx does not provide a font-embedding API. Font embedding in PPTX requires
  either (a) using a template `.pptx` that already has the fonts embedded, or (b)
  post-processing the `.pptx` zip to add font files to the `ppt/fonts/` directory
  and update the content-types manifest. If font embedding is required, use a
  pre-embedded template and do not generate from a blank `Presentation()`.

### Density (PPTX)
- [ ] Title ≤ 6 words (or justified exception for data/reference slides)
- [ ] ≤ 30 words body text (soft ceiling; data slides may exceed — review manually)
- [ ] ≤ 6 bullet points per slide
- [ ] Only one visual structure (table OR chart OR grid) per slide

### Consistency
- [ ] Single table style applied everywhere
- [ ] Colors from defined 3-color palette only
- [ ] Paragraph spacing derived from a defined scale (not random values)
- [ ] Headers/footers present on every page (DOCX multi-section; PDF via callback)

---

## Quick Reference: Recommended Defaults

| Setting | PDF (A4) | DOCX | PPTX (16:9 widescreen) |
|---|---|---|---|
| Page / slide size | 210×297 mm | 8.5×11 in (letter) or A4 | 10×7.5 in |
| Margins | 1.5–2 cm | 1–1.25 in all | 0.5 in safe zone |
| Body font | 11pt | 11–12pt | 18–20pt |
| Line height (leading) | 1.4–1.5× | 1.15–1.5× | 1.2× |
| H1 size | 18pt | 16pt | 36–40pt |
| H2 size | 14pt | 13pt | 28–32pt |
| Caption size | 8pt | 9pt | 14pt |
| Max body text/unit | N/A (flowable) | N/A (flowable) | ~30 words (soft) |
| Color palette | 3 colors | 3 colors | 3 colors |

---

## Sources
- Oria.one / TechGrid (2026): production AI-slide engineering constraints and failure taxonomy
- Ivern AI (2026): 12 best practices for professional AI slides
- Microsoft DocReward (2025): specialized document quality evaluation — cited for the general finding that specialized evaluators outperform LLMs on structure/style judgment
- python-pptx documentation: placeholders, EMU units, autofit XML, nvPicPr structure
- python-docx documentation: styles, paragraph formatting, table layout, WD_ORIENT enum
- ReportLab Platypus documentation: flowables, PageTemplates, color API, KeepTogether

## References
- `references/pptx-recipe.md` — full python-pptx recipe: layout placeholders, EMU grid,
  text overflow helpers (`estimate_font_size`, `get_autofit_type`, `check_overflow_risk`),
  dark-theme patterns, post-generation validator with chrome exemptions, image alt-text.
- `references/docx-recipe.md` — full python-docx recipe: margins, named styles, fixed
  table layout, multi-section headers/footers, markdown-to-docx conversion, tracked changes
  OOXML helpers (w:ins/w:del), gap-analysis integration editorial standard, chunked-edit
  pattern for large existing docs, and three pitfall sections (TOC text-match, cross-ref
  renumbering, semantically-wrong cross-refs).
- `references/pdf-reportlab-recipe.md` — full ReportLab recipe: page template, style
  sheets (HexColor requirement), custom font registration, Platypus flowable composition
  with KeepTogether, running headers/footers via callbacks, image handling patterns.
- `references/tracked-changes-recipe.md` — full OOXML tracked-changes recipe for python-docx:
  w:ins/w:del helpers, paragraph-level insertion marking, anchor-triggered annotation dispatch
  with deduplication, table-row anchor scanning. Used for NAB LIP gap-analysis update (2026-07-08).
- `references/api-pitfalls.md` — compact catalogue of silent failures and wrong API calls
  for python-pptx, python-docx, and ReportLab; surfaced across 6 adversarial review passes.
  Load this when debugging unexpected rendering, crash-at-runtime errors, or Word/PowerPoint
  "looks fine in code, broken on open" failures. Includes the List Number shared-counter bug
  and the rFonts ascii/hAnsi/cs font-substitution bug.
- `references/dark-theme-pptx-pattern.md` — full working scaffold for dark-background
  PowerPoint decks with manually drawn bar charts and status grids. Load when building
  a presentation from scratch on a dark theme or when `add_chart()` results look broken.
- `references/ucb-pharma-branding.md` — validated UCB pharma colour palette, wordmark
  layout, footer pattern, and drug-to-colour mapping. Load for any UCB Medical Affairs
  presentation work.
- `scripts/md_to_docx.py` — reusable markdown-to-docx converter (headers, bold/code
  spans, bullet/numbered lists) for when pandoc isn't installed. Run with `--src` and
  `--out` paths.
## Brand Colour Verification Methodology (Python)

**Source hierarchy** (highest to lowest authority): Live website CSS → Official PDFs → Brand portal → Third-party databases (Brandfetch, logotyp.us, triangulate only) → Image/Word template artifacts (NEVER authoritative).

**Step 1 — Extract live CSS colors:**
```python
import requests, re
from collections import Counter
resp = requests.get("https://www.brand.com/etc/clientlibs/main.css", timeout=15)
hexes = re.findall(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', resp.text)
counts = Counter('#' + h.upper() for h in hexes)
for color, n in counts.most_common(20): print(f"{color}: {n} uses")
```

**Step 2 — Extract official PDF colors** (`pip install pymupdf`):
```python
import fitz
from collections import Counter
def extract_pdf_colors(path):
    doc = fitz.open(path)
    colors = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    c = span.get("color", 0)
                    r,g,b = (c>>16)&0xFF, (c>>8)&0xFF, c&0xFF
                    if (r,g,b) != (0,0,0): colors.append(f"#{r:02X}{g:02X}{b:02X}")
    return Counter(colors)
```

**Step 3 — Reconcile:** Convergence signal: if CSS and PDF agree within ±5% luminance on the same hue → brand primary. Deprecation signal: color in images/templates but NOT in live CSS or official PDFs → mark deprecated, don't add to palette.

**Real examples (verified 2026-07-03):** NAB web=`#C20000`, docs=`#ED0000` (both official). UCB primary=`#001489` (87.4% CSS/PDF convergence).

**Pitfalls:** CSS minification may split files — check multiple CSS URLs. PDF CMYK is auto-converted to RGB by fitz. Brands use different reds for web vs print — report both labeled by medium.

See `references/brand-verification-methodology.md` for full code, semantic class extraction, and font extraction.

## Reference files

- `references/nab-branding.md` — NAB (National Australia Bank) Brand Palette — Verified
