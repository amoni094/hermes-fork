> **SUPERSEDED 2026-08-25 — do not apply.** Live aux/leaves are
> `mistral-small-latest` / mistral. `zai-glm-4.7` is archived (404). Cerebras
> remaining models are quota-exhausted. Canonical: parent `claude-routing-hierarchy/SKILL.md`.
> Historical note (2026-07-06): Groq/Gemini/GitHub Models keys were not present.

# Free-Tier Auxiliary Task Routing (2026 Session Data)

## Discovery context
Hermes config uses Anthropic Haiku for several mechanical auxiliary tasks that can be fulfilled by free-tier providers, saving 15–20% of session costs with no quality loss. This reference documents the session-specific routing pattern applied 2026-07-01.

## Auxiliary tasks worth moving to free tier

| Task | Original | Free alternative | Why | Notes |
|------|----------|-------------------|-----|-------|
| `triage_specifier` | haiku-4-5 | cerebras/gpt-oss-120b | <8K output, no reasoning needed | Label + summary classification only |
| `kanban_decomposer` | haiku-4-5 | gemini-2.5-flash | Needs multimodal capability, 1.5K RPD plenty | Kanban cards may include images; Gemini has higher capacity |
| `monitor` | haiku-4-5 | cerebras/gpt-oss-120b | Simple pass/fail checks, <8K | Health status reporting, threshold checks |
| `background_review` | haiku-4-5 | custom:groq/llama-3.3-70b | ~131K context, zero timeout risk | Code review on medium-sized diffs; Groq faster than Haiku |
| `approval` | auto | custom:github-models/gpt-4o | Frontier quality, free, no training concerns | Final go/no-go decisions benefit from GPT-4 class capability |
| `profile_describer` | sonnet-4-6 | gemini-2.5-flash | One-off descriptor, does not need Sonnet reasoning | Profile generation is templated, not complex reasoning |

## Fallback chain improvement
Current chain: `gemini -> cerebras -> local`. Gap: Groq (1K RPD, 131K ctx, faster inference) is not in the chain despite being configured.

Proposed: `groq/llama-3.3-70b -> gemini-2.5-flash -> cerebras/gpt-oss-120b -> local/qwen3:8b`

Benefits:
- Groq catches fast tasks first (320 tok/s avg inference)
- Gemini acts as high-capacity backup (1M ctx, generous RPD)
- Cerebras covers tight 8K windows and massive throughput (14.4K RPD)
- Local fallback still available if all API keys are exhausted

## Implementation notes
- **SambaNova, Mistral not yet wired.** Both have strong free tiers; SambaNova best for one-shot reasoning quality (DeepSeek-V3.2, 32K ctx, 20 RPD); Mistral for high-volume code (codestral, 256K ctx, 1B tok/mo). Consider adding for specific cron jobs rather than auxiliary tasks.
- **GitHub Models `gpt-4o` for approval** saves Anthropic usage while maintaining frontier-class quality. Requires separate `GITHUB_TOKEN` (zero scopes) — already configured.
- **Groq in fallback requires split-tunnel routing** on this host (ProtonVPN blocks datacenter IPs). The `groq-split-tunnel.service` user systemd unit handles this automatically at login — verify with `systemctl --user status groq-split-tunnel.service`.

## Costs saved estimate (rough)
- haiku-4-5: ~$0.80 per 1M in / $2.40 per 1M out
- cerebras/gpt-oss-120b (free): $0
- gemini-2.5-flash (free): $0
- groq/llama-3.3-70b (free): $0
- github-models/gpt-4o (free): $0

Shifting 4 heavy auxiliary tasks (triage, kanban, monitor, background_review) from Haiku to free tiers could reduce monthly costs by ~$8–12 on a typical Hermes user profile (2–3 heavy auxiliary ops per session, ~100 sessions/month). Not huge in isolation but compounds with other slots.
