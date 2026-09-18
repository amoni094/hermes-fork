---
name: hermes-research-sweep-ops-resume
description: 'Use when resuming a dropped math sweep wave session.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, sweep, math, resume, state-check]
    related_skills:
      - hermes-research-sweep-ops
      - hermes-math-research
---

# Sweep Session Resume & Math Corpus Pitfalls

Supplement to hermes-research-sweep-ops for session-drop recovery and math corpus gotchas.
When a wave session drops mid-run, follow this procedure before restarting.

## Session Resume Procedure

1. Find the dropped session:
   session_search(query="wave math sweep interpreter", sort="newest", limit=3)
   Read bookend_end for: last wave number, last batch number, ideas total.

2. Check actual on-disk state (bookend may be stale if context was compacted):

```python
import json
from pathlib import Path
cache = Path.home() / ".hermes/cache/research"

# Ideas totals
math_ideas = json.loads((cache / "math-ideas-queue.json").read_text())["total_ideas"]
cs_ideas   = json.loads((cache / "cs-ideas-queue.json").read_text())["total_ideas"]
core_ideas = json.loads((cache / "research-ideas-queue.json").read_text())["total_ideas"]

# Math seen (rolling window, typically ~29 -- small is NORMAL, not a reset)
math_seen = len(json.loads((cache / "math-seen-papers.json").read_text()).get("seen", []))

# Math corpus
d = json.loads((cache / "hermes-math-sweep-latest.json").read_text())
flat = len(d.get("new_papers_flat", []))   # what interpreter reads
all_ = len(d.get("all_papers", []))        # broader set, do NOT use for interpreter sizing

# Suite count
import re
ms_text = (Path.home() / ".hermes/scripts/monitor-suite-runner.py").read_text()
monitor_lines = [l.strip().strip(',').strip('"\' ') for l in ms_text.splitlines()
                 if '.py"' in l or ".py'" in l]
print(f"math_ideas={math_ideas}, cs={cs_ideas}, core={core_ideas}")
print(f"math_seen={math_seen} (rolling window, normal to be ~29)")
print(f"new_papers_flat={flat}, all_papers={all_} (interpreter uses flat)")
print(f"suite={len(monitor_lines)} monitors")
```

3. Run prefetch if abstracts are missing:
```bash
python3 ~/.hermes/scripts/math-prefetch-abstracts.py --limit 448 --workers 8
```
   Prefetch writes into new_papers_flat entries. If coverage shows 0/N, the sweep file
   may need a fresh math sweep first (hermes-math-sweep.py in hermes-fork venv).

4. Resume interpreter from next batch number:
```bash
cd ~/.hermes/hermes-fork && source venv/bin/activate && \
for i in <next_batch> ...; do
  echo "=== MATH WAVE<N> BATCH $i ===" >> /tmp/math-wave<N>.log
  timeout 300 python3 ~/.hermes/scripts/math-paper-interpreter.py 2>>/tmp/math-wave<N>.log
  echo "EXIT:$?" >> /tmp/math-wave<N>.log
done
echo "MATH_WAVE<N>_DONE" >> /tmp/math-wave<N>.log
```
   /tmp/math-waveN.log does NOT persist across reboots or session drops -- do not rely
   on it for state. Use math-seen-papers.json and math-ideas-queue.json instead.

## Math Sweep JSON Structure: Critical Keys

hermes-math-sweep-latest.json has two paper lists -- they are NOT interchangeable:

  new_papers_flat   what math-paper-interpreter.py reads (e.g. 79 papers, recent sweep only)
  all_papers        broader set including non-math categories (e.g. 448 papers total)

Do NOT use all_papers count to judge interpreter corpus size -- it inflates by 5-6x.
Category breakdown of all_papers is dominated by reasoning_planning + game_theory (non-math).
Math-cat papers are a minority; filter by MATH_CATS before counting.

Other useful keys: sweep_date, prefetch_date.

## Math Seen Cache: Rolling Window Behaviour

math-seen-papers.json tracks a rolling window of ~29 papers, not a growing cumulative set.
A seen count of 29 with 419/448 papers "unseen" after 13+ waves is NORMAL -- not a sign
of a broken cache or that waves achieved nothing. The interpreter auto-resets the seen
cache when all known papers are seen, then starts the window again.

Saturation criterion: NOT "unseen count is low". Instead: multiple consecutive batches
  produce 0 SPIKE and 0 OPTIMIZATION outputs (the two actionable tiers). The IDEA tier
  (backlog queue) is NOT a saturation signal — it grows continuously as papers are
  re-interpreted. Saturation = 0 spikes + 0 optimizations across 8+ consecutive batches,
  regardless of idea count.

  NOTE: batches killed by `timeout 300` before the budget-guard (270s) fires produce no
  Results line and leave IDEAS_TOTAL unchanged. These are NOT silent exits — they are
  mid-run kills. The same papers are unmarked (not added to seen cache) and reprocessed
  in the next batch. Net data loss: 0. Do not count them as "missing" in the streak.

## Unimplemented Ideas: Scale Context

Most math ideas propose scripts not yet implemented; this is the normal state -- the
ideas queue is a backlog, not a to-do list blocking resumption.
Before implementing any idea, check BOTH naming variants:
  artifact_name.py  AND  artifact-name.py
in ~/.hermes/scripts/ (underscore vs dash duplicates are common).

Priority for implementation:
  1. [script]-tagged ideas -> implement as .py in ~/.hermes/scripts/
  2. [skill]-tagged -> only if class-level and non-trivial
  3. Skip if duplicate name exists under either naming convention
