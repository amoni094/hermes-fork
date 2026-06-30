---
name: free-llm-provider-integration
title: Free LLM Provider Integration
description: |
  Integrate free-tier and open-source LLM providers into Hermes workflows.
  Covers signup flows, API key management, provider quirks, and routing them
  for small leaf tasks and cron jobs. Now includes 6 providers: Groq, Google 
  Gemini, Cerebras, SambaNova, Mistral, and GitHub Models.

triggers:
  - Configuring free-tier LLM providers in custom_providers
  - Setting up new provider API keys and environment variables
  - Choosing between providers for cost-effective small tasks
  - Troubleshooting OAuth/browser-based signup flows
  - Creating GitHub Personal Access Tokens (PAT) for API access or git operations
  - Adding provider fallbacks to the routing hierarchy
  - Debugging free-tier provider rate limits or quota exhaustion

steps:
  - Identify target providers from references/provider-capability-matrix.md and references/provider-catalog.md
  - Verify provider supports OpenAI-compatible endpoint or Hermes-compatible custom_provider config
  - Check references/provider-caveats-by-session.md for network blockers and auth gotchas
  - Assess signup flow blockers; most Tier 1 require Google OAuth or email verification (cannot automate on Flatpak)
  - For GitHub Models PAT: manual browser creation required; create TWO PATs if needing both models API AND git write access (see references/github-pat-auth-pitfalls.md)
  - For datacenter IP blocks (Groq etc.): see references/groq-vpn-datacenter-workaround.md for split-tunnel systemd service setup
  - Create API key via provider dashboard and store in ~/.hermes/.env as PROVIDER_API_KEY
  - Add custom_provider entry to ~/.hermes/config.yaml with endpoint, api_key_env, and model list (examples in templates/config-example.yaml)
  - Verify model names are case-sensitive (SambaNova DeepSeek-V3.2 not deepseek-v3.2)
  - Run scripts/verify-providers.py to test all keys and endpoints before routing
  - Test with live API call (curl with Authorization header or hermes query --model flag)
  - Document provider in claude-routing-hierarchy skill with capability info and quota
  - For fallback chains: add to config.yaml fallback_providers list and set routing rules in claude-routing-hierarchy
  - When exporting config to shared repo: use references/config-export-workflow.md patterns to sanitize before commit

pitfalls:
  - OAuth flows cannot be automated on Fedora Atomic; browser sandbox blocks CAPTCHA + email confirmation. Manual signup required.
  - GitHub PAT device code flow (gh auth refresh) blocks waiting for user manual entry. Browser session state does NOT persist across CDP restarts.
  - GitHub Models PAT is zero-scope by design. If needing both models API AND git repo access, create TWO separate tokens.
  - Groq blocks datacenter/VPS IPs at Cloudflare layer. ProtonVPN AU and similar fail at API with "Access denied". See references/groq-vpn-datacenter-workaround.md for split-tunnel service setup.
  - Cerebras free tier is HARD CAPPED at 8K tokens context, even though paid is 128K. Do not use for context >8K.
  - SambaNova model IDs are case-sensitive (DeepSeek-V3.2 not deepseek-v3.2). DeepSeek-V3.2 context is 32K not 128K.
  - Mistral Google OAuth occasionally returns 500. Workaround: email/password signup or use key-based API auth directly.
  - Gemini free tier outside EU/UK/EEA/CH uses prompts for training. Use SambaNova for sensitive data or request EU key.
  - Mistral free tier opts into data training by default. Disable in account settings or use SambaNova for privacy.
  - Free tiers have rate limits and daily quotas suitable for leaf tasks, not sustained high-throughput work.
  - API keys are hard to rotate on free tiers. Treat .env file as secret; never commit to git. See references/config-export-workflow.md before sharing repos.

verification:
  - Run curl to list models and verify endpoint connectivity
  - Test routing with hermes model test or hermes query commands
  - Check ~/.hermes/.env contains the key and ~/.hermes/config.yaml references it

related_skills:
  - claude-routing-hierarchy
  - secret-hygiene
---

## Context

Free-tier LLM providers are cost-effective for small, non-critical tasks: verification steps in cron jobs,
quick text processing for leaf agents, low-frequency background work. This skill bundles:

- Provider evaluation (stability, uptime, OpenAI-compatible APIs)
- Signup flows and their automation blockers
- Integration into Hermes config and routing
- Pitfalls specific to free tiers and Fedora Atomic environments

Most providers require manual signup due to OAuth + CAPTCHA. See references/ for signup links and integration details.

## Provider Capability Matrix

Full matrix with quotas, context windows, and tested models in **references/provider-capability-matrix.md**.

Quick reference (as of this session):

| Provider | Strength | RPD | Ctx | Caveat |
|---|---|---|---|---|
| **Groq** | Fastest inference + agentic models | 1,000 | 131K | Datacenter IP block, split-tunnel required |
| **Gemini** | Largest context window | 1,500 | 1M | Data training outside EU |
| **Cerebras** | Highest volume | 14,400 | 8K free | Free tier capped at 8K hard stop |
| **SambaNova** | Best quality reasoning | 20/model | 32–196K | Case-sensitive IDs, DeepSeek-V3.2 is 32K not 128K |
| **Mistral** | Code specialist | ~1B tok/mo | 262K | Data training opt-in |
| **GitHub Models** | Free GPT-4o and Llama-405B | 150–1,000 | 131K | PAT zero-scope requirement |

All 6 tested and active. See references/provider-caveats-by-session.md for provider-specific gotchas (Groq IP block, Cerebras 8K cap, SambaNova case sensitivity, data training, etc.).

## Key Setup Patterns

### GitHub Models (New)

Unique auth: GitHub Personal Access Token with **zero scopes** (models API rejects any scopes).
Setup: already configured as GITHUB_TOKEN in ~/.hermes/.env

```bash
# Verify
GITHUB_TOKEN="ghp_..." curl -s https://models.inference.ai.azure.com/models \
  -H "Authorization: Bearer $GITHUB_TOKEN" | jq '.data | length'
```

See references/github-models-pat-integration.md for full details and quota info.

### Groq (VPN Interaction)

If using ProtonVPN or datacenter-routed VPN: Groq blocks at Cloudflare layer.
Split-tunnel workaround: routing rules to send Groq traffic through home gateway.
Status: groq-split-tunnel.service active (see references/groq-vpn-datacenter-workaround.md)

## Integration Pattern

```yaml
# ~/.hermes/config.yaml
custom_providers:
  groq:
    endpoint: "https://api.groq.com/openai/v1"
    api_key_env: "GROQ_API_KEY"
    models:
      - "llama-3.3-70b-versatile"
      - "mixtral-8x7b-32768"
```

```bash
# ~/.hermes/.env
GROQ_API_KEY="gsk_..."
GITHUB_TOKEN="ghp_..."
CEREBRAS_API_KEY="csk_..."
SAMBANOVA_API_KEY="..."
MISTRAL_API_KEY="..."
GOOGLE_API_KEY="..."
```

Test: `hermes query "hello" --model groq:llama-3.3-70b-versatile`

Then reference in `claude-routing-hierarchy` under `free_providers` section for capability-based routing.

## Common Gotchas

- **GitHub Models PAT scope mismatch:** Models API explicitly rejects tokens with any scopes. If you need repo access, create a separate PAT with `repo` scope for git operations.
- **Cerebras 8K limit:** Free tier hard-caps context at 8K tokens; do not use for long docs or summarization >5K input.
- **SambaNova DeepSeek-V3.2 context:** Has 32K context, not 128K like V3.1. Plan prompts accordingly.
- **Mistral data training:** Free tier opts into training by default. Avoid sensitive prompts or switch to SambaNova for privacy.
- **Quota resets vary:** Groq/Cerebras reset midnight UTC, Gemini resets midnight PT.
