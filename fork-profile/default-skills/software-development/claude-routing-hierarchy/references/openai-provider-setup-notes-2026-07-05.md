# OpenAI Provider Setup Notes — 2026-07-05 (updated 2026-07-06)

> **UPDATE 2026-07-06:** the "ZERO QUOTA" finding below is now STALE — a direct curl retest on
> 2026-07-06 (`gpt-4.1-nano` chat completion) returned a real, well-formed response. Billing
> status on this account has flipped at least once between the two dates. Treat quota state as
> perishable external state, not a fact this repo controls — always re-test live
> (`curl https://api.openai.com/v1/chat/completions ...`) before trusting either this note or the
> "it works now" follow-up. Everything else below (transport mismatch, custom_providers fix,
> model list, cost table) is still architecturally accurate and unaffected by quota state.

## Confirmed Working Config (2026-07-06)

`custom_providers` entry now exists in config.yaml and is live-verified end-to-end through Hermes:

```yaml
custom_providers:
  - name: openai
    base_url: https://api.openai.com/v1
    key_env: OPENAI_API_KEY
    api_mode: chat_completions
    context_length: 128000
    max_output_tokens: 16384
    models:
      gpt-5.4:
        context_length: 1050000
      gpt-5.5:
        context_length: 1050000
```

**Fixed 2026-07-06**: added per-model `context_length` override for gpt-5.4/gpt-5.5 (~1.05M each).
The `models.<id>.context_length` key IS supported by Hermes' `custom_providers` schema.

**IMPORTANT footgun**: `hermes config set custom_providers.0.models.gpt-5.4.context_length ...`
(dotted-path CLI form) BREAKS on literal dots inside a model id — it splits `gpt-5.4` into
nested keys `gpt-5` → `4`, producing garbage YAML. Editing `custom_providers[].models` entries
whose key contains a dot must be done via a direct `python3 -c "import yaml; ..."` read-modify-write
(use `terminal`, not blocked). Always re-run `hermes config check` after.

Usage: `hermes chat -m gpt-4.1-nano --provider custom:openai -q "..."` or as delegation override:
`model={"provider": "custom:openai", "model": "gpt-4.1"}`.

## Pitfall: `hermes config set <key> '<json-array-or-object>'` silently stringifies instead of parsing

`hermes config set` only coerces scalar values (`true`/`false`/int/float/bare string) — it does
NOT parse a JSON array or object passed as the value string. Running
`hermes config set custom_providers '[{"name":"cerebras",...}, ...]'` "succeeds" (prints
`✓ Set custom_providers = [...]`) but writes the ENTIRE array as one literal YAML string
(`custom_providers: '[{"name":"cerebras",...}]'`), not a YAML list — silently corrupting any
config key that is supposed to be list- or dict-shaped. **Never use `hermes config set` for a
list/dict-valued key** (e.g. `custom_providers`, `fallback_model`, `auxiliary`) — instead do a
direct read-modify-write:
```python
import yaml, sys
sys.path.insert(0, '/var/home/rainbow/.hermes/hermes-agent')
path = '/var/home/rainbow/.hermes/config.yaml'
cfg = yaml.safe_load(open(path, encoding='utf-8'))
cfg['custom_providers'] = [...]  # build the real Python list/dict here
from utils import atomic_yaml_write
atomic_yaml_write(path, cfg, sort_keys=False)
```
Run via `terminal` (not blocked), then verify with `python3 -c "... print(type(cfg[...]))"`
and `hermes config check` / `hermes doctor` before trusting the write.

## Pitfall: CLI chat path ignores custom_providers `max_output_tokens` — gateway path honors it

- `gateway/run.py` reads `custom_providers[].max_output_tokens` and applies it correctly.
- `cli.py`'s `self.max_tokens` only reads `HERMES_MAX_TOKENS` (env var) or the global `model.max_tokens`
  — never a named custom_providers entry's cap. Result: even with `max_output_tokens: 16384` set,
  plain `hermes chat --provider custom:openai` sends Hermes' default 65536 max_tokens, and OpenAI
  rejects it:
  ```
  HTTP 400: max_tokens is too large: 65536. This model supports at most 32768 completion tokens.
  ```
  Workaround: `HERMES_MAX_TOKENS=8192 hermes chat -m gpt-4.1-nano --provider custom:openai -q "..."`.
  Do NOT set `model.max_tokens` globally — it caps every provider including Anthropic.

Confirmed working models through custom:openai: gpt-4.1-nano, gpt-4.1, gpt-4o, o3-mini, o4-mini.
Codex-tier models (gpt-5-codex, gpt-5.1-codex-mini, gpt-5.3-codex) fail with 400 — Responses
endpoint only; would need a second `custom_providers` entry with `api_mode: responses`.

## Model Catalog + Pricing (verified live 2026-07-06)

| Model | Input $/M | Output $/M | Works via `custom:openai`? | Notes |
|-------|-----------|------------|----------------------------|-------|
| gpt-5.5 | $5.00 | $30.00 | Yes | Flagship, 1.05M ctx |
| gpt-5.5-pro | $30.00 | $180.00 | Yes | Highest tier |
| gpt-5.4 | $2.50 | $15.00 | Yes | Best balance for explicit cross-provider review |
| gpt-5.4-mini | $0.75 | $4.50 | Yes | Mid-cheap non-reasoning |
| gpt-5.4-nano | $0.20 | $1.25 | Yes | Cheapest usable; preferred for cheap-task routing |
| gpt-5.3-codex | $1.75 | $14.00 | **No** — 400 "not supported in v1/chat/completions" |
| gpt-5-codex, gpt-5.1-codex-mini | n/a | n/a | **No** — same Responses-endpoint-only error |
| o3-mini | $1.10 | $4.40 | **Yes — confirmed working** | `reasoning_tokens` populated |
| o4-mini | $1.10 | $4.40 | **Yes — confirmed working** | Same behavior as o3-mini |
| gpt-4.1, gpt-4.1-mini, gpt-4.1-nano | legacy | — | Yes | Prefer gpt-5.4-nano for new routing |
| gpt-4o, gpt-4o-mini | legacy | — | Yes | Being superseded |

See `provider-capability-map-2026.md` for full OpenAI model table alongside other providers.

## History: Key findings from initial activation attempt (2026-07-05)

### OPENAI_API_KEY is in .env but the account had ZERO QUOTA as of 2026-07-05 (see update above)
Direct curl to `https://api.openai.com/v1/chat/completions` returns:
```
You exceeded your current quota, please check your plan and billing details.
```
The key is structurally valid (sk-proj-...) but the account had no credits as of this test.
Fix: https://platform.openai.com/settings/billing — add payment + credits ($5–10 is enough to start).

A ChatGPT Plus/Pro subscription does NOT fix this — that's a separate billing account from the API.

### Built-in `openai-api` provider uses the WRONG transport for chat models
Hermes has a built-in provider `openai-api` (auth.py, id="openai-api") that:
- Uses `codex_responses` transport (OpenAI Responses API — designed for o-series reasoning models)
- Points to `https://api.openai.com/v1`
- Reads `OPENAI_API_KEY`

When you try to use it with a chat model like gpt-4.1:
```
hermes -m gpt-4.1 --provider openai-api -z "hi"
→ HTTP 400: Encrypted content is not supported with this model.
```
This is because the Responses API sends `encrypted_content` replay headers that chat/completions models reject.

**Do NOT use `--provider openai-api` for gpt-4.1, gpt-4.1-mini, o4-mini, etc.**

### Correct approach: custom_providers with openai_chat transport
`custom_providers` in config.yaml always uses `openai_chat` transport (chat completions endpoint).
This is the correct transport for all gpt-4.x and o4-mini models.

Note: o3 and o4-mini might also work via `openai-api` (Responses transport), since they are
reasoning/o-series models. Only gpt-4.x definitely needs `custom:openai` (chat transport).

### History of getting here (superseded framing)

Key was present in `.env`. Billing/quota status is NOT stable — it has flipped between sessions
before. Points below describe the state BEFORE 2026-07-06 fix:

1. **Quota**: previously reported as zero (2026-07-05 curl returned "exceeded your current quota"),
   but a direct test on 2026-07-06 returned a real, well-formed response — quota was funded/working.
   Treat both states as perishable; re-test before relying on either claim.
2. **No `custom_providers` entry in config.yaml** — not invokable as `custom:openai`, independent
   of quota state. Verify with `grep custom_providers ~/.hermes/config.yaml`.
3. Hermes' built-in `openai-api` provider uses the Responses API transport (`codex_responses`),
   which rejects chat models like gpt-4.1 with a 400 error ("Encrypted content is not supported
   with this model"). Only a `custom_providers` entry with the default `openai_chat` transport
   works for gpt-4.x models. o3/o4-mini (reasoning models) may work via the native `openai-api`
   provider instead — untested end-to-end through Hermes.

If/when a `custom_providers` entry is added, the intended use is narrow: explicit cross-provider
adversarial review (`-m gpt-5.x --provider custom:openai`), not automatic fallback.
Regardless of quota state, do not describe OpenAI as "Active" or list models as usable-today
anywhere in this skill until the `custom_providers` entry actually exists in config.yaml.

### Old cost reference (2026-07-05; prefer the table above)
| Model | Input /1M | Output /1M | Notes |
|-------|-----------|------------|-------|
| gpt-4.1 | $2 | $8 | 47% cheaper output vs Sonnet 5 ($15) |
| gpt-4.1-mini | $0.4 | $1.6 | Very cheap, 1M ctx |
| gpt-4.1-nano | $0.1 | $0.4 | Cheapest, structured output/classification |
| o4-mini | ~$1.1 | ~$4.4 | Reasoning; vs Opus 4.8 ($5/$25) at ~1/5 cost |
| o3 | $10 | $40 | Comparable to Opus/Fable range; expensive |
