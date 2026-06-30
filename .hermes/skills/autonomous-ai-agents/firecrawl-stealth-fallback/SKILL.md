---
name: firecrawl-stealth-fallback
description: Use Firecrawl as the default extractor and escalate to stealth-browser-mcp when bot protection blocks or degrades extraction.
created_by: agent
version: 1.0.0
---

# Firecrawl stealth fallback

Use this when a site is likely to use Cloudflare, bot checks, or JS-heavy blocking and you still want Firecrawl as the normal path.

## What is installed here
- Local Firecrawl API at `http://127.0.0.1:3002`
- Hermes MCP server `stealth-browser-mcp`
- Helper script at `~/.hermes/scripts/firecrawl_stealth_fetch.py`
- Reference notes: `references/integration-notes.md`
- Social-platform notes: `references/social-platform-notes.md`

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

## Pitfalls
- Stealth browser success still depends on IP reputation and site-specific challenge behavior.
- Some targets may require non-headless runs, persistent sessions, or proxy rotation.
- `--session-name` / `--session-dir` reuse browser storage; use separate sessions per target/account to avoid cross-site contamination.
- If you add more helper scripts that import stealth-browser modules, pin them to the stealth MCP venv interpreter or explicitly activate that venv before execution.
- A benign websocket close warning may appear after stealth browser shutdown; verify the JSON result before treating it as a failure.
- For Facebook-style rendered blobs, decode extracted string payloads with `json.loads` rather than `unicode_escape`; the latter can reintroduce surrogate/UTF-8 write failures.
- Rendered social HTML often contains repeated post URLs and texts; dedupe by canonical URL/text before emitting summaries.
- X and Instagram may still expose only partial recent-post data without authenticated session reuse; treat rendered metadata as a success even when full recent-post extraction is incomplete.
