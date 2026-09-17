# HP Pavilion g6 Fan Error Diagnosis (2026-09-02)

Machine: `galina-hppaviliong6notebookpc`, BIOS F.42, Lubuntu 22.04 (kernel 7.0.0-30-generic)

## Symptom

BIOS POST fan check error causes boot to hang and wait for Enter on every boot.
Also: kernel log shows `hp-wmi: Failed to apply initial fan settings: -22` on every boot.

## Root cause analysis

### 1. BIOS POST hang
HP BIOS Fan Check setting is enabled. The BIOS cannot detect a fan tach signal
it is satisfied with. Physical F10 BIOS entry needed to disable it (one-time).
Cannot be bypassed via Linux/GRUB — happens before any OS code runs.

### 2. OS-level kernel error
The `hp-wmi` driver (file: `hp-wmi.ko.zst`, kernel 7.0.0-30-generic) loads and
attempts to apply fan settings via a WMI BIOS call. BIOS F.42 does not implement
the required WMI method, returning EINVAL (-22). Also:
- `hp_bioscfg: Unable to set BIOS settings on HP systems` — hp_bioscfg module fails
  similarly; BIOS attributes interface not supported
- `wmi_bus wmi_bus-PNP0C14:00: [Firmware Bug]: WQBC data block query control method not found`
  — WMI data block query method missing in BIOS ACPI tables

## Key diagnostic data

### hwmon devices present
| hwmon | name     | relevant attributes |
|-------|----------|--------------------|
| hwmon0 | ACAD    | in0 (AC adapter)   |
| hwmon1 | acpitz  | temp1 = 30°C       |
| hwmon2 | BAT0    | voltage, current   |
| hwmon3 | hp      | pwm1_enable = 2    |
| hwmon4 | coretemp| Core 0/1, Package  |

`pwm1_enable = 2` = BIOS automatic control. Fan hardware is running.

### Thermal state at diagnosis
- Package id 0: +32°C (high=80°C, crit=85°C)
- Core 0: +32°C, Core 1: +33°C
- acpitz temp1: +30°C
- ACPI thermal zone TZ01: 31°C

All values well within safe range. Fan is physically working.

### No fan RPM counter
`find /sys/class/hwmon -name 'fan*_input'` returns empty — the embedded controller
controls fan speed directly; Linux has no visibility into RPM on this hardware.

### ACPI cooling devices (idle state)
```
cooling_device0-3: Processor  cur=0/max=10  (CPU idle throttling)
cooling_device4:   intel_powerclamp  cur=0/max=100
cooling_device5:   LCD  cur=0/max=10
```
All at minimum — system is cool and idle.

### Boot time
```
Startup finished in 1.880s (kernel) + 5.787s (initrd) + 29.502s (userspace) = 37.170s
graphical.target reached after 25.478s in userspace
```
No boot delays caused by the hp-wmi error (error appears at t=24.39s, after graphical
system is already loading).

## Fix applied

```bash
# Blacklist hp_wmi and hp_bioscfg
echo 'blacklist hp_wmi' | sudo tee /etc/modprobe.d/hp-wmi-blacklist.conf
echo 'blacklist hp_bioscfg' | sudo tee -a /etc/modprobe.d/hp-wmi-blacklist.conf
sudo update-initramfs -u
```

Result: hp_wmi and hp_bioscfg will not load on next boot. Fan remains under BIOS
hardware PWM automatic control. coretemp and all other hwmon sensors unaffected.
Fn hotkeys (brightness, wifi toggle) will be non-functional after blacklisting.

## Remaining action required

Galina must physically enter BIOS (F10 at boot) and disable Fan Check.
Step-by-step: see `lxqt-remote-desktop-management` SKILL.md, "BIOS POST fan check hang" section.
