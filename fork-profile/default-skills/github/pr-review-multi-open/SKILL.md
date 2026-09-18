---
name: pr-review-multi-open
version: 1.2.0
author: Hermes Agent
description: "Use when reviewing all open PRs for comments and fixes."
keywords:
- pr
- review
- multi-pr
- followup
- gh
- adversarial
platforms:
- linux
---

# Multi-PR Open Review and Fix Pass

Use when the user asks to go through all open/unmerged PRs and respond to comments or fix issues.

## Step 1: Enumerate all open PRs

```bash
gh pr list --author <handle> --state open --json number,title,url,reviewDecision,comments
```

Note PR numbers. Identify which branch is deepest in the inheritance chain (e.g., if
branch C was cut from B which was cut from A, C inherits everything).

## Step 2: Mine BOTH comment surfaces per PR

`gh pr view --comments` shows only top-level conversation comments. Inline code-review
threads require a separate GraphQL query:

```bash
gh api graphql -f query='
  query($owner:String!,$repo:String!,$number:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$number){
        reviewThreads(first:50){
          nodes{
            id
            isResolved
            comments(first:10){ nodes{ author{login} body path line } }
          }
        }
      }
    }
  }' -F owner=OWNER -F repo=REPO -F number=N
```

Run this for every open PR. Skip bot-authored comments (automated diagram tools, CI
reporters). Only human or code-review-bot inline threads are actionable.

## Step 3: Check for architecture doc gate

If the repo's AGENTS.md requires a `docs/architecture/` slice before new capabilities
can land, write the architecture docs FIRST -- before dispatching any code fixes.
Automated reviewers flag this on every PR until satisfied.

Required slice content:
- Each new module: what it owns / must-not-own
- Integration boundaries: what calls it, what it calls
- Validation contract: which test files cover it, key invariants

Match the existing slice format in `docs/architecture/` exactly.

## Step 4: Deduplicate findings across PRs

When the same bug appears on multiple open PRs on different base branches, apply the
fix ONCE on the deepest branch that all others inherit from. Do not patch each branch
separately -- the fix propagates through git inheritance.

## Step 5: Dispatch fixes in parallel batches

Group fixes by file surface (not by PR) to avoid write conflicts between subagents.
Each subagent gets a distinct set of files with no overlap.

Mandatory per-subagent instructions:
- Explicit `Do NOT git commit` (orchestrator commits after all fixes land)
- Output contract: write `/tmp/fix_<batch>_result.json`:
  `{"status": "pass"|"fail", "test_count": N, "fixes_applied": [...], "notes": ""}`

## Step 6: Verify then commit

After all subagent results arrive:
1. Full test suite run (not just targeted tests) -- cross-fix regressions are common.
2. PYTHONHASHSEED stability check if any enum-involving modules were touched.
3. Commit with structured message listing each reviewer finding addressed.
4. Push the deepest branch (contains all fixes via inheritance).

## Step 7: Reply to and resolve all reviewer threads in bulk

After fixes are pushed, both reply to and resolve every unresolved thread.
Batch all operations into one Python loop — never one API call per thread.

### Reply (add comment to thread)
```python
import subprocess, json

REPLIES = {
    "PRRT_kwDORF5oBs6iwbW0": (2027, "Fixed in bb9d0a3. <one-sentence what changed>."),
}
OWNER, REPO = "org", "repo"
for thread_id, (pr_num, body) in REPLIES.items():
    result = subprocess.run(
        ["gh", "api", "-X", "POST",
         f"repos/{OWNER}/{REPO}/pulls/{pr_num}/comments/{thread_id}/replies",
         "-f", f"body={body}"],
        capture_output=True, text=True
    )
    print("OK" if result.returncode == 0 else f"FAIL: {result.stderr[:100]}", thread_id)
```

### Resolve (mark thread resolved via GraphQL mutation)
```python
def resolve_thread(thread_id):
    mutation = '''
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { id isResolved }
    }
  }'''
    r = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={mutation}", "-f", f"threadId={thread_id}"],
        capture_output=True, text=True
    )
    return r.returncode == 0
```

Thread reply content: commit SHA + one sentence on the fix mechanism.
Fetch thread IDs via the GraphQL query in Step 2 (node `id` field).

## Step 8: Recursive adversarial pass until saturation

After committing and pushing, dispatch cold adversarial reviewers against the changed files.
Run at least 2 reviewers in parallel — cold subagents with no knowledge of the fix intent.

Each reviewer writes findings to `/tmp/adversarial_<round>_<batch>.json`:
```json
{"verdict": "pass|conditional_pass|fail", "issues": [{"severity": "CRITICAL|HIGH|MEDIUM|LOW", ...}]}
```

Apply all CRITICAL and HIGH findings. Apply MEDIUM findings that are real bugs (not style).
Skip LOW unless they are precision bugs (wrong formula, off-by-one with mathematical consequence).

Repeat adversarial pass after each fix round. Saturated when:
- Verdict = `pass` from both reviewers, OR
- Only LOW/style issues remain across two consecutive rounds

Throttle: if a fix in round N introduces a regression caught in round N+1, that is an
osscillation signal — step back and find the structurally correct solution rather than
patching back and forth between two wrong implementations.

## Pitfalls

- `gh pr view --comments` and GraphQL `reviewThreads` are separate surfaces. An empty
  `--comments` output does NOT mean no review threads exist. Always run both.
- Architecture doc mandates in AGENTS.md are flagged by automated reviewers on every
  PR until satisfied. Write the slice early, not after reviewer comments arrive.
- Pytest output lines containing the word 'error' are test NAMES, not collection errors.
  To find real collection failures: `pytest --co -q 2>&1 | grep '^ERROR '`. A subagent
  reporting N collection errors may mean N test names contain 'error' -- verify by running
  `pytest --co -q` and checking if the error lines begin with 'ERROR' (collection) vs appear
  in test names (benign).
- Subagents writing to overlapping files cause non-deterministic merge conflicts. Group
  tasks by distinct file surfaces before dispatching.
- When 3+ PRs share common ancestry, a fix to the deepest branch covers all; do not
  apply the same patch at multiple branch levels.
- Do NOT commit between parallel fix batches -- wait until all subagents finish and
  the full suite passes. Intermediate commits lock in partial-fix state.
- strands/optional-dep collection errors: if `pytest tests/` hits 80+ collection ERRORs
  before running any test, check if they all trace to a missing optional package (e.g.
  `strands`, `boto3`). Run `pytest tests/<changed_dirs>/` to avoid the noise entirely.
- Reviewer thread replies do NOT automatically resolve threads. Always call
  `resolveReviewThread` mutation separately after replying — replied-to threads that
  remain unresolved will continue to block PR approval in many repo policies.
- New reviewer threads can appear between adversarial passes on the same PR (automated
  reviewers re-scan on push). Re-check all PRs for unresolved threads after each push.
