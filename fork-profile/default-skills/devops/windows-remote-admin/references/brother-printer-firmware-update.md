# Brother Network Printer — Firmware Update & Windows Integration

Captures workflow from Sep 4 2026 for Brother MFC-7860DW at 192.168.0.99.
Generalises to other Brother network printers with embedded web UI.

## Discover printer on LAN

```powershell
# Parallel ping scan of common subnet range (fast — runs all pings simultaneously)
1..254 | ForEach-Object -Parallel {
    $ip = "192.168.0.$_"
    if (Test-Connection -ComputerName $ip -Count 1 -TimeoutSeconds 1 -Quiet) {
        Write-Output $ip
    }
} -ThrottleLimit 50
```

Brother printers respond to ping and open ports 80 (web UI) and 9100 (raw print).

```powershell
# Probe specific IP for printer ports
$ip = '192.168.0.99'
80, 9100 | ForEach-Object {
    $t = New-Object System.Net.Sockets.TcpClient
    try {
        $t.Connect($ip, $_)
        "Port $_ OPEN"
    } catch {
        "Port $_ CLOSED"
    } finally { $t.Close() }
}
```

## Check current firmware version

Brother printers expose a CSV info endpoint (no auth required):

```powershell
$r = Invoke-WebRequest -Uri "http://192.168.0.99/etc/mnt_info.csv" -UseBasicParsing
$r.Content
# Returns CSV with firmware version in the MainVersion/SubVersion fields
# Example: ...J,1.01,... where J = main firmware letter, 1.01 = sub
```

Firmware version is a single letter (A–Z) for the main firmware. Higher = newer.
Sub version is a dotted number (e.g. 1.01). The CSV format varies slightly by model —
look for a column matching the model name (e.g. `MFC-7860DW`) with version adjacent.

## Check if firmware is outdated

Brother firmware lookup: https://support.brother.com/g/b/downloadlist.aspx?c=us&lang=en&prod=mfc7860dw_all&os=26&type2=4
(Adjust `prod=` slug for your model — find from Brother support site.)

Latest available firmware (Sep 2026, MFC-7860DW): version R/S (main).
Version J = outdated by ~10+ iterations. Any version < the latest letter = update recommended.

## Pre-requisite: Print Spooler must be running

Windows Printer ports (and the web UI session) need the Spooler service.
If Spooler was disabled (e.g. as part of hardening):

```powershell
# Re-enable temporarily for printer work
Start-Service Spooler
Set-Service Spooler -StartupType Manual  # Manual = won't auto-start but starts on demand

# Verify printer port registration
Get-PrinterPort | Where-Object { $_.PrinterHostAddress -eq '192.168.0.99' } | Select-Object Name,PrinterHostAddress,PortNumber
```

If no printer port exists, add it:
```powershell
Add-PrinterPort -Name 'IP_192.168.0.99' -PrinterHostAddress '192.168.0.99'
```

## Firmware update via Brother web UI (user-interactive)

Brother's firmware update is click-gated — the DLF download server requires a browser session.
Silent remote install is not feasible. User must do this step.

1. Navigate to http://[PRINTER_IP] in a browser
2. Login — default credentials: **username blank, password `access`**
   (If password changed, check sticker on printer or try `initpass`)
3. Go to Administrator > Firmware Update
4. Follow prompts — printer downloads and applies update (~5-10 min, reboots itself)

## Post-update verification

```powershell
# Re-check firmware version after update
$r = Invoke-WebRequest -Uri "http://192.168.0.99/etc/mnt_info.csv" -UseBasicParsing
$r.Content
```

Printer will be offline for ~2-3 minutes during firmware application. Normal.

## After printer work: decide Spooler state

Print Spooler is a known attack surface (PrintNightmare family). Decision tree:

- **No network printer, no local printer**: Disable Spooler permanently
  (`Set-Service Spooler -StartupType Disabled; Stop-Service Spooler -Force`)
- **Occasional printing**: Leave at Manual — Spooler starts when a print job is sent,
  stops when idle. Drift-check task should log but not auto-kill it.
- **Regular printing**: Leave Running/Manual is acceptable; document in drift baseline.

On DESKTOP-PH4F2DK (Sep 2026): left at Running/Manual to support Brother MFC-7860DW.
Drift check logs it as potential drift but does not auto-stop it.
