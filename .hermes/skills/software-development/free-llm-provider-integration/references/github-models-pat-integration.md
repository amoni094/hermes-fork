# GitHub Models PAT Integration

## Overview

GitHub Models provides free access to frontier models (GPT-4o, Llama 3.1 405B) via Microsoft Azure inference. Uses a GitHub Personal Access Token (PAT) — no API key signup required.

Base URL: `https://models.inference.ai.azure.com`
Auth: HTTP Bearer token (PAT)

## PAT Creation (Two Types)

### Type 1: Models-only PAT (zero scopes, already created)
- Name: `hermes-models`
- Scopes: **NONE** (this is the default)
- Created via: https://github.com/settings/tokens/new
- Use: GitHub Models API calls only
- Cannot be used for: git operations, repo write access

### Type 2: Repo-scoped PAT (for git push)
- Name: `hermes-repo` (or any name)
- Scopes: `repo` (full repo access)
- Created via: https://github.com/settings/tokens/new
- Use: git push/clone with authentication
- Cannot use for: GitHub Models API (will be rejected)

**Important distinction:** Do NOT use the same PAT for both purposes. The Models API explicitly rejects tokens with scopes, and git operations require `repo` scope.

## Current Setup

- **GITHUB_TOKEN** (in ~/.hermes/.env) = `ghp_ZG...` (models-only, zero scopes)
  - Used in config.yaml as custom_provider for GitHub Models
  - Works for `gpt-4o`, `Llama-3.1-405B-Instruct`, etc.

- **GITHUB_PAT_REPO** (if needed for this session) = create fresh with `repo` scope
  - Use `gh auth refresh -h github.com -s repo` to upgrade existing auth
  - Or: manual browser signup at https://github.com/settings/tokens/new with `repo` scope

## Quota & Limits

- RPD: 150–1,000 (varies by model; Llama-405B is lowest at ~150)
- RPM: 15
- No training data usage (unlike Gemini)
- No credit card required

## Working Models (as of this session)

| Model | Context | Notes |
|-------|---------|-------|
| gpt-4o | 128K | GPT-4 quality, strongest reasoning |
| gpt-4o-mini | 128K | Faster, cheaper variant |
| Meta-Llama-3.1-405B-Instruct | 131K | Largest free open model |
| Meta-Llama-3.1-8B-Instruct | 131K | Fast small model |

## Testing

```bash
# Verify key is valid and list available models
GITHUB_TOKEN="ghp_..." curl -s https://models.inference.ai.azure.com/models \
  -H "Authorization: Bearer $GITHUB_TOKEN" | head -20
```

## Common Issues

- **"401 Unauthorized"** — invalid or expired PAT, or PAT has scopes (Models API rejects scoped tokens)
- **"403 Forbidden"** — PAT is valid but doesn't have access to this model (rare)
- **Rate limited (429)** — hit RPD or RPM quota; wait and retry

## See Also

- `references/github-pat-creation.md` — manual browser workflow for PAT creation
- `references/provider-catalog.md` — full provider comparison
