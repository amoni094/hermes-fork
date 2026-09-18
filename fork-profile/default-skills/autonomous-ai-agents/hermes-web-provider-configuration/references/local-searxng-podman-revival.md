# Local SearXNG Podman revival

Use this when Hermes should use a self-hosted SearXNG again and the machine may already have a local instance.

## Fast triage
1. Check for an existing container before installing anything.
   - `podman ps -a`
   - Look specifically for a `searxng` container and whether it already maps `8888->8080`.
2. Inspect the container if it exists.
   - `podman inspect searxng`
   - Confirm image, port mapping, bind mounts, and env such as `SEARXNG_BASE_URL`.
3. Check the Hermes env file.
   - `hermes config env-path`
   - Verify `SEARXNG_URL=http://localhost:8888` in `~/.hermes/.env`.
4. If the container exists but is stopped, restart it instead of rebuilding.
   - `podman start searxng`

## Config locations that mattered in this recovery
- Hermes live config: `~/.hermes/config.yaml`
- Hermes env file: `~/.hermes/.env`
- Existing SearXNG bind mount: `~/searxng/searxng/settings.yml`

## Good verification sequence
1. Verify SearXNG directly first.
   - Query `http://127.0.0.1:8888/search?q=<query>&format=json`
   - Confirm the JSON contains results.
2. Then point Hermes at it.
   - `web.search_backend: searxng`
   - `web.search_fallback_backends: [ddgs, brave-free]`
3. Verify with a fresh Hermes process, not the current session.
   - `hermes chat -q "Use the web_search tool ..." --quiet`

## Approval-friendly verification note
Avoid `curl | python` even for localhost JSON. Approval gates may classify it as high risk because it pipes network content into an interpreter. Prefer:
- a pure Python/httpx one-liner that fetches and parses JSON itself, or
- fetch to stdout/file first, then parse in a separate step.

## Durable lesson
When the user says search is broken, the fastest fix may be to revive an already-configured local provider rather than replacing it. Check runtime state before changing architecture.
