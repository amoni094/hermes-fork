---
name: windows-remote-management
description: Use when managing Windows PCs remotely via SSH or Tailscale.
tags: [windows, ssh, tailscale, remote, updates, drivers]
---

# Windows Remote Management

Covers: connecting to Windows machines over Tailscale SSH, setting up passwordless key auth, running Windows Update remotely, and auditing devices/drivers.

## 0. Pre-flight: ensure tailscaled is running

Before any SSH attempt, confirm the local tailscaled daemon is up:

    sudo systemctl start tailscaled
    tailscale status

The daemon takes ~4s to warm up. Wait until the target node shows `-` (online), not `offline` or `NoState`. Without this, SSH connections time out silently — the symptom is indistinguishable from a firewall block or wrong IP.

## 1. Connecting via SSH (password first)

Windows OpenSSH Server (built-in or via `C:\Program Files\OpenSSH\`) supports password auth by default. Use `sshpass`:

    sshpass -p 'PASSWORD' ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password -o PubkeyAuthentication=no \
      USER@HOST "whoami"

Pitfall: Windows OpenSSH blocks SSH login for accounts with a blank password, even with `sshpass -p ''` and `-o PasswordAuthentication=yes`. The server returns `Permission denied` regardless. A blank-password Administrator account cannot be used for SSH without first setting a password locally on the machine. The only no-password remote path is a pre-installed public key (see Section 3).

Pitfall: A Windows Hello PIN is NOT the account password and cannot be used for SSH. Windows Hello PINs authenticate locally via TPM — they are never transmitted over the network. If the user gives you a 4–6 digit PIN, it is useless for `sshpass`. Ask for the account password or use key auth instead.

If the username is unknown, try common Windows usernames in a loop:

    for user in Administrator admin USER HOSTNAME; do
      result=$(sshpass -p 'PASSWORD' ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
        -o PreferredAuthentications=password -o PubkeyAuthentication=no \
        "$user@HOST" "whoami" 2>&1)
      echo "$user: $result"
    done

The `whoami` output reveals the machine name, e.g. `booran\admin`.

## 2. Transferring and running scripts

For any non-trivial PowerShell: write the script to `/tmp/`, scp it, then execute. Avoids shell-quoting hell.

    # Write script locally
    cat > /tmp/task.ps1 << 'EOF'
    Write-Host "Hello"
    EOF

    # Upload
    sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password -o PubkeyAuthentication=no \
      /tmp/task.ps1 USER@HOST:'C:\Windows\Temp\task.ps1'

    # Run
    sshpass -p 'PASSWORD' ssh USER@HOST \
      "powershell -ExecutionPolicy Bypass -File C:\\Windows\\Temp\\task.ps1"

Pitfall: Never try to inline multi-line PowerShell via SSH command-line quoting — single-quote vs double-quote escaping across bash→ssh→cmd→powershell layers causes parser errors. Always scp a .ps1 file and run it with `-File`.

## 3. Setting up passwordless SSH (key auth)

Windows OpenSSH has a non-obvious admin-account quirk and strict file permission requirements.

### Step 1 — Identify the actual home directory

The SSH username and the Windows profile folder often differ. Always confirm:

    powershell -Command "[System.Environment]::GetFolderPath('UserProfile')"

Example: username `admin`, home `C:\Users\alexe`. The `authorized_keys` must go in the ACTUAL profile folder.

### Step 2 — Write authorized_keys with correct encoding

Must be UTF-8 no BOM, Unix LF. `Add-Content` and `Out-File` write CRLF by default, which corrupts the key:

    $key = "ssh-ed25519 AAAA..."
    $authKeys = "$env:USERPROFILE\.ssh\authorized_keys"
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force | Out-Null
    [System.IO.File]::WriteAllText($authKeys, "$key`n", [System.Text.UTF8Encoding]::new($false))

Pitfall: Keys written with CRLF line endings are rejected by sshd silently — the log shows `Failed publickey` with the correct fingerprint. Always use `[System.IO.File]::WriteAllText` with `[System.Text.UTF8Encoding]::new($false)` (no BOM, LF only).

### Step 3 — Fix file permissions

Windows OpenSSH rejects authorized_keys if the ACL has extra entries. Only SYSTEM and the account owner:

    icacls $sshDir /inheritance:r
    icacls $sshDir /grant "SYSTEM:(OI)(CI)F"
    icacls $sshDir /grant "MACHINENAME\username:(OI)(CI)F"
    icacls $authKeys /inheritance:r
    icacls $authKeys /grant "SYSTEM:F"
    icacls $authKeys /grant "MACHINENAME\username:F"

Use `MACHINENAME\username` — bare usernames can fail silently on name conflicts.

### Step 4 — Fix sshd_config

Two blockers to check:

**a) Match Group administrators block** — Windows default sshd_config often ends with:

    Match Group administrators
        AuthorizedKeysFile __PROGRAMDATA__/ssh/administrators_authorized_keys

This overrides `AuthorizedKeysFile` for all admin users. Remove the block entirely:

    $content = $content -replace "(?s)`r?`nMatch Group administrators.*$", ""

**b) PubkeyAuthentication** — set explicitly:

    PubkeyAuthentication yes

**c) Write config back with no BOM:**

    [System.IO.File]::WriteAllText($conf, $content, [System.Text.UTF8Encoding]::new($false))
    Restart-Service sshd

### Step 5 — Test and add to ~/.ssh/config

    ssh -o BatchMode=yes -i ~/.ssh/id_ed25519 USER@HOST "whoami && hostname"

    Host SHORTNAME
        HostName IP_OR_TAILSCALE_IP
        User USERNAME
        IdentityFile ~/.ssh/id_ed25519
        StrictHostKeyChecking no

Pitfall: Editing `C:\Users\USERNAME\.ssh\authorized_keys` has no effect if the Match Group administrators block is active — sshd reads `C:\ProgramData\ssh\administrators_authorized_keys` instead. The sshd log shows the correct fingerprint but still rejects — check the Match block first.

Pitfall: Two OpenSSH versions can coexist: `C:\Windows\System32\OpenSSH\` (Windows built-in) and `C:\Program Files\OpenSSH\` (newer install). Run `(Get-WmiObject Win32_Service -Filter "Name='sshd'").PathName` to find which sshd.exe is actually running. Configure the sshd_config for THAT one only.

Pitfall: `$env:USERPROFILE` returns the profile of the PowerShell session's user. If the SSH session runs as `admin` but the profile is `C:\Users\alexe`, write authorized_keys to `C:\Users\alexe\.ssh\` — not to `C:\Users\admin\.ssh\`.

## 4. Debugging SSH key auth failures

Enable verbose sshd logging temporarily:

    # In C:\ProgramData\ssh\sshd_config: LogLevel DEBUG3
    Restart-Service sshd

    # After a failed attempt, read the event log:
    Get-WinEvent -LogName "OpenSSH/Operational" -MaxEvents 30 | Sort-Object TimeCreated |
        ForEach-Object { "[$($_.TimeCreated)] $($_.Message)" }

If the log shows `Failed publickey` with a fingerprint that matches `ssh-keygen -l -f ~/.ssh/id_ed25519.pub`, the key is seen but rejected for non-content reasons — check permissions and the Match block.

Restore log level when done:

    # Change: LogLevel DEBUG3 -> #LogLevel INFO
    Restart-Service sshd

## 5. Windows Update via SSH (remote)

The `Microsoft.Update.Session` COM object requires elevation. Calling it directly over SSH (even as admin) raises `E_ACCESSDENIED (0x80070005)`. The SYSTEM scheduled-task route is mandatory for install operations.

### Check pending updates (works without elevation)

    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
    Write-Host "Pending: $($result.Updates.Count)"
    $result.Updates | ForEach-Object { Write-Host "  [$($_.MsrcSeverity)] $($_.Title)" }

### Install via scheduled task as SYSTEM

Write the install logic to a .ps1 file (output results to a log file), schedule as SYSTEM, start, poll:

    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File C:\Windows\Temp\do_update.ps1"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName "HermesUpdateRun" -Action $action -Principal $principal -Force
    Start-ScheduledTask -TaskName "HermesUpdateRun"
    Start-Sleep -Seconds 30
    Get-Content C:\Windows\Temp\update_result.txt

    # Result codes: 2=Succeeded, 3=SucceededWithErrors, 4=Failed

Pitfall: `$session.CreateUpdateDownloader()` and `CreateUpdateInstaller()` raise `E_ACCESSDENIED` under a non-elevated SSH session even if the account is in Administrators. There is no workaround except running as SYSTEM via a scheduled task.

## 6. Device / driver audit

    # Devices with non-OK status
    Get-PnpDevice | Where-Object { $_.Status -ne "OK" } |
        Select-Object Status, FriendlyName, DeviceID

    # Driver version for a specific device
    Get-PnpDeviceProperty -DeviceId $_.DeviceID -KeyName "DEVPKEY_Device_DriverVersion"

### Interpreting "Unknown" status — false positives

These are normal, not actionable:
- `STORAGE\VOLUMESNAPSHOT\...` — VSS shadow copies
- `SWD\MMDEVAPI\...` — audio endpoint enumeration (multiple Speakers entries = multiple outputs)
- `SWD\PRINTENUM\...` — virtual print queues (OneNote, PDF, etc.)
- `SW\{96E080C7...}` — Microsoft Streaming Service Proxy

Actually investigate:
- `USB\VID_XXXX&PID_XXXX` with Unknown — USB device missing driver or physically disconnected
- Any hardware with `Error` status or error code 43 — real driver failure

## 7. Remote audio device troubleshooting

Use when an audio application (e.g. Jabra Direct) reports the device is "in a call or streaming" but no call is active.

### Step 1 — Find the blocking process

    Get-Process | Where-Object { $_.Name -match 'Softphone|jabra|Teams|Zoom|Slack|Discord|chrome|firefox|msedge|skype|webex' } | Select-Object Name, Id | Format-Table -AutoSize

Common culprits:
- **SoftphoneIntegrations** — Jabra's UC/softphone bridge; holds audio endpoint open even with no active call
- **firefox / chrome / msedge** — browsers with audio permissions granted to a web app
- Any conferencing app (Teams, Zoom, Slack) with background audio sessions

### Step 2 — Kill the blocking process

    Stop-Process -Name SoftphoneIntegrations -Force -ErrorAction SilentlyContinue
    Stop-Process -Name firefox -Force -ErrorAction SilentlyContinue
    # Or by PID: Stop-Process -Id NNNN -Force

Pitfall: `taskkill /F /IM firefox.exe` may fail to exit the process when Firefox is sandboxed or protected by a crash helper — verify with `Get-Process firefox` after. If processes persist, they may be respawning from a service; check for a parent process.

Pitfall: `Disable-PnpDevice` / `Enable-PnpDevice` will fail with `HRESULT 0x80041001` on ghost/Unknown-status audio endpoints — those are stale cached entries for disconnected devices and cannot be toggled remotely. They resolve on their own when the device physically reconnects.

### Step 3 — Restart Windows Audio services

If killing processes doesn't clear the state:

    Stop-Process -Name jabra-direct -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Restart-Service -Name Audiosrv -Force
    Restart-Service -Name AudioEndpointBuilder -Force

### Step 4 — Replug the USB device

If the "in a call" flag is stored on the device's own firmware (not in Windows), no amount of process-killing helps. Force a fresh audio session by replugging the USB dongle/device — this resets the Windows audio session for that endpoint with nothing attached to it yet.

### Checking active audio endpoints

    Get-PnpDevice | Where-Object { $_.Class -eq 'AudioEndpoint' -and $_.Status -eq 'OK' } | Select-Object FriendlyName | Format-Table -AutoSize

## 8. Windows PC as ICS/network bridge for TV

When a Windows PC shares its internet connection to a TV or other device via Ethernet (ICS — Internet Connection Sharing), all TV traffic routes through the PC. Key diagnostic consequences:

- **DNS for the TV comes from the PC**, not the router. Router-level DNS blocklists are irrelevant — the TV's DNS queries go through ICS's built-in DHCP/DNS (168.254.x.x range) and then out via whatever DNS the PC uses.
- **If the PC runs a VPN (NordVPN, ProtonVPN, etc.), ALL TV traffic exits through the VPN tunnel.** SBS On Demand, Stan, and other Australian streaming services geo-block non-AU VPN exit servers. If SBS works with VPN disconnected but not with it connected, the VPN exit country is the cause — switch to an Australian server.
- **Disconnecting the VPN breaks TV internet entirely** if ICS routing depends on the VPN interface. Test by switching the VPN to an AU server rather than disconnecting it.
- To change the TV's DNS without touching the router: set DNS on the PC's ICS-shared adapter (`netsh interface ip set dns "Ethernet" static 8.8.8.8 primary`), or set it globally (`Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Set-DnsClientServerAddress -ServerAddresses "8.8.8.8","8.8.4.4"`). Requires an elevated (admin) PowerShell — the `Get-NetAdapter` CIM cmdlet fails with "access to CIM resource not available" when run without elevation.

## 9. Known machines

See `references/machines.md` for machine inventory.
