---
name: skills-library-hygiene
description: Audit and consolidate a skills library to remove platform-irrelevant tools, dupes, broken refs, and wiring gaps. Ensure architecture clarity and clean dependency relationships.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, maintenance, curation, architecture, refactoring]
    related_skills: [writing-skills, workflow-map, requesting-code-review, skill-family-router-maintenance]
---

# Skills Library Hygiene

Use when you need to consolidate, audit, or clean up a skills library to:
- remove platform-specific skills from hosts where they don't apply (e.g. macOS-only skills on Linux)
- identify and delete duplicate/overlapping skills
- fix broken `related_skills` references
- wire new architectural patterns (e.g. security tools as opt-in escalations rather than defaults)
- surface hidden dependencies and make relationships explicit
- archive unused or incomplete skills with clear intent tracking

## Prerequisites

- Read access to all skill directories
- Ability to run `find`, `grep`, and understand YAML frontmatter parsing
- Understanding of the target skill library's scope and user base

## Core audit phases (in order)

### Phase 1: Platform and relevance triage

Inventory all skills by **platform applicability**:

```bash
# Find all skills with platform constraints
find ~/.hermes/skills -name 'SKILL.md' ! -path '*/.archive/*' -exec grep -l 'platforms:' {} \;

# Group by platform
grep -rh 'platforms:' ~/.hermes/skills --include='SKILL.md' | grep -v '.archive' | sort | uniq -c
```

**Decision rules:**
- If a skill lists `[macos]` or `[macos, ...]` and you're on Linux, archive it to `.archive/<category>/<name>/`.
- If a skill requires a macOS-specific tool (e.g. `imessage`, `findmy`, `apple-notes`), same rule applies.
- If a skill is multi-platform `[linux, macos, windows]` but requires a tool that's definitely not installed on your host (e.g. a specific binary for a tool that was uninstalled), **do not delete yet** — move to Phase 3 for dependency resolution first.

**Output:** A list of candidates for archival; a note of why each was archived.

### Phase 2: Duplication detection

Look for skills that solve the same problem or are near-exact dupes:

```bash
# Extract skill descriptions
grep -rh 'description:' ~/.hermes/skills --include='SKILL.md' ! -path '*/.archive/*' | sort

# Spot dups by eye, then verify
```

**Decision rules:**
- If two skills have descriptions that are nearly identical or one is a subset of the other, they are candidates for consolidation.
- If one is more general and one is specialized, keep the general one and fold the specialized content into it as a subsection or link.
- If they are genuinely separate concerns (e.g. one is for debugging, one is for optimization), keep both and add a reciprocal `related_skills` link.

**Specific patterns to watch for:**
- `writing-plans` vs `plan` — exact dupe, delete the former
- `hermes-agent-skill-authoring` vs `writing-skills` — different audiences (in-repo vs user-local), keep both
- `github-code-review` and `scoped-pr-fix-and-verification` — complementary, not dupes; add links

**Output:** A list of confirmed dupes with merge/delete decisions; related_skills updates.

### Phase 3: Broken reference hunting

Extract all `related_skills` values and verify they exist:

```bash
# Extract all related_skills refs
grep -rh 'related_skills:' ~/.hermes/skills --include='SKILL.md' | grep -v '.archive' \
  | grep -oP '\[.*?\]' | tr ',' '\n' | tr -d '[] ' | sort -u > /tmp/referenced.txt

# Get actual skill names
grep -rh '^name:' ~/.hermes/skills --include='SKILL.md' | grep -v '.archive' \
  | sed 's/name: //' | sort -u > /tmp/existing.txt

# Find refs that don't exist
comm -23 /tmp/referenced.txt /tmp/existing.txt
```

**Decision rules:**
- Toolset names like `browser`, `terminal`, `image_gen` (meant for context, not to be loaded as skills) → remove from `related_skills`
- Non-existent skills that look like typos or old names → either fix the name if it's a rename or delete the ref
- Skills that should exist but don't (e.g. `hermes-video`, `concept-diagrams`) → decide whether to create them or remove the ref

**Output:** A list of broken refs and fixes applied (find-replace commands, sed patterns, or individual skill patches).

### Phase 4: Architecture clarity and wiring

After cleanup, audit how dependencies actually flow:

- **Security tools**: Should they be loaded by default in `requesting-code-review`, or opt-in escalations? Current Hermes convention is **opt-in escalation** — they live in a decision table, not as hard dependencies.
- **Router skills**: Do family-category skills route clearly to their children? Test by loading them.
- **Overlapping skill families**: `github/*` skills, `hermes-*` skills, `ouroboros/*` commands — verify no cross-family dupes.

**Output:** A summary of architectural decisions (e.g. "security tools are opt-in from `requesting-code-review`, not defaults").

### Phase 5: Archive and document intent

Create an archive-tracking note to explain what was archived and why:

```
~/.hermes/skills/.archive/ARCHIVAL_LOG.md

# Archival Log

## macOS-only skills (Linux host, inapplicable)
- apple/apple-notes (v1.0.0) — macOS Notes sync, not applicable to Linux
- apple/apple-reminders (v1.0.0) — macOS Reminders sync, not applicable to Linux
- apple/findmy (v1.0.0) — Apple Find My, not applicable to Linux
- apple/imessage (v1.0.0) — macOS iMessage, not applicable to Linux
- apple/macos-computer-use (v1.0.0) — macOS-specific, see computer-use instead

## Exact dupes (deleted, content merged)
- superpowers/writing-plans → merged into plan

## Incomplete or dependency-unmet (archived pending future setup)
- github/codebase-inspection — requires pygount (not installed), archived until installed

## Cross-profile note
Each profile may have a different set of archived skills. This log applies to profile: default
```

## Workflow

1. **Run Phase 1** (platform triage). Identify and archive platform-irrelevant skills. Verify archival with `ls ~/.hermes/skills/.archive/`.
2. **Run Phase 2** (duplication). Use description grep + eyeball to find dupes. Merge or delete confirmed dupes. Update related_skills in survivor skills.
3. **Run Phase 3** (broken refs). Use the three-file diff above to find non-existent references. Fix them with targeted skill patches or sed.
4. **Run Phase 4** (architecture). Review security-tool placement, router skills, family overlaps. Patch any wiring gaps found.
5. **Run Phase 5** (document). Create an archival log. Final spot-check: `skills_list` should be shorter and cleaner; `skill_view` on a few random skills should show no broken refs.

## Verification checklist

- [ ] Archival log created at `~/.hermes/skills/.archive/ARCHIVAL_LOG.md`
- [ ] No broken `related_skills` refs remain (run Phase 3 diff to confirm)
- [ ] Duplicate skills removed or consolidated
- [ ] Updated security skills to use opt-in escalation pattern, not hard defaults
- [ ] Router skills (if any) load cleanly and point to children
- [ ] `skills_list()` returns a cleaner list (fewer count)
- [ ] Sampled 5+ skills with `skill_view(name)` — no broken refs in output
- [ ] Profile-specific note added if working in a non-default profile (see Cross-Profile below)

## Cross-Profile Note

Each Hermes profile has its own `~/.hermes/profiles/<name>/skills/` tree. If you're auditing a profile other than `default`:
- archive decisions apply only to that profile
- create the archival log at `~/.hermes/profiles/<name>/skills/.archive/ARCHIVAL_LOG.md`
- note in the log which profile this audit applies to (easy to forget later)

## Pitfalls

- **Archiving too aggressively.** If a skill lists `[linux, macos]` but only requires a tool not yet installed, archive it as "pending tool install" instead of deleting it, so it can be recovered.
- **Not verifying the diff.** The three-file grep/diff above will find most broken refs, but review the results with eyeballs — false positives (refs that happen to not match on exact name) do occur.
- **Forgetting toolset names.** `browser`, `terminal`, `file`, `vision`, `computer-use` are toolsets that should NOT be in `related_skills` — they get confused with skill names. Remove them.
- **Merging too aggressively.** If two skills have overlapping scope but serve different audiences (e.g. in-repo authoring vs user-local), keep both and link them instead of merging.
- **Not updating the archival log.** Future sessions will re-audit if there's no clear log of why something was archived. Create the log even if it's short.
- **Not testing after wiring changes.** If you change `related_skills` or security tool placement, load a few affected skills and verify `skill_view()` shows the new wiring.

## Token optimization addendum

Token spend is dominated by skill *bodies*, not descriptions. High-impact optimizations:

**Description-line trimming**: Descriptions are injected every turn via `skills_list()`. Redundant clauses or nested detail in descriptions are scanned on every session start. Trim descriptions to trigger + core scope, remove exemplary details. Example: `agentic-actions-auditor` was 586 chars of examples; trim to ~230 chars (core trigger + scope) saves ~30% per-instance without losing clarity. Per-skill savings are modest (~70-100 chars each), but cumulative across 160+ skills is measurable. Target: keep descriptions under 200 chars; consolidate multiple concerns into `related_skills` instead.

**Dead-weight archival**: Skills with no CLI installed (xurl, yuanbao), cosmetic-only skills (petdex mascot), jailbreak/red-teaming skills rarely invoked (godmode), and thin pointer skills that just redirect to another skill (superpowers-bootstrap → using-superpowers) are safe candidates. These add noise to skill routing without value. Archive them under `.archive/misc/` with clear intent notes.

**One-time-task skills**: Skills documenting a task already completed (e.g. porting-superpowers-to-hermes, hermes-agent-skill-authoring for a specific project port) outlive their utility. Once the porting is done, archive to `.archive/misc/` — future runs of that migration won't need the skill, and it clutters the navigator.

## References

- `references/broken-refs-patterns.md` — common broken-ref patterns and how to fix them
- `references/security-tools-wiring.md` — opt-in escalation pattern for security scanning tools
- `references/archival-log-template.md` — copy-paste template for creating an archival log
- `references/archival-patterns.md` — six common archival patterns (no CLI, cosmetic, jailbreak, thin pointer, one-time-task, empty dirs) with detection and triage rules

## Completion rule

Do not mark this as complete until:
1. Archival log exists and documents all archived skills with intent.
2. Phase 3 diff confirms no broken refs remain (empty `comm -23` output).
3. You have sampled at least 5 random skills and verified no broken refs in their `related_skills` output.
4. A clean `skills_list()` call succeeds (no errors).
