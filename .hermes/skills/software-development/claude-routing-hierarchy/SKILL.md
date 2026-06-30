---
name: claude-routing-hierarchy
description: Model routing hierarchy for Hermes — Anthropic primary, free tier providers for cron/leaf/auxiliary tasks. Capability-based decision matrix with context windows, quotas, and fallback chains.
version: 3.0.0
author: Hermes
---

# Claude Routing Hierarchy

## Primary Anthropic hierarchy

| Role | Model | When to use |
|------|-------|-------------|
| Main session | claude-sonnet-4-6 | Default orchestration |
| Delegation workers | claude-opus-4-8 | Security, architecture, research synthesis |
| Auxiliary / cheap | claude-haiku-4-5 | High-volume internal ops |
| Escalation peak | claude-fable-5 | Formal verification, adversarial red-team, large-doc synthesis, max reasoning |

Escalation rules:
- Prefer claude-opus-4-8 delegation for: security audits, arch decisions, exhaustive research
- Prefer claude-fable-5 ONLY when: correctness > cost, >100K token synthesis, max reasoning required
- Do NOT escalate for: routine edits, simple debug, summarization, token-heavy but low-judgment work

---

## Fallback chain (config.yaml fallback_providers)

Fires automatically when Anthropic is unavailable/429/timeout:
  1. anthropic / claude-sonnet-4-6          (primary)
  2. gemini / gemini-2.5-flash              (free, 15 RPM, 1M ctx)
  3. custom:cerebras / gpt-oss-120b         (free, high RPD, 8K ctx cap on free tier)
  4. custom:local / qwen3:8b               (offline, always available)

---

## Free tier providers — full capability map

### Groq (provider: custom:groq)
Key: GROQ_API_KEY — Note: blocked from datacenter IPs; split-tunnel routes active via groq-split-tunnel.service
Quota: 1,000 RPD, 30 RPM
Strength: fastest inference (~320 tok/s on 70B), low latency

| Model | Context | Best for |
|-------|---------|----------|
| llama-3.3-70b-versatile | 131K | General reasoning, fast cron tasks |
| llama-3.1-8b-instant | 131K | Ultra-fast simple tasks |
| qwen/qwen3-32b | 131K | Strong reasoning, math |
| qwen/qwen3.6-27b | 131K | Balanced reasoning/speed |
| openai/gpt-oss-120b | 131K | Heavy reasoning at speed |
| meta-llama/llama-4-scout-17b-16e-instruct | 131K | Multimodal (text+image) |
| groq/compound | 131K | Agentic/tool-use tasks |
| groq/compound-mini | 131K | Lightweight agentic tasks |
| whisper-large-v3 | - | Speech-to-text (free!) |

### Cerebras (provider: custom:cerebras)
Key: CEREBRAS_API_KEY
Quota: 14,400 RPD, 30 RPM — highest volume free tier
CRITICAL: free tier caps context at 8K tokens (128K is paid only)
No data training policy

| Model | Free ctx | Best for |
|-------|----------|----------|
| gpt-oss-120b | 8K | Fast classification, short summarization |
| gemma-4-31b | 8K | Lightweight reasoning, short tasks |
| zai-glm-4.7 | 8K | Alternative short-context model |

### SambaNova (provider: custom:sambanova)
Key: SAMBANOVA_API_KEY
Quota: 20 RPD per model (low but permanent, no data training)
Strength: best quality per request, no training data concerns, good for privacy-adjacent tasks

| Model | Context | Best for |
|-------|---------|----------|
| DeepSeek-V3.2 | 32K | Best reasoning quality (note: 32K not 128K) |
| DeepSeek-V3.1 | 131K | Long-context DeepSeek tasks |
| gpt-oss-120b | 131K | Heavy reasoning, long context |
| MiniMax-M2.7 | 196K | Longest context on SambaNova |
| Meta-Llama-3.3-70B-Instruct | 131K | General long-context tasks |
| gemma-4-31B-it | 131K | Instruction following |

### Mistral (provider: custom:mistral)
Key: MISTRAL_API_KEY
Quota: ~1B tokens/month (most generous by volume), ~1 RPS, 500K TPM
Warning: data training opt-in required — avoid sensitive prompts
Strength: very long context (up to 262K), specialized models for code/reasoning

| Model | Context | Best for |
|-------|---------|----------|
| codestral-latest | 256K | Code generation, completion, review |
| devstral-latest | 262K | Agentic coding tasks, multi-file edits |
| mistral-small-latest | 262K | Fast general tasks |
| mistral-medium-latest | 262K | Stronger general reasoning |
| magistral-small-latest | 262K | Reasoning/thinking tasks |
| ministral-8b-latest | 262K | Tiny fast model, high volume |

### Google Gemini (provider: gemini)
Key: GOOGLE_API_KEY
Warning: prompts used for training outside EU/UK/EEA/CH
Strength: largest free context window (1M tokens), multimodal, generous RPD

| Model | Context in | Context out | RPD | Best for |
|-------|-----------|------------|-----|----------|
| gemini-2.5-flash | 1M | 65K | 1,500 | Long docs, multimodal, general |
| gemini-3.5-flash | 1M | 65K | 1,500 | Newest, strong quality |
| gemini-3.1-flash-lite | 1M | 65K | 1,500 | High-volume lightweight |
| gemma-4-31b-it | 262K | 32K | 1,500 | No-training-concern alternative |
| gemini-2.5-pro | 1M | 65K | 50 | Strongest Gemini, save for hard tasks |

### GitHub Models (provider: custom:github-models)
Key: GITHUB_TOKEN (classic PAT, **zero scopes** — already configured)
base_url: https://models.inference.ai.azure.com
Quota: 150–1,000 RPD, 15 RPM (varies by model; Llama-405B is ~150)
No data training policy
Strength: frontier model access (GPT-4o, Llama 405B) for free
Important: Models API rejects any scoped tokens. If you need git/repo access, create a separate PAT with `repo` scope.

| Model | Context | Best for |
|-------|---------|----------|\n| gpt-4o | 128K | GPT-4 quality without Anthropic billing |
| gpt-4o-mini | 128K | Faster/cheaper GPT-4 class |
| Meta-Llama-3.1-405B-Instruct | 131K | Largest free open model available |
| Meta-Llama-3.1-8B-Instruct | 131K | Fast small open model |

---

## Capability-based routing decision matrix

| Scenario | Model | Provider | Why |
|----------|-------|----------|-----|
| Context >128K tokens | gemini-2.5-flash | gemini | Only free provider with 1M ctx |
| Context 32K–128K, code | codestral-latest | custom:mistral | 256K ctx, purpose-built for code |
| Context 32K–128K, general | gpt-oss-120b | custom:sambanova | 131K ctx, no data training |
| Context <8K, max throughput | gpt-oss-120b | custom:cerebras | 14,400 RPD, ~2600 tok/s |
| Speed-critical / real-time | llama-3.3-70b-versatile | custom:groq | ~320 tok/s, lowest latency |
| GPT-4 quality, free | gpt-4o | custom:github-models | Frontier model, no billing |
| Largest open model | Meta-Llama-3.1-405B-Instruct | custom:github-models | 405B params, free |
| Agentic coding (multi-file) | devstral-latest | custom:mistral | Purpose-built dev agent |
| Agentic tool-use | groq/compound | custom:groq | Built for tool calling |
| Reasoning / thinking | magistral-small-latest | custom:mistral | 262K + reasoning |
| Reasoning (privacy-safe) | gpt-oss-120b | custom:sambanova | No data training |
| Multimodal (image+text) | llama-4-scout-17b-16e | custom:groq | Free multimodal, 131K |
| Speech-to-text | whisper-large-v3 | custom:groq | Free STT |
| Daily one-shot best quality | DeepSeek-V3.2 | custom:sambanova | Best reasoning, 20 RPD |
| High-volume code (>100 calls/day) | codestral/ministral-8b | custom:mistral | 1B tok/month budget |
| Privacy-sensitive non-Anthropic | gpt-4o or Llama-405B | custom:github-models | No data training |
| Offline / no network | qwen3:8b | custom:local | Always available |
| Anthropic primary orchestration | claude-sonnet-4-6 | anthropic | Default |
| Security / architecture | claude-opus-4-8 | anthropic | Strongest reasoning |
| Max reasoning, high-stakes | claude-fable-5 | anthropic | Escalation only |

---

## Auxiliary task routing (config.yaml)

Internal Hermes ops — routed to free tier to save Haiku credits:

| Task | Provider | Model |
|------|----------|-------|
| compression | custom:cerebras | gpt-oss-120b (fast, fits in 8K) |
| summarization | custom:cerebras | gpt-oss-120b |
| title_generation | gemini | gemini-2.5-flash |
| skills_hub | gemini | gemini-2.5-flash |
| everything else | anthropic | claude-haiku-4-5 |

---

## Cron job patterns

Hermes does NOT auto-cascade fallback_providers for cron jobs — model is fixed at creation.

Pattern A — high volume, short context (<8K):
  model={"provider": "custom:cerebras", "model": "gpt-oss-120b"}

Pattern B — long context, multimodal, daily briefings:
  model={"provider": "gemini", "model": "gemini-2.5-flash"}

Pattern C — code-related cron (non-sensitive):
  model={"provider": "custom:mistral", "model": "codestral-latest"}

Pattern D — best quality, once-daily task:
  model={"provider": "custom:sambanova", "model": "DeepSeek-V3.2"}

Pattern E — frontier quality, privacy-safe:
  model={"provider": "custom:github-models", "model": "gpt-4o"}

Pattern F — speed-critical or tool-calling:
  model={"provider": "custom:groq", "model": "groq/compound-mini"}

Pattern G — Anthropic with auto-fallback:
  model={"provider": "anthropic", "model": "claude-haiku-4-5"}
  (fallback chain: gemini -> cerebras -> local kicks in if Anthropic is down)

---

## Provider quick-reference

| Provider | RPD | Context | Data training | No-credit-card |
|----------|-----|---------|---------------|----------------|
| Groq | 1,000 | 131K | No | Yes |
| Cerebras | 14,400 | 8K (free) | No | Yes |
| SambaNova | 20/model | 32K–196K | No | Yes |
| Mistral | ~1B tok/mo | 256K–262K | YES (opt-in req) | Yes |
| Gemini | 1,500 (Flash) | 1M | YES (outside EU) | Yes |
| GitHub Models | 150–1,000 | 128–131K | No | Yes |
| Local Ollama | unlimited | hardware | No | N/A |

## Notes

- **GitHub Models PAT:** GITHUB_TOKEN has zero scopes by design (models API explicitly rejects scoped tokens). If you need git/repo access later, create a separate PAT with `repo` scope — do NOT try to reuse or upgrade the models token.
- Groq requires split-tunnel routing on this machine (ProtonVPN blocks it); groq-split-tunnel.service handles this automatically at login.
- Cerebras 8K context cap on free tier is a hard limit — do not use for long documents.
- SambaNova DeepSeek-V3.2 has 32K ctx (not 128K like V3.1) — plan prompts accordingly.
- Mistral 1B token/month budget sounds large but codestral can burn through it quickly on large codebases.
- Gemini free tier quota resets midnight PT; Cerebras/Groq reset midnight UTC.
- GitHub Models has no expiration — stored as GITHUB_TOKEN (separate from repo-scoped PAT if created).
- For STT tasks, Groq whisper-large-v3 is free and excellent — use before paying for other STT.
- OpenRouter not configured (50 RPD too low without $10 topup) — add OPENROUTER_API_KEY if topup added.
