# GitHub Actions workflow authoring and hardening

Use this when adding or tightening workflow files in a GitHub repository.

## Practical authoring sequence
1. Read one or two existing workflows in the target repo first.
2. Copy the repo's conventions before inventing your own:
   - runner labels
   - SHA pinning style for actions
   - artifact naming/layout
   - local installer/helper scripts under `contrib/`, `scripts/`, or similar
3. Add the new workflow with the narrowest useful triggers.
4. If the workflow accepts `workflow_dispatch` input, validate and sanitize it in a dedicated shell step.
5. Export the cleaned value with `GITHUB_ENV` and make later steps consume only that cleaned variable.
6. Read the workflow back after editing to ensure no later `env:` block rebinds the raw `${{ github.event.inputs.* }}` value.
7. Parse the workflow YAML locally before commit.

## Good defaults
- top-level `permissions: contents: read`
- `concurrency` for scheduled or artifact-producing jobs
- `push`/`pull_request` scoped with `branches:` and `paths:` when the workflow should only react to its own files or shared templates
- prefer repo-local helper scripts over duplicating install/validation logic inline

## Input-validation patterns
- image refs: allow a constrained character set before passing to shell
- repository URLs: require the specific expected host/path form when the workflow is repo-scoped
- filesystem paths from dispatch input: reject absolute paths and parent traversal
- namespace-like identifiers: validate against the platform's naming regex
- secrets-backed config blobs: fail early if the secret is empty before writing files

## Easy mistake to catch
After adding a validator step, a later step may still contain something like:
`env: VALUE: ${{ github.event.inputs.value }}`
That silently bypasses the sanitized value. Read back the downstream step and remove the raw rebind.

## Local proof options when remote CI is unavailable
- parse workflow YAML with PyYAML
- read back the changed workflow files
- diff only the workflow/template/doc paths you intended to touch
- if the workflow shells out to a repo-local script, confirm the script exists and its usage matches the new invocation
