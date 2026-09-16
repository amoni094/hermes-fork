---
name: hermes-web-provider-configuration
triggers:
  - User wants to change how Hermes chooses web_search or web_extract backends
  - User wants search-provider fallback behavior added, reordered, or made configurable
  - Configuring or extending Hermes web provider selection and fallback ordering
  - A web_search or web_extract provider is failing and needs to be swapped or reordered
description: >
  Use when configuring or extend Hermes web_search/web_extract provider selection, fallback ordering, and related tests/docs without breaking runtime config behavior.
related_skills:
  - autonomous-agent-loop-design
  - verification-before-completion
---

# Hermes Web Provider Configuration

## SearXNG Engine Status — Aug 2026

Working in SearXNG:
- braveapi: Brave Search API (key required in settings.yml + BRAVE_SEARCH_API_KEY env var) — primary general web
- bing: HTML scraping, works but mediocre quality
- searchmysite, wiby: niche indie web
- Academic: Semantic Scholar, Google Scholar, PubMed, OpenAIRE, arXiv all functional

Permanently blocked at source regardless of config:
- google: empty results (fingerprint detection)
- duckduckgo: CAPTCHA
- startpage: CAPTCHA
- qwant: 403
- brave (HTML): 429 — use braveapi engine instead

Hermes primary backend: `web.search_backend = brave-free` (plugin id; prefer this spelling).
Uses `BRAVE_SEARCH_API_KEY` from env (also accepted as dual-read with yaml `web.brave_api_key` on some paths).
Bare `brave` is a **legacy alias** normalized to `brave-free` in:
- `agent/web_search_registry.py` (`normalize_provider_name` / `get_provider`)
- `tools/web_tools.py` (`_normalize_web_backend_name` / `_get_capability_backend`)
Still write `brave-free` in config — do not re-teach bare `brave` in docs/setup.
If logs show: `web is configured to use 'brave' ... no registered web search provider has that name`
→ config was bare `brave` on a build without the alias, or plugins failed to load. Fix: set
`hermes config set web.search_backend brave-free` and confirm `hermes doctor` shows web search (brave-free).
SearXNG braveapi engine: parallel path — same key, configured in ~/searxng/searxng/settings.yml.
Disabled in settings.yml (do not re-enable): HTML `brave`/`brave.images`/`brave.videos`/`brave.news`,
`duckduckgo` (web), `qwant` (web), `startpage` (web). Keep `braveapi` + `bing` active.
Free tier: 2,000 queries/month. Sign up: https://brave.com/search/api/

---
- User wants to change how Hermes chooses `web_search` or `web_extract` backends.
- User wants search-provider fallback behavior added, reordered, or made configurable.
- You are editing Hermes web provider dispatch, capability selection, or provider-specific config defaults.
- A news/research workflow is underpowered because Hermes is choosing the wrong backend or not falling back cleanly.

## Preconditions
0. **If the new provider requires account signup (SerpApi, SearchApi, Apify, etc.), do not attempt to automate the signup.** Email/OTP verification, CAPTCHA, and payment steps cannot be completed by an agent. Hand the signup back to the user with the direct URL and the minimal steps (sign up → verify email → copy API key from the dashboard), then do the actual config/integration work once they hand you the key. Don't burn a session trying to drive a headless/GUI browser through a verification wall — if browser automation in the current environment is degraded (timeouts, daemon not starting), that's an extra reason to hand off rather than debug the browser stack as a side quest.
1. Load the bundled `hermes-agent` skill first for current CLI/config conventions.
2. Confirm whether the request is:
   - repo code change,
   - live user config change,
   - docs-only change,
   - or all three.
3. Inspect the current dispatch path before editing. Typical files:
   - `tools/web_tools.py`
   - `agent/web_search_registry.py`
   - provider plugin under `plugins/web/`
   - config defaults in `hermes_cli/config.py`
   - focused tests under `tests/tools/`
   - docs in `website/docs/user-guide/configuration.md`

## Core workflow
1. **Read the current routing logic first**
   - Find capability-specific selection (`search_backend`, `extract_backend`, shared `backend`).
   - Identify whether fallback belongs in the dispatch layer, provider layer, or registry layer.
   - Prefer dispatch-layer fallback when multiple providers can satisfy the same capability.

2. **Keep config surface explicit**
   - If adding a new config key, add it to `DEFAULT_CONFIG` in `hermes_cli/config.py`.
   - Use a capability-specific key when behavior differs for `web_search` vs `web_extract`.
   - Document accepted input shapes if you support both YAML list and string forms.

3. **Implement fallback deterministically**
   - Try the explicitly selected provider first.
   - Then try configured fallbacks in user order.
   - Then optionally append remaining available providers in stable default order.
   - Deduplicate provider names while preserving first occurrence.
   - Availability checks must not crash dispatch; wrap provider `is_available()` safely.

4. **Preserve actionable failure reporting**
   - Return provider-specific errors for failed attempts.
   - When all providers fail, combine a short bounded summary rather than losing the trail.
   - Sanitize exception text; do not leak tracebacks or secrets.

5. **Update tests with focused coverage**
   - Add or extend tests in `tests/tools/test_web_tools_config.py` unless another file is clearly a better fit.
   - Cover at least:
     - success via fallback,
     - all-providers-fail reporting,
     - configured fallback order overriding default order.
   - Prefer small monkeypatched provider stubs for ordering tests when real provider availability gates would add noise.

6. **Update docs and live config separately**
   - Repo docs: update `website/docs/user-guide/configuration.md`.
   - Live config: use `hermes config set` when possible, then verify the resulting on-disk type.
   - Do not assume a successful CLI message means the YAML shape is what the code expects.
   - In particular, list-like values passed through `hermes config set` may land as a quoted string; if the code accepts both list and comma-string forms, keep going but normalize the YAML when you want durable readability and exact typing.

7. **For backend switches, verify runtime prerequisites in the Hermes venv**
   - Search backends are only usable if their real runtime requirement exists in the Hermes environment, not just in the current shell.
   - Example: `web.search_backend: ddgs` still falls through unless the `ddgs` package is importable from `~/.hermes/hermes-agent/venv`.
   - If a package-backed backend is selected, install/verify it in the Hermes venv, then re-check the backend selector from that environment.

8. **When reviving a local SearXNG, inspect existing local runtime state before reinstalling**
   - Check whether the machine already has a SearXNG container, bind-mounted config, or `.env` entry such as `SEARXNG_URL=http://localhost:8888`.
   - On Fedora/Silverblue setups using rootless Podman, it is often faster and safer to inspect `podman ps -a`, `podman inspect searxng`, and the mounted `settings.yml` first, then restart the existing container instead of building a fresh deployment.
   - Verify the endpoint directly with a local JSON probe before blaming Hermes routing.

9. **Remember session-boundary behavior**
   - Tool/config changes do not apply to the current conversation's tool bundle.
   - After changing web backend config, verify with a fresh `hermes chat -q ...` process or instruct the user to `/reset` or start a new session.
   - Do not treat a stale in-session tool failure as proof that the new config did not work.
   - If the backend depends on values from `~/.hermes/.env` (for example `FIRECRAWL_API_URL` for a local Firecrawl extract path), verify in a fresh process even when the on-disk config already shows the correct backend.

9. **Verify before claiming completion**
   - Run the focused pytest target for the changed area.
   - Run one broader nearby subset if available.
   - Read back the live config snippet after changing it.
   - For live config-only repairs, prefer a fresh one-shot `hermes chat -q` probe that exercises `web_search` end to end.

## Adding a brand-new provider plugin from scratch (not just reordering existing ones)

When the user hands you a fresh API key for a provider that has no plugin yet
(e.g. SerpApi, SearchApi, Apify), the fastest correct path is to copy the
smallest existing single-capability plugin rather than invent structure:

1. **Pick a template by capability.** Search-only (no extract) → copy
   `plugins/web/brave_free/` layout. Search+extract → copy `plugins/web/tavily/`.
2. **Three files per plugin**, under `plugins/web/<name>/`:
   - `provider.py` — subclass `agent.web_search_provider.WebSearchProvider`.
     Implement `name`, `display_name`, `is_available()` (env var presence
     check only, no network call), `supports_search()`/`supports_extract()`,
     `search()`/`extract()`, and `get_setup_schema()` (drives the `hermes
     tools` picker UI — include `env_vars` with `key`/`prompt`/`url`).
   - `__init__.py` — a `register(ctx)` function calling
     `ctx.register_web_search_provider(YourProvider())`.
   - `plugin.yaml` — `kind: backend`, `provides_web_providers: [<name>]`.
     Bundled `kind: backend` plugins auto-load; no `plugins.enabled` entry
     needed.
3. **Use `get_provider_env(name)`** (from `agent.web_search_provider`) inside
   the provider for credential lookup — it checks `os.environ` then
   `~/.hermes/.env` via the config layer, so it works from gateway/delegate
   subprocess contexts, not just the launching shell.
4. **Set the key via the config API, not a hand-edit**: `from
   hermes_cli.config import save_env_value; save_env_value("KEY_NAME",
   value)`. This goes through the same denylist/sanitization/managed-scope
   guards as `hermes config set`.
5. **Verify without restarting the process**:
   ```python
   from hermes_cli.plugins import get_plugin_manager
   get_plugin_manager().discover_and_load(force=True)
   from agent import web_search_registry as reg
   for p in reg.list_providers():
       print(p.name, p.is_available(), p.supports_search(), p.supports_extract())
   # then a live smoke test:
   reg.get_provider("<name>").search("test query", limit=3)
   ```
   `force=True` is required — plugin discovery is cached, and a plain
   `discover_and_load()` will not pick up a plugin directory added mid-process.
6. **Registering a provider does NOT make it active.** A new provider only
   becomes the one `web_search`/`web_extract` actually calls if
   `web.search_backend`/`web.extract_backend`/`web.backend` names it
   explicitly, OR it is the only capability-eligible + available provider,
   OR it wins the legacy preference walk (`firecrawl > parallel > tavily >
   exa > searxng > brave-free > ddgs` — a newly added plugin is invisible to
   this hardcoded list and will never be picked by default). If the user
   wants the new provider actually used, set the config key explicitly and
   say so — don't imply "installed" means "in use."

## Pitfalls
- **Do not stop at `tools/web_tools.py`**. If you add a new config key but skip `hermes_cli/config.py` and docs, the feature becomes invisible and fragile.
- **Never set `web.search_backend` to bare `brave`.** The plugin registry id is `brave-free`. Pre-alias builds raise NotFoundError even with a valid API key. Alias exists in current local tree, but docs/setup must still teach `brave-free`.
- **Do not re-enable SearXNG HTML `brave*` / ddg / qwant / startpage web** after a restart “to get more engines” — they re-block immediately and pollute `unresponsive_engines`.
- **SearXNG `settings.yml` is often container-UID owned.** Direct write can PermissionError; edit `/tmp` copy → `podman cp` into container → update bind-mount source → `podman restart searxng`. See `references/braveapi-searxng-setup.md`.
- **Do not trust provider availability during ordering tests**. Availability gates can reorder or suppress candidates; use fake providers or monkeypatch the registry when verifying dispatch order itself.
- **Do not assume `hermes config set` preserves list typing**. If you pass a list-like value, verify whether the file contains a true YAML list or a quoted string. Normalize it if needed before declaring success.
- **Do not encode fallback only in one provider plugin** when the behavior is meant to apply across all search backends.
- **Do not reinstall local SearXNG blindly**. An existing rootless Podman container plus a valid `SEARXNG_URL` in `~/.hermes/.env` may already be the intended setup; inspect and restart before replacing it.
- **Do not use `curl | python` for verification when a simpler parser would do**. Approval gates flag it as high risk even for localhost JSON; prefer a direct Python/httpx probe or fetch first and parse second.
- **Parallel client unit tests may fail when `security.allow_lazy_installs=false`** and `parallel-web` is absent — env/policy, not a web-provider routing regression. Do not “fix” search by enabling lazy installs unless the user asked.

## Good verification commands
```bash
# from ~/.hermes/hermes-agent (use the hermes venv python)
./venv/bin/python -m pytest -q tests/tools/test_web_providers.py \
  tests/tools/test_web_keyless_fallback.py tests/tools/test_web_keyless_rescue.py \
  tests/tools/test_web_tools_tavily.py
# alias regression specifically:
./venv/bin/python -m pytest -q tests/tools/test_web_providers.py::TestPerCapabilityBackendSelection::test_legacy_brave_alias_resolves_to_brave_free
hermes doctor   # expect: web search (brave-free), web extract (firecrawl)
hermes config get web
# live Hermes provider smoke (loads plugins):
./venv/bin/python - <<'PY'
from hermes_cli.plugins import get_plugin_manager
get_plugin_manager().discover_and_load(force=True)
from tools.web_tools import web_search_tool, _get_search_backend
import json
print('backend', _get_search_backend())
print(json.loads(web_search_tool('Hermes Agent Nous Research', limit=3)).get('success'))
PY
# SearXNG probes (prefer urllib/httpx, not curl|python):
# default JSON + engines=braveapi; unresponsive_engines should be []
```

## Current live configuration (as of Sep 11 2026)
- `web.search_backend: serpapi` — SerpAPI (Google-backed, confirmed working)
  - `SERPAPI_API_KEY` in ~/.hermes/.env (required)
  - Set via: `hermes config set web.search_backend serpapi`
  - Returns a dict `{success, data: {web: [...]}}` — NOT a list; the Hermes tool handles this correctly but raw provider calls need `result['data']['web']`
- `web.extract_backend: firecrawl` — local Firecrawl (rootless Podman)
  - FIRECRAWL_API_URL=http://localhost:3002 in ~/.hermes/.env
- Local SearXNG running but degraded (http://localhost:8888):
  - braveapi engine: SUSPENDED (access denied) as of Sep 2026
  - bing engine: timing out intermittently
  - Working engines: searchmysite, wiby (low quality for research)
  - SearXNG is NOT recommended as primary search backend until braveapi key is refreshed
- brave-free (Hermes-native plugin): braveapi key suspended — same root cause as SearXNG braveapi

If search quality degrades:
1. `hermes doctor` → expect `web search (serpapi)` and `web extract (firecrawl)`
2. Check SerpAPI key: `hermes config get web.search_backend`; smoke test via execute_code + provider.search()
3. If SerpAPI fails, next fallback: `ddgs` (no key required) — `hermes config set web.search_backend ddgs`
4. Do NOT switch to brave-free or SearXNG braveapi engine until Brave API key is confirmed refreshed

## Provider fallback priority (Sep 2026 status)
1. serpapi — Google quality, key confirmed present ✓ ACTIVE
2. ddgs — keyless, moderate quality, rate-limited on high volume
3. searxng — local but braveapi/bing engines degraded; only wiby+searchmysite working
4. brave-free — suspended (same key as SearXNG braveapi) — DO NOT USE until key refreshed

## Audit first — before any config change
When a search quality complaint comes in (narrow results, all from one source, all arXiv, etc.),
run a full provider audit before assuming a config key needs to be added. The most common cause
is a key already present in `.env` but `search_backend`/`extract_backend` pointing elsewhere.
See `references/provider-audit-procedure.md` for the one-shot audit command and fix table.

## Support files
- `references/search-fallback-session-notes.md` — concrete file targets, test patterns, and config-shape pitfalls from a real fallback-order implementation.
- `references/live-ddgs-cutover-notes.md` — live-profile repair notes for switching off a dead local SearXNG to `ddgs`, including venv verification and fresh-session probing.
- `references/local-searxng-podman-revival.md` — how to inspect, restart, verify, and rewire an existing local SearXNG instance on rootless Podman without rebuilding it.
- `references/provider-audit-procedure.md` — full provider audit procedure: one-shot availability check, interpret available-but-unconfigured gaps, common fix patterns. Run when results look narrow or homogeneous.
- `references/searxng-engine-status-aug2026.md` — empirical per-engine block matrix from Aug 21 2026 (AU residential IP). Working: bing, bing news/images/video, google news, google scholar, searchmysite, wiby, braveapi. Blocked: google web (fingerprint), duckduckgo (403), startpage (CAPTCHA), brave HTML (429), qwant (403), presearch (timeout), mojeek (empty). Re-test blocked engines quarterly — bot-detection drifts.
- `references/braveapi-searxng-setup.md` — Brave API key + Hermes `brave-free` + SearXNG `braveapi` dual-path setup; container-owned settings.yml deploy; engines to keep disabled.
- `references/brave-free-alias-and-engine-hardening.md` — Aug 26 2026 repair: bare-`brave` NotFoundError, registry alias, disabled HTML engines, verification matrix.
