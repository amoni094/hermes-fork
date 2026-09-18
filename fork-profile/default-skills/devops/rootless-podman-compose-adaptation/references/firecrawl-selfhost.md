# Firecrawl self-host on rootless Podman

Session pattern that worked on Fedora Silverblue with rootless Podman.

## Layout

- Upstream clone: `/var/home/rainbow/src/firecrawl`
- Local adaptation dir: `/var/home/rainbow/firecrawl-selfhost`
- Compose runner: `~/.local/bin/podman-compose`

## Key compose adaptations

1. Use fully qualified image names for Docker Hub images.
   - `docker.io/library/redis:alpine`
   - `docker.io/library/rabbitmq:4-management`

2. RabbitMQ fix for rootless Podman:
   - `user: "999:999"`
   - healthcheck: `rabbitmq-diagnostics -q ping`

3. API dependency ordering:
   - wait for RabbitMQ `service_healthy`
   - wait for PostgreSQL `service_healthy`

4. PostgreSQL readiness:
   - healthcheck with `pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres}`

5. Firecrawl queue URL needed credentials in the local compose:
   - `NUQ_RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672`

## Verification evidence pattern

A valid verification sequence was:
1. `podman ps` confirms all `firecrawl_*` containers are up.
2. `GET /` on port 3002 returns Firecrawl API JSON banner.
3. `POST /v1/scrape` with `https://example.com` succeeds and returns markdown.

## Important note

`/v1/health` returned 404 on the tested image (returns HTML OpenAPI docs).
`/health` also returns HTML. The correct liveness check is root:
```bash
curl -sf http://localhost:3002/ | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"
```

## RabbitMQ 4.x: env var config removed (2026-09)

RabbitMQ 4.x silently exits (code 1) when `RABBITMQ_VM_MEMORY_HIGH_WATERMARK` or similar
env vars are set. The deprecation became a hard failure.

Fix: mount a config file instead of using env vars.

```yaml
# docker-compose.yaml rabbitmq service
environment: {}  # remove all RABBITMQ_* env vars
volumes:
  - ./rabbitmq-conf/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro,Z
```

```ini
# rabbitmq-conf/rabbitmq.conf
vm_memory_high_watermark.absolute = 512MiB
```

Diagnostic: `podman logs <rabbitmq_container>` shows the rejected var name just before exit.

## Redis eviction policy for BullMQ / Firecrawl

`volatile-lru` causes silent BullMQ job queue corruption — jobs without a TTL get evicted.
Always use `noeviction` for queue backends:

```yaml
command: redis-server --bind 0.0.0.0 --maxmemory 512mb --maxmemory-policy noeviction
```

Firecrawl logs `IMPORTANT! Eviction policy is volatile-lru` as a warning — that IS the
diagnostic. Fix it before jobs start disappearing silently.

## Firecrawl harness startup timeout

Default `HARNESS_STARTUP_TIMEOUT_MS=60000` (60s) is insufficient. The harness polls
for port 3002 only after all worker subprocesses have started, which can take >90s
depending on Postgres/RabbitMQ health check timing.

Set in `.env`:
```
HARNESS_STARTUP_TIMEOUT_MS=120000
```

Symptom: `Error: Port 3002 did not become available within 60000ms` in api container
logs even though all workers show as running.

## systemd service note

With `Type=oneshot` + `RemainAfterExit=yes`, `SubState=exited` is CORRECT and expected —
systemd ran the `podman-compose up -d` command which returned, containers are actually
running. Do not treat `exited` as a failure for this service type.
