# Skill Library Adversarial Audit — Methodology & Reference

Worked methodology from a full 143-skill audit pass (2026-07-04).
Use this when running trigger coverage audits, routing correctness checks, or
cross-reference validation across the entire skill library.

---

## Skill Classification Taxonomy

Before auditing, classify all skills into categories — each class has different
correctness criteria and patch strategies:

| Class | Examples | Needs triggers? | Patchable? |
|---|---|---|---|
| Routing candidates | hermes-agent, spike, stay-in, systematic-debugging | Yes — loaded by routing | Yes |
| Slash-command skills | auto, pm, run, cancel, qa, seed, evolve, publish | No — invoked by name | Yes |
| Repo-specific workflows | policy-dashboard-workflow, kanban-orchestrator | No — context-locked | Yes |
| Tool wrappers | arxiv, firecrawl-research, codex, codeql | No — invoked by tool name | Yes |
| Builtins (read-only) | computer-use (depth=1 in skills dir) | N/A | NO |

Heuristic for builtins: `path.count("/") == 1` relative to `~/.hermes/skills/` root.

Full exempt slash-commands list (verified 2026-07-04):
`auto, brownfield, cancel, config, evaluate, evolve, help, humanizer, pm,
publish, qa, ralph, run, seed, simplify-code, songsee, status, tutorial,
unstuck, update, welcome, resume-session, maps, nano-pdf, nab-formatting,
research-document-output`

---

## Bulk Frontmatter Extraction

Extract all skill metadata in one pass with Python:

```python
import re, glob, os, json

base = os.path.expanduser("~/.hermes/skills")
skills = {}

for path in sorted(glob.glob(base + "/**/SKILL.md", recursive=True)):
    if "/.archive/" in path or "/.disabled/" in path:
        continue
    content = open(path).read()
    parts = content.split("---", 2)
    if len(parts) < 3:
        continue
    fm = parts[1]
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    if not name_m:
        continue
    name = name_m.group(1).strip().strip('"\'')
    
    has_triggers = bool(re.search(r'^triggers:', fm, re.MULTILINE))
    has_related = bool(re.search(r'^related_skills:', fm, re.MULTILINE))
    rel = path.replace(base + "/", "")
    depth = rel.count("/")
    
    desc_m = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    desc = desc_m.group(1).strip() if desc_m else ""
    
    skills[name] = {
        "path": path,
        "depth": depth,
        "has_triggers": has_triggers,
        "has_related": has_related,
        "desc": desc[:100],
    }

# Coverage report
local = {k: v for k, v in skills.items() if v["depth"] > 1}
with_trig = sum(1 for v in local.values() if v["has_triggers"])
print(f"Local: {len(local)}, with triggers: {with_trig} ({with_trig*100//len(local)}%)")
```

---

## Adversarial Check Set

Run these five checks after any mass-patch operation:

### 1. Trigger collisions
```python
trig_index = {}
for name, data in skill_map.items():
    for t in data["triggers"]:
        key = re.sub(r'\W+', ' ', t.lower()).strip()[:60]
        trig_index.setdefault(key, []).append(name)
collisions = {k: v for k, v in trig_index.items() if len(v) > 1}
```

### 2. Vague triggers
```python
VAGUE = [r'^use when', r'^any ', r'^general', r'^working on',
         r'^handling ', r'^need help', r'^all .* tasks']
for name, data in skill_map.items():
    for t in data["triggers"]:
        for pat in VAGUE:
            if re.match(pat, t.lower()):
                print(f"VAGUE [{name}]: '{t}'")
```

### 3. Triggers in body (placement error)
```python
body_errors = []
for name, data in skill_map.items():
    content = open(data["path"]).read()
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    if re.search(r'^triggers:', body, re.MULTILINE) and data["has_triggers"]:
        body_errors.append(name)
```

### 4. Broken related_skills references
```python
all_names = set(skill_map.keys())
for name, data in skill_map.items():
    content = open(data["path"]).read()
    fm = content.split("---", 2)[1]
    rel_m = re.search(r'^related_skills:\n((?:[ \t]+-[^\n]+\n?)+)', fm, re.MULTILINE)
    if rel_m:
        refs = [l.strip().lstrip('- ').strip() for l in rel_m.group(1).strip().split('\n') if l.strip()]
        for ref in refs:
            if ref not in all_names:
                print(f"BROKEN REF [{name}]: '{ref}' does not exist")
```

### 5. Description/trigger content mismatch (spot-check)
```python
spot_checks = {
    "hermes-agent": ("hermes", "configure"),
    "spike": ("spike", "experiment"),
    "stay-in": ("watch", "recommend"),
}
for skill_name, (kw1, kw2) in spot_checks.items():
    combined = " ".join(skill_map[skill_name]["triggers"]).lower()
    if kw1 not in combined and kw2 not in combined:
        print(f"MISMATCH [{skill_name}]: expected '{kw1}' or '{kw2}'")
```

---

## Trigger Insertion Patch Pattern

Insert a `triggers:` block inside frontmatter, **before** the `description:` line.
Direct string replacement is more reliable than skill_manage for bulk operations:

```python
def insert_triggers(path, triggers):
    content = open(path).read()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    fm = parts[1]
    if re.search(r'^triggers:', fm, re.MULTILINE):
        return False  # already has triggers
    
    trig_block = "triggers:\n" + "\n".join(f"  - {t}" for t in triggers) + "\n"
    
    # Insert before first `description:` line
    new_content = content.replace("\ndescription:", "\n" + trig_block + "description:", 1)
    
    # Verify triggers landed in frontmatter
    new_parts = new_content.split("---", 2)
    if len(new_parts) < 3 or "triggers:" not in new_parts[1]:
        return False  # placement check failed
    
    open(path, "w").write(new_content)
    return True
```

Caveat: if `description:` appears in the body (e.g. in a code example), the replace
hits the frontmatter occurrence first because it comes earlier in the file, and the `1`
count limit prevents double-insertion. Verify after patching.

---

## Severity Classification

| Severity | Condition | Action |
|---|---|---|
| HIGH | Broken frontmatter (can't parse), or routing candidate with no description at all | Fix immediately |
| MEDIUM | Routing candidate missing triggers block | Add triggers block |
| LOW | Exempt skill missing triggers, or missing related_skills | Skip or enrich as time allows |

Note: `computer-use` (builtin) was a false-positive HIGH in the 2026-07-04 audit —
it uses a YAML block-scalar description (`description: |...`) which grep-for-triggers
can misread. Always do a structural parse, not grep, to confirm true HIGH issues.

---

## Coverage Outcomes (2026-07-04 baseline)

- 143 total skills, 140 local (patchable), 3 builtins
- Before audit: 38/140 local skills had triggers (27%)
- After audit: 99/140 local skills have triggers (70%)
- 41 exempt (slash-cmds, repo-specific, tool wrappers) — correctly skipped
- Zero collisions, zero placement errors, zero broken refs after patching

Next audit target: `related_skills` coverage — currently ~15% of local skills
have cross-references. High-value skills to add backlinks to first:
verification-before-completion, autonomous-agent-loop-design, hermes-acp-routing,
hermes-swarm-consensus.

---

## Structural Defect Patterns (2026-08-14 full cross-category audit)

Findings from a full 10-section workflow audit (SOFTWARE-DEV → DEVOPS → GITHUB →
PRODUCTIVITY → SUPERPOWERS → RESEARCH → NOTE-TAKING → EMAIL → disabled-refs →
web-provider). Defect taxonomy below — use as a checklist for any future audit pass.

### Defect class A: Self-referencing related_skills

Skill lists itself in its own `related_skills` block.

**Detected in:** `github-operations` (listed `github-operations` as a related skill),
`pdf` (listed `pdf` as a related skill in the body YAML block).

**Detection script:**
```python
import re, glob

base = "/var/home/rainbow/.hermes/skills"
for path in glob.glob(base + "/**/SKILL.md", recursive=True):
    if "/.archive/" in path: continue
    content = open(path, errors="replace").read()
    parts = content.split("---", 2)
    if len(parts) < 3: continue
    fm = parts[1]
    name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
    if not name_m: continue
    name = name_m.group(1).strip().strip('"\'')
    # Check both frontmatter and body for self-ref
    full_related = re.findall(r'related_skills:.*?(?=\n\S|\Z)', content, re.DOTALL)
    for block in full_related:
        if f"- {name}" in block or f"  {name}" in block:
            print(f"SELF-REF: {name} in {path}")
```

**Fix:** Remove the self-reference from `related_skills`. It is always a copy-paste error.

---

### Defect class B: Spurious template `related_skills` block in skill body

Skills generated from a shared template often have a duplicate `related_skills:` block
at the bottom of the frontmatter (just before the closing `---`) that contains
`[grounded-citations, pdf]` or similar irrelevant cross-references inherited from a template.

**Detected in:** `xlsx`, `docx`, `session-librarian` — all had `related_skills: [grounded-citations, pdf]`
in the YAML body block, completely unrelated to the skill's actual purpose.

**Detection:** look for a second `related_skills:` key inside the frontmatter (between the
second and third `---`). YAML last-key-wins semantics mean the body block silently overrides
the metadata header block — the wrong refs win.

```python
for path in glob.glob(base + "/**/SKILL.md", recursive=True):
    if "/.archive/" in path: continue
    content = open(path, errors="replace").read()
    parts = content.split("---", 2)
    if len(parts) < 3: continue
    fm = parts[1]
    count = len(re.findall(r'^related_skills:', fm, re.MULTILINE))
    if count > 1:
        name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
        print(f"DUPLICATE related_skills: {name_m.group(1).strip() if name_m else path}")
```

**Fix:** Remove the spurious body block; keep only the `metadata.hermes.related_skills` entry.

---

### Defect class C: Active `metadata.related_skills` referencing disabled skills

Skills list disabled skills in their `metadata.hermes.related_skills` header. This appears
in the system prompt routing graph and can cause agents to try loading disabled skills.

**Detected in:**
- `pdf`, `docx`, `xlsx` → all reference disabled `powerpoint`
- `pdf` → references disabled `ocr-and-documents`
- `xlsx` → references disabled `ocr-and-documents`
- `competitor-news-monitor` → references disabled `political-source-monitoring`

**Detection:** cross-reference `related_skills` entries against `config.yaml`'s `skills.disabled` list.

**Fix:** Remove disabled skill from metadata `related_skills`. If the disabled skill is the
correct routing target (e.g. "for scanned PDFs use X"), replace with the live fallback
(`pdf` / `docx` directly) and note the disabled state inline in the body text.

---

### Defect class D: Body text routing to disabled skill without caveat

Skill body says "for X, use `disabled-skill`" with no note that the skill is disabled.
Agent follows the instruction and hits a dead end.

**Confirmed worst case:** `pdf` skill body (lines 27, 37, 96, 108) says "route to
`ocr-and-documents`" for scanned PDFs — `ocr-and-documents` is in `config.yaml disabled:`.

**Contrast with correct pattern:** `document-to-action-items` body says:
"ocr-and-documents is disabled — use pdf/docx directly for scanned docs".

**Fix:** Add "(disabled — use pdf/docx directly)" inline next to every reference to a
disabled routing target. Do NOT remove the reference entirely; the guidance about when
to use it is still correct, it just needs the caveat.

---

### Defect class E: Fallback chain order inconsistency across skills

Two authoritative skills document the same fallback chain in different orders.

**Detected:** Web extraction fallback chain:
- `defuddle` trigger description: `web_extract → defuddle → firecrawl-research → blocked-page-recovery`
- `academic-literature-review` §"Canonical web extraction fallback chain": `web_extract → firecrawl-research → defuddle → blocked-page-recovery`

The order of `defuddle` (step 2) vs `firecrawl-research` (step 2) is swapped.
The `hermes-skill-library-consolidation-audit` §"Cross-cutting chain audit" documents the
canonical order as: `web_extract → firecrawl-research → defuddle → blocked-page-recovery`.
`academic-literature-review` is correct; `defuddle`'s trigger description is wrong.

**Fix:** `defuddle` trigger should read "step 3 in the fallback chain after firecrawl-research
fails", not "step 2" / "first-pass extraction".

---

### Defect class F: Disabled skill present on disk with no in-skill disabled marker

Skill is disabled via `config.yaml skills.disabled` but has no `disabled: true`, `status: disabled`,
or inline note in its own SKILL.md. Other skills referencing it cannot tell from the SKILL.md
alone that it's disabled.

**Detected:** `political-source-monitoring` — fully disabled in config but SKILL.md reads as
a normal active skill. `competitor-news-monitor` correctly says "(political-source-monitoring is
disabled)" in its own body, but a skill can't rely on its *callers* documenting its own status.

**Best practice:** add to frontmatter: `status: disabled  # disabled via config.yaml skills.disabled`
on any skill that is archived-in-place rather than moved to `.archive/`.

---

## Coverage Outcomes (2026-08-14 cross-category workflow audit)

Scope: 10 workflow chains, ~50 skills read.

| Defect class | Count | Highest severity |
|---|---|---|
| A: Self-referencing related_skills | 2 skills | HIGH |
| B: Spurious template body related_skills block | 3 skills | HIGH |
| C: Active metadata → disabled skill (routing metadata) | 5 pairs | HIGH |
| D: Body text routing to disabled skill without caveat | 1 critical case (pdf→ocr-and-documents) | HIGH |
| E: Fallback chain order inconsistency | 1 pair (defuddle vs academic-lit-review) | MEDIUM |
| F: Disabled skill with no in-skill disabled marker | 1 skill (political-source-monitoring) | LOW |

Zero CRITICAL findings. Highest-priority fix: `pdf` body routing to disabled `ocr-and-documents`.

