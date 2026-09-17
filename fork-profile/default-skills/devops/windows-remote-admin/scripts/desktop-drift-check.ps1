# desktop-drift-check.ps1
# Weekly privacy/security drift check and auto-remediation for DESKTOP-PH4F2DK
# Task: \Maintenance\DesktopDriftCheck, Sundays 3am, SYSTEM
# Logs: C:\Temp\drift-check-YYYYMMDD-HHmmss.txt (auto-purged 30 days)
# Installed: Sep 4 2026 after full hardening session

$log = "C:\Temp\drift-check-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
$out = [System.Collections.Generic.List[string]]::new()
$pass = 0; $fail = 0; $fixed = 0

function Check($label, $actual, $expected, $note="") {
    if ("$actual" -eq "$expected") {
        $script:pass++
        $out.Add("[PASS] $label = $actual")
    } else {
        $script:fail++
        $out.Add("[DRIFT] $label = '$actual'  (expected '$expected')  $note")
    }
}

$out.Add("=== DESKTOP DRIFT CHECK - $(Get-Date) ===")
$out.Add("")

# 1. WinRM - stop if running
$wr = Get-Service WinRM
Check "WinRM Status" $wr.Status "Stopped"
Check "WinRM StartType" $wr.StartType "Manual"
if ($wr.Status -ne "Stopped") {
    Stop-Service WinRM -Force -EA SilentlyContinue
    Set-Service WinRM -StartupType Manual -EA SilentlyContinue
    $fixed++; $out.Add("  -> Stopped WinRM and set to Manual")
}

# 2. Spooler
$sp = Get-Service Spooler
Check "Spooler Status" $sp.Status "Stopped"
Check "Spooler StartType" $sp.StartType "Disabled"
if ($sp.Status -ne "Stopped" -or $sp.StartType -ne "Disabled") {
    Stop-Service Spooler -Force -EA SilentlyContinue
    Set-Service Spooler -StartupType Disabled -EA SilentlyContinue
    $fixed++; $out.Add("  -> Stopped and disabled Spooler")
}

# 3. AutoRun
$ar = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" -EA SilentlyContinue).NoDriveTypeAutoRun
Check "AutoRun HKLM" $ar 255
if ($ar -ne 255) {
    reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f | Out-Null
    $fixed++; $out.Add("  -> Restored AutoRun HKLM=255")
}

# 4. PromptOnSecureDesktop
$sd = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System").PromptOnSecureDesktop
Check "PromptOnSecureDesktop" $sd 1
if ($sd -ne 1) {
    Set-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name PromptOnSecureDesktop -Value 1 -Type DWord -Force
    $fixed++; $out.Add("  -> Restored PromptOnSecureDesktop=1")
}

# 5. DoH registry
$doh = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters" -EA SilentlyContinue).EnableAutoDoh
Check "EnableAutoDoh" $doh 2
if ($doh -ne 2) {
    reg add "HKLM\SYSTEM\CurrentControlSet\Services\Dnscache\Parameters" /v EnableAutoDoh /t REG_DWORD /d 2 /f | Out-Null
    $fixed++; $out.Add("  -> Restored EnableAutoDoh=2")
}

# 6. DoH per-interface (Wi-Fi - ifIndex may change; find dynamically)
$wifiIdx = (Get-NetAdapter | Where-Object {$_.Name -like "*Wi-Fi*" -and $_.Status -eq "Up"} | Select-Object -First 1).ifIndex
if ($wifiIdx) {
    $basePath = "HKLM:\SYSTEM\CurrentControlSet\Services\Dnscache\InterfaceSpecificParameters\$wifiIdx\DnsPolicyConfig"
    $doh1 = (Get-ItemProperty "$basePath\1.1.1.1" -EA SilentlyContinue).ConfigOptions
    $doh2 = (Get-ItemProperty "$basePath\1.0.0.1" -EA SilentlyContinue).ConfigOptions
    Check "DoH 1.1.1.1 ConfigOptions" $doh1 2
    Check "DoH 1.0.0.1 ConfigOptions" $doh2 2
    if ($doh1 -ne 2 -or $doh2 -ne 2) {
        foreach ($server in @("1.1.1.1","1.0.0.1")) {
            $kp = "$basePath\$server"
            if (-not (Test-Path $kp)) { New-Item -Path $kp -Force | Out-Null }
            Set-ItemProperty -Path $kp -Name "DohTemplate" -Value "https://cloudflare-dns.com/dns-query" -Type String -Force
            Set-ItemProperty -Path $kp -Name "ConfigOptions" -Value 2 -Type DWord -Force
        }
        $fixed++; $out.Add("  -> Restored DoH per-interface policy")
    }
} else {
    $out.Add("[SKIP] Wi-Fi adapter not up - skipping DoH per-interface check")
}

# 7. Delivery Optimization
$do = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization" -EA SilentlyContinue).DODownloadMode
Check "DODownloadMode" $do 1
if ($do -ne 1) {
    $doPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization"
    if (-not (Test-Path $doPath)) { New-Item -Path $doPath -Force | Out-Null }
    Set-ItemProperty -Path $doPath -Name "DODownloadMode" -Value 1 -Type DWord -Force
    $fixed++; $out.Add("  -> Restored DODownloadMode=1")
}

# 8. Windows Recall
$r1 = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI" -EA SilentlyContinue).DisableAIDataAnalysis
Check "DisableAIDataAnalysis" $r1 1
if ($r1 -ne 1) {
    $aiPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI"
    if (-not (Test-Path $aiPath)) { New-Item -Path $aiPath -Force | Out-Null }
    Set-ItemProperty -Path $aiPath -Name "DisableAIDataAnalysis" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $aiPath -Name "AllowRecallEnablement" -Value 0 -Type DWord -Force
    $fixed++; $out.Add("  -> Restored Recall disable policy")
}

# 9. Activity history
$pub = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -EA SilentlyContinue).PublishUserActivities
Check "PublishUserActivities" $pub 0
if ($pub -ne 0) {
    Set-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Name PublishUserActivities -Value 0 -Type DWord -Force
    Set-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System" -Name UploadUserActivities -Value 0 -Type DWord -Force
    $fixed++; $out.Add("  -> Restored activity history policy")
}

# 10. LLMNR
$llmnr = (Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient" -EA SilentlyContinue).EnableMulticast
Check "LLMNR disabled" $llmnr 0
if ($llmnr -ne 0) {
    $llmnrPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
    if (-not (Test-Path $llmnrPath)) { New-Item -Path $llmnrPath -Force | Out-Null }
    Set-ItemProperty -Path $llmnrPath -Name "EnableMulticast" -Value 0 -Type DWord -Force
    $fixed++; $out.Add("  -> Restored LLMNR disable")
}

# 11. NetBIOS on all adapters (registry, WMI method fails over SSH)
$nbBase = "HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
$nbKeys = Get-ChildItem $nbBase -EA SilentlyContinue
$nbFail = $nbKeys | Where-Object { (Get-ItemProperty $_.PSPath -EA SilentlyContinue).NetbiosOptions -ne 2 }
Check "NetBIOS all adapters" ($nbFail.Count -eq 0) $true
if ($nbFail.Count -gt 0) {
    $nbKeys | ForEach-Object { Set-ItemProperty $_.PSPath -Name NetbiosOptions -Value 2 -Type DWord -Force }
    $fixed++; $out.Add("  -> Restored NetBIOS=2 on $($nbFail.Count) adapter(s)")
}

# 12. ASR rules (auto-heal if reverted to Audit mode by Defender update)
$asrPath = "HKLM:\SOFTWARE\Microsoft\Windows Defender\Windows Defender Exploit Guard\ASR\Rules"
foreach ($guid in @("56a863a9-875e-4185-98a7-b882c64b5ce5","9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2","e6db77e5-3df2-4cf1-b95a-636979351e5b")) {
    $v = (Get-ItemProperty $asrPath -EA SilentlyContinue).$guid
    Check "ASR $($guid.Substring(0,8))" $v 1
    if ($v -ne 1) {
        Set-ItemProperty $asrPath -Name $guid -Value 1 -Type String -Force
        $fixed++; $out.Add("  -> Restored ASR rule $guid")
    }
}

# 13. Read-only checks (no auto-fix - alert only)
$wdRTP = (Get-MpComputerStatus -EA SilentlyContinue).RealTimeProtectionEnabled
Check "Defender RealTimeProtection" $wdRTP $true

$rdp = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server").fDenyTSConnections
Check "RDP disabled" $rdp 1

$out.Add("")
$out.Add("=== RESULT: $pass passed, $fail drifted, $fixed auto-fixed ===")
$out.Add("Log: $log")
$out | Out-File $log -Encoding utf8
$out | Write-Output

# Purge old logs older than 30 days
Get-ChildItem "C:\Temp\drift-check-*.txt" | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-30)} | Remove-Item -Force
