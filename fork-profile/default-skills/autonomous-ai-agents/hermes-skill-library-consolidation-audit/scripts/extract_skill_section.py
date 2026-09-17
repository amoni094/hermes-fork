#!/usr/bin/env python3
"""
extract_skill_section.py — Extract an oversized section from a SKILL.md to references/

Usage:
    python3 extract_skill_section.py <skill_path> <section_header_partial> <ref_filename> [replacement_line]

Example:
    python3 extract_skill_section.py \
        ~/.hermes/skills/autonomous-ai-agents/agent-memory-consolidation/SKILL.md \
        "Session Logs" \
        session-logs-archival.md \
        "*Session Logs (archival) — see references/session-logs-archival.md.*"

How it works:
  1. Finds the section matching `section_header_partial` (H1 or H2 prefix match)
  2. Extracts everything from that header to the next header at the same or higher level
  3. Writes extracted content to references/<ref_filename>
  4. Replaces extracted section in SKILL.md with the replacement_line
  5. Prints before/after byte counts

Pitfalls:
  - Header matching is substring-based; be specific enough to match exactly one section
  - The replacement_line should include a pointer back to the ref file
  - Run on a git-tracked file so changes are reversible
  - After extraction, verify the SKILL.md is still valid YAML (check frontmatter parses)
"""

import re
import os
import sys


def extract_and_replace(skill_path, section_header_partial, ref_filename, replacement_line=None):
    """
    Extract a section from a SKILL.md into references/ and replace with a pointer.

    Returns: (old_size, new_size, ref_path) or raises ValueError if section not found.
    """
    content = open(skill_path, errors='replace').read()
    old_size = len(content)

    # Find section start (H1 or H2)
    m = re.search(r'\n(#{1,2} ' + re.escape(section_header_partial) + r'[^\n]*)', content)
    if not m:
        raise ValueError(f"Section not found: {section_header_partial!r}")

    full_header = m.group(1)
    level = len(full_header.split(' ')[0])  # count '#' chars

    # Find end: next section at same or higher heading level
    next_pat = re.compile(r'\n#{1,' + str(level) + r'} ', re.MULTILINE)
    next_m = next_pat.search(content, m.end())

    if next_m:
        section_content = content[m.start():next_m.start()]
        repl = '\n\n' + (replacement_line or f'*{section_header_partial} — see references/{ref_filename}.*')
        new_content = content[:m.start()] + repl + content[next_m.start():]
    else:
        section_content = content[m.start():]
        repl = '\n\n' + (replacement_line or f'*{section_header_partial} — see references/{ref_filename}.*') + '\n'
        new_content = content[:m.start()] + repl

    # Write reference file
    refs_dir = os.path.join(os.path.dirname(skill_path), 'references')
    os.makedirs(refs_dir, exist_ok=True)
    ref_path = os.path.join(refs_dir, ref_filename)
    with open(ref_path, 'w') as f:
        f.write(section_content.strip() + '\n')

    # Write updated SKILL.md
    with open(skill_path, 'w') as f:
        f.write(new_content)

    return old_size, len(new_content), ref_path


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    skill_path = os.path.expanduser(sys.argv[1])
    section_partial = sys.argv[2]
    ref_filename = sys.argv[3]
    replacement_line = sys.argv[4] if len(sys.argv) > 4 else None

    if not os.path.exists(skill_path):
        print(f"ERROR: skill path not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    try:
        old_size, new_size, ref_path = extract_and_replace(
            skill_path, section_partial, ref_filename, replacement_line
        )
        saved = old_size - new_size
        print(f"OK: {skill_path}")
        print(f"  Section: {section_partial!r}")
        print(f"  Ref:     {ref_path}")
        print(f"  Size:    {old_size} → {new_size} bytes ({saved:+d})")
        print(f"  Under 50KB: {new_size < 50000}")
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
