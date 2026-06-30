---
name: rootless-podman-compose-adaptation
description: Adapt Docker Compose self-host projects to rootless Podman on Fedora Atomic or similar Linux systems, with verification-first startup and container-specific compatibility fixes.
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

# Support files

- `references/firecrawl-selfhost.md` — concrete Firecrawl notes from a successful Podman adaptation, including the RabbitMQ and readiness fixes.
