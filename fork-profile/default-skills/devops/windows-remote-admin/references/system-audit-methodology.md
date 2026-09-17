# Windows System Architecture Audit Methodology

Captures the audit workflow developed Sep 2026 for DESKTOP-PH4F2DK post-damage recovery.
Useful as a template for periodic system audits on Windows power-user/gaming machines.

## Core principle: read-only first, always

Phase 1 is a pure read. No changes. Produce a structured findings list.
Get user confirmation on the findings list before entering Phase 2.
Never combine audit and cleanup into a single step.

## Phase 1: Read-only system scan

Run these in sequence over SSH. Save output to a findings file.

```powershell
# === DISK ===
Get-PSDrive C,D,F | Select-Object Name,@{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}},@{N='UsedGB';E={[math]::Round($_.Used/1GB,1)}}

# Top-level C:\ sizes
Get-ChildItem "C:\" | ForEach-Object {
    $sz = (Get-ChildItem $_.FullName -Recurse -EA SilentlyContinue | Measure-Object Length -Sum).Sum
    [PSCustomObject]@{Folder=$_.Name; SizeGB=[math]::Round($sz/1GB,2)}
} | Sort-Object SizeGB -Descending | Format-Table

# === PROCESSES ===
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 25 Name,Id,@{N='MB';E={[math]::Round($_.WorkingSet/1MB,1)}} | Format-Table

# === SERVICES ===
Get-Service | Where-Object { $_.StartType -in @('Automatic','AutomaticDelayedStart') } |
    Select-Object Name,DisplayName,Status,StartType | Sort-Object Status,Name | Format-Table -AutoSize

# === SCHEDULED TASKS (non-Microsoft) ===
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } |
    Select-Object TaskName,TaskPath,State | Sort-Object TaskPath | Format-Table -AutoSize

# === STARTUP ITEMS ===
Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location,User | Format-Table -Wrap

# === APPDATA TOP CONSUMERS (per user) ===
foreach ($user in @('rainbow','admin')) {
    Write-Host "=== $user ==="
    Get-ChildItem "C:\Users\$user\AppData\Local" -EA SilentlyContinue | ForEach-Object {
        $sz = (Get-ChildItem $_.FullName -Recurse -EA SilentlyContinue | Measure-Object Length -Sum).Sum
        [PSCustomObject]@{Folder=$_.Name; SizeGB=[math]::Round($sz/1GB,3)}
    } | Sort-Object SizeGB -Descending | Select-Object -First 15 | Format-Table
}

# === SECURITY CHECK ===
# UAC level
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System').ConsentPromptBehaviorAdmin
# WinRM status
Get-Service WinRM | Select-Object Status,StartType
# Execution policy
Get-ExecutionPolicy -List
```

## Phase 2: Adversarial pass on findings

Before presenting findings to the user, challenge each item:

1. Is this definitely orphaned or is there a non-obvious dependency?
2. Does removing it have a one-way door (cannot easily undo)?
3. Is the size saving worth the risk?
4. Is the "correct" action actually something the user must do interactively (GUI only)?

Label each finding: SAFE/CONFIRM/SKIP/USER-INTERACTIVE

## Phase 3: Prioritised recommendation list

Present findings as a prioritised list grouped by risk level:
- Quick wins (safe, minimal risk, good size recovery): do these first
- Medium items (require confirmation or have some dependency): present with context
- Deferred (GUI-only, complex, or marginal gain): list but don't do
- Rejected (adversarial pass found reasons to skip): explain briefly

Don't present a wall of individual items. Group by theme: disk, services, tasks, security.

## Adversarial challenges that are worth running

For each proposed change, check:

| Challenge | How to verify |
|-----------|---------------|
| Service is truly orphaned | Check if any running process depends on it (`sc qc <svc>`) |
| Task trigger script still exists | `Get-ScheduledTask | Select -Expand Actions` — check Execute path |
| AppData folder is truly orphaned | Check if parent app is still installed in Add/Remove Programs |
| WSL folder is safe to delete | `wsl -l -v` — if no distros, safe; also check wsl --status |
| Registry key belongs to uninstalled app | Cross-check DisplayName against Get-Package or HKLM Uninstall |

## Findings from Sep 2026 audit (DESKTOP-PH4F2DK)

Total disk recovered: ~26 GB over one session (20 GB free -> 45.9 GB free)

Breakdown:
- Pagefile reduction: 12 GB
- safe-cleanup script: 975 MB
- Crash dumps: 1.47 GB
- WSL (admin account): 3.7 GB
- AppData orphans (rainbow + admin): 3.2 GB combined
- F: drive installer/cache: 612 MB

RAM freed from startup optimization:
- DSAService (Intel DSA disabled): 243 MB
- PhoneExperienceHost (Phone Link deprovisioned): 186 MB
- OfficeClickToRun set to Manual: ~72 MB
- Google Updater services removed: ~20 MB
Total: ~520 MB freed at idle

## Security gaps found and remediation status

Updated Sep 4 2026 after second audit pass.

| Finding | Risk | Fix | Status |
|---------|------|-----|--------|
| UAC ConsentPromptBehaviorAdmin = 1 | Medium | Revert to 5 | FIXED (Sep 3 2026) |
| PromptOnSecureDesktop = 0 | Low-Medium | Set to 1 so UAC prompts render on secure desktop | FIXED (Sep 4 2026) |
| WinRM port 5985 running + bound to all interfaces | Low-Medium | Stopped, set to Manual startup | FIXED (Sep 4 2026) |
| NoDriveTypeAutoRun = 158 (partial) | Low | Set HKLM+HKCU to 255 | FIXED (Sep 4 2026) |
| SoftLandingCreativeManagementTask PUP scheduler | Medium | Deleted via schtasks | FIXED (Sep 4 2026) |
| Print Spooler running unnecessarily | Low-Medium | Stopped + Disabled | FIXED (Sep 4 2026) |
| Chrome mDNS / Lync / FAXRX orphan firewall rules | Low | Removed (6 rules) | FIXED (Sep 4 2026) |
| DoH not configured | Medium | EnableAutoDoh=2 + Cloudflare set to Encrypted Only in UI | FIXED (Sep 4 2026) |
| Activity history cloud sync enabled | Low | PublishUserActivities=0, UploadUserActivities=0 | FIXED (Sep 4 2026) |
| BitLocker off on C: and D: | High | User declined — accepted risk | DEFERRED (user choice) |
| Maintenance scripts have no error logging | Low | Add try/catch + log to each script | Pending |
| UsoClient in driver-update.ps1 has no timeout | Low | Wrap with 15-min Start-Job timeout | Pending |
| HNS Container Networking firewall rules (port 53 open) | Low | Removed 2 rules (Docker/WSL2 absent) | FIXED (Sep 4 2026) |
| NetBIOS over TCP/IP enabled on Wi-Fi adapter | Low | Set NetbiosOptions=2 on all adapters via registry | FIXED (Sep 4 2026) |
| Delivery Optimization mode 3 (LAN+internet peers) | Low | Set DODownloadMode=1 (LAN-only) | FIXED (Sep 4 2026) |
| Windows Recall policy absent | Low | DisableAIDataAnalysis=1, AllowRecallEnablement=0 | FIXED (Sep 4 2026) |
| Activity history cloud sync | Low | PublishUserActivities=0, UploadUserActivities=0 | FIXED (Sep 4 2026) |

## Drift prevention — scheduled task

A weekly drift-check + auto-heal task was installed Sep 4 2026:

    Task: \Maintenance\DesktopDriftCheck
    Script: C:\Scripts\desktop-drift-check.ps1
    Schedule: Sundays 3:00 AM, SYSTEM account
    Logs to: C:\Temp\drift-check-YYYYMMDD-HHmmss.txt (auto-purged after 30 days)

The task checks all 19 hardened settings and auto-heals any that drift:
- WinRM (stop if restarted), Spooler (stop if re-enabled)
- AutoRun HKLM (255), PromptOnSecureDesktop (1)
- EnableAutoDoh (2), per-adapter DoH ConfigOptions (2)
- DODownloadMode (1), DisableAIDataAnalysis (1)
- PublishUserActivities (0), LLMNR (0)
- NetBIOS on all adapters (2)
- ASR rules (all 3 GUIDs = 1)
- Read-only checks (no auto-fix): Defender RTP, RDP disabled

Drift sources observed:
- WinRM: restarts itself if any Windows service triggers a WS-Management dependency;
  was found Running/Automatic 15 minutes after being stopped in the same session.
- ASR rules: Windows Defender updates occasionally reset ASR rules to Audit mode.
- Delivery Optimization: major feature updates reset DODownloadMode.

## Next audit cadence

Recommended: run Phase 1 scan quarterly. Disk and AppData audits accumulate fast on gaming machines.
Scheduled maintenance tasks run weekly/monthly already — full audit is an overlay check, not a replacement.

## Privacy hardening batch (remote-safe, no reboot needed)

This batch can be applied in a single fixes.ps1 script over SSH after a read-only audit confirms
these gaps. All changes take effect immediately. User declined BitLocker — not included.

```powershell
# a) AutoRun: disable all drive types
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f

# b) UAC secure desktop enforcement
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' PromptOnSecureDesktop 1 -Type DWord

# c) WinRM: stop and set Manual
Stop-Service WinRM -Force
Set-Service WinRM -StartupType Manual

# d) SoftLanding PUP task (path is user-SID-specific, adjust as needed)
Unregister-ScheduledTask -TaskPath '\SoftLanding\S-1-5-21-1781395712-2779854169-197615253-1003\' -TaskName 'SoftLandingCreativeManagementTask' -Confirm:$false

# e) Orphaned Chrome mDNS firewall rule
Get-NetFirewallRule -DisplayName 'Google Chrome (mDNS-In)' -EA SilentlyContinue | Remove-NetFirewallRule

# f) Orphaned Lync + FAXRX firewall rules
Get-NetFirewallRule | Where-Object { $_.DisplayName -like '*Lync*' -or $_.DisplayName -eq 'FAXRX.EXE' } | Remove-NetFirewallRule

# g) Print Spooler: stop and disable (re-enable temporarily when printing needed)
Stop-Service Spooler -Force
Set-Service Spooler -StartupType Disabled

# h) DoH: arm the feature (also do Settings UI step for full enforcement)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters" /v EnableAutoDoh /t REG_DWORD /d 2 /f

# i) Activity history
$path = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'
if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
Set-ItemProperty $path PublishUserActivities 0 -Type DWord
Set-ItemProperty $path UploadUserActivities 0 -Type DWord
```

Note: DoH (h) requires an additional Settings UI step to fully enforce "Encrypted only" per adapter.
See the DoH section in SKILL.md for verification command.
