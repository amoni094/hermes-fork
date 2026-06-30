---
name: hermes-acp-routing
description: Route Hermes delegate_task work to local Codex ACP safely, with Hermes fallback and compact context packets.
version: 1.0.0
author: Hermes
---

# Hermes ACP Routing

Use this when you want Hermes delegation plus explicit ACP transport where the target CLI is actually ACP-compatible.

Local reality on this machine:
- `codex` is installed and authenticated, but Hermes ACP delegation was not confirmed against it in this session.
- Hermes `delegate_task(..., acp_command=...)` currently expects an ACP-compatible CLI. The Codex CLI available here exposes `mcp-server`, not the documented `--acp --stdio` transport, so treat Codex routing as experimental rather than guaranteed.
- Prefer normal Hermes `delegate_task` unless you have a verified ACP target such as a CLI that explicitly supports `--acp --stdio`.

## Single-task pattern

Use this only with a CLI you have already verified to support ACP.

```python
delegate_task(
  goal="Implement the bugfix and run focused tests",
  context="Pass only the relevant files, errors, and acceptance criteria.",
  toolsets=["terminal", "file"],
  acp_command="<verified-acp-cli>",
  acp_args=["--acp", "--stdio"]
)
```

## Parallel pattern

```python
delegate_task(tasks=[
  {
    "goal": "Inspect the code path and identify the regression",
    "context": "Return only findings and affected files.",
    "toolsets": ["file", "terminal"]
  },
  {
    "goal": "Implement the fix and run targeted tests",
    "context": "Keep the patch minimal and include exact commands run.",
    "toolsets": ["file", "terminal"],
    "acp_command": "<verified-acp-cli>",
    "acp_args": ["--acp", "--stdio"]
  }
])
```

## Compact context packet

Always pass:
1. exact file paths
2. exact failing command or error
3. acceptance criteria
4. constraints on scope
5. output contract: changed files, commands run, pass/fail

## Guardrails

- Prefer Hermes leaf agents for discovery and Codex ACP for implementation.
- Keep ACP tasks narrow.
- Verify any side effects yourself before reporting success.
- Do not assume Claude Code is installed unless `command -v claude` or equivalent confirms it.
