# Adversarial Pass Pitfalls — Aug 2026

Lessons from the Aug 18 2026 recursive adversarial pass of the full
skill/topology/cron/runtime/memory system. Each entry is a false positive or
structural issue that the audit methodology missed and that a future pass must handle.

---

## 1. `\n` corruption scan: code-block context awareness (CONFIRMED FP CLASS)

**Symptom:** A naive `r'\n' in content` or `line.count('\\n') > 0` regex flags 11
skills as "structurally corrupted" when 0 are actually corrupted.

**Root cause:** Skills that *document* escape sequences in prose trigger the check:
- Shell format strings: `printf '%d\n' 0x8E`
- Windows line endings: `\r\n`
- PTY mode docs: `\r vs \n`
- Meta-documentation about the corruption pattern itself

**Fix: context-aware scan — only flag outside code blocks AND long lines:**

```python
import glob, os
base = "/var/home/rainbow/.hermes/skills"
for path in glob.glob(base + "/**/SKILL.md", recursive=True):
    if '/.archive/' in path or '/.curator/' in path: continue
    content = open(path).read()
    if r'\n' not in content: continue
    in_code = False
    for i, line in enumerate(content.split('\n'), 1):
        if line.strip().startswith('```'): in_code = not in_code
        if not in_code and r'\n' in line and len(line) > 300 and line.count(r'\n') > 2:
            print(f"{os.path.basename(os.path.dirname(path))}:{i}: {line[:80]}")
```

**Rule:** A hit is real corruption only when ALL THREE are true:
1. Line is outside a fenced code block
2. Line is >300 chars
3. >2 `\n` sequences on the same line

Documented escape sequences in prose are intentional — do NOT "fix" them.

---

## 2. Root-level skill placement anti-pattern (STRUCTURAL BUG)

**Symptom:** A skill's `SKILL.md` lives at `skills/<name>/SKILL.md` (category root)
instead of the correct `skills/<category>/<name>/SKILL.md` (nested). This makes the
skill show up as a "category with 0 sub-skills" in the category inventory scan,
and the standard `glob("**/*/SKILL.md")` nested check does NOT find it (it's at depth 1,
not depth 2).

**Aug 2026 confirmed instances:**
- `skills/thunderbird-cli-anything/SKILL.md` → should be `skills/email/thunderbird-cli-anything/SKILL.md`
- `skills/computer-use/SKILL.md` → should be `skills/computer-use/computer-use/SKILL.md`

Both were miscategorized this way — one a wrong location entirely, the other the
"category folder IS the skill" pattern.

**Detection query (add to category audit):**
```python
import glob, os
base = "/var/home/rainbow/.hermes/skills"
root_skills = glob.glob(base + "/*/SKILL.md")
for p in root_skills:
    print(f"ROOT-LEVEL SKILL (wrong location): {p.replace(base+'/', '')}")
```
Expected count: 0. Any non-zero result is a structural bug.

**Fix:**
```bash
# Move to correct nested location
mkdir -p skills/<correct_category>/<skill_name>
mv skills/<skill_name>/SKILL.md skills/<correct_category>/<skill_name>/SKILL.md
rmdir skills/<skill_name>
```

**Why the standard ghost-dir scan misses this:** Ghost-dir detection checks for
`SKILL.md` in subdirs of each category dir. A skill at category root is the opposite
— it looks like a category dir with no sub-skills, but actually IS the skill. Add the
root-level check explicitly alongside ghost-dir detection.

---

## 3. L1 memory pipeline timing: minimum gap between extract and promote

**Issue:** `l1-extract-periodic` (180m) and `l1-promote-periodic` were set to 190m —
only a 10-minute gap. If extract takes longer than usual or schedules slip, promote
runs on stale data (previous day's facts, or incomplete current-day facts).

**Validated fix (Aug 2026):** promote rescheduled from 190m → 220m (40m gap). The
downstream `l1-hindsight-promote` stays at 240m (20m after promote, enough for it to
finish scoring and writing staging.md).

**Rule:** L1 pipeline timing floors:
- extract → promote gap: minimum 40m
- promote → hindsight-promote gap: minimum 20m
- These are SEQUENTIAL pipeline stages, not redundant duplicates. All three are needed.

**Pipeline summary (correct state as of Aug 2026):**
```
l1-extract-periodic:  every 180m  → writes memory-facts/YYYY-MM-DD.md
l1-promote-periodic:  every 220m  → scores facts, writes staging.md
l1-hindsight-promote: every 240m  → reads staging.md, calls hindsight_retain
```

After any cron schedule change to pipeline jobs, verify the gaps remain above the
minimums. Check with: `hermes cron list` and compute intervals manually.

---

## 4. Ghost category dirs vs ghost sub-dirs vs root-level skills: three distinct checks

The audit must run THREE separate ghost/placement checks — conflating them causes misses:

| Check | What it finds | Detection |
|-------|--------------|-----------|
| Ghost category dirs | Category dirs with no skills anywhere inside | `find skills/<cat> -name SKILL.md | wc -l` == 0 |
| Ghost sub-dirs | Dirs inside a category with DESCRIPTION.md only (no SKILL.md) | `glob(base + "/*/*/")` where no SKILL.md inside |
| Root-level skills | SKILL.md at depth 1 (should be depth 2) | `glob(base + "/*/SKILL.md")` |

All three are structurally distinct. The "ghost category with DESCRIPTION.md only" check
won't catch a root-level skill (it has a SKILL.md but in the wrong location).

**Aug 2026 removals:**
- Ghost category dirs (DESCRIPTION.md only): apple/, data-science/, media/, smart-home/, social-media/, mlops/
- Ghost mlops sub-dirs (DESCRIPTION.md only): mlops/evaluation/, mlops/inference/, mlops/models/
- Ghost productivity sub-dir: productivity/ocr-and-documents/
- Root-level skills (wrong location): thunderbird-cli-anything/, computer-use/ (both fixed)

---

## 5. Project-level script references are not Hermes scripts/ issues

Skills that reference scripts like `~/Religion/scripts/query_corpus.py` or
project-specific `scripts/validate_contract.py` are pointing at project-local scripts,
not Hermes infrastructure scripts. Do NOT flag these as "missing from `~/.hermes/scripts/`".

**Triage rule:** Before flagging a script reference as missing, check:
1. Is the path absolute and outside `~/.hermes/scripts/`? → project script, not Hermes
2. Is it a relative path in a code example? → documentation, not a real dependency
3. Does the skill's context (religion corpus, ouroboros harness) explain the path? → yes

Only flag scripts referenced in `no_agent=True` cron job `script:` fields and not
found in `~/.hermes/scripts/` as real issues.
