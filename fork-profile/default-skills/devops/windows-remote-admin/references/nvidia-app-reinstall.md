# NVIDIA App reinstall after rmdir damage (DESKTOP-PH4F2DK)

This-machine procedure. Resolve the installer version from the registry; do not hardcode a CDN version.

NVIDIA App uses the same ghost-folder pattern as ProtonVPN after `rmdir` damage:
folder structure exists but files are empty (0 bytes).

```bash
ssh admin@host "dir \"C:\\Program Files\\NVIDIA Corporation\\NVIDIA app\" 2>&1"
# Damaged: shows subdirs (CEF, NvBackend, NvCpl, ShadowPlay...) but 0 files
```

1. Get version from registry (even if files deleted):
```bash
ssh admin@host "powershell -Command \"Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' -EA SilentlyContinue | Where-Object { \$_.DisplayName -like '*NVIDIA App*' } | Select DisplayName,DisplayVersion\""
```

2. CDN URL format: `https://us.download.nvidia.com/nvapp/client/VERSION/NVIDIA_app_vVERSION.exe`
Probe with `curl -sI` and confirm HTTP 200 + Content-Length before downloading. Last-seen example on this PC was 11.0.6.383 — re-resolve; do not reuse blindly.

3. Remove ghost registry entries (NVIDIA App, ShadowPlay, NvBackend) from HKLM Uninstall + WOW6432Node, then clear empty `NVIDIA app` folders under Program Files and Program Files (x86).

4. Install via scheduled task as SYSTEM with `-s`. Silent install completes in ~30s. Poll `NVIDIA_app_setup` then unregister the task.

Verify: `Get-ChildItem "C:\Program Files\NVIDIA Corporation\NVIDIA app" -Recurse -Filter *.exe` should list multiple exes.

NVIDIA App replaced GeForce Experience. Registry name is "NVIDIA App". winget ID is not reliable — use the CDN URL.
