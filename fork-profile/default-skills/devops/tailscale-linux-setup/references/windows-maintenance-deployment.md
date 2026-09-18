# Windows Remote Maintenance Deployment (via SSH Jump Host)

Pattern validated 2026-09-02 on `booran` (Windows 11 build 22631) via Galina jump host.

## Deployment Sequence

1. Write the PS1 script locally, then push via scp through the jump host:
```bash
# Push to jump host
scp /tmp/maintenance.ps1 galina@100.79.225.3:/tmp/maintenance.ps1

# Push from jump host to Windows target (C:\Windows\System32\ for persistence)
ssh -o BatchMode=yes galina@100.79.225.3 \
  "sshpass -p 'PASS' scp -o StrictHostKeyChecking=accept-new \
   /tmp/maintenance.ps1 admin@192.168.1.xxx:'C:/Windows/System32/maintenance.ps1'"
```

2. Register the scheduled task via schtasks.exe (NOT PowerShell cmdlets — see pitfall below):
```bash
ssh -o BatchMode=yes galina@100.79.225.3 \
  "sshpass -p 'PASS' ssh -o BatchMode=no admin@192.168.1.xxx \
   'schtasks /delete /tn MyTask /f 2>nul & \
    schtasks /create /tn \"MyTask\" \
      /tr \"powershell -NonInteractive -ExecutionPolicy Bypass -File C:\\Windows\\System32\\maintenance.ps1\" \
      /sc weekly /d SUN /st 03:00 /ru SYSTEM /rl HIGHEST /f && \
    schtasks /query /tn MyTask /fo LIST'"
```

3. Do a test run and check the log:
```bash
# Trigger immediate run
ssh ... 'schtasks /run /tn MyTask'

# Wait, then read log
sleep 30
ssh ... 'type C:\\Windows\\Temp\\maintenance.log'
```

4. Clean up temp bootstrap files:
```bash
ssh ... 'del C:\\Windows\\Temp\\register-task.ps1'
```

## schtasks.exe Key Flags

    /tn "TaskName"       Task name (use quotes if spaces)
    /tr "command"        What to run (full path, with args)
    /sc weekly           Schedule type (once, daily, weekly, monthly)
    /d SUN               Day of week (SUN, MON, TUE, etc.)
    /st 03:00            Start time (24h)
    /ru SYSTEM           Run as SYSTEM account
    /rl HIGHEST          Highest privileges (required for system-level ops)
    /f                   Force overwrite if task exists
    /fo LIST             Output format for /query

## PS1 Script Best Practices

```powershell
# Log helper
$LogFile = "C:\Windows\Temp\taskname.log"
function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Tee-Object -FilePath $LogFile -Append | Out-Null
}

# Rotate log if old
if (Test-Path $LogFile) {
    $age = (Get-Date) - (Get-Item $LogFile).LastWriteTime
    if ($age.TotalDays -gt 30) { Remove-Item $LogFile -Force }
}

# Wrap every section in try/catch so one failure doesn't abort the rest
try {
    # ... task ...
    Log "Section OK"
} catch {
    Log "Section warning: $_"
}
```

## Windows Update via PowerShell (non-module)

The PSWindowsUpdate module requires installation. Without it, use COM:
```powershell
$Session = New-Object -ComObject Microsoft.Update.Session
$Searcher = $Session.CreateUpdateSearcher()
$Result = $Searcher.Search("IsInstalled=0 and Type='Software' and IsHidden=0")
$Updates = $Result.Updates
if ($Updates.Count -gt 0) {
    $Downloader = $Session.CreateUpdateDownloader()
    $Downloader.Updates = $Updates
    $Downloader.Download() | Out-Null
    $Installer = $Session.CreateUpdateInstaller()
    $Installer.Updates = $Updates
    $InstallResult = $Installer.Install()
    # ResultCode 2 = Succeeded, 3 = SucceededWithErrors
    if ($InstallResult.RebootRequired) {
        shutdown /r /t 60 /c "Maintenance reboot" /f
    }
}
```

## Disk Cleanup Items

```powershell
# Windows Update download cache (stop service first)
Stop-Service wuauserv -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
Start-Service wuauserv -ErrorAction SilentlyContinue

# Temp files older than 7 days
Get-ChildItem $env:TEMP -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) -and -not $_.PSIsContainer } |
    Remove-Item -Force -ErrorAction SilentlyContinue

# Recycle bin
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

# Prefetch
Remove-Item "C:\Windows\Prefetch\*.pf" -Force -ErrorAction SilentlyContinue

# Event logs (trim if >50MB)
$sizeMB = [math]::Round((Get-WmiObject Win32_NTEventLogFile -Filter "LogFileName='System'").FileSize / 1MB, 1)
if ($sizeMB -gt 50) { wevtutil cl System }
```

## Auto-delete User Downloads Folder (N days)

```powershell
$DownloadsPath = "C:\Users\Leon\Downloads"  # adjust per user
$cutoff = (Get-Date).AddDays(-30)
$old = Get-ChildItem -Path $DownloadsPath -Recurse -ErrorAction SilentlyContinue |
       Where-Object { -not $_.PSIsContainer -and $_.LastWriteTime -lt $cutoff }
$count = ($old | Measure-Object).Count
$sizeMB = [math]::Round(($old | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
if ($count -gt 0) {
    $old | Remove-Item -Force -ErrorAction SilentlyContinue
    # Remove empty subdirs left behind
    Get-ChildItem $DownloadsPath -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.PSIsContainer } |
        Sort-Object FullName -Descending |
        Where-Object { (Get-ChildItem $_.FullName -ErrorAction SilentlyContinue).Count -eq 0 } |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Log "Downloads cleanup: removed $count file(s), ~${sizeMB}MB"
}
```

## Windows Autologin (standard user, no password)

To configure a machine to boot straight into a specific user account without any login prompt:

```powershell
$reg = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty -Path $reg -Name AutoAdminLogon    -Value '1'
Set-ItemProperty -Path $reg -Name DefaultUserName   -Value 'Leon'       # target account
Set-ItemProperty -Path $reg -Name DefaultPassword   -Value ''           # empty if no password
Set-ItemProperty -Path $reg -Name DefaultDomainName -Value 'BOORAN'     # machine hostname
Remove-ItemProperty -Path $reg -Name ForceAutoLogon -ErrorAction SilentlyContinue
```

Deploy via bootstrap task as SYSTEM (same pattern as maintenance deployment). Takes effect on next reboot.

Notes:
- The admin account (password-protected) stays separate — autologin only affects the boot-to-desktop flow.
- Works even if the target account has no password (set DefaultPassword to empty string).
- `ForceAutoLogon` re-engages autologin after every logout; omit it (or remove it) so the user can switch accounts normally.
- Check `Get-LocalUser | Select Name,Enabled,PasswordRequired` first to confirm target is standard (not admin) and has no password.

## Windows Security Hardening for Non-Technical Users

Apply these as a SYSTEM scheduled task alongside maintenance. Does NOT block adult content — only malware/phishing.

### DNS: Cloudflare malware+phishing blocking

```powershell
# 1.1.1.2 / 1.0.0.2 = malware+phishing blocking; 1.1.1.3 / 1.0.0.3 = also blocks adult content
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
foreach ($adapter in $adapters) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.InterfaceIndex `
        -ServerAddresses @('1.1.1.2', '1.0.0.2')
}
Clear-DnsClientCache
```

Re-run this in every maintenance pass — Windows Update and DHCP can reset DNS.

### Windows Defender hardening

```powershell
Set-MpPreference -PUAProtection Enabled                  # block adware/bundleware/miners
Set-MpPreference -EnableNetworkProtection Enabled        # block malicious URLs at kernel level
Set-MpPreference -DisableRealtimeMonitoring $false       # ensure real-time on
Set-MpPreference -MAPSReporting Advanced                 # cloud-based protection
Set-MpPreference -SubmitSamplesConsent SendSafeSamples
Set-MpPreference -CloudBlockLevel High                   # faster zero-day detection
Set-MpPreference -DisableEmailScanning $false
Set-MpPreference -DisableArchiveScanning $false
```

### SmartScreen enforcement via policy

```powershell
# App/file SmartScreen
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer' `
    -Name SmartScreenEnabled -Value 'RequireAdmin'

# Edge SmartScreen — enforce via policy so user can't bypass
$edgePolicies = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge'
if (-not (Test-Path $edgePolicies)) { New-Item -Path $edgePolicies -Force | Out-Null }
Set-ItemProperty -Path $edgePolicies -Name SmartScreenEnabled                      -Value 1
Set-ItemProperty -Path $edgePolicies -Name PreventSmartScreenPromptOverride        -Value 1
Set-ItemProperty -Path $edgePolicies -Name PreventSmartScreenPromptOverrideForFiles -Value 1
```

## Staged Deploy Pattern (target offline at time of authoring)

When the target Windows machine is offline/asleep at the time you want to deploy, push a one-shot cron to the jump host that fires when the target comes back:

```bash
# On Galina's laptop — self-deleting cron that deploys when booran is reachable
ssh admin@100.79.225.3 "sudo bash -c '
echo \"*/5 * * * * root timeout 30 bash /tmp/deploy.sh >> /tmp/deploy.log 2>&1 && rm /etc/cron.d/deploy-target\" \
  > /etc/cron.d/deploy-target && chmod 644 /etc/cron.d/deploy-target'"
```

The deploy script must start with a connectivity check and exit 1 if the target isn't reachable (so the cron self-deletes only on success):

```bash
#!/bin/bash
if ! sshpass -p "$WIN_PASS" ssh -o ConnectTimeout=10 admin@"$WIN_IP" 'echo ok' 2>/dev/null | grep -q ok; then
    exit 1  # target not reachable — cron will retry in 5 minutes
fi
# ... deploy logic ...
# cron deletes itself only when this script exits 0
```

## Pitfalls

- **New-ScheduledTaskSettingsSet boolean args**: On PS5, `-RunOnlyIfNetworkAvailable $false` and `-WakeToRun $false` fail with "positional parameter not found". Use schtasks.exe instead of PS cmdlets for task registration.
- **Bootstrap task runs as wrong user**: If schtasks is run via SSH and `/ru SYSTEM` doesn't stick, check `schtasks /query /fo LIST /v` and look at "Run As User". The SSH session itself doesn't affect `/ru SYSTEM` — usually means the task already existed with a different user.
- **Task created but never ran**: `/st 00:00` causes "past time" warning but task still runs when you call `/run` manually. The `Start-WhenAvailable` equivalent in schtasks is `/sc once /st 00:00 /f` — the task runs on demand via `/run`.
- **`type` command for log reading**: Works over SSH for small files. For large logs, use `powershell Get-Content -Tail 50`.
- **Nested quote escaping over SSH jump**: Three-layer escaping (local shell → SSH → Windows cmd) is fragile. Prefer writing a PS1 or .bat file to the target and calling it, rather than inline complex commands.
- **C:\Users\admin\Downloads\ may not exist**: The admin account may not have been used interactively. Use `C:\Windows\Temp\` for all remote-dropped files.
- **DNS silently reset by DHCP/Windows Update**: Always re-apply DNS settings in the weekly maintenance pass, not just at setup.
- **`Get-Service sshd` ≠ service running**: Windows OpenSSH Optional Features install does not start or enable the service. Must explicitly `Start-Service sshd` + `Set-Service sshd -StartupType Automatic` + add firewall rule.
