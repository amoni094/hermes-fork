# Vite dashboard URL discovery and LAN startup

Use this pattern when the user asks for the IP address, login URL, or "start it" for a local Vite-based dashboard.

## Goal
Answer with the real reachable URL, not a guessed localhost default.

## Fast discovery order
1. Read the repo README for documented dev/preview commands and any stated local-only/LAN assumptions.
2. Read `package.json` scripts to see whether the app uses `vite`, `vite preview`, or a custom wrapper.
3. Read `vite.config.*` for explicit `server.host`, `server.port`, `preview.host`, or `preview.port` overrides.
4. Check live machine IPs with `hostname -I`.
5. Check listening ports with `ss -ltnp`, especially common Vite ports `5173`, `5174`, and preview `4173`.
6. If something is listening, verify with `curl -I http://127.0.0.1:<port>/` before claiming the URL works.

## Answering pattern
- If the app is not running:
  - Say it is not running now.
  - Give the machine LAN IP.
  - If the repo appears to use default Vite settings, say the likely local URL is `http://localhost:5173` and the likely LAN URL after starting with host binding is `http://<LAN-IP>:5173`.
  - Do not present a dead URL as active.
- If the user says "start":
  - Start the dev server with LAN binding: `npm run dev -- --host`
  - Keep it as a tracked background process.
  - Verify both the socket (`ss -ltnp`) and HTTP (`curl -I`) before replying.
  - Return both loopback and LAN URLs plus the background process handle.

## Notes
- Plain `vite` in `package.json` usually means localhost on port 5173 unless config overrides it.
- `vite preview` usually defaults to port 4173, so distinguish dev from preview before answering.
- For "what IP do I log into" questions on a local app, include both `localhost` and the primary LAN IP when relevant; users often mean "from this machine" and "from another device" interchangeably.
