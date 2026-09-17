# NAB (National Australia Bank) Brand Palette — Verified

Source: live CSS pulled from nab.com.au's own AEM clientlibs bundle
(`clientlib-base`, `clientlib-generated-components`), 2026-07-07. Verified by
matching hex values to semantically bound utility classes (`.bg-nab-red`,
`.bg-nab-emerald`, etc.), not by raw frequency count or a third-party
aggregator site. Re-verify if this file is more than ~12 months old before
using for a client-facing/regulated deliverable — brand systems do get
refreshed.

## Core palette

| Name | Hex | Class binding | Use |
|---|---|---|---|
| NAB Red (primary) | `#C20000` | `.bg-nab-red` | Primary brand accent, CTAs, H2/emphasis |
| NAB Red hover | `#8F0000` | `.bg-nab-red-hover` | Hover/darker accent states |
| NAB Red selected | `#750000` | `.bg-nab-red-selected` | Pressed/selected states |
| NAB Slate (secondary) | `#3A4F59` | `.bg-nab-slate` | Headings, dark UI chrome, H1 |
| NAB Slate hover | `#26343A` | `.bg-nab-slate-hover` | — |
| NAB Slate selected | `#1C262B` | `.bg-nab-slate-selected` | — |
| NAB Emerald | `#2C853C` | `.bg-nab-emerald` | Positive/success accents |
| NAB Emerald hover | `#1F5F2B` | `.bg-nab-emerald-hover` | — |
| NAB Amber | `#E9600E` | `.bg-nab-amber` | Warning/medium-severity accent |
| NAB Sapphire | `#1E5AA3` | `.bg-nab-sapphire` | Tertiary/info accent |

## Greyscale

| Name | Hex | Class |
|---|---|---|
| Grey 90 | `#E6E6E6` | `.bg-nab-grey90` |
| Grey 70 | `#B3B3B3` | `.bg-nab-grey70` |
| Grey 50 | `gray` (browser default ~`#808080`) | `.bg-nab-grey50` |
| Grey 30 | `#4D4D4D` | `.bg-nab-grey30` |
| Grey 10 | `#1A1A1A` | `.bg-nab-grey10` |
| Background | `#F5F5F5` | `.bg-nab-background` |

## Typography

Body/UI font stack (from CSS): `source-sans-pro, helvetica, -apple-system,
blinkmacsystemfont, "Segoe UI", roboto, oxygen-sans, ubuntu, cantarell,
"Helvetica Neue", sans-serif`. There's also a custom display face,
`@font-face` `"NAB Impact"` (weight 700, woff2/woff/ttf), used for hero/large
display headlines — not needed for standard report/document work, but note
its existence if asked to match marketing-grade hero typography.

For DOCX/PPTX/PDF generation where Source Sans Pro isn't installed locally,
declare the font by name anyway (`"Source Sans Pro"`) — Word/PowerPoint on a
machine with the corporate font installed will render correctly, and falls
back gracefully via the OS font-substitution table otherwise. Don't silently
swap to Calibri/Arial without noting the substitution if brand fidelity matters.

## Suggested mapping for internal report/critique documents

Consistent with the "3 colors: primary 60%, accent 30%, neutral 10%" rule in
this skill's Universal Rules section:

- Primary (60%): body text in Grey 10 (`#1A1A1A`) on white/Grey-background pages
- Accent (30%): NAB Slate (`#3A4F59`) for H1 headings, cover title, running
  header/footer chrome
- Accent (10%): NAB Red (`#C20000`) for H2 headings, the cover-page accent
  bar, and any single-line emphasis/callout — don't use Red for body text,
  it's too strong at that density
- Severity/status color-coding (if the document has High/Medium/Low findings):
  Red = High, Amber (`#E9600E`) = Medium, Emerald (`#2C853C`) = Low — this
  maps directly onto NAB's own palette, no need to invent a separate
  red/amber/green scheme

## Wordmark / logo

Do not reproduce NAB's actual logo/wordmark image asset without an
authorized source file — it's a registered trademark. For internal working
documents (not going to print/external distribution), a text-based brand
treatment is standard and safe: a small colored chip/box in NAB Red with
white bold "nab" text (lowercase, matches their actual visual convention),
used only as a document-header brand cue — not a reproduction of the
vector logo itself. If a deliverable is going external or to print, ask the
user for the official logo asset/brand guideline PDF rather than
approximating it.

## Re-verification command (for future refresh)

```bash
curl -s https://www.nab.com.au/ -A "Mozilla/5.0" -o /tmp/nab_site.html
grep -oE 'href="[^"]*\.css[^"]*"' /tmp/nab_site.html
# fetch clientlib-base + clientlib-generated-components bundles, then:
grep -oE '\.bg-nab-[a-z-]+\{background-color:#[0-9a-fA-F]{6}\}' /tmp/nab_all.css
```
