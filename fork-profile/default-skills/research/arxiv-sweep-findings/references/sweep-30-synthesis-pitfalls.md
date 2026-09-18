# Sweep 30 Synthesis Pitfalls (2026-08-31)

Lessons from the sweep 30 research pass and adversarial review. These complement
`sweep-implementation-pitfalls.md` (which covers sweep script infrastructure);
this file covers the *synthesis workflow* (triage → implement → adversarial).

## 1. Multi-source sweeps: cutoff ID regression

When new sources (HuggingFace Papers, Papers With Code, Crossref) are added to a
sweep, they surface papers with arXiv IDs from any date — not just the current week.
If the highest ID returned is older than the previous sweep cutoff, writing it as the
new cutoff is a regression.

Sweep 30 example: reported new cutoff as 2608.23552, which predated sweep-24's start.

Rule: only advance the cutoff if genuinely new IDs *above* the previous cutoff were
processed. Otherwise: write "cutoff unchanged; multi-source sweep surfaced older IDs
from new sources."

## 2. Crossref noise without query constraint

Bare Crossref queries (e.g. `q=agent+reasoning`) return high-citation papers across all
domains. Medical, physics, and psychology dominate because those fields produce high-cited
work. Sweep 30 produced 420 raw / 75 filtered (5.6:1 noise ratio).

Fix applied to sweep script: append `" agent language model"` to all Crossref queries.
Also add `filter=type:journal-article` for cleaner results.

Check noise ratio after adding any new source to the sweep for the first time.

## 3. Ad-hoc verifier function names must come from source, not intuition

The sweep-30 verifier used `search_pwc` as the expected wired function name, but the
actual implementation used `scrape_pwc`. The check therefore always failed, masking a
real gap. The verifier only reached 9/9 after the check was corrected.

Pattern: extract actual function names programmatically:

```python
import re
functions = set(re.findall(r'^def (\w+)', src, re.MULTILINE))
# verify against functions, not hardcoded strings
assert 'scrape_pwc' in functions
```

Never hardcode expected names in a verifier without first reading the script to confirm
the exact identifier.

## 4. Adversarial pass: stale example references in SKILL.md

After a sweep adds a new reference file (e.g. `sweep-30.md`), the SKILL.md body still
says "Example matrix: references/sweep-28.md". Found by round-2 adversarial pass.

Rule: after every sweep, grep the SKILL.md for the prior two sweep numbers and update
any example/pointer lines to the current sweep.

## 5. Sign-off scope terms need quantitative thresholds

The agent-task-signoff patch added "required for any multi-tool agentic run" — caught
by adversarial pass as undefined. Fixed to: "2+ distinct tools or 2+ sequential tool
calls of any type."

Rule: all scope terms in sign-off/checklist additions must have a quantitative threshold
or a clear N/A escape hatch with the same threshold applied consistently.
