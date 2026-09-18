---
name: hermes-research-sweep-resume-notes
description: Use when resuming a dropped sweep wave. Pitfall supplements.
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, sweep, math, resume, state-check]
    related_skills:
      - hermes-research-sweep-ops-resume
      - hermes-research-sweep-ops
      - hermes-math-research
---

# Sweep Resume: Observed Pitfalls and Fallbacks

Supplement to hermes-research-sweep-ops-resume (default-profile, not patchable from fork).
Load BOTH skills when resuming a dropped wave session. Rules here take precedence where
they conflict with the parent skill.

## Step 1 Fallback: session_search WAL Lock

If session_search fails with a WAL lock / DeletedWalGenerationError, skip directly to
disk-state inspection (Step 2 of the parent skill). Disk state is fully authoritative
for resumption; session history adds convenience, not data.

Also: the user's recollection of the wave number is often off by 1-2. Always verify
the actual wave in progress from the /tmp log before resuming:

  ls /tmp/math-wave*.log        # find actual wave number
  tail -50 /tmp/math-waveN.log  # find last completed batch and exit code

Trust the log filename over user memory.

## Rolling Window Size: Not Fixed at ~29

The parent skill documents the rolling window as "~29 papers". In practice it grows
beyond that as waves accumulate. A seen count of 53 (or higher) with unseen papers
remaining is NORMAL, not a sign of a cache problem or reset. Do not treat any specific
count as anomalous; the saturation criterion is unchanged: 0 Stage 3 ideas across
multiple consecutive waves, no new script names proposed.

## BrokenPipeError on Exit is Harmless

The interpreter exits with code 1 and prints a BrokenPipeError traceback after the
budget-guard flush when its stdout pipe closes before the final summary print. This is
not data loss: the flush writes ideas to disk before the print attempt. EXIT:1 from
this cause is safe to ignore. Confirm safety: ideas queue total increased AND
math-interpretation-latest.json has a recent run_date.

## Resume Loop: Capture Both stdout and stderr

The parent skill's resume loop template pipes stderr to the log (2>>) but stdout only
through tee, splitting budget-guard flushes (stdout) and tracebacks (stderr) into
different streams. Use this form to capture both in the same log:

```bash
cd ~/.hermes/hermes-fork && source venv/bin/activate && \
for i in <next_batch> ...; do
  echo "=== MATH WAVE<N> BATCH $i ===" >> /tmp/math-wave<N>.log
  timeout 300 python3 ~/.hermes/scripts/math-paper-interpreter.py \
    2>>/tmp/math-wave<N>.log | tee -a /tmp/math-wave<N>.log
  echo "EXIT:$?" >> /tmp/math-wave<N>.log
  IDEAS=$(python3 -c "
import json, pathlib
d = json.loads(pathlib.Path('~/.hermes/cache/research/math-ideas-queue.json').expanduser().read_text())
print(d['total_ideas'])
" 2>/dev/null)
  echo "IDEAS_TOTAL=$IDEAS" | tee -a /tmp/math-wave<N>.log
done
echo "MATH_WAVE<N>_DONE" >> /tmp/math-wave<N>.log
```

The IDEAS_TOTAL checkpoint after each batch lets you spot saturation (no growth)
without reading the full log.
