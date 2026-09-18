---
name: nab-formatting
description: >
  Use when applying NAB (National Australia Bank) brand formatting to Word docs, PDFs, PowerPoints, and other documents — correct colors, fonts, header/footer, table styles, heading hierarchy, and classification markings.
version: 1.1.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [nab, formatting, word, powerpoint, pdf, branding, documents]
triggers:
  - Task involves applying NAB (National Australia Bank) brand formatting to Word, PowerPoint, or PDF
  - User says "apply NAB style", "format for NAB", or "use NAB branding"
related_skills:
  - docx
  - pdf
---

# NAB Formatting

Apply NAB (National Australia Bank) brand guidelines to any document — Word (.docx), PowerPoint (.pptx), PDF, or plain markdown/text output.

## Triggers

- "format this in NAB style"
- "apply NAB branding/formatting"
- "make this look like an NAB document"
- "use NAB formatting for this [Word/PDF/PowerPoint]"
- "reformat with NAB brand guidelines"

## NAB Brand Identity (VERIFIED against official nab.com.au documents)

> Colors and fonts below were verified 2026-07 by extracting embedded fonts and
> RGB color operators directly from four official NAB PDFs (2023 Annual Report,
> Group Securities Trading Policy, Board Charter, style-guide page render) plus
> the live nab.com.au CSS. See `references/nab-brand-verification.md` for the full
> evidence trail and the extraction method. TRUST THESE over any third-party
> brand-color site (logotyp.us, brandfetch, pickcoloronline) — those report
> logo-*render* artifacts that do NOT match NAB's actual documents.

### Colors

- NAB Red (PRIMARY, print/docs): #ED0000  (rgb 0.929,0,0) — the dominant red across
  every official NAB PDF. Use this for docs/reports.
- NAB Red (web/UI):              #C20000  — primary red in live nab.com.au CSS
  (69 uses). Use this when matching the website.
- NAB Dark Red (hover/accent):   #8F0000  (web) / #D41F11 (docs) — deeper red for
  borders, hover states, dividers.
- NAB Bright Accent Red:         #ED1C29  — occasional accent in annual reports.
- NAB Body Text:                 #000000  (PURE BLACK) — official docs use pure black
  body copy, NOT #231F20.
- NAB Callout/Table Blue:        #C4D6EE  — light blue used for shaded cells / callout
  boxes in policy documents (NOT red — see Tables note below).
- NAB White:                     #FFFFFF
- NAB Light Grey:                #F5F5F5  (subtle fills; header bands render light grey)

> DEPRECATED third-party values — do NOT use as brand truth:
> #DE1F26, #A91F23 (never found in any official document/CSS);
> #231F20 (a logo-render near-black from 3rd-party sites, not used as body color).

### Typography

Fonts confirmed from embedded font tables in official NAB PDFs:

- Formal policy / charter documents: **Arial** (Regular + Bold) is the primary body
  font, with Times New Roman / Calibri as fallbacks. Use Arial for policies, charters,
  letters, correspondence.
- Modern brand + annual reports: **Epilogue** (Light / Regular / Medium / SemiBold /
  Italic) is the display/heading font; **Source Sans Pro** (Regular / SemiBold / Bold)
  is the secondary/body font; Helvetica Neue LT Pro also present. Use Epilogue +
  Source Sans Pro when matching contemporary NAB brand / report styling.
- **Avenir was NOT found in any official document** — do not claim it as a NAB font.
  If a "brand" font is needed and Epilogue isn't available, use Source Sans Pro
  (open-source, freely installable) or Arial.
- Font sizes:
  - Body text:          11–12pt
  - Section headings:   near-BLACK (#000000), light/regular weight — headings in NAB
    docs are BLACK, not red. Red is reserved for the logo, hyperlinks, and UI accents.
  - Sub-headings:       bold, near-black
  - Table header text:  bold, dark text on light fill (see Tables)
  - Caption/footer:     9–10pt

### Spacing and Layout

- Single space after all punctuation (periods, colons, question marks)
- No paragraph indentation — use blank line between paragraphs instead
- Margins: standard 2.54 cm (1 inch) all sides for letters/reports
- No ALL CAPS in body copy
- Left-align body text (not justified)
- Consistent, minimal line spacing: 1.15 or single for dense docs, 1.5 for readable reports

### Header / Footer (document pages)

- Top-left: NAB star logo (red star + "nab" wordmark)
- Header text (right of logo): "[NAB Confidential — Internal] | [Document Title]"
- Horizontal red divider line below header (#DE1F26, 1pt)
- Footer: page number (right-aligned), optional date (left-aligned)

### Classification Marking

Standard NAB classification labels used in header:
- NAB Confidential — Internal
- NAB Confidential — External (for partner/client delivery)
- NAB Public
Always follow with: | [Document / Project Title]

### Tables

> OBSERVED in official NAB policy PDFs: shaded cells use **light blue #C4D6EE**, not a
> red header row. The red-header style below is an acceptable branded *design choice*
> for docs you generate, but it is NOT how NAB's own policy documents style tables — if
> the goal is to match real NAB documents, prefer light-blue (#C4D6EE) shaded headers
> with black text.

- Header row (branded option): NAB Red background (#ED0000 print / #C20000 web), white bold text
- Alternating data rows: white (#FFFFFF) and light grey (#F5F5F5)
- Body cell text: NAB Near-Black (#231F20), 11pt Arial, left-aligned
- Borders: thin (0.5pt), NAB Dark Red (#A91F23) or light grey
- First column (use-case/label column): bold, slightly wider
- No merged cells unless essential — use row grouping instead

### Headings Hierarchy

1. Document Title — 18–20pt, NAB Red, bold (cover/title page only)
2. Section / H1 — 14pt, NAB Red (#DE1F26), bold (e.g. "Executive summary")
3. Sub-section / H2 — 12pt, NAB Near-Black, bold
4. Body label / H3 — 11pt, NAB Near-Black, bold italic or bold
5. Body text — 11–12pt, NAB Near-Black, regular

### Key Tone and Content Rules (from NAB style guide)

- Do not use ALL CAPS in correspondence
- Use an ampersand (&) ONLY when part of a formal company name — never as a substitute for "and"
- Use one space after all punctuation
- Spell-check every document before delivery
- Proofread thoroughly before any distribution
- For letters: do not indent paragraphs, leave one blank line between paragraphs

---

## Workflow by Document Type

### Word (.docx) — python-docx

1. Load the skill: `skill_view(name='nab-formatting')`
2. Install if needed: `pip install python-docx`
3. Apply:
   - Set default font to Arial 11pt throughout
   - Apply Heading 1 style: Arial 14pt, bold, color #DE1F26
   - Apply Heading 2 style: Arial 12pt, bold, color #231F20
   - Add NAB header: logo placeholder + classification text + red divider paragraph border
   - Format all tables: header row fill #DE1F26, white text; alternating rows #F5F5F5
   - Set paragraph spacing: space-before 0pt, space-after 6pt, no first-line indent
   - Check for ALL CAPS runs and normalize
   - Save as [filename]-NAB.docx

Sample snippet (python-docx):
```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

NAB_RED   = RGBColor(0xED, 0x00, 0x00)  # verified print/docs red (#ED0000); use 0xC2,0,0 for web
NAB_BLACK = RGBColor(0x00, 0x00, 0x00)  # official docs use pure black body text
NAB_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
NAB_GREY  = RGBColor(0xF5, 0xF5, 0xF5)

doc = Document("input.docx")

# Apply heading style
for para in doc.paragraphs:
    if para.style.name.startswith("Heading 1"):
        for run in para.runs:
            run.font.color.rgb = NAB_RED
            run.font.size = Pt(14)
            run.bold = True
    else:
        for run in para.runs:
            run.font.name = "Arial"
            run.font.size = Pt(11)
            run.font.color.rgb = NAB_BLACK

# Format tables
for table in doc.tables:
    for i, row in enumerate(table.rows):
        for cell in row.cells:
            if i == 0:
                cell._tc.get_or_add_tcPr()  # header row: red bg
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.color.rgb = NAB_WHITE
                        run.bold = True

doc.save("output-NAB.docx")
```

### PowerPoint (.pptx) — python-pptx

1. Install if needed: `pip install python-pptx`
2. Apply:
   - Set slide master font to Arial
   - Title placeholder: Arial 28–32pt, bold, NAB Red
   - Content placeholders: Arial 18–20pt, NAB Near-Black
   - Slide background: white (#FFFFFF) for standard slides
   - Accent shapes/dividers: NAB Red fills or outlines
   - Table headers: NAB Red fill, white bold text
   - Footer: NAB classification label + slide number

### PDF

- **Verify NAB colors/fonts from a source PDF** when tooling is missing: run
  `scripts/pdf_stdlib_probe.py FILE.pdf` (stdlib-only — works even when poppler/pymupdf/
  mutool/gs are absent or blocked). Add `--image` to dump the first embedded RGB image to
  PNG for vision inspection. Method + evidence in `references/nab-brand-verification.md`.
- If source is Word/PPT: apply NAB formatting first, then export to PDF via LibreOffice:
  `libreoffice --headless --convert-to pdf output-NAB.docx`
- If editing an existing PDF: use the `pdf` skill (nano-pdf is disabled) or marker-pdf for text extraction then re-render
- For new PDFs: generate via reportlab or weasyprint with NAB color/font constants

### Markdown / Plain Text Output

When producing NAB-formatted text output (e.g. for copy-paste into docs):
- Use `## Executive Summary` style headings (map H1 → Section in NAB Red when rendered)
- State classification at top: `NAB Confidential — Internal | [Title]`
- Tables: use markdown table syntax; specify NAB Red header row when converting
- No ALL CAPS words
- One blank line between paragraphs, no leading spaces/indent

---

## Pitfalls

- Arial may not be installed on Linux — check with `fc-list | grep -i arial`. Fallback: Liberation Sans (metrically identical). Install Arial via: `sudo dnf install mscore-fonts-all` (or copy from a Windows machine into ~/.fonts/).
- python-docx cannot set table cell background directly via high-level API — use the `_tc` XML element with `OxmlElement` for fill color.
- NAB primary Red is #ED0000 (print/docs) or #C20000 (web), NOT pure #FF0000 and NOT
  the third-party #DE1F26. Always use the verified hex for the target medium.
- Do NOT trust third-party brand-color sites (logotyp.us, brandfetch, pickcoloronline)
  for NAB — they report logo-render artifacts (#DE1F26, #A91F23, #231F20) that do not
  match NAB's actual documents or website. Verify from official PDFs/CSS instead
  (see `references/nab-brand-verification.md`).
- PowerPoint slide masters control default fonts — change the master, not just individual slides.
- Avenir is a paid font (Linotype) — only use it if licensed. Arial is always safe.
- Do NOT use ALL CAPS for headings even though some heading styles might default to it — override explicitly.
- Classification marking is required on every page header for Confidential documents.

## Verification

After applying NAB formatting to any document, check:
- [ ] Heading 1 / title text is NAB Red (#ED0000 docs / #C20000 web), bold, Arial or Source Sans Pro 14pt+ (Word) or 28pt+ (PPT)
- [ ] Body text is Arial or Source Sans Pro 11–12pt, pure black (#000000)
- [ ] Table header rows: light blue #C4D6EE fill with black bold text (policy/charter style) OR red #ED0000 fill with white bold text (branded report style)
- [ ] Header includes NAB classification label and red divider line
- [ ] No ALL CAPS in body copy
- [ ] One space after punctuation throughout
- [ ] Spell-check has been run
- [ ] File saved as [name]-NAB.[ext] to preserve original
- [ ] Colors verified against official source: #ED0000 (print/docs), #C20000 (web) — NOT #DE1F26 or #FF0000
