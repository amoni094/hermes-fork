# Known Windows Machines

## BOORAN — Grandpa's laptop

- Model: Lenovo IdeaPad Flex 5 14IAU7 (SKU 82R7)
- OS: Windows 11 Home 23H2 (10.0.22631), 8GB RAM, Micron NVMe 512GB
- Tailscale IP: 100.115.122.121
- SSH: `ssh booran` or `ssh admin@100.115.122.121`
- Credentials: `admin` / `Gunn1967`
- Profile home: `C:\Users\alexe` (NOT `C:\Users\admin`)
- OpenSSH: `C:\Program Files\OpenSSH\sshd.exe` (Oct 2025 build)
- SSH key installed: yes (id_ed25519, fingerprint SHA256:sGaRC221ZPLy6KwNaH/dpCOx8SDhzk9DyDVcrZv5VG8)
- Notes: Defender definitions auto-update daily. Lenovo USB Ethernet (USB dock) shows Unknown status when dock not connected — normal.

## DESKTOP-PH4F2DK — User's main desktop

- OS: Windows 11
- Tailscale IP: 100.88.247.70 (LAN: 192.168.0.181)
- SSH: `ssh admin@100.88.247.70`
- Credentials: `admin` / `Gunn1967`
- Firefox profile: `C:\Users\admin\AppData\Roaming\Mozilla\Firefox\Profiles\7oi20t52.default-release\`
- Firefox version: 157.0
- ProtonVPN: running (ProtonVPN Service + ProtonVPN WireGuard services)
- Firefox privacy hardening: applied (user.js + policies.json with uBlock + CanvasBlocker force-install); backup at `C:\Users\admin\Documents\firefox-user.js.bak`
- Notes: policies.json at `C:\Program Files\Mozilla Firefox\distribution\policies.json` covers Brave Search + extension force-installs. See `firefox-privacy-hardening` skill for full procedure.
