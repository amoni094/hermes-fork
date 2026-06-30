# Free LLM Provider Catalog

Sources: https://github.com/slavarazbash/awesome-free-gpt and https://github.com/cheahjs/free-llm-api-resources

## Recommended (Tier 1)

### Groq
- **Signup:** https://console.groq.com/login → Continue with Google → Create API key
- **Endpoint:** https://api.groq.com/openai/v1
- **Key format:** `gsk_...`
- **Free quota:** Generous (100K tokens/day typical, but varies)
- **Rate limit:** ~30 req/min per free account
- **Models:** llama-3.1-70b-versatile, mixtral-8x7b-32768, gemma-7b-it
- **Notes:** Fastest inference on free tier. Reliable uptime. Email verification required.
- **Automation blocker:** Google OAuth + email verification

### Google AI Studio (Gemini)
- **Signup:** https://aistudio.google.com/app/apikey
- **Endpoint:** https://generativelanguage.googleapis.com/v1beta/openai/
- **Key format:** `AIza...` (not OpenAI-compatible out of box; needs adapter)
- **Free quota:** 60 requests/minute, 1500 requests/day
- **Models:** gemini-2.0-flash, gemini-1.5-pro
- **Notes:** Strong reasoning models. Relatively new free tier. Google account required.
- **Automation blocker:** Google account sign-in, may require verification

### Cerebras
- **Signup:** https://cloud.cerebras.ai/ → Sign Up → Continue with Google
- **Endpoint:** https://api.cerebras.ai/v1
- **Key format:** `csk_...`
- **Free quota:** ~100K tokens/month (usage-based)
- **Models:** gpt-oss-120b, gemma-4-31b, llama-3.1-70b
- **Notes:** Emerging provider, good uptime. Can deplete quota quickly on long-context tasks. Models are case-sensitive.
- **Automation blocker:** Google OAuth

### SambaNova
- **Signup:** https://cloud.sambanova.ai/ → Sign Up (no credit card required)
- **Endpoint:** https://api.sambanova.ai/v1
- **Key format:** `sb-...` (UUID format)
- **Free quota:** Generous (100K tokens/day typical, but check dashboard)
- **Models:** DeepSeek-V3.2, Meta-Llama-3.3-70B-Instruct, DeepSeek-Coder-33B-Instruct, Qwen-2.5-72B-Instruct
- **Notes:** Best value free tier. No credit card, no data collection on free tier. Fast inference.
- **Automation blocker:** Email verification (non-OAuth), manageable programmatically

### Mistral AI
- **Signup:** https://console.mistral.ai/ → Sign Up (email/password or OAuth)
- **Endpoint:** https://api.mistral.ai/v1
- **Key format:** `msty_...`
- **Free quota:** ~1M tokens/month (~1M tokens free tier access)
- **Models:** mistral-7b, mistral-large, codestral
- **Notes:** Solid models, good performance. Occasional SSO bugs but direct email signup works.
- **Automation blocker:** Email verification or OAuth (has recurring SSO 500 errors; use email backup)

## Community-Collected (Tier 2 — less stable, verify before use)

See the upstream repos for the full list:
- https://github.com/slavarazbash/awesome-free-gpt
- https://github.com/cheahjs/free-llm-api-resources

Common patterns in Tier 2:
- Shorter free quotas (1-5K tokens/day)
- Higher rate limits → more prone to abuse/IP blocking
- Less frequent model updates
- Higher churn (providers often deprecate or change API without notice)

## Signup Automation Blockers

All three Tier 1 providers use Google OAuth, which cannot be fully automated:

1. **CAPTCHA** — Google detects automated signup attempts and requires human verification
2. **Email confirmation** — Groq sends a verification code to email; must click link manually
3. **Account state** — Browser must be logged into Google already; cannot programmatically log in (violates Google ToS)

**Workaround:** Manual signup is fastest. Estimated time: 2 minutes per provider.

## Testing Signup

After obtaining API key:

```bash
export GROQ_API_KEY="gsk_..."
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "llama-3.1-70b-versatile",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

Should return a response. If you get 401 Unauthorized, the key is wrong or not yet active.

## Fedora Atomic Considerations

Browser automation (headless Chromium) on Fedora Atomic is sandboxed and cannot reach external networks.
For signup flows:
- Use the **headed browser** (DISPLAY=:0 flatpak run org.chromium.Chromium) and click manually
- Or use the system Firefox/Chrome outside of Flatpak sandbox
- Do NOT attempt headless browser automation for OAuth flows

For API testing via curl from terminal, no special handling needed.
