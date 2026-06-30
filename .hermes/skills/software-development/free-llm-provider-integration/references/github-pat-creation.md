# GitHub PAT Creation for Model Access

GitHub Models (experimental feature) provides access to free models via GitHub's platform. Requires a GitHub Personal Access Token (PAT) with minimal scopes.

## Automated vs Manual Signup

**Browser automation via Hermes** currently fails because:
1. GitHub OAuth with Google doesn't auto-redirect (form isn't automatically filled)
2. Wrong GitHub passwords fail silently with "Incorrect username or password" — need to either know the password or reset it first
3. Headless browser auth to GitHub (even if password is known) may hit additional challenges on Fedora Atomic

**Fastest approach:** Manual signup in your regular browser (2 minutes).

## Manual PAT Creation

1. **Logged into GitHub** in your regular browser: https://github.com/login
2. Navigate to **Settings → Developer settings → Personal access tokens → Tokens (classic)** 
   - Direct URL: https://github.com/settings/tokens
3. Click **"Generate new token (classic)"**
4. Fill in:
   - **Note:** `hermes-models` (or any memorable name)
   - **Expiration:** "No expiration" or "90 days" (no expiration is valid for automation)
   - **Scopes:** Leave empty (GitHub Models doesn't require specific scopes; token just needs to exist)
5. Click **"Generate token"**
6. **Copy the token immediately** — it only displays once
7. Save to `~/.hermes/.env`:
   ```bash
   echo 'GITHUB_TOKEN="ghp_..."' >> ~/.hermes/.env
   ```

## Verify

```bash
# Check token format
cat ~/.hermes/.env | grep GITHUB_TOKEN

# Test GitHub API access
curl -H "Authorization: token $(grep GITHUB_TOKEN ~/.hermes/.env | cut -d'"' -f2)" \
  https://api.github.com/user
```

Should return your GitHub user info. If 401, the token is wrong or expired.

## Integration into config.yaml

GitHub Models endpoint (when available) would look like:

```yaml
custom_providers:
  github:
    endpoint: "https://models.inference.ai.azure.com"
    api_key_env: "GITHUB_TOKEN"
    models:
      - "gpt-4o"  # (if available)
      - "claude-3.5-sonnet"  # (if available)
```

**Status:** GitHub Models is currently in limited access. If you have access, add the above config after testing the token.

## Troubleshooting

- **"Incorrect username or password"** — GitHub password is wrong or account doesn't exist. Reset via https://github.com/login → "Forgot password?" using amoni094@gmail.com
- **401 Unauthorized on API test** — Token is invalid, expired, or formatted wrong. Regenerate at https://github.com/settings/tokens
- **Token not showing in ~/.env** — Check file exists and is readable: `cat ~/.hermes/.env`

## Related

- API key security: `secret-hygiene` skill
- GitHub oauth/signup blockers: See `free-llm-provider-integration` pitfalls
