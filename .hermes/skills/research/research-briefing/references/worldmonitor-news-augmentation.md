# WorldMonitor augmentation for news briefings

Use WorldMonitor as a secondary situational-awareness layer when a news update needs better geopolitical, infrastructure, macro, or conflict context.

What WorldMonitor is good at
- broad source coverage: 500+ RSS feeds plus structured layers
- cross-domain context: conflict, unrest, aviation, maritime, cyber, weather, outages, markets
- source freshness checks via `/api/health`
- machine-discoverable docs via `/.well-known/api-catalog`, `/openapi.yaml`, and agent skills

What to use without credentials
- `https://worldmonitor.app/llms-full.txt`
  - high-level capability and source overview
- `https://worldmonitor.app/.well-known/agent-skills/index.json`
  - discover built-in task recipes
- `https://api.worldmonitor.app/api/health`
  - verify source freshness before trusting WorldMonitor-heavy conclusions
- local app-only dev run from a checkout
  - `npm ci`
  - `npm run dev -- --host 127.0.0.1`
  - useful for UI inspection and feed behavior, but not a full local API stack

What requires auth or full self-hosting
- country briefs and most high-value intelligence endpoints require `X-WorldMonitor-Key`
- some direct API requests may hit Cloudflare bot protection from CLI clients
- for full local `/api/*` behavior, use the self-hosted stack with Podman/Docker:
  - create `.env` with `RELAY_SHARED_SECRET`, `REDIS_PASSWORD`, `REDIS_TOKEN`
  - run `uvx podman-compose up -d`
  - run `./scripts/run-seeders.sh`

How to use it in a briefing
1. Run your normal narrow topic search packs first.
2. If the topic touches geopolitics, conflict, energy, shipping, aviation, cyber, or market stress, check WorldMonitor freshness via `/api/health`.
3. Use WorldMonitor to improve context, not to replace corroboration.
4. Pull only the relevant angle:
   - conflict / country stress -> CII, country brief, regional brief
   - markets / macro -> finance, commodities, crypto, fear/greed, ETF flow
   - infrastructure -> ports, cables, chokepoints, outages, airports
   - fast-moving security -> advisories, unrest, weather, aviation disruptions
5. In the final writeup, label WorldMonitor-derived context explicitly when it materially shaped the conclusion.

Suggested wording in a briefing
- `WorldMonitor context:` source freshness was healthy and its conflict/infrastructure layers reinforced the same direction as mainstream reporting.
- `WorldMonitor caveat:` health was stale, auth-gated, or bot-blocked, so it was not used as a primary signal.

Do not
- do not treat WorldMonitor as canonical truth for a breaking claim without corroboration
- do not claim you used premium/API-key-gated endpoints unless you actually did
- do not overfit the briefing around its map/dashboard framing when the user asked for a simple news update
