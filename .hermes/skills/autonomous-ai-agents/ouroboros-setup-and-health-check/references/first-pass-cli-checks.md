# First-pass CLI checks for Ouroboros setup

Use this sequence when the user asks to "set up" or verify Ouroboros.

## Minimal probe order
1. Binary presence
   - `command -v ouroboros`
   - optionally `command -v ooo`
2. Version
   - `ouroboros --version`
3. Runtime and config health
   - `ouroboros status health`
   - `ouroboros config show`
   - `ouroboros config backend`
4. Backend-specific integration
   - Codex: `ouroboros codex doctor`
5. Plugin inventory
   - `ouroboros plugin list`

## Interpretation notes
- If `ouroboros` works and `ooo` does not, guide with `ouroboros` commands first.
- If `status health` says the database is missing and will be created on first run, that is usually benign.
- If runtime backend and credentials are both OK, the install is generally ready for a first real run.
- A healthy next step is usually one of:
  - `ouroboros init`
  - `ouroboros auto`
  - `ouroboros plugin list`

## Useful correction discovered in session
- Plugin management is under `ouroboros plugin ...` (singular), not `ouroboros plugins ...`.
