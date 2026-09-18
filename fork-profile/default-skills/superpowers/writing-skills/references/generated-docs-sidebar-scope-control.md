# Generated docs sidebar scope control

Use this when a skill/doc generator updates shared nav/catalog files and the change must stay tightly scoped.

## Durable pattern

1. Edit the source skill file first; treat generated docs as derived.
2. Run the generator once.
3. Inspect `git status --short` or `git diff --stat` immediately to spot collateral churn.
4. Restore unrelated generated files before making follow-up edits.
5. Search shared nav files before patching. A reference page may need to appear in more than one section.
6. Patch each intended occurrence explicitly with enough context to stay unique.
7. If the generator or another command rewrote the file, re-read it before patching again.
8. After patching, search for the new identifier to confirm the expected count of occurrences.
9. Stage only intended source/generated/catalog/sidebar files.
10. Finish with `git diff --check` and a staged diff summary.

## Why this matters

Shared generated surfaces like `sidebars.ts` and catalog pages are easy to over-edit:

- one patch can miss a second nav surface
- a repeated patch can create duplicate entries
- generator runs can reintroduce unrelated churn after you already inspected the diff

The fix is not "avoid generators"; it is to constrain, re-read, count occurrences, and stage only the intended surface.
