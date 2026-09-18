# Daily Note Discovery Worked Example

## Scenario
Vault at `/var/home/rainbow/Documents/SecondBrain/` uses a non-standard daily-note directory structure. When you attempt to read today's note (2026-07-07) from the hardcoded path `/var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-07.md`, it returns "not found". The daily-note directory could be any of: `10 Daily/`, `02 Daily Notes/`, `memory/`, or other variants used by different vault templates.

## Solution: Search-based discovery

1. **Run search_files immediately after the "not found" error** (do not attempt multiple read_file retries):
   ```
   search_files(
     target='files',
     path='/var/home/rainbow/Documents/SecondBrain',
     pattern='*2026-07-07*'
   )
   ```
   This returns results like:
   ```
   /var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-07.md
   /var/home/rainbow/Documents/SecondBrain/memory/2026-07-07.md
   /var/home/rainbow/Documents/SecondBrain/01 Daily Notes/2026-07-07.md
   ```

2. **Identify the canonical daily-note path** from the results:
   - If multiple date-matching files exist, prefer the directory that already contains recent siblings (e.g., if `10 Daily/` has 2026-07-06.md and 2026-07-05.md, that's the canonical daily-note directory).
   - If multiple equally-populated candidates exist, pick the alphabetically-first one (or ask the user if ambiguity is genuinely unresolved).

3. **Use the discovered path for all subsequent reads/writes in the sync run**:
   - Update your mental model: "daily notes live at `/var/home/rainbow/Documents/SecondBrain/10 Daily/`"
   - Read/write today's note using that path
   - Read yesterday's note (if needed for comparison) using the same directory
   - Do not re-search on subsequent operations; the discovery was one-time per sync run

4. **Why this matters**:
   - Obsidian vaults can migrate directories, users can customize layouts, and templates vary.
   - Hardcoding a single path (e.g. `10 Daily/`) breaks when the vault structure differs.
   - Search-based discovery is fast (milliseconds) and avoids repeated failed reads.
   - A single search + directory inference is more efficient than trying multiple hardcoded paths.

## Real execution from 2026-07-07

Actual commands executed:
```bash
# Step 1: Resolve date
date '+%Y-%m-%d %H:%M:%S %Z'  # → 2026-07-07 12:35:36 AEST

# Step 2: Read the live-sync note (exists, found)
read_file(path='/var/home/rainbow/Documents/SecondBrain/04 Resources/Hermes Chat Live Sync.md')

# Step 2b: Attempt to read today's daily note (fails)
read_file(path='/var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-07.md')
# → File not found; returns empty output

# Step 2c: Discover daily-note directory structure
search_files(
  target='files',
  path='/var/home/rainbow/Documents/SecondBrain',
  pattern='*.md'
)
# Returns 30 files, including:
# /var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-06.md
# /var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-05.md
# /var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-04.md
# ... (establishing `10 Daily/` as the canonical directory)

# Step 3: Now that the directory is known, proceed with full rewrite
# (no further searches needed; 2026-07-07.md will be created in discovered path)
```

## Pitfall avoidance

- **Do not retry read_file with offset/limit on a not-found error** — the file does not exist, offset/limit will still fail.
- **Do not hardcode vault structure assumptions across sessions** — different vaults use different conventions; discover per run.
- **Do not assume "if the file doesn't exist, create it without discovering the directory first"** — you might create `/var/home/rainbow/Documents/SecondBrain/2026-07-07.md` in the vault root when it should be in `/var/home/rainbow/Documents/SecondBrain/10 Daily/2026-07-07.md`.
- **Once discovered, the path is canonical for the entire sync run** — do not re-search or re-query for subsequent operations on the same daily note or adjacent dates.
