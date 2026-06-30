# Hermes bootstrap usage for Superpowers

Recommended entrypoints:

- `hermes -s superpowers-bootstrap`
- in an active CLI session: `/skill superpowers-bootstrap`
- optionally follow with `/skill using-superpowers` if you want the core workflow body visible immediately

Why this exists:

Upstream Superpowers ports rely on harness-level automatic session-start injection. In Hermes, a plain installed skill is discoverable but not automatically injected into every new session by installation alone. This bootstrap skill is the honest local equivalent.

Suggested habit:

For coding-heavy sessions, preload `superpowers-bootstrap` once at session start and let it route you into `using-superpowers` and the rest of the workflow.
