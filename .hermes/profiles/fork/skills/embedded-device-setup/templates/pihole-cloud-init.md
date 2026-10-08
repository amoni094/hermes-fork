# Pi-hole headless cloud-init template

For Raspberry Pi OS Trixie on a Pi 3B+, headless WiFi + Pi-hole auto-install.

## user-data

```yaml
#cloud-config

hostname: pihole
manage_etc_hosts: true

users:
  - name: rainbowpi
    groups: [adm, dialout, cdrom, sudo, audio, video, plugdev, games, users, input, render, netdev, gpio, i2c, spi]
    shell: /bin/bash
    lock_passwd: false
    passwd: "<output of: openssl passwd -6 'thepassword'>"

ssh_pwauth: true
package_update: true
package_upgrade: true

packages:
  - avahi-daemon

runcmd:
  - curl -sSL https://install.pi-hole.net | PIHOLE_SKIP_OS_CHECK=true bash /dev/stdin --unattended
```

## network-config

```yaml
network:
  version: 2
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      regulatory-domain: AU
      access-points:
        "144McKinnonNetwork":
          password: "<password>"
```

## Deployment steps

1. Write files to /tmp/pisetup/ (agent can write there)
2. sudo cp to /mnt/piboot/ after mounting sda1
3. sudo touch /mnt/piboot/ssh
4. sudo sync && sudo umount /mnt/piboot /mnt/piroot

First boot takes ~15-20 min. SSH in with: ssh rainbowpi@pihole.local
