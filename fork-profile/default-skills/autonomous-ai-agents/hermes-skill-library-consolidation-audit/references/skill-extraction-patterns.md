# Skill Extraction Patterns (for large SKILL.md reduction)

Validated Aug 2026 during `knowledge-graph-corpus-pipeline` refactor (82KB → 58KB).

## Three extraction patterns

### Pattern A — New extraction (no reference file yet)
Use when: a large self-contained section (>50 lines of code or prose) has no
corresponding file in `references/`.

Steps:
1. Write full section to `references/[descriptive-name].md` using `write_file`
   (never `skill_manage` — write_file works reliably on arbitrary paths)
2. Replace inline section with a 3-line pointer stub:
   ```
   ## Section Name
   Full implementation: `references/[file].md`
   [1-sentence summary of what the section covers — enough to know when to load it]
   ```
3. Add a bullet to the `## Reference Files` section of SKILL.md pointing at the new file

### Pattern B — Pitfall condensing (reference file already exists, pitfall has inline code)
Use when: a pitfall section is 40+ lines but the reference/ already has the deep
content; the inline version just needs enough to recognize the issue.

Steps:
1. Do NOT create a new references/ file — one already exists
2. Compress the pitfall body to ~10-15 lines of prose capturing all key points
3. End with: `See \`references/[existing-file].md\` for full detail / verification scripts`

Example — pitfall 22 (OWL schema audit) went from 50-line bullet list to a 14-line
paragraph pointing at `owl-rdf-ontology-audit-checklist.md`. Saves ~2.5KB per pitfall.

### Pattern C — Cross-reference only (pitfall body redundant with existing reference)
Use when: a pitfall has a large table or API spec list that's already in a references/ file.

Steps:
1. Keep pitfall header + 2-3 sentence description of the failure mode only
2. Strip inline code blocks that are already in the reference file
3. Add trailing `See references/[file].md` line

Example — pitfall 19 (native language sources, 60 lines + table) condensed to
8 lines + pointer to `native-language-sources.md`. Saves ~3KB per pitfall.

## Cleanup checklist after any extraction pass

- `wc -c SKILL.md` — confirm under target
- `grep -n "^---$" SKILL.md` — check for duplicate `---` separators (can appear when
  sections are removed, leaving orphaned `---` pairs that render as `<hr><hr>`)
- `grep -n "^[a-z]" SKILL.md | head -20` — check for orphaned text blocks not under
  any `##` heading (context artifacts from prior sessions / context compression)
- Verify the `## Reference Files` index lists all new files created in this pass

## Size targets

| Range | Status | Action |
|-------|--------|--------|
| < 30KB | Healthy | No action |
| 30–50KB | Monitor | Check if any section >5KB is a knowledge bank |
| 50–80KB | Extract | Identify largest self-contained section first |
| > 80KB | Urgent | Skill writes may fail; extract immediately |

Target after extraction: < 50KB for comfortable headroom (not just under 60KB).

## Tool notes

- Use `patch` for targeted section replacement — more reliable than write_file on
  large files since it does fuzzy match (9 strategies handle minor whitespace diffs)
- Use `wc -c` not `wc -l` for size checks (bytes are the constraint, not lines)
- `write_file` on `references/[file].md` directly (not via skill_manage) for new refs
- After creating new reference files, verify with `ls -la references/` to confirm
