# Private repo bootstrap from a local workspace

Use when the user asks to turn an existing local project into a new private GitHub repository.

Minimal verified sequence
1. `gh auth status`
2. `gh repo view OWNER/NAME` to detect whether the repo already exists
3. inspect local state: `git status --short --branch`, `git branch --show-current`, and if needed `git rev-parse --show-toplevel`
4. commit the intended files locally first
5. `gh repo create OWNER/NAME --private --source=. --remote=origin --push`
6. verify with `gh repo view OWNER/NAME --json name,visibility,isPrivate,url,defaultBranchRef`
7. confirm tracking with `git status --short --branch` and `git remote -v`

Why this matters
- avoids accidental creation of a public repo
- avoids claiming success before the remote exists
- gives a final report with exact visibility, branch, commit, and URL

MVP honesty note
If the repository is a front-end scaffold with seeded analytics or placeholder data, say so explicitly in the repo README or UI rather than presenting it as a live data product.
