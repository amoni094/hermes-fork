# New Windows Machine Remote Bootstrap

Use when adding a Windows machine to Tailscale and needing remote access without prior SSH.

## Step 1: Probe reachability

```bash
tailscale status  # confirm machine is online
python3 -c "
import socket
for port in [22, 445, 3389, 5985]:
    s = socket.socket(); s.settimeout(5)
    r = s.connect_ex(('IP', port))
    print(f'Port {port}: {\"OPEN\" if r==0 else \"CLOSED\"}')
    s.close()
"
```

Note: `nc` and `nmap` may not be installed on this host — use the Python socket probe instead.
Expected baseline on a stock Windows machine: 445 open, everything else closed.

## Step 2: Confirm credentials via SMB

```bash
smbclient -U "admin%PASSWORD" //IP/IPC$ -c "exit" && echo OK
```

- Success (exit 0): credentials valid, session works over SMB.
- `STATUS_LOGON_FAILURE`: wrong username or password.
- `STATUS_ACCOUNT_DISABLED`: account exists but disabled (common for built-in Administrator).

## Step 3: Identify the actual username

If the account name is unknown, try common variants:
```bash
for user in admin Administrator User; do
  echo "=== $user ==="
  smbclient -U "${user}%" //IP/IPC$ -c "exit" 2>&1 | tail -1
done
```

For blank-password accounts:
```bash
smbclient -U "admin%" //IP/IPC$ -c "exit" 2>&1  # blank password = user%
```

If the account is a Microsoft account (email sign-in), the local username is the
first 5-20 chars of the email prefix — ask the user to check Start menu > account name,
or Settings > Accounts > Your Info.

**PITFALL: The local username that shows in the Start menu (e.g. "Natasha") is not necessarily
the Windows account name used for authentication.** Always confirm with `net user` once you have
execution access, or ask the user to read Settings > Accounts.

## Step 4: Test remote execution (impacket)

Install if missing: `pip install impacket` (scripts land at `~/.local/bin/`).

Try in order (each handles different UAC/service states):
```bash
psexec.py 'USER:PASS@IP' "hostname"
wmiexec.py 'USER:PASS@IP' "hostname"
atexec.py 'USER:PASS@IP' "hostname"
```

Common failure signatures:
- `STATUS_LOGON_FAILURE`: credentials wrong
- `share 'ADMIN$' is not writable`: credentials OK, UAC token filtering blocking (local non-built-in admin)
- `rpc_s_access_denied`: WMI/RPC path blocked by UAC — same root cause as above

## Step 5: Break the UAC deadlock

If credentials are correct but all three impacket tools fail with access denied,
the machine is using a local non-built-in admin account and UAC remote token filtering
is active. This cannot be bypassed remotely — physical access or WinRM enablement required.

### Option A: Enable WinRM (user at machine — one admin CMD paste)

WinRM is faster to enable than SSH and does not require a download:
```cmd
powershell -Command "Enable-PSRemoting -Force; netsh advfirewall firewall add rule name='WinRM' dir=in action=allow protocol=TCP localport=5985; winrm quickconfig -q"
```

If the firewall rule doesn't stick, also disable it entirely for home machines:
```cmd
netsh advfirewall set allprofiles state off
```

Then test from Linux:
```bash
wmiexec.py 'USER:PASS@IP' "hostname"
```

**Enables without any download — fastest path when connectivity is confirmed.**

### Option B: Enable SSH (user at machine — one admin CMD paste)

```cmd
powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd; Set-Service -Name sshd -StartupType Automatic; New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"
```

**PITFALL: `Add-WindowsCapability` requires internet access and Windows Update to be functional.**
If port 22 is still closed after running this, the capability download failed silently. Fall back
to Option A (WinRM) which requires no download.

**CMD paste tip: right-click to paste (not Ctrl+V or Ctrl+Shift+V).** Ensure the title bar says
"Administrator: Command Prompt" — elevation is required. A UAC popup asking "Do you want to
allow..." must be clicked Yes.

## Step 6: Enable built-in Administrator account (once execution access works)

The built-in Administrator account is disabled by default on Windows. It bypasses UAC token
filtering over network SMB — useful for long-term remote access even when wmiexec works.

```bash
wmiexec.py 'admin:PASS@IP' "net user Administrator NEWPASS /active:yes"
# Verify it's now active:
wmiexec.py 'Administrator:NEWPASS@IP' "whoami"
```

Check first whether it's disabled:
```bash
wmiexec.py 'admin:PASS@IP' "net user Administrator"
# Look for: Account active  Yes/No
```

## Step 7: Set up passwordless SSH via key (durable access)

For long-term passwordless access, push your public key via SMB (no execution access needed):

```bash
# Push key via SMB share (works even with UAC restricting execution)
echo "$(cat ~/.ssh/id_ed25519.pub)" > /tmp/administrators_authorized_keys
smbclient -U "Administrator%PASS" //IP/C$ -c \
  "mkdir ProgramData\ssh; put /tmp/administrators_authorized_keys ProgramData\ssh\administrators_authorized_keys"
# NT_STATUS_OBJECT_NAME_COLLISION on mkdir is fine (directory already existed)
```

For Administrator account, keys go to `C:\ProgramData\ssh\administrators_authorized_keys`
(not the per-user `~/.ssh/authorized_keys` location).

Then test:
```bash
ssh -i ~/.ssh/id_ed25519 Administrator@IP "whoami"
```

Windows OpenSSH often accepts the key without needing to set `icacls` permissions first;
skip the `icacls` step and test before adding it (it frequently times out via wmiexec anyway).

## Step 8: Verify SSH works

```bash
ssh Administrator@IP "hostname && whoami"
```

If SSH connects but WinRM/RDP are still closed, that is fine — SSH is sufficient for
all remote admin tasks.

## Notes

- Built-in `Administrator` account (distinct from any account *named* 'admin') bypasses
  UAC token filtering over network SMB, but Windows disables it by default.
  `STATUS_ACCOUNT_DISABLED` on that name confirms it's disabled.
- wmiexec.py prompts for a password interactively if credentials are passed incorrectly;
  always use the `'user:pass@ip'` single-argument form to avoid the interactive prompt.
- Microsoft account usernames may be truncated (e.g. 'natas' for 'natasha@...');
  blank-password local accounts often respond to `USERNAME%` with no password string.
- wmiexec.py commands that run PowerShell inline can time out if the PowerShell command
  takes >20s or opens a GUI. Prefer shorter individual commands over chained PowerShell.
- Use `smbclient` to write files to the machine directly when wmiexec times out — it
  bypasses execution restrictions and doesn't time out on file transfers.

## Performance and bloat removal for home machines (email/browser/Office use)

Apply after SSH access is established. Targeted at non-gaming consumer machines.

### Step 1: Collect audit data (run individually — compound commands return empty via SSH)

```bash
IP=100.121.155.11
ssh -i ~/.ssh/id_ed25519 Administrator@$IP "tasklist /fo csv /nh"
ssh Administrator@$IP "reg query \"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\""
ssh Administrator@$IP "reg query \"HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run\""
ssh Administrator@$IP "powershell -Command \"Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location | Format-List\""
ssh Administrator@$IP "powershell -Command \"Get-PhysicalDisk | Select-Object MediaType,Size\""
ssh Administrator@$IP "powershell -Command \"Get-EventLog -LogName System -EntryType Error -Newest 20 | Select-Object TimeGenerated,Source,Message | Format-List\""
```

**PITFALL: `wmic` is not installed on Windows 11 — use CIM (`Get-CimInstance`) instead.**
CIM commands must be run via `powershell -Command` through SSH.

**PITFALL: Compound commands (`cmd1 && cmd2`, `cmd | findstr`) passed to SSH return empty output.**
Run each command in a separate SSH call. Only single, non-piped commands reliably return output.

### Step 2: Remove adware/PUP scheduled tasks

```bash
# SoftLanding (adware)
ssh Administrator@$IP "schtasks /delete /tn \"\\SoftLanding\\...\" /f"
# PCHelpSoft Driver Updater (PUP)
ssh Administrator@$IP "schtasks /delete /tn \"PCHelpSoft Driver Updater\" /f"
```

### Step 3: Disable bloat services (ASUS gaming machines are the worst offenders)

See `references/startup-and-orphans.md` — ASUS OEM bloat section for full service list.

### Step 4: Clean up startup registry entries

```bash
# Safe to remove on non-gaming home machines:
ssh Administrator@$IP "reg delete \"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" /v AdobeAAMUpdater-1.0 /f"
ssh Administrator@$IP "reg delete \"HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run\" /v \"Acrobat Assistant 8.0\" /f"
ssh Administrator@$IP "reg delete \"HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run\" /v BrotherSoftwareUpdateNotification /f"
ssh Administrator@$IP "reg delete \"HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run\" /v TeamsMachineInstaller /f"
```

### Step 5: Disable SysMain if C: is SSD

```bash
ssh Administrator@$IP "powershell -Command \"Get-PhysicalDisk | Select-Object MediaType,Size\""
# If SSD:
ssh Administrator@$IP "sc config SysMain start= disabled && sc stop SysMain"
```

### Step 6: Set visual effects for performance (per-user)

VisualFXSetting 2 = "Best Performance" (disables animations, shadows, thumbnails).
Apply to the primary user's SID:

```bash
# Get user's SID: ssh Administrator@$IP "powershell -Command \"(New-Object Security.Principal.NTAccount 'Natasha').Translate([Security.Principal.SecurityIdentifier]).Value\""
ssh Administrator@$IP "reg add \"HKU\\SID-HERE\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects\" /v VisualFXSetting /t REG_DWORD /d 2 /f"
```

### Step 7: Adversarial verification

```bash
# Confirm deleted tasks are gone (expect: ERROR: The system cannot find the file specified.)
ssh Administrator@$IP "schtasks /query /tn \"PCHelpSoft Driver Updater\" 2>&1"
# Confirm services disabled
for svc in SysMain AGMService "ROG Live Service" LightingService; do
  ssh Administrator@$IP "sc qc \"$svc\" | findstr START_TYPE"
done
# Confirm startup keys removed
ssh Administrator@$IP "reg query \"HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run\""
# Confirm visual effects set
ssh Administrator@$IP "reg query \"HKU\\SID\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\VisualEffects\" /v VisualFXSetting"
```

---

## Machine inventory

| Name | Tailscale IP | OS | Credentials | Notes |
|------|--------------|----|-------------|-------|
| desktop-naihles | 100.121.155.11 | Windows 11 Pro | Administrator:Gunn1967 | Natasha's desktop; WinRM+SSH open; passwordless SSH configured; security pass done. Python 3.11.9 + Playwright/Chromium installed at `C:\Users\Administrator\AppData\Local\Programs\Python\Python311`. Telstra LH1000 router at 192.168.0.1 — neither 'Telstra' nor 'Gunn1967' login works; password unknown, must ask Natasha or check modem label. |
| desktop-l5hdmr9 | 100.120.172.13 | Windows | Natasha/unknown | Mum's TV laptop; WinRM partially configured; no SSH yet; credentials TBD |

---

## Security and privacy hardening for non-technical user machines

Use after gaining SSH access. Applies to home machines used for email, browser, Office — not servers or gaming rigs.

### Run all at once via SSH

```bash
# Windows Update: auto-download and install at 3am, no forced reboots while user is logged in
ssh Administrator@IP "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU\" /v AUOptions /t REG_DWORD /d 4 /f && reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU\" /v NoAutoRebootWithLoggedOnUsers /t REG_DWORD /d 1 /f && reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU\" /v ScheduledInstallDay /t REG_DWORD /d 0 /f && reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU\" /v ScheduledInstallTime /t REG_DWORD /d 3 /f"

# Telemetry: minimum (security-only level 1)
ssh Administrator@IP "reg add \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection\" /v AllowTelemetry /t REG_DWORD /d 1 /f"

# Toast notifications off, Start menu suggestions off, OneDrive sync prompts off
ssh Administrator@IP "reg add \"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\PushNotifications\" /v ToastEnabled /t REG_DWORD /d 0 /f && reg add \"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager\" /v SystemPaneSuggestionsEnabled /t REG_DWORD /d 0 /f && reg add \"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager\" /v SubscribedContent-338389Enabled /t REG_DWORD /d 0 /f && reg add \"HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\" /v ShowSyncProviderNotifications /t REG_DWORD /d 0 /f"

# Disable RDP (attack surface reduction)
ssh Administrator@IP "reg add \"HKLM\\System\\CurrentControlSet\\Control\\Terminal Server\" /v fDenyTSConnections /t REG_DWORD /d 1 /f"

# Disable Guest account, disable DiagTrack telemetry service, disable RemoteRegistry
ssh Administrator@IP "net user Guest /active:no && sc config DiagTrack start= disabled && sc stop DiagTrack && sc config RemoteRegistry start= disabled"
```

### Harden SSH: disable password auth (key-only)

After passwordless SSH is confirmed working, disable password login to prevent brute-force:

```bash
# Fetch sshd_config, set PasswordAuthentication no, push back via SMB
ssh -i ~/.ssh/id_ed25519 Administrator@IP "type C:\\ProgramData\\ssh\\sshd_config" \
  | sed 's/#PasswordAuthentication yes/PasswordAuthentication no/' \
  > /tmp/sshd_config_patched
smbclient -U "Administrator%PASS" //IP/C$ -c "put /tmp/sshd_config_patched ProgramData\\ssh\\sshd_config"
# Restart sshd to apply
ssh -i ~/.ssh/id_ed25519 Administrator@IP "net stop sshd && net start sshd && echo OK"
# Verify key still works
ssh -i ~/.ssh/id_ed25519 Administrator@IP "whoami"
```

**PITFALL: PowerShell Set-Content via wmiexec/SSH often returns empty and fails silently.**
Always use the fetch-patch-push-via-smbclient pattern above instead of inline PowerShell file writes.

**PITFALL: Registry writes via SSH land in the Administrator session's HKCU, not the primary user's hive.**
Settings like ToastEnabled (notifications), VisualFXSetting, and ContentDeliveryManager keys must be written
to the primary user's SID under HKU, not HKCU. HKCU in an SSH session is the Administrator's hive.

```bash
# Get primary user's SID
ssh Administrator@IP "powershell -Command \"(New-Object Security.Principal.NTAccount 'USERNAME').Translate([Security.Principal.SecurityIdentifier]).Value\""
# Write to correct hive (replace SID-HERE)
ssh Administrator@IP "reg add \"HKU\\SID-HERE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\PushNotifications\" /v ToastEnabled /t REG_DWORD /d 0 /f"
```

### Firewall: ensure SSH/WinRM survive reboot

After re-enabling the firewall, confirm rules cover all network profiles (not just Private):

```bash
# Fix SSH rule to all profiles
ssh Administrator@IP "netsh advfirewall firewall set rule name=\"OpenSSH SSH Server (sshd)\" new profile=any"
# Add WinRM rule (all profiles)
ssh Administrator@IP "netsh advfirewall firewall add rule name=WinRM-In dir=in action=allow protocol=TCP localport=5985 profile=any"
# Verify
ssh Administrator@IP "netsh advfirewall firewall show rule name=\"OpenSSH SSH Server (sshd)\" | findstr Profiles"
```

**PITFALL: Default OpenSSH firewall rule created by Windows is Private profile only.**
If the machine's network is classified as Public (common on laptops or after Tailscale install),
SSH will be blocked post-reboot even though the rule exists. Always widen to `profile=any`.

**PITFALL: `netsh advfirewall set allprofiles state on` in the same SSH session drops the connection.**
Enable the firewall first in a subprocess that outlives the SSH session — use a scheduled task:
```bash
ssh Administrator@IP "schtasks /create /tn RestoreFirewall /tr \"netsh advfirewall set allprofiles state on\" /sc onstart /ru SYSTEM /rl highest /f"
```
Then reboot — the task fires at startup, restores the firewall with the rules already in place.
Alternatively, enable firewall from a separate terminal connection while keeping the SSH session open.

### Run Windows Update + driver update remotely

PSWindowsUpdate module runs under SYSTEM via scheduled task — the only reliable way since
running it directly via SSH raises Access Denied (E_ACCESSDENIED 0x80070005).

```bash
# Install PSWindowsUpdate module
ssh -i ~/.ssh/id_ed25519 Administrator@IP "powershell -Command \"Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope AllUsers; Install-Module PSWindowsUpdate -Force -Scope AllUsers\""

# Write the update script locally, upload via smbclient
cat > /tmp/wupdate.ps1 << 'EOF'
Import-Module PSWindowsUpdate
Get-WindowsUpdate -AcceptAll -Install -IgnoreReboot | Out-File C:\Windows\Temp\wu-log.txt
EOF
smbclient -U "Administrator%PASS" //IP/C$ -c "put /tmp/wupdate.ps1 Windows\Temp\wupdate.ps1"

# Create and run as SYSTEM scheduled task
ssh -i ~/.ssh/id_ed25519 Administrator@IP "schtasks /create /tn WinUpdateNow /tr \"powershell -ExecutionPolicy Bypass -File C:\\Windows\\Temp\\wupdate.ps1\" /sc once /st 00:00 /ru SYSTEM /rl highest /f"
ssh -i ~/.ssh/id_ed25519 Administrator@IP "schtasks /run /tn WinUpdateNow"

# Poll for results (takes several minutes)
ssh -i ~/.ssh/id_ed25519 Administrator@IP "type C:\\Windows\\Temp\\wu-log.txt"

# Verify all done
ssh -i ~/.ssh/id_ed25519 Administrator@IP "powershell -Command \"Import-Module PSWindowsUpdate; (Get-WindowsUpdate).Count\""  # expect 0

# Clean up
ssh -i ~/.ssh/id_ed25519 Administrator@IP "schtasks /delete /tn WinUpdateNow /f && del C:\\Windows\\Temp\\wupdate.ps1"
```

**PITFALL: `Get-WindowsUpdate -AcceptAll -Install` run directly via SSH returns Access Denied.**
Always run it as a SYSTEM scheduled task — SYSTEM has the WU service access that the SSH session lacks.

**NOTE: `/st 00:00` will warn if the time is already past midnight — this is harmless.**
Use `schtasks /run` immediately after creation; the warning does not prevent manual trigger.

### Install Sumatra PDF (lightweight, no background processes)

```bash
# Download installer
ssh -i ~/.ssh/id_ed25519 Administrator@IP "powershell -Command \"Invoke-WebRequest -Uri 'https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64-install.exe' -OutFile 'C:\\Windows\\Temp\\SumatraPDF.exe'\""

# Install silently
ssh -i ~/.ssh/id_ed25519 Administrator@IP "C:\\Windows\\Temp\\SumatraPDF.exe /install /s"

# PITFALL: Silent install lands in C:\Users\Administrator\AppData\Local\SumatraPDF\ — fragile path.
# Move to Program Files for stability:
ssh -i ~/.ssh/id_ed25519 Administrator@IP "mkdir \"C:\\Program Files\\SumatraPDF\" 2>nul"
ssh -i ~/.ssh/id_ed25519 Administrator@IP "copy \"C:\\Users\\administrator\\AppData\\Local\\SumatraPDF\\SumatraPDF.exe\" \"C:\\Program Files\\SumatraPDF\\SumatraPDF.exe\" /y"

# Register App Paths system-wide
ssh -i ~/.ssh/id_ed25519 Administrator@IP "reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\SumatraPDF.exe\" /ve /d \"C:\\Program Files\\SumatraPDF\\SumatraPDF.exe\" /f"

# Set .pdf association for primary user (replace SID-HERE)
ssh -i ~/.ssh/id_ed25519 Administrator@IP "reg add \"HKU\\SID-HERE\\Software\\Classes\\.pdf\" /ve /d \"SumatraPDF.pdf\" /f"
ssh -i ~/.ssh/id_ed25519 Administrator@IP "reg add \"HKU\\SID-HERE\\Software\\Classes\\SumatraPDF.pdf\\shell\\open\\command\" /ve /d \"\\\"C:\\Program Files\\SumatraPDF\\SumatraPDF.exe\\\" \\\"%1\\\"\" /f"

# Verify
ssh -i ~/.ssh/id_ed25519 Administrator@IP "reg query \"HKU\\SID-HERE\\Software\\Classes\\SumatraPDF.pdf\\shell\\open\\command\""
# Expect: C:\Program Files\SumatraPDF\SumatraPDF.exe
```

```bash
IP=100.121.155.11
ssh -i ~/.ssh/id_ed25519 Administrator@$IP "type C:\\ProgramData\\ssh\\sshd_config | findstr PasswordAuthentication" # expect: PasswordAuthentication no
ssh Administrator@$IP "sc query sshd | findstr STATE"                              # expect: RUNNING
ssh Administrator@$IP "sc qc sshd | findstr START_TYPE"                            # expect: AUTO_START
ssh Administrator@$IP "sc qc DiagTrack | findstr START_TYPE"                       # expect: DISABLED
ssh Administrator@$IP "sc qc RemoteRegistry | findstr START_TYPE"                  # expect: DISABLED
ssh Administrator@$IP "net user Guest | findstr /i active"                         # expect: No
ssh Administrator@$IP "reg query \"HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU\""  # expect: AUOptions=4
ssh Administrator@$IP "netsh advfirewall firewall show rule name=\"OpenSSH SSH Server (sshd)\" | findstr Profiles" # expect: Domain,Private,Public
ssh Administrator@$IP "schtasks /query /tn RestoreFirewall /fo LIST | findstr Status"  # expect: Ready
```
