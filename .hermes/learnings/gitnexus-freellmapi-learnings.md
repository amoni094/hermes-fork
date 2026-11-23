# GitNexus & FreeLLMAPI Learnings Artifacts

## Implementation

- **diff-impact.py** — git+rg impact analyzer
  - Input: git diff (default HEAD~1..HEAD)
  - Output: JSON report with confidence, blast radius, symbol blast, suggested skill hooks
  - Schema: `impact.confidence`, `impact.blast_radius`, `impact.symbols`, `impact.files`, `impact.hooks`
  - Hooks: `code-impact-preflight`, `risk-based-review`, `hermes-coding-review-loop`, `verification-before-completion`

- **code-impact-preflight** skill
  - Trigger: git diffs, code impact analysis
  - Output: blast radius, confidence, skill hooks
  - Wired into: `risk-based-review`, `hermes-coding-review-loop`, `verification-before-completion`

## Integration

- `risk-based-review`: blast radius → review depth
- `hermes-coding-review-loop`: preflight → skill hooks
- `verification-before-completion`: preflight → verification scope

## Verification

```bash
cd ~/.hermes
python3 scripts/diff-impact.py --repo . --range HEAD~1..HEAD --json
```

Output:
```json
{
  "impact": {
    "confidence": "low",
    "blast_radius": "module",
    "symbols": [],
    "files": [".hermes/skills/software-development/code-impact-preflight/SKILL.md", ".hermes/scripts/diff-impact.py"],
    "hooks": ["code-impact-preflight", "risk-based-review"]
  },
  "stats": {
    "lines_added": 335,
    "lines_deleted": 2,
    "files_changed": 2
  }
}
```

## Artifacts

- `/var/home/rainbow/.hermes/scripts/diff-impact.py`
- `/var/home/rainbow/.hermes/skills/software-development/code-impact-preflight/SKILL.md`

## Next Steps

- Use `diff-impact.py` in any git diff workflow
- Load `code-impact-preflight` skill for impact analysis
- Review pipeline now auto-scales depth based on blast radius