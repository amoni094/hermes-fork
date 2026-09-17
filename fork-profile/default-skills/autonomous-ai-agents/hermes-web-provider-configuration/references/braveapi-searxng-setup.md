# Brave Search API + SearXNG braveapi Engine Setup (Aug 22 2026)

## Context
SearXNG HTML-scraping engines for Google, DDG, Startpage, Qwant are permanently blocked
at the source (fingerprint detection / CAPTCHA / 429). This is not a config issue —
no settings.yml change fixes it. The solution is the Brave Search API (official JSON API,
no scraping) configured at two levels: Hermes-native and SearXNG engine.

## What blocks HTML scraping (do not attempt to re-enable)
- google: returns empty silently (fingerprint detection)
- duckduckgo: CAPTCHA block
- startpage: CAPTCHA block
- qwant: 403 access denied
- brave (HTML engine): 429 too many requests — suspends itself, resets on restart but re-blocks immediately

## Brave Search API — free tier
- 2,000 queries/month, no credit card required
- Sign up: https://brave.com/search/api/
- Key management: https://api.search.brave.com/app/keys
- Reset cycle: monthly (not calendar-month — from signup date)

## Step 1: Add key to Hermes .env
```bash
echo "BRAVE_SEARCH_API_KEY=<your_key>" >> ~/.hermes/.env
```

## Step 2: Set Hermes native backend
```bash
hermes config set web.search_backend brave-free
# Plugin registry id is brave-free. Prefer this spelling always.
# Local tree aliases bare "brave" → brave-free in registry + web_tools, but
# older builds and external docs still break on bare "brave" (NotFoundError).
# Hermes reads BRAVE_SEARCH_API_KEY from .env automatically.
```
Verify: `hermes config get web` — should show `search_backend: brave-free`
Also: `hermes doctor` should report `web search (brave-free)`.

## Step 3: Configure SearXNG braveapi engine
The `braveapi` engine in SearXNG uses the official API (not HTML scraping).
It is separate from the `brave` HTML engine. Prefer **braveapi only** for Brave:
disable HTML `brave`, `brave.images`, `brave.videos`, `brave.news` (they 429 and
pollute `unresponsive_engines`). Also keep disabled: duckduckgo web, qwant web,
startpage web (CAPTCHA/403).

Find the block in ~/searxng/searxng/settings.yml:
```yaml
  - name: braveapi
    engine: braveapi
    # read https://docs.searxng.org/dev/engines/online/brave.html
    api_key: ""
    inactive: true
```

Replace with:
```yaml
  - name: braveapi
    engine: braveapi
    api_key: "<your_key>"
    categories: [general, web]
    shortcut: bapi
    timeout: 6.0
```
Note: remove `inactive: true` — absence means active.

## Step 4: Deploy settings.yml to container
SearXNG settings.yml may be owned by the container UID (not rainbow). Use podman cp:
```bash
# Edit a copy in /tmp first to avoid permission issues
cp ~/searxng/searxng/settings.yml /tmp/settings.yml
# ... edit /tmp/settings.yml ...
podman cp /tmp/settings.yml searxng:/etc/searxng/settings.yml
sudo cp /tmp/settings.yml ~/searxng/searxng/settings.yml  # update bind-mount source
podman restart searxng
sleep 5
```

## Step 5: Verify braveapi works
Prefer a direct Python probe (avoids curl|python approval noise):
```bash
python3 - <<'PY'
import json, urllib.request
url = "http://127.0.0.1:8888/search?q=test+query&format=json&engines=braveapi"
with urllib.request.urlopen(url, timeout=30) as r:
    d = json.load(r)
print("Results:", len(d.get("results", [])), "Unresponsive:", d.get("unresponsive_engines"))
PY
```
Expected: 10-20 results, empty unresponsive list.
Also probe default search (no engines=) — unresponsive should stay empty after HTML engines are disabled.

## SerpAPI status (as of Aug 22 2026)
- SERPAPI_API_KEY present in ~/.hermes/.env (uncommented)
- Free tier: 250 searches/month — quota EXHAUSTED, resets Sep 7 2026
- NOT the active backend — it is a fallback for when Brave quota is exhausted
- Complements Brave API: SerpAPI proxies Google's index, Brave has its own independent index

## ddgs fallback
- Package: `duckduckgo-search` installed in ~/.hermes/hermes-agent/venv
- Use in execute_code as a last resort:
  ```python
  from hermes_tools import terminal
  # or directly:
  from duckduckgo_search import DDGS
  results = DDGS().text('your query', max_results=10)
  ```
- Works via a different DDG code path than SearXNG's HTML engine — avoids the 403

## Enable SearXNG limiter (reduces fingerprinting)
In settings.yml, set:
```yaml
server:
  limiter: true  # was: false
```
This activates SearXNG's built-in rate-limiting / bot-detection avoidance. Low cost, reduces
the rate at which scraped engines get re-blocked after a restart.

## Academic engines — unaffected
All academic engines continue working regardless of general web engine status:
- Semantic Scholar (API)
- Google Scholar (SearXNG HTML — works because academic search has lighter bot detection)
- PubMed, OpenAIRE, arXiv (all official APIs)
