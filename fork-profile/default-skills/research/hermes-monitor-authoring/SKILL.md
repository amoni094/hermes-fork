---
name: hermes-monitor-authoring
description: 'Use when writing or debugging Hermes monitor suite scripts.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [monitor, suite, alarm, calibration, session, scripts, research]
    related_skills:
      - hermes-research-sweep-ops
      - hermes-research-pipeline-pitfalls
      - adversarial-review
triggers:
  - writing a new monitor script for ~/.hermes/scripts/
  - adding a monitor to the suite runner
  - debugging a monitor that produces no alarm output
  - monitor fires every run (fixture alarm)
  - monitor alarm not detected by suite runner
  - monitor script crashes with argparse error
  - calibration threshold appears wrong
related_skills:
  - hermes-research-sweep-ops
  - hermes-research-pipeline-pitfalls
  - adversarial-review
---

# Hermes Monitor Script Authoring

Procedure and pitfalls for writing monitor scripts that work correctly in the 53-monitor
daily suite. This emerged from the adversarial pass that found 29 issues across 22 scripts.

## Monitor Architecture

Suite runner:  ~/.hermes/scripts/monitor-suite-runner.py
Script dir:    ~/.hermes/scripts/
Cron:          daily 7am, cron id c7e4d8aa60d5
Python:        /usr/bin/python3 (numpy 2.4.6, scipy 1.18.1 available)
Cache dir:     ~/.hermes/cache/monitors/

All scripts run as: /usr/bin/python3 <script>.py
The hermes-fork venv does NOT have numpy/scipy -- never run monitors via that venv.

## Procedure: Adding a New Monitor

1. Write the script with /usr/bin/python3 shebang.
2. Implement the ALARM format contract (see below).
3. Implement the session path coverage pattern (both profile dirs).
4. Test locally: /usr/bin/python3 <script>.py -- confirm non-zero results.
5. Add --dry-run argparse argument.
6. Classify: suite vs run-on-demand (see classification rules below).
7. If suite: append script filename to MONITORS list in monitor-suite-runner.py.
8. Verify suite runner detects alarm: /usr/bin/python3 monitor-suite-runner.py

## ALARM Format Contract (critical)

Every monitor must emit EXACTLY ONE of these lines per run, unconditionally:

  ALARM: yes -- <specific reason>        (triggers suite runner)
  ALARM: no                              (suppresses)
  ALARM: no -- insufficient data         (skip when data below minimum)

The suite runner detects alarms via:
  re.match(r"ALARM:\s+YES\b", line.strip(), re.IGNORECASE)

Never embed a count, path, or variable where "yes"/"no" belongs:
  BAD:  ALARM: 3 session(s) detected         -> runner never matches
  BAD:  ALARM: /tmp/alarm.json written        -> runner never matches
  BAD:  Alarm: 2 issues                      -> case mismatch, never matches
  GOOD: ALARM: yes -- 3 high-fan-out sessions detected

Always add an else branch that emits ALARM: no.

Template:
```python
if alarm_condition:
    print(f"ALARM: yes -- {count} {description}")
else:
    print(f"ALARM: no -- {metric} within bounds")
```

## Session Path Coverage

Glob only ~/.hermes/sessions/ misses fork-profile sessions. Always merge both:

```python
HOME          = Path.home()
SESSIONS_DIR  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"
files = sorted(
    [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists()
     for f in d.glob("*.jsonl")],
    key=lambda p: p.stat().st_mtime
)
```

Sessions are *.jsonl, NOT *.json. The *.json glob matches only the routing index.

## --dry-run Argument Discipline

If the suite runner passes --dry-run to any script, ALL scripts in the suite must accept it.
A script without --dry-run crashes with an argparse error and appears as a suite failure.

```python
parser.add_argument('--dry-run', action='store_true',
                    help='Print output without writing cache files')
```

## Suite vs Run-on-Demand Classification

Add to daily suite only when ALL three hold:
  1. Has a working "insufficient data" guard that emits ALARM: no on micro-sessions
     (< 8-10 tool calls or < 3 sessions)
  2. Requires no external input (plan file, specific CLI arg) to produce a result
  3. Would not be a fixture alarm on the current static system

If any condition fails, keep it run-on-demand. Document run-on-demand scripts in
the "Run-on-Demand Catalogue" section of hermes-research-sweep-ops.

## Fixture Alarm / Permanent Alarm Trap

Monitors that alarm on a static property (a constant count, a demo credential, a fixed
file count) fire forever and get classified as false positives.

Fix: baseline delta-gating. Only alarm when measured value exceeds baseline by DELTA:

```python
BASELINE_FILE = CACHE_DIR / "<monitor>-baseline.json"
baseline = json.loads(BASELINE_FILE.read_text()) if BASELINE_FILE.exists() else {}
old_count = baseline.get("count", 0)
DELTA = 5
if new_count > old_count + DELTA:
    print(f"ALARM: yes -- {new_count - old_count} new issues above baseline")
else:
    print(f"ALARM: no -- within baseline ({new_count} issues, baseline {old_count})")
BASELINE_FILE.write_text(json.dumps({"count": new_count, "ts": now}))
```

Apply to any monitor measuring a property of the static corpus (skills, config files)
rather than live session data. Also: remove demo credentials from example data in monitors
that scan for secret patterns -- a credential in a demo plan triggers every run.

## Threshold Calibration Pitfalls

From the adversarial MATH defect class (5 scripts):

- Calibration error metric: abs(raw_sim - cal_prob) is wrong when raw_sim is derived from
  cal_prob. Use abs(gt_prob - cal_prob) where gt_prob is a ground-truth proxy (e.g. Jaccard).
- JSD cap for k distributions: cap to log(k) nats, not 1.0. For k=3, max JSD = log(3) ~= 1.099.
- Spectral gap: use abs(eigs) (complex modulus), not abs(eigs.real). Real-part-only misses
  cyclic chains where imaginary parts dominate.
- Curvature sign: do not suppress with max(0, curv). Negative curvature is a valid signal.
- r_cov vs r_pack: keep distinct. r_cov = max_pairwise/2 (enclosing ball upper bound);
  r_pack from nearest-neighbor distances. Sharing a variable collapses the ratio to 1.

## Dead Code Traps

- Blind glob: session monitors that glob *.json instead of *.jsonl see zero sessions silently.
  Test on a real session file and verify non-zero output before adding to suite.
- Boolean tautology in filters (A & A is always True): apply a logic check to any filter
  expression before shipping. Use `ast.parse` if the filter is complex.
- Window comparison: comparing all items vs only the last one inflates "drift" signal;
  use equal-width windows for pairwise comparisons.

## Adversarial Defect Category Reference

From the 29-issue adversarial pass on the 53-monitor suite:
  ALARM_LOGIC (6):   invisible alarm format -- count/path/variable instead of yes/no
  THRESHOLD (4):     fixture alarms or wrong error metrics
  MATH (5):          eigenvalue modulus, JSD cap, curvature sign, r_cov/r_pack
  DEAD_CODE (3):     blind globs, tautologies, orphaned guards
  COHERENCE (3):     near-duplicate monitors; Jaccard max 0.31 is acceptable
  REGISTRATION (8):  run-on-demand scripts incorrectly in suite list

Genuine alarm baseline (post-fix, 55-monitor suite as of 2026-09-15):
  ~6 genuine alarms: session-stability, retrieval-saturation, consensus-convergence,
  absorption-capacity, spec-semantic-graph (baseline-gated), skill-graph-reachability
  (baseline-gated).
