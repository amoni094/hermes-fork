# Custom Provider api_mode Routing — Debugging Notes

## Problem

`hermes -m gpt-4.1 --provider custom:openai -z "hi"` returned:

    HTTP 400: Encrypted content is not supported with this model.

then (after api_mode fix) escalated to:

    Context length exceeded (15 tokens). Cannot compress further.

## Root Cause 1 — api.openai.com auto-detected as codex_responses

**File:** `hermes_cli/runtime_provider.py`
**Function:** `_detect_api_mode_for_url(base_url)` (around line 95)

Logic: `if hostname == "api.openai.com": return "codex_responses"`.

Hermes defaults OpenAI's primary endpoint to the Responses API because GPT-5 and
o-series models live there. But gpt-4.1 only speaks chat/completions. The result:
OpenAI returns `"Encrypted content is not supported with this model."` (HTTP 400).

**Fix:** Add `api_mode: chat_completions` explicitly to the custom_providers entry
so gpt-4.1 stays on chat/completions.

**GPT-5.x exception (2026-08-25):** that pin 400s `gpt-5.6-sol` — function tools +
`reasoning_effort` are not supported on `/v1/chat/completions`.
`AIAgent._should_auto_upgrade_chat_to_responses` now upgrades GPT-5.x on
`api.openai.com` to `codex_responses` even when the custom entry pins
`chat_completions`. gpt-4.1 is unchanged.

```yaml
custom_providers:
  - name: openai
    base_url: https://api.openai.com/v1
    key_env: OPENAI_API_KEY
    api_mode: chat_completions   # must be explicit — auto-detect picks codex_responses
```

**How the override works:**
`resolve_runtime_provider` → custom_provider branch (line ~1022):
```python
"api_mode": custom_provider.get("api_mode") or _detect_api_mode_for_url(base_url)
```
When `api_mode` is set in the entry, `_detect_api_mode_for_url` is never called.

**Verification:**
```python
import sys; sys.path.insert(0, '/var/home/rainbow/.hermes/hermes-agent')
from hermes_cli.env_loader import load_hermes_dotenv; load_hermes_dotenv()
from hermes_cli.runtime_provider import resolve_runtime_provider
r = resolve_runtime_provider(requested='custom:openai', target_model='gpt-4.1')
print(r['api_mode'], bool(r.get('api_key') and r['api_key'] != 'no-key-required'))
# Expected: chat_completions True
```

## Root Cause 2 — "Context length exceeded (N tokens)" mystery

After the api_mode fix, `hermes -z` returned `"Context length exceeded (15 tokens)"`.
The N-token count is the count **after** compression, not the original prompt size.

Likely cause (not fully confirmed): the auxiliary compressor (then cerebras/gpt-oss-120b)
returns reasoning-only responses (no `content` key — confirmed by direct API call).
Hermes may misread this as empty/failed compression, triggering the context-overflow
retry path even though the original call might have succeeded.

**Cerebras gpt-oss-120b response shape (observed):**
```json
{"choices": [{"message": {"reasoning": "...", "role": "assistant"}}]}
```
No `content` key. Any code path that reads `message["content"]` will KeyError or get None.

**Relevant code path:**
`agent/conversation_loop.py` line ~3600:
```python
_final_response = f"Context length exceeded ({new_tokens:,} tokens). Cannot compress further."
```
This fires when `compression_attempts > max_compression_attempts` — the compression loop
ran to exhaustion, not that the actual prompt was too long.

**Do not apply this suspected fix as of 2026-08-25.** Live `auxiliary.compression` is
`mistral/mistral-small-latest`. Do not flip it back to Cerebras.

**Historical suspected fix:** Change the auxiliary compression model from `cerebras/gpt-oss-120b`
to a non-reasoning model (e.g. `cerebras/llama-3.3-70b`).

## Error Classification for "Encrypted content is not supported"

OpenAI returns: `{"error": {"message": "Encrypted content is not supported with this model.", "type": "invalid_request_error", "code": null}}`

In `agent/error_classifier.py` `_classify_400()`:
- `error_code = None` (code is null)
- `error_msg` contains `"invalid_request_error"` but that string is **excluded** from the
  `_REQUEST_VALIDATION_PATTERNS` check (line ~1121)
- Not in `_CONTEXT_OVERFLOW_PATTERNS`
- `is_generic = False` (message > 30 chars)
- → Falls through to `format_error, retryable=False, should_fallback=True`

So classification is correct — it tries to fall back. The problem was the fallback
chain kicking in and eventually hitting compression exhaustion.

## Key Source Files

| Purpose | File | Symbol |
|---|---|---|
| api_mode auto-detection | `hermes_cli/runtime_provider.py` | `_detect_api_mode_for_url` |
| GPT-5.x override of chat pin | `run_agent.py` | `_should_auto_upgrade_chat_to_responses` |
| custom_provider resolution | `hermes_cli/runtime_provider.py` | `resolve_runtime_provider` (custom_providers branch ~line 975) |
| api_mode parsing | `hermes_cli/runtime_provider.py` | `_parse_api_mode` |
| Error classification for 400 | `agent/error_classifier.py` | `_classify_400` |
| Compression exhaustion | `agent/conversation_loop.py` | ~line 3600 `"Cannot compress further"` |
| Azure model api_mode inference | `hermes_cli/models.py` | `azure_foundry_model_api_mode` + `_AZURE_FOUNDRY_RESPONSES_PREFIXES` |
