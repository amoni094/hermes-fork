# Hermes Config Export and Push Workflow

Pattern for exporting local Hermes configuration to a private GitHub repository, validating the export, and pushing with full verification.

## Context

Hermes stores configuration, skills, cron jobs, agent hooks, and policy state across multiple files in `~/.hermes/`. When you want a snapshot in a private git repo (for version control, backup, or config-as-code discipline), you need to:

1. **Sanitize secrets** — blank api_keys, tokens, passwords, auth headers
2. **Validate the export** — check for leftover secrets, missing metadata, schema correctness
3. **Resolve mismatches** — ensure supporting files (README, gitignore, docs) stay in sync with the validator rules
4. **Commit and push** — with scoped, detailed commit messages

This pattern handles all four steps.

## Prerequisites

- Local Hermes installation at `~/.hermes/`
- Git remote configured for the export repo (e.g., `git@github.com:user/hermes-config.git`)
- Scripts already in the repo: `scripts/sanitize_config.py` and `scripts/validate_repo.py` (see **Script Templates** below if creating from scratch)

## Steps

### Step 1: Regenerate the sanitized snapshot

```bash
cd /path/to/hermes-config/repo
python3 scripts/sanitize_config.py
```

This reads `~/.hermes/config.yaml`, blanks all secret-looking keys (api_key, token, password, etc.), and writes a clean copy to `config.sanitized.yaml`.

**What it does:**
- Reads full local config (with real secrets).
- Applies recursive sanitization rules (exact key patterns, allowlist for safe names, structural nesting).
- Writes a public-safe version to `config.sanitized.yaml`.
- Blanks keys like `api_key`, `access_token`, `secret_key`, `password`, `authorization`, `bearer_token`, `client_secret`, `cookie`, `secret`, `token`, `passwd`, etc.
- Preserves safe keys like `access_token_env` (env var names, not the secret itself) and `max_tokens` (numeric param, not a secret).

### Step 2: Validate the export

```bash
python3 scripts/validate_repo.py
```

This checks:
- All YAML files parse correctly.
- No non-empty secret-looking keys remain in `config.sanitized.yaml`.
- README.md contains a statement about sanitization (required by the validator).
- Veto rules YAML is well-formed (if present).
- No required support files are missing.

**If validation fails:**
- Read the error message carefully — it names the specific check that failed.
- Most common failures:
  1. **"still contains non-empty sensitive-looking keys"** → `sanitize_config.py` was not run or did not complete. Re-run it.
  2. **"no longer states that the config export is sanitized"** → README.md lost the required phrase. Add this line: "`config.sanitized.yaml` is a sanitized copy of the active Hermes config (all api_key, token, and password fields blanked)."
  3. **"did not parse into a mapping"** → A YAML file has a syntax error. Run `python3 -c "import yaml; yaml.safe_load(open('path/to/file'))"` on each file to find it.

### Step 3: Check git status and diff

```bash
git status --short --branch
git diff --stat
```

Review which files changed since the last push:
- `config.sanitized.yaml` — expected (from Step 1)
- `README.md` — if you fixed the sanitization statement (expected from Step 2)
- `.gitignore` — if you added exclusions (e.g., `*.pyc`, `__pycache__/`)
- Other files — only if you intentionally edited them

### Step 4: Stage and commit

```bash
git add -A
git commit -m "feat: update config snapshot and validation

- config.sanitized.yaml regenerated from live ~/.hermes/config.yaml
- validate_repo.py passes all checks
- README.md updated with sanitization statement"
```

Use a scoped commit message that names:
- **What changed** (e.g., "config snapshot", "veto rules", "cron jobs")
- **Why** (e.g., "after security audit", "operator config tuning", "delegation timeout extension")
- **Validation evidence** (e.g., "all checks pass", "20 hard-block rules active")

### Step 5: Push

```bash
git push
```

Verify the push succeeded and the remote branch matches your local head:

```bash
git log --oneline -n 3
# Example output:
# a1b2c3d (HEAD -> main, origin/main) feat: update config snapshot
```

## Troubleshooting

### Conflict on config.sanitized.yaml (already pushed)

If you pull and there's a conflict on `config.sanitized.yaml`:

```bash
git status
# On branch main, both modified: config.sanitized.yaml
```

**Resolution:** Take your version (it's the fresh one from Step 1):

```bash
git checkout --ours config.sanitized.yaml
git add config.sanitized.yaml
git commit -m "resolve: take fresh sanitized config snapshot"
git push
```

Do NOT merge the remote version — it's stale.

### validate_repo.py fails on YAML syntax

If a veto rule or config snippet has invalid YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('veto/rules/hard-block.yaml'))"
# yaml.YAMLError: ... line 42 ...
```

Fix the YAML, re-run sanitize and validate, then commit:

```bash
# Edit the file
git add veto/rules/hard-block.yaml
python3 scripts/validate_repo.py  # Should pass now
git commit -m "fix: veto rule YAML syntax"
```

### "config.sanitized.yaml still contains non-empty sensitive-looking keys"

This means `sanitize_config.py` saw a secret but did not blank it. Check:

1. Is the key in a nested structure that the script skips (e.g., inside a `secrets:` dict that the script does NOT recurse)? If so, manually blank it and re-validate.
2. Is there a typo in the key name (e.g., `api_key` vs `apikey`) that's not caught by the pattern? If so, add it to `FORBIDDEN_KEY_PATTERNS` in the script.
3. Did the sanitizer run at all? Check the timestamp: `stat config.sanitized.yaml | grep Modify`.

**Manual fix:** Open `config.sanitized.yaml` and blank any secret values by hand:

```yaml
# Before
provider:
  api_key: "sk-..."

# After
provider:
  api_key: ""
```

Then re-run `python3 scripts/validate_repo.py` to confirm.

### README.md lost the sanitization statement

The validator requires a specific phrase in README.md. Add it near the top:

```markdown
# hermes-config

`config.sanitized.yaml` is a sanitized copy of the active Hermes config 
(all api_key, token, and password fields blanked). Other files like 
config.yaml, veto/rules, and agent-hooks are symlinks or exports pointing 
to the real state.
```

Then:

```bash
git add README.md
python3 scripts/validate_repo.py  # Should now pass
git commit -m "docs: update README with sanitization note"
git push
```

## Script Templates

If your hermes-config repo doesn't have the scripts yet, create them:

### scripts/sanitize_config.py

```python
#!/usr/bin/env python3
"""
Sanitize Hermes config: blank all api_key, token, password, and similar fields.
Reads from ~/.hermes/config.yaml, writes to config.sanitized.yaml in the repo.
"""

import argparse
import pathlib
import re
import sys
import yaml

DEFAULT_SOURCE = pathlib.Path.home() / ".hermes" / "config.yaml"
OUT_PATH = pathlib.Path(__file__).parent.parent / "config.sanitized.yaml"
REPO_ROOT = OUT_PATH.parent

FORBIDDEN_KEY_PATTERNS = [
    "api_key", "access_token", "refresh_token", "bot_token", "bearer_token",
    "client_secret", "secret_key", "password", "authorization", "cookie",
    "secret", "token", "passwd",
]

ALLOWLIST = {
    "access_token_env",     # names an env var, not a secret
    "redact_secrets",       # boolean policy flag
    "use_cache",            # boolean flag
    "max_tokens",           # numeric model param
    "session_ttl_seconds",  # numeric TTL
}

STRUCTURAL_KEYS = {"secrets"}

AUTH_IN_URL = re.compile(r"(://[^:@]+:[^@]+@|Bearer\s+[a-zA-Z0-9_\-]+)")


def key_is_sensitive(key: str) -> bool:
    norm = key.lower()
    if norm in ALLOWLIST:
        return False
    return any(pat in norm for pat in FORBIDDEN_KEY_PATTERNS)


def sanitize(node):
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(k, str) and k.lower() in STRUCTURAL_KEYS:
                out[k] = sanitize(v)
            elif isinstance(k, str) and key_is_sensitive(k):
                out[k] = ""
            elif isinstance(k, str) and k.lower() in ("base_url", "callback_url", "public_url", "server_url") \
                    and isinstance(v, str) and AUTH_IN_URL.search(v):
                out[k] = ""
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(node, list):
        return [sanitize(v) for v in node]
    return node


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=pathlib.Path, default=OUT_PATH)
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"source config not found: {args.source}")

    raw = yaml.safe_load(args.source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("source config did not parse into a mapping")

    cleaned = sanitize(raw)
    args.out.write_text(yaml.dump(cleaned, default_flow_style=False), encoding="utf-8")
    print(f"wrote sanitized config -> {args.out}")


if __name__ == "__main__":
    main()
```

### scripts/validate_repo.py

```python
#!/usr/bin/env python3
"""
Validate the hermes-config export repo:
- All YAML parses correctly
- No secrets remain in config.sanitized.yaml
- Required metadata is present
"""

import pathlib
import sys
import yaml

REPO_ROOT = pathlib.Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config.sanitized.yaml"
SENSITIVE_KEYS = {
    "api_key", "access_token", "refresh_token", "bot_token", "bearer_token",
    "client_secret", "secret_key", "password", "authorization", "cookie",
    "secret", "token", "passwd",
}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_sanitized_config() -> None:
    if not CONFIG_PATH.exists():
        fail(f"config.sanitized.yaml not found at {CONFIG_PATH}")

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        fail("config.sanitized.yaml did not parse into a mapping")

    def check_for_secrets(obj, path=""):
        offenders = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if k.lower() in SENSITIVE_KEYS and v not in (None, "", [], {}):
                    offenders.append(f"{new_path}={v!r}")
                else:
                    offenders.extend(check_for_secrets(v, new_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                offenders.extend(check_for_secrets(item, f"{path}[{i}]"))
        return offenders

    offenders = check_for_secrets(cfg)
    if offenders:
        fail("config.sanitized.yaml still contains non-empty sensitive-looking keys: " + ", ".join(offenders))

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if "sanitized copy of the active Hermes config" not in readme:
        fail("README.md no longer states that the config export is sanitized")

    print("repo validation passed")


if __name__ == "__main__":
    validate_sanitized_config()
```

## Verification Checklist

- [ ] `python3 scripts/sanitize_config.py` runs without error
- [ ] `python3 scripts/validate_repo.py` passes
- [ ] `git status --short` shows only intended files changed
- [ ] `git diff --stat` shows a reasonable change count (not hundreds of files)
- [ ] `git log --oneline -n 1` shows your commit message
- [ ] `git branch -vv` or `git log -n 1 --decorate` shows `origin/main` or similar is updated
- [ ] Remote repo on GitHub shows the new commit

## Related Patterns

- **Private repo bootstrap:** `references/private-repo-bootstrap.md`
- **Validation workflow in CI:** `references/private-export-validation-workflow.md` (for automating this check on every push)
- **Config-as-code:** Treat this repo like infrastructure: version control, code review, audit trail. If multiple agents or team members touch it, require PR review before merge.
