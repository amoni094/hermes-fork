# Local Firecrawl quick reference

This skill assumes the local self-hosted Firecrawl instance is the default retrieval layer for crawl/scrape/research work in this workspace.

## Endpoints
- Base URL: `http://127.0.0.1:3002`
- Good verification endpoint: `GET /`
- Do not use: `GET /v1/health` on this image; it returns `404`

## Quick verification
```bash
curl -sS http://127.0.0.1:3002/
podman ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep '^firecrawl_' || true
```

Expected root response:
```json
{"message":"Firecrawl API","documentation_url":"https://docs.firecrawl.dev"}
```

## Scrape one page
```bash
curl -sS -X POST http://127.0.0.1:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "formats": ["markdown"]
  }'
```

## Pretty-print scrape output
```bash
curl -sS -X POST http://127.0.0.1:3002/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com",
    "formats": ["markdown"]
  }' | python -m json.tool
```

## Local Podman stack commands
Self-host workspace:
```bash
cd /var/home/rainbow/firecrawl-selfhost
```

Start or restart:
```bash
~/.local/bin/podman-compose up -d
```

Stop:
```bash
~/.local/bin/podman-compose down
```

Render effective config:
```bash
~/.local/bin/podman-compose config
```

Show Firecrawl containers:
```bash
podman ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep '^firecrawl_' || true
```

## Known local container names
- `firecrawl_api_1`
- `firecrawl_nuq-postgres_1`
- `firecrawl_playwright-service_1`
- `firecrawl_rabbitmq_1`
- `firecrawl_redis_1`

## Troubleshooting

### Root endpoint fails
- Check whether the Firecrawl containers are running.
- If not, restart from `/var/home/rainbow/firecrawl-selfhost` with `~/.local/bin/podman-compose up -d`.
- Confirm that port `3002` is still mapped by `firecrawl_api_1`.
- If the stack keeps disappearing across sessions or after reboot, add a user systemd unit; see `references/firecrawl-systemd-user-service.md`.

### `/v1/health` returns 404
- This is expected for the current self-host image.
- Use `GET /` plus a real scrape request as the health check instead.

### Scrape request fails
- Check API logs:
```bash
podman logs --tail=100 firecrawl_api_1
```
- Check RabbitMQ health:
```bash
podman ps --format '{{.Names}}\t{{.Status}}' | grep '^firecrawl_rabbitmq_1' || true
```
- Check Postgres health:
```bash
podman ps --format '{{.Names}}\t{{.Status}}' | grep '^firecrawl_nuq-postgres_1' || true
```
- Re-run a known-good scrape against `https://example.com` to separate stack failure from target-site failure.

### Containers up but extraction still broken
- Re-run a known-good scrape against `https://example.com` first.
- If `example.com` works but a target site fails, treat it as target-specific blocking/compatibility rather than stack failure.
- Fall back to `web_search`/`web_extract` if the target is unsuitable for Firecrawl.

## Verified local result
A real local test succeeded with:
- `GET http://127.0.0.1:3002/`
- `POST http://127.0.0.1:3002/v1/scrape` for `https://example.com`
