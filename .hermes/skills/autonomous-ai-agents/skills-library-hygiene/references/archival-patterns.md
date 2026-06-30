# Archival Patterns and Candidates

This document codifies common archival patterns discovered through real library audits. Use this to quickly triage candidates instead of re-auditing every run.

## Pattern 1: No CLI / Tool Installed

**Candidates**: `xurl` (X/Twitter CLI), `yuanbao` (Yuanbao CLI), any skill wrapping a tool that's listed in the description but not installed on your host.

**Detection**: Run `which <toolname>` for the tool mentioned in the skill description. If exit code is 1 (not found), the skill cannot work on this host.

**Action**: Archive to `.archive/misc/<name>`. Rationale: the skill exists but its primary tool is absent. If the user installs the tool later, the skill can be recovered. Do NOT delete permanently.

**Example**:
```bash
which xurl  # not installed
which yuanbao  # not installed
# Archive both
mv ~/.hermes/skills/social-media/xurl ~/.hermes/skills/.archive/misc/
```

## Pattern 2: Cosmetic / Non-Work Skills

**Candidates**: `petdex` (animated mascot installer), theming/UI-only skills without tangible work output.

**Detection**: Read the SKILL.md. If the skill's primary purpose is UI customization, character selection, or aesthetic preference with no functional work output, it's cosmetic.

**Action**: Archive to `.archive/misc/<name>`. Rationale: Hermes agent sessions are work-focused. Mascot selection adds cognitive load to skill routing without contributing to work. Keep it in the background if the user requests it, but don't inject it into every session.

## Pattern 3: Jailbreak / Red-Teaming Skills

**Candidates**: `godmode` (LLM jailbreak skill, 403 lines), any skill whose purpose is to circumvent safety guidelines.

**Detection**: Read the SKILL.md and look for descriptions like "Jailbreak LLMs", "bypass", "override constraints", "GODMODE", "ULTRAPLINIAN".

**Action**: Archive to `.archive/red-teaming/<name>`. Rationale: jailbreak skills are specialized attack vectors for red-teaming contexts, not normal work. They should NOT be in the default skill set injected into every session. If the user is doing adversarial testing, they can explicitly load `/skill godmode` — do not make it auto-available.

## Pattern 4: Thin Pointer / Router Skills

**Candidates**: `superpowers-bootstrap` (just says "load using-superpowers"), any skill that primarily redirects to another skill without adding new steps or context.

**Detection**: Read the SKILL.md. If the body is < 50 lines and the only meaningful instruction is "load this other skill", it's a thin pointer.

**Action**: Archive to `.archive/misc/<name>`. Rationale: Thin pointers duplicate the work of the destination skill. In Phase 4 (architecture), a router skill should have explicit decision logic (e.g., "IF you're refactoring code, THEN check test-driven-development first"). A pointer that just says "load X" is better handled by `related_skills` annotation in the calling skill. Remove the redundant middleman.

## Pattern 5: One-Time Task / Migration Skills

**Candidates**: `porting-superpowers-to-hermes` (describes a one-time port already completed), `hermes-agent-skill-authoring` for a specific project port, migration-specific skills that document how to move from system A to system B when that migration is one-time.

**Detection**: Read the SKILL.md. If the trigger is "when you are migrating X to Y" or "when you are porting X", and that porting has already happened and is not a recurring task, it's a one-time-task skill.

**Action**: Archive to `.archive/misc/<name>`. Rationale: The port is done. The next time this migration comes up (in 2 years, on a different project), the old skill will be stale and misleading. Create a fresh skill documenting the new migration path when it's needed. One-time-task skills in the active library confuse the skill router — when loading `skills_list()`, the agent has to skip over "how to port Superpowers" to find actual work skills.

**Exception**: If the task is highly recurring (e.g., "how to set up CI/CD for GitHub Actions"), keep it as a class-level skill. The distinction is: "we do this migration every quarter" → keep it; "we did this migration once and moved on" → archive it.

## Pattern 6: Empty Category / Orphaned Dirs

**Candidates**: Directories under `~/.hermes/skills/` that contain only `DESCRIPTION.md` with no `SKILL.md` files.

**Detection**:
```bash
find ~/.hermes/skills -maxdepth 1 -type d | while read d; do 
  c=$(find "$d" -name 'SKILL.md' 2>/dev/null | wc -l)
  if [ "$c" -eq 0 ]; then echo "$d: empty"; fi
done
```

**Action**: Remove the directory. It's dead weight — no skills live under it.

**Example**:
```bash
# After archiving all social-media/* skills
rmdir ~/.hermes/skills/social-media
```

## Frequency

Run this triage once per audit cycle (e.g., quarterly or after a major skill cleanup). Most sessions should NOT re-run this — the patterns are stable. If new candidates appear regularly, it signals that the skill creation bar is too low (skills are being created for things that aren't recurring work).
