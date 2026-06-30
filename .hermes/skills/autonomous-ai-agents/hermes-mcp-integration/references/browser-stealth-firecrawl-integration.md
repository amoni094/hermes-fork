# Browser stealth MCP + Firecrawl integration notes

Use case
- User wants better success on Cloudflare / bot-protected sites while keeping Firecrawl as the default extraction path.

Selection heuristic
- Prefer the option that is already an MCP server and can be registered directly with Hermes.
- A custom anti-detect Chromium fork may have stronger fingerprint claims, but it is a worse first integration target if it lacks clean MCP packaging and Linux/Hermes setup guidance.

Validated pattern
1. Install or expose a Chromium-family browser.
2. If the browser is Flatpak-managed and not on PATH, add a shim such as:
   - `~/.local/bin/chromium` -> `exec flatpak run org.chromium.Chromium "$@"`
3. Put the MCP launch command behind `~/.hermes/scripts/<name>.sh`.
4. Register with Hermes using `hermes mcp add <name> --command <script>`.
5. Confirm with `hermes mcp test <name>`.
6. Configure Firecrawl as the extract backend and set `FIRECRAWL_API_URL` for the local instance.
7. Smoke-test the real browser path: spawn -> navigate -> close.

Why this matters
- Firecrawl remains the cheap/default extractor.
- The stealth MCP becomes an escalation path when normal fetch/extract is blocked.
- The launcher-script pattern avoids brittle inline command/env quoting and makes PATH fixes persistent.

Good verification set
- Firecrawl base URL returns HTTP 200.
- `hermes mcp test` enumerates tools.
- Browser environment validator reports ready.
- A live navigation test succeeds on a known site.
