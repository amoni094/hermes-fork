# News/music/stay-in dashboard reference

Session pattern proven in this workspace:
- App path: `/var/home/rainbow/news_dashboard/app.py`
- Default local URL: `http://127.0.0.1:8765/`
- Recommended routes:
  - `/`
  - `/healthz`
  - `/api/daily-update`
  - `/api/music`
  - `/api/stayin`

Data-source pattern that worked well:
- News: Google News RSS search grouped into user topic lanes; no API key required.
- Music: local reference files from the loaded `suggest-music` skill:
  - `/var/home/rainbow/.hermes/skills/research/suggest-music/references/music_taste_seeds.yaml`
  - `/var/home/rainbow/.hermes/skills/research/suggest-music/references/music_map_seed_neighbors.yaml`
- Stay-in picks: small curated taste-fit pool with verified Metacritic values stored locally in the app.

Verification pattern that worked:
1. `python3 -m py_compile <app.py>`
2. Start the server locally.
3. Check `/healthz`.
4. Curl each JSON endpoint and confirm counts.
5. Open `/` in browser tools.
6. Click refresh buttons and confirm rotating panes actually change across repeated requests.

Security/hardening notes:
- Escape interpolated data before assigning to `innerHTML`.
- Prefer `defusedxml.ElementTree` for RSS/XML parsing when available.
- Keep each pane independently refreshable so partial failures are contained.
