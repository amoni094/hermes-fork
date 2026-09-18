# Browser Security on Linux (for non-technical users on streaming sites)

Context: Galina uses Firefox on Ubuntu 26.04 to watch movies on Russian/Eastern
European streaming sites that may run unvetted ad/tracker scripts.

## Actual threat landscape (ordered by real risk)

### 1. Tracking and ads (low risk, high annoyance)
- Sites run JavaScript trackers, fingerprinters, and ad networks
- No OS-level persistence; stops when tab closes
- Blocked by: **uBlock Origin** (install once, no config needed)

### 2. Crypto mining JavaScript (medium annoyance, negligible harm)
- Runs inside the browser tab, consumes CPU while the tab is open
- Symptom: fan noise, browser feels sluggish during movie
- No persistence; stops when tab/browser closes
- Blocked by: uBlock Origin (cryptominer filter lists are built-in)

### 3. Phishing / fake login pages (medium risk)
- Social engineering: fake "sign in to continue" or "update your account" popups
- Not a technical infection — requires the user to enter credentials
- Blocked by: user awareness + uBlock (blocks many known phishing domains)
- Galina low-risk for this: she doesn't have accounts on these sites

### 4. Drive-by browser exploits (low risk on Linux)
- Requires an unpatched Firefox vulnerability + successful sandbox escape
- Firefox sandbox (`bwrap --unshare-all`) contains exploitation to the browser process
- Ubuntu 26.04 gets Firefox security updates automatically via unattended-upgrades
- AppArmor userns fix (60-firefox-userns.conf) actually ENABLES the Firefox sandbox —
  before the fix, the sandbox was crashing and Firefox was running WITHOUT it
- Visible in `ps aux` when sandbox is working: `galina bwrap --unshare-all` process

## What the AppArmor userns fix actually does

Counter-intuitive: `kernel.apparmor_restrict_unprivileged_userns=0` makes Firefox
MORE secure, not less.

- Ubuntu 26.04 default: `apparmor_restrict_unprivileged_userns=1`
  - Firefox tries to sandbox its media content process via user namespaces
  - AppArmor blocks the namespace creation (DENIED sys_admin)
  - Firefox content process crashes; Firefox restarts it (~11min cycle)
  - Result: Firefox runs WITHOUT its media sandbox during the crash window

- After fix: `apparmor_restrict_unprivileged_userns=0`
  - Firefox successfully creates the user namespace sandbox
  - Content processes run inside `bwrap --unshare-all` (visible in ps aux)
  - Any malicious code in a web page is contained to the sandboxed process
  - Result: Firefox runs WITH its full security sandbox

## How to verify nothing malicious ran

After a browsing session on unfamiliar sites, check:

```bash
# Any unexpected processes currently running?
ps aux --no-headers | grep -v 'root\|\[' | awk '{print $1, $11}' | grep -v 'galina\|admin\|systemd\|message\|polkit\|rtkit'

# New files written outside .mozilla and .cache in the last 24h?
sudo find /home/galina -newer /var/log/boot.log -type f \
  -not -path '*/.mozilla/*' -not -path '*/.cache/*' -not -path '*/.config/*'

# Any new cron entries or autostart files today?
sudo find /etc/cron* /var/spool/cron /home/galina/.config/autostart \
  -newer /var/log/boot.log -type f 2>/dev/null

# AppArmor denial count (should be 4 baseline after the userns fix)
sudo journalctl -b --no-pager -q | grep -c 'apparmor.*DENIED'
```

Baseline (normal, nothing compromised):
- 4 AppArmor denials (all from boot, all sys_admin userns attempts from before fix)
- No new files in /home/galina outside .mozilla/.cache
- No new cron entries beyond our own (galina-panel-watchdog, leon-deploy)
- Running processes are all known: lxqt stack, pipewire, nm-applet, pasystray, picom, tint2

## Bottom line for this setup

With uBlock Origin installed and Firefox sandbox working:
- Drive-by malware: very unlikely to succeed
- Crypto mining: blocked by uBlock filter lists
- Tracking: blocked by uBlock
- Phishing: blocked at domain level by uBlock; Galina not logging into accounts
- OS compromise: not achievable via browser alone on Linux with a working sandbox

The main ongoing risk is if Galina is tricked into installing something (fake
"you need this codec" download). She doesn't do that, so practical risk is low.

## Identifying deb vs snap Firefox from journal

Deb Firefox and snap Firefox look similar in ps output but differ in AppArmor
label and binary path. The distinction matters for diagnosing issues:

```bash
# Live check
ls -la /proc/$(pgrep -x firefox | head -1)/exe 2>/dev/null
# Deb:  -> /usr/lib/firefox/firefox
# Snap: -> /snap/firefox/NNNN/usr/lib/firefox/firefox

# AppArmor label in journal (from past boot)
sudo journalctl -b -1 --no-pager -q | grep 'comm="firefox' | head -3
# Deb:  label="unconfined"
# Snap: label="snap.firefox.firefox"
```

Key rule: if the journal shows `label="unconfined"`, deb Firefox is running.
Snap-specific issues (gpu-2404 mount clash, hook.install mid-session) do NOT
affect deb Firefox even if snapd logs those events at the same time.
