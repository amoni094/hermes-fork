---
name: github-issue-agent
description: >
  Use when routing open GitHub issues to isolated Hermes subagents, one agent per issue, each in its own git worktree. Agents fix the issue, push a branch, open a PR, and comment on the issue. Trigger on "dispatch issues", "route issues to agents", "fix issues automatically", or "issue-to-agent".
triggers:
  - dispatch issues
  - route issues to agents
  - fix issues automatically
  - issue-to-agent
  - assign issues to subagents
related_skills:
  - github-issues
  - github-operations
  - dispatching-parallel-agents
---

# GitHub Issue-to-Agent Routing

Implements the "agent takes an issue like a teammate" pattern. Each open issue
becomes a scoped subagent task with worktree isolation.

## Workflow

1. Fetch open issues via `gh issue list`
2. Create a git worktree per issue under `~/hermes-worktrees/OWNER_REPO/issue-N/`
3. Dispatch one Hermes subagent per issue with a self-contained prompt
4. Each agent: implements the fix, commits, pushes branch, opens PR, comments on issue

## Step-by-step

### 1. Enumerate issues

```bash
gh issue list --repo OWNER/REPO --state open --json number,title,body,labels --limit 10
```

Filter by label for scoped runs:
```bash
gh issue list --repo OWNER/REPO --label "agent-ready" --limit 5
```

### 2. Use the helper script

```bash
python3 ~/.hermes/scripts/issue-to-agents.py \
  --repo OWNER/REPO \
  --label agent-ready \
  --local-repo ~/path/to/local/clone \
  --limit 5 \
  --dry-run
```

Remove `--dry-run` / add `--execute` when ready to dispatch.

### 3. Manual dispatch (single issue)

For each issue, delegate a subagent:

```
delegate_task(
  goal="Fix GitHub issue #N: <title>. Work in worktree ~/hermes-worktrees/OWNER_REPO/issue-N. Commit changes, push branch issue-N-agent, open a PR referencing issue #N, post PR link as comment on the issue.",
  context="Repo: OWNER/REPO. Issue body: <body>. Local worktree already created.",
  toolsets=["terminal", "file", "web"]
)
```

### 4. After dispatch

- HUD shows in-flight agents: `python3 ~/.hermes/scripts/hermes-hud.py`
- Agents complete independently; ledger entries appear in `~/.hermes/logs/hermes-task-ledger.jsonl`
- Check PRs: `gh pr list --repo OWNER/REPO`

## Pitfalls

- **Label filter**: add a label like `agent-ready` or `good-first-issue` to avoid routing
  complex/blocked issues. Don't dispatch everything blindly. See `references/issue-dispatch-strategy.md`
  for a decision tree.
- **Worktree limit**: git limits open worktrees. Keep `--limit` under 10 at a time.
- **Branch collision**: if a branch `issue-N-agent` already exists, the worktree add will fail.
  Run `git worktree prune` in the repo first.
- **Delegation depth**: each dispatched agent is depth=1. They should NOT re-delegate further —
  pass `role='leaf'` explicitly.
- **Scope**: only dispatch issues with enough context. Include the full issue body in the prompt;
  the subagent has no memory of your session.

## Verification

After agents complete:
```bash
gh pr list --repo OWNER/REPO --state open
gh issue list --repo OWNER/REPO --state open --label agent-ready
python3 ~/.hermes/scripts/hermes-hud.py
```
