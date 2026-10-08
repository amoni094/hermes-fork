---
name: tplink-ax55-api-auth
description: "Use when authenticating to TP-Link AX55 router API. Router authentication, network device API, admin session management."
---

# TP-Link AX55 API Authentication

## Problem
The AX55 web UI uses RSA+AES encrypted login — plaintext POST/GET won't work. The browser vault_fill also fails with hash URLs on camofox tabs.

## Quick Login (use this)

Run the login script — it handles camofox startup, SSL patch, module import, RSA+AES login, and vault password retrieval automatically:

```python
import subprocess, json, sys
sys.path.insert(0, '/var/home/rainbow/.hermes/hermes-fork')

r = subprocess.run(
    ['python3', '/var/home/rainbow/.hermes/profiles/fork/scripts/router-login.py'],
    capture_output=True, text=True
)
result = json.loads(r.stdout)   # {"stok": "...", "tab_id": "...", "serviceAdapter": true}
stok = result['stok']
tab_id = result['tab_id']
# serviceAdapter (window._sa) is now available in the tab for API calls
```

Then make API calls via camofox evaluate on the same tab_id. Vault handle: `vault_8f686f61c712`.

## Manual Approach (if script fails)

Use a camofox API tab with `ignoreHTTPSErrors: true` (required for self-signed cert), import the router's own JS modules, and call the login function directly.

### Step 1: Patch camofox for SSL bypass
```
# Add ignoreHTTPSErrors: true to contextOptions in server.js (~line 1392)
# Restart camofox after patch
```

### Step 2: Create camofox API tab
```python
r = subprocess.run(['curl', '-s', '-X', 'POST', 'http://localhost:9377/tabs',
     '-H', 'Content-Type: application/json',
     '-d', json.dumps({"userId": "hermes", "sessionKey": "router-login", "url": "https://192.168.0.1/webpages/index.html"})], ...)
TAB = result['tabId']
```

### Step 3: Load the store modules
```javascript
// Wait ~5s after tab creation for page load
await import('/webpages/js/index-CsRkz4iz.js');  // main chunk
const m = await import('/webpages/js/update-store-BP3PGMSQ.js');
window._sa = m.s;   // serviceAdapter: {read, write, load, insert, remove, request}
window._EM = m.E;   // EncryptManager
window._RSA = m.R;  // RSA class
```

### Step 4: Login
```javascript
async function doLogin(password) {
  const authData = await window._sa.read('/login?form=auth');
  const keysData = await window._sa.read('/login?form=keys');
  const [authN, authE] = authData.key;
  window._EM.init('', authData.seq, authN, authE);
  const encPw = window._RSA.encrypt(password, ...keysData.password);
  return await window._sa.write('/login?form=login',
    {password: encPw, operation: 'login', confirm: true},
    {preventSuccess: true, preventError: true, withAesKey: true}
  );
  // Returns {stok: '...'} on success
}
```

### Step 5: Read vault password and call login
```python
from agent.vault_backends import backend_for_handle
pw = backend_for_handle('vault_HANDLE').resolve_password('vault_HANDLE')
# Pass pw to evaluate() as JSON string in JS expression
# Delete pw immediately after use
```

## Key Endpoints (via serviceAdapter after login)

- `/login?form=keys` — RSA public key (password encryption)
- `/login?form=auth` — RSA key + seq (session AES)
- `/admin/access_control?form=enable` — access control on/off
- `/admin/access_control?form=mode` — `{accessMode: 'black'|'white'}`
- `/admin/access_control?form=black_list` — load/insert/remove blocked devices
- `/admin/access_control?form=black_devices` — available devices to block
- `/admin/wireless?form=wireless_2g` — 2.4GHz settings
- `/admin/system?form=sysmode` — system mode

## Important Pitfalls

- **Access control blacklist blocks ALL traffic** (LAN + internet), not just internet. Not suitable for printer isolation if LAN printing is needed.
- The `ignoreHTTPSErrors` patch must be reverted after use (security).
- Vault password must be injected via JSON in POST body (not subprocess argv).
- The camofox tab must load `index-CsRkz4iz.js` before importing `update-store-BP3PGMSQ.js` or the Pinia store won't initialize.
- Module imports take ~3-5 seconds to complete.

## Access Control Format

Blacklist entry format:
```json
{"name": "DeviceName", "deviceType": "Printer", "mac": "D4-4B-5E-FF-19-3B",
 "ipaddr": "192.168.0.99", "host": "NON_HOST", "conn_type": "wired", "key": ""}
```
MAC format: `XX-XX-XX-XX-XX-XX` (dashes, not colons).

## browser_vault_fill Bug (fixed in hermes-fork)

`browser_vault_fill` was failing with "Could not determine the current page origin" because `_eval_js()` in `browser_vault_tool.py` looked up the supervisor with the raw task_id instead of the resolved session key. Fix: use `SUPERVISOR_REGISTRY.get(_last_session_key(task_id))` in both `_eval_js` and `_ensure_supervisor`. Applied to `/var/home/rainbow/.hermes/hermes-fork/tools/browser_vault_tool.py` — takes effect next session.
