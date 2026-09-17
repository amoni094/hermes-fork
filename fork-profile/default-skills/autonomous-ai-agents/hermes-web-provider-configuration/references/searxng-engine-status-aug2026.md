# SearXNG Engine Status

Empirical test results from residential AU IP, self-hosted rootless Podman SearXNG instance.
Tested with isolated `&engines=<name>` queries. Re-test any "BLOCKED" engine quarterly—bot-detection drifts.

---

## Sep 11 2026 update

| Engine | Status | Notes |
|--------|--------|---------|
| braveapi | SUSPENDED | access denied — same root cause as Brave API key expiry |
| bing | TIMEOUT | intermittent; flaky under load |
| searchmysite | OK | low quality, personal-site index |
| wiby | OK | indie web, low quality |

Default query (all engines): returns ~25 results from `bing + searchmysite + wiby`.
SearXNG NOT recommended as primary search backend until braveapi key is refreshed.
Active primary backend switched to **SerpAPI** (Google-backed).

---

## Aug 21 2026 baseline

### Working engines (confirmed Aug 21, 2026)

| Engine | Category | Notes |
|--------|----------|-------|
| bing | general, web | Primary workhorse. 10 results, reliable, no blocks. |
| bing news | news | Reliable. 10 results. |
| bing images | images | Reliable. 46 results. |
| bing videos | video | Reliable. 20 results. |
| google news | news | Works even when google web is blocked. 92–99 results. Separate endpoint. |
| google scholar | science, academic | Works even when google web is blocked. 10 results. Separate endpoint. |
| wiby | general, web | Indie/personal web index. Flaky timeout on isolated test but contributes in default multi-engine search. |
| searchmysite | general | Personal-site index. Reliable. 10 results. |
| braveapi | general, web | Brave Search API. Requires BRAVE_SEARCH_API_KEY in settings.yml. |

### Broken / blocked engines (Aug 2026)

| Engine | Status | Root cause |
|--------|--------|-----------|
| google (web) | EMPTY — silent | Fingerprint/JS-challenge detection. Returns 0 results, no error logged. |
| duckduckgo | BLOCKED (403) | access denied, 180s suspension. |
| startpage | BLOCKED (CAPTCHA) | 3600s suspension. |
| brave (HTML) | BLOCKED (429) | Too many requests. Use braveapi engine instead. |
| qwant | BLOCKED (access denied) | |
| presearch | BLOCKED (timeout) | |
| mojeek | EMPTY | Returns 0 results, no error. |
| yahoo | BLOCKED (HTTP protocol error) | |
| arxiv | BLOCKED (rate limit) | Use the arxiv skill's direct API call instead. |
| crossref | ENGINE BUG | `KeyError: 'type'` in `searx/engines/crossref.py:56` — SearXNG code defect. |
| reddit | BLOCKED (access denied) | |
| openstreetmap | BLOCKED (access denied) | |
| semantic scholar | BLOCKED (timeout) | Use direct API: https://api.semanticscholar.org/graph/v1/paper/ |
| pubmed | BLOCKED (timeout) | |

### Configuration applied (Aug 2026)

Enabled:
- bing, wiby, searchmysite, braveapi

Disabled (add `disabled: true` with comment):
- duckduckgo — `# blocked: 403 access denied`
- google (web) — `# blocked: returns empty (fingerprint detection)`
- startpage — `# blocked: CAPTCHA`
- brave (HTML) — `# blocked: too many requests`
- crossref — `# engine bug: KeyError on type field in this SearXNG version`
- arxiv — `# blocked: rate-limited (use direct arxiv skill instead)`

## Podman bind-mount write technique

The bind-mount dir (`~/searxng/searxng/`) is owned by the container UID (SELinux: `container_file_t`).
The host user cannot write to it directly. Two-step workflow:

```bash
# Step 1: Edit a copy in /tmp
cp ~/searxng/searxng/settings.yml /tmp/settings.yml
# ... make edits to /tmp/settings.yml ...

# Step 2a: Inject into running container (takes effect after restart)
podman cp /tmp/settings.yml searxng:/etc/searxng/settings.yml

# Step 2b: Update the bind-mount for persistence across `podman rm && podman run`
podman unshare cp /tmp/settings.yml ~/searxng/searxng/settings.yml

# Step 3: Restart
podman restart searxng && sleep 8
```

`podman unshare` runs the copy inside the container's user namespace, bypassing UID mismatch.
Without step 2b, settings revert the next time the container is recreated from scratch.

## Key insight: Google News/Scholar vs Google Web

`google`, `google news`, `google scholar`, `google images`, `google videos` are separate SearXNG engines
hitting different Google endpoints. Bot-detection on the main web search endpoint does NOT apply to
the News or Scholar endpoints. Always test these independently when diagnosing "Google is broken."

## SerpAPI vs SearXNG vs brave-free selection

When braveapi key is suspended:
- Switch Hermes primary to serpapi: `hermes config set web.search_backend serpapi`
- SerpAPI returns `{success, data: {web: [...]}}` dict, NOT a list — Hermes tool handles this; raw provider.search() calls need `result['data']['web']`
- ddgs is keyless fallback if SerpAPI also fails: `hermes config set web.search_backend ddgs`
- Restore brave-free when key is refreshed and confirmed working via smoke test
