# Fable-5 Audit + Config Export Workflow for GitHub

## Context
This workflow combines a deep adversarial audit (via Fable-5 reasoning) with automated config export and git synchronization. It produces clean, validated commits with no secrets leaked and full durable traceability of what changed and why.

## Typical flow

1. **Run a Fable-5 adversarial audit** on the live Hermes config or another complex operational system.
   - Use delegation with `model: claude-fable-5` (deep reasoning).
   - Audit passes identify security, configuration, and efficiency issues.
   - Apply all fixes to the live system and verify they land (hermes doctor, cron validation, etc.).

2. **Export the updated live config** to the version-control repository:
   - Copy the live config file to the repo's config.yaml (raw, with real API keys).
   - This becomes the sanitizer's input; the raw version is never pushed to GitHub.

3. **Run the sanitizer script** (if one exists):
   ```bash
   cd ~/hermes-config && python3 scripts/sanitize_config.py
   # Outputs: config.sanitized.yaml with all api_key/token/password fields blanked to [REDACTED]
   ```

4. **Run validation**:
   ```bash
   cd ~/hermes-config && python3 scripts/validate_repo.py
   # Must pass before proceeding
   ```

5. **Regenerate supporting artifacts** (if applicable):
   - skills-index.md (updated skill inventory)
   - docs/upgrade-pass-YYYY-MM-DD.md (audit summary, can be written manually)
   - audit/hermes-audit-report.json (versioned pass entries)
   - audit/audit-security-findings.md (findings appended)

6. **Clean up** build artifacts:
   - Remove `scripts/__pycache__/` if present
   - Update `.gitignore` if needed (e.g., `scripts/__pycache__/`)

7. **Commit and push**:
   ```bash
   cd ~/hermes-config
   git add config.yaml config.sanitized.yaml skills-index.md docs/ audit/
   git commit -m "feat: full sync pass N — config, skills, docs, audit (YYYY-MM-DD)
   
   - config.yaml updated from live ~/.hermes/config.yaml (N lines, streamlined from M)
   - config.sanitized.yaml regenerated + validated (0 secrets leaked)
   - skills-index.md regenerated (N skills, YYYY-MM-DD)
   - docs/upgrade-pass-YYYY-MM-DD.md: pass-N audit summary
   - audit/hermes-audit-report.json: pass-N entries added
   - audit/audit-security-findings.md: pass-N findings appended
   - scripts/__pycache__ removed from tracking, .gitignore updated"
   
   git push origin main
   ```

8. **Verify**:
   ```bash
   git log --oneline -n 3
   git status --short --branch
   ```

## Key principles

- **Live config is always the source of truth**: the repo's `config.yaml` is regenerated from the live `~/.hermes/config.yaml` after each audit/fix cycle, not the other way around.
- **Sanitizer is the gatekeeper**: All API keys must be [REDACTED] before push. Validate with `validate_repo.py` before committing.
- **Audit artifacts become documentation**: Each pass gets a docs entry and audit record. This creates a historical audit trail of what was found and fixed.
- **Commits are atomic by pass**: A single commit covers all changes from one audit pass (config, docs, audit records, cleanup). Do not split into multiple commits per artifact type.

## Pitfalls

- **Do not commit the raw config to GitHub**: Only the sanitized version is pushed. The raw config.yaml in the repo is a working input for the sanitizer script, not a commit target.
- **Do not assume the sanitizer output matches the input**: Always verify the sanitized file has all secrets blanked (grep for actual key values, not just [REDACTED] placeholders).
- **Do not skip validate_repo.py**: Even if it looks clean, validation catches embedded secrets, malformed YAML, and inconsistencies.
- **Do not hardcode pass numbers**: Use the actual calendar date for the pass document (e.g., `upgrade-pass-2026-07-03.md`) so historical traceability is unambiguous.

## Dependencies

- `scripts/sanitize_config.py` — API key blanking (produces config.sanitized.yaml with all secrets [REDACTED])
- `scripts/validate_repo.py` — Security scan + YAML syntax check (blocks commit if issues found)
- Optional: `scripts/generate_skill_inventory.py` — Skill catalog regeneration (if maintaining a skills-index.md or inventory files)

## Example commit message template

```
feat: full sync pass N — config, skills, docs, audit (YYYY-MM-DD)

- config.yaml updated from live ~/.hermes/config.yaml (L lines, streamlined)
- config.sanitized.yaml regenerated + validated (0 secrets leaked)
- skills-index.md regenerated (S skills, YYYY-MM-DD)
- docs/upgrade-pass-YYYY-MM-DD.md: pass-N audit summary and findings
- audit/hermes-audit-report.json: pass-N entries with issue counts added
- audit/audit-security-findings.md: pass-N findings appended
- scripts/__pycache__ removed from tracking, .gitignore updated
```

## Typical Fable-5 audit findings → fixes → git sync cycle

1. **Audit identified**: 47 security/efficiency/consistency issues (passes 4 & 5)
2. **Fixes applied**: hermes-hud.py permissions corrected, obsidian-weekly-review cron fixed, orphan scripts removed, config consolidated, all verified
3. **Export**: config.yaml copied to repo, sanitizer run, validate_repo.py passed
4. **Docs**: docs/upgrade-pass-YYYY-MM-DD.md written with full narrative
5. **Audit records**: hermes-audit-report.json and audit-security-findings.md updated with new pass entries
6. **Commit**: Single atomic commit with all changes, commit SHA recorded in durable memory
7. **Verification**: hermes doctor clean (1 known CVE only), all crons verified ok, git log shows clean history

This workflow is repeatable: after future audits, follow the same steps (export, sanitize, validate, document, commit) for consistent traceability.
