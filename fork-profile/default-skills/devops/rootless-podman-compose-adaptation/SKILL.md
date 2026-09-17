---
name: rootless-podman-compose-adaptation
triggers:
  - Docker is unavailable or undesirable, but podman is available on a Fedora system
  - A project documents 'docker compose up' and the same stack is needed locally with podman
  - Adapting a Docker Compose self-host project to rootless Podman on Fedora Atomic
  - Podman compose is failing or behaving differently from Docker and needs adaptation
description: >
  Use when adapting Docker Compose self-host projects to rootless Podman on Fedora Atomic or similar Linux systems, with verification-first startup and container-specific compatibility fixes.
related_skills:
  - hermes-agent
  - atomic-desktop-app-installation
---

# When to use

Use this when a repo ships a Docker Compose workflow but the local machine is running rootless Podman (especially Fedora Silverblue/Atomic) and you need a working local deployment rather than a Docker-only recipe.

Typical triggers:
- `docker` is unavailable or undesirable, but `podman` is available.
- A project documents `docker compose up` and you need the same stack locally.
- A self-hosted app fails under rootless containers due to permissions, startup order, or image assumptions.

# Goal

Get the service actually running under Podman with small, verifiable changes. Prefer an overlay deployment directory and adapter compose file over editing the upstream repo unless the user explicitly wants repo changes.

# Workflow

1. Inspect the upstream compose and self-host docs first.
   - Identify required services, ports, env vars, health dependencies, and whether the app expects helper containers to exist before boot.
   - Look for queue backends, databases, browser workers, and admin UIs.

2. Check local runtime/tooling.
   - Confirm `podman` works.
   - If compose support is missing, install `podman-compose` in user space rather than assuming Docker.
   - On Atomic systems, prefer user-space installs (for example `uv tool install podman-compose`) over OS mutation.

3. Create an adaptation directory outside the cloned repo when possible.
   - Put the local compose file and `.env` there.
   - Keep the upstream clone readable and easy to diff against later.

4. Translate images and compose assumptions carefully.
   - Expand short Docker Hub image names to fully qualified references when Podman short-name resolution may block unattended pulls.
   - Prefer published images over local builds when the goal is quick local bring-up.
   - Keep ports minimal; expose only the app port unless the user asks for admin UIs.

5. Add explicit readiness gates.
   - If the API depends on RabbitMQ/PostgreSQL/Redis or similar, add `healthcheck`s and `depends_on` conditions where compose semantics support them.
   - Databases often need a real readiness check (`pg_isready`), not just container start.
   - Queue or worker-heavy apps commonly fail fast if infra is only “started” but not “ready”.

6. Expect rootless Podman incompatibilities and fix the container, not the whole machine.
   - Prefer per-service workarounds in compose.
   - Keep fixes scoped and reversible.

7. Verify with real HTTP/API calls, not container state alone.
   - First prove containers are up.
   - Then hit the service root or documented info endpoint.
   - Then run one real workload (scrape, API request, job enqueue, etc.).

# Pitfalls

## RabbitMQ 4.x: env vars removed (hard failure since 4.0)

RabbitMQ 4.x exits with code 1 if any `RABBITMQ_VM_MEMORY_*` env vars are set.
Switch to a mounted config file. See `references/firecrawl-selfhost.md` for the full recipe.
Diagnostic: `podman logs <rabbitmq>` shows the rejected var just before exit.

## Redis eviction policy: must be `noeviction` for BullMQ queues

`volatile-lru` silently evicts BullMQ jobs without TTLs. Always set
`--maxmemory-policy noeviction`. Firecrawl logs `IMPORTANT! Eviction policy is volatile-lru`
as a warning — that IS the problem. Fix it.

## RabbitMQ under rootless Podman

The official RabbitMQ management image can fail under rootless Podman with `.erlang.cookie` permission errors. A durable workaround is to run the service as the rabbitmq UID/GID already expected inside the image:

- `image: docker.io/library/rabbitmq:4-management`
- `user: "999:999"`

Also give RabbitMQ a real healthcheck, e.g. `rabbitmq-diagnostics -q ping`, and make dependent services wait for health rather than raw container start.

Do not save the lesson as “RabbitMQ is broken on Podman.” The durable lesson is the compose-level compatibility fix.

## Short-name pulls under Podman

Short names like `redis:alpine` may fail in unattended contexts because Podman can require TTY-based short-name resolution. Use fully qualified names such as:
- `docker.io/library/redis:alpine`
- `docker.io/library/rabbitmq:4-management`

## Fast-failing API harnesses

Some app harnesses spawn many workers and abort if a dependent queue or database is not reachable immediately. If the main container exits quickly with connection-refused errors, check infra readiness and `depends_on`/healthchecks before changing app code.

# Verification checklist

- `podman ps` shows all required services up.
- Queue/database containers are healthy where healthchecks were added.
- The main app answers on the expected port.
- A real user-level API action succeeds, not just `/` returning 200.
- Logs show workers connected to Redis/queue/database without crash loops.

# Deliverables

Prefer to leave:
- an adaptation directory with `docker-compose.yaml` and `.env`
- exact start/stop/test commands
- one reference note under `references/` for project-specific quirks discovered during bring-up

## Updating a source-build compose project (firecrawl pattern)

Some projects ship a `docker-compose.yaml` with `build:` directives (builds from local source) instead of pre-pulled `image:` references. Running `podman-compose up -d` on these triggers a full compilation (Rust + Node, 10+ minutes). Do NOT run compose directly for routine updates.

**Correct update pattern when compose builds from source:**

1. `cd ~/src/<project> && git pull`
2. Identify the `build:` line (e.g. `build: apps/api`) and the commented-out `image:` alternative above it in the compose file
3. Temporarily swap: `cp docker-compose.yaml docker-compose.yaml.bak && sed -i 's|build: apps/api|image: ghcr.io/firecrawl/firecrawl:latest|' docker-compose.yaml`
4. Restart: `podman-compose up -d --no-recreate api`
5. Restore original: `mv docker-compose.yaml.bak docker-compose.yaml`
6. Verify: `podman ps --filter name=<project>_api_1` then `curl -s -o /dev/null -w '%{http_code}' http://localhost:3002/v1/scrape` => 404 = healthy (endpoint needs POST body; connection refused = actually down)

**Pitfall:** `podman-compose up -d` on a source-build compose file triggers compilation, not image pull. Always detect `build:` in the compose file before running a routine update.

**Pitfall:** 404 on `POST /v1/scrape` with no body is correct/healthy. Don't mistake this for a container failure.

## Firecrawl self-host on rootless Podman (verified pattern)

Layout: clone at `~/src/firecrawl`, adaptation at `~/firecrawl-selfhost`, runner at `~/.local/bin/podman-compose`.

Key adaptations:
1. Use fully-qualified image names: `docker.io/library/redis:alpine`, `docker.io/library/rabbitmq:4-management`
2. RabbitMQ rootless fix: `user: "999:999"`, healthcheck: `rabbitmq-diagnostics -q ping`
3. API dependency ordering: wait for RabbitMQ `service_healthy` AND PostgreSQL `service_healthy`
4. PostgreSQL healthcheck: `pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres}`
5. Queue URL needs credentials: `NUQ_RABBITMQ_URL=amqp://guest:***@rabbitmq:5672`

Verification sequence:
1. `podman ps` — all `firecrawl_*` containers up
2. `GET /` on port 3002 — returns Firecrawl API JSON banner
3. `POST /v1/scrape` with `https://example.com` — returns markdown

Pitfall: `/v1/health` returns 404 on the tested image. Use root endpoint + one real scrape as verification instead.

# Support files

- `references/firecrawl-selfhost.md` — concrete Firecrawl notes from a successful Podman adaptation, including the RabbitMQ and readiness fixes.
