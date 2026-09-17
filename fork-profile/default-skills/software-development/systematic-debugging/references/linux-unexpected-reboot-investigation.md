# Linux unexpected reboot investigation

Use this when a Linux machine appears to have "randomly reset" or rebooted.

## Fast triage order

1. Anchor the reboot timeline first.
   - `who -b`
   - `last -x`
   - `journalctl --list-boots`

2. Check the previous boot for crash signatures.
   - kernel panic / BUG / Call Trace
   - watchdog
   - thermal / critical temperature
   - machine check / MCE
   - OOM just before shutdown

3. If crash evidence is absent, inspect intentional reboot paths.
   - systemd user services started near login
   - system update services (`rpm-ostree`, `ostree`, `flatpak`, distro updater units)
   - local scripts under `~/.config/systemd/user/`, `~/.local/bin/`, `~/.hermes/scripts/`, dotfiles repos, or other automation directories
   - search those scripts for `reboot`, `shutdown`, `systemctl reboot`, `loginctl reboot`

4. Correlate logs across layers.
   - previous boot system journal
   - previous boot user-service journal
   - updater/service log files in the user state directory
   - current `rpm-ostree status` or equivalent update status

## Silverblue-specific pitfall

On Fedora Silverblue/Kinoite and similar OSTree systems, a reboot after login may be deliberate rather than a crash:
- a login-triggered user service can run `rpm-ostree upgrade`
- the script may stage a deployment successfully
- the same script may then call `/usr/sbin/reboot`

Strong confirmation pattern:
- previous boot journal shows `rpm-ostree` creating/finalizing a deployment
- `journalctl --user -b -1 -u <service>` shows the updater service running
- the journal records `sudo ... COMMAND=/usr/sbin/reboot` or equivalent shortly before the boot ends
- no panic/thermal/MCE/watchdog evidence exists nearby

## Interpretation rule

If explicit reboot commands and update activity line up in time, classify the event as an intentional automation-triggered reboot unless contradictory crash evidence appears.

Do not call it a hardware reset just because the user experienced it as unexpected.
