---
name: hermes-monitor-session-format
description: "Use when parsing Hermes session JSONL in monitor scripts."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
tags: [monitor, session, jsonl, format, adversarial, threshold]
related_skills:
  - hermes-monitor-authoring
  - hermes-research-sweep-ops
triggers:
  - writing a monitor that reads session JSONL files
  - tool result extraction from Hermes sessions
  - monitor alarm threshold calibration
  - adversarial bug review of monitor scripts
  - competitive ratio docstring in routing script
  - PROP1 fairness floor going negative
  - prev_tools set causing permanent alarm
---

# Hermes Monitor: Session Format and Adversarial Bug Patterns

Canonical reference for the two most common sources of bugs in Hermes monitor scripts:
(1) wrong assumptions about the session JSONL format, and (2) threshold/math errors
uncovered by adversarial review. Distilled from two adversarial passes across 69 scripts.

## Verified Hermes Session JSONL Format

Adversarial subagents frequently get this wrong. Always verify against live files
before trusting any external claim about message structure.

Verification command:
```bash
python3 -c "
import json; from pathlib import Path
sf = sorted((Path.home()/'.hermes/sessions').glob('*.jsonl'))[-1]
for l in sf.read_text().splitlines()[:20]:
    if l.strip():
        m = json.loads(l)
        print(m.get('role'), list(m.keys())[:4])
"
```

Actual format:

  role='assistant'  -- agent turns.
                       Tool calls in `api_content` (Anthropic format, preferred) or
                       `content` (fallback). Blocks: {type:'tool_use', id:'toolu_...', name, input}
  role='tool'       -- tool result messages. Fields:
                         tool_call_id  (primary -- Anthropic toolu_... id)
                         tool_use_id   (secondary alias; same value)
                         content       (parsed Python str, NOT raw JSON)
  role='user'       -- human turns only. Never contains tool_result blocks.

NOT CORRECT (common wrong claims from adversarial subagents):
  - Tool results are NOT in role='user' messages as type='tool_result' blocks.
  - tool_use_id is NOT the primary field; tool_call_id is.
  - content for role='tool' is NOT raw JSON -- it is a parsed Python string.

## Correct Extraction Patterns

Extract tool calls from assistant messages:
```python
# Always prefer api_content (Anthropic format); fall back to content list
blocks = msg.get('api_content') or (
    msg.get('content', []) if isinstance(msg.get('content'), list) else []
)
for b in blocks:
    if b.get('type') == 'tool_use':
        tid = b.get('id', '?')           # toolu_01... Anthropic format
        tool_name = b.get('name', '')
```

Match tool results:
```python
elif role == 'tool':
    # Use tool_call_id as primary; fall back to tool_use_id (same value, alias)
    tid = msg.get('tool_call_id', msg.get('tool_use_id', '?'))
    content = str(msg.get('content', ''))
```

Search for failures in tool content (content is a Python string, not raw JSON):
```python
# WRONG: 'exit_code": 1'  -- the JSON quote char never appears in parsed strings
# RIGHT:
ok = not any(w in content.lower() for w in
             ['error', 'exception', 'traceback', 'failed', 'exit_code: 1'])
```

Session files are *.jsonl, NOT *.json. The *.json glob matches only the routing index.

## Adversarial Bug Patterns: Second Pass (10 bugs, 16 scripts, Sep 2026)

These complement the first-pass bugs documented in hermes-monitor-authoring.

### THRESHOLD: prev_tools set -> permanent productivity alarm

`prev_tools = set()` marks a tool permanently 'not useful' after first call.
A session with 50 `terminal` calls gets useful_calls=1, productivity=0.02, permanent alarm.
Use a string `prev_tool` for consecutive-repeat detection instead:
```python
prev_tool: str = ''   # NOT a set
if name != prev_tool:
    useful_calls += 1
prev_tool = name
```
Use a set ONLY to measure tool type diversity (distinct tool count), not repeated-call productivity.

### DEAD_CODE: alarm ceiling outside variable's domain

State the variable's domain before setting a threshold. If C, R in [0,1], ceiling=2.5
can never be exceeded -- the alarm silently never fires.
```python
# BAD: C,R in [0,1]; condition permanently False
alarm = t['C'] > 2.5 and t['R'] > 2.5
# GOOD: ceiling inside the domain
alarm = t['C'] > 0.75 and t['R'] > 0.75
```

### MATH: competitive ratio != threshold value

For static-threshold secretary strategy: CR = THETA * (1 - THETA), NOT THETA.
At THETA=0.75, CR=0.1875 (a 1/5-approximation, not 3/4). Document correctly:
```python
THETA = 0.75
# Competitive ratio: THETA*(1-THETA) = 0.1875
```

### MATH: negative PROP1 floor is vacuously satisfied

When max_item > opt_n, PROP1 floor = opt_n - max_item < 0.
Every allocation trivially passes -- not a real fairness check.
```python
prop1_floor = opt_n - max_item - PROP1_SLACK * opt_n
if prop1_floor <= 0:
    print(f'PROP1 floor vacuous (max_item={max_item:.3f} > opt_n={opt_n:.3f}); skipping')
else:
    if agent_value < prop1_floor:
        alarm = True
```

### COHERENCE: fallback using wrong data source

Fallback that reads `leaking_count`/`low_productivity_count` from unrelated monitor
cache files as 'critique severity' produces spurious convergence data.
If the right data source is absent, return empty -- never alias unrelated fields:
```python
if 'issue_count' not in d:
    continue   # do not alias leaking_count, alarm_count, etc.
issues = d['issue_count']
```

### DATA: dict_values is not a list

`{...}.values()` returns a view. Wrap in `list()` before indexing, slicing, or
iterating multiple times:
```python
all_results = list({r['id']: r for r in pool_a + pool_b}.values())
```

### ALARM_LOGIC: fallback path missing alarm print

Every code path including fallbacks must emit exactly one ALARM line:
```python
if accepted is None:
    accepted = best_option
    print('ALARM: no -- fallback to best available; no threshold met')
```

## Adversarial Review Workflow

After writing 10+ new monitors, dispatch a cold adversarial subagent before committing.

1. Bundle scripts: name + full text, one block per script (60-80KB typical).
2. Specify bug categories: ALARM_LOGIC, MATH, DEAD_CODE, THRESHOLD, COHERENCE, DATA.
3. Use claude-sonnet-4-6 -- NOT grok-4.6 (schema validation failures burn 80-130s each).
4. Verify all DATA claims against live session files before applying.
   Adversarial subagents get Hermes session format wrong ~30% of the time.
5. Apply HIGH bugs; compile-check: `/usr/bin/python3 -m py_compile <script>`
6. Spot-run 2-3 patched scripts before committing.

## Suite State (Sep 2026)

60 monitors in daily suite. Math: 365 ideas (wave12 done). CS: 80. Core: 340.
All in amoni094/hermes-fork feature/adaptive-compression-plugin-api.
Default-profile skills hermes-monitor-authoring and hermes-research-sweep-ops also
need these updates -- apply via `patch` tool on absolute paths when in fork profile session.
