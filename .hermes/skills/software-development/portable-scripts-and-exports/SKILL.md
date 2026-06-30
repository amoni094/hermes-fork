---
name: portable-scripts-and-exports
description: Make utility scripts, exports, and configurations portable across machines and users. Use Path.home(), __file__ resolution, and config templating instead of hardcoding paths or credentials.
trigger: |
  - Writing utility scripts that will run on different machines (repo tools, code generators, data processors)
  - Preparing configs or code for public sharing or team collaboration
  - Refactoring hardcoded paths that break when cloned or run under a different user
  - Designing a repo export that should be redistributable without manual path edits
  - Setting up validation rules to prevent accidental credential commits
keywords:
  - pathlib
  - Path.home()
  - __file__
  - config sanitization
  - .gitignore
  - validation scripts
  - env vars
  - template configs
related_skills:
  - hermes-agent
  - github-operations
---

# Portable Scripts and Exports

When writing utility scripts meant to run across machines or sharing code/config with others, avoid hardcoding absolute paths and credentials. Use Python's pathlib and environment context to make scripts self-locating and config-independent.

## Patterns

### Path Resolution

**DO:**
```python
# Scripts in a repo — locate relative to itself
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / 'docs' / 'output.json'

# User data in ~/.hermes — use Path.home()
HERMES_HOME = pathlib.Path.home() / '.hermes'
SKILLS_DIR = HERMES_HOME / 'skills'
CONFIG_PATH = HERMES_HOME / 'config.yaml'
```

**DON'T:**
```python
# Hardcoded to a specific machine — breaks when cloned
ROOT = pathlib.Path('/var/home/username/.hermes/skills')
OUTPUT = pathlib.Path('/home/user/my-repo/docs/output.json')
```

**Why:** `Path.home()` works on any Unix/Windows machine; `Path(__file__).resolve().parents[N]` makes scripts portable within their repo structure regardless of where the repo is cloned.

### Config Sanitization

When exporting a config repo for sharing:

1. **Scrub before commit:**
   - All API keys, tokens, secrets → empty string `''` or placeholder
   - Auth files (`.env`, `auth.json`) → `.gitignore` so they never enter git
   - Chat/channel IDs from personal messaging platforms → redacted (keep structure, replace values)
   - Absolute paths to user home dirs → replace with `~` or `$HOME` placeholders in docs; use `Path.home()` in code

2. **Validate on push:**
   - Add a pre-commit hook or CI check (e.g., `validate_repo.py`) that fails if sensitive keys are non-empty
   - Use regex patterns to catch `api_key:`, `secret_key:`, `token:` with non-empty values
   - Whitelist safe keys like `telegram_allowed_users` (usernames, not secrets)

3. **Document what was excluded:**
   - In README, note: "sanitized copy of the active Hermes config — real secrets stored in ~/.hermes/"
   - In docs, list what was redacted and why (gateway state, session histories, auth tokens)

### Example: Validate Script

See `references/validate-export-example.py` (from amoni094/hermes-config) for a production example that checks:
- No tracked `__pycache__` or `.pyc` files
- `.gitignore` contains required exclusions
- YAML config has no non-empty sensitive-looking keys
- Cron snapshot has redacted chat/channel IDs
- Documentation includes export-hygiene markers

## Pitfalls

- **Forgetting env vars in .gitignore:** Even though a secret is empty, git will track the key name. Always add `key: ''` before committing, then ensure `.gitignore` blocks `.env` and `auth.json` so the *actual* secrets never enter the repo.
- **Sharing before validation:** Run a validation script to prove no secrets leaked before pushing. A single hardcoded API key in a public repo grants full account access.
- **Relative imports in scripts:** When moving scripts between directories, `from config import X` may break. Use `Path(__file__).resolve().parents[1]` or `sys.path.insert` to make imports robust.
- **Parametrization after shipping:** It's easier to parametrize paths *before* you first distribute a script. Retrofitting requires all downstream users to update.

## Steps

When preparing a utility script for sharing:

1. Replace all hardcoded absolute paths with `Path.home() / '.hermes' / ...` or `Path(__file__).resolve().parents[N] / ...`
2. For config/data files, use pathlib exclusively (no f-strings with `/` concatenation)
3. Test the script from a different directory to ensure `__file__` resolution works
4. If the script reads config, test with `~/.hermes/config.yaml` (via `Path.home()`) so it works on any machine
5. Add a validation step (linting, compile check) to catch syntax errors before distribution
6. Document the expected directory structure in a README or docstring

## Verification

Run scripts from different working directories and verify paths resolve correctly:
```bash
cd /tmp && python3 ~/my-repo/scripts/generate_inventory.py  # Should still work
# Check output is written to the repo, not /tmp
```

If sharing a repo, clone it to a clean directory under a different username and verify scripts still run without path edits.
