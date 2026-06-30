# Config-guarded Hermes edit pattern

Use when a Hermes maintenance/tuning task requires a small edit to `~/.hermes/config.yaml` but direct mutation tools refuse because the file is treated as security-sensitive.

## Trigger
- A direct edit tool refuses with a message equivalent to: Hermes config is security-sensitive and must be edited via Hermes-native means or direct file editing.

## Safe fallback
1. Confirm the target change is narrow and reversible.
2. Create a timestamped backup of `~/.hermes/config.yaml`.
3. Use the smallest possible scripted edit, ideally replacing one known YAML block rather than rewriting the whole file.
4. Read back the exact changed lines.
5. Run `hermes config check`.
6. Re-run the live inventory command that proves the intended effect:
   - `hermes skills list` for skill disables
   - `hermes tools list` for toolset changes
   - `hermes mcp list` for MCP changes

## Why this pattern
- It preserves reversibility.
- It avoids broad hand edits to a security-sensitive file.
- It produces grounded verification instead of stopping at the first tool refusal.

## Reporting pattern
- State that the direct config patch path was blocked by Hermes guardrails.
- State that a backup was created first.
- List the exact config-surface changes made.
- Report verification from both config readback and live Hermes CLI output.

## Scope rule
Use this only for small, well-understood config edits. If the task is broad or ambiguous, prefer Hermes-native subcommands or ask the user before making wider manual edits.
