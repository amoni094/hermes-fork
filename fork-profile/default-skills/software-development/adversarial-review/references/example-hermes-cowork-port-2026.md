# Example: Adversarial Review — Hermes → Cowork Port (2026)

A worked example of the adversarial-review skill applied to a cowork port project.

## Findings

- **Contradiction**: Platform Watchdog prompt told Cowork to ping `http://127.0.0.1:3002`; connectors/README said VMs can't reach localhost. ✗
  - Fix: Rewrite to check externally reachable endpoints only, move localhost reference to explanatory note.
- **Placeholder literals**: 7 task prompts used `YYYY-MM-DD.md` verbatim in code blocks. ✗
  - Fix: Rename to `<TODAY>` with inline substitution instruction.
- **Count drift**: CLAUDE.md ~185, README 179, catalog 179. ✗
  - Fix: Verify actual count (185), update all three documents.
- **Missing specs**: firecrawl-watchdog and hermes-mutation-gate-watch had no documented Cowork equivalent. ✗
  - Fix: Add both to scheduled-tasks/README.md with explicit "not portable" + nearest Cowork alternative.
- **Platform statement**: Cowork = macOS/Windows; source agent = Linux. Not stated in README intro. ✗
  - Fix: Add platform support statement to README and CLAUDE.md front-matter.

## Verification Script

```bash
python3 - <<'EOF'
import re, pathlib, sys
fails = []

# No localhost in code blocks
for f in pathlib.Path('.').rglob('*.md'):
  src = f.read_text()
  for b in re.findall(r'```.*?```', src, re.DOTALL):
    if '127.0.0.1' in b: fails.append(f'localhost in code: {f}')

# No bare YYYY-MM-DD.md in code blocks
for f in pathlib.Path('.').rglob('*.md'):
  src = f.read_text()
  for b in re.findall(r'```.*?```', src, re.DOTALL):
    if re.search(r'YYYY-MM-DD\.md', b): fails.append(f'literal date in code: {f}')

# Count consistency
readme_count = int(re.search(r'(\d+)', open('README.md').read()).group(1)) if 'README' in open('README.md').read() else 0
claude_count = int(re.search(r'(\d+)', open('CLAUDE.md').read()).group(1)) if '185' in open('CLAUDE.md').read() else 0
if readme_count and claude_count and readme_count != claude_count:
  fails.append(f'Count mismatch: README {readme_count}, CLAUDE {claude_count}')

# All 6 jobs documented
for job in ['hourly-chat-sync', 'memory-audit', 'platform-watchdog', 'skillspector', 'firecrawl', 'mutation-gate']:
  if not any(job in f.read_text() for f in pathlib.Path('scheduled-tasks').rglob('*.md')):
    fails.append(f'Missing job spec: {job}')

if fails:
  for f in fails: print(f'FAIL: {f}')
  sys.exit(1)
else:
  print('OK: All checks passed')
EOF
```
