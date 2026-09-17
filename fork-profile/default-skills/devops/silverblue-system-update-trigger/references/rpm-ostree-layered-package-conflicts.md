# rpm-ostree Layered Package Conflicts

## Pattern: Hyprland COPR vs libwayland version mismatch (observed 2026-07-09)

### Symptom
`rpm-ostree upgrade` fails with a depsolve error like:

```
error: Could not depsolve transaction; 4 problems detected:
 Problem 1: package hyprland-0.55.4-1.fc44.x86_64 from @commandline requires
   pkgconfig(wayland-server) >= 1.22.91, but none of the providers can be installed
   - cannot install both libwayland-client-1.24.0-3.fc44.x86_64 from fedora
     and libwayland-client-1.25.0-1.fc44.x86_64 from @System
```

### Root cause
Layered packages from a COPR (hyprland, hypridle, hyprlock,
xdg-desktop-portal-hyprland) were built against wayland 1.24.x. The base
Fedora image updated libwayland to 1.25.x (@System). rpm-ostree can't
satisfy the dep chain because the COPR hasn't yet published packages built
against the newer wayland.

### Affected packages (fc44, July 2026)
- hyprland-0.55.4-1.fc44.x86_64 (from @commandline)
- hypridle-0.1.7-4.fc44.x86_64
- hyprlock-0.9.5-1.fc44.x86_64
- xdg-desktop-portal-hyprland-1.3.12-1.fc44.x86_64

### Remediation options

**Option A — Wait for COPR rebuild** (recommended if Hyprland is actively used)
Check whether the COPR (copr.fedorainfracloud.org/tofik/nwg-shell or the
Hyprland COPR) has published updated packages built against wayland 1.25.
Once they do, `rpm-ostree upgrade` will resolve cleanly.

**Option B — Remove layered packages, update, reinstall**
```
rpm-ostree uninstall hyprland hypridle hyprlock xdg-desktop-portal-hyprland
# reboot into new deployment
rpm-ostree install hyprland hypridle hyprlock xdg-desktop-portal-hyprland
```
This allows the base image to update but loses Hyprland until the COPR
publishes updated packages. Only viable if running GNOME or another session
in parallel.

**Option C — Pin and wait**
Leave the conflict in place. Flatpak, toolbox DNF, and firmware updates
still run cleanly. rpm-ostree simply won't update until the conflict
resolves upstream. This is the zero-risk option.

### Detection
The conflict always shows `@commandline` as the package source for the
layered packages and a `cannot install both ... from fedora and ... from @System`
line for the library. That pattern reliably identifies a layered-package
COPR/version mismatch rather than a base-image-only dep conflict.

---

## Pattern: LocalPackage restore after OS upgrade (observed 2026-07-09)

This covers the restore phase when Option B was used — packages were removed
before the OS upgrade and now need to be reinstalled.

### Critical distinction: LocalPackages vs LayeredPackages
rpm-ostree distinguishes two kinds of added packages:
- **LayeredPackages**: installed by name from a repo (`rpm-ostree install <name>`)
- **LocalPackages**: installed from local `.rpm` files (`rpm-ostree install /path/to/pkg.rpm`)

After an OS upgrade, `rpm-ostree status` shows both the booted deployment and
the prior one. If the removed packages appear under `LocalPackages` in the
*previous* deployment, they were local-RPM installs — NOT repo installs.

**`rpm-ostree install <name>` will fail** with "Packages not found" for
LocalPackages, even if the package name exists in a repo, because rpm-ostree
treats them as distinct. You must reinstall using the original `.rpm` files.

### Locate the RPM files
Before giving up on a restore, check these locations in order:
1. `~/ricing-rpms/recover-*/` — a dedicated local RPM stash (if the user
   maintains one; this is where the Hyprland RPMs lived: `~/ricing-rpms/recover-20260629/`)
2. `~/Downloads/` or any other known download dir
3. `~/.cache/rpm-ostree/`, `/var/cache/rpm-ostree/`, `/var/cache/libdnf5/`,
   `/var/cache/dnf/` — rpm/dnf caches (usually cleared, but worth checking)
4. The ostree repo itself (`find ~ -name "*.rpm" 2>/dev/null | grep hypr`)

The ostree repo may still hold the content objects for the prior deployment's
packages even if the `.rpm` files are gone — but extraction from ostree is
non-trivial. Try the local stash first.

### Reinstall from local RPMs
```bash
rpm-ostree install \
  ~/ricing-rpms/recover-20260629/hyprland-0.55.4-1.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/hypridle-0.1.7-4.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/hyprlock-0.9.5-1.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/hyprsunset-0.3.3-6.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/hyprutils-0.13.1-1.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/hyprland-qt-support-0.1.0-10.fc44.x86_64.rpm \
  ~/ricing-rpms/recover-20260629/xdg-desktop-portal-hyprland-1.3.12-1.fc44.x86_64.rpm
```

After the OS upgrade to Fedora 44.20260709.0 (wayland 1.25.0), the same
local RPMs installed cleanly — the root cause (wayland dep conflict) was
resolved by the OS upgrade itself.

### Pitfall: background transaction from GNOME Software
rpm-ostree is single-transaction. If GNOME Software is running an
"upgrade check only" transaction in the background, `rpm-ostree install`
will fail with:
```
error: Transaction in progress: upgrade (check only)
You can cancel the current transaction with `rpm-ostree cancel`
```
Fix: `rpm-ostree cancel && sleep 2` then retry the install.

### Reinstall script caveat
The reinstall script generated in the previous session used
`rpm-ostree install <name>` (repo-style), which fails for LocalPackages.
If you have a generated reinstall script, update its install command to use
the local `.rpm` paths from `~/ricing-rpms/recover-*/` instead of bare
package names.

### Config restore
After reinstall + reboot, configs in `~/.config/hypr` etc. are typically
untouched (they're in the user homedir, not in the ostree image). Check
before extracting the backup tarball — it's usually unnecessary.
