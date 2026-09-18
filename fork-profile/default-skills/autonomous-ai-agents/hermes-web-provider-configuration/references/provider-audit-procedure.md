# Web Provider Full Audit Procedure

## When to run
- User reports search results look narrow or homogeneous (e.g. all from one source like arXiv)
- After adding a new API key
- Routine config health check

## One-shot audit command

```python
# Run in execute_code or the Hermes venv python
from hermes_cli.plugins import get_plugin_manager
pm = get_plugin_manager()
pm.discover_and_load(force=True)  # force=True required — discovery is cached
from agent import web_search_registry as reg
for p in reg.list_providers():
    print(f'{p.name:20} available={p.is_available():<5} search={p.supports_search():<5} extract={p.supports_extract():<5}')
```

Then cross-reference against active config:
```bash
hermes config get web
grep -oP '^[A-Z0-9_]+(?==)' ~/.hermes/.env | sort
```

## Interpreting results

| Situation | Meaning | Fix |
|---|---|---|
| available=True but not in search_backend/extract_backend | Key present, provider installed, but never called | `hermes config set web.search_backend <name>` |
| available=False, key present in .env | Plugin missing or key var name mismatch | Check provider.py `is_available()` for expected env var name |
| available=False, no key in .env | Simply not configured — expected | Add key if desired |
| extract_backend blank | Falls through to hardcoded preference walk (firecrawl > tavily > exa > searxng > brave-free > ddgs) | Pin explicitly: `hermes config set web.extract_backend firecrawl` |

## Common gap found (Aug 2026)
- SERPAPI_API_KEY was present in .env, serpapi plugin installed and available=True
- But `web.search_backend` was set to `ddgs` — SerpAPI never called
- Fix: `hermes config set web.search_backend serpapi`
- Similarly: `web.extract_backend` was blank; firecrawl was available but implicit
- Fix: `hermes config set web.extract_backend firecrawl`

## Signal that triggered audit
User noticed research results were all from arXiv — a narrow/homogeneous pattern
that indicates the active search backend lacks broad web coverage (ddgs tends
to over-index on academic/aggregator results vs SerpAPI's broader web index).

## After changing config
Config changes don't apply to the current session's tool bundle.
Verify in a fresh process:
```bash
hermes chat -q "search for latest news on AI agents" 2>&1 | head -20
```
