# Skill Reference File Audit

Periodic check: scan all skills for declared linked reference files that do not exist on disk.

## Procedure

```python
from hermes_tools import terminal, read_file
import re, os

skills_root = "/var/home/rainbow/.hermes/profiles/fork/skills"

# 1. Find all SKILL.md files
result = terminal(f"find {skills_root} -name 'SKILL.md' | sort")
skill_files = [f for f in result['output'].strip().split('\n') if f]

# 2. Find all existing non-SKILL.md content files
result2 = terminal(
    f"find {skills_root} -type f "
    "! -name 'SKILL.md' ! -name 'SKILL_TEMPLATE.md' "
    "! -path '*/.locks/*' ! -path '*/.curator_backups/*' "
    "! -name '.bundled_manifest' ! -name '.curator_ledger.jsonl' "
    "! -name '.curator_state' ! -name '.usage.json' ! -name '.usage.json.lock' | sort"
)
existing_content_files = set(result2['output'].strip().split('\n')) if result2['output'].strip() else set()

# 3. Parse each SKILL.md for file_path references
# IMPORTANT: Only check YAML frontmatter write_file declarations,
# NOT code block text — code blocks mentioning scripts/foo.py produce false positives.
# The correct signal is a skill_manage write_file action that created the file;
# that file will appear in the linked_files dict when skill_view is called.
# A simpler proxy: check whether the file exists at skill_dir/ref_path.

# Pattern: references/, templates/, scripts/, chapters/ paths that appear
# outside code fences (in prose or YAML) are candidates.
# BUT: verify against skill_view(name).linked_files rather than text scan.

missing = {}
for sf in skill_files:
    skill_dir = os.path.dirname(sf)
    skill_name = os.path.basename(skill_dir)
    try:
        content = read_file(sf)['content']
    except:
        continue
    # Only match paths mentioned OUTSIDE triple-backtick blocks
    # Strip code fences before scanning
    stripped = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    ref_pattern = re.compile(r'(?:references|templates|scripts|chapters)/[\w\-\.]+\.\w+')
    refs = set(ref_pattern.findall(stripped))
    for ref in refs:
        full_path = os.path.join(skill_dir, ref)
        if full_path not in existing_content_files:
            missing.setdefault(skill_name, []).append((ref, full_path))

print(f"Skills with missing linked files: {len(missing)}")
for skill, refs in sorted(missing.items()):
    print(f"  {skill}:")
    for ref, fp in refs:
        print(f"    MISSING: {ref}")
```

## Key pitfall

Regex matching `scripts/foo.py` inside code block text produces false positives.
The correct test: check whether the file physically exists at `skill_dir/ref_path`.
Also verify against `skill_view(name).linked_files` — if `linked_files` is null or
does not list the path, the file was never registered as a linked file and the
reference in the body is just documentation pointing to a global script path
(e.g. `~/.hermes/hermes-scripts/`), not a skill-local file.

Strip code fences from the SKILL.md body before scanning to avoid matching
paths inside bash/python examples that reference global script locations.

## Evaluation criteria (worth implementing?)

- If the script is already present at a global path (`~/.hermes/hermes-scripts/`
  or `~/.hermes/scripts/`) and the SKILL.md just documents how to call it:
  **not missing** — the body reference is documentation only.
- If the skill says "see references/foo.md for detail" and that file does not
  exist on disk: **missing** — implement or remove the pointer.
- If a `templates/` or `scripts/` file would be reused across multiple agent
  sessions for the same task class: **worth implementing**.
- One-off or highly context-specific content: not worth a permanent file.
