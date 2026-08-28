#!/usr/bin/env python3
"""
diff-impact.py — code impact analysis from git diffs.

Input: git diff (default HEAD~1..HEAD) or explicit commit range.
Output: JSON report with confidence, symbol blast radius, and skill hooks.

Usage:
    ./diff-impact.py [--range <commit-range>] [--repo <path>] [--json]

Example:
    ./diff-impact.py --range HEAD~3..HEAD --repo ~/code/hermes

Output schema:
    {
      "impact": {
        "confidence": "high|medium|low",
        "blast_radius": "local|module|project|external",
        "symbols": ["sym1", "sym2", ...],
        "files": ["path1", "path2", ...],
        "hooks": ["skill1", "skill2", ...]
      },
      "stats": {
        "lines_added": N,
        "lines_deleted": N,
        "files_changed": N
      }
    }

Confidence rules:
  - high: single file, <10 lines, no shared symbols
  - medium: 2-5 files, <50 lines, shared symbols in same module
  - low: 6+ files, 50+ lines, shared symbols across modules or external

Blast radius rules:
  - local: single file, no shared symbols
  - module: shared symbols within one module (e.g. hermes/skills/)
  - project: shared symbols across modules (e.g. hermes/skills/ + hermes/plugins/)
  - external: shared symbols outside the repo (e.g. ~/.hermes/scripts/)

Skill hooks:
  - code-impact-preflight (this script)
  - risk-based-review (depth decision)
  - hermes-coding-review-loop (iterative review)
  - verification-before-completion (final gate)
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Symbol extraction patterns
SYMBOL_PATTERNS = {
    'python': [
        r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?!lambda)',
        r'from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_, ]+)'
    ],
    'javascript': [
        r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
        r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
        r'const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',
        r'let\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=',
        r'var\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*='
    ],
    'yaml': [],
    'markdown': []
}

# Skill hook mapping (blast_radius -> skills)
HOOKS = {
    'local': ['code-impact-preflight'],
    'module': ['code-impact-preflight', 'risk-based-review'],
    'project': ['code-impact-preflight', 'risk-based-review', 'hermes-coding-review-loop'],
    'external': ['code-impact-preflight', 'risk-based-review', 'hermes-coding-review-loop', 'verification-before-completion']
}


def extract_symbols(diff: str, file_path: str) -> Set[str]:
    """Extract symbols from diff hunks for a file."""
    ext = Path(file_path).suffix.lstrip('.').lower()
    patterns = SYMBOL_PATTERNS.get(ext, [])
    symbols = set()
    
    for line in diff.split('\n'):
        if line.startswith(('+', '-')) and not line.startswith(('+++', '--')):
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if isinstance(match, tuple):
                        symbols.update(m.strip() for m in match if m.strip())
                    else:
                        symbols.add(match.strip())
    
    return symbols


def get_git_diff(repo_path: str, commit_range: str) -> Tuple[str, Dict[str, str]]:
    """Get git diff for the given range and return diff text + file diffs."""
    cmd = ['git', '-C', repo_path, 'diff', '--unified=0', commit_range]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    diff_text = result.stdout
    
    # Split diff into file sections
    file_diffs = {}
    current_file = None
    current_diff = []
    
    for line in diff_text.split('\n'):
        if line.startswith('diff --git'):
            if current_file:
                file_diffs[current_file] = '\n'.join(current_diff)
            current_file = line.split()[-1].lstrip('b/')
            current_diff = [line]
        elif current_file:
            current_diff.append(line)
    
    if current_file:
        file_diffs[current_file] = '\n'.join(current_diff)
    
    return diff_text, file_diffs


def analyze_impact(file_diffs: Dict[str, str]) -> Dict:
    """Analyze impact from file diffs."""
    symbols: Dict[str, Set[str]] = defaultdict(set)
    files = set()
    lines_added = 0
    lines_deleted = 0
    
    for file_path, diff in file_diffs.items():
        files.add(file_path)
        file_symbols = extract_symbols(diff, file_path)
        symbols[file_path] = file_symbols
        
        # Count added/deleted lines
        for line in diff.split('\n'):
            if line.startswith('+'):
                lines_added += 1
            elif line.startswith('-'):
                lines_deleted += 1
    
    # Determine blast radius
    all_symbols = set().union(*symbols.values())
    shared_symbols = set()
    
    for sym in all_symbols:
        count = sum(1 for s in symbols.values() if sym in s)
        if count > 1:
            shared_symbols.add(sym)
    
    # Classify blast radius
    if len(files) == 1 and not shared_symbols:
        blast_radius = 'local'
    elif len(files) <= 3 and len(shared_symbols) <= 2:
        blast_radius = 'module'
    elif len(shared_symbols) <= 5:
        blast_radius = 'project'
    else:
        blast_radius = 'external'
    
    # Classify confidence
    total_lines = lines_added + lines_deleted
    if len(files) == 1 and total_lines < 10:
        confidence = 'high'
    elif len(files) <= 5 and total_lines < 50:
        confidence = 'medium'
    else:
        confidence = 'low'
    
    # Get skill hooks
    hooks = HOOKS.get(blast_radius, [])
    
    return {
        'impact': {
            'confidence': confidence,
            'blast_radius': blast_radius,
            'symbols': list(all_symbols),
            'files': list(files),
            'hooks': hooks
        },
        'stats': {
            'lines_added': lines_added,
            'lines_deleted': lines_deleted,
            'files_changed': len(files)
        }
    }


def main():
    parser = argparse.ArgumentParser(description='Analyze code impact from git diffs.')
    parser.add_argument('--range', default='HEAD~1..HEAD', help='Git commit range')
    parser.add_argument('--repo', default='.', help='Repository path')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    try:
        diff_text, file_diffs = get_git_diff(args.repo, args.range)
        report = analyze_impact(file_diffs)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Impact report for {args.range}:")
            print(f"  Confidence: {report['impact']['confidence']}")
            print(f"  Blast radius: {report['impact']['blast_radius']}")
            print(f"  Files changed: {report['stats']['files_changed']}")
            print(f"  Lines added: {report['stats']['lines_added']}")
            print(f"  Lines deleted: {report['stats']['lines_deleted']}")
            print(f"  Suggested skill hooks: {', '.join(report['impact']['hooks'])}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running git: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()