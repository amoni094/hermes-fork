# Runtime maintenance command patterns

Use these as patterns, not blind copy-paste.

## Preserve the current Hermes session before killing siblings

1. Print the current shell PID / PPID / SID.
2. Enumerate Hermes-related processes with enough context to separate:
   - the current Hermes parent
   - helper children of that parent
   - unrelated sibling sessions
   - user-service processes

A practical shape:
- current shell identity
- `ps -eo pid,ppid,sid,etimes,cmd | grep -i '[h]ermes'`

Key interpretation rule:
- preserve the current Hermes parent PID and its helper children
- do not kill qmd / stealth-browser / hindsight helpers that belong to the preserved parent

## Stop service-managed Hermes components explicitly

When user services are present, inspect:
- `systemctl --user --no-pager --type=service --all | grep -i hermes`

If the dashboard or gateway should go away, stop them by service name:
- `systemctl --user stop hermes-dashboard.service hermes-gateway.service`

Then verify both:
- remaining Hermes-related processes via `ps`
- resulting user-service states via `systemctl --user ...`

## Update pass on Fedora Atomic / Silverblue

Recommended order:
1. baseline versions and OS facts
2. `hermes update`
3. `hermes --version`
4. `rpm-ostree upgrade`
5. `flatpak update -y`
6. `rpm-ostree status`

## rpm-ostree verification rule

`rpm-ostree --check` and `rpm-ostree status` can advertise an `AvailableUpdate` even when the actual `rpm-ostree upgrade` run says `No upgrade available.`

Report this explicitly as a preview/status mismatch.
Do not claim that an OS update was applied unless the real `rpm-ostree upgrade` run did so.
