# Hermes → Cowork Adversarial Review Checks

Reference script and findings from porting a live Hermes agent to Claude Cowork.

## Actual verification commands used

```bash
#!/bin/bash
set -e
REPO=/var/home/rainbow/hermes-to-cowork-port
echo "=== Ad-hoc adversarial review verification ==="

echo "[1] localhost:3002 not in any task prompt code block (ok in notes)"
# Check only inside ``` code fences (task prompts), not in prose/notes
python3 - <<'PYEOF'
import re, sys, pathlib
bad = []
for f in pathlib.Path('/var/home/rainbow/hermes-to-cowork-port').rglob('*.md'):
    src = f.read_text()
    # extract code blocks only
    blocks = re.findall(r'```.*?```', src, re.DOTALL)
    for b in blocks:
        if '127.0.0.1:3002' in b:
            bad.append(str(f))
if bad:
    print('FAIL: localhost in code block:', bad); sys.exit(1)
else:
    print('OK: no localhost:3002 in task prompt code blocks')
PYEOF

echo "[2] YYYY-MM-DD literal not bare in task prompt code blocks"
python3 - <<'PYEOF'
import re, sys, pathlib
bad = []
for f in pathlib.Path('/var/home/rainbow/hermes-to-cowork-port').rglob('*.md'):
    src = f.read_text()
    blocks = re.findall(r'```.*?```', src, re.DOTALL)
    for b in blocks:
        if re.search(r'YYYY-MM-DD\.md', b):
            bad.append(str(f))
if bad:
    print('FAIL: literal YYYY-MM-DD.md in code block:', bad); sys.exit(1)
else:
    print('OK')
PYEOF

echo "[3] Skills count consistent (185)"
grep -q "185" "$REPO/CLAUDE.md" && grep -q "185" "$REPO/README.md" && echo "  OK" || { echo "  FAIL"; exit 1; }

echo "[4] Platform warning present"
grep -q "macOS or Windows" "$REPO/README.md" && echo "  OK: README" || { echo "  FAIL"; exit 1; }
grep -q "macOS and Windows" "$REPO/CLAUDE.md" && echo "  OK: CLAUDE.md" || { echo "  FAIL"; exit 1; }

echo "[5] All 6 cron jobs documented"
for job in "hourly-hermes-chat-sync" "hermes-memory-drift-audit" "hermes-platform-watchdog" "skillspector-guard" "firecrawl-watchdog" "hermes-mutation-gate-watch"; do
  grep -q "$job" "$REPO/scheduled-tasks/README.md" && echo "  OK: $job" || { echo "  FAIL: $job"; exit 1; }
done

echo "[6] Skills-catalog portability warning"
grep -q "Not all skills are portable" "$REPO/skills-catalog/README.md" && echo "  OK" || { echo "  FAIL"; exit 1; }

echo "[7] .gitignore covers macOS+Windows artifacts"
grep -q ".DS_Store" "$REPO/.gitignore" && grep -q "Thumbs.db" "$REPO/.gitignore" && echo "  OK" || { echo "  FAIL"; exit 1; }

echo "[8] Git clean, remote up to date"
cd "$REPO"
[[ -z "$(git status --short)" ]] && echo "  OK: clean" || { echo "  FAIL: dirty"; exit 1; }

echo ""
echo "=== All checks passed (ad-hoc verification, not a test suite) ==="
```

## Findings and fixes

### CRITICAL — self-contradiction

**Finding:** Platform Watchdog task prompt instructed Cowork to ping `http://127.0.0.1:3002` (Firecrawl service).
Connectors/README.md explicitly states: "Cowork's isolated VM has no access to host-local services."

**Fix:** Rewrote task prompt to check **externally reachable endpoints only**. Moved localhost reference to explanatory note marked "Portability note," not executable task prompt.

**Lesson:** When a target platform has explicit connector restrictions (e.g., "no localhost"), scan task prompts for *instructions* that violate those restrictions, not just *statements about* them. A prompt that says "do X" overrides a doc that says "X is blocked."

### Count drift

**Finding:**
- CLAUDE.md: ~185 items
- README.md: 179 items
- skills-catalog/README.md: 179 items (inline count and actual files)

**Root cause:** Skill SKILL.md descriptions used block-YAML (```yaml) which the count parser silently skipped.

**Fix:** Verified actual count (185), updated all three documents.

**Lesson:** When docs claim "N items," enumerate them once from source, then hard-check all documents that reference the count. Use a one-liner script: `grep "Total.*:" README.md && ls -1 skills-catalog/*.md | wc -l`.

### Placeholder literals in code blocks

**Finding:** 7 task prompts across scheduled-tasks/ and workflows/ used `YYYY-MM-DD.md` verbatim in code blocks (inside ```...```), not as a placeholder to be substituted.

**Fix:** Renamed to `<TODAY>` with inline instruction: "Substitute <TODAY> with YYYY-MM-DD format."

**Lesson:** If docs use placeholders, validate they're never bare in code blocks — always pair with a substitution instruction visible in the same code fence. Check both task prompts and workflow examples.

### API reference to non-existent interface

**Finding:** Session Sync task prompt said: "Review the most recent 10 Cowork session artifacts using the enumerable Artifacts API."

**Problem:** Cowork has no `getSessionList` or equivalent enumerable API. The user can inspect artifacts in the history sidebar, but there's no programmatic enum endpoint.

**Fix:** Replaced with: "Review files you created/modified today in ~/Documents, ~/Desktop, ~/Downloads. Write summary to Obsidian vault." Added explanatory note: "Cowork does not expose enumerable session artifacts API; uses folder inspection instead."

**Lesson:** When translating task prompts, verify every API reference exists and is accessible in the target platform. If it doesn't, replace with a concrete workaround (file inspection, user input, etc.) and document the gap.

### Missing job specs

**Finding:** Cowork scheduled-tasks README documented 4 of 6 Hermes cron jobs.
Missing:
1. firecrawl-watchdog (every 10m)
2. hermes-mutation-gate-watch (every 1440m/daily)

**Fix:** Added both to scheduled-tasks/README.md with explicit "not portable" explanations and nearest Cowork equivalents.

**Lesson:** Enumerate all source items at the start. Mark each one as "portable," "not portable + workaround," or "documented elsewhere." Don't silently omit items — a missing item in the port is a portability gap, not cleanup.

### Platform blindspot

**Finding:** Cowork runs on **macOS and Windows only**. Source agent (Hermes) runs on **Linux (Fedora Silverblue).**

This was documented in scattered places (connectors notes, skills-catalog footer) but not stated upfront in README or CLAUDE.md.

**Fix:** Added prominent platform statement in README intro and CLAUDE.md preamble.

**Lesson:** For cross-platform ports, state the source and target platforms in the README headline or opening paragraph. Don't bury it in subsections.

### Missing cross-platform .gitignore entries

**Finding:** .gitignore covered Linux/Hermes artifacts (.env, *.token, auth.json) but not macOS/Windows artifacts (.DS_Store, Thumbs.db).

**Fix:** Added both to .gitignore.

**Lesson:** When porting to a different OS family, update the artifact ignore list to cover the new platform's temporary/system files.

---

## When to run this checklist

Use this reference after porting an agent/config/code across platforms:

1. **Before pushing to GitHub**, run the verification script above.
2. **If any check fails**, apply the corresponding fix pattern above.
3. **Commit fixes together** with a message describing what contradictions, gaps, and literals were found and resolved.
4. **Verify again** to confirm all checks pass.

This is **ad-hoc verification**, not a test suite. Pair it with domain-specific tests if the port includes executable code.
