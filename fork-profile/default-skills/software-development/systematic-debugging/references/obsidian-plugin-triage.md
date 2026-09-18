# Obsidian plugin triage

Use when a user reports that Obsidian or a similar Electron note app "doesn't work properly anymore" and logs are thin.

## Goal

Prove whether the regression lives in:
1. the core app/runtime,
2. community plugins, or
3. workspace/layout state.

## Safe recovery order

1. Read the enabled community plugin list.
   - Obsidian: `.obsidian/community-plugins.json`
2. Read the local app logs.
   - Obsidian often logs launches and updates but may not emit a useful plugin stack trace.
3. Back up the current enablement and layout files with timestamps.
   - Obsidian: back up `.obsidian/community-plugins.json`
   - Obsidian: back up `.obsidian/workspace.json`
4. Disable all community plugins by replacing the enabled-plugin list with `[]`.
5. Restart the app and retest.
6. If the app is fixed, re-enable plugins in small batches or one-by-one until the culprit returns.
7. Only if the app is still bad with all plugins disabled, try resetting workspace/layout state from the backed-up `workspace.json` baseline.

## Why this order works

- Plugin regressions are common after app updates and can present as vague slowness, broken panes, missing commands, or general "weirdness".
- The logs may stay clean enough that waiting for an explicit stack trace wastes time.
- Disabling the enabled-plugin list is a small, reversible isolation step.
- Resetting layout/workspace before proving the no-plugin baseline throws away useful state too early.

## Reporting checklist

In the final message, include:
- which file was changed,
- the backup paths,
- whether the plugin list now validates as JSON,
- the exact next user action (`fully quit and reopen Obsidian`).
