# GitHub Organization Invitations

## Pattern: Email-based invites for org repos

### The blocker

GitHub's REST API for adding collaborators has a fundamental asymmetry:

- **Personal repos** (`/repos/USER/REPO/collaborators/USERNAME`): requires GitHub **username only**. Email-invite endpoints fail (404 Not Found).
- **Organization repos** (`/repos/ORG/REPO/invitations`): accepts email addresses directly via the invitations endpoint.

Attempting to invite by email to a personal repo will fail:
```json
{
  "message": "Not Found",
  "documentation_url": "https://docs.github.com/rest",
  "status": "404"
}
```

### Workaround: Migrate the repo to an organization

1. **Create the GitHub organization** (web UI only — no API):
   - Go to https://github.com/organizations/new
   - Pick a slug name (no spaces; use `kebab-case`)
   - Choose free plan
   - Confirm creation

2. **Check the org exists** (verify):
   ```bash
   gh api orgs/ORG-SLUG --jq '.login,.type'
   ```

3. **Transfer the repo into the org**:
   ```bash
   gh api --method POST repos/PERSONAL-USER/REPO-NAME/transfer \
     -f new_owner=ORG-SLUG \
     -f new_name=REPO-NAME
   ```

4. **Poll until transferred** (transfer is async, ~5-10s):
   ```bash
   for i in $(seq 1 12); do
     result=$(gh api repos/ORG-SLUG/REPO-NAME --jq '.full_name' 2>/dev/null)
     if [ "$result" = "ORG-SLUG/REPO-NAME" ]; then
       echo "TRANSFERRED: $result"; break
     fi
     sleep 5
   done
   ```

5. **Verify your role in the org** (sanity check):
   ```bash
   gh api orgs/ORG-SLUG/memberships/YOUR-USERNAME --jq '.role,.state'
   # Should return "admin" and "active"
   ```

6. **Invite by email to the org**:
   ```bash
   gh api --method POST orgs/ORG-SLUG/invitations \
     -f email=person@example.com \
     -f role=direct_member
   ```
   The invitee receives an email from GitHub with an accept link.

### Token scopes

Inviting members to an org requires the `admin:org` scope on your GitHub token.

If your token lacks it, refresh with:
```bash
gh auth refresh -h github.com -s admin:org
```

This will trigger a device-code flow (blocks on CLI):
```
! First copy your one-time code: XXXX-XXXX
Open this URL to continue in your web browser: https://github.com/login/device
```

Manually visit the URL and enter the code. The token scope is updated immediately upon approval.

If using browser-automation tooling (e.g., CDP), **be aware that the browser session state does not persist across tool calls** — if you are re-prompted during refresh, use a dedicated foreground terminal instead.

### Pitfalls

- Do not try to invite by email to a personal repo — the API will reject it silently (404).
- Do not assume the transfer is instantaneous — poll or sleep 5–10s before assuming the repo is ready under the new org.
- Do not skip the `admin:org` scope refresh if the initial invite attempt fails with "You must be an admin" — that means the token needs the scope, not that you lack admin permissions.
- Device-code auth blocks the CLI waiting for manual browser entry — cannot be automated end-to-end from a headless tool context.
