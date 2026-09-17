# Flatpak Transient Update Errors (Silverblue / Atomic)

Observed during system update runs. These are non-blocking patterns — document
them so they're not misread as failures requiring intervention.

## Chromium user Flatpak: SSL/CDN fetch failure

Error pattern (curl 56 or 35):
```
Error: While pulling app/org.chromium.Chromium/x86_64/stable from remote flathub:
While fetching https://dl.flathub.org/repo/objects/<sha>.filez: [56] Failure when
receiving data from the peer
```
or:
```
[35] SSL connect error
```

- Cause: transient CDN/TLS issue on Flathub delivery servers. Network is up (ping
  passes); it's a server-side blip on a specific object.
- Behavior: persists across retries in the same session (the `.filez` object hash
  doesn't change between attempts).
- Resolution: self-resolves by next daily run. No manual intervention needed.
- How to report: "Chromium not updated this run — transient Flathub SSL error.
  Will retry automatically tomorrow."
- Observed: 2026-08-14 (3 consecutive retry failures, curl 56 then 35).

## System Flatpak: "No such ref" bulk warnings

Error pattern:
```
F: Warning: Treating remote fetch error as non-fatal since <ref> is already installed:
No such ref 'runtime/org.gnome.Platform/x86_64/50' in remote flathub
```

- These appear in bulk at the start of a system flatpak update.
- Cause: remote catalog refresh timing or refs renamed/retired upstream; the
  locally installed versions remain valid.
- All are marked non-fatal by flatpak — update continues.
- The actual app updates (Thunderbird, Obsidian, Telegram, Firefox) proceed after
  this block and succeed on retry 1 if they hit an SSL error on the first attempt.
- How to report: ignore these in the summary. Only report actual app-level
  update success/failure.
- Observed: 2026-08-14 (25+ warnings, all non-fatal; system apps updated on retry 1).

## Reboot notification: "already loaded" error

```
Failed to start transient service unit: Unit reboot-required-notify.service was
already loaded or has a fragment file.
```

- Benign. A prior run already queued the notification. Reboot IS required.
- The script exits non-zero because of this, but the reboot requirement is real.
- Report: reboot required, notification already sent earlier.
