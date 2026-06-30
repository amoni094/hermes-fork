# Port separation: Hermes dashboard vs sidecar local apps

Use when a user remembers an older dashboard/web app port and thinks Hermes moved or went down.

Observed durable pattern:
- Hermes dashboard is often managed by a user systemd unit with an explicit `ExecStart=... --port <n>`.
- A different local app may have been started ad hoc with `python3 app.py` on another port.
- When that standalone process dies, the old port disappears even though Hermes is healthy on its pinned port.

Recovery/diagnosis steps:
1. Inspect the Hermes user unit and read the exact `ExecStart` port.
2. Check active listeners for both the remembered port and the current service port.
3. Search user systemd units for the old port/app name.
4. If the old port is free and no unit references it, look for a standalone app path from recent logs/session history.
5. If both apps should coexist, keep Hermes on its configured port and start the sidecar app separately.
6. Verify both listeners with `ss` and a real HTTP request, not just process presence.

User-facing explanation pattern:
- "Hermes did not move randomly; 9119 is the pinned systemd-managed dashboard port. 8765 belonged to a separate local app that was not persistent."
- "It can stay open too, but if it is only a background Python process it will not survive reboot/logout unless you make it a user service."

Durable recommendation:
- Distinguish service-managed dashboard ports from ad hoc app ports before changing Hermes config.
- When the user wants both, prefer separate stable ports and make the sidecar app persistent with its own user systemd unit.