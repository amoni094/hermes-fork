# Skill topology cleanup

Use this when a session reveals that the skill library itself needs maintenance rather than just one more new skill.

## Target shape
- class-level umbrella skills
- narrow specialist leaves
- session-specific detail in `references/`
- no proliferation of one-session-one-skill entries

## Cleanup order
1. patch the currently loaded skill if it governs the work
2. patch the existing umbrella/router if overlap spans several siblings
3. add a compact reference file for session-specific detail or reconciliation notes
4. create a new umbrella only if no existing class-level skill fits

## Signals that justify cleanup
- stale references to missing sibling skills
- two or more skills that seem to answer the same trigger
- oversized `SKILL.md` bodies whose first screen does not tell the agent when to use the skill
- usage metadata that no longer matches active skill paths because of renames, archives, or bundled-name aliases
- repeated need to explain "use X for the umbrella, Y for the leaf"

## Inventory reconciliation pattern
When `~/.hermes/skills/.usage.json` disagrees with active skill paths:
- separate entries into:
  - active exact matches
  - alias/renamed matches
  - archived/superseded names
  - unknown legacy names
- do not use raw usage keys as authoritative rankings until this mapping exists
- record the mapping in a concise reference or inventory report before pruning or consolidation

## Routing cleanup pattern
- make the umbrella explicitly say when to load it
- tell the agent which narrow sibling to use for the most common subcases
- remove references to missing or retired siblings immediately
- keep the opening screen compact; move long examples/checklists to references

## Reporting rule
A useful maintenance pass should usually end with at least one of:
- a patched trigger/description
- a removed stale reference
- a new reference file capturing reconciliation detail
- a clearer umbrella -> leaf map
