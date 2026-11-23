---
name: channel-fracture-cron
description: Use when cron memory writes look successful. Verify receiver-side, not writer-side.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
triggers:
  - cron job wrote memory but target agent does not see it
  - channel fracture
  - skip_memory=True cron isolation
  - cross-profile skill routing failed
  - silent delivery / fail-plausible cron
  - NOT for designing a new cron schedule (use hermes-cron-and-agents)
metadata:
  hermes:
    tags: [cron, reliability, memory, multi-agent, verification]
    related_skills: [hermes-cron-and-agents, stalled-session-recovery, hermes-gateway-lifecycle-guard, verification-before-completion]
---

# Channel Fracture (Cron / Cross-Agent Delivery)

Source: arXiv:2606.04896 — Channel Fracture (production Hermes deployment).

## Failure mode

Information routed across agent boundaries is silently blocked. Writer-side checks pass; only receiver-side inspection shows the miss.

Documented Hermes instances:

1. Cron memory injection blocked by skip_memory=True / memory-tool not registered.
2. Cross-profile skill routing fractured by recursive directory traversal.
3. WebSocket delivery confirmation fallback causing duplication.

## Rules

1. Inverse verification. After any cron or cross-profile write, read the target store (the receiving profile's memory/session), not the writer log.
2. Channel matching. The write path must be the path the receiver actually reads (same profile, same DB, memory toolset enabled, gateway restarted after config).
3. A cron exit code 0 is not proof of delivery. Treat fail-plausible reports as untrusted (arXiv:2606.14589).

## Procedure

```bash
python3 ~/.hermes/scripts/channel-fracture-verify.py --target <profile>
```

Check:

- Target profile HERMES_HOME / HERMES_PROFILE paths
- Whether cron sessions set skip_memory=True
- Whether memory / fact-store tools are in the cron enabled toolsets
- Receiver-side row count or mtime actually changed

## Pitfalls

- Writer-side "I stored the fact" with no receiver read-back.
- Config change without gateway restart so memory manager stays None and the tool never registers.
- Cross-profile writes into the wrong profiles/<name>/ tree.

## Verification

- [ ] Receiver-side evidence (query or file mtime) recorded in the job output
- [ ] Cron job does not claim success from writer logs alone
