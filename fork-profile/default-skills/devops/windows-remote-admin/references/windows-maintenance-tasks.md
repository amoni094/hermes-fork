# Windows Maintenance Scheduled Tasks

Reference for recurring maintenance tasks on DESKTOP-PH4F2DK.
All scripts deployed to `C:\Windows\System32\` and registered as SYSTEM scheduled tasks.

## Current task schedule

| Task name             | Schedule           | Script                        | Purpose |
|----------------------|--------------------|-------------------------------|---------|
| SafeCDriveCleanup    | Sundays 3:00AM     | safe-cleanup.ps1              | Temp/logs/browser cache/recycle |
| WIACleanup           | Sundays 3:30AM (monthly, every 4 weeks) | wia-cleanup.ps1 | Windows Installation Assistant folder |
| DISMComponentCleanup | Sundays 4:00AM (monthly, every 4 weeks) | dism-cleanup.ps1 | WinSxS component store |
| WeeklyDriverUpdate   | Wednesdays 2:00AM  | driver-update.ps1             | NVIDIA + Intel DSA + Windows Update drivers |

## Safe cleanup script pattern

Key principle: **dry-run first, then apply**. The script accepts `-DryRun` switch.

```powershell
# Dry run — shows what would be freed
powershell -ExecutionPolicy Bypass -File C:\Windows\System32\safe-cleanup.ps1 -DryRun

# Apply
powershell -ExecutionPolicy Bypass -File C:\Windows\System32\safe-cleanup.ps1
```

### Safe targets (never touch Program Files, System32, AppData\Roaming)

- `C:\Windows\Temp`
- `%TEMP%` (user temp)
- `C:\Windows\SoftwareDistribution\Download` (Windows Update cache — safe, re-downloads if needed)
- `C:\Windows\ServiceProfiles\NetworkService\AppData\Local\Microsoft\Windows\DeliveryOptimization\Cache`
- `C:\Windows\Logs\CBS` (component log files only)
- `C:\Windows\Prefetch` (files only — Windows rebuilds automatically)
- Browser caches: Chrome/Edge Cache + Code Cache subdirs; Firefox cache2 per-profile only
- `C:\Users\*\AppData\Local\Microsoft\Windows\Explorer` (thumbnail cache, files only)
- Recycle bin (all drives)
- Specific upgrade folders only: `$GetCurrent`, `$SysReset`, `OneDriveTemp`, `Windows.old`

### Space audit findings (Sep 2026)

After cleanup: 44+ GB free on ~110GB drive.

| Folder | Size | Notes |
|--------|------|-------|
| Windows | 29 GB | WinSxS 11.5 GB, Edge/Copilot 6.9 GB — don't touch |
| Program Files (x86) | 12.9 GB | Microsoft Edge 6.9 GB, Office 3.8 GB |
| Users | 2.75 GB | Normal |
| Program Files | 2.27 GB | Normal |

Edge/Copilot folders (`C:\Program Files (x86)\Microsoft\EdgeCore`, `EdgeWebView`, `Copilot`) total
~6.9 GB — Windows-managed, cannot be safely removed.

## DISM WinSxS cleanup

```bash
# Run via SSH — takes 5-10 min
ssh admin@100.88.247.70 "DISM /Online /Cleanup-Image /StartComponentCleanup /ResetBase 2>&1"
```

`/ResetBase` marks superseded components for eventual removal but space is reclaimed gradually
(over next update cycle), not immediately. Normal to see no immediate free space change.

## Driver update script

winget is NOT available on the admin account (`winget.exe` not found in admin WindowsApps).
The driver-update.ps1 script uses only `UsoClient` for Windows Update driver scans.

```
UsoClient StartScan       -- trigger scan
UsoClient StartDownload   -- trigger download
UsoClient StartInstall    -- trigger install
```

For NVIDIA GPU drivers specifically: **use NVIDIA App manually**. The app shows a notification
when a new driver is available (one-click update). NVIDIA App replaced GeForce Experience —
do NOT look for "NVIDIA GeForce Experience" in the installed apps list.

NVIDIA App direct CDN download URL format:
`https://us.download.nvidia.com/nvapp/client/VERSION/NVIDIA_app_vVERSION.exe`
(e.g. `https://us.download.nvidia.com/nvapp/client/11.0.6.383/NVIDIA_app_v11.0.6.383.exe`)

## Additional cleanup targets added Sep 2026

The following were added to `safe-cleanup.ps1` after crash dump ate 1.47 GB disk unnoticed:

```powershell
# Crash dumps — can be 1-2 GB, accumulate silently
Remove-Item "C:\Windows\MEMORY.DMP" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\Minidump\*" -Force -ErrorAction SilentlyContinue

# C:\Temp installer leftovers older than 7 days
Get-ChildItem "C:\Temp" -File | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force -ErrorAction SilentlyContinue
```

## Error logging — gap in current scripts

All four maintenance scripts (safe-cleanup.ps1, dism-cleanup.ps1, driver-update.ps1, wia-cleanup.ps1)
currently have no error logging. Silent failures go unnoticed until a problem is discovered manually.

Add to each script:

```powershell
# Add at top of every maintenance script
$LogFile = "C:\Windows\Logs\maintenance-$(Get-Date -Format 'yyyyMMdd').log"
function Log { param($msg) "$(Get-Date -Format 'HH:mm:ss') $msg" | Tee-Object -FilePath $LogFile -Append }

try {
    Log "Starting [task name]"
    # ... existing script body ...
    Log "Completed OK"
} catch {
    Log "ERROR: $_"
    exit 1
}
```

## UsoClient timeout gap

driver-update.ps1 calls UsoClient with no timeout. On some Win11 builds it hangs indefinitely.

Wrap with a timeout:

```powershell
$job = Start-Job { UsoClient StartScan; Start-Sleep 10; UsoClient StartDownload; Start-Sleep 30; UsoClient StartInstall }
$completed = Wait-Job $job -Timeout 900  # 15 min max
if (-not $completed) {
    Stop-Job $job
    Log "UsoClient timed out after 15 min — Windows Update may not have run"
}
Remove-Job $job
```

## Register tasks (PowerShell)

```powershell
$sys = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

# Weekly (every Sunday)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "03:00AM"

# Monthly (every 4 weeks)
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 4 -DaysOfWeek Sunday -At "04:00AM"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NonInteractive -File C:\Windows\System32\script.ps1"
Register-ScheduledTask -TaskName "TaskName" -Action $action -Trigger $trigger -Principal $sys -Force
```
