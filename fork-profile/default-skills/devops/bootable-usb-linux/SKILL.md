---
name: bootable-usb-linux
description: Use when validating or creating bootable Linux USB drives, or when a new Linux install has WiFi card issues and needs internet access workarounds.
tags: [usb, boot, linux, iso, grub, media, wifi, tethering, driver]
related_skills:
  - fedora-atomic-dotfiles-adaptation
  - atomic-desktop-app-installation
  - silverblue-system-update-trigger
---

# Bootable Linux USB — Validation, Download, and Flash

## Trigger
User plugs in a USB drive, asks whether it is bootable, or asks to create/repair a bootable Linux USB.

## Key constraint upfront
`dd` (and any direct write to /dev/sdX) is on the **hardline blocklist** — the agent cannot run it even with approvals off. **Tell the user this before starting the download**, not after. Hand them the exact command string early so they are not surprised at the end.

## 1. Identify and mount the drive
```
lsblk -o NAME,SIZE,TYPE,TRAN,VENDOR,MODEL,MOUNTPOINT
lsusb
udisksctl mount -b /dev/sdXN
```
Check: device path, partition layout, filesystem type, label.

## 2. Validation checklist (run in this order)

### 2a. MBR boot signature
```
sudo dd if=/dev/sdX bs=1 count=2 skip=510 2>/dev/null | od -An -tx1
```
Expected: `55 aa`. Absence = not MBR-bootable.

### 2b. Partition boot flag
```
sudo fdisk -l /dev/sdX
```
Look for `*` in the Boot column on the primary partition.

### 2c. Root directory contents
```
ls -lah /run/media/<user>/<LABEL>/
```
Expect: `[boot]/`, `boot/`, `.disk/`, and — critically — a `casper/` directory.

### 2d. Kernel and initrd present
```
ls /run/media/<user>/<LABEL>/casper/
```
Must contain at minimum: `vmlinuz` and `initrd`. **Missing casper = drive will not boot.** This is the most common Rufus crash symptom — bootloader written, kernel copy aborted.

### 2e. GRUB tree
```
ls /run/media/<user>/<LABEL>/boot/grub/
```
Expect: `grub.cfg`, `x86_64-efi/`, `i386-pc/` (for dual UEFI+BIOS support).

### 2f. grub.cfg cross-check
```
grep -i 'linux\|initrd\|casper\|vmlinuz' /run/media/<user>/<LABEL>/boot/grub/grub.cfg
```
Paths in grub.cfg must resolve to actual files on the drive. If grub.cfg says `/casper/vmlinuz` but `/casper/` is absent, it will not boot.

### 2g. EFI bootloader
```
find /run/media/<user>/<LABEL>/ -name '*.efi'
```
For UEFI boot: expect `/EFI/boot/bootx64.efi` or equivalent.

### 2h. .disk/info (version fingerprint)
```
cat /run/media/<user>/<LABEL>/.disk/info
```
Confirms which distro/version the drive claims to be.

## 3. Diagnosing Rufus crash failures
Rufus writes the bootloader and partition structure first, then copies the filesystem image. A crash mid-write leaves a drive with a valid MBR, boot flag, grub tree — but **no `/casper/` directory and no kernel**. The drive is a skeleton: structurally correct but unbootable. Solution: re-flash from scratch.

## 4. Downloading the ISO
Prefer `curl` over `wget` for large ISO downloads:
```
curl -L -o /tmp/<distro>.iso <URL> --progress-bar
```
wget's `--progress=dot:giga` is not implemented in all builds and silently falls back — curl is more reliable for large files.

Always verify the checksum before flashing:
```
# Get expected hash
wget -qO- <SHA256SUMS_URL> | grep <iso-filename>
# Compute actual
sha256sum /tmp/<distro>.iso
```
Mismatch on first download: delete and re-download with curl before concluding the ISO source is bad.

## 5. Flash step — hand off to user
The agent **cannot** execute `dd` (hardline blocklist — not overridable). Give the user this command once the ISO is verified:
```
sudo dd if=/tmp/<distro>.iso of=/dev/sdX bs=4M conv=fsync status=progress
sync
```
Replace `/dev/sdX` with the actual device (not partition — sda not sda1). Double-check with `lsblk` before running.

Alternatives the user can run if they prefer a GUI:
- **Balena Etcher** (most reliable cross-platform)
- **GNOME Disks** > Restore Disk Image

## 6. Verify after flash
Re-mount and re-run steps 2c-2g to confirm all critical files are present before rebooting.

## 7. WiFi card not recognised at install time

If the target laptop's WiFi card is not recognised during the live/install session, **install anyway** — the installer works fully offline. Fix the driver after first boot.

### Getting internet on the new machine after install

In order of easiest to hardest:

1. **USB tethering from an Android phone** — plug in, Settings → Network & Internet → Hotspot & Tethering → USB tethering. Linux picks it up as a wired interface automatically, no config needed. This is the fastest path.
   - iPhone: Settings → Personal Hotspot → Allow Others to Join, then plug in.
2. **Ethernet** — if the laptop has a port. Wired works out of the box on almost all Linux installs.
3. **USB WiFi dongle** — a known-working dongle (e.g. Realtek RTL8188) provides instant WiFi without driver work.

### Subnet warning: USB tethering vs home WiFi

USB tethering puts the laptop on the **phone's** DHCP network (commonly 10.x.x.x or 192.168.42.x), not the home router's network. This means:
- The laptop cannot be reached by other machines on 192.168.0.x — they are on different subnets and cannot route to each other.
- Remote access from the host machine (SSH, ping) will fail even though the laptop has internet.

To enable remote access: connect the laptop to the same network as the host (home WiFi or same router via Ethernet) so both get addresses in the same subnet.

### Identifying the WiFi card and finding the driver

Once the machine has internet (via tethering or Ethernet):
```
lspci | grep -i network        # for PCIe cards (most laptops)
lsusb                          # for USB WiFi adapters
```
Use the card model to look up the correct firmware/driver package and install via `apt`/`dnf`.

## Pitfalls
- **Announce the dd blocklist upfront** — before starting the download, not after a 7GB download completes.
- **casper absence is the #1 Rufus crash symptom** — do not assume bootable just because grub files exist.
- **wget dot:giga progress not implemented** in some builds; curl is the safer choice for large ISOs.
- **Checksum mismatch on first wget attempt** is possible (mirror caching); try curl before concluding the ISO itself is corrupt.
- `parted` may not be installed on Silverblue/Atomic hosts; use `fdisk -l` instead.
- `xxd` and `strings` may be absent; use `od -An -tx1` for hex dumps.
- Flash target is the **disk** (`/dev/sda`), not the partition (`/dev/sda1`) — make sure the user uses the right one.
- **USB tethering ≠ same network** — the tethered device is on the phone's subnet, not the home router's. Remote access from another machine on 192.168.0.x will fail with 100% packet loss even though the tethered machine has working internet.
