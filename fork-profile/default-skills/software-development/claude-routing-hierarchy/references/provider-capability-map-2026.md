# Configured Providers — Capability Map (verified live 2026-08-30)

## Anthropic (`provider: anthropic`)
Key: `ANTHROPIC_API_KEY` in `.env`

| Model | Context | Status | Best for |
|-------|---------|--------|----------|
| claude-sonnet-4-6 | 200K | LIVE | Daily parent/orchestrator |
| claude-haiku-4-5 | 200K | LIVE | Compression, vision aux |
| claude-opus-4-8 | 1M | LIVE | Long context sessions (200K price cliff) |
| claude-sonnet-5 | 200K | LIVE | Exception-only (1.0–1.35x token cost vs Sonnet 4.6) |
| claude-opus-5 | 1M | LIVE | Exception-only, top-tier reasoning |
| claude-fable-5 | TBC | LIVE | Exception-only (see fable-orchestrate skill) |

## xAI (`provider: xai`)
Key: `XAI_API_KEY` in `.env` · Uses Responses API transport (automatic for Grok 4.x)

| Model | Context | Status | Notes |
|-------|---------|--------|-------|
| grok-4.6 | 500K (use 200K for billing) | LIVE | Default worker/fallback; stall-prone as parent |
| grok-4 | 500K | LIVE | Legacy alias, verified 2026-08-30, 126 out tokens on test |

Note: grok-4.5, grok-4.3 may be discoverable via `hermes model` — not probed 2026-08-30.

## OpenAI — via `openai-api` (first-class provider)
Key: `OPENAI_API_KEY` in `.env` · **Use `openai-api` for all GPT-5.x, NOT `custom:openai`.**
`openai-api` auto-upgrades GPT-5.x to Responses API. `custom:openai` with `chat_completions` → HTTP 400 when tools loaded.

| Model | Input $/M | Output $/M | Context | Status | Notes |
|-------|-----------|------------|---------|--------|-------|
| gpt-5.6-sol | $4.00 | $20.00 | 1.05M | LIVE | Adversarial review; verified via openai-api 2026-08-30 |
| gpt-5.6-luna | ~$0.80 | ~$4.00 | 1.05M | LIVE | 80% price cut July 2026; cheaper adversarial option |
| gpt-5.5 | $5.00 | $30.00 | 1.05M | LIVE | 2-call bootstrap (0 tokens then actual) — normal Responses API |
| gpt-5.4 | $2.50 | $15.00 | 1.05M | Wired | Via custom:openai if needed |
| gpt-5.4-mini | $0.75 | $4.50 | 1.05M | Wired | Via custom:openai |

## OpenAI — via `custom:openai` (legacy path, keep for gpt-4.x ONLY)
`api_mode: chat_completions` · gpt-4.1/gpt-4.1-mini still need this path.
DO NOT use for GPT-5.x — triggers HTTP 400 when tools are loaded.

| Model | Status | Notes |
|-------|--------|-------|
| gpt-4.1 | OK | Legacy chat_completions works |
| gpt-4.1-mini | OK | Cheap legacy option |

## Mistral (`provider: mistral`)
Key: `MISTRAL_API_KEY` in `.env` · Quota ~1B tokens/month · Data training opt-in required.

| Model | Context | Status | Best for |
|-------|---------|--------|----------|
| mistral-small-latest | 262K | LIVE | Mechanical aux (titles, triage, curator) |
| mistral-large-latest | 262K | LIVE | Fallback chain #2 |
| devstral-latest | 262K | LIVE verified 2026-08-30 | Coding agent sessions, multi-file edits |
| magistral-small-latest | 262K | LIVE verified 2026-08-30 | Reasoning tasks, lighter than Grok delegation |
| codestral-latest | 256K | Wired | Code completion |
| mistral-medium-latest | 262K | Wired | Stronger general reasoning |
| ministral-8b-latest | 262K | Wired | Tiny/fast, high volume |
| mistral-medium-2508 | 262K | Newly discovered | Untested 2026-08-30 |

DO NOT set `reasoning_effort` on any Mistral model — 422 `extra_forbidden`. This caused compression stall loop (fixed 2026-08-29).

## SambaNova (`provider: sambanova` via custom_providers)
Base URL: `https://api.sambanova.ai/v1` · Key: `SAMBANOVA_API_KEY` · Quota: ~20 RPD per model (permanent low quota)

| Model | Context | Status | Notes |
|-------|---------|--------|-------|
| gemma-4-31B-it | 131K | LIVE (200 OK) | Live last-resort fallback #3 |
| DeepSeek-V3.2 | 32K | 429 (rate-limited) | Previously in fallback chain |
| DeepSeek-V3.1 | 131K | Wired | Long-context DeepSeek |
| gpt-oss-120b | 131K | 429 (rate-limited 2026-08-30) | Heavy reasoning |
| MiniMax-M3 | ~32K | 429 (rate-limited 2026-08-30) | High demand |
| MiniMax-M2.7 | 196K | Wired | Longest context on SambaNova |
| Meta-Llama-3.3-70B-Instruct | 131K | Wired | General long-context |

## Cerebras (`provider: cerebras` via custom_providers)
Base URL: `https://api.cerebras.ai/v1` · Key: `CEREBRAS_API_KEY`

| Model | Status | Notes |
|-------|--------|-------|
| gpt-oss-120b | 402 Payment Required | Free trial exhausted |
| gemma-4-31b | 402 Payment Required | Free trial exhausted |

Cerebras REMOVED from fallback chain 2026-08-29. Do not re-add without a paid tier.

## Summary: What's Actually Working (2026-08-30)

Live and callable without fallback:
- anthropic: sonnet-4-6, haiku-4-5, opus-4-8, sonnet-5, opus-5, (fable-5)
- xai: grok-4.6, grok-4
- openai-api: gpt-5.6-sol, gpt-5.6-luna, gpt-5.5
- mistral: mistral-small-latest, mistral-large-latest, devstral-latest, magistral-small-latest
- sambanova: gemma-4-31B-it (only)

Dead / rate-limited:
- cerebras: all models (402)
- sambanova: gpt-oss-120b, MiniMax-M3 (429)
- custom:openai for GPT-5.x (400 — wrong transport)
