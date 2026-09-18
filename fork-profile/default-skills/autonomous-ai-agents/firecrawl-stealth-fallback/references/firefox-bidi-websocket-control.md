# Firefox WebDriver BiDi — Raw WebSocket Control

Confirmed working: Firefox 152 on Fedora 44 Silverblue (July 2026).

## When to use

- You need to control a live Firefox session (user's real browser with cookies)
- The task does NOT require Chromium-specific CDP (`/json/list`, `npx agent-browser --cdp`, Playwright `connect_over_cdp`)
- Useful for non-Kasada sites where Firefox's fingerprint is preferable, or where the user only has Firefox open

## Launch Firefox with remote debugging

```bash
# System Firefox (Fedora — binary at /usr/lib64/firefox/firefox)
WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 \
  /usr/lib64/firefox/firefox --remote-debugging-port=9222 "https://target.example" &

# Flatpak Firefox — use same binary path via Flatpak env, or let system wrapper pick it up
# NOTE: `flatpak run org.mozilla.firefox` may exit immediately if another instance is running
# Kill existing firefox first: kill $(pgrep -f /usr/lib64/firefox/firefox)
```

Wait 10-15 seconds for Firefox to fully start before connecting.

## Why NOT standard Chrome CDP

Firefox's `--remote-debugging-port` serves `httpd.js` — NOT Chrome's CDP API.
All Chrome CDP REST endpoints return 404:
- `/json` → 404
- `/json/list` → 404  
- `/json/version` → 404
- `/` → 200 "httpd.js is up and serving requests!" (not useful)

Do NOT use `Playwright.connect_over_cdp()` or `npx agent-browser --cdp` with Firefox.

## BiDi endpoint

Firefox exposes WebDriver BiDi at: `ws://localhost:9222/session`

**Origin restriction:** Firefox rejects connections with any Origin header set.
Omit the Origin header entirely — the handshake will succeed with HTTP 101.

```
GET /session HTTP/1.1
Host: localhost:9222
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <base64 key>
Sec-WebSocket-Version: 13
# NO Origin header
```

## Session lifecycle (required order)

1. `session.new` — MUST be called first, before any other command
   - Returns `sessionId` on success
   - Error "Maximum number of active sessions" = a previous session is still held open
     → Kill Firefox and restart fresh (`kill $(pgrep -f /usr/lib64/firefox/firefox)`)
   - Error "session not created" = same cause, same fix
2. `browsingContext.getTree` — lists all open tabs with context IDs and URLs
3. `browsingContext.navigate` — navigate a context to a URL
4. `script.evaluate` — run JS in a context (e.g. `window.scrollBy(0, 700)`)
5. `browsingContext.captureScreenshot` — returns base64 PNG in `result.data`

## Working Python implementation

```python
import socket, base64, struct, json, time

def ws_connect():
    key = base64.b64encode(b'hermesagent12345').decode()
    sock = socket.create_connection(('localhost', 9222), timeout=10)
    # No Origin header — Firefox rejects any Origin value
    req = (
        f'GET /session HTTP/1.1\r\n'
        f'Host: localhost:9222\r\n'
        f'Upgrade: websocket\r\n'
        f'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Key: {key}\r\n'
        f'Sec-WebSocket-Version: 13\r\n'
        '\r\n'
    )
    sock.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        resp += sock.recv(4096)
    assert b'101' in resp, f'Handshake failed: {resp[:100]}'
    return sock

def ws_send(sock, data):
    payload = json.dumps(data).encode()
    n = len(payload)
    mask = b'\x01\x02\x03\x04'
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x81, 0x80 | n]) if n < 126 else bytes([0x81, 0xfe]) + struct.pack('>H', n)
    sock.sendall(header + mask + masked)

def ws_recv(sock, timeout=15):
    sock.settimeout(timeout)
    h = sock.recv(2)
    length = h[1] & 0x7f
    if length == 126: length = struct.unpack('>H', sock.recv(2))[0]
    elif length == 127: length = struct.unpack('>Q', sock.recv(8))[0]
    data = b''
    while len(data) < length:
        data += sock.recv(min(65536, length - len(data)))
    return json.loads(data)

# --- Usage ---
sock = ws_connect()

# 1. Create session (required first)
ws_send(sock, {'id': 0, 'method': 'session.new', 'params': {'capabilities': {}}})
r = ws_recv(sock)
assert r.get('type') == 'success', f"session.new failed: {r}"

# 2. List tabs
ws_send(sock, {'id': 1, 'method': 'browsingContext.getTree', 'params': {}})
tree = ws_recv(sock)
ctxs = tree['result']['contexts']
ctx_id = ctxs[0]['context']
print(f"Active tab: {ctxs[0]['url']}")

# 3. Navigate
ws_send(sock, {'id': 2, 'method': 'browsingContext.navigate', 'params': {
    'context': ctx_id,
    'url': 'https://target.example',
    'wait': 'interactive'   # waits for DOMContentLoaded
}})
ws_recv(sock, timeout=30)
time.sleep(8)  # JS-heavy sites need extra time

# 4. Screenshot
ws_send(sock, {'id': 3, 'method': 'browsingContext.captureScreenshot',
               'params': {'context': ctx_id}})
shot = ws_recv(sock, timeout=20)
png = base64.b64decode(shot['result']['data'])
with open('/tmp/page.png', 'wb') as f:
    f.write(png)

# 5. Scroll and re-screenshot
ws_send(sock, {'id': 4, 'method': 'script.evaluate', 'params': {
    'expression': 'window.scrollBy(0, 700)',
    'target': {'context': ctx_id},
    'awaitPromise': False
}})
ws_recv(sock)
time.sleep(2)
# repeat screenshot...

sock.close()
```

## Pitfalls

- **One session at a time.** Firefox allows only one active BiDi session per process.
  If you get "Maximum number of active sessions", kill Firefox and restart — there is no
  session.delete endpoint that reliably frees the slot without restarting.
- **Don't close the socket mid-session** without a `session.end` — the session stays open
  until Firefox exits, blocking new connections.
- **websocket-client library**: `websocket.WebSocketApp` always sends an Origin header
  (`ws://localhost:9222` or `http://localhost:9222`) which Firefox rejects with 400.
  Use raw sockets (as above) or monkey-patch the library to omit Origin.
- **Flatpak Firefox**: `flatpak run org.mozilla.firefox` may silently fail if an existing
  system Firefox instance is already running. Prefer the direct binary path
  `/usr/lib64/firefox/firefox` for reliable launch.
- **Page load timing**: `wait: 'interactive'` triggers at DOMContentLoaded but JS bundles
  run after. Add 6-10s sleep before screenshot for React/Vue/Next.js pages.
- **Large payloads**: BiDi screenshot returns full-page base64 PNG inline over the WebSocket.
  A 1280x720 screenshot is ~1MB b64. Ensure your ws_recv handles large frames (use 65536
  chunk reads, not recv(length) in one shot for big payloads).

## Kasada limitation

Firefox BiDi control does NOT help bypass Kasada on realestate.com.au / domain.com.au.
Kasada blocks at the IP reputation + TLS fingerprint level — a freshly launched Firefox
(even with BiDi) navigating to REA gets a blank white page with no DOM.
Only a *pre-authenticated* human session (user navigated normally with cookies) survives.
