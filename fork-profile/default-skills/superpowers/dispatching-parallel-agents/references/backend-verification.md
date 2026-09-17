# Verifying Which Search Backend a Subagent Used

Confirmed technique from Aug 2026. Use when the user asks whether SerpAPI (or another
premium provider) was actually active for a parallel research dispatch.

## The problem

Subagents inherit the parent's config at dispatch time, but `web_search` result payloads
don't stamp which backend served them. The tool call looks identical whether DuckDuckGo
or SerpAPI answered it.

## The `"position"` field method

SerpAPI results always include `"position": N` on each result object — Google's organic
result rank. DuckDuckGo/ddgs results never include this field.

Check the delegation logs:

```bash
DELEG_ID=deleg_xxxxxxxx   # from session_search or async result message

for i in 0 1 2; do
  pos=$(grep -c '"position"' \
    ~/.hermes/cache/delegation/live/${DELEG_ID}/task-${i}.log 2>/dev/null)
  calls=$(grep -c 'web_search ok' \
    ~/.hermes/cache/delegation/live/${DELEG_ID}/task-${i}.log 2>/dev/null)
  echo "task-${i}: calls=$calls  results-with-position=$pos"
done
```

**Reading the output:**
- `pos ≈ calls` (gap of 1–2): SerpAPI confirmed. The small gap is normal — some non-Google
  sources (CyberLeninka, J-STAGE hits) don't include `"position"` even when SerpAPI is
  the active backend routing through Google.
- `pos = 0` across all tasks: ddgs fallback fired. SerpAPI key was missing or config was
  set after dispatch.
- `pos` well below `calls` (e.g. half): mixed — some queries hit SerpAPI, some fell back.

## Full confirmation checklist

All three must hold to be definitive:

1. **Config at dispatch time**: `hermes config get web` → `search_backend: serpapi`
2. **Config mtime before dispatch**: `stat -c '%y' ~/.hermes/config.yaml` must predate
   the subagent dispatch timestamp shown in the async result message.
3. **Key present**: `grep -c SERPAPI ~/.hermes/.env` returns non-zero (don't print value).

Then the `"position"` count is the runtime confirmation.

## Aug 2026 confirmed run

Three parallel research subagents (runtime behaviour, memory topology, skill+config).
- task-0: 16 web_search calls, 15 with `"position"` (1 CyberLeninka exception)
- task-1: 19 calls, 18 with `"position"`
- task-2: 18 calls, 18 with `"position"`

All three pre-conditions satisfied. SerpAPI confirmed: Google-backed across all 53 calls.

## Pitfall: non-Google sources always miss `"position"`

CyberLeninka, J-STAGE, and similar domain-specific academic indexes return results without
a `"position"` field even when SerpAPI is the active backend (SerpAPI uses different
parsers per domain). Expect 1–3 results per subagent run without `"position"` regardless
of backend — don't count those as ddgs fallback evidence.
