# Camofox REST API Quick Reference

Source: jo-inc/camofox-browser (v1.11.2, June 2026)
Confirmed working: July 2026 on Fedora Silverblue, npm install path

## Server
- Default port: 9377
- Health: `GET http://localhost:9377/health`
  - Returns: `{"ok":true,"engine":"camoufox","browserConnected":true,"browserRunning":true,...}`

## Tab lifecycle

### Create tab + navigate
```bash
TAB=$(curl -s -X POST http://localhost:9377/tabs \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","sessionKey":"task1","url":"https://target.example"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tabId'])")

sleep 8  # JS-heavy sites (findmyschool, maps) need 6-10s; simple sites 3-4s
```

### Accessibility snapshot
```bash
curl -s "http://localhost:9377/tabs/$TAB/snapshot?userId=agent"
# Returns JSON with 'snapshot' (text) and element refs (e1, e2, ...)
```

### Screenshot (raw PNG — save directly, don't parse as JSON)
```bash
curl -s "http://localhost:9377/tabs/$TAB/screenshot?userId=agent" -o /tmp/page.png
```

### Click element by ref
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB/click" \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","ref":"e5"}'
```

### Type into element
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB/type" \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","ref":"e8","text":"3 Packer Street Murrumbeena"}'
```

### Fill (clear + type)
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB/fill" \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","ref":"e8","text":"3 Packer Street Murrumbeena"}'
```

### Navigate existing tab
```bash
curl -s -X POST "http://localhost:9377/tabs/$TAB/navigate" \
  -H "Content-Type: application/json" \
  -d '{"userId":"agent","url":"https://new-url.example"}'
```

### Close tab
```bash
curl -s -X DELETE "http://localhost:9377/tabs/$TAB?userId=agent"
```

## Hermes config integration
Set in ~/.hermes/.env (or via hermes config):
```
CAMOFOX_URL=http://localhost:9377
```
When set, Hermes browser tools (browser_navigate, browser_snapshot, etc.) route through
Camofox automatically instead of agent-browser/headless Chrome.

## Silverblue notes
- On Fedora Silverblue, `npm start` from ~/camofox-browser works directly from host terminal
- Camofox auto-detects Flatpak Chromium as backend (visible as /app/chromium/chrome via bwrap)
- No Docker needed for local use
- CAMOFOX_URL in config routes all Hermes browser_* tools through it

## Kasada limitation
Cold Camofox sessions are blocked by Kasada (realestate.com.au, domain.com.au).
Camofox with imported user cookies (export via extension, import via --session-name) MAY work
but untested as of July 2026. The blank aria snapshot (snapshotLen: 0) is the Kasada signal.
Camofox IS useful for Cloudflare-protected sites and non-Kasada JS-heavy sites.

## findmyschool.vic.gov.au via Camofox REST (confirmed working July 2026)
The site is a JS map app — works via Camofox REST. Interaction sequence:
1. Create tab with URL https://www.findmyschool.vic.gov.au/ — wait 8s
2. Fill address combobox (ref e8 typically) with partial address like "3 Packer Street Murrumbeena"
3. Wait 2-3s, snapshot — autocomplete dropdown appears
4. Click appropriate dropdown option (e.g. "1/3 Packer Street Murrumbeena 3163")
5. Wait 2-3s, snapshot — year/school type selectors appear
6. Click year label (2026 = e8 radio) and "Secondary" label (e11 or similar)
7. Wait 4-5s, snapshot — result: "For 2026 enrolments, your address is in the secondary school zone for: [School Name]"
