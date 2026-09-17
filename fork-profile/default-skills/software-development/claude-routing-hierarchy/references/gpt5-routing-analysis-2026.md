# Should gpt-5.4/gpt-5.5 Replace or Join Default/Fallback/Delegation Routing? — No (researched 2026-07-06)

Both models are now reachable (see openai-provider-setup-notes-2026-07-05.md for config details)
but were deliberately NOT added to `model:`, `fallback_model`, or `delegation` after a research
pass (academic/benchmark + GitHub + Reddit + non-English sources per user's standing native-venue
research requirement):

- **SWE-bench Pro** (llm-stats.com, July 2026 snapshot): Claude Sonnet 5 0.632 @ $3/$15 per M
  beats both GPT-5.5 (0.586 @ $5/$30) and GPT-5.4 (0.577 @ $2.50/$15) — Sonnet 5 is strictly
  dominant vs GPT-5.5 (higher score, cheaper both directions) and higher-scoring than GPT-5.4 at
  a comparable/cheaper output-token price. No cost-quality case for swapping the default or
  fallback tier.
- **OSWorld / computer-use tasks**: Sonnet 5 leads (~81%) — another vote against GPT-5.x for
  this account's actual workload mix (this profile does a lot of computer_use/browser work).
- Reddit (`r/ChatGPTCoding`, `r/OpenAI`, `r/codex`) discussion is mixed/anecdotal and doesn't
  contradict the benchmark gap; no thread made a quality-adjusted cost case for switching either.
- GitHub search for router configs pinning gpt-5.4/5.5 as a default over Sonnet-class models
  turned up nothing structurally different from this account's existing pattern (small
  provider set, explicit override for cross-checks).
- Non-English pass (per user's CNKI/CiNii/HAL native-venue standard): searched CNKI (大语言模型
  路由 多模型协同), CiNii (LLM ルーティング), HAL (routage multi-LLM) — no independent non-English
  empirical study surfaced that favors GPT-5.x over Claude for coding/agentic tasks or for
  non-English task quality specifically. The multi-LLM routing survey found (HAL preprint) is
  consistent with the English-language conclusion: calibrated routing on cost/difficulty beats
  ad hoc "add a bigger model" moves.
- Aligns with the existing FrugalGPT/RouteLLM-grounded stance (small, well-understood provider
  set beats a wide loosely-managed pool) and the MAST/UCCI-grounded escalation policy — gpt-5.4/5.5
  don't clear any of the four escalation triggers (>200K context need, explicit user ask,
  security/arch signoff, reconciling contradictory subagent output) as a *routing default*; they
  remain available for **explicit** manual/cross-provider-review use only
  (`-m gpt-5.4 --provider custom:openai` or `-m gpt-5.5`).

If OpenAI ships a model that actually leads SWE-bench Pro/OSWorld at comparable or lower cost,
re-run this comparison before touching `model:`/`fallback_model`/`delegation` — don't assume a
version-number bump alone justifies a routing change.

## Exception — Cross-Family Verifier Role

`hermes-role-pipelines`'s Verification-Gated Escalation section flags that a same-family judge
(claude-haiku-4-5 judging claude-sonnet-5 output) has measurable self-preference bias
(Wataoka et al., NeurIPS 2024 Safe GenAI workshop, arXiv:2410.21819 — LLM judges score
lower-perplexity/more-familiar outputs higher, and same-family outputs are lowest-perplexity to
a same-family judge). This does not argue for adding gpt-5.4/5.5 to `model:`/`fallback_model`/
`delegation` — it's a case for using the already-wired `custom:openai` provider (gpt-5.4-nano/
gpt-4.1-nano are cheap enough) as the independent judge specifically in a verification gate,
called explicitly per-verification, not auto-routed.

Keep this distinction sharp: routing-default = no; scoped cross-family verifier = yes, when a
same-family judge would otherwise be the only check available.

## Should More Providers Be Added? — No, Not Right Now

| Candidate | Reason to add | Reason to skip |
|-----------|---------------|-----------------|
| Groq | Fast LPU inference | No key configured |
| Google Gemini | 1M context, multimodal | No key configured |
| GitHub Models | Free frontier models | No token configured |
| OpenRouter | Unified multi-model routing | No key; adds a routing hop + cost markup |
| HuggingFace router | Fills image/video/VLM gaps | `HF_TOKEN` line exists in `.env` but is commented out (`# HF_TOKEN=...`) — not an active key. Verify with `grep '^HF_TOKEN' ~/.hermes/.env` (empty = inactive). |

Three configured free-tier providers (Cerebras, SambaNova, Mistral) already cover: max-throughput
short tasks, best one-shot reasoning quality, and long-context/code specialization. Per cascade-
routing literature (FrugalGPT, RouteLLM, arXiv:2410.10347), a well-understood small provider set
with a good escalation signal beats a wide, loosely-managed provider list — this favors NOT
adding more providers over expanding the pool.
