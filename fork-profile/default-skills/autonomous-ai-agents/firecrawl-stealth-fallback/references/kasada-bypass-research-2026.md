# Kasada Anti-Bot Bypass Research — July 2026

## What Kasada Is

Kasada is an Australian anti-bot platform used by realestate.com.au, domain.com.au,
Canada Goose, and others. It operates at MULTIPLE layers simultaneously:

1. JS fingerprinting — detects navigator.webdriver, automation flags, headless markers
2. TLS fingerprinting — detects non-browser TLS handshake patterns
3. IP reputation — datacenter IPs flagged regardless of JS fingerprint
4. Timing/behaviour analysis — detects bot-speed interactions

**Signal:** page body contains `window.KPSDK={};KPSDK.now=...` — Kasada challenge JS.
When you see this the page will not render content. A blank white screenshot confirms blocking.

**Key insight:** All three bypass layers must be addressed together. A tool that only
fixes JS fingerprinting still fails on datacenter IPs.

---

## Open-Source Tool Comparison (confirmed working as of July 2025-2026)

### Patchright ✅ (with residential proxy)
- Drop-in replacement for Playwright Python — just change the import
- Patches well-known Playwright automation tells (navigator.webdriver, CDP detection, etc.)
- Install: `pip install patchright && python -m patchright install chromium`
- Usage: identical to Playwright, add proxy config
- Kasada success: YES — confirmed on Canada Goose and similar sites
- IP requirement: **requires residential proxy** for datacenter IPs
- GitHub: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python

```python
from patchright.sync_api import sync_playwright

proxies = {'server': 'http://ENDPOINT:PORT', 'username': 'USER', 'password': 'PWD'}
ARGS = ['--no-first-run', '--disable-blink-features=AutomationControlled']

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=200, args=ARGS,
                                ignore_default_args=["--enable-automation"])
    context = browser.new_context(proxy=proxies, ignore_https_errors=True)
    page = context.new_page()
    page.goto('https://target.com/', timeout=0)
    html = page.content()
    browser.close()
```

### Zendriver ✅ (with residential proxy)
- Fork of Nodriver (successor to undetected-chromedriver)
- Uses Chrome DevTools Protocol directly — no WebDriver at all
- Async Python API; more actively maintained than Nodriver
- Install: `pip install zendriver`
- Kasada success: YES — confirmed on Kasada-protected sites
- IP requirement: **requires residential proxy** for datacenter IPs
- GitHub: https://github.com/cdpdriver/zendriver

```python
import asyncio
import zendriver as zd

proxies = {'server': 'http://ENDPOINT:PORT', 'username': 'USER', 'password': 'PWD'}

async def main():
    async with await zd.start(proxy=proxies) as browser:
        await browser.get('https://target.com/')
        await asyncio.sleep(10)
        await browser.stop()

asyncio.run(main())
```

### Camoufox (Python direct) ✅ (with residential proxy)
- Firefox fork with C++-level fingerprint spoofing (hardwareConcurrency, WebGL, AudioContext)
- Install: `pip install camoufox && python -m camoufox fetch`
- Kasada success: YES — confirmed on Canada Goose
- IP requirement: **requires residential proxy** — C++-level spoof alone not enough
- Key: forge a non-Linux OS fingerprint (`os="windows"`) to avoid Linux server detection
- Note: the camofox-browser Node wrapper does NOT set OS spoof or proxy by default —
  use the Python library directly for Kasada bypass

```python
from camoufox.sync_api import Camoufox

proxies = {'server': 'http://ENDPOINT:PORT', 'username': 'USER', 'password': 'PWD'}

with Camoufox(humanize=True, os="windows", geoip=True, proxy=proxies) as browser:
    page = browser.new_page()
    page.goto('https://target.com/', timeout=0)
    html = page.content()
    browser.close()
```

### Standard Playwright ❌
- Fails on Kasada regardless of flags — well-documented pattern
- Even with `--disable-blink-features=AutomationControlled` and Brave binary: blank page

---

## Residential Proxy Options

All Kasada bypass tools require a residential proxy when running from datacenter/server IPs.
**Exception:** if running FROM A RESIDENTIAL IP (home internet), no proxy needed.

### Webshare
- Free tier: 10 datacenter proxies (NOT residential — won't help with Kasada)
- Residential: ~$7/month for 1GB (~500-1000 REA listing fetches)
- Pay-as-you-go: ~$7/GB residential
- API format: `http://user:pass@proxy.webshare.io:80`
- URL: https://webshare.io

### Proxies.fo
- Residential: ~$3-5/GB
- Smaller provider, less likely to be on Kasada's proxy blocklist
- URL: https://proxies.fo

### IPRoyal
- Pay-as-you-go residential: ~$7/GB
- No monthly minimum
- URL: https://iproyal.com

### Bright Data
- Industry standard, most reliable residential pool
- Pricing: ~$15/GB residential (expensive)
- Free trial available
- URL: https://brightdata.com

### Minimum viable spend for REA/Kasada
For occasional use (checking ~10-20 property listings/month):
- ~1GB/month = ~$7-15/month on Webshare or IPRoyal
- At ~500KB per listing page = 2000 pages/GB = well within budget

---

## The Residential IP Advantage

**Critical insight:** Kasada's IP reputation layer only blocks DATACENTER IPs.
Residential ISP IPs (Aussie Broadband, Telstra, iiNet, etc.) are NOT flagged.

If running browser tools FROM YOUR OWN HOME MACHINE (not a VPS/server), your IP
is already residential. In this case:
- CDP attach to live Firefox/Chromium = works (real browser + residential IP + existing cookies)
- Zendriver/Patchright from your home machine = likely works WITHOUT a proxy
- The tools only need a proxy when running on cloud/server infrastructure

This means the simplest reliable solution for personal use is:
CDP attach to the user's live browser (see firecrawl-stealth-fallback main SKILL.md
for the Chromium + remote debugging port workflow).

---

## Managed Cloud APIs (no local setup)

### Scrapfly
- Handles proxy rotation + JS rendering + anti-bot bypass as a single API call
- Pricing: ~$50/month for 500K API credits; REA listing ≈ ~5 credits
- API: `https://api.scrapfly.io/scrape?key=YOUR_KEY&url=TARGET&render_js=true&asp=true`
- Has MCP server: check https://scrapfly.io/docs for MCP/Claude integration
- No confirmed report of Kasada bypass on REA specifically (as of July 2026)

### ZenRows
- Similar managed approach: premium proxies + fortified browser
- Pricing: ~$49/month starter
- Confirmed Kasada bypass on general Kasada-protected sites
- URL: https://zenrows.com

### Browserbase
- Cloud browser service, configured via BROWSERBASE_API_KEY in Hermes .env
- CDP-compatible — Hermes has native support via browser.cloud_provider = "browserbase"
- Pricing: ~$150/month professional; free tier limited
- URL: https://browserbase.com

---

## Decision Tree

```
Is the target site Kasada-protected?
  → Check for `window.KPSDK` in page source
  → Or: 429 then loads + x-kpsdk-ct headers in DevTools

YES:
  Running on residential home IP?
    YES → Try Zendriver/Patchright without proxy first
           OR CDP attach to live browser (Chromium, port 9222)
    NO (VPS/server/CI) → Add residential proxy (~$7/GB)
                          Use Patchright or Zendriver with proxy

Occasional use (< 50 pages/month)?
  → Ask user to paste details (fastest, free)
  OR CDP attach workflow (one-time browser relaunch)
  OR Scrapfly/ZenRows managed API (~$49-50/month)

Frequent/automated use:
  → Zendriver + Webshare residential proxy
  OR Scrapfly API with caching

NOT Kasada (Cloudflare, basic JS challenge):
  → Camofox Node wrapper (http://localhost:9377) handles these
  → Firecrawl + stealth-browser-mcp handles most cases
```

---

## Sites Confirmed Blocked (July 2026)

| Site | Bot protection | Status |
|------|---------------|--------|
| realestate.com.au | Kasada | Blocked (all automated methods) |
| domain.com.au | Kasada | Blocked (all automated methods) |
| Canada Goose | Kasada | Bypassed with Patchright+proxy, Zendriver+proxy, Camoufox+proxy |

## Sites That Work Fine

| Site | Notes |
|------|-------|
| jelliscraig.com.au | No bot protection — reliable for comparable sales data |
| property.com.au | Minimal protection — works with Firecrawl |
| barryplant.com.au | No bot protection — best source for suburb profiles |
| view.com.au | Works with Firecrawl |
| findmyschool.vic.gov.au | JS map app — needs browser_navigate but no bot protection |
| gdp.com.au | No bot protection — fast ABS suburb data aggregator |
