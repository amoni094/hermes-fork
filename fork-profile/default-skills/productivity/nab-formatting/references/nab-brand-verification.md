# NAB Brand Verification — Evidence Trail (2026-07)

Verified NAB's real brand colors and fonts by extracting embedded data directly from
official documents, because third-party brand-color sites disagreed and were wrong.

## Verified findings

### Colors (RGB operators extracted from official PDFs + live CSS)
| Color | Hex | Source |
|---|---|---|
| Primary red (print/docs) | `#ED0000` (rgb 0.929,0,0) | Group Securities Trading Policy PDF + 2023 Annual Report PDF — dominant red in every official PDF |
| Primary red (web/UI) | `#C20000` | nab.com.au components CSS, **69 occurrences** |
| Dark/hover red | `#8F0000` (web) / `#D41F11` (docs) | live CSS (14 uses) / policy+report PDFs |
| Bright accent red | `#ED1C29` | 2023 Annual Report |
| Body text | `#000000` (pure black) | all PDFs, dominant text color |
| Callout/table shade | `#C4D6EE` (light blue) | Securities Trading Policy shaded cells |

### Fonts (from embedded /BaseFont tables)
- **2023 Annual Report (modern brand):** Epilogue (Light/Regular/Medium/SemiBold/Italic)
  = display/heading; Source Sans Pro (Regular/SemiBold/Bold) = body; Helvetica Neue LT Pro.
- **Group Securities Trading Policy:** Arial / Arial-Bold (body) + Source Sans Pro +
  CorpidC1-Bold + Epilogue.
- **Board Charter:** Arial / Arial-Bold (primary) + Times New Roman + Calibri/Calibri-Light.
- **Avenir: never found in any official document.**

### Layout observations
- Headings are BLACK/near-black, light weight — NOT red. Red = logo, hyperlinks, UI accents.
- Web page footer band is black with white text + the ABN/AFSL/ACL line:
  "© National Australia Bank Limited ABN 12 004 044 937 AFSL and Australian Credit Licence 230686".
- No confidentiality/classification markings appear in the public documents examined.

### DEBUNKED third-party values (do NOT use)
`#DE1F26`, `#A91F23`, `#231F20` — from logotyp.us / pickcoloronline. These are
logo-render artifacts and do not appear in NAB's actual documents or website.

## Official document URLs used
- 2023 Annual Report: `https://www.nab.com.au/content/dam/nab/documents/reports/corporate/2023-annual-report.pdf`
- Group Securities Trading Policy: `https://www.nab.com.au/content/dam/nabrwd/documents/policy/corporate/group-securities-trading-policy.pdf`
- Board Charter: `https://www.nab.com.au/content/dam/nabrwd/documents/reports/corporate/board-charter.pdf`
- Live CSS: `https://www.nab.com.au/etc.clientlibs/nab/clientlibs/clientlib-generated-components.*.css`

## TECHNIQUE: extract fonts + colors from a PDF with Python stdlib only

When poppler (`pdffonts`/`pdftotext`), `pymupdf`/`fitz`, `mutool`, and `gs` are all
unavailable (or blocked), you can still read fonts, colors, and even embedded raster
images from most PDFs using only the Python standard library (`zlib`, `re`, `struct`).
No pip install required. See `scripts/pdf_stdlib_probe.py` in this skill.

Core idea:
- PDF content lives in `stream ... endstream` blocks, usually `/FlateDecode` compressed
  → `zlib.decompress` each block (wrap in try/except; skip ones that aren't flate).
- Fonts: regex `/BaseFont /XXXXXX+FontName` inside the *decompressed* streams (font
  defs are often inside compressed object streams / ObjStm, so decompress first).
- Colors: regex `([0-9.]+) ([0-9.]+) ([0-9.]+) (rg|RG)` = device-RGB fill/stroke ops;
  multiply each 0–1 float by 255 for hex. Filter `r>g and r>b` to find reds.
- Embedded image: find `/Width N` in the raw bytes, locate the following `stream`,
  decompress → raw pixel buffer (RGB = W*H*3 bytes). Can be written to a minimal PNG
  by hand (zlib + IHDR/IDAT/IEND chunks) with no imaging library, then read with vision.

Pitfall: after `stream` the data starts after a CR/LF or LF — skip the right number of
bytes before decompressing, or zlib will error on the first byte.
