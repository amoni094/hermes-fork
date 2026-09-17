# System Update Script: Known Partial Failure Patterns

The daily update script exits 1 if any step fails, but continues with remaining
steps. Non-zero exit does NOT mean the run was catastrophic — read per-step log
lines to determine actual outcome.

## Flatpak delta CDN failures (flathub)

Symptom: user flatpak update fails after 2 retries with:
  - `[56] Failure when receiving data from the peer`
  - `[35] SSL connect error`
  - URL pattern: `dl.flathub.org/repo/deltas/<hash>/0`

Cause: flathub delta CDN is occasionally flaky. The failure is transient and
not caused by local network issues (network connectivity check passes both before
and after the error).

Effect: the target app (e.g. Chromium ~171 MB) is NOT updated. Other steps
(system flatpak, toolbox DNF, firmware, managed repos) continue and may succeed.
The script exits 1 for the partial failure.

Fix: no investigation needed. Tell the user to run `flatpak update` manually
when convenient — the CDN usually recovers within minutes to hours. Do not
retry immediately within the same script invocation.

Observed: 2026-08-30, Chromium update (171 MB), failed all 3 script attempts
with alternating SSL/connection errors despite confirmed network availability.

## Git ref locking errors (see SKILL.md pitfalls section)

See the 'Git ref locking errors on fetch' pitfall in the main SKILL.md for the
`cannot lock ref` pattern and `git remote prune origin` remediation.

## Reboot notification service already loaded

`Failed to start transient service unit: Unit reboot-required-notify.service
was already loaded or has a fragment file.`

Benign. Means a prior run already queued the desktop reboot notification. The
reboot IS required; the notification was simply already sent. Do not treat as
a failure — report the reboot requirement normally.

## rpm-ostree transaction conflict (GNOME Software)

`Transaction in progress: upgrade (check only)` — initiated by gnome-software.service
when `AutomaticUpdates: stage` is on. Canceling and retrying immediately often
fails because GNOME Software grabs a new check-only transaction within ~1s.

Fix: poll `rpm-ostree status` until `State:` is not `busy`, then re-run the
daily script immediately. Trust the script's own checksum comparison over any
`AvailableUpdate: Diff: N upgraded` shown during the check-only transaction.
