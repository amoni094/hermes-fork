# Cron PR follow-up prompt template

Use this as the starting structure for recurring PR maintenance jobs.

```
Monitor GitHub PR #<PR_NUMBER> in the <REPO_NAME> repo on branch <BRANCH_NAME>.

Each run:
1. Confirm the repo at <REPO_PATH> is on branch <BRANCH_NAME>.
2. Inspect PR #<PR_NUMBER> for:
   - new review comments
   - review decisions / requested changes
   - conversation comments
   - failing or pending CI via gh
3. If there are actionable requested changes, comments, or relevant failing checks, fix them in the repo.
4. After any code change, rerun the required verification commands:
   - <CHECK_1>
   - <CHECK_2>
   - <CHECK_3>
5. If fixes were made:
   - git add/commit with a concise message
   - push to the same branch
   - report exact changes and verification evidence
6. If nothing is actionable, reply exactly:
   No action needed for PR #<PR_NUMBER> at this check.

Constraints:
- Do not widen scope beyond PR-related issues.
- Use gh for PR inspection when available.
- Do not create or modify cron jobs.
- Be concise and evidence-based.
```

Notes:
- Fill in repo path, branch, PR number, and exact verification commands before scheduling.
- Tell the user the resulting cron job id immediately after creation so they can cancel it later.
