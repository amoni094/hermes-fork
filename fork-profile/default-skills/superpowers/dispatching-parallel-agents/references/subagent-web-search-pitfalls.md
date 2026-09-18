# Subagent web_search Pitfalls (Aug 2026)

## Brave provider not registered in subagents

Subagents do NOT inherit the parent session's `web_search` provider registration.
If the parent has `web.search_backend=brave`, subagent `web_search()` calls fail:

```
"web is configured to use 'brave' but no registered web search provider has that name."
```

The subagent retries up to 8 times, hits `same_tool_failure_halt`, and returns empty —
wasting ~80s of wall time. Task-3 of sweep 21 (Aug 22 2026) failed this way.

### Fix: SearXNG fallback instruction

Include this in every research subagent's context block:

> "IMPORTANT: web_search may fail with 'brave provider not registered'. If so, immediately
> fall back to SearXNG via execute_code:
>
> ```python
> import subprocess
> result = subprocess.run(
>     ['curl', '-s', 'http://localhost:8888/search?q=QUERY&format=json&engines=braveapi,bing'],
>     capture_output=True, text=True
> )
> import json
> data = json.loads(result.stdout)
> results = data.get('results', [])
> ```
>
> SearXNG uses the same Brave API key via its `braveapi` engine — same results, different path.
> URL-encode the query string (replace spaces with `+`)."

Task-4 of sweep 21 used this fallback and successfully ran all 7 planned queries, returning 70 results.

### Diagnosing a "stalled" research session

A session waiting on parallel subagents looks stalled (idle prompt, no output). It is
usually alive, blocked on delegation result delivery.

**Diagnosis steps:**
1. Find the delegation ID from `session_search` on the research session (look for `deleg_<id>` in tool call args).
2. Check live logs:
   ```bash
   ls -la ~/.hermes/cache/delegation/live/deleg_<id>/
   tail -3 ~/.hermes/cache/delegation/live/deleg_<id>/task-*.log
   ```
3. If all task logs end with `final | status=completed`, subagents finished. The parent is
   waiting for consolidated results to re-enter the conversation.
   - Try pressing Enter in the stalled terminal.
   - If context was exhausted before results arrived: restart from here and replay using
     the delegation logs as source material.
4. For full subagent output: read `~/.hermes/cache/delegation/subagent-summary-N-<timestamp>.txt`
   — log tails truncate large `execute_code` outputs (look for `(+NNNN chars)` markers).

**Individual subagent status** can be read from final lines:
- `final | status=completed duration=NNNs` → finished normally
- `final | status=completed ... I stopped retrying` → hit tool-loop guardrail, returned partial/empty
- No final line → subagent is still running or crashed without writing final summary

### Template for research subagent context block

```
IMPORTANT: web_search may fail with "brave provider not registered". If it does,
immediately fall back to SearXNG:

  import subprocess, json
  r = subprocess.run(['curl','-s',
      'http://localhost:8888/search?q=YOUR+QUERY+HERE&format=json&engines=braveapi,bing'],
      capture_output=True, text=True)
  results = json.loads(r.stdout).get('results', [])

SearXNG is on port 8888 with Brave API + Bing engines. URL-encode all queries.
Do NOT retry web_search more than twice — switch to SearXNG immediately on first failure.
```

## Brave API rate limits under parallel fan-out

Note: these two sections describe distinct failure modes. Section 1 ("Brave provider not registered") fires when the Brave provider is misconfigured or not registered in the subagent's environment. Section 2 (below) fires when it IS registered correctly but gets rate-limited under high-concurrency fan-out. Both can occur; the SearXNG fallback resolves both.

When Brave is registered and working: subagents inherit the parent's web_search provider. If parent uses Brave, subagent also uses Brave. Brave API has rate limits that fire faster under parallel fan-out.

Mitigation:
- (a) use SearXNG fallback when >3 subagents each do web_search
- (b) stagger web_search calls across subagents with 1-2s delay
- (c) if a subagent gets 429 from web_search, it should retry with web_extract on the URL directly

