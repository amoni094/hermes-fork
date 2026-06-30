---
name: writing-skills
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

## Retrospective update order

When learning from a completed session, prefer this order:
1. patch the currently loaded skill that governed the task
2. patch an existing umbrella skill that already covers the class
3. add a support file under that umbrella (`references/`, `templates/`, or `scripts/`) and point to it from `SKILL.md`
4. create a new class-level umbrella only if no existing skill fits

If two skills overlap, prefer tightening the router language and cross-references before spawning a new sibling skill.

See upstream-inspired notes in `using-superpowers/references/porting-notes.md`.