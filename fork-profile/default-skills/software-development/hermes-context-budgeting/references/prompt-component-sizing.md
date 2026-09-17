# Measuring the size of a specific system-prompt component

`hermes prompt-size` gives whole-prompt totals. When you need the cost of ONE
component (the skills block, tool schemas, a memory section) to decide where to
optimize, measure that component directly instead.

## Golden rule: don't import hermes modules to measure

Importing `agent.prompt_builder` (or calling `build_skills_system_prompt()`)
can trigger config/gateway side effects and is often blocked in restricted
sessions. Prefer a **read-only parse of an existing on-disk artifact** that the
builder already produced, and reconstruct the rendered string yourself using the
exact formatting from the source. This is faster, side-effect-free, and matches
what actually ships in the prompt.

## The skills block — where it comes from

- Builder: `build_skills_system_prompt()` in `agent/prompt_builder.py` (~line 1417).
- Rendered string assembled at ~lines 1646–1688:
  - `## Skills (mandatory)` **preamble** (~515 chars as of 2026-07-03 optimization pass).
  - `<available_skills>` … `</available_skills>` index body.
  - Footer: proceed-note + dormant-skills note (~402 chars when 51 dormant skills exist; ~82 chars when none).
- Per-category line (multi-skill): `  {category}: {cat_desc_truncated}` (or bare `  {category}:`).
  - Category descriptions capped at **80 chars** (`cat_desc[:77] + "..."` if longer). Added 2026-07-03.
- Per-skill line: `    - {name}: {desc}` (or `    - {name}` with no desc).
- **Single-skill categories** render inline as `  {category}/{name}: {desc}` — no separate header line. Added 2026-07-03.
- Fields emitted per skill: **only** frontmatter `name` + truncated `description`.
  No paths, no body, no tags.

## Optimization / size hooks

- **Description truncation**: `extract_skill_description()` in
  `agent/skill_utils.py` (~line 710) hard-caps descriptions at **40 chars**
  (`desc[:37] + "..."` if longer). Updated from 60 chars on 2026-07-03.
- **Category description truncation**: category DESCRIPTION.md contents are
  capped at **80 chars** at render time (added 2026-07-03).
- **Single-skill category inlining**: categories with exactly one skill emit
  `  {category}/{name}: {desc}` instead of a header + bullet (added 2026-07-03).
- **`compact_categories`** (coding posture) demotes whole categories to a single
  `  {category} [names only]: a, b, c` line — drops descriptions, keeps names.
  This is the main context-aware size lever. See `agent/coding_context.py`.
- Two-layer cache (in-process LRU + disk snapshot) — perf only, not size.
- There is **no** relevance/embedding filtering. Every enabled + compatible skill
  emits a full line every turn.

## Filtering layers applied before render (affect which skills appear)

- Platform: `skill_matches_platform` (frontmatter `platforms:` list).
- Environment: `skill_matches_environment` (kanban/s6/docker offer-time gate).
- Per-platform disabled list: `get_disabled_skill_names(platform)`.
- Tool/toolset conditions: `_skill_should_show` — `requires_tools/toolsets`,
  `fallback_for_tools/toolsets`.

Note: the **disk snapshot is unfiltered** (it caches all parsed skills). The
disabled/tool/platform filters are applied at *render* time, so a raw snapshot
count can be a few higher than the number that actually ships.

## Read-only measurement recipe (reusable)

Snapshot lives at `~/.hermes/.skills_prompt_snapshot.json`. Structure:
`{version, manifest, skills: [{skill_name, category, frontmatter_name,
description, platforms, conditions}], category_descriptions: {...}}`.

```python
#!/usr/bin/env python3
"""Read-only sizing of the available_skills block. No hermes imports."""
import json

snap = json.load(open("/var/home/rainbow/.hermes/.skills_prompt_snapshot.json"))

def trunc_desc(d, cap=40):          # mirror extract_skill_description (40-char cap)
    d = str(d or "").strip().strip("'\"")
    return d[:cap-3] + "..." if len(d) > cap else d

def trunc_cat(d, cap=80):           # mirror category description truncation
    return d[:cap-3] + "..." if len(d) > cap else d

by_cat, cat_desc = {}, snap.get("category_descriptions", {}) or {}
for e in snap.get("skills", []):
    by_cat.setdefault(e.get("category") or "general", []).append(
        (e.get("frontmatter_name") or e.get("skill_name") or "", trunc_desc(e.get("description", ""))))

lines = []
for cat in sorted(by_cat):
    seen = set()
    cat_skills = []
    for name, d in sorted(by_cat[cat], key=lambda x: x[0]):
        if name not in seen:
            seen.add(name)
            cat_skills.append((name, d))

    if len(cat_skills) == 1:
        name, d = cat_skills[0]
        lines.append(f"  {cat}/{name}: {d}" if d else f"  {cat}/{name}")
    else:
        cd = cat_desc.get(cat, "")
        lines.append(f"  {cat}: {trunc_cat(cd)}" if cd else f"  {cat}:")
        for name, d in cat_skills:
            lines.append(f"    - {name}: {d}" if d else f"    - {name}")

body = "\n".join(lines)
block = "<available_skills>\n" + body + "\n</available_skills>\n"
n_skills = len([l for l in lines if l.strip().startswith("- ")] +
               [l for l in lines if l.startswith("  ") and "/" in l and not "[names" in l])
print("skill entries      :", n_skills)
print("<available_skills> :", len(block), "chars  (~", round(len(block)/4), "tokens)")
print("avg chars / entry  :", round(len(block)/max(n_skills,1),1))
# Full section = preamble (~515 chars) + block + footer (~402 chars with dormant note)
```

## Measured baseline (July 2026, post-optimization, 101 enabled / 51 dormant)

| Segment | chars | ~tokens (÷4) |
|---|---|---|
| Preamble (mandatory header+instructions) | 515 | ~128 |
| `<available_skills>` index body | 9,609 | ~2,402 |
| Footer (proceed note + dormant note) | 402 | ~100 |
| **full skills section** | **10,526** | **~2,631** |

- 100 skill lines in index, ~24 chars/skill avg (names dominate over descriptions now).
- Category descriptions capped at 80 chars; single-skill categories inlined.

### Pre-optimization baseline for comparison (same install, 149 enabled skills)

| Segment | ~tokens |
|---|---|
| Full skills section (149 skills, 60-char desc, uncapped cat desc, no inlining) | ~3,933 |

Net savings from full pass (disable 48 skills + 5 render patches): **~1,302 tokens/session**.

## Optimization implications (respect the AGENTS.md constraints)

- Prompt caching is "sacred": the block must stay **byte-stable for the life of a
  conversation**. Any size change must not mutate mid-conversation.
- Entries must **never be fully removed** — agent-created skills are the model's
  project memory; `compact_categories` demotes to names-only rather than deleting.
- Biggest remaining lever: **embedding-based semantic shortlist** per-turn using
  an embedding model (e.g. OpenAI text-embedding-3-small; NOTE: Ollama/nomic-embed-text
  was uninstalled 2026-07-12, use OpenAI API instead). Would inject only top-K
  relevant skills in the messages layer (NOT system prompt, to preserve prefix
  caching). Estimated saving: ~2,000 tokens/session. Prior art: Anthropic Tool
  Search Tool (advanced-tool-use-2025-11-20 beta, `defer_loading`), 85% token
  reduction in production. Pattern already exists in hindsight `prefetch(query)`
  / `sync_turn` per-turn lifecycle.
