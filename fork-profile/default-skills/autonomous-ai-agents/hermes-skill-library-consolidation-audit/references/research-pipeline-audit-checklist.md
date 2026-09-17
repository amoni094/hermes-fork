# Research Pipeline Audit Checklist

Validated August 2026. Use when the audit scope is the `research/` skill category
(or any subset of: `academic-literature-review`, `domain-research-synthesis`, `arxiv`,
`arxiv-sweep-findings`, `grounded-citations`, `blocked-page-recovery`, `firecrawl-research`,
`firecrawl-stealth-fallback`, `defuddle`, `hermes-web-provider-configuration`,
`obsidian-research-ingestion`, `llm-agent-memory-pipeline-research`, `agent-reach-discovery`,
`competitor-news-monitor`, `lecture-transcript-summarization`, `hermes-research`,
`trajectory-research-synthesis-to-skills`).

---

## 0. Pre-consolidation overlap map (run before any trigger edits)

The research/ category has 22 skills as of 2026-08-30. The 4-way sweep pipeline cluster
(hermes-research, arxiv-sweep-findings, trajectory-research-synthesis-to-skills,
llm-agent-memory-pipeline-research) is the primary source of trigger ambiguity.

**Role split (must be kept distinct):**

| Skill | Role | Owns what |
|-------|------|----------|
| `hermes-research` | ORCHESTRATOR | Running the weekly sweep pipeline; routing to correct downstream skill |
| `arxiv-sweep-findings` | FINDINGS BANK | Recording/querying what past sweeps found |
| `trajectory-research-synthesis-to-skills` | APPLY | Converting findings into skill patches |
| `llm-agent-memory-pipeline-research` | DEEP DIVE | Memory-specific research; NOT the sweep pipeline |

**Trigger phrasing discipline:**
- `hermes-research`: "run the [weekly] research pipeline/sweep", "what's new in agent research"
- `arxiv-sweep-findings`: "what did sweep N find", "research findings bank", "what papers are pending"
- `trajectory-research-synthesis-to-skills`: "apply research findings AS SKILL PATCHES", "implement a paper finding in a skill"
- Never use "apply findings" alone — it's ambiguous between arxiv-sweep-findings and trajectory-research-synthesis-to-skills

---

## 1. Trigger clarity and routing correctness

Check for overlap and missing NOT-triggers between all pipeline-adjacent research skills:

| Skill | Primary trigger | Must have NOT-trigger for |
|-------|----------------|--------------------------|
| `arxiv` | Find/search/fetch individual arXiv papers by keyword, ID, or category | multi-institution sweeps → academic-literature-review |
| `academic-literature-review` | Structured survey across institutions, geographies, technique clusters | individual paper lookup → arxiv; community/tool research → domain-research-synthesis |
| `domain-research-synthesis` | Tools/frameworks/community consensus; GitHub stars; domain knowledge banks | academic paper surveys → academic-literature-review; single arXiv lookup → arxiv; news → competitor-news-monitor; product hunt → product-availability-search |
| `arxiv-sweep-findings` | Query what past sweeps found; findings bank | searching arXiv → arxiv; running the sweep → hermes-research; applying patches → trajectory-research-synthesis-to-skills |
| `hermes-research` | Run the weekly pipeline; what's new in agent research | one-off paper lookup → arxiv; domain research → domain-research-synthesis; query past findings → arxiv-sweep-findings; applying patches → trajectory-research-synthesis-to-skills |
| `trajectory-research-synthesis-to-skills` | Apply findings AS SKILL PATCHES; implement a paper in a Hermes skill | querying findings → arxiv-sweep-findings; running the sweep → hermes-research |

**Known gap (Aug 2026):** `domain-research-synthesis` triggers include "algorithmic trading
strategies — academic evidence with AU context" — this is academic paper work, not community
consensus, and belongs in `academic-literature-review`. Watch for trigger creep in the
domain-specific section of `domain-research-synthesis`.

---

## 1b. Programmatic trigger-collision scan

Run this before manual review. Scopes the grep to ONLY the `triggers:` block (not
`related_skills`, NOT-trigger clauses, or prose), eliminating false-positive collisions.

```python
import re, subprocess

SKILLS = [
    "hermes-research", "arxiv-sweep-findings",
    "trajectory-research-synthesis-to-skills",
    "llm-agent-memory-pipeline-research",
    "domain-research-synthesis", "academic-literature-review", "arxiv",
]

def extract_triggers(path):
    """Extract ONLY the triggers: block, stopping at the next top-level YAML key."""
    try:
        content = open(path, errors='replace').read()
        fm = content.split('---')[1] if '---' in content else ''
        in_triggers = False
        triggers = []
        for line in fm.split('\n'):
            if re.match(r'^triggers:', line):
                in_triggers = True; continue
            if in_triggers:
                if re.match(r'^[a-z]', line):  # new top-level key
                    break
                m = re.match(r'^\s+- (.+)', line)
                if m:
                    t = m.group(1).strip().strip('"').lower()
                    # Skip NOT-FOR entries (they are counter-triggers, not positive triggers)
                    if not t.startswith('not '):
                        triggers.append(t)
        return triggers
    except Exception as e:
        return []

import glob
SKILL_ROOT = "/var/home/rainbow/.hermes/skills"

positive_triggers = {}
for skill in SKILLS:
    paths = glob.glob(f"{SKILL_ROOT}/**/{skill}/SKILL.md", recursive=True)
    if paths:
        positive_triggers[skill] = extract_triggers(paths[0])

# Find collisions
collisions = []
for a in SKILLS:
    for b in SKILLS:
        if a >= b: continue
        shared = set(positive_triggers.get(a, [])) & set(positive_triggers.get(b, []))
        if shared:
            collisions.append((a, b, shared))

if collisions:
    for a, b, shared in collisions:
        print(f"COLLISION: {a} / {b} -- shared: {shared}")
else:
    print("Zero positive trigger collisions across all 7 skills.")
```

Expected clean output (2026-08-30): `Zero positive trigger collisions across all 7 skills.`

If collisions are found, the fix is always to:
1. Add specificity to one trigger ("run the **weekly** research pipeline" vs "run the pipeline")
2. Move ambiguous triggers to one canonical owner
3. Re-run the scan to confirm zero collisions

---

## 1c. Oscillation risk check

Oscillation = two adjacent skills could both plausibly fire for the same user request,
creating a feedback loop or ambiguous routing. Check each adjacent pair:

| Pair | Oscillation vector | Resolution |
|------|-------------------|------------|
| `domain-research-synthesis` / `product-availability-search` | "product research" could fire either | domain-research = landscape/compare; product-avail = hunt specific variant. NOT-FOR added to domain-research-synthesis |
| `academic-literature-review` / `hermes-research` | Both sweep arXiv | academic-literature-review = ad-hoc user-initiated; hermes-research = 7-category automated weekly pipeline. Trigger language distinct |
| `arxiv-sweep-findings` / `trajectory-research-synthesis-to-skills` | "apply findings" | Fixed: trajectory says "as skill patches"; arxiv-sweep-findings says "query bank" |
| `arxiv` / `hermes-research` | Both return arXiv papers | arxiv = individual paper lookup; hermes-research = 7-category cron sweep. Context (single vs many, ad-hoc vs scheduled) disambiguates |

**Test:** For each pair, write a 5-word user request that could plausibly trigger either.
If the disambiguation depends ONLY on context (not on trigger-word specificity), the
oscillation risk is low. If the triggers themselves are ambiguous, fix the triggers.

---

## 1d. Handoff chain integrity check

For the weekly research pipeline:

```
hermes-research-weekly (cron, no_agent)
    → hermes-research-sweep.py
    → ~/.hermes/cache/research/hermes-research-latest.json
    → hermes-research-apply (cron, agent, job_id: 001715fd293f)
        → loads: hermes-research, trajectory-research-synthesis-to-skills,
                 arxiv-sweep-findings, adversarial-review, verification-before-completion
        → writes: ~/.hermes/cache/research/hermes-research-apply-latest.md
    → pending-improvements-review (cron, context_from=["001715fd293f"])
```

Verify each link:
- [ ] JSON cache path matches between sweep script and apply job prompt
- [ ] apply job's `skills:` list matches what hermes-research skill documents
- [ ] pending-improvements-review has `context_from` pointing to apply job ID
- [ ] No two links in the chain have the same schedule (prevents race)

---

## 2. Fallback chain consistency

The canonical web research fallback chain is:

```
web_search → web_extract → firecrawl → defuddle → blocked-page-recovery
```

Check each research skill for:

- [ ] Does the skill's primary extraction tool match its position in this chain? (`firecrawl-research` should not list `web_search`/`web_extract` as primary — Firecrawl IS the primary, search/extract are upstream discovery tools)
- [ ] Is the full chain documented somewhere the agent can follow? No single skill documented the complete chain as of Aug 2026 — the chain only exists as a fragmented cross-reference across 5 skills
- [ ] Does `blocked-page-recovery` appear in the skill's workflow for pages that fail web_extract AND Firecrawl? (Missing in `arxiv`, `academic-literature-review`, `domain-research-synthesis`)
- [ ] Does `defuddle` appear in `blocked-page-recovery`'s recovery ladder? (Missing as of Aug 2026 — it is only in `related_skills` metadata)
- [ ] Does the skill correctly distinguish "Firecrawl is down" (fallback to web_extract) from "target site is blocking Firecrawl" (use blocked-page-recovery)? The `firecrawl-research` skill has this right; others do not.

**Inversion anti-pattern:** A skill that positions Firecrawl as primary and web_search as
fallback is correct for Firecrawl's own skill but wrong if applied to `arxiv` or
`academic-literature-review`, where web_search is discovery and Firecrawl is extraction fallback.

---

## 3. Research synthesis absorption quality

For each "absorbed" technique, verify it meets the full absorption standard — not just mentioned:

**Full absorption standard (all four must be present):**
1. Named + cited (arXiv ID or equivalent)
2. Core finding in 1–3 sentences
3. Hermes-specific implementation note ("Hermes pattern: ...")
4. Target skill(s) named

**Techniques to check (status as of Aug 2026):**

| Technique | arXiv ID | absorption status | absorbed-in |
|-----------|----------|-------------------|-------------|
| PaSa (parallel paper search) | unconfirmed — verify via search_arxiv.py | ❌ mentioned only; no invocation pattern, no decision rule | `arxiv`, `academic-literature-review` refs |
| OpenScholar (citation grounding) | N/A (Nature 2025) | ❌ mentioned only; no API endpoint, no when-to-prefer rule | `arxiv`, `academic-literature-review` refs |
| SPAR (structured paper retrieval) | N/A (Semantic Scholar 2025) | ❌ indistinguishable from existing S2 steps | `academic-literature-review` refs |
| Agentic RAG survey | arXiv:2501.09136 | ❌ citation only; taxonomy classes listed, no Hermes implementation note | `academic-literature-review` refs |
| Context interference mitigation | arXiv:2608.10743 | ✅ fully absorbed | `domain-research-synthesis` SKILL.md lines 321–333 |
| Self-ontology query expansion | arXiv:2608.11030 | ⚠️ split-absorbed: in `domain-research-synthesis` body BUT also in Blocked Patches as pending | `domain-research-synthesis`, `arxiv-sweep-findings` |

**PaSa arXiv ID**: Primary arXiv ID unconfirmed as of Aug 2026 (noted in
`academic-literature-review/references/research-master-synthesis-2026.md` line 271).
Verify with: `python3 ~/.hermes/skills/research/arxiv/scripts/search_arxiv.py "PaSa paper search agent bytedance"`

---

## 4. Reference file duplication check

High-risk duplication pairs to check at byte/content level:

| File A | File B | Risk area |
|--------|--------|-----------|
| `domain-research-synthesis/references/agent-memory-topology-research-2026-08.md` | `academic-literature-review/references/agent-memory-architecture-6topics-2025-2026.md` + `agent-memory-aug2026.md` | Agent memory topology papers (Aug 2026 sweep) |
| `domain-research-synthesis/references/neurosymbolic-ai-landscape-2026.md` | `academic-literature-review/references/neurosymbolic-ai-research-2026.md` | NeSy/neurosymbolic AI landscape |

`domain-research-synthesis` SKILL.md also directly cross-references `academic-literature-review`
reference files (lines 297–311) — this is intentional pointer discipline, not duplication.
Only the reference FILES themselves need a byte-level diff.

**Duplicate body content pattern (2026-08-30):**
When slimming a deep-dive skill (e.g. `llm-agent-memory-pipeline-research`), check whether
its "research methodology" body section is verbatim from a sibling skill
(e.g. `academic-literature-review`). If yes, replace with a 2-line pointer. The implementation
roadmap (unique findings, checked items, pitfalls) is worth keeping; generic research process
descriptions are not. Use this test: would a future agent get anything new from this section
that they couldn't get by loading the canonical skill?

---

## 5. arxiv-sweep-findings structural integrity

- [ ] **Sweep boundary log is continuous.** Every sweep from 1 to N has a row. A gap indicates
  untracked work. As of Aug 2026, sweeps 1–10 have no log entries.
- [ ] **Single Blocked Patches table.** SKILL.md must have exactly one `## Blocked Patches`
  section. Duplicate sections (one per sweep) create split-state and false "still pending" signals.
- [ ] **No split-absorbed entries.** Before adding a blocked-patches row, check whether the
  technique already appears in the target skill's SKILL.md body. If yes, close the row, don't add.
- [ ] **Route table completeness.** Every HIGH/MED finding has a named target skill. "Hermes pattern:
  invest in memory topology" with no target skill is incomplete.
- [ ] **arXiv IDs are confirmed.** Check each ID in the sweep reference files exists on arxiv.org.
  Unconfirmed IDs (noted in source files) must be verified or marked `[UNCONFIRMED]`.
- [ ] **Description and triggers don't claim the apply role.** As of 2026-08-30, the description
  must say "findings bank / query what past sweeps found" — NOT "apply sweep findings to skills".
  The apply role belongs to trajectory-research-synthesis-to-skills.

---

## 6. Missing-skill disk check

Before auditing any research skill's content, verify it exists on disk:

```bash
for skill in defuddle competitor-news-monitor lecture-transcript-summarization \
             obsidian-research-ingestion firecrawl-stealth-fallback \
             hermes-web-provider-configuration agent-reach-discovery grounded-citations \
             hermes-research trajectory-research-synthesis-to-skills; do
  path=$(find ~/.hermes/skills -name 'SKILL.md' -path "*/$skill/*" 2>/dev/null | head -1)
  if [ -z "$path" ]; then
    echo "MISSING: $skill"
  else
    echo "OK: $skill"
  fi
done
```

As of Aug 2026, `defuddle`, `competitor-news-monitor`, `lecture-transcript-summarization`,
and `obsidian-research-ingestion` returned no disk results via search_files. These are
referenced in `related_skills` fields of multiple extant skills. If they are missing,
the related_skills references in `firecrawl-research`, `blocked-page-recovery`, and
`academic-literature-review` are dead cross-references.

---

## 7. Knowledge-bank creep check

Research skills are prone to accumulating unrelated content via `catastrophic remembering`
(arXiv:2608.11095 — instruction files grow 226% over lifetime without active pruning).

**High-risk skill:** `firecrawl-research` (523 lines, 26KB as of Aug 2026). Lines 99–141
contain a Chinese/Japanese vision PDF parser knowledge bank (MinerU2.5, PaddleOCR-VL,
Dolphin, SemCAFE, CrediBench) with no relationship to "use local Firecrawl for web
extraction." This content belongs in `academic-literature-review` or
`domain-research-synthesis` references.

**Check:** For each research skill, identify any section > 5KB that is a knowledge bank
(paper lists, comparison tables, stats) rather than procedural steps. If found, extract
to `references/[topic].md` and replace with a 2-line pointer.

---

## 8. Broken cross-reference check (programmatic)

Check that every skill name in `related_skills` blocks actually exists on disk.
This catches dead references introduced when skills are renamed or removed.

```python
import glob, os, re, yaml

SKILL_ROOT = "/var/home/rainbow/.hermes/skills"

# Build set of all real skill names
real_names = set()
for path in glob.glob(SKILL_ROOT + "/**/SKILL.md", recursive=True):
    if '/.archive/' in path or '/.curator/' in path: continue
    try:
        parts = open(path, errors='replace').read().split('---')
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            name = fm.get('name', '').strip()
            if name:
                real_names.add(name)
            # Also accept the directory name as a valid alias
            real_names.add(os.path.basename(os.path.dirname(path)))
    except: pass

# Check each skill's related_skills
broken = []
for path in glob.glob(SKILL_ROOT + "/**/SKILL.md", recursive=True):
    if '/.archive/' in path or '/.curator/' in path: continue
    try:
        parts = open(path, errors='replace').read().split('---')
        if len(parts) < 3: continue
        fm = yaml.safe_load(parts[1]) or {}
        skill_name = fm.get('name', os.path.basename(os.path.dirname(path)))
        for ref in (fm.get('related_skills') or []):
            if isinstance(ref, str) and ref.strip() and ref not in real_names:
                broken.append((skill_name, ref))
    except: pass

if broken:
    print(f"{len(broken)} broken references:")
    for skill, ref in sorted(broken):
        print(f"  {skill} -> {ref}")
else:
    print(f"Zero broken references across {len(real_names)} skills.")
```

Expected: zero broken references. Run after any rename or consolidation pass.

---

## Overlap notes for background curator

These skill pairs were flagged for potential consolidation during the Aug 2026 audit:

- `firecrawl-research` ↔ `firecrawl-stealth-fallback`: overlapping scope on Firecrawl
  anti-bot escalation. The stealth-fallback skill is in `autonomous-ai-agents/` (not
  `research/`), which may indicate it was incorrectly categorized at creation time.
- `academic-literature-review` (44 reference files) ↔ `domain-research-synthesis` (24
  reference files): agent memory topology and neurosymbolic AI reference files appear in
  both. Not a skills-level overlap, but a reference-file-level duplication.
- `llm-agent-memory-pipeline-research` — review after next consolidation pass. As of
  2026-08-30 it was slimmed (removed verbatim academic-literature-review methodology),
  keeping only the memory-specific implementation roadmap. Its remaining unique value is
  the Priority 1-3 implementation checklist; if that gets absorbed into hermes-research
  category mapping, this skill becomes a candidate for deletion.
