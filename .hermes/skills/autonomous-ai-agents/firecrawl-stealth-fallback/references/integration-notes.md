# Firecrawl + stealth-browser integration notes

Session-learned details worth reusing:

## Why `stealth-browser-mcp` won over `undetectable-fingerprint-browser`
- It is already an MCP server, so Hermes can register and test it directly.
- It exposes browser-management, navigation, DOM, screenshot, and cookie/storage tools without extra glue code.
- It supports launch-time proxy configuration and persistent `user_data_dir` sessions.
- The alternative repo may still be useful as a research source for anti-detect ideas, but it is a worse direct Hermes/Firecrawl integration target.

## Durable implementation pattern
1. Keep `web.extract_backend` / normal extraction on Firecrawl.
2. Treat stealth browser as fallback/escalation, not the default.
3. Escalate on either:
   - hard Firecrawl failure, or
   - challenge-page signals in returned content (`Just a moment`, Cloudflare, captcha, JS/cookie gate, 401/403/429/503).
4. Preserve stdout JSON stability; print fallback/debug decisions to stderr.

## Helper-script implementation detail
If the helper imports code from the installed stealth MCP tree (`browser_manager`, `models`, `dom_handler`), execute it with the MCP venv interpreter. Using plain system Python can fail on missing dependency imports such as `nodriver`, even when `hermes mcp test stealth-browser-mcp` passes.

## Useful runtime knobs
- `--force-stealth`: bypass Firecrawl for known-hard targets.
- `--session-name` or `--session-dir`: reuse cookies/local storage across runs.
- `--proxy`: push stealth traffic through a residential or other upstream proxy.
- `--header` and `--timezone`: shape locale/request context.
- `--debug-block-detection`: emit fallback reasoning without polluting stdout JSON.

## Verification pattern
- Verify normal page stays on Firecrawl.
- Verify forced-stealth path succeeds.
- Verify debug mode reports `block_reasons: []` on clean pages.
- Unit/probe the block detector with simulated challenge HTML so future edits do not silently weaken fallback triggering.
