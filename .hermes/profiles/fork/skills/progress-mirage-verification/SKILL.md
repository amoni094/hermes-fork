---
name: progress-mirage-verification
description: "Use when verifying fixes. Grounded evidence required."
tags: [verification, adversarial, wave16]
---

# Progress Mirage Grounded Verification Gate

Based on arXiv:2604.28831. Self-reported success fails on 62% of tasks.

## Rule (extends H-I3)
Never accept self-report without ONE of:
- File existence check
- SHA256 hash match
- Python compile success
- Command exit-code-0
- Test output with PASS / 0 errors

## Script
```bash
python3 ~/.hermes/hermes-scripts/progress-mirage-gate.py --verify-compile script.py
python3 ~/.hermes/hermes-scripts/progress-mirage-gate.py --verify-exit-zero "CMD"
python3 ~/.hermes/hermes-scripts/progress-mirage-gate.py --verify-file /path
python3 ~/.hermes/hermes-scripts/progress-mirage-gate.py --audit
```

## Chain for code fixes
write -> verify-file -> verify-compile -> verify-exit-zero

## Cron: daily 6:30am (wave16-progress-mirage-audit)

## Lessons
- Gate log: cache/progress-mirage-gate.jsonl
- Always run at minimum compile check after any code fix
