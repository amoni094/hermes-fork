---
name: firecrawl-stealth-fallback
triggers:
  - Firecrawl extraction returns empty, blocked, or degraded content due to bot protection
  - Need to escalate from Firecrawl to stealth-browser-mcp for a site with heavy anti-bot measures
  - Web extraction is failing and a fallback to a headless stealth browser is needed
  - Standard web_extract is blocked and stealth extraction must be attempted
description: >
  Use when: Use Firecrawl as the default extractor and escalate to stealth-browser-mcp when bot protection blocks or degrades extraction.
related_skills:
  - firecrawl-research
  - academic-literature-review
  - domain-research-synthesis
  - hermes-web-provider-configuration
  - browser-agent-ops
  - blocked-page-recovery
---

# Firecrawl stealth fallback

Use this when a site is likely to use Cloudflare, bot checks, or JS-heavy blocking and you still want Firecrawl as the normal path.

## What is installed here
- Local Firecrawl API at `http://127.0.0.1:3002`
- Hermes MCP server `stealth-browser-mcp`
- Helper script at `~/.hermes/scripts/firecrawl_stealth_fetch.py`
- Reference notes: `references/integration-notes.md`
- Social-platform notes: `references/social-platform-notes.md`
- Firefox BiDi WebSocket control: `references/firefox-bidi-websocket-control.md`

## Implementation rules
- Keep Firecrawl as the default extractor; use stealth only as escalation.
- If a helper script imports `stealth-browser-mcp` internals such as `browser_manager`, `dom_handler`, or `models`, run it with the MCP server virtualenv interpreter, not plain system Python. Otherwise module imports like `nodriver` can fail even when the MCP server itself works.
- When adding diagnostics, write human/debug traces to stderr and keep stdout as machine-parseable JSON so the helper remains pipe-friendly.

## Default pattern
1. Try Firecrawl first.
2. If Firecrawl errors, returns empty content, or matches common block/challenge signals (Cloudflare, captcha, access-denied, JS/cookie challenge, 403/429/503), fall back to stealth browser.
3. For public social profiles, prefer a two-stage path: lightweight/static fetch first, then real-browser rendered HTML as the intermediate artifact for downstream parsing.
4. If a platform has a strong public extractor, use it before generic DOM parsing (example: YouTube via `yt-dlp`).
5. Use the stealth/rendered result for manual extraction, screenshots, DOM inspection, or follow-up scraping.
6. If the page is already open interactively and the agent thrash-clicks the same control, that is `browser-agent-ops` (loop guard / multi-act) — not this skill.

## CDP-attach to user's existing Chrome (MediaCrawler pattern — strong general technique)

Before spinning up any headless browser, consider attaching to the user's **real, already-logged-in Chrome**.
This is the most robust anti-detection technique because you inherit real cookies, extensions, session state,
and a genuine browser fingerprint. MediaCrawler uses this as its **default mode** for all platform crawls.

```bash
# User relaunches Chrome with debugging port
chromium --remote-debugging-port=9222 --no-sandbox &
# Verify:
curl -s http://localhost:9222/json/version

# Agent attaches (Playwright):
browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
page = browser.contexts[0].pages[0]   # inherits login

# Agent attaches (agent-browser CLI):
npx agent-browser --cdp 9222 snapshot
```

Use CDP-attach when:
- Auth is required (login-gated content)
- The platform uses JS-computed request signing (you can call `page.evaluate()` on the platform's own signing function — no reverse engineering needed)
- Standard stealth/Firecrawl fails and Kasada/heavy anti-bot is suspected
- You need real session persistence across multiple requests

Session state caching for non-CDP Playwright runs:
```python
await context.storage_state(path="session_state.json")  # save after login
context = await browser.new_context(storage_state="session_state.json")  # reload
```

Pitfalls:
- Requires user to manually launch Chrome with --remote-debugging-port=9222 before agent connects
- Fedora Silverblue: use Flatpak Chromium, not Firefox (Firefox CDP incompatible — uses WebDriver BiDi)
- Not suitable for unattended cron jobs; depends on user's live browser session

## Helper script
Basic use:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --headless https://target.example
```

For small reusable rendered-DOM probes on public social pages, keep a lightweight local Chromium helper alongside the broader Firecrawl/stealth workflow. Treat its JSON output as an intermediate artifact (`html`, `title`, `description`) that downstream code can parse repeatedly without re-driving the browser.

Force stealth path:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --force-stealth --headless https://target.example
```

JSON-only output for piping:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --json-only --headless https://target.example
```

Debug block detection decisions:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --headless --debug-block-detection https://target.example
```
This prints a compact JSON debug line to stderr showing Firecrawl block reasons and whether fallback was triggered.

Save per-run debug files:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --headless --save-debug-files https://target.example
```
This writes per-run payloads under `~/.hermes/state/firecrawl-stealth-debug/<timestamp>-<host>/`, including Firecrawl and final result JSON. When fallback runs, the stealth result is saved there too.

Persistent cookie/storage reuse:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py --force-stealth --headless --session-name target-example https://target.example
```
This stores the browser profile under `~/.hermes/state/stealth-browser-sessions/<session-name>` so later runs reuse cookies and local storage.

Proxy + header example:
```bash
~/.hermes/scripts/firecrawl_stealth_fetch.py \
  --force-stealth --headless \
  --proxy http://user:pass@host:port \
  --header 'Accept-Language: en-AU,en;q=0.9' \
  --timezone Australia/Sydney \
  https://target.example
```

## Output shape
The script prints JSON with:
- `mode`: `firecrawl` or `stealth-browser-mcp`
- `success`: boolean
- `url`
- `title`
- `content`
- `html`
- `metadata`
- optional `fallback_errors`
- optional `debug.firecrawl_block_reasons`
- optional `debug.fallback_triggered`

## Manual Hermes workflow
If the helper script is not enough:
1. Try `web_extract` first.
2. If blocked, use the `stealth-browser-mcp` tools:
   - `spawn_browser`
   - `navigate`
   - `get_page_content`
   - `query_elements`
   - `take_screenshot`
3. Reuse the resolved page state or content in the next extraction step.

## Verification commands
```bash
hermes mcp test stealth-browser-mcp
~/.hermes/scripts/firecrawl_stealth_fetch.py --headless https://example.com
~/.hermes/scripts/firecrawl_stealth_fetch.py --force-stealth --headless https://example.com
~/.hermes/scripts/firecrawl_stealth_fetch.py --headless --debug-block-detection https://example.com
```

## Kasada-protected sites (realestate.com.au and similar)

Some sites use **Kasada** bot protection (identifiable by `window.KPSDK` in the page JS).
Kasada operates at multiple layers — JS fingerprinting, TLS fingerprinting, IP reputation,
timing analysis — and blocks ALL of the following (confirmed July 2026):

- Headless Chromium (Playwright/agent-browser) — blank white page rendered
- Firecrawl via basic proxy — returns HTTP 429 Too Many Requests
- Camofox/Camoufox Firefox stealth browser — blank aria snapshot (snapshotLen: 0), no DOM
- curl with spoofed browser UA — empty body

**Confirmed blocked:** realestate.com.au, domain.com.au (listing pages and search).

**Signal:** page body contains `window.KPSDK={};KPSDK.now=...` — this is the Kasada challenge JS.
When you see this, the page content is not coming. Don't retry with a different tool.

**The only reliable bypass is a live authenticated human browser session:**
1. Ask user to paste listing details directly — fastest, most reliable
2. CDP attach to user's live browser: ask them to relaunch **Chromium** (NOT Firefox — see
   pitfall below) with `chromium --remote-debugging-port=9222 --no-sandbox`, navigate to page
   normally (passes Kasada with real browser fingerprint + existing cookies), then connect:
   `npx agent-browser --cdp 9222 snapshot` — inherits full session state
3. Camofox with imported cookie export: if user exports REA cookies via browser extension
   and imports via `--session-name`, Camofox can reuse them. Cold sessions still blocked.

**CDP attach browser choice: Chromium only, NOT Firefox (confirmed July 2026).**
Firefox's `--remote-debugging-port` serves an httpd.js server that returns 404 for ALL
Chrome CDP REST endpoints (`/json/list`, `/json/version`, `/json/targets`). Firefox uses
**WebDriver BiDi** (not Chrome CDP) — incompatible with Playwright `connect_over_cdp()` and
`npx agent-browser --cdp`. Firefox CAN be controlled via BiDi (raw WebSocket to `/session`,
no Origin header, `session.new` first) — see `references/firefox-bidi-websocket-control.md`
for the full working implementation. But for Kasada bypass specifically, use Chromium CDP.
For CDP attach to work with agent-browser, the user must relaunch **Chromium** (system or Flatpak), not Firefox:
```bash
chromium --remote-debugging-port=9222 --no-sandbox &
# OR (Flatpak)
flatpak run org.chromium.Chromium --remote-debugging-port=9222 --no-sandbox &
```
Then verify: `curl -s http://localhost:9222/json/version` should return JSON with `webSocketDebuggerUrl`.

**Don't waste more than 1-2 attempts on Kasada-protected sites.** Escalate to option 1 immediately.

### Camofox (port 9377): when to use vs stealth-browser-mcp
Camofox is a lightweight REST-based headless browser (no MCP, no CDP). Use Camofox when:
- stealth-browser-mcp is unavailable or crashed (Camofox is the fallback)
- Task is simple: navigate + extract text (no clicks, form fills, or JS interaction needed)
- Low-overhead scraping: Camofox has no session state overhead
Use stealth-browser-mcp when: JS interaction required, cookies/sessions needed, CDP-level inspection needed.
Camofox REST: `POST http://localhost:9377/scrape {url, options}` - see references/camofox-rest-api-quick-reference.md for full API.

## Camofox local setup (jo-inc/camofox-browser)

Camofox is a Firefox-based stealth browser REST API (port 9377). Useful for Cloudflare-protected
sites and authenticated sessions. Does NOT bypass cold-session Kasada (REA/Domain).

**Install (no Docker needed):**
```bash
git clone https://github.com/jo-inc/camofox-browser ~/camofox-browser
cd ~/camofox-browser && npm install
npm start   # -> http://localhost:9377 (starts Camoufox Firefox + REST server)
```

**Health check:**
```bash
curl -s http://localhost:9377/health
# {"ok":true,"engine":"camoufox","browserConnected":true,"browserRunning":true,...}
```

**Core API (tab lifecycle):**
```bash
# Create tab and navigate
TAB=$(curl -s -X POST http://localhost:9377/tabs \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","sessionKey":"task1","url":"https://target.example"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tabId'])")

sleep 8  # JS-heavy sites need 6-10s to fully render

# Accessibility snapshot (returns JSON with snapshot + refs)
curl -s "http://localhost:9377/tabs/$TAB/snapshot?userId=agent"

# Screenshot (returns raw PNG bytes, not JSON — save directly)
curl -s "http://localhost:9377/tabs/$TAB/screenshot?userId=agent" -o /tmp/page.png

# Click element by ref
curl -s -X POST "http://localhost:9377/tabs/$TAB/click" \
  -H "Content-Type: application/json" -d '{"userId":"agent","ref":"e5"}'
```

**Silverblue/Flatpak notes:**
- On Fedora Silverblue, Camofox auto-detects the Flatpak Chromium as backend
  (visible in `ps` as `/app/chromium/chrome` via bwrap sandbox)
- `npm start` works directly from host terminal — no container needed
- Hermes config: `CAMOFOX_URL=http://localhost:9377` routes browser tools through Camofox

## stealth-browser-mcp setup on Fedora Silverblue / Flatpak Chromium

`nodriver` (the CDP engine powering stealth-browser-mcp) searches for Chrome by a hardcoded
list of binary names: `google-chrome`, `chromium-browser`, `chrome`, `google-chrome-stable`.
On Fedora Silverblue, Chromium is a Flatpak — its host wrapper lands at
`~/.local/bin/chromium`, which is NOT in nodriver's search list. This causes a silent
connection failure: `hermes mcp test stealth-browser-mcp` reports "Connection closed" even
though `server.py` itself starts fine.

**Diagnosis:** run `hermes mcp test stealth-browser-mcp` — "Connection closed" after ~7s
means nodriver can't find Chrome, not an MCP protocol error.

**Fix (one-time, survives reboots):**
```bash
ln -sf ~/.local/bin/chromium ~/.local/bin/google-chrome
hermes mcp test stealth-browser-mcp   # should show ✓ Connected, 97 tools
```

**Verify Flatpak Chromium CDP capability before blaming the symlink:**
```bash
timeout 5 flatpak run org.chromium.Chromium --headless --remote-debugging-port=9222 \
  --no-sandbox about:blank 2>&1 | grep -i "DevTools listening"
# Must print: DevTools listening on ws://127.0.0.1:9222/...
```
Zygote/ptrace sandbox warnings in the output are harmless — headless CDP still works.

## Pitfalls
- Stealth browser success still depends on IP reputation and site-specific challenge behavior.
- Some targets may require non-headless runs, persistent sessions, or proxy rotation.
- `--session-name` / `--session-dir` reuse browser storage; use separate sessions per target/account to avoid cross-site contamination.
- If you add more helper scripts that import stealth-browser modules, pin them to the stealth MCP venv interpreter or explicitly activate that venv before execution.
- A benign websocket close warning may appear after stealth browser shutdown; verify the JSON result before treating it as a failure.
- For Facebook-style rendered blobs, decode extracted string payloads with `json.loads` rather than `unicode_escape`; the latter can reintroduce surrogate/UTF-8 write failures.
- Rendered social HTML often contains repeated post URLs and texts; dedupe by canonical URL/text before emitting summaries.
- X and Instagram may still expose only partial recent-post data without authenticated session reuse; treat rendered metadata as a success even when full recent-post extraction is incomplete.
## Social Platform Extraction Pitfalls (from social-platform-notes.md)

**X/Twitter tweet extraction (browser-free):**
- `browser_navigate` reliably times out on x.com; do NOT use it as the primary path.
- Proven fallback: `web_search(query="<user> site:x.com <id>")` for snippet, then `web_extract(urls=["https://x.com/<user>/status/<id>"])` for full body. No browser session needed.

**Facebook public-page extraction:**
- Rendered DOM exposes post/reel data raw `urllib` misses.
- Scan rendered HTML for: `"creation_time":<unix_ts>`, `"url":"...facebook.com/reel/..."`, `"text":"..."` payloads.
- Decode JSON-string text with `json.loads(f'"{raw}"')` — not `unicode_escape` — to avoid surrogate/encoding errors.
- Deduplicate Facebook URLs before emitting summaries; blobs often repeat the same reel/post.

**General social fallback order:**
1. Normal extractor / static fetch first.
2. Real browser render if JS-heavy or static HTML lacks post links.
3. Platform-specific tools (e.g. `yt-dlp` for YouTube).
4. Cache rendered HTML as reusable intermediate artifact.

## Reference files

- `references/camofox-rest-api-quick-reference.md` — Camofox REST API Quick Reference
- `references/kasada-bypass-research-2026.md` — Kasada Anti-Bot Bypass Research — July 2026
