# Compression trigger checklist

Use `/compress` or explicitly recommend it at these boundaries:
- after large `session_search` results
- after broad repo-wide `search_files` sweeps
- after multi-file patch or docs maintenance passes
- before switching task families after heavy tool use
- whenever the user explicitly flags context pressure

If `/compress` is not invokable from the active tool surface:
- say so briefly
- recommend `/compress`
- continue on the lowest-context path available
