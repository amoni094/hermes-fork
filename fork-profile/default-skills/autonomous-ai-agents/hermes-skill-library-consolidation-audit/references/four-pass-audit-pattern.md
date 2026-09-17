# Four-Pass Audit Pattern for Skill Description & Structure Cleanup

**Source**: Session 20260717_111614 (July 17, 11:16 AM) — recursive audit of seven review-path skills (adversarial-review, requesting-code-review, review-driven-followup-fixes, hermes-coding-review-loop, hermes-skill-library-consolidation-audit, hermes-agent-skill-authoring, risk-based-review).

This pattern emerged as a reliable way to catch and fix format/structure issues while minimizing false positives and avoiding correcting-the-correction cycles.

## The Four Passes

### Pass 1: Full Audit (Broad Detection)

Run a comprehensive check against all target skills using regex or yaml parsing. Allow broad matching — this pass is designed to *over*-flag, not under-flag.

**Checks to include:**
- Description frontmatter: `Use when` clause present
- Description frontmatter: `Triggers on` clause present (if user-invocable=true)
- Description length: < 1024 chars
- Related-skills frontmatter: all referenced skills resolve to real `name:` fields (via yaml.safe_load)
- Body structure: top-level `# Title` heading, key sections like `## When to Use`, `## Common Pitfalls` present for user-facing skills
- Duplicate real headings (outside code blocks) in body prose

**Expected output:** HIGH/MEDIUM/LOW findings with false positives expected (regex headings inside code blocks, function names that look like headings, multi-line YAML block scalars that fool simple line-based matching).

### Pass 2: Verification & False-Positive Triage

For each finding from Pass 1, manually inspect:
1. Is it a real issue (frontmatter key missing, actual duplicate outside code blocks)?
2. Is it a false positive (heading inside a fenced code block, placeholder text in a template example)?
3. Is it a structural artifact (multi-line YAML parsing limitation)?

Mark each finding as:
- **Real** → escalate to Pass 3 for fix
- **False positive** → note the pattern for Pass 3's tighter regex
- **Already correct** → discard (e.g., a YAML block scalar that's valid but confused the parser)

### Pass 3: Targeted Fixes + Tightened Detector

After Pass 2 triage, implement fixes for all real findings. **Simultaneously**, refine the detection logic:
- Add code-block stripping before regex heading checks
- Switch from simple line-based regex to YAML-aware parsing
- Add negative lookahead for placeholder text (`<Title>`, `<Topic>`, `$PLACEHOLDER`)
- Exclude internal tool names from heading detection

Re-run the improved detector on the same target skills. Expected output: ~0 false positives, only real issues.

### Pass 4: Final Confirmation Run

Run the tightened detector one more time against all target skills to confirm:
- All previous real findings have been fixed
- New false positives are zero (or acceptable known patterns)
- No new issues appeared as side effects of fixes

Exit criteria: detector runs clean with 0 HIGH, 0 MEDIUM, 0 LOW findings.

## False-Positive Patterns & How to Filter Them

### Pattern: Headings Inside Code Blocks

**False positive example:**
```
## Peer-Matched Structure

Every in-repo skill follows roughly:

\`\`\`
# <Title>

## Overview
One or two paragraphs.
\`\`\`
```

Simple regex detects `# <Title>` and `## Overview` as real headings.

**Fix**: Strip all code blocks (fenced with ` ``` ` or indented 4+ spaces) before running heading detection.

```python
import re

def strip_code_blocks(text):
    # Remove fenced code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove indented code blocks (4+ spaces at line start)
    lines = text.split('\n')
    stripped_lines = [l if not l.startswith('    ') else '' for l in lines]
    return '\n'.join(stripped_lines)

body_no_code = strip_code_blocks(body)
headings = [l.strip() for l in body_no_code.split('\n') if re.match(r'^#{1,3} ', l)]
```

### Pattern: Placeholder/Template Text

**False positive example:**
```
Each skill follows this template:

# <Title>
## Overview
## When to Use
```

Regex detects `# <Title>` as a duplicate heading.

**Fix**: Exclude lines containing angle-bracket placeholders or common template markers.

```python
def is_placeholder_heading(heading):
    return any(marker in heading for marker in ['<', '>', '$', '[', 'example', 'template'])

real_headings = [h for h in headings if not is_placeholder_heading(h)]
```

### Pattern: YAML Block Scalars (Multi-line Descriptions)

**False positive example:**
```yaml
description: |-
  Systematic adversarial review for catching self-contradictions,
  broken references, portability gaps, and inconsistencies
```

Simple `re.search(r'^description:', content)` returns only the first line. Multi-line content is invisible to line-based regex.

**Fix**: Use `yaml.safe_load()` to parse frontmatter instead of regex on raw lines.

```python
import yaml

def extract_frontmatter(skill_path):
    content = open(skill_path).read()
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1])

fm = extract_frontmatter(path)
desc = fm.get('description', '')
has_use_when = 'Use when' in desc or 'use when' in desc
```

## Session Results (July 17, 11:16 AM)

**Target skills:** 7 (adversarial-review, requesting-code-review, review-driven-followup-fixes, hermes-coding-review-loop, hermes-skill-library-consolidation-audit, hermes-agent-skill-authoring, risk-based-review)

**Pass 1 findings:** 15 issues (HIGH/MEDIUM/LOW)
**Pass 2 triage:** 7 real, 8 false positives (code blocks, placeholders, YAML parsing artifacts)
**Pass 3 fixes:** 7 real issues patched; detector logic refined (YAML parsing, code-block stripping, placeholder filtering)
**Pass 4 result:** 0 HIGH, 0 MEDIUM, 0 LOW — all skills pass

**Durable fixes applied:**
- Added missing `# Title` heading to `adversarial-review` body
- Added skill-freshness clause with concrete action reference to `review-driven-followup-fixes` Step 6
- Updated "four audit surfaces" → "five audit surfaces" in `hermes-skill-library-consolidation-audit` (Step 0 added)
- Added cross-ref to `adversarial-review/references/skill-library-audit.md` from `hermes-skill-library-consolidation-audit`
- Fixed description format (Use when + Triggers on) for `requesting-code-review` and `hermes-agent-skill-authoring`

## When to Use This Pattern

Use four-pass audit when:
- Auditing a cluster of related skills for consistency (not a one-off fix)
- False positives are likely (large codebase, template-heavy descriptions, YAML complexity)
- Fixes may have side effects or introduce new issues (multi-skill interaction)
- You want high confidence the final state is clean before stopping

Do NOT use four-pass audit for:
- Single-skill fixes (just read, patch, verify readback)
- Simple typo corrections
- Tasks where one pass is sufficient (low false-positive risk)

## Reference Scripts

**Minimal four-pass runner** (Python):

```python
import glob, re, yaml, os

base = os.path.expanduser("~/.hermes/skills")
target_skills = ["adversarial-review", "requesting-code-review", ...]  # as needed

def read_skill(name):
    for path in glob.glob(base + f"/**/{name}/SKILL.md", recursive=True):
        content = open(path).read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None, None
        fm = yaml.safe_load(parts[1])
        return path, {"fm": fm, "body": parts[2]}
    return None, None

# Pass 1: Full audit
findings = []
for name in target_skills:
    path, skill = read_skill(name)
    if not skill:
        continue
    desc = skill["fm"].get("description", "")
    if "Use when" not in desc:
        findings.append(("HIGH", "format", name, "missing 'Use when'"))
    # ... add more checks

# Pass 2: Triage (manual inspection)
real_issues = [f for f in findings if not is_false_positive(f)]

# Pass 3: Patch + refine detector
for sev, cat, skill, issue in real_issues:
    # apply fix to skill file
    pass

# Pass 4: Re-run with refined detector
# (same checks but with updated filtering logic)
```
