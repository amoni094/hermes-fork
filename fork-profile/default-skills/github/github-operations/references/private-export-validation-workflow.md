# Private export validation workflow

Use this pattern for small private repositories that store sanitized operational/config exports rather than application code.

## Goal
Add a low-friction GitHub Actions workflow that verifies the export stays sanitized without introducing unnecessary write permissions or broad CI scope.

## Recommended workflow shape
- trigger on `push`, `pull_request`, and optional `workflow_dispatch`
- narrow `branches:` to the main branch used by the repo
- narrow `paths:` to only the workflow file, exported config/snapshot files, key docs, and validator scripts
- set top-level `permissions:` to `contents: read`
- add `concurrency:` with `cancel-in-progress: true`
- pin third-party actions to immutable commit SHAs
- keep the job single-purpose: install the minimum dependency, compile scripts, run the canonical local validator

## Good minimal job
1. `actions/checkout` pinned by SHA
2. `actions/setup-python` pinned by SHA
3. install only the validator dependency (for example `PyYAML` when the repo-local validator structurally parses YAML)
4. `python -m compileall scripts`
5. `python scripts/validate_repo.py`

## Verification pattern
Before committing or pushing the workflow:
- parse the workflow locally with `yaml.safe_load`
- confirm `permissions: {contents: read}`
- confirm `concurrency` exists
- rerun the repo-local validator after adding the workflow
- after push, confirm the workflow is registered remotely with `gh workflow view <name> --yaml`
- check `gh run list --workflow <name> --limit 3` to confirm the triggered run exists

## Generated-artifact pitfall
If the repo contains generated reports derived from live local state, a post-commit verification run may mutate them again. After the verification rerun:
- check `git status --short`
- if only expected generated artifacts changed, stage them and amend the commit before push
- do not claim the repo is clean until that second check is done

## When to keep a small non-stdlib dependency
If the validator needs structural parsing of nested YAML exports, keep `PyYAML` rather than downgrading to regex/text checks. For config-export repos, correctness of nested-key inspection is usually worth the tiny install step in CI.
