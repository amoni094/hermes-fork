# GitHub Actions hardening for repo-maintenance workflows

Use this pattern when a repository has automation that validates content, regenerates derived files, or writes small housekeeping commits back to the repo.

## Low-friction hardening checklist

1. Default to least privilege at workflow top level:
   ```yaml
   permissions:
     contents: read
   ```
2. Grant write only to the specific job that pushes commits:
   ```yaml
   jobs:
     update-index:
       permissions:
         contents: write
   ```
3. Pin third-party actions to immutable SHAs, not floating tags.
4. Add `concurrency` to auto-write workflows to avoid overlapping bot commits.
5. Add explicit job guards such as `if: github.ref == 'refs/heads/main'` for branch-scoped writers.
6. Prefer a repo-local validation tool over duplicated inline workflow scripts.
   - Example: call `python3 tools/validate-skill.py --all` from CI instead of maintaining a second regex validator in YAML.
7. When replacing a custom frontmatter parser, prefer `yaml.safe_load` over ad hoc regex/string parsing.

## Why this matters

- Reduces token/permission surface in Actions.
- Prevents drift between local validation and CI validation.
- Avoids false positives from regex parsing nested YAML structures.
- Keeps contributor UX simple: one validator, one source of truth.

## Verification pattern

After hardening:
1. Read back the changed workflow files.
2. Run the canonical validator locally.
3. Confirm the validator result reflects real repository state and not parser artifacts.

Example evidence line:
- `python3 tools/validate-skill.py --all` -> all skills pass
