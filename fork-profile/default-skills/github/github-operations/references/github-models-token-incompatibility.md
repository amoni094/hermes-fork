# GitHub Models API + Git Operations Token Incompatibility

## The Problem

GitHub has **two incompatible token ecosystems**:

1. **GitHub Models API** (hosted at models.inference.ai.azure.com)
   - Requires a classic Personal Access Token (PAT)
   - **Must have zero scopes** — the API explicitly rejects any scoped tokens
   - Free tier: gpt-4o, Llama-405B, etc. — no training on prompts

2. **Git Operations** (clone, push, pull via HTTPS)
   - Requires a PAT with at least `repo` scope
   - A zero-scoped token will be rejected by git

## Why This Matters

If you create a single PAT with `repo` scope to push to a GitHub repository, **you cannot use that same PAT for GitHub Models API calls**. The API will return 403.

## Solution: Separate Tokens

Create **two distinct PATs**:

### Token 1: GitHub Models (Zero Scopes)

In the GitHub web UI (Settings > Developer Settings > Personal access tokens > Tokens classic):
1. Click "Generate new token (classic)"
2. Name it `github-models` or similar
3. **Do NOT check any scopes**
4. Set expiration (e.g., No expiration)
5. Click "Generate token"
6. Copy and save as `GITHUB_TOKEN` in `~/.hermes/.env`

Test:
```bash
curl -s https://models.inference.ai.azure.com/models \
  -H "Authorization: Bearer ghp_..." | jq '.data | length'
# Should return a number (count of models)
```

### Token 2: Git Operations (Repo Scope)

In the GitHub web UI:
1. Click "Generate new token (classic)" again
2. Name it `github-repo` or `hermes-git` or similar
3. Check **`repo`** scope only
4. Set expiration
5. Click "Generate token"
6. Save as `GITHUB_PAT_REPO` or configure git credential store:
   ```bash
   git config --global credential.helper store
   # Then git will prompt you to paste the PAT on first clone/push
   ```

Test:
```bash
git clone https://GITHUB_PAT_REPO@github.com/amoni094/hermes-config.git
# Should clone without auth prompts if token is valid
```

## Device Code Flow (gh auth refresh)

When refreshing token scopes using `gh auth refresh -s repo`:
1. The CLI prints a one-time device code (e.g., `C4E3-F29C`)
2. It blocks waiting for you to visit https://github.com/login/device and enter that code
3. Once entered in the browser, the CLI continues and the token is upgraded

**Fedora Atomic / CDP caveat**: If the browser session (from `browser_navigate` / CDP) has closed or restarted, the cached GitHub login state may be lost. If `gh` prompts again on retry:
- Use a fresh foreground terminal window where you can see the code prompt
- Or open a new headed browser manually (not via CDP) for better session persistence

## Storage Pattern

In `~/.hermes/.env`:
```bash
# GitHub Models API (zero scopes, read-only)
GITHUB_TOKEN="ghp_..."

# Git operations (repo scope, for clone/push/pull)
GITHUB_PAT_REPO="ghp_..."
```

In `~/.hermes/config.yaml`, GitHub Models is already configured under `custom_providers`:
```yaml
custom_providers:
  github-models:
    endpoint: "https://models.inference.ai.azure.com"
    api_key_env: "GITHUB_TOKEN"
    models:
      - "gpt-4o"
      - "gpt-4o-mini"
      - "Meta-Llama-3.1-405B-Instruct"
```

For git operations, store the repo-scoped PAT in the credential helper:
```bash
git config --global credential.helper store
# When git prompts, paste GITHUB_PAT_REPO
```

Or use it directly in URLs (temporary, not for scripting):
```bash
git clone https://ghp_REPO@github.com/amoni094/hermes-config.git
```

## Common Mistakes

1. **Creating one PAT with `repo` + using it for Models API** → 403 on Models API calls
2. **Forgetting the `public_repo` scope when upgrading** → Scope cascade with `gh auth refresh` may require multiple runs
3. **Storing both tokens with the same variable name** → Overwrites the first with the second
4. **Assuming GitHub CLI auto-uses the right token** → You must explicitly route: `GITHUB_TOKEN` for Models API, git credential helper for git ops

## Verification Checklist

- [ ] `gh auth status` shows the correct account
- [ ] `curl https://models.inference.ai.azure.com/models -H "Authorization: Bearer $GITHUB_TOKEN"` returns JSON model list
- [ ] `git clone https://github.com/amoni094/hermes-config.git` clones without auth prompts (if token is in credential helper)
- [ ] Both tokens are stored in `~/.hermes/.env` with clear variable names
- [ ] `~/.hermes/.env` is in `.gitignore` or not tracked anywhere
