# Telstra Smart Modem Gen 2 — LAN Device Map

Gateway: 192.168.0.1 (Arcadyan LH1000, Telstra Smart Modem Gen 2)
Last verified: September 2026

## Known devices

| IP           | Hostname / Name              | Device type              | MAC                 | Notes |
|--------------|------------------------------|--------------------------|---------------------|-------|
| 192.168.0.1  | gateway                      | Telstra modem            | bc:30:d9:ca:a4:d2  | ISP gateway; admin: admin/Gunn1967 (factory 'Telstra' changed) |
| 192.168.0.2  | LinkTap_Gateway_ECAF         | Smart irrigation (GW-02) | 02:4b:5f:25:ec:af  | LinkTap garden watering; access control OFF by default — set password |
| 192.168.0.3  | Eufy Device                  | Eufy HomeBase/hub        | 04:17:b6:b8:ba:1b  | Smart Innovation LLC OUI; no local admin interface; cloud-managed |
| 192.168.0.4  | bravia315a4cd9c79609c9       | Sony Bravia TV           | 00:a0:96:52:53:b2  | KDL-40NX700; EOL firmware; UPnP on :52323; Mitsumi Electric OUI |
| 192.168.0.5  | BRW00410EFED256              | Brother printer          | 00:41:0e:fe:d2:56  | MFC-L2800DW; firmware 1.29/Sub1 1.11 (updated Sep 2026) |
| 192.168.0.6  | (device-1c:93:c4:60:89:50)  | Amazon Echo/Fire TV      | 1c:93:c4:60:89:50  | Amazon Technologies OUI; ports 55442, 55443 (FFS), 8009 (local API); ADB port 5555 closed (good) |
| 192.168.0.14 | iPhone                       | iPhone                   | —                  | — |
| 192.168.0.46 | DESKTOP-NAIHLES              | Windows desktop (Natasha's)| a8:5e:45:55:c8:e7  | ASUSTek NIC; SSH as Administrator via Tailscale (100.121.155.11) |
| 192.168.0.57 | (unnamed)                    | Tesla Energy Gateway     | 20:0d:3d:50:19:71  | Quectel LTE module OUI; Powerwall/solar gateway; TLS cert: O=Tesla Energy Products; API requires auth (403); OTA-managed by Tesla |
| 192.168.0.60 | (mum's machine)              | Ubuntu LXQt PC           | 5c:87:9c:db:4d:90  | Intel NIC; accessible via SSH |
| 192.168.0.61 | ThinkPad (this machine)      | Linux laptop (Hermes)    | —                  | |

Additional IPs with randomised/private MACs (phones using MAC privacy):
  192.168.0.48, .50, .51, .55 — cannot identify by MAC; ephemeral

## Sony Bravia KDL-40NX700 (192.168.0.4)
- 2010/2011 era; runs XrossMediaBar (pre-Android TV)
- No Sony REST/BRAVIA API (only came with 2013+ models)
- Firmware: EOL — no updates available from Sony since ~2013-2014
- UPnP/DLNA active on port 52323 — normal for local media sharing; model confirmed via
  `curl http://192.168.0.4:52323/dmr/DMRdevicedesc.xml`
- Risk: LAN-local only; NAT-protected from internet
- Action: nothing to update

## Brother MFC-L2800DW (192.168.0.5)
- Web UI: https://192.168.0.5 (HTTP redirects to HTTPS, port 80 → HTTPS)
- Unauthenticated status: https://192.168.0.5/home/status.html
- Admin login: password field name=Bcaa id=LogBox; submit id=login
- Admin password: Gunn1967 (household password, as of Sep 2026)
- Firmware: 1.29 / Sub1: 1.11 (updated Sep 2026 from 1.28/1.10)
- Page counter: ~1921 pages, drum 88%, toner 60% remaining
- Security: X-Frame-Options: DENY; HTTPS enforced; PJL security enabled; firmware rollback disabled
- Admin pages: /general/information.html, /admin/firmwareupdate.html, /network/protocol.html
- Enabled protocols: Web/HTTPS, SNMP, LPD, Port 9100, IPP, AirPrint, Mopria, Web Services,
  Network Scan, POP3/IMAP4/SMTP client, FTP client
- Disabled (good): Syslog, Proxy, PC Fax Receive, SMTP Server, FTP Server, TFTP

## LinkTap GW-02 (192.168.0.2)
- Web UI: http://192.168.0.2 (HTTP only, no HTTPS)
- No login required by default — access control is disabled out of the box
- To enable: bottom of the web UI page, 'Access settings' section — set username and password
- Firmware updates: via the LinkTap phone app only; not triggerable from web UI
- MQTT: disabled by default (good)
- Model GW-02 firmware string is a long build ID, not a simple version number

## Tesla Energy Gateway (192.168.0.57)
- TLS cert: C=US, O=Tesla, OU=Tesla Energy Products; self-signed
- API at /api/* requires authentication (returns 403 unauthenticated)
- Managed entirely by Tesla OTA — do not attempt firmware updates locally
- Quectel LTE module OUI (20:0D:3D) — used for Tesla's cellular monitoring link
- No local admin action needed or possible

## Amazon Echo/Fire TV (192.168.0.6)
- OUI: Amazon Technologies Inc. (1C:93:C4)
- Open ports: 55442, 55443 (Amazon Frustration-Free Setup), 8009 (local device API)
- ADB port 5555: CLOSED — ADB debugging is off (correct security posture)
- Firmware: automatic OTA from Amazon, no manual action possible
- No local admin interface

## Eufy device (192.168.0.3)
- OUI: Smart Innovation LLC (04:17:B6) — Eufy/Anker brand
- No open HTTP/HTTPS/ADB ports; communicates via Eufy cloud app only
- Firmware: pushed automatically by Eufy cloud
- No local admin interface or action possible
