# Toolbox-backed CLI runtime wrappers on Fedora Atomic

Use when an upstream CLI/TUI app is locally useful but expects a heavyweight runtime you do not want to layer onto the host.

Condensed pattern
- Create a dedicated Toolbox container for the app.
- Install the runtime/toolchain in the container.
- Build or install the app in a stable location.
- Expose tiny host wrappers in `~/.local/bin/` that `podman exec` into the container.
- Preserve `PWD` and pass UTF-8 locale/env vars through the wrapper when needed.
- Verify both the wrapped command and the downstream integration that probes for companion binaries.

Hermes-specific note
- In non-interactive Hermes shells, `toolbox run` can be good for one-off probes but is not the best steady-state wrapper path.
- If `toolbox run` throws GLib/GIO assertion failures or other session-init errors, switch to direct `podman exec` wrappers into the named Toolbox container.
- For interactive commands such as `tmux`, request `-it` only when stdin/stdout are real TTYs; otherwise fall back to plain `podman exec`.

Why this mattered
- A Toolbox-installed runtime was sufficient for real local use even though the host remained immutable.
- `toolbox run` was not the best steady-state wrapper path for repeated host invocation from Hermes; `podman exec` gave a cleaner bridge.
- Companion shims may be needed when integrations probe for runtime helpers (`escript`, `erl`) rather than only the top-level app binary.

Minimal non-interactive wrapper shape
```bash
#!/usr/bin/env bash
set -euo pipefail
container="fedora-toolbox-44"
workdir="${PWD:-$HOME}"
exec podman exec -w "$workdir" "$container" <command> "$@"
```

TTY-aware wrapper shape
```bash
#!/usr/bin/env bash
set -euo pipefail
container="fedora-toolbox-44"
workdir="${PWD:-$HOME}"
if [ -t 0 ] && [ -t 1 ]; then
  exec podman exec -it -w "$workdir" "$container" <command> "$@"
else
  exec podman exec -w "$workdir" "$container" <command> "$@"
fi
```

Verification checklist
- `command -v <wrapped-command>` resolves on the host.
- The wrapped command returns a real status output, version probe, or detect output.
- Any dependent local plugin or doctor command now reports the toolchain as ready.
- If the app has a self-check (`--detect`, `--prompt`, headless JSON mode), run that too.

Pitfalls
- Fixing only the main binary and forgetting helper/runtime probes.
- Leaving locale warnings unresolved when the guest runtime expects UTF-8.
- Using a transient clone/build path instead of a stable local source/install location.
- Forcing `-it` unconditionally and breaking non-interactive callers.
