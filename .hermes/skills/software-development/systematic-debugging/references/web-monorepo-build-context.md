# Web monorepo build-context debugging

Use this when a web app fails through its launcher/wrapper but succeeds when run directly from a package directory.

## Pattern

Symptoms:
- Wrapper says `npm install failed` or `build failed`
- Manual `cd <package> && npm install && npm run build` succeeds
- Repo recently moved to npm workspaces / monorepo layout

## Root-cause checklist

1. Reproduce the wrapper path exactly.
2. Reproduce the direct package path exactly.
3. Compare working directories used by each path.
4. Check whether workspace-root install pulls unrelated packages/workspaces.
5. Check for native deps or postinstall hooks outside the target package.
6. If the target package builds locally, treat the launcher/build context as the primary suspect.

## Durable fix shape

- Prefer the narrowest install/build context that satisfies the target app.
- Keep workspace-root behavior only where explicitly required.
- If runtime chat/PTY pieces have a prebuilt artifact, consider a safe fallback to the prebuilt artifact rather than crashing the whole web UI.

## Verification

Do both:
- Process-level: confirm the server starts and listens on the expected port.
- Browser-level: load the page, navigate the relevant route, and check for JS errors.

## Example from a Hermes dashboard repair

A Hermes v0.16 dashboard/WebUI regression came from using workspace-root `npm install` during startup after a move to npm workspaces. The actual `web/` package could still install and build successfully on its own. Narrowing the install context to `web/` fixed startup; adding a fallback to a prebuilt embedded-chat entrypoint prevented websocket/chat initialization from crashing the whole UI when the broader TUI npm path failed.
