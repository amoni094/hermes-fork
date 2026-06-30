# Firecrawl user-systemd durability pattern

Use this when the local Firecrawl self-host works manually but is down after reboots/logouts or keeps disappearing between sessions.

## Symptom pattern
- `web_extract` or other Firecrawl-backed retrieval fails with `127.0.0.1:3002 connection refused`
- The self-host directory and compose file exist, but the containers are stopped
- Manual `podman-compose up -d` restores service

## Durable fix
Create a user service that starts the stack from the self-host directory and survives across sessions.

Example unit:
```ini
[Unit]
Description=Firecrawl self-host stack (Podman Compose)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/var/home/rainbow/firecrawl-selfhost
RemainAfterExit=yes
ExecStart=/var/home/rainbow/.local/bin/podman-compose up -d
ExecStop=/var/home/rainbow/.local/bin/podman-compose down
TimeoutStartSec=180
TimeoutStopSec=120

[Install]
WantedBy=default.target
```

## Important pitfall
Do not assume `podman compose` will work inside a user systemd unit just because it worked interactively in a shell. The unit PATH may not expose the compose provider. If systemd reports errors like:
- `looking up compose provider failed`
- `docker-compose: executable file not found in $PATH`
- `podman-compose: executable file not found in $PATH`

then use the explicit working binary path in `ExecStart` / `ExecStop` instead.

## Activation
```bash
systemctl --user daemon-reload
systemctl --user enable --now firecrawl.service
```

## Verification
```bash
systemctl --user is-enabled firecrawl.service
systemctl --user is-active firecrawl.service
curl -sS http://127.0.0.1:3002/
podman ps --format '{{.Names}}|{{.Status}}' | grep '^firecrawl_'
```

## Interpretation
- If root responds and a known-good scrape like `https://example.com` succeeds, the stack is healthy.
- If a specific site still fails after that, treat it as target-site blocking or compatibility, not a Firecrawl outage.
