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

`/v1/health` returned 404 on the tested image, so do not assume that endpoint exists. Prefer root endpoint + one real scrape/job as verification.
