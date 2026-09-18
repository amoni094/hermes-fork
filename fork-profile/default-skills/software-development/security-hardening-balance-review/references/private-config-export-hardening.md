# Private config/export repo hardening

Use this pattern for repositories that intentionally store sanitized operational snapshots rather than runnable production services.

## When it applies
- private config/export repositories
- sanitized snapshots of agent config, cron state, workflow notes, or inventories
- maintenance scripts that read live local state and emit redacted/generated repo artifacts

## High-value controls
1. Add a repo-local instruction file (`AGENTS.md`) with explicit export boundaries.
   - name forbidden files and state stores
   - say that snapshots are security-sensitive exports
   - specify the verification commands that must run before completion

2. Add a single validation script.
   - compile or syntax-check local maintenance scripts
   - verify required `.gitignore` exclusions remain present
   - inspect sanitized config snapshots for non-empty sensitive-looking keys
   - inspect redacted cron/job snapshots for unredacted origin identifiers
   - verify key docs still state the sanitized-export posture

3. Harden maintenance scripts for low-blast-radius behavior.
   - default live-state mutation scripts to dry-run
   - require an explicit `--apply` or equivalent for real rewrites
   - use atomic writes for generated outputs
   - put timeouts and explicit error shaping around local CLI subprocess calls

4. Ignore generated cache noise.
   - add `__pycache__/` and `*.py[cod]` so verification runs do not pollute diffs

## Pitfalls
- relying on documentation alone with no executable validation gate
- scripts that rewrite live local state on plain invocation
- non-atomic writes that can leave generated inventories half-written
- treating private visibility as sufficient hygiene for sensitive operational metadata

## Verification minimum
- run the syntax/compile check for touched scripts
- run the repo-local validation script
- rerun any generator whose behavior changed
- read back the generated diff for the changed scripts/docs

## Smallest-safe-fix heuristic
Prefer guardrails that improve default safety without changing the user's live workflow unless they explicitly opt in. For this repo class, that usually means validation gates, redaction checks, dry-run defaults, and better docs before broader behavioral changes.