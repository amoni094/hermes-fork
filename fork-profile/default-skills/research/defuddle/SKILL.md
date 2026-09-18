---
name: defuddle
description: Use when extracting clean markdown from web pages.
triggers:
  - User provides a URL to read or analyze
  - Extracting article or documentation content from the web
  - Need clean readable text from a webpage with minimal clutter
  - First-pass extraction before running grounded-citations or research synthesis (step 2 in web fallback chain: web_extract → defuddle → firecrawl-research → blocked-page-recovery)
  - NOT for .md URLs (use web_extract), NOT for JS-heavy SPAs (use firecrawl-research)
platforms: [linux, macos]
related_skills:
  - firecrawl-research
  - blocked-page-recovery
  - grounded-citations
  - academic-literature-review
---

# Defuddle

Extract clean readable markdown from web pages using the `defuddle` CLI. Prefer over `web_extract` for standard web pages (articles, docs, blog posts) — strips navigation, ads, and clutter, reducing token usage.

Install: `/var/home/rainbow/.npm-global/bin/defuddle` (v0.19.2, installed 2026-08-13)

Do NOT use for `.md` URLs — already markdown, use `web_extract` directly.

## Basic usage

```bash
# Extract to stdout as markdown
defuddle parse --md <URL>

# Save to file
defuddle parse --md <URL> -o content.md

# Extract specific metadata
defuddle parse -p title <URL>
defuddle parse -p description <URL>
defuddle parse -p domain <URL>
```

## Output formats

| Flag      | Format                          |
|-----------|---------------------------------|
| `--md`    | Markdown (default choice)       |
| `--json`  | JSON with HTML + markdown       |
| (none)    | HTML                            |
| `-p prop` | Specific metadata property      |

## Workflow

1. Run `defuddle parse --md <URL>` via terminal
2. Use cleaned markdown directly — no post-processing needed
3. For large pages, save with `-o content.md` and read with `read_file`

## Pitfalls

- Requires `~/.npm-global/bin` on PATH — verify with `which defuddle` if it fails
- Not suitable for JS-heavy SPAs — fall back to `browser_navigate` for those
- Paywalled pages still block; use `blocked-page-recovery` skill as fallback
