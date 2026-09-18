# Startup, orphans, and AppData cleanup (DESKTOP-PH4F2DK)

This-machine audit results, not general Windows advice. Re-audit before deleting.
Always READ FIRST, produce findings, get confirmation, THEN act.

## Read-only queries

```powershell
Get-Service | Where-Object { $_.Status -eq 'Running' } | Select-Object Name,DisplayName,StartType | Sort-Object StartType,Name | Format-Table -AutoSize
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 20 Name,Id,@{N='MB';E={[math]::Round($_.WorkingSet/1MB,1)}} | Format-Table
Get-ScheduledTask | Where-Object { $_.TaskPath -notlike '\Microsoft\*' } | Select-Object TaskName,TaskPath,State | Sort-Object TaskPath | Format-Table -AutoSize
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location
```

## Common orphan patterns (seen on this PC)

| Pattern | Source | Fix |
|---------|--------|-----|
| GoogleUpdater/GoogleChromeUpdate services + tasks | Chrome removed but updater survived | Stop services, delete registry keys, Unregister-ScheduledTask |
| LHMDownload / LHMRun tasks | LibreHardwareMonitor uninstalled | Unregister-ScheduledTask |
| InstallAB / InstallAB2 tasks | Afterburner silent-install orphan | Unregister-ScheduledTask (Afterburner itself still works) |
| ZoomUpdateTask | Zoom uninstalled | Unregister-ScheduledTask |
| PhoneExperienceHost | Phone Link not in use | Full package removal — registry disable alone is insufficient |

## Phone Link — full deprovision only

`PhoneManagerEnabled = 0` is insufficient; the app reinstates at next login.

```powershell
Get-AppxPackage -AllUsers -Name Microsoft.YourPhone | Remove-AppxPackage -AllUsers
Get-AppxProvisionedPackage -Online | Where-Object { $_.PackageName -like '*YourPhone*' } | Remove-AppxProvisionedPackage -Online
```

Verify: `Get-AppxPackage -AllUsers -Name Microsoft.YourPhone` returns nothing.

## Google Updater leftovers

```powershell
'gupdate','gupdatem','GoogleChromeElevationService' | ForEach-Object {
    Stop-Service $_ -Force -ErrorAction SilentlyContinue
    sc.exe delete $_ 2>$null
}
Remove-Item 'HKLM:\SYSTEM\CurrentControlSet\Services\gupdate' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'HKLM:\SYSTEM\CurrentControlSet\Services\gupdatem' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'HKLM:\SYSTEM\CurrentControlSet\Services\GoogleChromeElevationService' -Recurse -Force -ErrorAction SilentlyContinue
Get-ScheduledTask | Where-Object { $_.TaskName -like '*Google*' } | Unregister-ScheduledTask -Confirm:$false
```

## WSL remnant

```powershell
wsl --shutdown
Start-Sleep 3
Remove-Item "$env:LOCALAPPDATA\wsl" -Recurse -Force -ErrorAction SilentlyContinue
Test-Path "$env:LOCALAPPDATA\wsl"
```

Typical size: 3-4 GB per user. If wsl.exe is missing, the folder is an uninstall remnant — delete directly.

## AppData scan

Use the logged-on username; do not assume `rainbow`.

```powershell
$user = $env:USERNAME
Get-ChildItem "C:\Users\$user\AppData\Local" | ForEach-Object {
    $sz = (Get-ChildItem $_.FullName -Recurse -EA SilentlyContinue | Measure-Object Length -Sum).Sum
    [PSCustomObject]@{Folder=$_.Name; SizeGB=[math]::Round($sz/1GB,3)}
} | Sort-Object SizeGB -Descending | Select-Object -First 20 | Format-Table
```

Telegram Desktop ~1 GB media cache is intentional unless the user confirms otherwise.

## ASUS OEM bloat (seen on ASUS laptops/desktops)

ASUS ships gaming-oriented services that waste RAM/CPU on non-gaming machines. Disable all safely:

```bash
for svc in "ROG Live Service" LightingService USBAppControl WorkflowAppControl WMIRegistrationService AsusUpdateCheck "GameSDK Service" asComSvc; do
  ssh -i ~/.ssh/id_ed25519 Administrator@IP "sc config \"$svc\" start= disabled & sc stop \"$svc\"" 2>&1
done
```

Also disable the scheduled update tasks:
```bash
ssh Administrator@IP "schtasks /change /tn \"\\ASUS\\ASUSUpdateTaskMachineCore*\" /disable"
ssh Administrator@IP "schtasks /change /tn \"\\ASUS\\ASUSUpdateTaskMachineUA\" /disable"
```

Disable Nahimic gaming audio tasks (pointless for non-gaming use):
```bash
for task in NahimicSvc32Run NahimicSvc64Run NahimicTask32 NahimicTask64; do
  ssh Administrator@IP "schtasks /change /tn $task /disable"
done
```

Common ASUS startup registry entries to remove (bloat, not needed):
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Run` → `AdobeAAMUpdater-1.0`
- `HKLM\Software\WOW6432Node\...\Run` → `Acrobat Assistant 8.0`, `BrotherSoftwareUpdateNotification`, `TeamsMachineInstaller`, `BMISR` (Genius webcam)

## SysMain (Superfetch) — disable on SSD systems

SysMain pre-loads frequently used files into RAM — beneficial on spinning HDDs, wasteful on SSDs
(adds RAM pressure with no read-time benefit since SSD random reads are already fast).

Check disk type first:
```bash
ssh Administrator@IP "powershell -Command \"Get-PhysicalDisk | Select-Object MediaType,Size\""
```

If C: is SSD:
```bash
ssh Administrator@IP "sc config SysMain start= disabled && sc stop SysMain"
```

If C: is HDD, leave SysMain enabled.

## DNS NRPT corruption fix

If System event log shows repeated `Microsoft-Windows-DNS-Client` errors about "Name resolution
policy table has been corrupted" or "read policy table failed with error 87", delete the corrupt rule:

```bash
# Get the GUID from the event log message, then:
ssh -i ~/.ssh/id_ed25519 Administrator@IP "powershell -Command \"Remove-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows NT\\DNSClient\\DnsPolicyConfig\\{GUID-HERE}' -Recurse -Force; ipconfig /flushdns\""
```

## AGMService (Adobe Genuine Monitor)

Phones home constantly to verify Adobe license. Disable unless the user actively needs it:

```bash
ssh Administrator@IP "sc config AGMService start= disabled && sc stop AGMService"
```

## PCHelpSoft Driver Updater

PUP (potentially unwanted program) — installs scheduled tasks without user awareness. Remove:

```bash
ssh Administrator@IP "schtasks /delete /tn \"PCHelpSoft Driver Updater\" /f"
```

**PITFALL: The silent uninstaller leaves behind both the registry entry and the program files.**
After running the uninstaller, force-clean both:

```bash
# Run the silent uninstaller
ssh Administrator@IP "\"C:\\Program Files\\PCHelpSoft\\Driver Updater\\VERSION\\installer.exe\" --uninstall --silent"
# Remove leftover registry entry
ssh Administrator@IP "reg delete \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{GUID}\" /f"
# Remove leftover files
ssh Administrator@IP "rmdir /s /q \"C:\\Program Files\\PCHelpSoft\""
# Verify
ssh Administrator@IP "reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{GUID}\" 2>&1"  # expect: key not found
ssh Administrator@IP "dir \"C:\\Program Files\\PCHelpSoft\" 2>&1"  # expect: File Not Found
```

## Intel DSA

```powershell
Stop-Service "DSAService","DSAUpdateService" -Force -ErrorAction SilentlyContinue
Set-Service "DSAService" -StartupType Disabled
Set-Service "DSAUpdateService" -StartupType Disabled
Get-Process "DSATray" -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Chrome/Zoom user-level uninstall

These are often HKCU installs. Admin uninstall does not remove them. Not Store apps — `Disable-AppxPackage` does not apply.
Per-user scheduled tasks cannot be unregistered by admin — delete task files under `C:\Windows\System32\Tasks` (takes effect after logoff).

## Crash dumps / C:\Temp

Add to weekly cleanup: `C:\Windows\MEMORY.DMP`, `C:\Windows\Minidump\*`, and `C:\Temp` files older than 7 days.

## MSI uninstall leaving file debris

MSI `/qn` silent uninstall often removes the registry entry but leaves program files behind.
Always verify after uninstall and force-remove if needed:

```bash
# Uninstall
ssh Administrator@IP "msiexec /x {PRODUCT-GUID} /qn /norestart && echo DONE"
# Verify registry gone
ssh Administrator@IP "reg query \"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{PRODUCT-GUID}\" 2>&1"
# Verify files gone
ssh Administrator@IP "dir \"C:\\Program Files (x86)\\AppName\" 2>&1"
# Force-remove if files remain
ssh Administrator@IP "rmdir /s /q \"C:\\Program Files (x86)\\AppName\""
```

Seen with: Adobe Acrobat XI Pro (leaves `C:\Program Files (x86)\Adobe\Acrobat 11.0\` intact after msiexec uninstall).
