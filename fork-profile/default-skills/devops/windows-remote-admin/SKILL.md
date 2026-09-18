---
version: 1.0.0
name: windows-remote-admin
description: "Use when remotely administering a Windows desktop via SSH."
tags: [windows, ssh, remote-admin, desktop, powershell, overclocking]
related_skills: [wake-on-lan-desktop]
triggers:
  - Administering DESKTOP-PH4F2DK via SSH
  - Running PowerShell commands remotely over SSH
  - Windows disk cleanup via SSH
  - CPU/GPU overclock validation on Windows
  - Any destructive command (rmdir, del, reg delete) via SSH on Windows
---

# Windows Remote Administration (SSH/Tailscale)

This-machine-only: DESKTOP-PH4F2DK. Tailscale `admin@100.88.247.70` and LAN `.181` are this PC — do not treat as general Windows SSH advice. Re-check `tailscale ip -4` if SSH fails.

## Critical: SSH command output quirks on Windows

**PITFALL: Compound commands passed via SSH return empty output.** Single commands work; chained commands (`cmd1 && cmd2`) and pipes (`cmd | findstr`) silently return nothing. Run each command in a separate SSH call.

**PITFALL: `wmic` is not installed on Windows 11.** Use PowerShell CIM equivalents:
- `wmic product get Name,Version` → `Get-CimInstance Win32_Product | Select-Object Name,Version`
- `wmic os get FreePhysicalMemory` → `Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory`
- `wmic startup list full` → `Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location`
- `wmic service where...` → `Get-CimInstance Win32_Service | Where-Object {$_.StartMode -eq 'Auto'}`

**PITFALL: PowerShell `Set-Content` / file writes via wmiexec or SSH return empty and fail silently.** Always use the fetch-local-patch-push-via-smbclient pattern for file edits (e.g. sshd_config). Never trust inline PowerShell file writes over SSH without verifying the file changed.

```bash
# Safe file-edit pattern:
ssh Administrator@IP "type C:\\ProgramData\\ssh\\sshd_config" | sed 's/old/new/' > /tmp/patched_file
smbclient -U "Administrator%PASS" //IP/C$ -c "put /tmp/patched_file ProgramData\\ssh\\sshd_config"
```

## Bootstrapping SSH on a new Windows machine (SMB foothold)

When a Windows machine has port 445 open but SSH is not yet enabled, use impacket
to push the enablement command remotely.

Install impacket (scripts land at `~/.local/bin/`):
```bash
pip install impacket
# Provides: psexec.py, wmiexec.py, atexec.py
```

Probe open ports first:
```bash
nc -zv <ip> 445 22 3389 5985
```

Try in order:
```bash
psexec.py 'admin:PASSWORD@IP' "hostname"
wmiexec.py 'admin:PASSWORD@IP' "hostname"
atexec.py 'admin:PASSWORD@IP' "hostname"
```

**PITFALL: All three fail for local non-built-in admin accounts due to UAC token filtering.**
Symptoms differ by tool but the cause is the same:
- psexec: `share 'ADMIN$' is not writable` (credentials accepted, UAC strips the token)
- wmiexec / atexec: `rpc_s_access_denied`

The fix requires the registry key `LocalAccountTokenFilterPolicy=1` — but you cannot push
it remotely without execution access. This is a true chicken-and-egg.

**To break the deadlock (choose one):**

Option A — try the built-in `Administrator` account (not a custom account named "admin");
the built-in account bypasses UAC filtering even over network SMB.

Option B — have the user paste this into an admin Command Prompt at the physical machine:
```cmd
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v LocalAccountTokenFilterPolicy /t REG_DWORD /d 1 /f
```
After that, wmiexec.py and atexec.py work. Once SSH is set up, undo the key:
```cmd
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v LocalAccountTokenFilterPolicy /f
```

**Option B2 — skip UAC workaround entirely; instead have user enable OpenSSH directly in one paste:**
```cmd
powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd; Set-Service -Name sshd -StartupType Automatic; New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"
```
This installs + starts + firewall-opens SSH in one shot without needing LocalAccountTokenFilterPolicy.
Takes 30–60 seconds; minimal output is normal.

**PITFALL: `Add-WindowsCapability` requires internet access and Windows Update to be functional.**
If the command runs but port 22 remains closed, the capability download likely failed silently. In this case, use Option B (LocalAccountTokenFilterPolicy) or manual WinRM enablement.

**CMD paste tip: right-click to paste (not Ctrl+V or Ctrl+Shift+V).** Standard CMD does not
respond to Ctrl+V. If the window title says "Administrator: Command Prompt" the elevation is
correct.

Enable OpenSSH remotely once execution access works:
```bash
wmiexec.py 'admin:PASSWORD@IP' "powershell -Command Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd; Set-Service sshd -StartupType Automatic"
```

---

## SSH connection (DESKTOP-PH4F2DK)

```bash
ssh admin@100.88.247.70 "echo ok"
```

Tailscale takes 30-60s to connect after login. If SSH times out right after reboot, wait and retry.
If it resets (not just times out), sshd may have crashed.

Restart sshd from the physical machine:
```
net start sshd        # cmd as admin
Start-Service sshd   # PowerShell as admin
```

If sshd fails to start (error 1067): run `sshd -t` in admin PowerShell to see the config error.
If sshd.exe or a dependency was deleted by accident (e.g. rmdir damage), reinstall the capability:
```powershell
# In admin PowerShell (run locally on the machine)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```
This restores the binary without touching sshd_config. Config file at `C:\ProgramData\ssh\sshd_config`.

---

## CRITICAL: Destructive commands via SSH

### NEVER pass `$`-prefixed folder names inline via SSH

```bash
# DANGEROUS - DO NOT DO THIS:
ssh admin@host "rmdir /s /q C:\$GetCurrent"
# Bash expands $GetCurrent to empty string -> becomes: rmdir /s /q C:\
# Silently attempts to delete all of C:\
# Access denied on most files, but unlocked folders (Program Files subdirs etc) WILL be wiped
```

This exact pattern destroyed ProtonVPN and Firefox installations in a real session (Sep 3 2026).
See references/rmdir-incident.md for the full incident record.

### Safe alternatives for `$`-folder deletion

**Option A: Scheduled task as SYSTEM (recommended)**
```bash
ssh admin@host "schtasks /create /tn CleanUp /sc once /st 00:00 /ru SYSTEM /tr \"cmd /c rmdir /s /q C:\\\$GetCurrent\" /f"
ssh admin@host "schtasks /run /tn CleanUp"
sleep 5
ssh admin@host "schtasks /delete /tn CleanUp /f"
```

**Option B: do not echo a batch file over SSH.** Unescaped `$GetCurrent` still expands in bash and wipes `C:\`. Prefer Option A (already-escaped schtasks) or Option C (quoted heredoc). Never `echo rmdir ... $GetCurrent` through ssh.

**Option C: scp a PowerShell script, run it**
```bash
cat > /tmp/cleanup.ps1 << 'EOF'
Remove-Item -Recurse -Force "C:\$GetCurrent"
EOF
scp /tmp/cleanup.ps1 admin@host:C:/Temp/cleanup.ps1
ssh admin@host "powershell -ExecutionPolicy Bypass -File C:\Temp\cleanup.ps1"
```

---

## PowerShell via SSH: variable interpolation

Bash expands `$var` and `@{...}` before the command reaches PowerShell.

**Broken pattern:**
```bash
ssh admin@host "powershell -Command \"\$x = Get-WmiObject Win32_ComputerSystem\""
# $x expanded by bash -> empty -> PowerShell receives garbage
```

**Safe pattern - write script file via Python heredoc:**
```python
import subprocess
script = '''
$x = Get-WmiObject Win32_ComputerSystem
$x.AutomaticManagedPagefile = $false
$x.Put()
'''
with open('/tmp/ps_script.ps1', 'w') as f:
    f.write(script)
subprocess.run(['scp', '/tmp/ps_script.ps1', 'admin@100.88.247.70:C:/Temp/ps_script.ps1'])
subprocess.run(['ssh', 'admin@100.88.247.70', 'powershell -ExecutionPolicy Bypass -File C:\\Temp\\ps_script.ps1'])
```

**Commands that work reliably inline:**
- `reg query/add/delete` - no `$` in paths
- `schtasks` - safe inline
- `wevtutil` - safe inline
- `dir C:\\path` - safe with double-backslash
- `tasklist | findstr something` - safe
- `nvidia-smi.exe ...` - safe (use full path with escaped backslashes)

---

## Disk cleanup

### Pagefile sizing (this-machine: 16GB RAM on DESKTOP-PH4F2DK)
Windows defaulted this PC to a 16GB pagefile. Cap via script file (not inline PS). Do not apply 2–4GB caps on machines with different RAM without checking commit charge.

```python
script = '''
$cs = Get-WmiObject Win32_ComputerSystem
$cs.AutomaticManagedPagefile = $false
$cs.Put()
$pf = Get-WmiObject Win32_PageFileSetting
if ($pf) {
    $pf.InitialSize = 2048
    $pf.MaximumSize = 4096
    $pf.Put()
} else {
    Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{Name="C:\\pagefile.sys";InitialSize=2048;MaximumSize=4096}
}
Write-Output "Pagefile set to 2GB min / 4GB max"
'''
```

Effective on next reboot. Frees ~12GB when pagefile was at 16GB default.

### Disk Cleanup automation
```bash
# Set cleanup flags then run cleanmgr silently
ssh admin@host "reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VolumeCaches\\Update Cleanup\" /v StateFlags0064 /t REG_DWORD /d 2 /f"
ssh admin@host "reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VolumeCaches\\Temporary Files\" /v StateFlags0064 /t REG_DWORD /d 2 /f"
ssh admin@host "start /b cleanmgr /sagerun:64"
```

Warning: cleanmgr holds file locks and causes SSH connection resets while running. Wait for it to finish.

### Space audit
```bash
# Check hidden files including pagefile.sys
ssh admin@host "dir C:\\ /a"

# Size of known big folders (don't recurse all of C:\ - times out)
ssh admin@host "powershell -ExecutionPolicy Bypass -Command \"@('Windows','Users','Program Files','Program Files (x86)') | ForEach-Object { \$s=(Get-ChildItem C:\\\$_ -Recurse -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum; '{0,7:N2} GB  {1}' -f (\$s/1GB),\$_ }\""
```

---

## Remote app reinstall after file deletion

When `rmdir` or similar damage deletes app files but leaves the registry intact,
Windows Installer reports "already installed" and blocks a fresh install.

### Ghost registry entry fix

Before reinstalling: detect and remove the stale uninstall record.

```powershell
# ghost-registry-remove.ps1
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($path in $regPaths) {
    Get-ChildItem $path -ErrorAction SilentlyContinue | ForEach-Object {
        $display = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DisplayName
        if ($display -like "*ProtonVPN*" -or $display -like "*Firefox*") {  # adjust filter
            Write-Host "Removing ghost: $display"
            Remove-Item $_.PSPath -Recurse -Force
        }
    }
}
# Also clear any partially empty folder
Remove-Item "C:\Program Files\Proton\VPN" -Recurse -Force -ErrorAction SilentlyContinue
```

Save as script, scp it, run via `powershell -ExecutionPolicy Bypass -File C:\Temp\script.ps1`.

### Firefox — silent install works

```bash
ssh admin@host "powershell -Command \"Invoke-WebRequest -Uri 'https://download.mozilla.org/?product=firefox-latest&os=win64&lang=en-US' -OutFile 'C:\\Temp\\Firefox_setup.exe' -UseBasicParsing\""
ssh admin@host "powershell -Command \"Start-Process 'C:\\Temp\\Firefox_setup.exe' -ArgumentList '/S' -Wait\""
# /S = fully silent, no UAC needed (installs to Program Files for all users)
# Bookmarks/profile stored in %APPDATA%\Mozilla, survive reinstall
```

Verify: `Test-Path "C:\Program Files\Mozilla Firefox\firefox.exe"` should return True.

### Python + Playwright bootstrap on a Windows machine with no Python

When a remote Windows machine has no Python (common on fresh or lightly-used machines), install it silently over SSH, then install Playwright. Enables headless browser automation (e.g. LAN router login) without physical access.

```bash
# 1. Download and install Python 3.11 silently
ssh administrator@<tailscale_ip> "powershell -Command \"Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'C:\\Users\\Administrator\\python_install.exe' -UseBasicParsing; Write-Host 'Downloaded'\""
ssh administrator@<tailscale_ip> "C:\\Users\\Administrator\\python_install.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0"

# 2. Install Playwright + Chromium (must prefix PATH in same cmd /c call)
ssh administrator@<tailscale_ip> "cmd /c set PATH=%PATH%;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\Scripts && pip install playwright -q && python -m playwright install chromium"
```

**PATH must be set inline in every cmd /c call** — `PrependPath=1` only applies to new login sessions, not the current SSH shell. Always prefix: `cmd /c set PATH=%PATH%;C:\\Users\\...\\Python311 && ...`

To run a remote script:
```bash
scp /tmp/my_script.py administrator@<tailscale_ip>:"C:\\Users\\Administrator\\my_script.py"
ssh administrator@<tailscale_ip> "cmd /c set PATH=%PATH%;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311 && python C:\\Users\\Administrator\\my_script.py"
```

**Pitfall: Never pass multi-line Python inline via SSH.** Windows cmd quoting collapses heredocs; PowerShell inline Python is unreliable for scripts >5 lines. Always scp the script file first, then run it.

### ProtonVPN — silent install via SYSTEM scheduled task

ProtonVPN's InnoSetup `/S` flag sometimes stalls when run by a non-interactive SYSTEM process
(waits on service registration or UI probe). Preferred approach:

1. Download installer (use GitHub releases API for direct .exe URL — ProtonVPN download page is JS-rendered):
```bash
curl -s https://api.github.com/repos/ProtonVPN/win-app/releases/latest | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print(a['browser_download_url']) for a in d.get('assets',[]) if 'x64' in a['name']]"
# Returns: https://github.com/ProtonVPN/win-app/releases/download/vX.Y.Z/ProtonVPN_vX.Y.Z_x64.exe
```

2. Download it:
```bash
ssh admin@host "powershell -Command \"Invoke-WebRequest -Uri 'URL' -OutFile 'C:\\Temp\\ProtonVPN_setup.exe' -UseBasicParsing\""
```

3. If silent remote install stalls, have user double-click `C:\Temp\ProtonVPN_setup.exe` locally.
   ProtonVPN settings/credentials survive reinstall (stored in `%APPDATA%\Proton`).

### ProtonVPN install layout (versioned subdirs)

Do NOT check for `ProtonVPN.exe` at the root — use `ProtonVPN.Launcher.exe`.
Service binaries live in `vX.Y.Z` subfolders; a previous version folder after upgrade is rollback, not breakage, unless the service is stopped.
Re-list the directory on this PC — do not assume v5.1.7/v5.1.5.

### NVIDIA App — ghost-folder reinstall

Same rmdir-damage pattern. Full steps: `references/nvidia-app-reinstall.md`. Resolve CDN version from the registry; never hardcode a versioned NVIDIA URL.

See `references/system-audit-methodology.md` for the full audit workflow (read-only phase,
adversarial pass structure, findings template, and Sep 2026 audit results for DESKTOP-PH4F2DK).

See `references/privacy-audit-scripts.md` for reusable audit1/2/3.ps1 plus the 32-check `verify-all.ps1`.
Always scp + `pwsh -File`; scripts must write `C:\Temp\auditN.txt` so results survive SSH drops.
- `Get-Service` PermissionDenied on IsolationSession / Sense / WaaSMedicSvc / WMPNetworkSvc is expected even as admin — ignore; exit 0.
  <!-- why: prevents treating a noisy audit2 run as a failed hardening pass -->
- `EnableAutoDoh` is null when the key is absent (DoH disabled) — null-check before `.GetType()`.
- SoftLandingCreativeManagementTask can show an empty Execute field after the binary was deleted; still delete the task scaffold via schtasks.

See `references/brother-printer-firmware-update.md` for the Brother network printer firmware
check + update workflow, Spooler re-enable pattern, and web UI login procedure.

---

## Scheduled maintenance tasks

See `references/windows-maintenance-tasks.md` for the full task schedule, safe-cleanup script
pattern, DISM notes, and winget driver IDs.

Quick reference — tasks registered on DESKTOP-PH4F2DK as SYSTEM:

    SafeCDriveCleanup     Sundays 3AM  (weekly)   temp/cache/logs
    WIACleanup            Sundays 3:30AM (monthly) Windows Installation Assistant folder
    DISMComponentCleanup  Sundays 4AM  (monthly)   WinSxS component store
    WeeklyDriverUpdate    Wednesdays 2AM (weekly)  NVIDIA + Intel DSA + WU drivers

Scripts live at `C:\Windows\System32\safe-cleanup.ps1` etc. Always deploy as script files via scp,
never inline PowerShell with `$`-containing paths (see bash variable expansion pitfall above).

Orphan/startup/AppData procedures: `references/startup-and-orphans.md` (this-machine audit results, not general Windows advice).
Phone Link: registry disable is insufficient — full Appx deprovision only. See that reference.

## Security hardening (this-machine last verified Sep 2026 — re-read registry, do not trust the date)

See references/system-audit-methodology.md for the full gap table and remediation status.

### UAC — both keys required

Pitfall: ConsentPromptBehaviorAdmin = 5 alone is NOT sufficient. If PromptOnSecureDesktop = 0,
the UAC prompt renders on the regular desktop, which a malicious process in user context can
inject into. Both keys must be 1/5 respectively.

```powershell
# Verify both are correct
$uac = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
$uac.ConsentPromptBehaviorAdmin  # expect 5
$uac.PromptOnSecureDesktop       # expect 1

# Fix if needed:
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' ConsentPromptBehaviorAdmin 5 -Type DWord
Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' PromptOnSecureDesktop 1 -Type DWord
```

Level guide for ConsentPromptBehaviorAdmin:
- 0 = elevate silently (worst — any process can auto-elevate)
- 1 = prompt without secure desktop (no isolation from desktop processes)
- 2 = prompt on secure desktop (no creds required)
- 5 = default — prompt on secure desktop, requires credential on non-admin account

### WinRM — keep Manual, verify at session end

On DESKTOP-PH4F2DK, SSH is the primary remote path. Keep WinRM Manual (not Disabled, not Automatic) so it can be started locally if SSH dies. Do NOT set Automatic — the listener binds all interfaces including this PC's LAN IP (192.168.0.181, this-machine-only) even with a Tailscale-only firewall rule.

**PITFALL: WinRM self-restarts within the same session.**
WinRM was observed going from Stopped/Manual back to Running/Automatic within 15 minutes
of being stopped, triggered by Windows Update or WS-Management service dependencies.
Always verify WinRM status at the END of a session, not just after stopping it.
The drift-check task (Sundays 3am) re-stops it if it regresses.

Verify it's still stopped:
```powershell
Get-Service WinRM | Select-Object Status, StartType
# Expect: Stopped, Manual
```

To re-enable as fallback if needed:
```powershell
Start-Service WinRM
# Then use from Linux:
timeout 5 bash -c "echo > /dev/tcp/100.88.247.70/5985" && echo "WinRM open"
```

### DoH — arms the feature, doesn't activate it

ENABLEAUTODOH = 2 in the registry enables auto-negotiation of DoH but does NOT enforce it.
Windows will try DoH opportunistically with known resolvers (1.1.1.1, 8.8.8.8, 9.9.9.9 are
in the built-in DohWellknownServers list), but plaintext fallback remains possible.

To fully enforce DoH ("Encrypted only"):
1. Set EnableAutoDoh = 2 (registry — done remotely)
2. In Settings > Network & Internet > Wi-Fi > your network > DNS server assignment
   > Manual > IPv4: 1.1.1.1 / 1.0.0.1 > select "Encrypted only (DNS over HTTPS)" in dropdown

Step 2 creates a per-interface policy key:
  HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\<ifIndex>\DnsPolicyConfig

Verify enforcement is active (not just armed):
```powershell
$wifiIdx = (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*'} | Select-Object -First 1).ifIndex
$ifKey = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig"
if (Test-Path $ifKey) { 'DoH enforced' } else { 'DoH armed but NOT enforced — do Settings UI step' }
```

If the per-interface key is absent after the user says they did the Settings step, they likely
set the DNS addresses but left the dropdown on "Unencrypted only" or "Encrypted preferred".
Have them redo the UI step and explicitly pick "Encrypted only".

**Alternatively: enforce per-interface DoH via direct registry write (remote-safe)**

This bypasses the Settings UI entirely and produces the same result:

```powershell
# doh_enforce.ps1 — run as admin on the desktop
$wifiAdapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.Name -like '*Wi-Fi*' } | Select-Object -First 1
$ifIndex = $wifiAdapter.ifIndex

$baseKey = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$ifIndex\DnsPolicyConfig"

@('1.1.1.1', '1.0.0.1') | ForEach-Object {
    $dnsKey = Join-Path $baseKey $_
    if (-not (Test-Path $dnsKey)) { New-Item -Path $dnsKey -Force | Out-Null }
    Set-ItemProperty -Path $dnsKey -Name 'ConfigOptions' -Value 2 -Type DWord  # 2 = encrypted only
    Set-ItemProperty -Path $dnsKey -Name 'Template' -Value 'https://cloudflare-dns.com/dns-query' -Type String
}

# Verify
@('1.1.1.1', '1.0.0.1') | ForEach-Object {
    $dnsKey = Join-Path $baseKey $_
    $opts = (Get-ItemProperty $dnsKey -EA SilentlyContinue).ConfigOptions
    "$_ ConfigOptions=$opts (expect 2)"
}
```

Deploy via scp + pwsh -File (not inline) due to `$` in variable names.

### AutoRun — target value

NoDriveTypeAutoRun = 255 (0xFF) disables autorun on ALL drive types.
The Windows default is 0x91 or 0x9E — both leave some drive types exposed.
Set both HKLM and HKCU to 255:
```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
```

---

## Drift prevention — weekly scheduled task

A weekly drift-check + auto-heal task is installed on DESKTOP-PH4F2DK (re-verify the task exists; do not trust the install date).
Script: `C:\Scripts\desktop-drift-check.ps1`
Task: `\Maintenance\DesktopDriftCheck` — Sundays 3am, SYSTEM account
Logs: `C:\Temp\drift-check-YYYYMMDD-HHmmss.txt` (auto-purged after 30 days)

The script checks 19 settings and auto-heals drift. Critical observed drift sources:
- WinRM self-restarts from WS-Management service dependencies — found Running/Automatic
  just 15 minutes after being stopped in the same session. The drift task re-stops it.
- ASR rules can revert to Audit mode after Defender definition updates.
- Delivery Optimization resets DODownloadMode on major feature updates.

To reinstall the task if lost (e.g. after OS reinstall):
```bash
scp /path/to/drift-check.ps1 admin@100.88.247.70:C:/Scripts/desktop-drift-check.ps1
# Then run install_task.ps1 to register the scheduled task
```

See `references/system-audit-methodology.md` for full drift-check task details and
the list of settings it monitors. Deployable script at `scripts/desktop-drift-check.ps1`.

---

## Hardening: NetBIOS over TCP/IP disable

The WMI method (`SetTcpipNetbios()`) consistently fails over SSH due to deserialization issues.
Use direct registry writes instead — more reliable and equally effective:

```powershell
# netbios_reg.ps1 — disable NetBIOS on all adapters
$interfaces = Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces'
foreach ($iface in $interfaces) {
    Set-ItemProperty -Path $iface.PSPath -Name 'NetbiosOptions' -Value 2 -Type DWord
    # 0 = default (from DHCP), 1 = enabled, 2 = disabled
}

# Verify all adapters set
$interfaces = Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces'
$interfaces | ForEach-Object {
    $v = (Get-ItemProperty $_.PSPath).NetbiosOptions
    "$($_.PSChildName): $v (expect 2)"
}
```

Deploy via scp + pwsh -File. Takes effect at next reboot; no immediate service restart needed.
Expect 8-12 adapter entries (physical + virtual adapters including Tailscale).

---

## Hardening: Delivery Optimization (P2P upload)

```powershell
# Set to LAN-only (no internet peers, no uploading to strangers)
$doPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization'
if (-not (Test-Path $doPath)) { New-Item -Path $doPath -Force | Out-Null }
Set-ItemProperty $doPath -Name 'DODownloadMode' -Value 1 -Type DWord
# Values: 0=off, 1=LAN only, 2=LAN+group, 3=LAN+internet, 99=simple (no P2P)
```

Note: major Windows feature updates can reset DODownloadMode. Included in drift-check.

## Hardening: Windows Recall (AI snapshot feature)

```powershell
$recallPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI'
if (-not (Test-Path $recallPath)) { New-Item -Path $recallPath -Force | Out-Null }
Set-ItemProperty $recallPath -Name 'DisableAIDataAnalysis' -Value 1 -Type DWord
Set-ItemProperty $recallPath -Name 'AllowRecallEnablement' -Value 0 -Type DWord
```

Both keys needed: DisableAIDataAnalysis blocks the feature; AllowRecallEnablement=0 prevents
users from re-enabling it via Settings.

---



## sshd_config: what NOT to add

OpenSSH on Windows (the built-in capability, not a third-party install) is strict about
unknown or unsupported directives. Adding unsupported options causes **Error 1067** (process
terminated unexpectedly) on `Start-Service sshd`.

**Directives that break Windows OpenSSH sshd:**
- `MaxSessions 10` — not supported in Windows OpenSSH build
- `MaxStartups 10` — not supported

Symptom: sshd starts, then immediately crashes with Error 1067. SSH goes down mid-session.

**Diagnosis:**
```powershell
# Run locally in admin PowerShell
sshd -t
# Shows the exact config line causing the error
```

**Fix:** open `C:\ProgramData\ssh\sshd_config` in notepad, remove the offending lines, then:
```powershell
Start-Service sshd
```

**Safe directives confirmed working on Windows OpenSSH:**
```
PubkeyAuthentication yes
PasswordAuthentication yes
Subsystem sftp sftp-server.exe
```

Leave everything else at defaults. The Windows OpenSSH implementation is a subset of OpenSSH;
Linux man page options often don't apply.

---

## PowerShell 7 setup

PS7 is more robust for complex scripts than PS5 (better error handling, no inline length limits,
actively maintained). Install via direct MSI from GitHub releases:

```bash
# Get latest release MSI URL
curl -s https://api.github.com/repos/PowerShell/PowerShell/releases/latest | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print(a['browser_download_url']) for a in d.get('assets',[]) if 'win-x64.msi' in a['name']]"

# Download and install (silent, SYSTEM-level)
ssh admin@host "powershell -Command \"Invoke-WebRequest -Uri 'MSI_URL' -OutFile 'C:\\Temp\\PS7.msi' -UseBasicParsing\""
ssh admin@host "msiexec /i C:\Temp\PS7.msi /qn ADD_EXPLORER_CONTEXT_MENU_OPENPOWERSHELL=1 ENABLE_PSREMOTING=1 REGISTER_MANIFEST=1"
```

Verify:
```bash
ssh admin@host "\"C:\\Program Files\\PowerShell\\7\\pwsh.exe\" -Command \"\$PSVersionTable.PSVersion\""
```

Set execution policy in PS7:
```bash
ssh admin@host "\"C:\\Program Files\\PowerShell\\7\\pwsh.exe\" -Command \"Set-ExecutionPolicy RemoteSigned -Scope LocalMachine -Force\""
```

Update all scheduled tasks to use `pwsh.exe` instead of `powershell.exe` for better reliability.

Note: PS7 is installed on DESKTOP-PH4F2DK. Re-check `$PSVersionTable.PSVersion` — do not assume v7.4.6. Maintenance tasks on this PC run under pwsh.exe.

## GPU/CPU validation

### Quick GPU health check
```bash
ssh admin@host "\"C:\\Windows\\System32\\nvidia-smi.exe\" --query-gpu=name,driver_version,power.limit,clocks.current.graphics,temperature.gpu --format=csv,noheader"
```

Expected values for this PC's RTX 2080 are in `references/desktop-oc-profile.md` (this-machine-only).

### Check HAGS and MMCSS
```bash
ssh admin@host "reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers /v HwSchMode"
# 0x2 = HAGS enabled

ssh admin@host "schtasks /query /tn NvidiaMaxPowerLimit2 /fo list | findstr /i status"
# Status: Ready = good
```

---

## CPU overclock crash diagnosis (this-machine: i7-9700K / Z390 on DESKTOP-PH4F2DK)

Login crash (green screen immediately after login) diagnostic:

```bash
# Get recent crash events
ssh admin@host "wevtutil qe System /c:5 /rd:true /f:text /q:\"*[System[EventID=41 or EventID=1001]]\""
```

Interpretation:
- Stop code 0x1E (KMODE_EXCEPTION_NOT_HANDLED) = CPU voltage insufficient, NOT a GPU issue
- Event 41 only, no stop code = hard crash / instant power failure = voltage severely insufficient
- Green screen = how Windows shows BSODs with NVIDIA drivers (not a GPU indicator)

Stable clocks/voltages/BIOS: `references/desktop-oc-profile.md` (this-machine-only). Do not copy Vcore, ratio, PL, BIOS version, Afterburner offsets, or IPs to another board.

If crashes persist at any voltage:
1. Disable all startup items (Afterburner, GPU power tasks) to isolate the crash source
2. Login-time crash != boot crash; it's caused by the login power spike
3. Afterburner applying OC profile at startup can cause green screen independent of CPU stability

---

## Event log queries

Crash EventID 41/1001 query is in the CPU OC section above. General critical/error + minidumps:
```bash
ssh admin@host "wevtutil qe System /c:20 /rd:true /f:text /q:\"*[System[Level<=2]]\""
ssh admin@host "wevtutil qe Application /c:20 /rd:true /f:text /q:\"*[System[Level<=2]]\""
ssh admin@host "dir C:\\Windows\\Minidump"
```

## References
- `references/new-machine-bootstrap.md` — adding a new Tailscale Windows machine: probe, cred check, username discovery, UAC deadlock, SSH enablement one-liner
- `references/desktop-oc-profile.md` — BIOS/OC/GPU profile for DESKTOP-PH4F2DK (this-machine-only; read before clock or BIOS changes)
- `references/privacy-audit-scripts.md` — privacy/security audit1–3 + 32-check verify-all.ps1
- `references/rmdir-incident.md` — `$`-folder rmdir expansion incident
- `references/system-audit-methodology.md` — read-first audit workflow and drift-check
- `scripts/desktop-drift-check.ps1` — this-machine drift-check script (re-verify task exists; do not trust install date)
- `references/windows-maintenance-tasks.md` — scheduled cleanup/DISM/driver tasks
- `references/nvidia-app-reinstall.md` — NVIDIA App ghost-folder reinstall (resolve version from registry)
- `references/startup-and-orphans.md` — this-machine startup/orphan/AppData cleanup
- `references/brother-printer-firmware-update.md` — this-LAN Brother printer via this Windows box (not general Windows admin)
