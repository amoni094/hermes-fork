---
name: context-safe-pdf-edits
description: >
  Use when: Edit large Python PDF-generation scripts (e.g. ReportLab build scripts) without triggering context blowouts or silent stalls. Use this whenever patching a script that is >500 lines or contains multi-hundred-line string blocks.
triggers:
  - editing large PDF build scripts
  - patching reportlab/weasyprint generation scripts
  - session stalled mid-rewrite of a code file
related_skills:
  - pdf
  - document-layout-design
---

## ReportLab UI helper pitfalls (learned in NAB wireframe session)

### 1. Never pass unsupported kwargs to helper functions
ReportLab helper wrappers (checkbox, field, dropdown etc.) have narrow signatures.
Passing `max_width=` or other unsupported kwargs causes a silent Pyright error that
becomes a runtime TypeError. Always check the function signature with:

    grep -n 'def checkbox\|def field\|def dropdown' script.py

If you need wrapping label text on a checkbox, DON'T add max_width — instead draw
the box/tick manually and call `wrap()` for the label:

    rect(x, y, 11, 11, fill=WHITE, stroke=BORDER, lw=1, radius=2)
    if checked:
        set_stroke(RED); c.setLineWidth(1.5)
        c.line(x+2, y+5, x+4.5, y+2.5); c.line(x+4.5, y+2.5, x+9, y+9)
    wrap(x+17, y+2, label, size=8, w=col_width-20, color=CHARCOAL)

### 2. Cluttered page: split stacked panels into separate pages
If a page has two stacked browser/panel screenshots, the result is always cluttered:
small text, clipped boxes, overlapping annotations. The fix is to give each panel
its own full page. Pattern:

- Name them 1.1a / 1.1b (or Step 1-2 / Step 3) so numbering stays coherent
- Use `PW - 2*M` full width for each browser frame
- Use `PH - 148` for browser height (leaves room for page header + footer strip)
- Inner usable width = `_bw - 40` (20px padding each side)

### 3. Explanatory text that overlaps a browser screenshot
Move it to the intro/section-title page that precedes the wireframe page. That page
has whitespace below the bullet list. Render it as a proper table (dark header row,
alternating row fills) rather than as floating text. Remove the heading from the
wireframe page entirely — the title page is the right home for "how it works".

### 5. Inlining a `section_title()` helper call to control page content
`section_title()` ends by calling `c.showPage()` internally. You cannot append
content after calling it — it has already closed the page. When you need to add a
key-recs block, matrix table, or any extra content to the section title page:

**Replace the `section_title(N, ...)` call with inline drawing code:**

```python
set_fill(WHITE); c.rect(0, 0, PW, PH, fill=1, stroke=0)
set_fill(RED); c.rect(0, 0, 150, PH, fill=1, stroke=0)
ctext(75, PH/2 + 20, "N", size=140, font="Helvetica-Bold", color=WHITE)
ctext(75, PH/2 - 40, "INITIATIVE", size=12, font="Helvetica-Bold", color=WHITE)
logo(200, PH - 60, scale=1.0)
text(200, PH/2 + 60, "Section Title", size=30, font="Helvetica-Bold", color=CHARCOAL)
# ... subtitle, bullets ...
# NOW add your extra content:
key_recs(200, yy - 4, PW - 200 - M, "Key Recommendations — X", [...])
page_footer("")
c.showPage()  # you own the showPage() now
```

This is the correct pattern whenever you need to append content to a section
title page. Do NOT try to call `section_title()` and then draw more — it won't work.

### 6. Key recommendations belong on section title pages, not wireframe pages
Wireframe pages are dense (browser frames, form fields, audit trails). Key recs
blocks placed there will spill over or cover other content. Pattern:

- Move key recs to the section title page for that section (see pitfall 5 above).
- If the section title already uses the `section_title()` helper, inline it (pitfall 5).
- Remove the `key_recs(...)` call from the wireframe page entirely.
- Add a comment on the wireframe page: `# key recs moved to section N title page`

### 7. Checking page structure before editing
Before touching any page, get a page map first:

    grep -n 'c\.showPage\|section_title\|page_header\|page_footer' script.py

Then read the target section in bounded chunks via `read_file(offset=N, limit=60)`.
Never patch blindly — confirm line numbers match what you expect.

### 8. Name replacement: check ALL occurrences across chat + audit trail separately
When replacing a person's name (e.g. S. Hoare → L. Eyelander), they appear in
at least two distinct data structures in the same file:
- The `msgs = [...]` list (chat panel)
- The `events = [...]` list (audit trail)
- Possibly `qrows = [...]` (triage queue Assigned column)

grep first to find all occurrences before patching:

    grep -n 'Hoare\|Monin\|old_name' script.py

Patch each list separately — a single patch trying to cover all three is fragile
if the blocks are not adjacent.

### 9. Embedding real brand logos — use drawImage(), not text glyphs
Never fake a corporate logo with a unicode character (★, ●) + bold text. The result
is obviously wrong to any stakeholder. Instead:

1. Download the official PNG from brandfetch.com or the brand's website.
   companieslogo.com has both light and dark variants with transparent background.
2. Save alongside the script: `nab_logo.png` (light), `nab_logo_dark.png` (dark).
3. Replace the fake `logo()` function with a `drawImage()` call:

```python
def logo(x, y, scale=1.0, on_dark=False):
    _base_w = 110 * scale
    _base_h = _base_w * (img_h / img_w)   # real pixel aspect ratio from PIL
    _img = "logo_dark.png" if on_dark else "logo.png"
    c.drawImage(_img, x, y - _base_h + 4, width=_base_w, height=_base_h,
                mask="auto", preserveAspectRatio=True)
```

`y - _base_h + 4`: PDF y=0 is PAGE BOTTOM. `drawImage(x,y,...)` anchors at the
BOTTOM-LEFT corner, so subtract height to anchor at the top (matching text baseline
feel). `mask="auto"` handles RGBA transparency on any background color.

Keep the same call signature — all existing `logo(x, y, scale, on_dark)` calls
work unchanged. File size increases by ~100K per embedded PNG (normal, expected).

### 10. "Move down the page" in PDF means DECREASE y
ReportLab y=0 is the BOTTOM of the page. Direction is inverted vs screen coords:
- "Move box down 3 paragraphs" → subtract ~45pt from y
- "Lift the box up" → ADD to y
- "Design note below buttons" → design note y must be LESS THAN button y

Always grep the current y value, then verify direction visually after rebuild.

### 4. Pyright float→int warnings in ReportLab scripts
Pre-existing false positives throughout — floats appear in lw=, size=, x/y positions
throughout the codebase. Do NOT introduce int() casts everywhere; they break
percentage-based layout math. Treat these as noise unless a genuine runtime TypeError
appears.

---

## Root cause of context blowouts

Passing the old block + new block of a 100+ line string-replace as tool arguments
in a single call inflates the prompt by 2x the block size. If that block is >2K chars,
it can consume the remaining context window and the call silently fails (no change,
no error; the file timestamp stays the same).

## Preventative workflow

1. **Use `patch` tool with uniquely-anchored fragments, not `execute_code` string.replace**
   - The `patch` tool sends only the diff, not the full file, so it scales.
   - If old_string is not unique, add 1-2 surrounding lines for context.
   - If the block is large (>50 lines), break it into 2-3 overlapping patches at natural
     boundary lines (function defs, blank lines, comments).

2. **Verify before patching**: `terminal("grep -n 'anchor_phrase' file.py")` to confirm
   the anchor exists and is unique before issuing the patch.

3. **Never rebuild the full file content in execute_code** if the script is >20K chars.
   Use `patch` for targeted edits. Only use `write_file` for full rewrites of short files.

4. **After every patch, run the script** with `terminal("python3 script.py 2>&1")` to
   confirm the change was applied and the file executes cleanly. Check output file
   timestamps. A stalled session leaves timestamps unchanged.

5. **Batch independent patches into sequential `patch` calls** (one call per logical
   change), not one giant patch. This way each change persists before the next starts.

6. **If session restarts mid-task**, check file timestamps first: if the timestamp
   predates the intended edit, the change never applied. Start fresh from the current
   file state — do not re-apply on top of a potentially partial edit.

## Reference files

- `references/reportlab-helper-signatures.md` — exact function signatures, page geometry constants, 2-col layout derived values, checkbox-with-wrap pattern, named wireframe personas (Sabrina Hoare, Kelsey Montgomery, Bettina Collins, Lauren Faba).

## Signs a session has stalled

- Tool call takes unusually long then returns no diff
- File timestamp unchanged after a claimed write
- Background process list shows no running processes
- `process(action='list')` is empty

## Recovery

1. `ls -lh <file>` to confirm last-modified timestamp
2. Diff against backup or re-read the file to see current state
3. Re-apply missed changes using targeted `patch` calls (not full rewrites)
4. Run and verify before continuing to the next change
