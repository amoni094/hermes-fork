# rmdir-via-SSH Incident (Sep 3 2026)

## What happened

Attempted to delete three legacy Windows upgrade folders:
- C:\$GetCurrent
- C:\$SysReset
- C:\OneDriveTemp

Command used:
```bash
ssh admin@100.88.247.70 "rmdir /s /q C:\\$GetCurrent 2>&1 & rmdir /s /q C:\\$SysReset 2>&1 & rmdir /s /q C:\\OneDriveTemp 2>&1 & echo Done"
```

## Root cause

Bash on the local Linux host expanded `$GetCurrent` and `$SysReset` as shell variables
(both undefined, expanding to empty string). The actual commands sent to Windows were:

```
rmdir /s /q C:\ 2>&1
rmdir /s /q C:\ 2>&1
rmdir /s /q C:\OneDriveTemp 2>&1
```

Windows executed `rmdir /s /q C:\` for the first two — silently attempting to delete
everything on C:\. Most system files were locked and returned "access denied", but
unlocked application folders were wiped:
- C:\Program Files\Proton\VPN\v5.1.7\ — completely emptied (all files deleted)
- C:\Program Files\Mozilla Firefox\ — partially emptied (xpcom.dll and other core DLLs deleted)

## Symptoms observed
- ProtonVPN shortcuts linked to nothing (executable deleted)
- Firefox crashed with "couldn't load xpcom" (xpcom.dll deleted)
- SSH connection dropping/resetting (cleanmgr was also running at the time, compounding issues)

## Recovery
- ProtonVPN: reinstalled from protonvpn.com/download/windows (settings preserved)
- Firefox: reinstalled from mozilla.org (bookmarks and profile preserved)
- OpenSSH, Tailscale, MSI Afterburner, NVIDIA driver: confirmed intact

## Prevention
See the main skill body — never pass `$`-prefixed folder names inline via SSH.
Use scheduled tasks or scp'd batch/PS files instead.
