# Windows Privacy & Security Audit Scripts

Reusable PowerShell audit scripts for DESKTOP-PH4F2DK. Developed Sep 4 2026.
Run via scp + pwsh pattern (never inline PS with $ variables over SSH).

## Workflow

```bash
# Write scripts locally, scp over, run, scp results back
write_file("/tmp/audit1.ps1", audit1_content)
write_file("/tmp/audit2.ps1", audit2_content)
write_file("/tmp/audit3.ps1", audit3_content)

scp /tmp/audit1.ps1 /tmp/audit2.ps1 /tmp/audit3.ps1 admin@100.88.247.70:C:/Temp/
ssh admin@100.88.247.70 "pwsh -ExecutionPolicy Bypass -File C:\Temp\audit1.ps1"
ssh admin@100.88.247.70 "pwsh -ExecutionPolicy Bypass -File C:\Temp\audit2.ps1"
ssh admin@100.88.247.70 "pwsh -ExecutionPolicy Bypass -File C:\Temp\audit3.ps1"
scp admin@100.88.247.70:C:/Temp/audit{1,2,3}.txt /tmp/
```

All scripts write output to C:\Temp\auditN.txt so results survive disconnection.
Run audit1 and audit2 sequentially (audit2 has a noisy Get-Service permission error on
IsolationSession/Sense/WaaSMedicSvc — safe to ignore, still exits 0).

---

## Script 1: System baseline — UAC, telemetry, Defender, firewall, ports, SSH, WinRM, shares

```powershell
# audit1.ps1 — system info, UAC, telemetry, Defender, firewall, listening ports, WinRM, SSH config
$out = [System.Collections.Generic.List[string]]::new()

$out.Add("=== SYSTEM INFO ===")
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$out.Add("Host: $($cs.Name)  OS: $($os.Caption) $($os.Version)")
$out.Add("RAM: $([math]::Round($cs.TotalPhysicalMemory/1GB,1)) GB")

$out.Add("=== UAC SETTINGS ===")
$uac = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
$out.Add("ConsentPromptBehaviorAdmin: $($uac.ConsentPromptBehaviorAdmin)")
$out.Add("EnableLUA: $($uac.EnableLUA)")
$out.Add("PromptOnSecureDesktop: $($uac.PromptOnSecureDesktop)")

$out.Add("=== TELEMETRY / PRIVACY SETTINGS ===")
$telPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
if (Test-Path $telPath) {
    $tval = (Get-ItemProperty $telPath -EA SilentlyContinue).AllowTelemetry
    $out.Add("AllowTelemetry (Policy): $tval  (0=Off, 1=Basic/Required)")
} else { $out.Add("AllowTelemetry (Policy): NOT SET (no policy key)") }
$cortana = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search" -EA SilentlyContinue).AllowCortana
$out.Add("AllowCortana (Policy): $cortana")
$advid = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -EA SilentlyContinue).Enabled
$out.Add("AdvertisingInfo Enabled: $advid  (0=Off is good)")
$act = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -EA SilentlyContinue).PublishUserActivities
$out.Add("PublishUserActivities: $act  (0=Off is good)")

$out.Add("=== WINDOWS DEFENDER ===")
$wdStatus = Get-MpComputerStatus -EA SilentlyContinue
if ($wdStatus) {
    $out.Add("RealTimeProtection: $($wdStatus.RealTimeProtectionEnabled)")
    $out.Add("AntivirusEnabled: $($wdStatus.AntivirusEnabled)")
    $out.Add("BehaviorMonitor: $($wdStatus.BehaviorMonitorEnabled)")
    $out.Add("TamperProtection: $($wdStatus.TamperProtectionSource)")
    $out.Add("SignaturesUpdated: $($wdStatus.AntivirusSignatureLastUpdated)")
    $out.Add("DownloadScan: $($wdStatus.IoavProtectionEnabled)")
}

$out.Add("=== FIREWALL ===")
Get-NetFirewallProfile | ForEach-Object {
    $out.Add("  $($_.Name): Enabled=$($_.Enabled)  In=$($_.DefaultInboundAction)  Out=$($_.DefaultOutboundAction)")
}

$out.Add("=== LISTENING TCP ===")
Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,@{N='PID';E={$_.OwningProcess}} | Sort-Object LocalPort | ForEach-Object {
    $proc = Get-Process -Id $_.PID -EA SilentlyContinue
    $out.Add("  $($_.LocalAddress):$($_.LocalPort)  PID=$($_.PID)  $($proc.Name)")
}

$out.Add("=== WINRM ===")
$winrm = Get-Service WinRM -EA SilentlyContinue
$out.Add("WinRM: Status=$($winrm.Status)  StartType=$($winrm.StartType)")
$out.Add((winrm enumerate winrm/config/listener 2>&1))

$out.Add("=== SSH CONFIG ===")
Get-Content "C:\ProgramData\ssh\sshd_config" -EA SilentlyContinue | Where-Object {$_ -notmatch '^\s*#' -and $_ -ne ''} | ForEach-Object { $out.Add("  $_") }

$out.Add("=== RDP ===")
$rdp = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server").fDenyTSConnections
$nla = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -EA SilentlyContinue).UserAuthentication
$out.Add("fDenyTSConnections: $rdp  (1=Disabled)")
$out.Add("NLA: $nla  (1=Required)")

$out.Add("=== SHARES ===")
Get-SmbShare | Select-Object Name,Path,Description | ForEach-Object { $out.Add("  $($_.Name)  $($_.Path)") }

$out.Add("=== AV in SecurityCenter2 ===")
Get-CimInstance -Namespace root\SecurityCenter2 -ClassName AntiVirusProduct -EA SilentlyContinue | ForEach-Object {
    $out.Add("  AV: $($_.displayName)  State: $($_.productState)")
}

$out | Out-File C:\Temp\audit1.txt -Encoding utf8
Write-Output "audit1 done"
```

---

## Script 2: Tasks, startup, services, VPN, network, DNS, BitLocker, permissions

```powershell
# audit2.ps1
$out = [System.Collections.Generic.List[string]]::new()

$out.Add("=== SCHEDULED TASKS (NON-MICROSOFT) ===")
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | Select-Object TaskName,TaskPath,State | Sort-Object TaskPath | ForEach-Object {
    $out.Add("  [$($_.State)] $($_.TaskPath)$($_.TaskName)")
}

$out.Add("=== STARTUP ENTRIES ===")
$out.Add("-- HKLM Run --")
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -EA SilentlyContinue | Get-Member -MemberType NoteProperty | Where-Object {$_.Name -notmatch '^PS'} | ForEach-Object {
    $val = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run").$($_.Name)
    $out.Add("  $($_.Name) = $val")
}
$out.Add("-- HKCU Run --")
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -EA SilentlyContinue | Get-Member -MemberType NoteProperty | Where-Object {$_.Name -notmatch '^PS'} | ForEach-Object {
    $val = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run").$($_.Name)
    $out.Add("  $($_.Name) = $val")
}
$out.Add("-- Startup Folder --")
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -EA SilentlyContinue | ForEach-Object { $out.Add("  $($_.Name)") }

$out.Add("=== PROTONVPN ===")
Get-Service -Name "ProtonVPNService","ProtonVPN WireGuard" -EA SilentlyContinue | ForEach-Object { $out.Add("  $($_.Name): $($_.Status) / $($_.StartType)") }

$out.Add("=== NETWORK ADAPTERS + DNS ===")
Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | ForEach-Object {
    $dns = (Get-DnsClientServerAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -EA SilentlyContinue).ServerAddresses -join ", "
    $ip = (Get-NetIPAddress -InterfaceIndex $_.ifIndex -EA SilentlyContinue | Where-Object {$_.AddressFamily -eq 'IPv4'}).IPAddress -join ", "
    $out.Add("  $($_.Name) [$($_.InterfaceDescription)]")
    $out.Add("    DNS=$dns  IP=$ip")
}

$out.Add("=== DoH REGISTRY ===")
$doh = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters" -EA SilentlyContinue).EnableAutoDoh
$out.Add("EnableAutoDoh: $doh  (2=Auto-detect is good; absent=off)")

$out.Add("=== ACTIVE CONNECTIONS (outbound) ===")
Get-NetTCPConnection -State Established | Where-Object {$_.RemoteAddress -notin @('127.0.0.1','::1')} | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,@{N='PID';E={$_.OwningProcess}} | Sort-Object RemoteAddress | ForEach-Object {
    $proc = Get-Process -Id $_.PID -EA SilentlyContinue
    $out.Add("  $($_.LocalAddress):$($_.LocalPort) -> $($_.RemoteAddress):$($_.RemotePort)  $($proc.Name)")
}

$out.Add("=== BITLOCKER ===")
Get-BitLockerVolume -EA SilentlyContinue | ForEach-Object {
    $out.Add("  $($_.MountPoint): ProtectionStatus=$($_.ProtectionStatus)  Method=$($_.EncryptionMethod)")
}

$out.Add("=== APP PERMISSIONS ===")
foreach ($k in @('webcam','microphone','location')) {
    $val = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\$k" -EA SilentlyContinue).Value
    $out.Add("  $k: $val")
}

$out.Add("=== VBS / CREDENTIAL GUARD ===")
$vbs = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\DeviceGuard" -EA SilentlyContinue).EnableVirtualizationBasedSecurity
$out.Add("VBS: $vbs  (1=Enabled)")

$out.Add("=== EXECUTION POLICY ===")
Get-ExecutionPolicy -List | ForEach-Object { $out.Add("  $($_.Scope): $($_.ExecutionPolicy)") }

$out | Out-File C:\Temp\audit2.txt -Encoding utf8
Write-Output "audit2 done"
```

---

## Script 3: Firewall rules (custom), autorun, DoH detail, task details, spooler, clipboard

```powershell
# audit3.ps1
$out = [System.Collections.Generic.List[string]]::new()

$out.Add("=== AUTORUN ===")
$ar1 = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" -EA SilentlyContinue).NoDriveTypeAutoRun
$ar2 = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" -EA SilentlyContinue).NoDriveTypeAutoRun
$out.Add("HKCU NoDriveTypeAutoRun: $ar1  (255=all disabled)")
$out.Add("HKLM NoDriveTypeAutoRun: $ar2  (255=all disabled)")

$out.Add("=== FIREWALL INBOUND RULES (custom) ===")
Get-NetFirewallRule | Where-Object {$_.Enabled -eq 'True' -and $_.Direction -eq 'Inbound' -and $_.Group -notlike 'Core Networking*' -and $_.Group -notlike '@*'} | Select-Object DisplayName,Profile,Action,@{N='Port';E={(Get-NetFirewallPortFilter -AssociatedNetFirewallRule $_ -EA SilentlyContinue).LocalPort}} | Sort-Object DisplayName | ForEach-Object {
    $out.Add("  $($_.DisplayName)  Profile=$($_.Profile)  Action=$($_.Action)  Port=$($_.Port)")
}

$out.Add("=== CLIPBOARD ===")
$cb = (Get-ItemProperty "HKCU:\Software\Microsoft\Clipboard" -EA SilentlyContinue).EnableClipboardHistory
$cbs = (Get-ItemProperty "HKCU:\Software\Microsoft\Clipboard" -EA SilentlyContinue).CloudClipboardEnabled
$out.Add("ClipboardHistory: $cb  CloudSync: $cbs")

$out.Add("=== PRINT SPOOLER ===")
$sp = Get-Service Spooler
$out.Add("Spooler: Status=$($sp.Status)  StartType=$($sp.StartType)")

$out.Add("=== TELEMETRY POLICY (raw) ===")
$dcp = Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -EA SilentlyContinue
$dcp | Get-Member -MemberType NoteProperty | Where-Object {$_.Name -notmatch '^PS'} | ForEach-Object {
    $out.Add("  $($_.Name) = $($dcp.$($_.Name))")
}

$out.Add("=== FEEDBACK ===")
$fn2 = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Siuf\Rules" -EA SilentlyContinue).NumberOfSIUFInPeriod
$out.Add("SIUF NumberOfSIUFInPeriod: $fn2  (0=disabled)")

$out | Out-File C:\Temp\audit3.txt -Encoding utf8
Write-Output "audit3 done"
```

---

## Known issues / gotchas

- Get-Service on IsolationSession, Sense, WaaSMedicSvc, WMPNetworkSvc throws PermissionDenied
  even as admin — safe to ignore, exits 0.
- EnableAutoDoh returns null if the key doesn't exist (key absence = DoH disabled). Handle with
  `-EA SilentlyContinue` and null-check before calling .GetType().
- WinRM listener `enumerate` output is multi-line and goes into the result file fine but looks
  odd when put in a List[string] — that's cosmetic.
- SoftLandingCreativeManagementTask action Execute field shows empty when the backing binary
  has been deleted. Task scaffold remains; still safe to delete via schtasks.

## NetBIOS disable — WMI method fails over SSH (use registry instead)

`SetTcpipNetbios()` on a `Win32_NetworkAdapterConfiguration` object fails with
"does not contain a method named 'SetTcpipNetbios'" when called over SSH because
the object comes back deserialized (not a live WMI object). Happens with both
`Get-WmiObject` and `Get-CimInstance` patterns. Use the registry directly:

```powershell
# Works reliably over SSH — no WMI method invocation needed
$base = "HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
Get-ChildItem $base -EA SilentlyContinue | ForEach-Object {
    Set-ItemProperty -Path $_.PSPath -Name "NetbiosOptions" -Value 2 -Type DWord -Force
}
# Verify
Get-ChildItem $base | ForEach-Object {
    $v = (Get-ItemProperty $_.PSPath).NetbiosOptions
    "$($_.PSChildName): NetbiosOptions=$v  (expected 2)"
}
```

NetbiosOptions: 0=default (DHCP decides), 1=enable, 2=disable explicitly.
Default 0 leaves port 137/138/139 open if DHCP doesn't disable it.
Takes effect immediately for new connections; no reboot required.

## DoH per-interface enforcement — UI step may not set ConfigOptions correctly

After the user does Settings > Network > DNS > "Encrypted only", verify the key was created:

```powershell
$wifiIdx = (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*'} | Select-Object -First 1).ifIndex
$k1 = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig\1.1.1.1"
$k2 = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig\1.0.0.1"
(Get-ItemProperty $k1 -EA SilentlyContinue).ConfigOptions  # expect 2
(Get-ItemProperty $k2 -EA SilentlyContinue).ConfigOptions  # expect 2
```

If keys are absent, the UI step set DNS addresses but left encryption at "Unencrypted only"
or "Encrypted preferred". User must redo the Settings step and explicitly pick
"Encrypted only" from the dropdown. Alternatively, write the keys directly:

```powershell
# Direct registry enforcement (bypasses UI step entirely)
$wifiIdx = (Get-NetAdapter | Where-Object {$_.Name -like '*Wi-Fi*'} | Select-Object -First 1).ifIndex
$base = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig"
foreach ($server in @("1.1.1.1","1.0.0.1")) {
    $kp = "$base\$server"
    if (-not (Test-Path $kp)) { New-Item -Path $kp -Force | Out-Null }
    Set-ItemProperty -Path $kp -Name "DohTemplate" -Value "https://cloudflare-dns.com/dns-query" -Type String -Force
    Set-ItemProperty -Path $kp -Name "ConfigOptions" -Value 2 -Type DWord -Force
}
```

ConfigOptions=2 = "Encrypted only". This is what Windows creates internally when you
pick "Encrypted only" in the UI; writing it directly is equivalent.

## Full verification script (all 32 checks)

Run after any hardening batch to confirm all settings are in place:

```powershell
# verify-all.ps1 — checks all hardened settings from Sep 4 2026 session
$pass = 0; $fail = 0
function Check($label, $actual, $expected) {
    if ("$actual" -eq "$expected") { $script:pass++; Write-Output "[PASS] $label = $actual" }
    else { $script:fail++; Write-Output "[FAIL] $label = '$actual'  (expected '$expected')" }
}

Check "AutoRun HKLM" (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" -EA SilentlyContinue).NoDriveTypeAutoRun 255
Check "AutoRun HKCU" (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" -EA SilentlyContinue).NoDriveTypeAutoRun 255
Check "PromptOnSecureDesktop" (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System").PromptOnSecureDesktop 1
$wr = Get-Service WinRM
Check "WinRM Status" $wr.Status "Stopped"
Check "WinRM StartType" $wr.StartType "Manual"
Check "SoftLanding task gone" ((Get-ScheduledTask -TaskName "SoftLandingCreativeManagementTask" -EA SilentlyContinue) -eq $null) $true
$sp = Get-Service Spooler
Check "Spooler Status" $sp.Status "Stopped"
Check "Spooler StartType" $sp.StartType "Disabled"
Check "Chrome mDNS rule gone" ((Get-NetFirewallRule -DisplayName "Google Chrome (mDNS-In)" -EA SilentlyContinue) -eq $null) $true
Check "HNS rules gone" ((Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*HNS Container*"}).Count -eq 0) $true
Check "EnableAutoDoh" (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters" -EA SilentlyContinue).EnableAutoDoh 2
$wifiIdx = (Get-NetAdapter | Where-Object {$_.Name -like "*Wi-Fi*"} | Select-Object -First 1).ifIndex
Check "DoH 1.1.1.1 ConfigOptions" (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig\1.1.1.1" -EA SilentlyContinue).ConfigOptions 2
Check "DoH 1.0.0.1 ConfigOptions" (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig\1.0.0.1" -EA SilentlyContinue).ConfigOptions 2
Check "PublishUserActivities" (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -EA SilentlyContinue).PublishUserActivities 0
Check "DODownloadMode" (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -EA SilentlyContinue).DODownloadMode 1
Check "DisableAIDataAnalysis" (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI" -EA SilentlyContinue).DisableAIDataAnalysis 1
Check "LLMNR disabled" (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient" -EA SilentlyContinue).EnableMulticast 0
$nbBase = "HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
$nbFail = (Get-ChildItem $nbBase -EA SilentlyContinue) | Where-Object { (Get-ItemProperty $_.PSPath -EA SilentlyContinue).NetbiosOptions -ne 2 }
Check "NetBIOS all adapters" ($nbFail.Count -eq 0) $true
Check "UAC ConsentPromptBehaviorAdmin" (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System").ConsentPromptBehaviorAdmin 5
Check "RDP disabled" (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server").fDenyTSConnections 1
Check "Defender RTP" (Get-MpComputerStatus -EA SilentlyContinue).RealTimeProtectionEnabled $true
foreach ($g in @("56a863a9-875e-4185-98a7-b882c64b5ce5","9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2","e6db77e5-3df2-4cf1-b95a-636979351e5b")) {
    Check "ASR $($g.Substring(0,8))" (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows Defender\Windows Defender Exploit Guard\ASR\Rules" -EA SilentlyContinue).$g 1
}
Check "LSA RunAsPPL" (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa").RunAsPPL 2
Check "SMBv1 disabled" (Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -EA SilentlyContinue).State "Disabled"

Write-Output ""
Write-Output "=== RESULT: $pass passed, $fail failed ==="
```

Expected result: 32/32 pass after Sep 4 2026 hardening session.
