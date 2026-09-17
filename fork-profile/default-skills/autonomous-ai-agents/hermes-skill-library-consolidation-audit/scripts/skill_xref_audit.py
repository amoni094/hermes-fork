#!/usr/bin/env python3
"""
Find dead cross-references in the local Hermes skill library.

Scans every SKILL.md under ~/.hermes/skills/ for:
  - `related_skills: [...]` frontmatter entries
  - inline `skill_view(name="...")` / `skill_view(name='...')` prose mentions

...and reports any referenced name that does not match a real `name:` field
in any SKILL.md on disk.

Usage:
    python3 skill_xref_audit.py [skills_base_dir]

Default skills_base_dir: /var/home/rainbow/.hermes/skills

Known false positives to expect in output (leave these alone):
  - generic template placeholders: family-name, other-skill, another-skill,
    some-user-local-skill, specific-skill
  - deliberate illustrative examples inside walkthrough prose (read context
    before patching; if the surrounding sentence is teaching a hypothetical
    rather than pointing at a real skill, it's not a bug)
"""
import glob
import re
import json
import sys

PLACEHOLDER_NAMES = {
    "family-name", "other-skill", "another-skill",
    "some-user-local-skill", "specific-skill",
}


def collect_real_names(base):
    names = set()
    for path in glob.glob(base + "/**/SKILL.md", recursive=True):
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        m = re.search(r"^name:\s*(\S+)", content, re.M)
        if m:
            names.add(m.group(1).strip("\"'"))
    return names


def find_broken_refs(base, real_names):
    broken = []
    for path in glob.glob(base + "/**/SKILL.md", recursive=True):
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        m = re.search(r"^name:\s*(\S+)", content, re.M)
        self_name = m.group(1).strip("\"'") if m else path

        # related_skills: [a, b, c]
        for rm in re.finditer(r"related_skills:\s*\[([^\]]*)\]", content):
            for ref in [x.strip().strip("\"'") for x in rm.group(1).split(",") if x.strip()]:
                if ref and ref not in real_names and ref not in PLACEHOLDER_NAMES:
                    broken.append((self_name, path, "related_skills", ref))

        # skill_view(name="...") / skill_view(name='...')
        for sm in re.finditer(r'skill_view\(\s*name\s*=\s*["\']([^"\']+)["\']', content):
            ref = sm.group(1).strip()
            if ref and ref not in real_names and ref not in PLACEHOLDER_NAMES:
                broken.append((self_name, path, "skill_view call", ref))

    return broken


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "/var/home/rainbow/.hermes/skills"
    real_names = collect_real_names(base)
    broken = find_broken_refs(base, real_names)
    print(json.dumps({
        "total_skills": len(real_names),
        "broken_refs": broken,
    }, indent=2))


if __name__ == "__main__":
    main()
