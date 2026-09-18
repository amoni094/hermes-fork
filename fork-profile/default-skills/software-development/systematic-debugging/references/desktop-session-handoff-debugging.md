# Desktop session handoff debugging

Use this when a Wayland compositor launched from GDM appears to black-screen, crash immediately, or lose portal/session services.

## Pattern
- Symptom: compositor session fails after login, often with sparse user-facing output.
- Hidden cause: previous desktop session shutdown overlaps the new session startup.
- Typical evidence:
  - `gdm-wayland-session` or the compositor wrapper aborts with a `std::system_error` / deadlock-style message.
  - `graphical-session.target` becomes inactive during startup.
  - `xdg-desktop-portal.service` fails with `result='dependency'`.

## Investigation steps
1. Pull both current and previous boot journals around the login/logout timestamps.
2. Inspect user-session unit state and failed units.
3. Read compositor startup config before editing it.
4. Map ordering between:
   - display manager session entry
   - compositor wrapper/start script
   - `graphical-session.target`
   - `xdg-desktop-portal.service`
   - desktop-specific portal backend
5. Distinguish:
   - compositor crash
   - portal dependency race
   - previous-session shutdown overlap

## Fix pattern
- Do not force-start `xdg-desktop-portal.service` early from compositor `exec-once`/startup hooks when logs show `graphical-session.target` inactive.
- If needed, add only the smallest session-target/environment bootstrap needed for plain sessions.
- Re-test from a clean reboot directly into the target session, not after first entering another desktop.

## Why this matters
Portal failures can be secondary symptoms. Forcing them earlier may make the race worse instead of fixing it.
