# bash-language-server V8 OOM crash investigation -- Sep 2026

## System
- OS: Fedora Silverblue 44, kernel 7.1.12
- Node: 22.23.1 (nodejs22 RPM)
- Process: bash-language-server 5.6.0 (latest at time of investigation)
- Launcher: Hermes LSP via ~/.hermes/lsp/bin/bash-language-server start

## Crash history
- 14 crashes over 3 weeks (Aug 11 - Sep 1 2026)
- Daily or 2-3x/day
- RSS at crash: 236-407 MB (healthy baseline: ~50-100 MB)
- Signal: SIGABRT (V8 self-abort, not kernel OOM kill)

## Confirmed stack trace (coredump PID 440788)
```
#0  __pthread_kill_implementation (libc.so.6)
#1  raise (libc.so.6)
#2  abort (libc.so.6)
#3  _ZN4node15OOMErrorHandlerE (libnode.so.127)
#4  _ZN2v85Utils16ReportOOMFailureE
#5  _ZN2v88internal2V823FatalProcessOutOfMemoryE
#6  _ZN2v88internal4Heap23FatalProcessOutOfMemoryEPKc
#7  _ZN2v88internal4Heap36ReportIneffectiveMarkCompactIfNeededEv
#8  CollectGarbage (libnode.so.127)
```

## Root cause
bash-language-server uses web-tree-sitter (WASM) to parse bash files.
The WASM runtime accumulates parsed AST nodes without releasing them on document close.
Heap grows unbounded until V8 GC becomes ineffective and calls abort().
Known upstream issue; no fix in 5.6.0 (latest as of Sep 2026).

## Hermes LSP internals caveat

agent/lsp/manager.py stores `command` list as binary_overrides[name].
_resolve_override() in servers.py returns only override[0]:
```python
def _resolve_override(ctx, server_id):
    override = ctx.binary_overrides.get(server_id)
    if override and override[0] and os.path.exists(override[0]):
        return override[0]   # first element only -- rest of list is dropped
    return None
```
Then _spawn_bash_ls builds [bin_path, "start"] = [wrapper, "start"].
Wrapper receives `start` via $@ and passes to node. Correct.

`hermes config set 'lsp.servers.bash-language-server.env.NODE_OPTIONS' ...` does not parse
nested dot paths via CLI (Sep 2026). Wrapper is the working approach.

## Fix applied

~/.hermes/lsp/bin/bash-language-server-wrapped:
```bash
#!/bin/bash
export NODE_OPTIONS="--max-old-space-size=200"
exec node /var/home/rainbow/.hermes/lsp/node_modules/bash-language-server/out/cli.js "$@"
```

~/.hermes/config.yaml section (written via hermes config set):
```yaml
lsp:
  servers:
    bash-language-server:
      command:
        - /var/home/rainbow/.hermes/lsp/bin/bash-language-server-wrapped
        - start
```

## Verify fix is live
```bash
hermes config get lsp  # command should show wrapper path
~/.hermes/lsp/bin/bash-language-server-wrapped --version  # should print 5.6.0
hermes lsp status  # ready; no active clients until file opened
```
