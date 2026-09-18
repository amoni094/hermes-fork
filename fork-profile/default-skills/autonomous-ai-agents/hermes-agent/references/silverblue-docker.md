# Fedora Silverblue: Docker Engine install notes

Use this when the host is Fedora Silverblue (or another rpm-ostree-based Fedora variant) and Docker Engine is needed for Hermes' Docker terminal backend.

Short recipe:
1. Add Docker's Fedora repo:
   `sudo curl -fsSL https://download.docker.com/linux/fedora/docker-ce.repo -o /etc/yum.repos.d/docker-ce.repo`
2. Layer packages with rpm-ostree (not dnf):
   `sudo rpm-ostree install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`
3. Reboot so the new deployment is active.
4. Start the daemon:
   `sudo systemctl enable --now docker`
5. Verify:
   `sudo docker run hello-world`

Notes:
- If Docker startup fails because iptables can't be found, point alternatives at nftables and restart:
  `sudo alternatives --set iptables /usr/bin/iptables-nft`
  `sudo systemctl restart docker`
- Silverblue usually requires a reboot after layering packages; don't expect the new Docker binaries to be available until the new deployment is booted.
- For non-root Docker use, add the user to the `docker` group and re-login:
  `sudo usermod -aG docker $USER`
