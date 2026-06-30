# Evaluating workflow/plugin repositories after clone

Use this when the repository is not primarily an application codebase but a methodology pack, plugin bundle, or agent workflow library.

## Fast review order

1. Read `README.md` for the stated workflow and supported platforms.
2. Inspect root metadata (`package.json`, plugin manifests, extension manifests) to see the real artifact shape.
3. Find the shared source-of-truth directories (`skills/`, `prompts/`, `templates/`, `hooks/`).
4. Inspect bootstrap/session-start files first. These usually explain how the repo injects behavior into the host harness.
5. Check platform-specific wrapper manifests to see whether they are thin shims or divergent implementations.
6. Look for testing/docs that verify the workflow itself, not just code units.

## What to extract

- Is there a single shared skills/prompt library with thin per-platform packaging?
- How does session bootstrap happen (hook, context file, plugin init, transform)?
- Which practices are core and portable versus overly harness-specific?
- Is there evidence the workflow is tested end-to-end through real sessions/transcripts?

## Superpowers example signals

In `obra/superpowers`, the high-value implementation ideas were:
- shared `skills/` library with thin Claude/Codex/Cursor/Gemini/OpenCode wrappers
- session-start hook that injects the bootstrap skill into context
- workflow-testing docs that validate subagent/review behavior from real transcripts

The less reusable parts were the universal hard gates (mandatory brainstorming/TDD/process for nearly every task). Favor selective adaptation over verbatim copying.
