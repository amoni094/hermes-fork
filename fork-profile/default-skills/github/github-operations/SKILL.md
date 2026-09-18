---
name: github-operations
provides: [git_ops, web_extract]
triggers:
  - User needs GitHub auth or gh CLI setup
  - User wants to clone, fork, or manage remotes on a GitHub repo
  - PR lifecycle task: creating, reviewing, merging, or closing a pull request
  - Broad GitHub workflow task not covered by a more specific GitHub skill
description: >
  Use when: Broad GitHub workflow skill for authentication, repository bootstrap, PR lifecycle, code review, follow-up automation, and issue triage. Absorbs: github-auth, github-pr-workflow, github-code-review, github-pr-followup-automation, codebase-inspection (all archived). Not for picking which GitHub skill applies (use github). Not for agent-vs-agent branch conflict arbitration (use merge-reconciler).
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [github, gh, git, auth, clone, fork, pull-request, review, issues, workflow]
ssl_scheduling:
  triggers:
    - User needs GitHub auth or gh CLI setup
    - User wants to clone, fork, or manage remotes on a GitHub repo
    - PR lifecycle task — creating, reviewing, merging, or closing a pull request
    - Broad GitHub workflow task not covered by a more specific GitHub skill
  preconditions:
    - gh CLI installed (gh --version succeeds)
    - GitHub account with appropriate repository permissions
    - git configured with user name and email
  estimated_steps: 8
ssl_structural:
  tools_used: [terminal, web_extract, read_file, browser_navigate]
  subtasks:
    - Authenticate with 'gh auth login' if needed
    - Clone or fork the target repository
    - Create scoped branch and implement change
    - Open or review pull request via 'gh pr create / gh pr review'
    - Monitor CI status and resolve review feedback
ssl_logical:
  side_effects:
    - Clones or forks repositories to local disk
    - Creates branches, commits, and pull requests on GitHub
    - May push code to remote branches
    - Writes or reads ~/.config/gh/hosts.yml (gh auth state)
  resources:
    - Local git working tree
    - GitHub API (via gh CLI)
    - ~/.config/gh/hosts.yml
  risk_level: medium
related_skills:
  - verification-before-completion
  - plan
---

# GitHub Operations

Use this when the task involves GitHub as a workflow surface rather than a single narrow action: logging in, cloning or forking repositories, creating or reviewing pull requests, triaging issues, or automating follow-up around a PR.

## Core idea
Treat GitHub work as one lifecycle:
1. authenticate
2. locate or bootstrap the repository
3. make a scoped branch change
4. open or review the PR
5. monitor CI/review state
6. follow up until the branch is stable

## Absorbed skills
These skills were archived and their content merged here:
- `github-auth` — authentication and gh CLI setup
- `github-pr-workflow` — PR branch/commit conventions, body format, CI monitoring
- `github-code-review` — inline review comments on other people's PRs
- `github-pr-followup-automation` — automated follow-up after PR review

Counter-triggers: for issue creation/triage use `github-issues`; for carrying an issue to a PR use `github-issue-to-pr`; for automated multi-issue dispatch use `github-issue-agent`.

## When to use
- User needs GitHub auth or `gh` setup.
- User wants to clone, fork, or manage remotes.
- User wants to open, review, or follow up on a PR.
- User wants issue triage or repository hygiene around GitHub objects.
- User wants a single playbook that spans repo setup, review, and delivery.

- Authenticate first
- GitHub Models API rejects scoped tokens — GITHUB_TOKEN must have zero scopes (no permissions). For git operations use a separate PAT with `repo` scope; never reuse the models token.
- Prefer the narrowest working auth path for the environment.
- Verify `gh auth status` or the equivalent git credential path before assuming access.
- If a credential helper or token is missing, solve that before blaming GitHub APIs.
- When upgrading token scopes with `gh auth refresh -s repo`, expect a device-code flow that blocks on the CLI waiting for manual entry at https://github.com/login/device. If using browser tooling (e.g., CDP), be aware that browser session state does not persist across tool calls — if re-prompted, use a foreground terminal or fresh headed browser instead.

### 2) Bootstrap or inspect the repository
- Clone/fetch the repo.
- Confirm remotes, default branch, and working branch state.
- Read repo instructions before modifying anything.
- **Private repo access when browser is unavailable**: skip browser login entirely — `gh repo clone OWNER/REPO localdir` works directly once `gh auth status` confirms authentication. Check auth first; if authenticated, clone immediately without attempting web-based flows. The gh CLI uses the stored OAuth token and handles private repos transparently. Do not attempt browser-based GitHub login when the terminal already has a valid gh session.
- If the user wants a fork-based workflow, keep upstream and origin separate and explicit.
- For a brand-new local project that needs a GitHub home, check whether the target repo already exists before creating it.
- If the user wants the repository private, create it with an explicit private flag and verify privacy after push instead of assuming the default.
- If inviting members by email, use an organization-based repo. Personal repos require GitHub usernames (not emails) for the collaborator invite API; organizations accept email invitations directly. See `references/github-org-invitations.md` for the personal→org migration pattern.
- **Username lookup from email**: GitHub provides no public email→username API. Guess common patterns with `gh api users/<guess> --jq '.login,.name'` — try `firstnamelastname`, `firstname-lastname`, `f+lastname`. Once the username resolves, use repo-level collaborator invite (`PUT /repos/ORG/REPO/collaborators/USERNAME`) which only needs `repo` scope — not `admin:org`. Transfer personal repo to an existing org first if needed; then repo-level invite works without elevated token scope.

#### New private repository bootstrap
Use this when a local workspace already exists and the user wants it published as a new private GitHub repo.
1. Verify auth first with `gh auth status`.
2. Check whether the target repo already exists, e.g. `gh repo view OWNER/NAME`.
3. **Check where the git root actually is** before assuming the target directory owns its own repo:
   ```bash
   cd ~/target-dir && git rev-parse --show-toplevel
   ```
   If the output is a PARENT of the target dir (e.g. `/var/home/rainbow` when you expected `/var/home/rainbow/Religion`), the directory is inside a larger repo and does NOT have its own dedicated git history. In that case, run `git init` inside the target dir to create a fresh standalone repo — do NOT push the parent's history or use `gh repo create --source=.` from the parent.
4. Inspect local git state before publishing so you know whether you are creating a fresh root commit or pushing an existing history. Check `git ls-files | wc -l` — zero tracked files after init is normal for a fresh repo inside a parent .gitignore.
5. If the repo contains a large corpus, vector DB, or generated blobs, inspect the existing `.gitignore` before staging. Only commit: source scripts, ontology/config files, lightweight derived artefacts (HTML visualisers, summary JSONs), and README. Exclude: raw text corpora, chroma_db/, vector index files, logs, download state.
6. If the repo is an export of local app/agent config or operational state, sanitize before publishing:
   - exclude `.env`, auth/token stores, session DBs, raw logs, and chat history
   - prefer a redacted config snapshot over copying the entire state directory
   - redact delivery/origin metadata in scheduler snapshots and similar files
   - add a `.gitignore` that blocks secret/state files in case future edits happen from the same repo
7. Create and push in one step with `gh repo create OWNER/NAME --private --source=. --remote=origin --push`.
8. Verify the result with `gh repo view OWNER/NAME --json name,visibility,isPrivate,url,defaultBranchRef`.
9. Re-check `git status --short --branch` and `git remote -v` so the final report names the tracked branch and remote, not just the GitHub URL.
10. Open in browser with `terminal(command="xdg-open 'https://github.com/OWNER/REPO'", background=true)` — do NOT use `&` in the command string; use `background=true` on the terminal call instead.

Pitfalls:
- Do not initialize git inside a live state directory like `~/.hermes/` just because the user asked for a config backup. Create a dedicated export workdir/repo, copy only sanitized artifacts into it, and then publish that repo.
- `xdg-open url &` in a terminal command string is rejected by the runner — use `terminal(background=True)` without the `&`.

### 3) PR lifecycle
- Create a branch with a scoped change.
- Commit only intended files.
- Open the PR or locate the existing PR.
- Re-read review comments after every push.
- Separate branch regressions from baseline repository failures.
- Keep the PR branch current with `main` via rebase. Rebase before resuming work and before pushing follow-up fixes.
- **Pinned-SHA force-with-lease (safe rebase push):** Before rebasing a pushed PR branch, record the current remote PR-head SHA, then pin it in the lease to prevent silent weakening:
  ```bash
  PR_HEAD=$(git rev-parse origin/<pr-branch>)  # record before any fetch
  git fetch upstream main
  git rebase upstream/main
  git push --force-with-lease=refs/heads/<pr-branch>:$PR_HEAD <pr-remote> HEAD:refs/heads/<pr-branch>
  ```
  If the lease is rejected, stop: fetch the remote branch, inspect new commits, incorporate them, redo the rebase, record the new SHA, and retry. An unguarded `--force` or unqualified `--force-with-lease` can silently discard collaborator commits if a background fetch moved the remote-tracking ref before the push. If the branch is shared, coordinate with maintainers instead.

### 4) Code review and follow-up
- Review the diff and surrounding context, not just the comment thread.
- Validate review comments against the live branch state.
- Keep generated or unrelated files out of follow-up commits.
- If the user wants automation, use a follow-up loop that checks for new comments, reruns CI, and reports only the new actionable items.

### 5) Issues
- Use issues for triage, scope, and lightweight tracking.
- Keep issue work separate from branch patching unless the issue explicitly drives a PR.
- When an issue references a PR, verify whether the live branch or the historical PR snapshot is the source of truth.

## Changing repo visibility
To change a repo's visibility:
```
gh repo edit OWNER/REPO --visibility public --accept-visibility-change-consequences
gh repo edit OWNER/REPO --visibility private --accept-visibility-change-consequences
```
Pitfall: `--yes` is NOT a valid flag for `gh repo edit`. The correct acknowledgement flag is
`--accept-visibility-change-consequences`. Without it the command exits with an error.
Verify after: `gh repo view OWNER/REPO --json name,visibility --jq '[.name,.visibility]'`

## Listing repos: personal vs org namespace
`gh repo list` (no argument) lists repos under the authenticated user's personal account only.
To list repos under a GitHub org: `gh repo list <org-name> --limit N`
When a user names a repo that isn't found under their personal account, always check relevant
org namespaces before concluding the repo doesn't exist.

## Practical rules
- Always confirm the live ref/branch state before concluding a PR is fixed.
- Do not assume historical PR metadata still matches the current branch tip.
- Do not widen scope to unrelated repo failures.
- Do not push without verifying the branch contains only the intended changes.
- Do not confuse auth problems with repository or CI failures.

## Ouroboros integration
- Treat `toolbox run ouroboros qa` as an extra QA pass for GitHub-facing artifacts, not a replacement for repo-native checks.
- Use it after you have real evidence in hand: clean diff review, targeted tests/builds, and any repo-required preflight.
- Good targets: PR descriptions, review summaries, workflow YAML, generated patch files, and captured test output.
- Prefer file-path inputs when possible so the QA run is reproducible from disk.
- If the local Ouroboros runtime is not authenticated or its configured backend is unavailable, treat that as an optional-tool blocker and continue with executable verification; report the skipped QA pass explicitly.
- Example commands:
  - `toolbox run ouroboros qa .github/workflows/ci.yml -t code -q "Workflow YAML is safe, scoped, syntactically plausible, and matches the intended GitHub Actions behavior."`
  - `toolbox run ouroboros qa /tmp/pr-body.md -t document -q "PR summary is accurate, complete, and consistent with the verified branch state."`
- If Ouroboros disagrees with repo-native evidence, report the disagreement explicitly and trust executable verification over prose QA.
- See `references/ouroboros-qa.md` for reusable command shapes and pass-bar examples.

## Repository automation and CI hardening
When the task involves GitHub-hosted repository automation rather than application code, inspect the workflows themselves before proposing changes.

Preferred low-friction hardening moves:
- set top-level workflow permissions to read-only by default
- grant write permission only on the exact job that must push or mutate repo state
- pin third-party actions to immutable commit SHAs rather than floating tags
- match the target repository's existing workflow conventions before introducing new ones (for example runner labels such as `ubuntu-2404-2core`, action pinning style, artifact naming, and whether the repo installs its own CLI/tool from a local script)
- add `concurrency` to workflows that auto-commit or update generated files
- add explicit branch/event guards for write-capable jobs
- for new workflow files, narrow `push`/`pull_request` triggers with `branches:` and `paths:` so the workflow only auto-runs when its own files or the shared templates/config it depends on change
- for `workflow_dispatch` inputs that later reach shell commands, add a dedicated validation/sanitization step first, export the cleaned value through `GITHUB_ENV`, and make later steps consume only that cleaned variable
- after adding a validation step, read the downstream job steps back to confirm you did not accidentally reintroduce the raw `${{ github.event.inputs.* }}` value in a later step-local `env:` block
- if CI contains inline validation logic that duplicates a repo script, prefer calling the repo-local validator/tool directly so local and CI behavior cannot drift
- when frontmatter or workflow metadata is YAML, prefer `yaml.safe_load` over regex parsing if a parser is available
- for small private config/export repositories, prefer a single read-only validation workflow over a broad CI matrix; see `references/private-export-validation-workflow.md` for a minimal pattern using path filters, pinned action SHAs, local YAML parse verification, and post-verification amend guidance when generated artifacts change again

For concrete workflow-authoring notes, see `references/github-actions-workflow-authoring.md`.

### Exporting operational state (Hermes config, agent snapshots, policy repos)

When exporting live operational state (e.g., Hermes configuration, veto rules, cron jobs) to a private repo for version control and audit:

1. **Sanitize secrets** — use a script that blanks api_key, token, password, and auth fields (see `references/hermes-config-export-and-push.md` for a full template).
2. **Validate the export** — run a separate validator that checks for leftover secrets and required metadata before pushing.
3. **Resolve supporting-file sync issues** — ensure README.md and .gitignore remain consistent with the validator's expectations.
4. **Commit with full context** — include what changed, why, and validation evidence in the commit message.

For a worked example and troubleshooting guide, see `references/hermes-config-export-and-push.md`.

Common pitfall:
- Do not maintain two validators with different rules (for example, a local script and a separate inline Actions regex validator). This causes false positives, contributor confusion, and security/quality blind spots.

See also: `references/github-actions-hardening.md`, `references/private-repo-bootstrap.md`, `references/religion-repo-bootstrap-2026-08-06.md` (worked example: corpus project with home-dir git trap + corpus exclusions)

## Verification
- Auth works.
- Repo state is known.
- Branch/PR identity is verified.
- Review or issue state is re-queried after changes.
- For CI/workflow hardening, read back the changed workflow files and run the canonical local validator/tool.
- When the change set is mostly YAML workflows/templates, parse the edited files locally with `yaml.safe_load`/PyYAML as a cheap syntax gate even if you cannot run the remote CI platform end to end.
- After input-hardening edits, verify both the validation step and the later consumer step so the cleaned variable is the one actually used.
- **For operational state exports** (Hermes config, cron snapshots, etc.): run sanitize and validate scripts before commit/push (see `references/hermes-config-export-and-push.md`).
- Final report names the exact PR, branch, or issue state that was observed.

## Preflight before commit/push
When a coding task ends with a commit or push, do a quick repo preflight before mutating git state:
1. inspect `git status --short` so you know the exact tracked/untracked scope
2. inspect `git diff --stat` and, when needed, targeted `git diff -- <files>` so only intended files are included
3. run the repo quality gates that actually apply (`npm run build`, `npm run lint`, tests, project validators)
4. if it is a local web app, prefer a lightweight runtime probe as well: start the dev/preview server, then verify localhost serves HTML with a shell HTTP request if browser tooling is flaky
5. for browser-compatibility or legacy-bundle changes in Vite/SPA repos, inspect the served HTML as part of preflight and confirm the expected loader path is present (for example both the modern module script and the `nomodule` / legacy entry tags when `@vitejs/plugin-legacy` is enabled)
6. if a refresh or generation step touched multiple derived files, inspect the generated diff and stage the intended generated artifacts explicitly so the commit stays scoped to the requested change
7. if you ran package-manager commands during verification (`npm install`, `pnpm install`, etc.), inspect lockfile and manifest diffs before staging. Revert incidental lockfile-only churn when it does not represent an intended dependency/runtime change.
8. for scraped/generated ranking surfaces, sample the regenerated output for source quality before commit. Prefer direct per-profile artifacts over generic party/channel fallback if the broader fallback pollutes a person-level summary with irrelevant content.
9. only then `git add` the intended paths, commit, and push

Pitfall:
- Do not rely on a successful build alone when the task explicitly asked for runtime verification. For local dashboards or SPAs, a served-HTML check is a cheap extra guard even if richer browser automation is unavailable.

## Notes
More specific GitHub workflows that fit under this umbrella include auth setup, repository management, PR workflow, code review, PR follow-up automation, and GitHub Actions hardening for repo-maintenance workflows.
## Hermes Config Export and Push Pattern (from hermes-config-export-and-push.md)

Workflow for exporting local Hermes configuration to a private GitHub repo with full sanitization and validation.

**Steps:**
1. `python3 scripts/sanitize_config.py` — blanks secrets (api_key, token, password, bearer_token, client_secret, cookie, etc.); preserves safe keys like `access_token_env`, `max_tokens`.
2. `python3 scripts/validate_repo.py` — checks YAML parses, no non-empty secret keys remain, README contains sanitization statement, veto YAML well-formed.
3. Commit with full context (what changed, why, validation evidence).
4. Push.

**Common validation failures:**
- "still contains non-empty sensitive-looking keys" → a new config section added a non-allowlisted key; either blank it in sanitize script or extend the allowlist.
- "README.md must contain a sanitization statement" → add one line; validator checks for presence, not exact wording.

**Single-validator rule:** Do NOT maintain two validators with different rules (local script + inline Actions regex). This causes false positives and security blind spots.

## Private Export Validation Workflow (from private-export-validation-workflow.md)

For small private repos storing sanitized operational/config exports, add a minimal GitHub Actions workflow:
- Triggers: `push`, `pull_request`, optional `workflow_dispatch` — narrowed to main branch and relevant paths.
- Top-level `permissions: contents: read`.
- `concurrency: cancel-in-progress: true` to avoid redundant runs.
- Pin third-party actions to immutable commit SHAs.
- Job steps: checkout (SHA-pinned) → setup-python (SHA-pinned) → install only validator dep (e.g. PyYAML) → `python -m compileall scripts` → `python scripts/validate_repo.py`.

**Generated-artifact pitfall:** If the repo contains generated reports from live local state, a post-commit verification run may mutate them again. After verification rerun: check `git status --short`; if only expected generated artifacts changed, amend the commit before push. Do not claim repo is clean until that second check is done.

### Async org transfer: polling + membership verification
Org transfers are async and take 5-10s. After initiating, poll until membership is confirmed:
```bash
# Wait for transfer to complete
for i in $(seq 1 10); do
  status=$(gh api orgs/ORG_NAME/memberships/YOUR_USERNAME --jq '.state' 2>/dev/null)
  [ "$status" = "active" ] && echo 'Transfer confirmed' && break
  sleep 2
done
```
Verify role after transfer: `gh api orgs/ORG_NAME/memberships/YOUR_USERNAME --jq '.role'`
Expected: member or admin. If pending after 30s, check if original owner accepted the invitation.

### Post-push workflow registration verification
After pushing a new workflow file, verify GitHub has registered it:
```bash
gh workflow view WORKFLOW_NAME.yml --yaml  # confirms file registered
gh run list --workflow WORKFLOW_NAME.yml --limit 3  # confirms it has run
```
If workflow view returns not found, the file may not be in the default branch yet, or the workflow name in the YAML does not match the filename.

## Reference files

- `references/collaborator-invite-by-email.md` — Finding a GitHub Username from an Email Address
- `references/fable5-audit-and-config-export-workflow.md` — Fable-5 Audit + Config Export Workflow for GitHub
- `references/github-models-token-incompatibility.md` — GitHub Models API + Git Operations Token Incompatibility
- `references/local-project-repo-bootstrap.md` — Local Project Repo Bootstrap Pattern
- `references/local-patches-on-upstream-repos.md` — Updating repos with local patches on top of upstream: commit-first, merge/rebase, conflict resolution, test assertion broadening, and known always-excluded repos
