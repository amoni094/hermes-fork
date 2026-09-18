# Repo export validator patterns

Use this note when hardening a private config/export repository whose purpose is to capture sanitized operational state without leaking secrets.

## Main lesson
Hardening validators can easily become over-broad and create false confidence.

Bad pattern:
- treat any key containing `token` or `secret` as a leak

Why it breaks:
- catches safe metadata such as `max_tokens`, feature flags like `show_token_analytics`, or indirection fields such as `access_token_env`
- pressures the maintainer to add broad exemptions or to weaken the validator later

Better pattern:
- match narrower secret-bearing names such as `api_key`, `access_token`, `refresh_token`, `bot_token`, `client_secret`, `authorization`, `cookie`
- keep a small exact-name allowlist for known-safe indirection/metadata fields when needed
- verify the rule against the real sanitized config, not just a synthetic example

## Mutation-script posture
For maintenance scripts that can rewrite live operator state:
- default to dry-run / read-only mode
- require an explicit `--apply` or `--write` flag for mutation
- if mutation occurs, create the backup only on the mutating path
- make backup naming auditable; UTC/Z-suffixed timestamps are preferable

## Generated-output posture
For repo-maintenance generators:
- use atomic writes for generated markdown/json artifacts
- put timeouts and explicit stderr/stdout surfacing around subprocess calls
- prefer clear parse failures over partial output

## Verification discipline
When documenting a hardening pass, make the verification list match the actual changed files and commands.

Minimum useful proof for this repo class:
- `python3 -m compileall scripts`
- repo-local validator command
- generator command(s)
- migration script in dry-run mode unless mutation was explicitly requested
- targeted `git diff -- ...` covering the files you claim to have reviewed

## When not to overreact
- A non-stdlib dependency already present and healthy in the real environment is not automatically a blocker.
- Treat it as a portability note unless the task requires broader portability or CI support.
