# GitHub PAT Authentication Pitfalls

## GitHub Models API vs Git Operations

GitHub Models API and `git` operations have **incompatible token requirements**:

- **GitHub Models API** — requires a PAT with **zero scopes**. The API explicitly rejects any scoped tokens.
- **Git operations** (clone, push, pull) — require a PAT with at least `repo` scope.

If you create a single PAT with `repo` scope for git, the same token **cannot** be used for GitHub Models API calls (will return 403).

## Solution

Create **two separate PATs**:

1. **GitHub Models PAT** — zero scopes (read-only access to models endpoint)
   ```bash
   gh auth login --with-token < <(echo "ghp_...")
   GITHUB_TOKEN="ghp_..." curl https://models.inference.ai.azure.com/models
   ```

2. **Git Operations PAT** — `repo` scope (for clone/push/pull)
   ```bash
   # When configuring git:
   git config user.name "amoni094"
   git config --global credential.helper store
   # Then when prompted by git, use the repo-scoped PAT
   ```

Store both in `~/.hermes/.env` with clear variable names:
```bash
GITHUB_TOKEN="ghp_..."           # Models API (zero scopes)
GITHUB_PAT_REPO="ghp_..."        # Git operations (repo scope)
```

## Device Code Flow Pitfall

When running `gh auth refresh -s repo -s public_repo` to upgrade token scopes, the command:
1. Prints a one-time device code (e.g., `C4E3-F29C`)
2. Blocks waiting for manual entry at https://github.com/login/device
3. After you enter the code in the browser, returns to the CLI

**Issue on Fedora Atomic with browser tooling**: If using `browser_navigate` (CDP), the browser session state from one CDP call does NOT persist to the next. If `gh auth refresh` is interrupted or re-prompted after a CDP browser closes, you'll need to:
- Open a fresh headed browser window manually
- Or start a new `gh auth refresh` in a foreground terminal where you can see the code and enter it

## GitHub Models Quota

As of 2026-06-30:
- **gpt-4o**: 150 requests/day
- **gpt-4o-mini**: 1,000 requests/day
- **Llama 3.1 405B**: 150 requests/day
- **Llama 3.1 8B**: 1,000 requests/day

Quota resets daily at midnight UTC. Free tier does not train on prompts.

## Verification

Test the token before saving:
```bash
# Models API
curl -s https://models.inference.ai.azure.com/models \
  -H "Authorization: Bearer $GITHUB_TOKEN" | jq '.data | length'
# Should return a number (count of available models)

# Git operations
git clone https://ghp_...@github.com/amoni094/hermes-config.git
# Should clone without authentication prompt (if token is valid)
```
