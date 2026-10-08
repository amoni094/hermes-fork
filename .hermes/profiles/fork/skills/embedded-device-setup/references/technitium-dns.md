# Technitium DNS — API Reference and Blocklists

## Auth flow

    BASE="http://localhost:5380/api"
    TOKEN=$(curl -s "$BASE/user/login?user=admin&pass=YOURPASS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

All subsequent API calls pass `?token=$TOKEN`.

## Change admin password

    curl -s --data-urlencode "pass=CURRENTPASS" --data-urlencode "newPass=NEWPASS" \
      "$BASE/user/changePassword?token=$TOKEN"

Parameter names: `pass` = current password, `newPass` = new password. BOTH are required in the POST body — omitting either one returns `{"status":"error","errorMessage":"Parameter 'X' missing."}` even though the token is valid. Attempting to pass them as URL query params also fails. Always use `--data-urlencode` (POST body) to handle special characters in passwords.

## Reset password when it is unknown

If the Technitium admin password is lost, delete the auth config to force a reset to `admin`/`admin`:

    sudo systemctl stop dns.service
    sudo rm /etc/dns/auth.config
    sudo systemctl start dns.service
    sleep 10  # wait for service to fully initialise and recreate auth.config
    # Login now works with admin / admin
    # Immediately change to a strong password using the changePassword endpoint above

## Blocklist management

Pitfall: `/api/blocklist/addUrl`, `/api/blocklist/add`, and `/api/blocklist/update` do NOT exist in Technitium v13+ — they return HTTP 404. The correct method is `settings/set` with one `blockListUrls` parameter per URL (repeatable). All blocklist URLs must be passed together in a single call or earlier ones are overwritten.

Add/replace all blocklist URLs in one call:

    curl -s -G "$BASE/settings/set?token=$TOKEN" \
      --data-urlencode "blockListUrls=https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts" \
      --data-urlencode "blockListUrls=https://small.oisd.nl" \
      --data-urlencode "blockListUrls=https://...additional..."

To add a local hosts-format file as a blocklist:

    # Write the file
    sudo tee /etc/technitium-custom-block.txt > /dev/null << 'EOF'
    0.0.0.0 bad-domain.com
    0.0.0.0 another-bad.com
    EOF

    # Add to blocklist URLs
    curl -s -G "$BASE/settings/set?token=$TOKEN" \
      --data-urlencode "blockListUrls=file:///etc/technitium-custom-block.txt"

Pitfall: Always include ALL existing URLs when calling `settings/set` — passing only the new one replaces the full list, dropping all previous blocklists. Fetch current list first:

    curl -s "$BASE/settings/get?token=$TOKEN" | python3 -c "
    import sys,json
    urls = json.load(sys.stdin).get('response',{}).get('blockListUrls',[]) or []
    for u in urls: print(u)
    "

Apply blocklists by restarting the dns service (no dedicated reload endpoint exists):

    sudo systemctl restart dns.service

Verify blocking is on:

    curl -s "$BASE/settings/get?token=$TOKEN" | python3 -c "
    import sys,json
    d=json.load(sys.stdin).get('response',{})
    print('Blocking:', d.get('enableBlocking'))
    print('Blocklists:', len(d.get('blockListUrls') or []))
    "

## Curated blocklist URLs

Note: Technitium accepts hosts format (0.0.0.0/127.0.0.1 lines) and plain domain lists. Use `/domains/` variants from Hagezi (not `/adblock/`) for maximum compatibility.

    # Steven Black (hosts format — broad, well-maintained)
    https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts

    # OISD small (ad/tracker focused, low false positives)
    https://small.oisd.nl

    # Hagezi multi-normal (comprehensive, low FP)
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/multi.txt

    # Hagezi Windows telemetry
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/win.only.txt

    # Hagezi Apple telemetry
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/native.apple.txt

    # Hagezi Xiaomi tracker (native broadband tracker)
    https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/domains/native.xiaomi.txt

    # Hagezi LG WebOS tracker
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/native.lgwebos.txt

    # Kevle1 Xiaomi telemetry (supplemental)
    https://raw.githubusercontent.com/kevle1/Xiaomi-Telemetry-Blocklist/main/xiaomi_telemetry_blocklist.txt

    # Perflyst smart TV
    https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/SmartTV.txt

    # Perflyst gaming consoles (PS4/PS5/Xbox/Switch)
    https://raw.githubusercontent.com/Perflyst/PiHoleBlocklist/master/GameConsole-AGH.txt

## Manual domain blocks

Pitfall: `zones/addZone` does not exist; `zones/create` does — but zone type `Block` does not exist in the API (returns "Requested value 'Block' was not found"). The only supported zone types via API are: Primary, Secondary, Stub, Forwarder, Catalog.

Reliable way to block individual domains: add them to a local hosts-format file and register it as a `file://` blocklist URL (see above). This is simpler and scales to any number of domains.

Alternatively, create a Primary zone and override the A record to 0.0.0.0:

    curl -s "$BASE/zones/create?token=$TOKEN&zone=BAD.DOMAIN&type=Primary"
    curl -s -X POST "$BASE/zones/addRecord" \
      -d "token=$TOKEN&domain=BAD.DOMAIN&type=A&ipAddress=0.0.0.0&ttl=3600"

Pitfall: `zones/add` with `type=Blocklist` and `/api/blocklist/forceUpdate` both return empty responses and silently do nothing — they are not valid API paths in v15. Do not use them.

Pitfall: `/api/blocklist/forceUpdate` does NOT re-read local `file://` blocklists — it only re-fetches remote HTTP URLs. To apply changes to `/etc/technitium-custom-block.txt`, restart the service:

    sudo systemctl restart dns.service

Verify a block took effect:

    TOKEN=$(curl -s "$BASE/user/login?user=admin&pass=admin" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
    curl -s "$BASE/dnsClient/resolve?token=$TOKEN&server=127.0.0.1&domain=BLOCKED.DOMAIN&type=A" | python3 -c '
    import sys,json; d=json.load(sys.stdin); print(d["response"]["result"]["RCODE"])'
    # Expected: NxDomain

## Key telemetry domains by device

### LG TV
lgtvsdp.com, lgappstv.com, aic-ngx.lge.com, iot.lge.com, smartshare.lgtvsdp.com
AU-specific ad/ACR stack (add all — Hagezi LG list misses these AU siblings and AWS CNAMEs):
  au.nextlgsdp.com (LG SDP / Smart TV Data Platform — highest-volume; 7400+ blocked hits/day),
  au.ad.lgsmartad.com, au.info.lgsmartad.com, au.rdx2.lgtvsdp.com, au.ibs.lgappstv.com,
  au.lgrecommends.lgappstv.com, au.cdpbeacon.lgtvcommon.com, au.cdpsvc.lgtvcommon.com,
  au.recommend.lgtvcommon.com, au.nudge.lgtvcommon.com, au.homeprv.lgtvcommon.com,
  au.service.lgtvcommon.com, au-ad-lgsmartad-com.aws-prd.net,
  au-info-lgsmartad-com.aws-prd.net, au-rdx2-lgtvsdp-com.aws-prd.net
LG ThinQ IoT telemetry (Seoul region — NOT blocked by Hagezi; safe to block if ThinQ app unused):
  *.iot.ap-northeast-2.amazonaws.com (e.g. a3phael99lf879-ats.iot.ap-northeast-2.amazonaws.com)
  This is a persistent MQTT keepalive — the TV pings LG's cloud 100+ times/day to stay "connected".
  Block the specific subdomain via /etc/technitium-custom-block.txt (0.0.0.0 <subdomain>).
  Safe to block: only disables remote control via LG ThinQ phone app. Local streaming
  (Miracast/WFD, Plex, HDMI), Netflix, Prime Video playback, and firmware updates are unaffected.
  ThinQ does NOT handle local streaming protocols — it is cloud control plane only.
Amazon Alexa/Fire TV integration (unagi-fe.amazon.com — 152+ queries/day from LG TV):
  unagi-fe.amazon.com — block only if Prime Video / Alexa voice features on LG are unused.
  Blocking it disables Amazon Prime Video deep linking and Alexa voice on the TV.
  Do NOT block if Prime Video is actively used — it affects app launch/search integration.
ACR/CDN (global):
  cdpbeacon.lgtvcommon.com, cdpbeacon2.lgtvcommon.com, ads.lgtvcommon.com,
  adts.lgtvcommon.com, videoads.lgtvcommon.com, recommend.lgtvcommon.com,
  rdl.lgtvcommon.com, wiseconfig.lgtvcommon.com, lgads.tv, lgsmartad.com
Third-party ACR: alphonso.tv, aic-ngfts.lge.com, smartclip.net, yumenetworks.com
DO NOT block (breaks updates/apps): snu.lge.com, su-ssl.lge.com, su.lge.com,
  ngfts.lge.com, eic-gfts.lge.com, au.lgtvsdp.com, au.emp.lgsmartplatform.com
On-device: Settings > General > Additional Settings > Live Plus: OFF (ACR);
  Personalized advertising: OFF; Quick Start+: OFF (stays network-connected while "off");
  Unplug USB drives when idle (USB path traversal → port 18888 secondscreen takeover).
CVEs: CVE-2023-6317–6320 (LAN auth bypass + root, patched in firmware); 2025 USB path traversal.
  Never port-forward 3000/3001/18888. Keep firmware current.

### PlayStation / PS5
telemetry.playstation.net, analytics.playstation.com, metrics.playstation.com,
collector.playstation.net, report.playstation.com, tracking.playstation.net,
eas.ea.com (EA analytics), data.sonypictures.com
Safe to add (do not break PSN/games):
  telemetry-console.api.playstation.com, telemetry-cii.api.playstation.com
Hagezi Pro may already block smetrics.aem.playstation.com — if PS Store breaks, whitelist that.
DO NOT block update CDNs: update.playstation.net, dau01.ps5.update.playstation.net, *.dl.playstation.net
On-device: Settings > Users and Accounts > Privacy: minimum; Personalized ads: OFF;
  Stay on firmware 14.00+ (Relapse browser→kernel chain affects ≤13.60). 2FA on Sony account.
CVE: Relapse (≤13.60) is a browser-triggered local exploit, not remote WAN.

### Windows
vortex.data.microsoft.com, watson.telemetry.microsoft.com, sqm.microsoft.com,
oca.telemetry.microsoft.com, settings-win.data.microsoft.com, activity.windows.com,
tile-service.weather.microsoft.com, *.events.data.microsoft.com,
telemetry.microsoft.com, tsfe.trafficshaping.dsp.mp.microsoft.com

### Apple
metrics.apple.com, xp.apple.com, pancake.apple.com, feedbackws.apple.com,
iadsdk.apple.com, analytics.apple.com, api-glb-useast.smoot.apple.com

### Xiaomi / MIUI / MiTV / Mi Air Purifier
Already covered by Hagezi or common lists:
  tracking.intl.miui.com, sdkconfig.ad.intl.xiaomi.com
Add (safe to block — telemetry/stats, not IoT control):
  data.mistat.intl.xiaomi.com, data.mistat.xiaomi.com, mistat.intl.xiaomi.com,
  api.ad.xiaomi.com, api.ads.xiaomi.com, sdkconfig.ad.xiaomi.com,
  ad.intl.xiaomi.com, tracking.miui.com, stat.miui.com, o2o.api.xiaomi.com,
  tracker.ai.xiaomi.com, idm.iot.mi.com
DO NOT block if you want Xiaomi Home remote control:
  api.io.mi.com, sts.io.mi.com, ot.io.mi.com, account.xiaomi.com, home.mi.com
The MIUI ad SDK domains (tracking.intl.miui.com etc.) are phone/TV telemetry, NOT what the
air purifier uses for IoT. The purifier communicates via api.io.mi.com — blocking it kills
Xiaomi Home remote control but the purifier still works locally.
On-device: update Xiaomi Home app past 10.0.623 (CVE-2024-45352, CVSS 8.8, code execution).
Isolate IoT devices on AX55 guest/IoT SSID with client isolation.

### TP-Link router (phone-home / HomeShield / Avira SafeThings)
tplinkcloud.com, devs.tplinkcloud.com, n.tplinkcloud.com, b.tplinkcloud.com,
ota.tplinkcloud.com, mdns.tplinkcloud.com, rule.tplinkcloud.com, n-devs.tplinkcloud.com,
safethings.avira.com, dfp-dual.safethings.avira.com, homeassistant.io-link.com
Note: Block these per-device (from the router's IP, not all clients) where possible — blocking tplinkcloud.com network-wide may disable the Tether app.
CVEs (AX55 V4): CVE-2026-18167 (EasyMesh stack overflow, LAN RCE, CVSS 7.7),
  CVE-2026-18330 (hard-coded RSA-1024 key exposes admin password on HTTP login, CVSS 6.1),
  CVE-2025-15608 (probe-handling stack overflow, adjacent-network, CVSS 7.7).
  Fix: firmware 1.2.1 Build 20260527+ (V4 only; check HW version on sticker/UI first).
  Wrong regional image bricks the router — download only from tp-link.com/au for the exact HW version.
Always use https://192.168.0.1 — HTTP login under CVE-2026-18330 exposes admin password to LAN capture.
On router: WPS off, UPnP off, EasyMesh off (if unused), HomeShield/Avira off, Remote Management off.

## Network traffic audit (pcap analysis)

Capture traffic on Pi wlan0 — use tshark with a hard duration limit (tcpdump can crash brcmfmac WiFi driver on Pi 3B+):

    sudo tshark -i wlan0 -a duration:300 -w /tmp/capture.pcap

Analyse the capture for leaks:

    # DNS bypass — queries to port 53 NOT going to the Pi
    sudo tshark -r /tmp/capture.pcap -Y "dns and udp.dstport==53 and ip.dst!=192.168.0.138" \
      -T fields -e ip.src -e ip.dst -e dns.qry.name 2>/dev/null | sort | uniq -c | sort -rn | head -30

    # DoH bypass — port 443 to known DoH provider IPs
    sudo tshark -r /tmp/capture.pcap \
      -Y "tcp.dstport==443 and (ip.dst==1.1.1.1 or ip.dst==1.0.0.1 or ip.dst==8.8.8.8 or ip.dst==8.8.4.4 or ip.dst==9.9.9.9 or ip.dst==149.112.112.112)" \
      -T fields -e ip.src -e ip.dst 2>/dev/null | sort | uniq -c

    # All external connections by source device
    sudo tshark -r /tmp/capture.pcap \
      -Y "not (ip.src==192.168.0.0/24 and ip.dst==192.168.0.0/24)" \
      -T fields -e ip.src -e ip.dst -e tcp.dstport -e udp.dstport 2>/dev/null \
      | sort | uniq -c | sort -rn | head -50

    # Cleartext HTTP
    sudo tshark -r /tmp/capture.pcap -Y "tcp.dstport==80" \
      -T fields -e ip.src -e ip.dst -e http.host 2>/dev/null | sort | uniq

    # DNS query source (which devices are querying the Pi)
    sudo tshark -r /tmp/capture.pcap -Y "dns and udp.dstport==53 and ip.dst==192.168.0.138" \
      -T fields -e ip.src 2>/dev/null | sort | uniq -c | sort -rn

Identify external IPs with whois:

    whois <IP> 2>/dev/null | grep -E 'OrgName|netname|descr' | head -5

Expected traffic on a hardened home Pi:
- Tailscale coordination: *.tailscale.com, *.tailscale.io (HTTPS 443)
- Technitium blocklist fetch: various CDN IPs every 24h (HTTPS 443)
- Crowdsec threat intel: *.crowdsec.net (HTTPS 443)
- Pi NTP: pool.ntp.org or 162.159.200.1 (UDP 123)
- Smart TV Hue discovery: discovery.meethue.com from LG TV — block it if no Hue setup

LG TV Hue discovery: LG webOS has a built-in smart home hub that scans for Philips Hue bridges
and phones Signify servers (57.67.x.x, 57.77.x.x) regardless of whether Hue is installed. Block:

    echo 'discovery.meethue.com' | sudo tee -a /etc/technitium-custom-block.txt
    sudo systemctl restart dns.service

## Per-device DNS attribution and live traffic audit

### Identifying what a device is querying

Pitfall: Query logging is OFF by default in Technitium. Without it, the DNS log captures almost nothing (only queries that coincide with service startup slip through), making per-device attribution impossible. Enable it FIRST before doing any device traffic investigation, then wait for traffic to accumulate:

    curl -s "$BASE/settings/set?token=$TOKEN&logQueries=true&maxLogFileDays=3"

Steps in order:

1. Confirm the device uses the Pi as its DNS resolver — check Technitium dashboard → top clients. A device not listed there is bypassing it entirely.

2. Check `dashboard/stats/get` for aggregate blocked/allowed hits:

    curl -s "$BASE/dashboard/stats/get?token=$TOKEN&type=LastDay"

   Pitfall: The `clientIpAddress` query param is silently ignored by `dashboard/stats/get` — it always returns global stats, not per-client stats. Use it only to get the top-clients list and then cross-reference the logged DNS file (`/var/log/technitium/dns/<date>.log`) for per-client detail.

3. Enable query logging if it is off (it is off by default):

    curl -s "$BASE/settings/get?token=$TOKEN" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("logQueries:", d["response"].get("logQueries"))'
    # If False:
    curl -s "$BASE/settings/set?token=$TOKEN&logQueries=true&maxLogFileDays=3"

   Without this, the DNS log captures almost nothing — only a handful of queries slip through (timing coincidence at server startup), making per-device attribution impossible.

4. With logging on, filter the day's log for a specific device:

    sudo grep '192.168.0.129' /var/log/technitium/dns/$(date +%Y-%m-%d).log | grep -oP 'QNAME: \K[^;]+' | sort | uniq -c | sort -rn

5. UFW firewall logs reveal direct LAN probes (not DNS) from IoT devices:

    sudo journalctl --since '48 hours ago' --no-pager | grep '<DEVICE_IP>' | grep -oP 'DPT=\d+' | sort | uniq -c | sort -rn

   LG TVs send UDP packets directly to high ephemeral ports (55000–65535) on LAN hosts — this is SSDP/UPnP device discovery. UFW blocks these; they are noisy but benign. The source ports (41225, 53619) and varying dest ports are characteristic of LG webOS UPnP scanning, not exfiltration.

## DNS bypass patterns — per-device audit

Devices commonly bypass router DHCP DNS in these ways:

- **ProtonVPN (Windows/Mac)**: Overrides DNS with Cloudflare DoH (1.1.1.1 with DoH: https://cloudflare-dns.com/dns-query). Check with `ipconfig /all` — look for `DoH:` line under DNS Servers. Fix: ProtonVPN Settings → Connection → Custom DNS → set to Pi IP. This routes DNS through the VPN tunnel but resolves at the Pi.
- **Tailscale**: Overwrites `/etc/resolv.conf` on the device it runs on. Fix on Pi: `sudo tailscale set --accept-dns=false`. Fix on desktop: set custom DNS in Tailscale app, or rely on ProtonVPN DNS override.
- **RethinkDNS (Android)**: Handles DNS per-app with its own encrypted resolver. Does not use network DHCP DNS at all — leave it in place, it provides stronger per-app control than Pi-level DNS.
- **Smart TVs / consoles**: Usually respect DHCP DNS but may have hardcoded fallback IPs (8.8.8.8, 1.1.1.1). Set DNS manually in device network settings to force use of Pi.
- **Pi itself**: Set to 127.0.0.1 by NetworkManager. Verify with `nmcli dev show wlan0 | grep DNS`.

Audit which clients are actually using the Pi: check Technitium dashboard → top clients. A device not appearing there is bypassing it.

Check desktop DNS from remote:

    # via SSH
    cmd /c ipconfig /all
    # look for "DoH:" under DNS Servers — indicates DoH active and bypassing Pi

## Network device identification

Use nmap on the Pi to enumerate all connected devices:

    sudo apt-get install -y nmap
    sudo nmap -sn 192.168.0.0/24 -T4 | grep -E "report for|MAC Address" | paste - -

Fingerprint unknowns:

    # TTL from ping: 64 = Linux/macOS, 128 = Windows
    ping -c2 <IP> | grep ttl

    # Targeted port scan + OS guess
    sudo nmap -sV -O --osscan-guess -p 22,80,443,445,139,5353,8080 -T4 <IP>

    # NetBIOS name (Windows)
    nmblookup -A <IP>

    # mDNS name (Apple/Linux)
    avahi-browse -a -t -r 2>/dev/null | grep -A3 "<IP>"

MAC interpretation:
- First byte odd (26:xx, 4a:xx, 72:xx, etc.) = locally administered bit set = MAC randomisation (phone privacy mode)
- Even first byte, known OUI = real hardware MAC; look up with: `curl https://api.macvendors.com/<mac>`
- Pi 3B+ WiFi OUIs: b8:27:eb, dc:a6:32, e4:5f:01
- Intel WiFi (laptops): 10:3d:1c, 8c:8d:28, a4:c3:f0, 40:ec:99 (common prefixes)

Pitfall: The agent's own LAN IP can appear as an "unknown device." Before treating any device as suspicious, run `ip route get <pi-ip>` on the agent host — if the `src` address shown matches the mystery IP, it is the agent's own machine. Never block it via UFW or router MAC filtering.

Pitfall: Do not run `tcpdump -i wlan0` for more than 15 seconds on a Pi 3B+ — the brcmfmac WiFi driver can crash, dropping the connection and requiring a physical power cycle to recover. Use `tshark -i wlan0 -a duration:N -w /tmp/cap.pcap` (background, with a hard duration limit) for longer captures.

Ongoing ARP monitoring: deploy `scripts/arp-monitor.sh` on the Pi via cron (`*/5 * * * *`) to log all active devices every 5 minutes to `/var/log/arp-monitor.log`. Filter for a specific IP: `grep '0.185' /var/log/arp-monitor.log`.

Router DHCP client list (TP-Link AX55): Advanced → Network → DHCP Server → Client List. Hostname column may be blank for headless Linux devices — this is normal, not suspicious by itself. Devices on 2.4GHz and 5GHz bands both appear in the same list with no band indicator.

Router MAC blocking: if the Access Control deny field is greyed out on AX55, check whether the mode is set to Whitelist (blocks unknown devices) vs Blacklist (only blocks listed devices) — toggling the mode unlocks the field.

## Recursive resolver config (no upstream forwarders)

Disable all forwarders in Settings → General. Technitium performs root-hint recursion natively — no Unbound needed. Verify with:

    curl -s "$BASE/settings/get?token=$TOKEN" | python3 -m json.tool | grep -E 'forwarder|recursion'

## Pi 3B+ optimization (1GB RAM, always-on DNS)

### Blocklist consolidation

13+ blocklists on 1GB RAM risks OOM during the 24h refresh cycle — each list creates a second copy in memory during reload. Research-validated safe set for 1GB:

    Hagezi Pro (replaces StevenBlack + OISD small + individual vendor lists)
    Hagezi TIF mini (Threat Intelligence Feed — replaces URLhaus)
    DoH bypass list (prevents Firefox/Chrome DoH from bypassing Pi)
    Custom local hosts file (device-specific: Xiaomi, TP-Link, NVIDIA, LG, Windows)

Drop: StevenBlack (covered by Hagezi Pro), OISD small (covered), URLhaus (covered by TIF), individual Xiaomi/Apple/Windows/LG vendor lists (covered by Pro + custom).

    # Hagezi Pro
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/pro.txt
    # Hagezi TIF mini
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/tif.mini.txt
    # DoH bypass
    https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/doh.txt

### Query logging — prevent SQLite OOM and SD/USB wear

Defaults log forever and will bloat and OOM on 1GB. The actual API field names (confirmed v15.5.1):
- Enable query logging: `logQueries=true` (NOT `enableQueryLogs`)
- Retention: `maxLogFileDays=3` (NOT `maxLogDays`)
- Stats retention: `maxStatFileDays=90`

    curl -s "$BASE/settings/set?token=$TOKEN&logQueries=true&maxLogFileDays=3&maxStatFileDays=90"

Pitfall: The field names in Technitium's API documentation differ from what `settings/get` returns in some versions. Always verify by calling `settings/get` and checking the actual key names in the response before building a `settings/set` call — wrong field names are silently ignored (status: ok, but nothing changes).

UseStorageSpaceQuota/maxStorageSpaceMBs:

Enable SQLite auto-vacuum — only possible by editing the config file directly (no API endpoint):

    sudo grep -r 'queryLogAutoVacuum\|vacuum' /etc/dns/ /var/lib/dns/ 2>/dev/null
    # In Technitium config (location varies by install): set queryLogAutoVacuum=true

### DNSSEC — CVE-2023-50387 KeyTrap

Do NOT enable DNSSEC validation unless Technitium is >= v15.5.1 (patched for CVE-2023-50387 — a crafted DNSSEC response can consume 100% CPU). Check version:

    curl -s "http://localhost:5380/api/dashboard?token=$TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response',{}).get('version','unknown'))"
    # Also: dpkg -l | grep technitium

### QPM rate limiting

Prevent external abuse and cache stampedes. Set via Settings → General → Rate Limiting. Recommended for home DNS:

    clientQueriesPerMinute: 1000   # per-IP rate limit (catches runaway devices)
    Enable: true

### IPv6 outbound recursion

If Pi has no working IPv6 route (most home networks), disable IPv6 DNS recursion to avoid latency on AAAA lookups. Test first:

    ping6 -c1 -W2 2606:4700:4700::1111 && echo 'IPv6 working' || echo 'no IPv6 route'

If no IPv6 route, disable at two levels:

    # 1. Technitium — the ipv6Mode field (confirmed v15.5.1 field name is 'enableIPv6', not 'ipv6Mode' in set):
    curl -s "$BASE/settings/set?token=$TOKEN&enableIPv6=false"
    # settings/get will show ipv6Mode: Disabled to confirm

    # 2. Kernel level — prevents any IPv6 socket bind and reduces attack surface:
    sudo tee /etc/sysctl.d/99-disable-ipv6.conf << 'EOF'
    net.ipv6.conf.all.disable_ipv6 = 1
    net.ipv6.conf.default.disable_ipv6 = 1
    net.ipv6.conf.lo.disable_ipv6 = 1
    EOF
    sudo sysctl -p /etc/sysctl.d/99-disable-ipv6.conf

### Cache-to-disk

Enable cache persistence so a Pi reboot doesn't cause a recursion storm (all clients re-resolve simultaneously):

    # Settings → Cache → "Save Cache to Disk" = ON
    # Sets interval (default 15 min) to flush cache to disk for restore after reboot

### Hardware watchdog

Pi 3B+ BCM2835 has a hardware watchdog. Enable so a kernel hang triggers automatic reboot.

Load the kernel module persistently (required on Trixie — the `dtparam=watchdog=on` config.txt approach is unreliable on newer kernels):

    echo 'bcm2835_wdt' | sudo tee /etc/modules-load.d/watchdog.conf
    sudo modprobe bcm2835_wdt
    ls /dev/watchdog*   # confirm /dev/watchdog and /dev/watchdog0 appear

Also add to /etc/modules for persistence across reboots (modules-load.d is the right place but adding both is safe):

    grep -q bcm2835_wdt /etc/modules || echo 'bcm2835_wdt' | sudo tee -a /etc/modules

Install and configure the watchdog daemon:

    sudo apt-get install -y watchdog
    sudo tee /etc/watchdog.conf << 'EOF'
    watchdog-device = /dev/watchdog
    watchdog-timeout = 15
    interval = 10
    max-load-1 = 24
    min-memory = 1
    EOF
    sudo systemctl enable --now watchdog

Pitfall: The watchdog daemon may not auto-start after reboot even when enabled — the bcm2835_wdt module must be loaded first. Verify after each reboot: `systemctl is-active watchdog`. If inactive, `sudo modprobe bcm2835_wdt && sudo systemctl start watchdog`.

Set kernel panic auto-reboot. On Trixie, `/etc/sysctl.conf` does not exist — always use `/etc/sysctl.d/`:

    echo 'kernel.panic=10' | sudo tee /etc/sysctl.d/99-kernel-panic.conf
    sudo sysctl -p /etc/sysctl.d/99-kernel-panic.conf

### log2ram — reduce write wear

Moves /var/log to tmpfs, syncs to disk periodically — dramatically reduces write wear on USB/SD:

    echo 'deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ bookworm main' | sudo tee /etc/apt/sources.list.d/azlux.list
    sudo wget -O /usr/share/keyrings/azlux-archive-keyring.gpg https://azlux.fr/repo.gpg
    sudo apt-get update && sudo apt-get install -y log2ram

Default log2ram size is 128MB (as of 2026). Set to 64M for a Pi DNS server — sufficient for rotated logs:

    sudo sed -i 's/^SIZE=.*/SIZE=64M/' /etc/log2ram.conf

Pitfall: The `SIZE=` line in log2ram.conf has a comment block immediately above it that also contains the word `SIZE=` (an example in the comment). Use `^SIZE=` anchored regex, not bare `SIZE=`, or sed will double-write the value — resulting in two `SIZE=` lines where the second wins but leaves the config messy.

Pitfall: The Crowdsec packagecloud.io repo does not have a release for Debian Trixie — it returns 404 and breaks `apt-get update`, causing log2ram (and any other package install) to fail. Fix before installing log2ram:

    # Either comment out the crowdsec repo:
    sudo sed -i 's/^deb/#deb/' /etc/apt/sources.list.d/crowdsec*.list
    # Or point it at bookworm (closest supported):
    sudo sed -i 's/trixie/bookworm/' /etc/apt/sources.list.d/crowdsec*.list
    sudo apt-get update

### tmpfs for /tmp and /var/tmp

Reduces write wear and speeds up temp file operations. Add to `/etc/fstab`:

    tmpfs /tmp     tmpfs defaults,noatime,nosuid,size=64m  0 0
    tmpfs /var/tmp tmpfs defaults,noatime,nosuid,size=32m  0 0

Applied automatically on next reboot. Verify with `mount | grep 'on /tmp'`.

### noatime mount option

Reduces writes by not updating access timestamps on every file read. Already set by Raspberry Pi OS on newer installs (check `/etc/fstab`). If missing, add to root mount entry in fstab:

    PARTUUID=xxxx  /  ext4  defaults,noatime  0 1

### Router secondary DNS — bypass risk

With a public DNS set as secondary (e.g. 1.0.0.1), clients round-robin ~50% of queries to the public resolver, bypassing all Pi blocking. Options:
  - **Blank the secondary** — single point of failure but guaranteed all queries hit Pi
  - **Second Technitium instance** — run on a second Pi or VM for true redundancy
  - **Leave public secondary** — accept ~50% bypass for resilience (queries still blocked on primary)

### Crowdsec vs fail2ban overlap

Running both on 1GB RAM is redundant (both do SSH brute-force detection). Crowdsec provides community threat intel that fail2ban lacks — remove fail2ban and keep Crowdsec:

    sudo apt-get remove --purge fail2ban
    sudo apt-get autoremove

### Crowdsec scenario pruning for DNS-only Pi

Crowdsec installs ~36 scenarios by default, most targeting web apps that don't run on a Pi DNS appliance. Trim to only relevant scenarios to reduce RAM and alert noise:

    # Keep:
    #   crowdsecurity/ssh-bf
    #   crowdsecurity/ssh-slow-bf
    #   crowdsecurity/iptables-scan-multi_ports

    # Remove all HTTP/CVE/app scenarios:
    sudo cscli scenarios list | grep enabled  # review first
    sudo cscli scenarios remove \
      crowdsecurity/http-generic-bf crowdsecurity/http-probing \
      crowdsecurity/http-bad-user-agent crowdsecurity/http-crawl-non_statics \
      crowdsecurity/http-path-traversal-probing crowdsecurity/http-sensitive-files \
      crowdsecurity/http-sqli-probing crowdsecurity/http-xss-probing \
      crowdsecurity/http-open-proxy crowdsecurity/http-backdoors-attempts \
      crowdsecurity/nginx-req-limit-exceeded crowdsecurity/spring4shell_cve-2022-22965 \
      crowdsecurity/grafana-cve-2021-43798 crowdsecurity/jira_cve-2021-26086 \
      crowdsecurity/vmware-cve-2022-22954 crowdsecurity/vmware-vcenter-vmsa-2021-0027 \
      crowdsecurity/thinkphp-cve-2018-20062 crowdsecurity/fortinet-cve-2018-13379 \
      crowdsecurity/f5-big-ip-cve-2020-5902 crowdsecurity/pulse-secure-sslvpn-cve-2019-11510 \
      crowdsecurity/apache_log4j2_cve-2021-44228 ltsich/http-w00tw00t \
      crowdsecurity/http-cve-2021-41773 crowdsecurity/http-cve-2021-42013 2>/dev/null
    sudo systemctl restart crowdsec

### RAM tuning — kernel VM parameters

Add to `/etc/sysctl.d/99-pi-tuning.conf` and apply with `sudo sysctl -p /etc/sysctl.d/99-pi-tuning.conf`:

    vm.swappiness=10          # prefer RAM; only use zram under genuine pressure (default 60 is too aggressive)
    vm.vfs_cache_pressure=50  # keep dentry/inode cache longer — reduces overhead for blocklist operations

Note: zram is enabled by default in Raspberry Pi OS Trixie (zstd compression, ~1x RAM size). No manual setup needed — verify with `cat /proc/swaps`. Do not install additional zram tools; they conflict with the default setup.
