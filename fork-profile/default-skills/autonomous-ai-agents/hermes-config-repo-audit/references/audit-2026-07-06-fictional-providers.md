# Audit pass 2026-07-06: fictional provider removal

## What triggered this pass
Three docs (`README.md`, `docs/routing-and-workflow.md`, `docs/current-workflow.md`) in
hermes-config described a 4-model Anthropic hierarchy (`claude-sonnet-4-6`,
`claude-opus-4-8`, `claude-haiku-4-5`, `claude-fable-5`) and multiple free-tier providers
(Groq, Google Gemini, GitHub Models) plus a local-Ollama-as-chat-fallback role — none of
which existed in the live config.yaml. This wasn't stale-value drift (a real provider with
an outdated field); it was entire providers that were never configured, likely inherited
from an early planning draft and never cleaned up.

## Ground truth used (verified, not assumed)
- Main + delegation model: `claude-sonnet-5` via `anthropic` — single model, no separate
  escalation/utility tier.
- Fallback chain (config.yaml `fallback_model`): `cerebras/gpt-oss-120b` →
  `sambanova/DeepSeek-V3.2` → `mistral/mistral-large-latest`.
- `auxiliary.compression`: `cerebras/zai-glm-4.7` — a newly added, separate config.yaml
  section from the fallback chain. Don't conflate compression routing with fallback routing;
  they are independent config keys.
- Provider names in config.yaml are bare (`cerebras`, `sambanova`, `mistral`, `anthropic`) —
  no `custom:` prefix convention exists there, even though some old docs used one.

## Method: live API verification, not just config-file trust
For Mistral specifically, the task required confirming that 6 previously-cited model ids
(`codestral-latest`, `devstral-latest`, `mistral-small-latest`, `mistral-medium-latest`,
`magistral-small-latest`, `ministral-8b-latest`) plus the fallback-chain id
(`mistral-large-latest`) actually exist live, not just that they're written in a doc:

```bash
curl -s https://api.mistral.ai/v1/models -H "Authorization: Bearer $MISTRAL_API_KEY" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
ids=[m['id'] for m in d.get('data',[])]
targets=['codestral-latest','devstral-latest','mistral-small-latest',
         'mistral-medium-latest','magistral-small-latest','ministral-8b-latest',
         'mistral-large-latest']
for t in targets:
    print(t, '->', 'FOUND' if t in ids else 'NOT FOUND')
print('total models:', len(ids))
"
```
Result: all 7 confirmed present (72 models total on the account). Nothing needed
correcting this time, but this is the check that would have caught a drifted/renamed
model id — run it every pass, not just when something looks off.

## What was removed from each doc
- **Groq** (provider `custom:groq`/`groq`, GROQ_API_KEY) — full section, capability-matrix
  rows, cron pattern (Pattern F), provider quick-reference row.
- **Google Gemini** (provider `gemini`, GOOGLE_API_KEY) — full section, capability-matrix
  rows, cron pattern (Pattern B), provider quick-reference row, auxiliary routing rows
  (title_generation/skills_hub — these auxiliary rules don't exist either; only
  `compression` is a real auxiliary.* entry).
- **GitHub Models** (provider `custom:github-models`, GITHUB_TOKEN) — full section,
  capability-matrix rows, cron pattern (Pattern E), provider quick-reference row.
- **Ollama as fallback** (`custom:local / qwen3:8b`, "offline always available") — removed
  from the fallback chain entirely. Ollama's only real role is serving embeddings for
  Hindsight/Graphiti at `localhost:11434` — this is a memory-stack fact, not a
  routing/fallback fact, and belongs in the memory-topology docs, not the routing docs.

## Verification / done-criteria pattern used
After the rewrite, three grep passes confirmed the removal was complete and no new gaps
were introduced:
```
search_files pattern="groq|gemini|github-models" (case-insensitive), the 3 edited files -> 0 matches
search_files pattern="claude-sonnet-4-6|claude-opus-4-8|claude-fable-5|claude-haiku-4-5" -> 0 matches
search_files pattern="DeepSeek-V3\.1" -> only legitimate hits allowed are inside the SambaNova
  6-model capability table (which lists both V3.1 and V3.2 as separately available models);
  zero hits allowed in fallback-chain context specifically
search_files pattern="Ollama" -> allowed only in embeddings/memory-stack context, zero in
  fallback/routing-chain context
```
This "grep for the exact banned tokens, then manually confirm the context of any surviving
match instead of blanket-forbidding a string" pattern is reusable for any future
provider-cleanup pass — some tokens (like `DeepSeek-V3.1` or `Ollama`) are legitimately
allowed to survive in one context and forbidden in another.
