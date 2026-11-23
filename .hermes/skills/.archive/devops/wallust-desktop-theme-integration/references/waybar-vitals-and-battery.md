Waybar top-right vitals + laptop battery pattern

Use this when adapting a JaKooLit-style Hyprland/Waybar setup to a more readable laptop-oriented top bar.

Layout pattern
- Put a vitals group to the left side of the top-right cluster.
- Put the laptop group (backlight + battery) near the far-right status area.
- Keep notifications and power actions at the far right.

Concrete module ordering used successfully
- modules-right:
  - group/motherboard
  - tray
  - network
  - group/audio
  - group/laptop
  - custom/swaync
  - group/power

Readable vitals labels
- Prefer shorthand words instead of icon-only vitals when the bar becomes visually dense.
- Proven labels:
  - CPU {usage}%
  - Mem {used:0.1f}G
  - Temp {temperatureC}°C
  - Disk {percentage_used}%
  - Pwr {profile}

Theme congruence notes
- Keep vitals, battery, and backlight on a shared semi-opaque surface block for consistency.
- Small rounded corners and narrow side margins make the cluster read as one unit without flattening all modules together.
- Keep battery visually stronger than the rest (for example by weight or a stronger accent color) so it remains scannable.

Verification notes
- After edits, reload Waybar with SIGUSR2.
- Check that Waybar remains running after reload.
- Confirm battery hardware exists with upower or /sys/class/power_supply before claiming battery support is live.
