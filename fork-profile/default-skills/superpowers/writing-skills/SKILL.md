---
name: writing-skills
related_skills:
  - test-driven-development
  - using-superpowers

triggers:
  - creating or refining a Hermes SKILL.md
  - authoring a new skill from scratch or improving an existing one
  - want quality standards and structure for a skill file
  - need to validate a skill against real pressure scenarios rather than prose alone
description: Use when creating or refining Hermes skills and you want them validated against real pressure scenarios rather than prose alone.
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, documentation, process, tdd]
    related_skills: [test-driven-development, using-superpowers]
---

# Writing Skills

Treat skill authoring as TDD for process documentation.

## Skill vetting (treat skills like dependencies)

A skill is instructions dropped into your agent's context. Treat it like an npm dependency:
- Read the SKILL.md before installing or loading any third-party skill.
- Star count is a popularity signal, not a quality review.
- Skim: what does it tell the agent to do? Does that match how you actually work?
- Keep only skills that align with your workflow; discard or disable those that don't.
- When a skill takes over your whole workflow (e.g. forces spec-driven steps you don't want), that is a signal to extract only the parts you need rather than using it wholesale.

For Hermes skills specifically: prefer adapting or patching an existing skill over installing a new external one that duplicates the same class of work.

## Hermes process

1. Identify the failure mode or repeated workflow worth encoding.
2. Capture one or more pressure scenarios showing baseline failure without the skill.
3. Write the minimum skill content that would prevent that failure.
4. Verify the skill is discoverable: strong `description`, relevant keywords, concise trigger conditions.
5. Load and read the skill back through Hermes tooling.
6. If the skill lives inside a repo with generated docs/indexes (for example hermes-agent optional skills), run the repo's generator, inspect the git diff, and restore unrelated generated churn before finishing.
7. Patch loopholes discovered during real use.

## Repo-generated skill surfaces

When adding or editing skills inside a repository that auto-generates docs/catalogs:

- treat the source `SKILL.md` as canonical; generated pages are derived artifacts
- after running the generator, inspect `git status`/`git diff --stat` immediately
- keep intended outputs only: the new skill source, its generated page, and the minimal catalog/sidebar/index updates
- if the generator rewrites unrelated pages, restore those unrelated files before final verification
- verify both source existence and generated-page/catalog/sidebar inclusion before claiming completion
- if a sidebar or index file contains the same reference section in multiple places, search first and patch each intended location explicitly; do not assume one insertion covers the whole nav surface
- after a generator rewrite or any other external edit, re-read the target file before patching again; patching against a stale partial read makes duplicate insertions much more likely

References:
- `references/hermes-agent-optional-skill-repo-integration.md`
- `references/generated-docs-sidebar-scope-control.md`

## Rules

- descriptions should describe when to use, not summarize the whole workflow
- keep reusable references in `references/` when they are heavy
- prefer concise, high-signal instructions over narrative history
- if a skill proves stale during use, patch it immediately
- prefer class-level umbrellas over one-session-specific skills
- when several narrow skills overlap, patch the umbrella/router first and move session-specific detail into `references/`
- if a maintenance session produces inventory/accounting ambiguity, prefer adding a reproducible support artifact (for example a small generator script plus generated report) under the existing umbrella/repo instead of leaving the conclusion as chat-only prose
- if usage metadata and active skill paths disagree, reconcile aliases / archived names / renamed skills before using raw usage counts to drive cleanup decisions
- when doing a maintenance pass, bias toward action: patch routing, add a concise reference, or update trigger text instead of concluding that nothing changed

## Skill writing discipline — rationale comments (arXiv:2608.11095)

Every rule or step added to a skill MUST include an inline rationale comment:
`<!-- why: prevents [specific failure mode] in [session/task type] -->`.
Rationale enables O(1) deletion audit vs O(2^n) without rationale.
(arXiv:2608.11095: +23.1% instruction-following in ablation over 1867 repos).
<!-- why: prevents un-auditable instruction sediment in skill-writing sessions -->

**Deletion audit:** When reviewing a skill, check each rule: does the rationale still apply?
Stale rationale → delete the rule. Missing rationale → flag as deletion candidate.
<!-- why: prevents keep-all default when SkillOpt reviews writing-skills / SKILL.md files -->

## Skill-library maintenance and topology cleanup

When a session reveals overlap, stale references, routing ambiguity, or inventory-count disagreement in the skill library:
1. patch the skill that was already loaded if it governs the class of work
2. if multiple sibling skills overlap, strengthen the umbrella/router so it points clearly to canonical leaves
3. remove or replace references to missing sibling skills immediately
4. generate inventory from multiple live surfaces before trusting counts: local `SKILL.md` files, `hermes skills list --source builtin`, `hermes skills list --source local`, and `.usage.json`
5. document stale usage-key mismatches and replacement targets in a concise `references/` note before using usage counts to justify pruning
6. favor a target topology of: umbrella router -> narrow leaves -> heavy detail in `references/`

Use `references/skill-library-topology-maintenance.md` for the compact maintenance checklist, replacement-map pattern, and inventory-generator workflow.
Use `references/usage-metadata-migration.md` for the backup-first migration pattern when stale `.usage.json` keys should be merged into current umbrella/leaf skills rather than left as historical drift.
- prefer updating an existing loaded skill or umbrella before creating anything new
- prefer class-level umbrella skills over narrow one-session skills
- put session-specific detail, research excerpts, transcripts, durable examples, and replacement maps into `references/` instead of bloating `SKILL.md`
- when bundled/protected skills are the conceptual umbrella, improve the surrounding local skills and references rather than forcing edits to the protected skill
- after substantial sessions, actively look for at least one skill update; a no-op pass should be rare and justified
- **verify subagent work before dispatching follow-up batches**: after parallel subagents patch skills, run the coverage check first — subagents frequently complete more than expected. In the 2026-07-04 audit, a follow-up batch of 61 manual patches was prepared but all 58 routing candidates were already done by the subagents. Check → then act, not act → then discover.
- **trigger coverage audit**: when auditing trigger presence across the skill library, classify skills first (routing candidates vs slash-cmds vs repo-specific vs tool-wrappers vs builtins) before computing coverage. Raw "X% have triggers" is misleading if exempt classes are mixed in. See `adversarial-review/references/skill-library-audit.md` for the full taxonomy, extraction script, and five adversarial checks.

## Retrospective update order

When learning from a completed session, prefer this order:
1. patch the currently loaded skill that governed the task
2. patch an existing umbrella skill that already covers the class
3. add a support file under that umbrella (`references/`, `templates/`, or `scripts/`) and point to it from `SKILL.md`
4. create a new class-level umbrella only if no existing skill fits

If two skills overlap, prefer tightening the router language and cross-references before spawning a new sibling skill.

See upstream-inspired notes in `using-superpowers/references/porting-notes.md`.

## Skill Library Topology — Maintenance Patterns

**Target shape:** class-level umbrella skills with narrow leaves for distinct workflows; heavy task-specific detail in `references/`; avoid one-session-one-skill proliferation.

**Maintenance order:**
1. Patch the loaded skill or umbrella already governing the task class
2. Strengthen routers before creating new siblings
3. Move compact task-specific learnings into `references/`
4. Generate inventory from multiple sources (live SKILL.md files + `hermes skills list --source builtin/local` + `.usage.json`) before trusting counts
5. Distinguish: active / archived / alias-renamed / historical-replacement-mapped

**Common pitfalls (topology):** Trusting raw `.usage.json` keys as live skill inventory. Treating bundled-name aliases as separate real skills. Deleting/archiving before clarifying the replacement path. Creating narrow new skills when an umbrella + reference file would do.

## Usage Metadata Migration — Safe Pattern

**When:** `.usage.json` keys no longer align with active skill names (renames, absorptions, archives).

**Steps:**
1. Build a replacement map first (separate pure aliases from true replacements; leave unresolved historical keys unresolved)
2. Back up raw `.usage.json` before any mutation
3. Merge: add `use_count`/`view_count`/`patch_count`, keep earliest `created_at`, keep latest `last_used_at`/`last_viewed_at`/`last_patched_at`, preserve `pinned` if either side pinned
4. Regenerate authoritative inventory; verify stale-key count drops
5. Keep a migration report so merge history is explainable

**Rule:** Do not mutate usage metadata blindly because a stale key exists. A documented unresolved historical key is better than a fabricated replacement.

See `references/skill-library-topology-maintenance.md` and `references/usage-metadata-migration.md` for full patterns.

## SKILL.md frontmatter schema (required fields)

Every SKILL.md must start with a YAML frontmatter block containing at minimum:

```yaml
---
name: skill-name-hyphenated          # matches directory name
description: >
  Use when <trigger>. <one-sentence behavior>. # first 57 chars shown in skill index
triggers:
  - Natural language trigger phrase 1
  - Natural language trigger phrase 2
related_skills:
  - other-skill-name
version: 1.0.0
platforms: [linux, macos, windows]   # omit platforms not supported
---
```

Optional but recommended: `author`, `license`, `metadata.hermes.tags`.
The `description` field's first 57 chars are shown in the skill index — make the trigger self-contained there.
Skills with `user-invocable: false` do not need Use when triggers (exclude from trigger coverage audits).

## Reference files

- `references/skill-topology-cleanup.md` — Skill topology cleanup
