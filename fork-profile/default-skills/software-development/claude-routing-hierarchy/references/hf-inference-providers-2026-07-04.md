# HF Inference Providers — Research Notes (2026-07-04)

## Status
> **Correction (2026-07-06):** the line below claiming "HF_TOKEN is already present" is WRONG.
> Direct check (`grep '^HF_TOKEN' ~/.hermes/.env`) returns nothing — the `.env` only has a
> commented-out placeholder (`# HF_TOKEN=...`) from the template, not an active key. HuggingFace
> is genuinely unprovisioned on this instance, matching the ground-truth table in the parent
> `claude-routing-hierarchy/SKILL.md`. Re-verify live before reusing this note.

HF_TOKEN placeholder exists (commented out) in ~/.hermes/.env — not an active key.
Hermes natively supports HF Inference Providers — confirmed in official HF docs:
https://huggingface.co/docs/inference-providers/integrations/hermes-agent

Not yet added as a custom_provider in config.yaml, and no active token to add it with. To activate:
- Uncomment/add a real `HF_TOKEN` in `.env`
- Add a custom provider with base_url: https://router.huggingface.co/v1
- API key: HF_TOKEN
- OpenAI-compatible wire format (chat completions only via the router)
- For non-chat tasks use huggingface_hub InferenceClient directly

## Router endpoint
https://router.huggingface.co/v1 — OpenAI-compatible, chat completions only.
Routing suffixes: `:fastest` (auto, highest throughput), `:groq`, `:cerebras`, `:together` etc.
Model listing: GET /v1/models returns all available models with per-provider pricing + latency.

## Provider coverage via HF router
Gaps filled that current free tiers do NOT cover:

| Provider (via HF) | Chat | VLM | Embeddings | Image | Video | STT |
|---|---|---|---|---|---|---|
| Featherless AI | ✅ | ✅ | | | | |
| DeepInfra | ✅ | ✅ | | | | |
| Together AI | ✅ | ✅ | | ✅ | | |
| Novita | ✅ | ✅ | | | ✅ | |
| Nscale | ✅ | ✅ | | ✅ | | |
| Replicate | | | | ✅ | ✅ | ✅ |
| WaveSpeedAI | | | | ✅ | ✅ | |
| HF Inference (native) | ✅ | ✅ | ✅ | ✅ | | ✅ |

Providers already covered by direct keys on this instance (Cerebras, Mistral, SambaNova) are also
available via HF router but add no new capability. Correction (2026-07-06): Groq, Gemini, and
GitHub Models were listed here as "already covered by direct keys" — verified live `.env` check
shows none of those three actually have a key on this instance. Do not treat them as configured.

## Key value-adds vs current stack
1. **Featherless AI**: largest open-model catalogue, rare/niche models unavailable elsewhere — no direct API.
2. **Image gen fallback**: Together AI + Nscale + Replicate all serve image generation via single HF token.
3. **Text-to-video**: Novita + Replicate + WaveSpeedAI — no current video gen provider in the stack.
4. **Embeddings**: HF native inference can serve feature extraction without local Ollama dependency.
5. **VLM breadth**: DeepInfra and Featherless expand VLM options significantly.

## CivitAI assessment
CivitAI is a community hub for Stable Diffusion LoRAs and checkpoints — local SD only.
No API surface integrates with Hermes tooling. Not actionable unless a local SD server is set up.
Revisit only if ComfyUI/Automatic1111 is deployed locally.

## Activation config snippet (not yet applied)
```yaml
custom_providers:
  hf:
    base_url: https://router.huggingface.co/v1
    api_key: ${HF_TOKEN}
    # OpenAI-compatible; chat completions only via router
    # Use for: Featherless models, image gen (Together/Nscale), VLM tasks
```

## Routing suggestions when activated
- Featherless model access: `provider: custom:hf`, model as `featherless-ai/<model>`
- Image gen fallback: `provider: custom:hf`, model as `<image-model>:together` or `:nscale`
- Embeddings (non-Ollama): use InferenceClient directly, not the router
