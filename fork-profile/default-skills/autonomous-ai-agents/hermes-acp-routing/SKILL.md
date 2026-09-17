---
name: hermes-acp-routing
triggers:
  - Routing a Hermes delegate_task to local Codex ACP safely
  - Deciding between native Hermes delegation and ACP execution for a coding task
  - Codex ACP is available locally and should be used for a bounded coding subtask
  - Need compact context packets for spawning an ACP-backed subagent
description: >
  Use when routing Hermes delegate_task work to local Codex ACP safely, with Hermes fallback and compact context packets.
version: 1.1.0
author: Hermes
related_skills:
  - dispatching-parallel-agents
  - autonomous-agent-loop-design
  - hermes-agent
---

# Hermes ACP Routing

Use this when you want Hermes delegation plus explicit ACP transport where the target CLI is actually ACP-compatible.

Local reality on this machine:
- `codex` is installed and authenticated, but Hermes ACP delegation was not confirmed against it in this session.
- Hermes `delegate_task(..., acp_command=...)` currently expects an ACP-compatible CLI. The Codex CLI available here exposes `mcp-server`, not the documented `--acp --stdio` transport, so treat Codex routing as experimental rather than guaranteed.
- Last verified: 2026-08-15. Re-verify with: `codex --help | grep -i acp`
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

- Do not assume Claude Code is installed unless `command -v claude` or equivalent confirms it.

## Aug 2026: Learned Orchestration Routing (Sakana AI "Learning to Orchestrate")

Source: https://sakana.ai/learning-to-orchestrate/
Finding: a meta-agent can learn *which* specialized sub-agent to delegate to by tracking
historical success rates per agent/skill and using them as routing weights — rather than
hard-coding routing rules.

**Hermes implementation pattern (lightweight, no extra infra):**
1. After each delegate_task completes, append to `~/.hermes/routing-log.jsonl`:
   ```json
   {"ts": "2026-08-12T01:00:00Z", "skill": "hermes-acp-routing", "goal_hash": "abc123",
    "success": true, "duration_s": 45, "error": null}
   ```
2. Before dispatching a new delegation, load the last 20 entries for matching skills.
3. Down-weight skills with >30% recent failure rate; prefer alternatives if available.
4. Reset weights when a skill is patched (version bump = fresh start).

This is a lightweight empirical routing layer on top of the current rule-based routing.
No ML required — rolling success rate is sufficient signal at Hermes scale.

## Guardrails

- Prefer Hermes leaf agents for discovery and Codex ACP for implementation.
- Keep ACP tasks narrow.
- Verify any side effects yourself before reporting success.

## MCP Gateway Auth Pattern (arXiv:2608.10760, Aug 2026)

Production pattern: centralized MCP gateway fronts ALL downstream MCP servers.

Two-axis auth model: persona (interactive user vs. non-user/agent) x credential type.
Hermes rule: treat cron/delegate_task calls as non-user persona — no interactive auth.

Three token models: BYOT (current Hermes pattern for API keys), GYOT (correct for cron jobs
that need service-account tokens), Delegated OAuth (for user-session-scoped calls).

Identity delegation: gateway logs originating session ID per tool call — when tools have
side effects (email, git push), Hermes should record originating session in the audit trail.
- Do not assume Claude Code is installed unless `command -v claude` or equivalent confirms it.

## Stateless-Protocol Agent Context Routing (estudy: 'Stateless 프로토콜에서 Agent 문맥 식별 라우터') — S6

Route on (session_id, turn_id) as the Markov identity pair — not on connection identity, IP, or request source.

The Markov property (Puterman): future routing is independent of past connection history given the current session and turn state. This means:
- A subagent resumed via a new TCP connection is identical to one that never disconnected, if session_id + turn_id match.
- A subagent that reconnects mid-task should receive exactly the context it would have if the connection had never dropped.
- Do NOT use socket identity, gateway session ID, or request fingerprint as the primary routing key.

Concrete rule for ACP routing:
  route_key = f"{session_id}:{turn_id}"  # immutable; never changes across reconnects
  connection_id = <ephemeral>             # changes on reconnect; discard for routing

Side-effect logging: log the route_key (session_id:turn_id) in the identity delegation audit trail for every tool call with side effects. This enables attribution even when connection identity changes.

<!-- why: connection-identity routing breaks on network interruption, gateway restarts, and session migration — all common in long-horizon agent runs; Markov pair is stable across these events -->

