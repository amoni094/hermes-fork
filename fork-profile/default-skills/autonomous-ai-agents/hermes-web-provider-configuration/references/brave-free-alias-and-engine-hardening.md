# Brave-free alias + SearXNG engine hardening (Aug 26 2026)

## Symptom
- Agent log: `web is configured to use 'brave' ... no registered web search provider has that name`
- `hermes doctor` or web_search fails even when `BRAVE_SEARCH_API_KEY` is set
- SearXNG JSON returns results but `unresponsive_engines` lists brave HTML / ddg / qwant / startpage

## Root causes
1. Config or docs used bare plugin name `brave`. Registered provider id is `brave-free`.
2. SearXNG still had blocked HTML scrapers enabled; they suspend (429/CAPTCHA) and add noise.

## Durable code fix (local hermes-agent tree)
- `agent/web_search_registry.py`
  - `_PROVIDER_NAME_ALIASES = {"brave": "brave-free"}`
  - `normalize_provider_name()`
  - `get_provider()` applies normalize
- `tools/web_tools.py`
  - `_normalize_web_backend_name()`
  - `_get_capability_backend()` returns normalized name
- Test: `tests/tools/test_web_providers.py::TestPerCapabilityBackendSelection::test_legacy_brave_alias_resolves_to_brave_free`

## Config (keep)
```yaml
web:
  search_backend: brave-free   # never bare brave
  extract_backend: firecrawl
```
Env: `BRAVE_SEARCH_API_KEY`, optional `SEARXNG_URL=http://localhost:8888`.

## SearXNG settings.yml
Disable (add `disabled: true` under each engine block if missing):
- `brave`, `brave.images`, `brave.videos`, `brave.news` (HTML family)
- `duckduckgo` (web), `qwant` (web), `startpage` (web)

Keep active:
- `braveapi` (API key required)
- `bing` (mediocre but works)
- academic engines

Deploy when file is container-UID owned:
1. Edit copy under `/tmp`
2. `podman cp /tmp/settings.yml searxng:/etc/searxng/settings.yml`
3. Update bind-mount source `~/searxng/searxng/settings.yml` (may need elevated write)
4. `podman restart searxng`

## Verification matrix
| Check | Expect |
| --- | --- |
| `hermes config get web` | `search_backend: brave-free` |
| `hermes doctor` | web search (brave-free), extract (firecrawl) |
| misconfig `search_backend: brave` on aliased build | resolves to brave-free; search succeeds |
| SearXNG default JSON | results > 0, `unresponsive_engines: []` |
| SearXNG `engines=braveapi` | ~10–20 results, unresponsive [] |
| pytest web_providers + keyless + tavily | 86 passed (focused suite) |

## Do not
- Re-document bare `brave` as the canonical backend id
- Re-enable HTML brave*/ddg/qwant/startpage “for coverage”
- Treat Parallel lazy-install test failures (`allow_lazy_installs=false`) as a search routing regression
