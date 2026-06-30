# Common Broken `related_skills` Patterns and Fixes

## Category 1: Non-existent skills (typos or deleted skills)

### Pattern: Skill was deleted but ref wasn't updated
- **Examples:** `writing-plans` (deleted after merging into `plan`), `hermes-security-preflight` (non-existent)
- **Detection:** `grep -r 'writing-plans' ~/.hermes/skills --include='SKILL.md' | grep related_skills`
- **Fix:** Sed replace in affected skills
  ```bash
  sed -i 's/writing-plans/plan/g' <file>
  sed -i 's/, hermes-security-preflight//g; s/hermes-security-preflight, //g' <file>
  ```
- **Session example:** Deleted `writing-plans` → updated 3 files (`using-superpowers`, `brainstorming`, `executing-plans`)

### Pattern: Skill was renamed but old name still referenced
- **Examples:** `audiocraft` (should be `audiocraft-audio-generation`)
- **Detection:** Check if the name exists: `grep -r "^name: audiocraft$" ~/.hermes/skills --include='SKILL.md'` (empty)
- **Fix:**
  ```bash
  sed -i 's/audiocraft/audiocraft-audio-generation/g' <file>
  ```

## Category 2: Toolsets mistaken for skills

Toolsets are system contexts (`browser`, `terminal`, `file`, `vision`, etc.) that are injected by the runtime, NOT loadable skills. They should never appear in `related_skills`.

- **Examples:** `browser`, `terminal`, `image_gen`, `file`, `vision`, `computer-use`
- **Detection:** 
  ```bash
  grep -rh 'related_skills.*\[.*browser' ~/.hermes/skills --include='SKILL.md' | grep -v '.archive'
  ```
- **Fix:** Remove from array entirely:
  ```bash
  sed -i 's/related_skills: \[browser\]/related_skills: []/g' <file>
  sed -i 's/, browser//g; s/browser, //g' <file>
  ```
- **Session example:** `computer-use` had `related_skills: [browser]` → fixed to empty array

## Category 3: Domain concepts mistaken for skill names

Some refs are actually domain keywords or library names, not skill names.

- **Examples:** `vllm`, `gguf`, `huggingface-tokenizers` (ML inference concepts), `concept-diagrams` (feature idea, not skill)
- **Detection:** 
  ```bash
  grep -r "^name: vllm$" ~/.hermes/skills --include='SKILL.md'  # empty → not a real skill
  ```
- **Fix:** Remove from related_skills:
  ```bash
  sed -i 's/, vllm//g; s/vllm, //g' <file>
  sed -i 's/, gguf//g; s/gguf, //g' <file>
  ```
- **Session example:** `obliteratus` had `[vllm, gguf, huggingface-tokenizers]` as related_skills → removed all three

## Category 4: Completely non-existent skills

Refs to skills that never existed in the first place. Usually historical or typos.

- **Examples:** `debugging-hermes-tui-commands`, `silverblue-desktop-ricing-adaptation`, `native-mcp`, `hermes-video`
- **Detection:** 
  ```bash
  # Collect all actual skill names
  grep -rh '^name:' ~/.hermes/skills --include='SKILL.md' ! -path '*/.archive/*' | sed 's/^name: //' | sort -u > /tmp/real_skills.txt
  
  # Collect all referenced skills
  grep -rh 'related_skills:' ~/.hermes/skills --include='SKILL.md' ! -path '*/.archive/*' \
    | grep -oP '\[.*?\]' | tr ',' '\n' | tr -d '[] ' | sort -u > /tmp/refs.txt
  
  # Find refs not in real skills
  comm -23 /tmp/refs.txt /tmp/real_skills.txt
  ```
- **Fix:** Remove entirely:
  ```bash
  sed -i 's/, debugging-hermes-tui-commands//g; s/debugging-hermes-tui-commands, //g' <file>
  sed -i 's/debugging-hermes-tui-commands//g' <file>  # if it was alone in the array
  ```

## Fixing strategy (safe order)

1. **Scan first, don't touch:** Run the comm diff above and save the output.
2. **Group by skill file:** For each broken ref, find all files that reference it.
3. **Batch fixes by file:** For each file, apply all fixes in one sed pass:
   ```bash
   sed -i 's/ref1/fix1/g; s/, ref2//g; s/ref3, //g; s/, ref4//g' <file>
   ```
4. **Verify after each file:** Load the skill and check `related_skills` in the SKILL.md output.
   ```bash
   skill_view(name="<skill>")  # read the output and confirm the array looks right
   ```

## Examples from this session

### Fixed 16 broken refs across 12 files:
- `hermes-security-preflight` (2 files) — deleted, not a real skill
- `writing-plans` (3 files) — replaced with `plan` (the surviving skill)
- `debugging-hermes-tui-commands` (2 files) — removed, was never created
- `browser` (1 file) — removed from computer-use
- `native-mcp`, `hermes-video`, `image_gen` — removed, domain concepts not real skills
- `vllm`, `gguf`, `huggingface-tokenizers` (3 files) — ML concepts, removed

**Result:** `comm -23` now returns empty, zero broken refs remain.
