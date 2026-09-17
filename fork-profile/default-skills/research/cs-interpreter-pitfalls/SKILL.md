---
name: cs-interpreter-pitfalls
description: 'Use when cs-paper-interpreter.py drops all papers silently.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, cs, interpreter, pitfalls, debugging, monitor, sweep]
    related_skills:
      - hermes-cs-research
      - hermes-research
      - hermes-math-research
      - hermes-research-pipeline-pitfalls
triggers:
  - cs-paper-interpreter produces 0 papers
  - core agent papers silently dropped
  - spike_queue TypeError
  - CS window saturated no new ideas
  - monitor suite false alarms
  - all-categories flag needed
related_skills:
  - hermes-cs-research
  - hermes-research
  - hermes-math-research
  - hermes-research-pipeline-pitfalls
---

# CS Interpreter Pitfalls

Fork-profile pitfall collection for cs-paper-interpreter.py and monitor-suite-runner.py.
Primary reference for default-profile pitfalls: hermes-research-pipeline-pitfalls.

## --all-categories Required for Core Agent Papers

When running cs-paper-interpreter.py against hermes-research-latest.json (core agent
sweep, NOT the CS sweep), ALL papers are silently dropped without `--all-categories`.

  CAUSE:  Core agent papers have `category="arxiv-listing:cs.AI"` (long-form arXiv strings).
          The CS_CATS filter uses short keys like `"software_testing"`. Zero papers match.
          Interpreter reports "0 CS papers to interpret" with EXIT:0 — no warning.

  FIX:    Always pass --all-categories when input is hermes-research-latest.json:
```bash
python3 ~/.hermes/scripts/cs-paper-interpreter.py \
  --input ~/.hermes/cache/research/hermes-research-latest.json \
  --all-categories
```
  VERIFY: "N CS papers to interpret" where N > 0. If still 0, abstracts missing — run prefetch.

## Output Namespacing by Input Stem

cs-paper-interpreter.py auto-derives output paths from the input stem:

  hermes-research-latest.json  ->  research-interpretation-latest.json,
                                    research-spike-queue.json,
                                    research-ideas-queue.json,
                                    research-seen-papers.json
  hermes-cs-sweep-latest.json  ->  cs-interpretation-latest.json (default),
                                    cs-spike-queue.json, cs-ideas-queue.json

Verify after a core agent run:
```bash
ls ~/.hermes/cache/research/research-*.json
```
If only cs-*.json files changed, --input was not parsed — check argparse position.

## spike_queue Variable Collision

`spike_queue` appears as BOTH a Path object (output file) AND a list (accumulation buffer).
The list assignment silently overwrites the Path, causing TypeError on write.

  FIX: Rename the Path variable to `spike_queue_path` everywhere; update all write calls.

```bash
grep -n 'spike_queue' ~/.hermes/scripts/cs-paper-interpreter.py | head -20
# Both 'Path(' and '= []' on lines with spike_queue = collision exists
```

## Seen-Cache Reset: Expected Behavior

"All papers already processed — resetting seen cache" = CORRECT behavior. The seen window
is full; the script starts a fresh 40-paper window. NOT a cache collision or config error.
If ALL batches report 0 papers + this message, the sweep file has fewer than 40 abstracts.
Run prefetch to expand coverage before next wave.

## CS Window Saturation

Saturation = multiple consecutive waves produce 0 new ideas (only duplicate Stage 3 names).

  CAUSE: Seen cache covers all available abstracts; Stage 3 dedup suppresses same names.
  FIX:   Expand abstract coverage with prefetch, then re-run interpreter.

```bash
python3 ~/.hermes/scripts/math-prefetch-abstracts.py \
  --limit 200 --workers 8 \
  --input ~/.hermes/cache/research/hermes-cs-sweep-latest.json
```

At 95%+ coverage (e.g. 537/562 papers), declare window exhausted; wait for next weekly sweep.

## Stage 3 Ideation Behavior by Interpreter

Stage 3 fires on full-chain SKIPs in all three interpreters. Output queues:
  Core agent (--all-categories): research-ideas-queue.json. Expected SKIP rate ~90%.
    reasoning_planning category produces 14+ spikes per 40-paper batch (highest yield).
  CS papers: cs-ideas-queue.json.
  Math papers: math-ideas-queue.json.

Cross-queue dedup is manual. Within-queue dedup is case-insensitive by hermes_artifact.

## Monitor Suite: Alarm Detection Logic

Use `alarm_line AND NOT no_alarm_line` — NOT exit code alone.

```python
alarm_line = any(
    line.strip().startswith("ALARM: yes")
    for line in out.splitlines()
)
no_alarm_line = any(
    line.strip().startswith("ALARM: no") or "insufficient data" in line
    for line in out.splitlines()
)
alarm = alarm_line and not no_alarm_line
```

Do NOT match bare "ALARM:" — matches "ALARM: no" lines. Do NOT use exit code alone —
exit 1 fires for both real alarms AND insufficient-data states. This fix reduced false
alarms from 14 to 4 (genuine) on the first real suite run after implementing new monitors.

## Real Alarm Signals (2026-09-15 baseline)

Five genuine persistent alarms (not calibration artifacts):
1. session-stability: V_t=23 on session 213144 (high tool-embedding variance)
2. retrieval-saturation: hindsight_recall slope -0.037/call (over-retrieval)
3. consensus-convergence: JS=0.534 mean (fragmented tool-use patterns)
4. absorption-capacity: saturation curve slope -0.077 (using fallback reference data)
5. spec-semantic-graph: 200 issues (11 MISSING_GUARD, 189 UNREACHABLE_POSTCONDITION)

duality-gap and frequency-stability correctly return OK after the detection fix.

## Script Runtime: System Python vs Fork Venv

Monitor and utility scripts: /usr/bin/python3 (numpy 2.4.6, scipy 1.18.1).
Sweep/interpreter scripts: hermes-fork venv (anthropic package, no numpy).

Never mix. The venv has no numpy; system python has no anthropic package.

```bash
# Monitors and utilities:
/usr/bin/python3 ~/.hermes/scripts/<monitor>.py --dry-run

# Interpreters:
cd ~/.hermes/hermes-fork && source venv/bin/activate && \
  python3 ~/.hermes/scripts/cs-paper-interpreter.py --all-categories ...
```

## Implemented Scripts Count (2026-09-15)

25 monitors in daily suite, ~19 run-on-demand utilities.
Idea queues: math=101, cs=80, core-agent=70. Total ideas ~251, scripts implemented ~44.
All scripts compile and pass --dry-run. Suite: 4 genuine alarms, 0 false positives.
