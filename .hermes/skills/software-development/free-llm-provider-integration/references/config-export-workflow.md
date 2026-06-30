# Config Export Workflow & Sanitization

Pattern for sharing Hermes config snapshots (e.g., via GitHub) without leaking API keys, credentials, or sensitive data.

## Overview

When exporting `~/.hermes/config.yaml` to a public or shared repository, sanitize all secrets systematically:

1. Identify sensitive fields (keys, tokens, passwords, URLs)
2. Redact to placeholder `<redacted>`
3. Verify no actual keys leaked before committing
4. Document placeholder stubs with provider info

## Fields to Scrub

**Always redact entirely:**
- `api_key`, `password`, `password_hash`, `secret`, `client_id`
- `portal_url`, `public_url`, `username`
- `ref_audio`, `ref_text` (voice references)
- `voice_id`, `persona_prompt_file`
- `guardrail_identifier`, `guardrail_version`
- `prefill_messages_file`, `orchestrator_profile`, `default_assignee`

**Redact values matching patterns:**
- `^(sk-|gsk_|ghp_|gho_|csk-|AIza|rfpC|AQ\.)` — API keys, bearer tokens
- `^(b058b2|ghp_ZG|gsk_NZ)` — session-specific observed keys
- Anything >35 chars that looks like `^[a-zA-Z0-9_\-\.]{35,}$` — likely token/key

**Always clear lists:**
- `terminal.env_passthrough[]` — environment variable names that should stay secret

## Sanitization Script (Python)

```python
import yaml, re

# Load config
with open('/var/home/rainbow/.hermes/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Fields that are always scrubbed
SCRUB_KEYS = {'api_key', 'password', 'password_hash', 'secret', 'client_id',
              'portal_url', 'public_url', 'username', 'ref_audio', 'ref_text',
              'voice_id', 'persona_prompt_file', 'guardrail_identifier',
              'guardrail_version', 'prefill_messages_file',
              'orchestrator_profile', 'default_assignee'}

SENSITIVE_PATTERNS = re.compile(
    r'^(sk-|gsk_|ghp_|gho_|csk-|AIza|rfpC|AQ\.|b058b2|ghp_ZG|gsk_NZ)'
)

def scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in SCRUB_KEYS:
                out[k] = '<redacted>'
            else:
                out[k] = scrub(v)
        return out
    elif isinstance(obj, list):
        return [scrub(i) for i in obj]
    elif isinstance(obj, str):
        # Redact if matches known pattern
        if SENSITIVE_PATTERNS.match(obj):
            return '<redacted>'
        # Redact if looks like a long token
        if len(obj) > 35 and re.match(r'^[a-zA-Z0-9_\-\.]{35,}$', obj):
            return '<redacted>'
        return obj
    return obj

clean = scrub(config)

# Clear env_passthrough list
if 'terminal' in clean and 'env_passthrough' in clean['terminal']:
    clean['terminal']['env_passthrough'] = []

# Write sanitized
with open('config.sanitized.yaml', 'w') as f:
    yaml.dump(clean, f, default_flow_style=False, allow_unicode=True)
```

## Pre-Commit Verification

Before pushing to git, verify no real keys leaked:

```bash
# Check diff for known key patterns
git diff --cached | grep -E "(gsk_NZ|csk-6p|rfpC4j|b058b2|AQ\.Ab|ghp_ZG)"
# Should output nothing

# Also scan the file directly
grep -E "(gsk_|csk-|rfpC|AQ\.|ghp_)" config.sanitized.yaml
# Should output only lines with <redacted> or template text
```

## Template / Stubs Documentation

Create a companion file documenting what each `<redacted>` field represents:

```markdown
# env.template

API key stubs for all supported providers. Copy to ~/.hermes/.env and fill in your keys.

## Anthropic (primary)
ANTHROPIC_API_KEY=<your_anthropic_key>

## Free tier providers

# Groq: 1,000 RPD, 30 RPM — https://console.groq.com/
GROQ_API_KEY=<your_groq_key>

# Cerebras: 14,400 RPD — https://cloud.cerebras.ai/
# Note: Free tier capped at 8K context (paid is 128K)
CEREBRAS_API_KEY=<your_cerebras_key>

# ... etc
```

Place this alongside the sanitized config so users know what keys to populate.

## GitHub Workflow

Example workflow to validate config before commit:

```yaml
# .github/workflows/validate-config.yml
name: Validate Config Export
on: [pull_request]
jobs:
  check-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for leaked keys
        run: |
          ! grep -r -E "(gsk_|csk-|rfpC|AQ\.|ghp_[A-Z])" . \
            --include="*.yaml" --include="*.yml" --exclude-dir=.git
          echo "✓ No API keys found"
```

## Session Example (This Conversation)

Files created and verified:
- `config.sanitized.yaml` — 754 lines, no keys leaked
- `env.template` — 37 lines, all keys as `<your_provider_key>` stubs
- `README.md` — updated with provider table and fallback chain

Verification before push:
```bash
git diff --cached | grep -E "(gsk_NZ|csk-6p|rfpC4j|AQ\.Ab8|ghp_ZG|gho_)"
# Output: (nothing = clean)

git push origin main
# Success
```

## Caveats

- **Commit history persists:** If you accidentally commit a real key, git history keeps it. Use git-filter-branch or BFG Repo-Cleaner to scrub history.
- **GitHub Actions secrets:** If using repo secrets for CI/CD, never log or export them — use `::add-mask::` to hide in workflow output.
- **.env files:** Never commit real .env files. Use .gitignore to exclude them:
  ```
  .env
  .env.local
  ~/.hermes/.env
  ```
- **SSH keys in config:** If SSH host keys or private keys end up in config, treat with same urgency as API keys.
