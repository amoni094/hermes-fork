---
name: silverblue-toolbox-wrapper-bootstrap
triggers:
  - A tool is installed only inside Toolbox and should behave like a host command
  - A Flatpak desktop app exists but lacks a convenient CLI launcher
  - Adding host-visible wrappers for toolbox-internal tools on Fedora Silverblue/Atomic
  - User wants a CLI shortcut for a Toolbox or Flatpak tool without broad host mutation
description: >
  Use when: Add host-visible wrappers and lightweight user-space tooling on Fedora Silverblue/Atomic without broad host mutation, preferring Podman/Toolbox bridges and real verification.
related_skills:
  - atomic-desktop-app-installation
  - silverblue-system-update-trigger
---

# When to use
Use when working on Fedora Silverblue or another Atomic desktop and you need common developer commands exposed on the host without layering large runtimes into the immutable base.

Typical triggers:
- a tool is installed only inside Toolbox and should behave like a host command
- a Flatpak desktop app exists but lacks a convenient CLI launcher
- a compatibility command like `docker` should resolve safely to an existing local runtime
- user-space package managers installed a binary outside `~/.local/bin`

# Goals
1. Prefer narrow user-space changes over rpm-ostree layering.
2. Make commands discoverable from the host shell.
3. Keep wrappers tiny, explicit, and inspectable.
4. Verify every claimed command with a real host-side invocation.

# Workflow
## 1) Inspect what already exists
Check before adding anything:
- whether the app/tool is already installed
- where the real binary lives
- whether a wrapper with the desired name already exists in `~/.local/bin`
- whether Toolbox access should target a stable named container

## 2) Prefer the narrowest exposure path
Use these patterns in order:
1. Native host binary already on PATH -> do nothing.
2. User-space binary outside `~/.local/bin` -> add a tiny wrapper in `~/.local/bin` that `exec`s the real path.
3. Flatpak GUI app -> add a wrapper that `exec flatpak run <app-id> "$@"`.
4. Toolbox-only CLI runtime -> add a wrapper that `podman exec` into the named Toolbox container.
5. Compatibility command -> add a wrapper only if the backing runtime is already present and the mapping is semantically close.

## 3) Toolbox wrapper pattern
Preferred wrapper shape:
- explicit container name
- preserve caller working directory with `-w "$PWD"`
- request `-it` only when stdin/stdout are real TTYs
- use plain `podman exec` in non-interactive Hermes shells

Example structure:
```bash
#!/usr/bin/env bash
set -euo pipefail
container="fedora-toolbox-44"
workdir="${PWD:-$HOME}"
if [ -t 0 ] && [ -t 1 ]; then
  exec podman exec -it -w "$workdir" "$container" <cmd> "$@"
else
  exec podman exec -w "$workdir" "$container" <cmd> "$@"
fi
```

## 4) Avoid `toolbox run` as the steady-state wrapper in Hermes
In non-interactive Hermes shells on Silverblue, `toolbox run` can fail with GLib/GIO session-init assertions.
Treat it as a probe only.
If it is unstable, switch to direct `podman exec` wrappers into the Toolbox container.

## 5) Flatpak launcher pattern
For a locally installed desktop app such as VS Code:
```bash
#!/usr/bin/env bash
set -euo pipefail
exec flatpak run com.visualstudio.code "$@"
```
Use `--version` or another non-GUI probe for verification when possible.

## 6) Compatibility shim pattern
For Docker-compatible local workflows where Podman is already the intended runtime:
```bash
#!/usr/bin/env bash
set -euo pipefail
exec podman "$@"
```
Only do this when the user explicitly wants the shim or when the local environment already treats Podman as the Docker replacement.
Verify both `docker --version` and any high-value subcommand such as `docker compose version`.

## 7) Normalize user-space tool visibility
If npm or another user-space manager installs tools into a custom prefix such as `~/.npm-global/bin`, add a wrapper in `~/.local/bin` so the command is reachable from a consistent launcher directory.

## 8) Verification requirements
Before claiming success:
1. chmod the wrapper executable.
2. read back the wrapper contents.
3. invoke the wrapper from the host.
4. prefer low-side-effect proof commands:
   - `code --version`
   - `docker --version`
   - `docker compose version`
   - `tmux -V`
   - `go version`
   - `pnpm --version`
5. if a command fails, fix pathing or runtime assumptions before finishing.

# Reporting
State:
- what already existed
- what wrappers were added
- where each wrapper lives
- the exact verification outputs
- any semantic caveats, such as `docker` being a Podman shim

# Pitfalls
- assuming an installed binary is on PATH when it lives in a custom prefix
- using `toolbox run` wrappers in Hermes after GLib/GIO failures appear
- creating wrappers without preserving working directory for Toolbox-backed CLIs
- requesting `-it` unconditionally and breaking non-interactive usage
- claiming a compatibility shim works without checking important subcommands like `compose`
