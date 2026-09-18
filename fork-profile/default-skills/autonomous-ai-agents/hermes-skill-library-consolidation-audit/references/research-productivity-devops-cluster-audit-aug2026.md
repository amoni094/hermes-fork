# Research / Productivity / Devops / Misc Cluster Audit — August 2026

Cluster: 58 skills across research/, productivity/, note-taking/, email/, devops/,
and software-development/ (selected skills).

Audited by subagent via read_file batch pass. Date: 2026-08-15.

---

## Ghost Skills (HIGH — 5 confirmed missing on disk)

Skills present in the system-prompt index / audit manifest but with no SKILL.md on disk.
All returned `File not found` on read_file.

| Ghost skill name | Category | Notes |
|-----------------|----------|-------|
| `recent-news-briefing` | research | Never created or deleted without absorbed_into record |
| `signal-oriented-research-briefing` | research | Never created or deleted without absorbed_into record |
| `wallust-desktop-theme-integration` | devops | Listed in manifest, absent on disk |
| `wayland-session-troubleshooting` | devops | Absorbed into wayland-session-management (covers startup/teardown/troubleshooting) — no deletion record |
| `waybar-popup-menu-debugging` | devops | Listed in manifest, absent on disk |

**Fix for each:**
- `wayland-session-troubleshooting`: run `skill_manage(action='delete', name='wayland-session-troubleshooting', absorbed_into='wayland-session-management')` to register the deletion properly (even though file is gone — cleans the index).
- `recent-news-briefing` / `signal-oriented-research-briefing`: either recreate as a unified news-briefing skill, or delete both index entries. If recreated, scope `recent-news-briefing` to "daily current-event briefings" and `signal-oriented-research-briefing` to "signal-to-action pipeline" — they serve different trigger conditions.
- `wallust-desktop-theme-integration` / `waybar-popup-menu-debugging`: create minimal stubs or delete from index.

**grep to find all related_skills references to these ghosts:**
```bash
grep -rn 'recent-news-briefing\|signal-oriented-research-briefing\|wallust-desktop\|wayland-session-troubleshooting\|waybar-popup' \
  ~/.hermes/skills/ --include='*.md'
```

---

## Structural Defects (bundled skills — cannot patch autonomously)

These require `hermes curator adopt <name>` before an autonomous agent can patch them.
Flag for foreground session resolution.

### email-inbox-triage (BUNDLED)
- **Stale reference**: `thunderbird-cli-anything` mentioned twice in procedure as "currently disabled — fall back to email-compose-and-send". The tool has been removed; the references add confusion.
- **Fix**: Remove both mentions of `thunderbird-cli-anything`. Replace with direct reference to `email-compose-and-send` for send commands.

### weekly-review-planning (BUNDLED)
- **Duplicate step numbering**: Two steps numbered `### 5.` — "Reconcile active projects" and "Review waiting and commitments". Steps 6 and 7 follow correctly after the duplicates, making procedure numbering broken.
- **Fix**: Rename second `### 5.` to `### 6.` and shift subsequent steps to `### 7.` and `### 8.`.

### meeting-action-items (BUNDLED)
- **Missing sibling pointer**: `related_skills` does not include `document-to-action-items`, which is its closest sibling (both extract obligations/owners/deadlines from content).
- **Fix**: Add `document-to-action-items` to `related_skills`.

### node-inspect-debugger (BUNDLED)
- **Dual related_skills**: Has two inconsistent `related_skills` blocks — `metadata.hermes.related_skills: [systematic-debugging, python-debugpy]` (semantically correct) and top-level `related_skills: [verification-before-completion, plan]` (generic). Both are in frontmatter YAML.
- **Fix**: Consolidate to single top-level `related_skills: [python-debugpy, systematic-debugging, verification-before-completion]`.

### python-debugpy (BUNDLED)
- **Dual related_skills**: Same issue as node-inspect-debugger — `metadata.hermes.related_skills: [systematic-debugging, node-inspect-debugger]` vs top-level `related_skills: [verification-before-completion, plan]`.
- **Fix**: Consolidate to single top-level `related_skills: [node-inspect-debugger, systematic-debugging, verification-before-completion]`.

### document-layout-design (BUNDLED)
- **Non-standard frontmatter key**: Has both `triggers:` (list, standard) and a separate `trigger:` (string, non-standard at line 13). The `trigger:` string duplicates/contradicts the description.
- **Fix**: Remove the `trigger:` key. Its content is redundant with `description:` and `triggers:`.

### obsidian (BUNDLED — note-taking/)
- **Missing frontmatter handoff**: Skill body has an excellent inline pointer to `obsidian-research-ingestion` (in a blockquote at line 18), but `related_skills` in frontmatter does not include it. Structured metadata won't surface the sibling automatically.
- **Fix**: Add `obsidian-research-ingestion` to frontmatter `related_skills` array.

---

## Structural Defects (non-bundled, fixable)

### knowledge-corpus-architecture (software-development/)
- **Duplicate section header**: `### 3. Chunking strategy:` appears at both line 161 and line 207. The first covers adaptive 5-metric framework (newer), the second covers legacy fixed-size recipe (older).
- **Fix**: Retitle line 207 section to `### 3b. Legacy fixed-size chunking recipe` to distinguish from the adaptive framework section above it.

---

## Overlap / Consolidation Findings (MED)

### document-to-action-items ↔ meeting-action-items
- ~50% shared procedure (evidence gathering, normalize fields, reconcile, approval batch).
- Distinction: formal documents (contracts, briefs) vs meeting transcripts.
- **Recommendation**: Add mutual exclusion pointers in each skill's "When to Use" section. Do NOT merge — the input modality difference is meaningful enough for separate routing.

### pdf ↔ context-safe-pdf-edits
- `context-safe-pdf-edits` contains general ReportLab pitfalls (items 1-10: checkbox signatures, y-axis direction, brand logos, etc.) that apply to any ReportLab task, not just large-script patch safety.
- **Recommendation**: Extract the general ReportLab pitfalls into `document-layout-design/references/pdf-reportlab-recipe.md` (already exists there). Keep `context-safe-pdf-edits` focused on context-safe patching strategy only (the session-stall detection + patch tool discipline sections).

### pdf ↔ document-layout-design (reverse pointer gap)
- `document-layout-design` lists `pdf` in `related_skills` (correct).
- `pdf` does NOT list `document-layout-design` or `context-safe-pdf-edits` in `related_skills`.
- **Fix**: Add both to `pdf`'s `related_skills` (blocked: bundled skill). Flag for foreground.

### knowledge-corpus-architecture ↔ knowledge-graph-corpus-pipeline
- Both cover Religion DB / ChromaDB / RDF knowledge corpus — design patterns vs implementation pipeline.
- Currently no explicit sequencing guide ("load architecture first, then pipeline").
- **Recommendation**: Add `knowledge-graph-corpus-pipeline` to `knowledge-corpus-architecture`'s `depends_on` with a note on load order. The pipeline skill should have `depends_on: [knowledge-corpus-architecture]`.

### domain-research-synthesis (orphaned from news briefing peers)
- With `recent-news-briefing` and `signal-oriented-research-briefing` missing on disk, `domain-research-synthesis` is functioning as the sole research orchestration skill. It overlaps ~30% with `competitor-news-monitor` on the daily-brief pattern.
- **Recommendation**: When recreating the news briefing skills, add explicit handoff pointers from `domain-research-synthesis` to the new skills for "time-boxed current-event briefings".

### officecli triggers too broad
- Trigger: "User asks to create, edit, or read a .docx, .xlsx, or .pptx file" — identical to `docx`/`xlsx` triggers.
- **Recommendation**: Narrow to specifically mention "officecli CLI tool" or "batch/CLI-first Office document editing". Add routing note: officecli for CLI-first operations, docx/xlsx for Python programmatic generation.

### kanban-swarm-nightly-ops misclassified
- Has `user_invocable: false` in frontmatter but description starts with "Use when: Spike/reference" — signals reference material, not procedural skill.
- **Recommendation**: Rewrite description to be trigger-forward: "Use when designing a nightly ops multi-agent swarm with parallel workers, verifier, and synthesizer roles."

---

## Clean Skills (no HIGH/MED findings)

academic-literature-review, agent-reach-discovery, arxiv, arxiv-sweep-findings,
blocked-page-recovery, competitor-news-monitor, defuddle, firecrawl-research,
gold-class, grounded-citations, lecture-transcript-summarization,
llm-agent-memory-pipeline-research, stay-in, suggest-music, visual-document-review,
computational-text-corpus-analysis, box, docx, product-price-monitor,
session-librarian, xlsx, obsidian-research-ingestion, email-compose-and-send,
atomic-desktop-app-installation, fedora-atomic-dotfiles-adaptation,
hermes-agent-independent-update-protocol, hermes-gateway-lifecycle-guard,
linux-thermal-workload-throttling, linux-wifi-stability,
rootless-podman-compose-adaptation, silverblue-system-update-trigger,
silverblue-toolbox-wrapper-bootstrap, local-personal-dashboard,
media-catalog-seed-data, policy-dashboard-workflow, repo1-gateway-workflow,
external-signal-pipeline-recovery, wayland-session-management

---

## Index-vs-Disk Divergence Check Command

Use this in any future cluster audit to catch ghost skills before batch-reading:

```bash
# Check all skill directories in a category for missing SKILL.md
for dir in ~/.hermes/skills/research/*/; do
  if [ ! -f "$dir/SKILL.md" ]; then
    echo "MISSING SKILL.md: $dir"
  fi
done
# Repeat for each category: research, productivity, devops, note-taking, email, software-development
```

Or from Python (usable in execute_code):
```python
import glob, os
base = "/var/home/rainbow/.hermes/skills"
categories = ["research", "productivity", "note-taking", "email", "devops", "software-development", "autonomous-ai-agents", "github", "computer-use", "superpowers"]
for cat in categories:
    for skill_dir in sorted(glob.glob(f"{base}/{cat}/*/")):
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            print(f"MISSING: {skill_dir}")
```
