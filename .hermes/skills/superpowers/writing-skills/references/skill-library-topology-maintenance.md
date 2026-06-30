# Skill Library Topology Maintenance

Use this when a session reveals overlap, stale routing, or mismatched inventory signals in the Hermes skill library.

## Target shape
- class-level umbrella skills
- narrow leaves for clearly distinct workflows
- heavy session-specific detail in `references/`
- avoid one-session-one-skill proliferation

## Maintenance order
1. patch the loaded skill or umbrella already governing the task class
2. strengthen routers before creating new siblings
3. move compact task-specific learnings into `references/`
4. generate inventory from multiple sources before trusting counts:
   - live `SKILL.md` files
   - `hermes skills list --source builtin`
   - `hermes skills list --source local`
   - `.usage.json`
5. distinguish four states in reports:
   - active
   - archived
   - alias/renamed
   - historical/replacement-mapped
6. prefer replacement maps and derived reports before mutating raw `.usage.json`

## Practical pattern from this session
- add tiny routing references to large umbrella skills before attempting major body rewrites
- patch overlapping local skills to point at canonical routers
- keep protected bundled skills unchanged; improve local umbrellas and support files around them instead
- when inventory sources disagree, create a reproducible generator and commit the generated outputs

## Common pitfalls
- trusting raw `.usage.json` keys as if they were the live skill inventory
- treating bundled-name aliases as separate real skills
- deleting or archiving before clarifying the replacement path
- creating narrow new skills when an umbrella plus a reference file would do
