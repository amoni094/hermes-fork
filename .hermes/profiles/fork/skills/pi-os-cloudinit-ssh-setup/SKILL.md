---
name: pi-os-cloudinit-ssh-setup
description: Use when setting up a fresh Pi OS via SD card or cloud-init.
---

# Pi OS Cloud-Init & SSH Setup

## Cloud-Init: user vs users

The singular `user:` key does NOT support `ssh_authorized_keys`. Must use list form:

    users:
      - name: myuser
        shell: /bin/bash
        lock_passwd: false
        passwd: "<hash>"
        sudo: null
        ssh_authorized_keys:
          - "ssh-ed25519 AAAA... user@host"

## Password Hashing — Pi OS Trixie

Pi OS Trixie uses **yescrypt** (`$y$`) as the default PAM hash algorithm. sha512 (`$6$`) hashes silently fail PAM auth even though they are structurally valid. Always generate with:

    mkpasswd -m yescrypt <password>

Verify before writing to /etc/shadow:

    python3 -c "
    import ctypes, ctypes.util
    lib = ctypes.CDLL(ctypes.util.find_library('crypt') or 'libcrypt.so.2')
    lib.crypt.restype = ctypes.c_char_p
    lib.crypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    h = b'<hash>'
    print('match:', lib.crypt(b'<password>', h) == h)
    "

## Cloud-Init State Reset (force re-run on next boot)

After editing user-data on the boot partition, clear state on rootfs:

    sudo rm -rf /mnt/piroot/var/lib/cloud/sem \
                /mnt/piroot/var/lib/cloud/data \
                /mnt/piroot/var/lib/cloud/instances \
                /mnt/piroot/var/lib/cloud/instance

## Disable Cloud-Init After First Run

    sudo touch /mnt/piroot/etc/cloud/cloud-init.disabled

## Pi OS SSH (OpenSSH) Config

Pi OS Trixie sshd_config has `KbdInteractiveAuthentication no` by default. Password auth via PAM requires it enabled. Add to `/etc/ssh/sshd_config.d/50-cloud-init.conf`:

    PasswordAuthentication yes
    PubkeyAuthentication yes
    AuthorizedKeysFile .ssh/authorized_keys
    KbdInteractiveAuthentication yes

## Injecting SSH Key Directly onto Rootfs

    sudo mkdir -p /mnt/piroot/home/<user>/.ssh
    sudo bash -c 'echo "<pubkey>" > /mnt/piroot/home/<user>/.ssh/authorized_keys'
    sudo chmod 600 /mnt/piroot/home/<user>/.ssh/authorized_keys
    sudo chmod 700 /mnt/piroot/home/<user>/.ssh
    sudo chown -R <uid>:<gid> /mnt/piroot/home/<user>/.ssh

UID/GID for pi5-home is 1000:1000.

Pitfall: Cloud-init re-runs on next boot will overwrite authorized_keys unless state is cleared or cloud-init is disabled.

## Dropbear vs OpenSSH

Pi OS ships OpenSSH. If `ssh-keyscan` returns `SSH-2.0-dropbear`, you are talking to a DIFFERENT device — not the Pi. Check router DHCP table or avahi to find the actual Pi IP.

## Finding Pi IP After Boot

    ip neigh show  # check ARP cache for new MAC
    avahi-browse -a -t 2>/dev/null | grep -i pi
    # Look for OpenSSH (not dropbear) banner:
    ssh-keyscan -t ecdsa <ip1> <ip2> ... 2>&1 | grep -v dropbear

## Boot Partition Mount Path

On Pi OS, the boot partition mounts at `/boot/firmware` (not `/boot`). Cloud-init reads user-data from `/boot/firmware/user-data` at runtime.

## Writing to Boot Partition (vfat)

The patch tool cannot write to vfat (permission denied). Use:

    sudo tee /mnt/piboot/user-data << 'EOF'
    ...
    EOF
