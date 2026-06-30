# Provider-Specific Caveats & Session Discoveries

Deep dives into provider-specific quirks, network blockers, and gotchas discovered during testing.

## Groq — Datacenter IP Block (Critical)

**Symptom:** Access denied. Please check your network settings.

**Root Cause:** Groq uses Cloudflare with aggressive bot/datacenter IP blocking. Your machine on **AS136557 "Host Universal Pty Ltd"** (a hosting/datacenter ASN) is blocked at Cloudflare layer on both web and API endpoints.

**Does not affect:** Residential IPs, home fiber, most ISP connections.

**Does affect:** ProtonVPN AU, other datacenter-routed VPNs, EC2/DigitalOcean/Linode instances, any proxy through ASN AS136557 range.

### Workaround: Split-Tunnel Routing

Send Groq traffic through residential gateway, bypass VPN/proxy.

**Groq Cloudflare IPs to route:**
- 172.64.149.20
- 104.18.38.236
- (Query `dig api.groq.com +short` to find current IPs)

**Persistent systemd service** (groq-split-tunnel.service):

```bash
# ~/.config/systemd/user/groq-split-tunnel.service

[Unit]
Description=Groq Split-Tunnel Routing
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c ' \
  for ip in 172.64.149.20 104.18.38.236; do \
    sudo ip route add $ip/32 via $(ip route show | grep default | awk "{print \$3}"); \
  done \
'
ExecStop=/bin/bash -c ' \
  for ip in 172.64.149.20 104.18.38.236; do \
    sudo ip route del $ip/32 2>/dev/null || true; \
  done \
'
RemainAfterExit=yes

[Install]
WantedBy=default.target
```

Enable at boot:
```bash
systemctl --user enable --now groq-split-tunnel.service
```

**Test:**
```bash
GROQ_API_KEY="gsk_..." curl -s https://api.groq.com/openai/v1/models | jq '.data | length'
# Should return number of models, not "Access denied"
```

**Session status:** Active and working. Routes tested via `curl` and hermes query both successful.

---

## Mistral — SSO Auth Bug

**Symptom:** 500 Internal Server Error on Google OAuth sign-in (Mistral status page logged it).

**Root Cause:** Mistral's SSO implementation has a recurring bug. Their own status page documented it as known issue.

**Workaround 1 (Email/Password):** Use email/password signup instead of "Continue with Google" button.

**Workaround 2 (API Key):** If already signed up, API key auth works fine (key-based API is not affected by SSO bug). Bug only blocks initial OAuth flow.

**Session Status:** Signed up via email/password successfully. API key `rfpC4jOX5pRdnhDbHyFtlOuUpqEJgRuQ` created and tested live — works.

---

## Cerebras — 8K Hard Context Limit on Free Tier

**Critical Detail:** Free tier is HARD-CAPPED at 8K tokens context. This is not a soft limit or guideline — the API rejects any input >8K with error.

**Paid tier:** 128K context, but free tier ==> 8K ONLY.

**Decision Matrix:**
- If context needed <8K → Use Cerebras (14.4K RPD, excellent for compression)
- If context needed 8–32K → Use SambaNova or Mistral instead
- If context needed >32K → Use Gemini (1M) or Mistral (262K)

**Session Impact:** Updated routing skill to note this. When using Cerebras for summarization/compression, ensure input is <8K or will fail at runtime.

---

## SambaNova — Case-Sensitive Model IDs

**Critical Detail:** Model names are case-sensitive and space-sensitive.

**Correct:**
- `DeepSeek-V3.2` (not `deepseek-v3.2`, not `DeepSeek-V3.2-Instruct`)
- `Meta-Llama-3.3-70B-Instruct` (not `meta-llama-3.3-70b-instruct`)

**Wrong:**
- `deepseek-v3.2` — 404 model not found
- `llama-3.3-70b-instruct` — 404 model not found

**Session Discovery:** DeepSeek-V3.2 context is 32K (not 128K). V3.1 has 128K. Use V3.1 or Llama-3.3-70B (192K) for longer contexts.

**Test:**
```bash
SAMBANOVA_API_KEY="..." curl -s https://api.sambanova.ai/v1/models \
  -H "Authorization: Bearer $SAMBANOVA_API_KEY" | jq '.data[] | .id'
# Returns: DeepSeek-V3.2, Meta-Llama-3.3-70B-Instruct, etc. — use EXACT IDs
```

---

## Gemini — Data Training & Quota

**Data Training:** Free tier outside EU/UK/EEA/CH includes training on your prompts (Google may use them to improve models). In EU/UK/EEA/CH, data is not used for training.

**Solution:** If sensitive data, either (1) use SambaNova instead, or (2) explicitly request EU-region API key if available.

**Free Tier Quota:**
- 1,500 requests per day (high RPD)
- 15 requests per minute (rate limit)
- 1M token context window (huge)

**Session Discovery:** Gemini API key initially showed "limit: 0" because Google Cloud project didn't have Gemini API properly enabled in their dashboard. Once enabled, quota appeared. Check Google Cloud console if quota shows 0.

---

## GitHub Models — PAT Zero-Scope Requirement

**Critical Detail:** Models API explicitly rejects Personal Access Tokens with ANY scopes. Token must have zero scopes.

**Consequence:** If you need BOTH models API access AND git repo write access, create TWO separate PATs:

1. **PAT for models API:** Zero scopes (models.inference.ai.azure.com)
2. **PAT for git ops:** `repo` scope for git push/pull

**Session Pattern:** Created PAT with zero scopes for models API. Later needed to push config to GitHub, so created SECOND PAT with `repo` scope for git operations.

**How Created:**
```bash
# First PAT: zero scopes (for API)
gh auth refresh -s ""  # Empty scope = zero scopes
# Models API accepts this

# Second PAT: repo scope (for git)
gh auth refresh -s repo,public_repo
# Git operations use this
```

**Test:**
```bash
# Models API with zero-scope PAT
GITHUB_TOKEN="ghp_..." curl -s https://models.inference.ai.azure.com/models \
  -H "Authorization: Bearer $GITHUB_TOKEN" | jq '.data | length'
# Works

# Git with repo-scope PAT
git push origin main
# Works
```

---

## Mistral — Data Training & Privacy

**Free Tier:** Mistral Experiment plan (free) opts INTO data training by default. Your prompts may be used to fine-tune Mistral models.

**Workaround:** Disable in account settings (`https://console.mistral.ai/account/settings/`) or use SambaNova (explicit no-training guarantee).

**Session Status:** Used Mistral for testing. Not recommended for sensitive/proprietary data unless training disabled in account settings.

---

## Gemini vs. Other Providers — Context Window Trade-offs

**Gemini advantage:** 1M token context (largest by far).

**Gemini disadvantage:** Data training outside EU, rate limit lower (15 RPM), cost/token on paid tier is higher.

**When to use Gemini:**
- Need to summarize/analyze very large documents (>100K tokens)
- Title generation (low-volume auxiliary task, ok to use free tier)
- Context compression from huge inputs

**When to use alternatives:**
- Need privacy (SambaNova — explicit no-training)
- Need speed (Groq)
- Need volume (Cerebras — 14.4K RPD, only 8K ctx but ok for compression)

---

## Quota Reset Times (Critical for Scheduling)

**Mistral:** Monthly quota (1B tokens, resets calendar month)

**Groq/Cerebras:** Midnight UTC

**Gemini:** Midnight Pacific Time (PT, UTC-7 or UTC-8 depending on DST)

**SambaNova:** Calendar day UTC (20 per model per 24h)

**GitHub Models:** Daily per model (varies 150-1000 per day)

**Implication:** If cron jobs run at a specific time, schedule:
- High-volume tasks before quota resets
- Low-volume fallback tasks after reset (if primary quota depleted)
- Cross-provider cascade to handle uneven reset times

Example: Groq at 23:55 UTC (5 min before reset), Cerebras at 00:05 UTC (5 min after reset) ensures continuous availability.

---

## Key Rotation & Expiration

**Groq:** No automatic rotation visible in dashboard. If key compromised, revoke and create new.

**Cerebras:** No automatic rotation. Manual revoke/recreate.

**SambaNova:** No automatic rotation.

**Mistral:** No automatic rotation visible.

**GitHub Models:** PATs can have expiration dates (set at creation). Recommended: no expiration for long-lived cron jobs, or handle in credential-rotation cron.

**Practice:** Treat .env file as secret. Never commit. Rotate keys quarterly or if leaked.
