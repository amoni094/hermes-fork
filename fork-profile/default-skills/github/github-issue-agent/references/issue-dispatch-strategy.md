# GitHub Issue Dispatch Strategy

Guidance on when and how to route issues to agents, and what issue characteristics predict success.

## Suitable Issues (Agent-Ready)

Agents do best with issues that have:

- **Clear acceptance criteria**: "implement function X that does Y"
- **Well-scoped**: single file, single subsystem, < 200 lines of code expected
- **Good examples**: issue includes a code sample or before/after
- **Non-blocking**: not waiting on external review, API changes, or upstream releases
- **Isolated**: doesn't interact with many other components
- **Self-contained test**: can verify the fix locally without external services

**Labels to use**: `agent-ready`, `good-first-issue`, `scope:small`, `type:feature`, `type:bug-fix`

## Risky Issues (Not Agent-Ready)

Avoid routing to agents when:

- **Ambiguous acceptance**: "improve performance" or "make it better"
- **Large scope**: > 3 files, > 500 lines of change expected
- **Architecture decision**: "refactor X subsystem"
- **Blocked**: waiting on maintainer decision, API design, blocked by another issue
- **Needs design review**: requires architectural discussion before implementation
- **External dependency**: needs API changes, new service integration, or upstream change
- **No test path**: hard to verify locally, requires integration test or staging environment

**Labels to avoid**: `blocked`, `needs-design`, `needs-review`, `in-progress`, `wontfix`, `duplicate`, `type:epic`, `scope:large`

## Dispatch Decision Tree

```
Is the issue well-scoped?
├─ NO → label it good-first-issue or skip
└─ YES
   ├─ Does it have clear acceptance criteria?
   │  ├─ NO → ask for clarification in the issue first
   │  └─ YES
   │     ├─ Is it isolated (single file or subsystem)?
   │     │  ├─ NO → large refactor? not agent-ready yet
   │     │  └─ YES
   │     │     ├─ Can you verify the fix locally?
   │     │     │  ├─ NO → needs integration test setup, skip for now
   │     │     │  └─ YES → AGENT READY
   │     │     └─ Add label: agent-ready
   │     └─ Is there a code example or test case included?
   │        ├─ NO → attach one before dispatch
   │        └─ YES → helps agent succeed
```

## Labeling Strategy

Maintain these labels on your repo:

| Label | When | Effect |
|-------|------|--------|
| `agent-ready` | issue is scoped, clear, isolated | include in `--label agent-ready` filter |
| `good-first-issue` | scoped but maybe a bit educational | lower dispatch priority, good for onboarding |
| `blocked` | waiting on decision, review, or external change | exclude from dispatch |
| `scope:small` | < 100 lines expected | dispatch immediately |
| `scope:large` | > 500 lines expected | don't route to agents |
| `type:bug-fix` | isolated fix to existing feature | agent friendly |
| `type:feature` | new small feature | agent friendly if scoped |
| `type:refactor` | restructuring | agent risky, needs design first |

## Dispatch Patterns

### Pattern 1: Single-Issue Dispatch (Interactive)

Best for: one issue you want fixed now, interactive oversight.

```bash
# Find the issue
gh issue list --repo OWNER/REPO --json number,title | head -5

# Dispatch it
python3 ~/.hermes/scripts/issue-to-agents.py \
  --repo OWNER/REPO \
  --issue 42 \
  --execute

# Wait for completion
python3 ~/.hermes/scripts/hermes-hud.py --watch
```

### Pattern 2: Batch by Label (Low Oversight)

Best for: multiple small issues, let agents work in parallel.

```bash
# Create 5 worktrees and dispatch agents
python3 ~/.hermes/scripts/issue-to-agents.py \
  --repo OWNER/REPO \
  --label agent-ready \
  --limit 5 \
  --execute

# Check results later
gh pr list --repo OWNER/REPO --state open
```

### Pattern 3: Dry-Run First (Safest)

Always preview what will be dispatched:

```bash
# See what would happen, no dispatch
python3 ~/.hermes/scripts/issue-to-agents.py \
  --repo OWNER/REPO \
  --label agent-ready \
  --limit 5 \
  --dry-run
```

Output shows:
- Issues to dispatch
- Worktrees to create
- Prompts that will be sent

Then add `--execute` when satisfied.

## Common Issues & Fixes

**Issue**: Agent dispatched but issue is confusing, fix is wrong.
→ Next time, require the issue to have:
  - Runnable reproduction case
  - Expected vs. actual behavior
  - Link to related code or PR

**Issue**: Worktree add fails (branch exists).
→ Before bulk dispatch: `git worktree prune && git branch -D issue-*-agent` (careful!)

**Issue**: All agents complete but PRs need manual rebasing.
→ Default branch moved, PRs are stale. Use `gh pr update` or rebase in worktrees before pushing.

**Issue**: Agents are dispatched but one seems stuck.
→ Check logs: `hermes doctor` then review the agent's ledger entry in `~/.hermes/logs/hermes-task-ledger.jsonl`

## Optimization: Parallel Dispatch Limits

Dispatch limits per session:
- **1–2 agents**: interactive, you'll notice if they go wrong
- **3–5 agents**: moderate parallelism, you can still debug if needed
- **6+ agents**: high parallelism, results are harder to audit, QA overhead increases

Recommendation: start with 3–5, audit the PRs, then scale up if quality is high.

## See Also

- **GitHub Operations**: full skill for auth, repo setup, branch/PR management
- **Subagent-Driven Development**: patterns for multi-agent work with ledger tracking
