---
name: github-operations
description: Broad GitHub workflow skill for authentication, repository bootstrap, PR lifecycle, code review, follow-up automation, and issue triage.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [github, gh, git, auth, clone, fork, pull-request, review, issues, workflow]
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

## When to use
- User needs GitHub auth or `gh` setup.
- User wants to clone, fork, or manage remotes.
- User wants to open, review, or follow up on a PR.
- User wants issue triage or repository hygiene around GitHub objects.
- User wants a single playbook that spans repo setup, review, and delivery.

- Authenticate first
- Prefer the narrowest working auth path for the environment.
- Verify `gh auth status` or the equivalent git credential path before assuming access.
- If a credential helper or token is missing, solve that before blaming GitHub APIs.
- When upgrading token scopes with `gh auth refresh -s repo`, expect a device-code flow that blocks on the CLI waiting for manual entry at https://github.com/login/device. If using browser tooling (e.g., CDP), be aware that browser session state does not persist across tool calls — if re-prompted, use a foreground terminal or fresh headed browser instead.

### 2) Bootstrap or inspect the repository
- Clone/fetch the repo.
- Confirm remotes, default branch, and working branch state.
- Read repo instructions before modifying anything.
- If the user wants a fork-based workflow, keep upstream and origin separate and explicit.
- For a brand-new local project that needs a GitHub home, check whether the target repo already exists before creating it.
- If the user wants the repository private, create it with an explicit private flag and verify privacy after push instead of assuming the default.

#### New private repository bootstrap
Use this when a local workspace already exists and the user wants it published as a new private GitHub repo.
1. Verify auth first with `gh auth status`.
2. Check whether the target repo already exists, e.g. `gh repo view OWNER/NAME`.
3. Inspect local git state before publishing so you know whether you are creating a fresh root commit or pushing an existing history.
4. If the repo is an export of local app/agent config or operational state, sanitize before publishing:
   - exclude `.env`, auth/token stores, session DBs, raw logs, and chat history
   - prefer a redacted config snapshot over copying the entire state directory
   - redact delivery/origin metadata in scheduler snapshots and similar files
   - add a `.gitignore` that blocks secret/state files in case future edits happen from the same repo
5. Create and push in one step with `gh repo create OWNER/NAME --private --source=. --remote=origin --push`.
6. Verify the result with `gh repo view OWNER/NAME --json name,visibility,isPrivate,url,defaultBranchRef`.
7. Re-check `git status --short --branch` and `git remote -v` so the final report names the tracked branch and remote, not just the GitHub URL.

Pitfall:
- Do not initialize git inside a live state directory like `~/.hermes/` just because the user asked for a config backup. Create a dedicated export workdir/repo, copy only sanitized artifacts into it, and then publish that repo.

### 3) PR lifecycle
- Create a branch with a scoped change.
- Commit only intended files.
- Open the PR or locate the existing PR.
- Re-read review comments after every push.
- Separate branch regressions from baseline repository failures.

### 4) Code review and follow-up
- Review the diff and surrounding context, not just the comment thread.
- Validate review comments against the live branch state.
- Keep generated or unrelated files out of follow-up commits.
- If the user wants automation, use a follow-up loop that checks for new comments, reruns CI, and reports only the new actionable items.

### 5) Issues
- Use issues for triage, scope, and lightweight tracking.
- Keep issue work separate from branch patching unless the issue explicitly drives a PR.
- When an issue references a PR, verify whether the live branch or the historical PR snapshot is the source of truth.

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

Common pitfall:
- Do not maintain two validators with different rules (for example, a local script and a separate inline Actions regex validator). This causes false positives, contributor confusion, and security/quality blind spots.

See also: `references/github-actions-hardening.md`, `references/private-repo-bootstrap.md`

## Verification
- Auth works.
- Repo state is known.
- Branch/PR identity is verified.
- Review or issue state is re-queried after changes.
- For CI/workflow hardening, read back the changed workflow files and run the canonical local validator/tool.
- When the change set is mostly YAML workflows/templates, parse the edited files locally with `yaml.safe_load`/PyYAML as a cheap syntax gate even if you cannot run the remote CI platform end to end.
- After input-hardening edits, verify both the validation step and the later consumer step so the cleaned variable is the one actually used.
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
