# Archival Log Template

Use this template to document why skills were archived. Store at `~/.hermes/skills/.archive/ARCHIVAL_LOG.md` (or `~/.hermes/profiles/<name>/skills/.archive/ARCHIVAL_LOG.md` if working in a non-default profile).

---

# Skills Archival Log

**Profile:** default  
**Last Audit Date:** [YYYY-MM-DD when archival happened]  
**Audit Intent:** Remove platform-irrelevant, duplicate, or incomplete skills; fix broken refs and wiring gaps.

## Archival Categories

### macOS-Only Skills (Linux host — not applicable)

Archived because this Hermes instance runs on Linux. These skills require macOS APIs or system integrations that do not exist on this platform.

| Skill | Version | Reason | Recovery |
|-------|---------|--------|----------|
| `apple/apple-notes` | 1.0.0 | Requires macOS Notes sync API | If user switches to macOS, recover from `.archive/apple/apple-notes/` |
| `apple/apple-reminders` | 1.0.0 | Requires macOS Reminders sync API | Recover if user switches to macOS |
| `apple/findmy` | 1.0.0 | Requires Apple Find My service (macOS/iOS only) | Not applicable to Linux |
| `apple/imessage` | 1.0.0 | Requires macOS iMessage framework | Recover if user switches to macOS |
| `apple/macos-computer-use` | 1.0.0 | macOS-specific computer automation; use `computer-use` instead | Use `computer-use` on Linux (browser, desktop automation available) |

### Exact Duplicates (Deleted, Content Merged)

Archived because another skill provides identical or near-identical functionality. Content was merged into the survivor skill; the archived skill should not be recovered.

| Archived Skill | Survivor Skill | Merged Content | Date |
|---|---|---|---|
| `superpowers/writing-plans` | `software-development/plan` | Skill authoring guidance, pressure scenarios, TDD workflow for skill documentation. All content folded into `plan` under "Hermes process" section. | 2026-06-30 |
| `autonomous-ai-agents/thunderbird-local-email-workflow` | `media/thunderbird-cli-anything` | Email workflow guidance; existing skill covers broader CLI use. | (prior audit) |

**How to recover:** If you delete the survivor by mistake, these are the originals.

### Incomplete / Dependency Unmet (Archived Pending Tool Install)

Archived because the skill requires external tools not yet installed. Recover this skill after installing the missing dependency.

| Skill | Missing Dependency | Install Command | Recovery |
|-------|-------------------|-----------------|----------|
| `github/codebase-inspection` | `pygount` | `pip install pygount` | After install, recover from `.archive/github/codebase-inspection/` and test with `skill_view(name="codebase-inspection")` |

**Do not delete these**. Archive them instead and create this log entry so a future session knows why.

### Broken Refs Fixed (Not Archived, In-Place Patched)

These skills were NOT archived; instead, their `related_skills` arrays were fixed in place. Listed here for audit trail.

| File | Broken Refs Removed | Fixed With |
|------|-------------------|-----------|
| `superpowers/using-superpowers/SKILL.md` | `writing-plans` | Replaced with `plan` |
| `superpowers/brainstorming/SKILL.md` | `writing-plans` | Replaced with `plan` |
| `superpowers/executing-plans/SKILL.md` | `writing-plans` | Replaced with `plan` |
| `software-development/node-inspect-debugger/SKILL.md` | `debugging-hermes-tui-commands` | Removed (skill does not exist) |
| `software-development/python-debugpy/SKILL.md` | `debugging-hermes-tui-commands` | Removed (skill does not exist) |
| `creative/architecture-diagram/SKILL.md` | `concept-diagrams` | Removed (feature idea, not a skill) |
| `devops/linux-thermal-workload-throttling/SKILL.md` | `silverblue-desktop-ricing-adaptation` | Removed (non-existent) |
| `creative/comfyui/SKILL.md` | `stable-diffusion-image-generation`, `image_gen` | Removed (non-existent, toolset confusion) |
| `autonomous-ai-agents/hermes-agent/SKILL.md` | `native-mcp` | Removed (non-existent) |
| `creative/touchdesigner-mcp/SKILL.md` | `native-mcp`, `hermes-video` | Removed (non-existent) |
| `autonomous-ai-agents/hermes-observability-and-task-ledger/SKILL.md` | `hermes-security-preflight` | Removed (non-existent) |
| `autonomous-ai-agents/hermes-cron-and-agents/SKILL.md` | `hermes-security-preflight` | Removed (non-existent) |
| `computer-use/SKILL.md` | `browser` (toolset, not skill) | Removed from `related_skills: [browser]` → `related_skills: []` |

**Verification:** `comm -23 /tmp/referenced.txt /tmp/existing.txt` returns empty.

## Architectural Decisions

### Security Tools: Opt-In Escalation

Security scanning tools are now positioned as **opt-in escalations** from the default code-review workflow, not hard defaults. See `requesting-code-review` and `workflow-map` for the new routing.

- Default path: lightweight grep-based scan in Step 2 of `requesting-code-review`
- Escalation tools: `semgrep`, `codeql`, `owasp-security`, `fp-check`, `secret-hygiene`, etc.
- Trigger: user intent, risk level, or change type

### Library Stats

| Metric | Before | After |
|--------|--------|-------|
| Active skills | 185 | 169 |
| Archived skills | 16 | 21 (added 5 in this audit) |
| Broken `related_skills` refs | 16 | 0 |

## How to Use This Log

**For future audits:**
- Check this log first before archiving. If a skill is already listed as archived, do not re-archive it.
- If you recover a skill, update this log with the recovery date and reason.

**For debugging broken skills:**
- If a skill loads with errors, check whether it references an archived skill in `related_skills`. See the "Broken Refs Fixed" table above.

**For cross-profile sync:**
- If you run multiple Hermes profiles, each may have its own archival log. A skill archived in `default` may still be active in another profile.

## Recovery Commands

To recover an archived skill:

```bash
# Copy from archive back to active
cp -r ~/.hermes/skills/.archive/<category>/<name> ~/.hermes/skills/<category>/<name>

# Verify
skill_view(name="<name>")

# Update this log
# (add an entry under "Recovered Skills" section below with date and reason)
```

## Recovered Skills

When you recover an archived skill, log it here:

(none yet)

---

**Document created:** 2026-06-30  
**Last updated:** 2026-06-30  
