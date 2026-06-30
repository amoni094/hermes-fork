# Hermes Agent optional-skill repo integration

Use this when the task is not just "write a skill" but "land a skill cleanly inside the hermes-agent repository".

## Canonical source

- `optional-skills/<category>/<skill>/SKILL.md` is the source of truth.
- Website pages under `website/docs/user-guide/skills/...` are generated artifacts.

## Safe sequence

1. Create or edit the source `SKILL.md` first.
2. Run `python3 website/scripts/generate-skill-docs.py` from repo root.
3. Immediately inspect `git status --short` and `git diff --stat`.
4. Keep only the expected outputs:
   - the new/edited source skill directory
   - the generated per-skill page(s)
   - `website/docs/reference/optional-skills-catalog.md`
   - `website/sidebars.ts`
5. If the generator rewrote unrelated generated docs, restore those unrelated files before final verification.
6. Verify all expected source and generated files exist, then run `git diff --check`.

## Why this matters

The generator may refresh other generated pages opportunistically. That churn is usually not the change you meant to ship, so treat it as noise unless the task explicitly included those pages.
