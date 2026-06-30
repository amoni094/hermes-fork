# Conservative disable-only pruning for Hermes

Use this when the user wants token optimization or prompt-surface cleanup, but the safest first move is reversible disable-only changes rather than deleting files or removing servers.

## Decision rule
Prefer this order:
1. disable low-value default toolsets
2. disable low-use enabled skills
3. leave MCP servers unchanged unless the user explicitly wants a second pass
4. verify before/after inventory and config health

Reason: default enabled surfaces matter more than on-disk size, and disable-only edits are easy to reverse.

## Recommended first-pass candidates
Toolsets:
- `image_gen`
- `tts`
- `computer_use`
- optionally `browser` if the user rarely uses browser automation

Skills:
- start with enabled local skills that show zero use or obvious overlap with umbrella skills
- prefer broad/nice-to-have skills over core verification/debugging/workflow skills

## Verification workflow
After changes, verify all of:
- `hermes tools list`
- `hermes skills list`
- `hermes config check`

If skill-state changes were made through `skills.disabled`, also verify the list is still a real YAML sequence, not a quoted scalar.

## Reporting format for this class of task
Keep the final report concise and in English.

Recommended structure:
1. `Applied conservative disable-only cleanup`
2. `Toolsets disabled` with exact names
3. `Skills disabled` with exact names
4. `What I verified`
   - before/after counts
   - config check result
   - whether MCP servers were changed or left untouched
5. one short note that toolset changes apply fully in a new session or after `/reset`

## Pitfalls
- Do not start by deleting skills or removing MCP servers unless the user asked for a more aggressive pass.
- Do not optimize based on disk size alone; optimize based on enabled prompt surface first.
- Do not bury the result in a long essay; this cleanup class benefits from short before/after accounting.
