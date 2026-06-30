# rpm-ostree stale cached-update diagnosis

Use when:
- `rpm-ostree status` shows `AvailableUpdate`
- but `rpm-ostree upgrade` returns `No upgrade available.`

## Fast rule
Prefer `rpm-ostree status --json` over the human-readable banner.

Check these fields:
- booted deployment `checksum`
- `cached-update.update-sha256`
- `cached-update.ref-has-new-commit`
- `cached-update.rpm-diff`

Interpretation:
- If `cached-update.update-sha256` equals the booted deployment checksum, the cached record points at the current deployment.
- If `cached-update.ref-has-new-commit` is `false`, there is no newer base commit waiting.
- In that state, `cached-update.rpm-diff` may still advertise package upgrades. Treat that as stale cached metadata rather than a real pending deployment.

## Session pattern captured
Observed state:
- `rpm-ostree upgrade --check` and `rpm-ostree status` reported `Diff: 2 upgraded`
- `rpm-ostree upgrade` reported `No upgrade available.`
- `rpm-ostree status --json` showed:
  - booted checksum = `fccd698dc240bd1a72d79e1c3f9187284a9ef306d328bfed9eaf41e54a4c0b3b`
  - `cached-update.update-sha256` = same checksum
  - `cached-update.ref-has-new-commit` = `false`
  - stale diff entries for `nwg-bar` and `nwg-panel`

Conclusion:
- host was already current
- the remaining `AvailableUpdate` banner was harmless stale cache state

## Cleanup attempts
These may be worth trying but are not guaranteed to clear the banner:
- `rpm-ostree cleanup -m`
- `rpm-ostree cleanup -p`
- `rpm-ostree cleanup -b`

If the JSON confirms no real new commit and the actual upgrade path says none is available, report the system as current.

## User guidance
Recommended next step:
- reboot once
- re-run `rpm-ostree status`

Phrase the result clearly:
- not "update applied"
- not "update failed"
- but "system is up to date; status banner is stale cached metadata"
