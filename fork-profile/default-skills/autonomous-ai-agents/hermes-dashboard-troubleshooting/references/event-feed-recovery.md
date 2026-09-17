# Event-feed recovery for Hermes dashboard chat sidebar

Symptom:
- Dashboard sessions/chat UI reports: `events feed disconnected — tool calls may not appear`.

Fast recovery path:
1. In `web/`, run `npm install`.
2. Build assets with `npm run build`.
3. Restart the dashboard with `hermes dashboard --no-open --skip-build`.
4. Confirm `127.0.0.1:9119` is listening.
5. Load the dashboard and check the Chat page.
6. If needed, verify the transport directly with a websocket round-trip.

Why this works:
- The dashboard frontend is built separately from the Python backend.
- The chat sidebar's tool list depends on websocket rebroadcasting, not just page load.
- A successful manual build followed by `--skip-build` isolates runtime verification from frontend build problems.

Transport under test:
- publisher: `/api/pub?channel=<id>`
- subscriber: `/api/events?channel=<id>`
- expected frame shape:

```json
{"method":"event","params":{"type":"tool.start","payload":{"tool_id":"abc123","name":"terminal","context":"date"}}}
```

Success condition:
- The subscriber receives the same JSON frame that the publisher sent.

Interpretation:
- If the round-trip succeeds, the event-feed transport is healthy and remaining issues are likely in session state, UI timing, or an idle/non-running PTY child rather than the rebroadcast path itself.
