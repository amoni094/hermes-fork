# Hindsight local heat and provider switch

Use when Hermes reports or causes local heat and the hot process is `ollama runner`, but the visible main Hermes model is remote.

## Durable pattern
Hindsight can be the hidden local LLM caller.

In `memory.provider: hindsight` + `mode: local_embedded`, the relevant settings are split across two locations:
- `~/.hermes/hindsight/config.json`
  - durable provider/model selection (`llm_provider`, `llm_model`, `mode`)
- `~/.hindsight/profiles/<profile>.env`
  - the daemon environment that `hindsight-api` actually launches with

Changing only the JSON may not change the currently running daemon if the parent Hermes process already cached the old values.

## Verification order
1. Confirm Hermes is using Hindsight:
   - `hermes memory status`
   - inspect `memory.provider`
2. Inspect persisted Hindsight config:
   - `~/.hermes/hindsight/config.json`
3. Inspect daemon profile env:
   - `~/.hindsight/profiles/<profile>.env`
4. Inspect the live daemon environment:
   - `/proc/<hindsight-api-pid>/environ`
5. Correlate with runtime evidence:
   - `ss -tnp` connections to `127.0.0.1:11434`
   - `curl http://127.0.0.1:9177/metrics`
   - active `ollama runner` process

## Proven session result
A successful persistent reconfiguration was:
- `llm_provider: anthropic`
- `llm_model: claude-haiku-4-5`

Hindsight supports this provider directly (`CodexLLM`); it is not just a Hermes-side alias.

## Important caveat
Even after writing the new config and profile env, the already-running Hermes parent may keep spawning `hindsight-api` with old values such as:
- `HINDSIGHT_API_LLM_PROVIDER=ollama`
- `HINDSIGHT_API_LLM_MODEL=llama3.2:3b`

If that happens, the fix is not more config editing. Restart Hermes, then re-check the live daemon env and Ollama connections.

## What to report
Do not claim the migration is complete until you distinguish between:
- persistent config changed successfully, and
- live current session actually switched providers.

Phrase it as:
- persistent switch complete; restart required for live process adoption
or
- live switch verified; no active Hindsight→Ollama connections remain
