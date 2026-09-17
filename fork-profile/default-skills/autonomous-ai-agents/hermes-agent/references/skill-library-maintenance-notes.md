# Skill Library Maintenance Notes

Use this when the task is about Hermes skill-library cleanup rather than runtime configuration.

## Common maintenance tasks
- route umbrella skills to canonical leaves
- replace stale references to missing sibling skills
- keep heavy examples/checklists in `references/`
- reconcile `.usage.json` keys with active skill paths before ranking/pruning
- prefer low-risk routing edits before aggressive archive/delete passes

## Typical cleanup sequence
1. inventory active vs archived skills
2. identify overlap clusters
3. patch umbrella/router language first
4. add compact support references for heavy skills
5. reconcile stale usage names and replacement targets
6. only then consider archive/disable recommendations
