---
name: hermes-web-provider-configuration
description: Configure or extend Hermes web_search/web_extract provider selection, fallback ordering, and related tests/docs without breaking runtime config behavior.
---

# Hermes Web Provider Configuration

## When to use
- User wants to change how Hermes chooses `web_search` or `web_extract` backends.
- User wants search-provider fallback behavior added, reordered, or made configurable.
- You are editing Hermes web provider dispatch, capability selection, or provider-specific config defaults.
- A news/research workflow is underpowered because Hermes is choosing the wrong backend or not falling back cleanly.

## Preconditions
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

## Pitfalls
- **Do not stop at `tools/web_tools.py`**. If you add a new config key but skip `hermes_cli/config.py` and docs, the feature becomes invisible and fragile.
- **Do not trust provider availability during ordering tests**. Availability gates can reorder or suppress candidates; use fake providers or monkeypatch the registry when verifying dispatch order itself.
- **Do not assume `hermes config set` preserves list typing**. If you pass a list-like value, verify whether the file contains a true YAML list or a quoted string. Normalize it if needed before declaring success.
- **Do not encode fallback only in one provider plugin** when the behavior is meant to apply across all search backends.
- **Do not reinstall local SearXNG blindly**. An existing rootless Podman container plus a valid `SEARXNG_URL` in `~/.hermes/.env` may already be the intended setup; inspect and restart before replacing it.
- **Do not use `curl | python` for verification when a simpler parser would do**. Approval gates flag it as high risk even for localhost JSON; prefer a direct Python/httpx probe or fetch first and parse second.

## Good verification commands
```bash
python -m pytest -q -o addopts='' tests/tools/test_web_tools_config.py::TestWebSearchFallbackChain
python -m pytest -q -o addopts='' tests/tools/test_web_tools_config.py -k 'TestWebSearchFallbackChain or exception_in_provider_search_is_sanitized'
```

## Support files
- `references/search-fallback-session-notes.md` — concrete file targets, test patterns, and config-shape pitfalls from a real fallback-order implementation.
- `references/live-ddgs-cutover-notes.md` — live-profile repair notes for switching off a dead local SearXNG to `ddgs`, including venv verification and fresh-session probing.
- `references/local-searxng-podman-revival.md` — how to inspect, restart, verify, and rewire an existing local SearXNG instance on rootless Podman without rebuilding it.
