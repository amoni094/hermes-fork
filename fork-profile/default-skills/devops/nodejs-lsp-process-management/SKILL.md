---
name: nodejs-lsp-process-management
triggers:
  - A Node.js LSP server is crashing with SIGABRT
  - Node process RSS is growing unbounded and eventually aborts
  - bash-language-server or yaml-language-server crashes repeatedly
  - V8 FatalProcessOutOfMemory appears in coredump stack trace
  - Node-based process needs a heap cap or memory containment
description: "Use when Node LSP crashes with SIGABRT; cap V8 heap."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [nodejs, lsp, memory-leak, v8, oom, bash-language-server]
    related_skills: [systematic-debugging]
related_skills:
  - systematic-debugging
---

# Node.js LSP Process Management

Use when a Node-based LSP server or long-lived Node process crashes repeatedly with SIGABRT and large RSS.

## Why LSP servers crash this way

Long-lived Node processes that parse document trees (tree-sitter, TypeScript compiler, YAML schema validator) accumulate objects in the V8 heap without releasing them across document open/close cycles. Over hours, RSS grows from ~50-100 MB to 350-450 MB. When V8 runs multiple full GC cycles without reclaiming enough space, it calls `abort()` via `FatalProcessOutOfMemory`. This produces a SIGABRT with no useful error message.

## Diagnosis

```bash
# List recent Node coredumps
coredumpctl list | grep node | tail -20

# Confirm the process and RSS at crash
coredumpctl info <PID> | grep -E "Command Line|Signal|Message"

# Check stack trace for V8 OOM signature
coredumpctl info <PID> | grep -A 40 "Stack trace" | grep -E "OOMError|FatalProcess|IneffectiveMark"
```

V8 OOM signature (all three must appear):
```
_ZN4node15OOMErrorHandlerE
_ZN2v88internal2V823FatalProcessOutOfMemoryE
_ZN2v88internal4Heap36ReportIneffectiveMarkCompactIfNeededEv
```

Regular interval + consistent RSS = deterministic leak, not a one-off.

Check if upgrade fixes it first:
```bash
npm show bash-language-server versions --json | python3 -c \
  "import json,sys; vs=json.load(sys.stdin); print('latest:', vs[-3:])"
```

If already on latest: the leak is in a tree-sitter dependency, not fixable by upgrade.

## Fix: V8 heap cap wrapper

Capping the heap makes V8 exit cleanly instead of aborting. The launcher restarts on next use.

### Create wrapper script

```bash
# Find the real entry point first
readlink -f ~/.hermes/lsp/node_modules/.bin/bash-language-server
# e.g. -> ~/.hermes/lsp/node_modules/bash-language-server/out/cli.js

cat > ~/.hermes/lsp/bin/bash-language-server-wrapped << 'EOF'
#!/bin/bash
# 384MB cap: enough headroom for normal operation + large-file parse bursts,
# but forces clean GC exit before reaching the ~400MB tree-sitter leak threshold.
# Do NOT use 200MB -- too low, kills the server during legitimate large-file parses.
export NODE_OPTIONS="--max-old-space-size=384"
exec node /var/home/rainbow/.hermes/lsp/node_modules/bash-language-server/out/cli.js "$@"
EOF
chmod +x ~/.hermes/lsp/bin/bash-language-server-wrapped
```

### Configure Hermes LSP to use the wrapper

```bash
hermes config set 'lsp.servers.bash-language-server.command' \
  '["/var/home/rainbow/.hermes/lsp/bin/bash-language-server-wrapped", "start"]'
hermes lsp stop
hermes config get lsp   # verify
```

## Heap cap sizing

| Process | Healthy RSS | Suggested cap |
|---|---|---|
| bash-language-server | 50-100 MB | 384 MB |
| yaml-language-server | 80-150 MB | 250 MB |
| typescript-language-server | 200-400 MB | 600 MB |
| pyright | 100-300 MB | 500 MB |

Rule: cap = ~2-3x healthy RSS, well below observed crash threshold.

## Pitfalls

### Hermes LSP binary_overrides only uses command[0]

Hermes `agent/lsp/servers.py::_resolve_override()` returns only `override[0]` from the command list.
The spawn function builds `[bin_path, "start"]`.

So `command: ["node", "--max-old-space-size=200", "cli.js"]` silently becomes `["node", "start"]`.
Always use a wrapper script as command[0], not `node` with inline flags.

### Hermes config set does not handle nested env keys

`hermes config set 'lsp.servers.<name>.env.NODE_OPTIONS' ...` does not parse nested dot paths
correctly as of Sep 2026. Use the wrapper script approach instead.

### SIGABRT vs SIGSEGV vs kernel OOM

- SIGABRT + V8 OOM stack = this skill (heap cap)
- SIGSEGV = actual crash in C++ extension, different diagnosis
- SIGKILL from systemd-oomd = system RAM pressure, different fix

### Do not set NODE_OPTIONS globally

Setting NODE_OPTIONS in the shell profile applies to every Node process. Use per-server wrappers.

## Verification

1. Trigger a file open (starts the LSP)
2. Confirm no new SIGABRT: `coredumpctl list | grep node`
3. Coredump storage stops growing: `du -sh /var/lib/systemd/coredump/`

See `references/node-v8-oom-lsp-crash.md` for the bash-language-server investigation detail.
