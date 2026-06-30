# Vite runtime refresh from generated JSON

Use this pattern when a local dashboard already ships generated TypeScript data at build time, but one pane now needs live client-side refresh without rebuilding the whole app.

## Pattern
- Keep the generated TypeScript module for initial render (`src/generated/...ts`).
- Also emit the same payload to a public static JSON path (for example `public/data/live-data.json`) during the refresh script.
- Hydrate React state from the imported generated payload first, then refresh from the JSON endpoint on entry and on an interval.
- Scope the interval to the active tab/pane so background tabs do not keep polling.

## Implementation notes
- In the refresh script, write both artifacts from the same in-memory payload so schema drift cannot appear between TS and JSON outputs.
- In the client, prefer `new URL('/data/live-data.json?...', window.location.origin)` over a bare relative fetch when tests run under jsdom/Node fetch.
- In Vitest/jsdom, guard the live-refresh effect with `import.meta.env.MODE === 'test'` when the test is not explicitly stubbing that endpoint. This avoids noisy 404/fetch failures while preserving production behavior.
- Show the current payload timestamp plus a small refresh-status chip so the user can tell whether they are seeing a fresh fetch or the last successful payload.

## Verification
- Run the refresh script and confirm both the TS artifact and `public/data/*.json` were written.
- Run tests after adding the live-refresh effect; if jsdom fetches the endpoint unexpectedly, either stub it in the test or skip the effect in test mode.
- Build the app and confirm the production bundle still succeeds with the new JSON asset present.
