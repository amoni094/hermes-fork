# Finding a GitHub Username from an Email Address

When you have an email (e.g. alexey.monin@nab.com.au) but need a GitHub username
to invite as a repo collaborator, try these patterns via gh CLI:

```bash
gh api users/alexeymonin  --jq '.login,.name' 2>/dev/null
gh api users/amonin        --jq '.login,.name' 2>/dev/null
gh api users/alexey-monin  --jq '.login,.name' 2>/dev/null
```

Success = JSON with `.login`; 404 = that variation doesn't exist. Try firstname+lastname,
firstinitiallastname, firstname-lastname. Most NAB/enterprise accounts use real names.

## Inviting once you have the username

For org repos, no `admin:org` scope needed for repo-level username invites:

```bash
gh api --method PUT \
  /repos/ORG/REPO/collaborators/USERNAME \
  -f permission=push
```

This sends a GitHub invitation email to the user's registered email address.
The invite appears in `/repos/ORG/REPO/invitations` until accepted.

## Why not just use email directly?

- **Personal repos**: `/repos/USER/REPO/collaborators/EMAIL` → 404 Not Found. Username only.
- **Org repos, repo-level API**: Username only, no admin:org needed.
- **Org-level invitation by email**: Requires `admin:org` token scope.
  Use `gh auth refresh -h github.com -s admin:org` to get it (triggers device code flow).
  See `references/github-org-invitations.md` for full org transfer + email invite pattern.

## Observed Jul 2026

alexey.monin@nab.com.au → username `alexeymonin` found on second try.
Invited to tech-legal/hermes-agent-spec with write permission.
Invite pending accept (invitation ID 326096344).
