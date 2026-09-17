SUPERSEDES the "zero billing quota" claim in `openai-provider-setup-notes-2026-07-05.md` and
the earlier memory note claiming certain Anthropic model names "do not exist." Both were
disproved by direct live API calls in this session. Kept as a dated point-in-time record —
re-verify before trusting either the old or new claim past this date.

## Anthropic model catalog — verified live 2026-07-06

`curl https://api.anthropic.com/v1/models -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01"`

Returned model ids (all confirmed to exist on this account's key):
```
claude-sonnet-5, claude-fable-5, claude-opus-4-8, claude-opus-4-7, claude-sonnet-4-6,
claude-opus-4-6, claude-opus-4-5-20251101, claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929
```

Direct `/v1/messages` calls (max_tokens=20, trivial prompt) against `claude-opus-4-8`,
`claude-haiku-4-5`, `claude-sonnet-4-6`, and `claude-fable-5` all returned normal `200` responses
with real completions — not 404/model-not-found. None of these are wired into `config.yaml` as
default/fallback/auxiliary; they are reachable only via explicit model override.

Lesson: a model absent from `config.yaml` does not mean it's absent from the account. Config
wiring and account model availability are two independent facts — check both separately.

## OpenAI quota — verified live 2026-07-06

`curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"` returned a
normal model list (gpt-3.5-turbo, tts-1, embeddings, etc. — plus presumably gpt-4.x, not fully
enumerated in this check).

`curl https://api.openai.com/v1/chat/completions ... -d '{"model":"gpt-4.1-nano", ...}'`
returned a real completion (`"content": "Hello! How can I"`, finish_reason: length) — not a
quota-exceeded error. This directly contradicts the 2026-07-05 note in
`openai-provider-setup-notes-2026-07-05.md` claiming zero billing quota.

Lesson: billing/quota state on an external account is not durable fact — it can be topped up,
reset, or throttled between sessions with no local signal. Do not encode "account X has no
quota" as a standing constraint in a skill; it will go stale and the skill will keep telling
future sessions to avoid a provider that now works fine. Always re-test rather than trust the
last-recorded state, and word claims in the skill body as "as of <date>, re-verify" rather than
flat assertions.

## What's still true after this check

- `custom_providers` entry for OpenAI still does not exist in config.yaml — this is a config
  fact, not an account fact, so it doesn't drift the same way; still verify with
  `grep custom_providers ~/.hermes/config.yaml` since a future session may add it.
- Anthropic fallback chain (Cerebras -> SambaNova -> Mistral) unchanged.
- No new provider was added to config as a result of this check — this was a verification-only
  pass to correct stale claims in this skill, not a routing change.
