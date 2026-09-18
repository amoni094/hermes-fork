# Pass-2 Audit — YAML Patch Regression Patterns (Aug 2026)

Findings from the round-1 → round-2 verification pass over 46 skills.
35 fixes were applied in round-1; pass-2 confirmed 28 clean and found 7 regressions
(3 HIGH, 4 MED) — all introduced or left open by the patches themselves.

---

## HIGH findings (net regressions from round-1 patches)

### 1. Two skills concatenated as one string — `scoped-pr-fix-and-verification`

**File:** `github/scoped-pr-fix-and-verification/SKILL.md`
**Symptom:** `related_skills[2]` = `'split-ci-workflow-change-and-draft-pr verification-before-completion'`
**Root cause:** The round-1 patch (fix 16) appended `verification-before-completion` to the
same line as the preceding list item rather than adding a new `  - ` entry.
**YAML parse result:** `['github-issue-to-pr', 'github-operations', 'split-ci-workflow-change-and-draft-pr verification-before-completion']`
**Effect:** `verification-before-completion` is unreachable from this skill's routing.
**Fix:** Split into:
```yaml
  - split-ci-workflow-change-and-draft-pr
  - verification-before-completion
```

### 2. Stale duplicate `name:` key not removed — `adversarial-review`

**File:** `software-development/adversarial-review/SKILL.md`
**Symptom:** `name: adversarial-review` appears at line 2 AND line 31.
**Root cause:** Round-1 fix 13 added `name:` at the top of the frontmatter (correctly) but
did not remove the pre-existing `name:` buried in the metadata tags block at line 31. A
stale `platforms:` block also leaked out of the metadata indentation alongside it.
**YAML parse result:** Python `yaml.safe_load` picks the LAST duplicate value. Both values are
identical (`adversarial-review`), so no immediate functional breakage — but YAML spec
forbids duplicate keys, and future patches that only touch line 2 will be overridden by
line 31 silently.
**Fix:** Remove `name: adversarial-review` at line 31 and the duplicate `platforms:` block
immediately following it.

### 3. List items embedded inside block scalar — `self-improve-agent`

**File:** `autonomous-ai-agents/self-improve-agent/SKILL.md`
**Symptom:** `boundary_note` is a block scalar (`>`), and the round-1 patch placed three
intended `related_skills` entries inside the block scalar body:
```yaml
boundary_note: >
  ... prose text ...
  - trajectory-risk-guardrail
  - verification-before-completion
  - agent-task-signoff
```
**YAML parse result:** The three `- item` lines are absorbed into the block scalar as literal
text. `related_skills` at top level has only 4 entries: `[ralph-loops, autonomous-agent-loop-design, subagent-driven-development, hermes-self-evolution]`. The three intended entries are invisible to the router.
**Fix:** Remove the three lines from the block scalar and add them as proper entries under
the top-level `related_skills:` list.

---

## MED findings (partial fixes / fixes landed in wrong field)

### 4. Fix landed in `metadata.hermes.related_skills` only — `meeting-action-items`

**File:** `productivity/meeting-action-items/SKILL.md`
**Round-1 fix:** 24 — "document-to-action-items cross-ref added"
**Actual state:**
- `metadata.hermes.related_skills`: `['email-inbox-triage', 'document-to-action-items', 'grounded-citations', 'pdf']` ✓
- Top-level `related_skills`: `['grounded-citations', 'pdf']` ✗ (document-to-action-items absent)
**Effect:** Hermes router uses top-level only. The cross-ref is invisible.
**Fix:** Add `  - document-to-action-items` to the top-level `related_skills:` list.

### 5. Routing entries landed in `metadata.hermes` only — `autonomous-ai-agents`

**File:** `autonomous-ai-agents/autonomous-ai-agents/SKILL.md`
**Round-1 fix:** 5 — "ghost 'auto'/'help' removed, routing entries added"
**Actual state:**
- `metadata.hermes.related_skills`: 13 entries including hermes-agent, hermes-role-pipelines, hermes-acp-routing, trajectory-risk-guardrail, mnemosyne-atp-safety, hermes-swarm-consensus, async-agent-nightshift-patterns, agent-task-signoff, agent-browser-troubleshooting, agent-runtime-stack-debugging, ouroboros-setup-and-health-check
- Top-level `related_skills`: `['autonomous-agent-loop-design', 'verification-before-completion']` (2 entries only)
**Fix:** Merge the 11 metadata.hermes entries into the top-level list.

### 6. Deduplication removed the top-level list entirely — `merge-reconciler`

**File:** `autonomous-ai-agents/merge-reconciler/SKILL.md`
**Round-1 fix:** 2 — "duplicate related_skills key removed"
**Actual state:**
- `metadata.hermes.related_skills`: `['hermes-agent', 'hermes-swarm-consensus', 'dispatching-parallel-agents', 'adversarial-review', 'autonomous-agent-loop-design', 'verification-before-completion']`
- Top-level `related_skills`: `[]` (empty list)
**Root cause:** The dedup pass removed the duplicate key, but appears to have removed
the top-level list (keeping only the nested metadata.hermes copy). All 6 skill
references are now invisible to routing.
**Fix:** Restore a top-level `related_skills:` block with the 6 entries from metadata.hermes.

### 7. Counter-triggers not added as formal key — `hermes-operating-pattern`

**File:** `software-development/hermes-operating-pattern/SKILL.md`
**Note:** This skill is in `software-development/`, NOT `autonomous-ai-agents/` — the
round-1 fix task listed an incorrect path (`autonomous-ai-agents/hermes-operating-pattern/`).
**Round-1 fix:** 10 — "counter-triggers added"
**Actual state:** No `counter_triggers:` YAML key in frontmatter. The description contains
inline disambiguation ("not a single focused workflow. For iterative patch loops use
hermes-coding-review-loop; for routing use workflow-map.") which may have been the
intended fix — but no formal key was added as in `officecli`, `skillopt`, etc.
**Status:** Ambiguous — inline prose disambiguation may be sufficient; a formal key is
cleaner but not breaking.

---

## Verified-clean skills (28 of 35 round-1 fixes confirmed landed correctly)

agent-runtime-loop-patterns, hermes-semantic-skill-routing, harness-first-agent-design,
graphiti-mcp-setup, hermes-skillspector-guard-maintenance, hermes-self-evolution,
agent-task-signoff, messaging-consent-boundaries, requesting-code-review,
github-operations, github-issues, split-ci-workflow-change-and-draft-pr,
skillopt-continuous-improvement, gepa-omni-optimization, symbolic-context-offload,
anthropic-agent-api-patterns, hermes-acp-routing, hermes-memory-surface-selection,
autonomous-agent-loop-design, obsidian, obsidian-research-ingestion, email-inbox-triage,
weekly-review-planning, knowledge-corpus-architecture, node-inspect-debugger,
python-debugpy, officecli, document-layout-design, pdf, kanban-swarm-nightly-ops,
document-to-action-items

Adjacent skills verified clean (all 9): hermes-skill-library-consolidation-audit,
writing-skills, hermes-cowork-port-sync, fable-orchestrate, hermes-config-repo-audit,
knowledge-graph-corpus-pipeline, context-safe-pdf-edits, domain-research-synthesis,
hermes-agent

---

## Validated detection queries (run after any bulk patch session)

```python
import glob, yaml, re

base = "/var/home/rainbow/.hermes/skills"

issues = []
for f in glob.glob(base + "/**/SKILL.md", recursive=True):
    if '/.archive/' in f or '/.curator/' in f:
        continue
    try:
        parts = open(f, errors='replace').read().split('---')
        if len(parts) < 3:
            continue
        fm_text = parts[1]
        data = yaml.safe_load(fm_text) or {}
        name = data.get('name', f)

        # 1. Duplicate top-level keys
        for key in ['name', 'description', 'version', 'related_skills']:
            count = len(re.findall(rf'^{key}:', fm_text, re.M))
            if count > 1:
                issues.append(f"DUPE_KEY '{key}' ({count}x): {name}")

        # 2. Block scalar containing list items
        for key, val in data.items():
            if isinstance(val, str) and '\n- ' in val:
                issues.append(f"BLOCK_SCALAR_LIST_ITEMS in '{key}': {name}")

        # 3. Concatenated skill names in related_skills
        rs = data.get('related_skills') or []
        for entry in rs:
            if isinstance(entry, str) and ' ' in entry.strip():
                issues.append(f"CONCATENATED_ENTRY '{entry}': {name}")

        # 4. Skills only in metadata.hermes (not top-level)
        top = set(data.get('related_skills') or [])
        meta = set((data.get('metadata') or {}).get('hermes', {}).get('related_skills') or [])
        only_meta = meta - top
        if only_meta:
            issues.append(f"META_ONLY_REFS {only_meta}: {name}")

    except Exception as e:
        issues.append(f"PARSE_ERROR {e}: {f}")

for i in issues:
    print(i)
print(f"\nTotal issues: {len(issues)}")
```
