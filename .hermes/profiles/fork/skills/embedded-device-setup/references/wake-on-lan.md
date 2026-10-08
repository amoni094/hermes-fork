# Wake-on-LAN from Pi — Patterns and Limitations

## Send magic packet from Pi

Install:

    sudo apt-get install -y wakeonlan etherwake

Pitfall: The `wakeonlan` CLI on Fedora host does NOT support the `-i <broadcast-ip>` flag (different version than Debian). If running from the host rather than the Pi, use the python3 socket fallback:

    python3 -c "
    import socket, struct
    mac = '70:D8:C2:70:0D:B4'.replace(':','')
    magic = bytes.fromhex('F'*12 + mac*16)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(magic, ('192.168.0.255', 9))
    s.sendto(magic, ('192.168.0.181', 9))
    s.close()
    print('Magic packet sent')
    "

On the Pi itself, `wakeonlan -i <ip>` works correctly — this limitation only applies to the host's Fedora `wakeonlan` package.

Script `/usr/local/bin/wake-desktop`:

    #!/bin/bash
    MAC="70:D8:C2:70:0D:B4"  # desktop MAC
    echo "Sending magic packet to 192.168.0.255:9 with $MAC"
    wakeonlan -i 192.168.0.255 $MAC
    echo "Sending magic packet to 192.168.0.181:9 with $MAC"
    wakeonlan -i 192.168.0.181 $MAC
    echo "Magic packet sent to DESKTOP-PH4F2DK via subnet broadcast and direct IP"

    sudo chmod +x /usr/local/bin/wake-desktop

Invoke remotely from any Tailscale device:

    ssh rainbowpi@100.110.242.79 wake-desktop

## Windows WoL pre-requisites (configure remotely via SSH)

    # Enable WakeOnMagicPacket on the NIC
    powershell -Command "Set-NetAdapterAdvancedProperty -Name 'Ethernet' -RegistryKeyword 'WakeOnMagicPacket' -RegistryValue 1"

    # Disable Fast Startup (blocks WoL from S5)
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled /t REG_DWORD /d 0 /f

    # Set power button to sleep (S3) instead of shutdown
    powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS PBUTTONACTION 1
    powercfg /setactive SCHEME_CURRENT

    # Prevent auto-hibernate (keeps S3 sleep stable indefinitely)
    powercfg /change standby-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0

## WiFi WoL — fundamental limitation

WiFi WoL (WoWLAN) does NOT work from S5 (full shutdown) on consumer hardware:
- The WiFi NIC loses radio association when Windows fully powers off
- The router cannot forward a magic packet to a client that is not associated
- Intel AX200 + TP-Link AX55 do not maintain association in S5 — this is a firmware/hardware limitation, not a config issue
- No software fix exists for S5 WiFi WoL on this hardware combination

WiFi WoL from S3 (traditional sleep) also unreliable on TP-Link AX55:
- The AX55 does not proxy ARP or maintain association for sleeping WiFi clients
- Magic packets sent to 192.168.0.255 (subnet broadcast) or the client's last IP both fail to reach a sleeping WiFi client through this router
- Intel AX200 is listed as `wake_armed` and `wake_programmable` via `powercfg /devicequery` but this does not override the router's inability to forward the packet

Verify S3 is available (not Modern Standby which behaves differently):

    powercfg /a

Look for "Standby (S3)" in the output. If the system only shows "Standby (S0 Low Power Idle)" it uses Modern Standby and WoL from sleep is also unreliable.

## BIOS requirements (ASRock Z390 Extreme4)

- Advanced → ACPI Configuration → PCIe Devices Power On: **Enabled**
- Advanced → ACPI Configuration → **Deep Sleep**: set to **Enabled in S4-S5** (this is ASRock's label for ErP/EuP — it does NOT appear as "ErP"). Enabling Deep Sleep cuts NIC power in S4/S5 and breaks WoL. S4-S5 setting keeps the NIC powered during hibernate and shutdown so it can receive magic packets.
- Requires physical BIOS access — cannot be set remotely

Note: The ACPI Configuration submenu on this board contains: Suspend to RAM, ACPI HPET Table, PS/2 Keyboard S4/5 Wakeup Support, PCIe Devices Power On, Ring In Power On, RTC Alarm Power On, USB Keyboard/Remote Power On, USB Mouse Power On, Deep Sleep. There is no "ErP" label — "Deep Sleep" is the equivalent setting.

## Reliable alternatives when WiFi WoL fails

1. **Ethernet cable** — I219-V onboard NIC on ASRock Z390 is wake-armed by default; plug in and it works immediately from S5
2. **Powerline adapters** — use home electrical wiring as ethernet; ~$50-80, no cable runs needed, WoL over powerline works reliably from S5
3. **S3 sleep instead of S5 shutdown** — keep WiFi association alive; power draw ~1-5W (negligible cost)
4. **Scheduled wake timer** — use `powercfg /waketimers` or Task Scheduler to auto-wake at a fixed time each day
