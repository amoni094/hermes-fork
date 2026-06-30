# Provider Capability Matrix

Full reference for all 6 active free-tier providers tested in this session.

## Quick Reference Table

| Provider | Best Use | RPD | Context | Cost | Data Training | Free Tier | Caveat |
|---|---|---|---|---|---|---|---|
| **Groq** | Speed + agentic | 1,000 | 131K | Free | No | Yes | Datacenter IP block, split-tunnel required |
| **Gemini** | Max context | 1,500 | 1M | Free | Yes* | Yes | Outside EU/UK: data training, 1.5K RPM |
| **Cerebras** | Highest volume | 14,400 | **8K** | Free | No | Yes | Hard 8K ctx cap free tier (paid=128K) |
| **SambaNova** | Best reasoning | 20/model | 32-196K | Free | No | Yes | Case-sensitive IDs, DeepSeek-V3.2=32K |
| **Mistral** | Code + context | 1B tok/mo | 262K | Free | Yes* | Yes | Data training default (opt-in) |
| **GitHub Models** | Free GPT-4o | 150-1000 | 131K | Free | No | Yes | PAT zero-scope requirement |

\* Outside EU/UK/EEA/CH. EU users: data not used for training.

## Per-Provider Details

### Groq

**Models (case-insensitive):**
- `llama-3.3-70b-versatile` — general purpose, 131K ctx
- `mixtral-8x7b-32768` — mixture of experts, 32K ctx
- `qwen3:7b` — lightweight inference
- `groq/compound` — agentic tool-use specialist, 131K ctx
- `groq/compound-mini` — lightweight agentic, 32K ctx
- `whisper-large-v3` — free STT (speech-to-text)
- `llama-4-scout` — reasoning model

**Free Tier:**
- 1,000 requests per day
- ~320 tokens/second throughput
- Reset: midnight UTC

**Signup:** https://console.groq.com/ — no credit card, Google OAuth

**Network Blocker:** Cloudflare blocks all datacenter and VPS IP ranges (AS136557, etc.) at API layer. ProtonVPN AU and similar datacenter-routed VPNs fail. Workaround: split-tunnel Groq IPs (172.64.149.20, 104.18.38.236) through residential gateway.

### Google Gemini

**Models:**
- `gemini-2.5-flash` — fastest, free tier, 1M ctx ✓ (RECOMMENDED)
- `gemini-3.5-flash` — also free tier
- `gemini-3.5-pro` — reasoning, paid only
- `gemini-2-flash-thinking-exp` — paid

**Free Tier:**
- 1,500 requests per day
- 15 requests per minute
- 1M token context window
- Reset: midnight Pacific Time

**Data Training:**
- EU/UK/EEA/CH: No training on prompts
- Elsewhere: Training enabled by default (prompts may be used to improve models)

**Signup:** https://aistudio.google.com/app/apikey — no credit card, Google OAuth

### Cerebras

**Models:**
- `gpt-oss-120b` — open-source, reasoning-capable, tested working
- (other inference endpoints available but untested in this session)

**Free Tier:**
- 14,400 requests per day (highest RPD of all free)
- **HARD LIMIT: 8K tokens max context** (paid tier=128K, but free tier absolute cap)
- Reset: midnight UTC

**Signup:** https://cloud.cerebras.ai/ — no credit card, email signup

**Critical Caveat:** 8K context limit is a hard stop, not a soft guidance. Do not attempt prompts >8K on free tier.

### SambaNova

**Models (case-sensitive):**
- `DeepSeek-V3.2` — best reasoning, **32K context** (NOT 128K), tested working
- `Meta-Llama-3.3-70B-Instruct` — instruction-tuned, tested working
- `DeepSeek-V3.1` — older reasoning, 128K context (use if >32K needed)
- `Llama-3.3-70B` — general, 192K context

**Free Tier:**
- 20 requests per model per day
- No data training (explicit no-training guarantee in TOS)
- Explicit privacy commitment

**Signup:** https://cloud.sambanova.ai/ — no credit card, email signup

**Critical Detail:** Model IDs are case-sensitive. DeepSeek-V3.2 != deepseek-v3.2. Test with exact case.

### Mistral

**Models:**
- `codestral-latest` — code specialist, 262K ctx
- `devstral-latest` — development, 262K ctx
- `magistral` — reasoning, 262K ctx
- `open-mistral-*` — various open models

**Free Tier:**
- ~1B tokens per month (approximately 333 req/day at 3K avg tokens)
- No per-request rate limit, only monthly quota
- 262K context window

**Data Training:**
- Experiment plan (free tier): models may be trained on user data by default
- Opt-out available in account settings

**Signup:** https://console.mistral.ai/ — email signup required

**Auth Bug:** Google OAuth occasionally returns 500 during sign-in. Workaround: use email/password signup instead.

### GitHub Models

**Models (via Azure endpoint):**
- `gpt-4o` — free tier access
- `llama-3.1-405b` — free tier access
- `phi-4` — free tier access
- Other paid models also available

**Free Tier:**
- 150-1,000 requests per day (varies by model)
- Rate limits enforced per model
- No data training

**Authentication:**
- Requires GitHub Personal Access Token (PAT)
- PAT must have ZERO scopes (models API explicitly rejects any scopes)
- If needing both models API AND git repo access, create TWO separate PATs

**Signup:** https://github.com/settings/tokens — manual browser creation

**Quirk:** API is hosted at `models.inference.ai.azure.com` not github.com. Uses Authorization Bearer header.

## Quota Reset Times

- **Groq:** midnight UTC
- **Cerebras:** midnight UTC
- **Gemini:** midnight Pacific Time
- **SambaNova:** calendar day UTC (20 per day per model)
- **Mistral:** monthly quota (1B tokens/month)
- **GitHub Models:** daily per model

## Context Window Comparison

For decision-making: which to use by context size needed

| Size | Provider |
|---|---|
| >1M | Gemini (1M) |
| 128K–262K | Mistral (262K), Gemini (1M) |
| 32K–128K | SambaNova Llama-3.3-70B (192K), Mistral (262K), Gemini (1M) |
| <32K | Any (Groq/Cerebras/GitHub Models all 128K+) |
| Absolute max free | Cerebras at **8K hard limit** — use SambaNova or Mistral for >8K |

## Model Quality / Reasoning Ranking (free tier)

Based on session testing and provider specs:

1. **SambaNova DeepSeek-V3.2** — best reasoning (20 req/day limit)
2. **Mistral magistral/codestral** — strong reasoning + code (1B tok/month)
3. **Groq llama-3.3-70b-versatile** — fast, capable (1K req/day)
4. **GitHub Models GPT-4o** — frontier (rare, 150–1000 req/day)
5. **Gemini 2.5 Flash** — very capable (1.5K req/day)
6. **Cerebras gpt-oss-120b** — reasoning capable (14.4K req/day, but 8K ctx)

## Signup Time Estimate

- Groq: 2 min (Google OAuth)
- Gemini: 2 min (Google OAuth)
- Cerebras: 5 min (email verification)
- SambaNova: 5 min (email verification)
- Mistral: 5 min (email, may hit SSO bug)
- GitHub Models: 1 min (already have GitHub account, just create PAT)

## Cost Analysis (Small/Cron Tasks)

If using for auxiliary tasks (compression, title gen, summarization):

- **Cheapest per request:** Cerebras (14.4K RPD free = essentially infinite for small tasks)
- **Best quality per request:** SambaNova (limited to 20/day but highest quality)
- **Largest context:** Gemini (1M window = can compress huge docs)
- **Best fallback:** Groq (fast, reliable, 1K/day usually sufficient)

For high-volume needs (100+ req/day), combine:
1. Primary: Anthropic/Claude (paid fallback)
2. Free 1: Cerebras (14.4K/day, use for compression <8K)
3. Free 2: Groq (1K/day, use for speed-critical tasks)
4. Free 3: Gemini (1.5K/day, use for large context)
5. Fallback: Local Ollama (unlimited, offline)
