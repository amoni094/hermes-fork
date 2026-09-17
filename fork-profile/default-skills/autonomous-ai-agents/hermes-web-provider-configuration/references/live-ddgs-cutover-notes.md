# Live ddgs cutover notes

Use when a Hermes profile is still pointed at a dead local SearXNG instance and you want a lightweight working search backend without editing repo code.

## Symptoms
- `web_search` fails with `All web search providers failed: searxng: Could not reach SearXNG at http://localhost:8888`
- `web.search_backend` looks updated, but Hermes still chooses `searxng`

## Repair pattern
1. Set a search-only backend in live config, e.g. `web.search_backend: ddgs`.
2. Read back `~/.hermes/config.yaml` and verify the stored type for `web.search_fallback_backends`.
3. If `hermes config set` serialized the fallback list as a quoted string, normalize it to a YAML list if you want exact typing/readability.
4. Verify the runtime prerequisite inside the Hermes venv:
   - `~/.hermes/hermes-agent/venv/bin/python -c 'import ddgs'`
5. If missing, install the package into that venv, not just the outer shell environment.
6. Confirm selection from the Hermes runtime by checking `_get_search_backend()` from the repo venv.
7. Verify end to end with a fresh `hermes chat -q ...` call; the current conversation will not pick up new tool config mid-session.

## Key lesson
A capability-specific backend override is ignored when `_is_backend_available()` is false, so Hermes falls back to the shared auto-selection path. For package-backed providers like `ddgs`, missing the package makes a valid-looking config behave as if it were unset.
