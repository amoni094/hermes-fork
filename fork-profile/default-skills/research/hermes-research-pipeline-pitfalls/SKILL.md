---
name: hermes-research-pipeline-pitfalls
description: 'Use when debugging Hermes sweep pipeline failures.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, sweep, cs, math, interpreter, pipeline, pitfalls, debugging]
    related_skills:
      - hermes-cs-research
      - hermes-math-research
      - hermes-research
      - trajectory-research-synthesis-to-skills
triggers:
  - CS interpreter produces all 0.3 confidence
  - sweep outputs off-topic papers
  - cs-paper-interpreter API failure
  - research pipeline debugging
  - interpreter fallback heuristic
  - cs sweep category bleed
  - reasoning_planning papers in CS sweep
  - sweep interpreter silent failure
  - NOT for running sweeps (use hermes-cs-research or hermes-math-research)
  - NOT for querying findings (use hermes-cs-sweep-findings or hermes-math-sweep-findings)
related_skills:
  - hermes-cs-research
  - hermes-math-research
  - hermes-research
  - trajectory-research-synthesis-to-skills
---

# Hermes Research Pipeline Pitfalls

Known failure modes and fixes for the Hermes math/CS/core research sweep pipeline.
For running normally, use hermes-cs-research or hermes-math-research.

## Quality Check: Detecting Silent API Fallback

After any interpreter run, check immediately:

  SIGNAL: Every spike/SA item has confidence=0.3 AND identical GWT template text
          ("Given Hermes uses ad-hoc approach, When applying <title>, Then improved reliability").

  CAUSE:  call_api() returned "" for every paper. The keyword-heuristic fallback
          assigns SPIKE to any title containing system/framework/tool/benchmark
          and templates a boilerplate GWT. This fires when ANTHROPIC_API_KEY is
          absent from os.environ (normal in subprocesses and cron jobs).

  ACTION: Discard those outputs entirely. Fix the API call (see below), re-run.

  NOTE:   confidence=0.7 = LLM judged the paper from the abstract.
          confidence=0.3 = keyword heuristic from title only.
          Never promote 0.3-confidence items to SYSTEMS-APPLICABLE.

## Fix: cs-paper-interpreter.py API Key Loading

cs-paper-interpreter.py must load from ~/.hermes/.env via the anthropic package.
The original used os.environ.get("ANTHROPIC_API_KEY") which is empty in subprocesses
and cron jobs, causing call_api to silently return "" and fire the heuristic fallback.

Required: `import os` at the top of the file (not just inside functions).

Correct call_api pattern (mirrors math-paper-interpreter.py):

```python
import os  # top-level import required

def _load_env() -> None:
    from pathlib import Path as _P
    env_path = _P("~/.hermes/.env").expanduser()
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

def call_api(prompt: str, model: str = "claude-haiku-4-5") -> str:
    _load_env()
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model, max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  [warn] API call failed: {e}", file=sys.stderr)
        return ""
```

Test the fix before a full run:

```bash
python3 - <<'EOF'
import os
from pathlib import Path
for line in Path("~/.hermes/.env").expanduser().read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())
import anthropic
msg = anthropic.Anthropic().messages.create(
    model="claude-haiku-4-5", max_tokens=20,
    messages=[{"role": "user", "content": "Reply: OK"}])
print(f"API test: {msg.content[0].text.strip()}")
EOF
```

## Fix: CS Sweep Category Bleed

The parent sweep's listing harvester hard-codes category="reasoning_planning" for papers
found via cs.AI/cs.CL/cs.LG listing pages (line ~1359 of hermes-research-sweep.py).
Allowing any listings through (even "high-signal" cs.AI/cs.CL) floods the CS output
with 200+ papers tagged reasoning_planning, which is not a CS category.

Fix in cs-research-sweep.py: suppress ALL listing-page harvests.

```python
# Suppress ALL listing harvests. Parent sweep hard-codes category="reasoning_planning"
# for cs.AI/cs.CL/cs.LG results. Keyword queries alone are sufficient for CS coverage.
def cs_listings_suppressed(arxiv_cats):
    return []

sweep.sweep_arxiv_listings = cs_listings_suppressed
```

Also add a post-filter after sweep.run_sweep() as belt-and-suspenders:

```python
all_papers = [p for p in all_papers if p.get("category") in CS_CATEGORIES]
new_papers = [p for p in new_papers if p.get("category") in CS_CATEGORIES]
```

Verify after patching:
```bash
python3 ~/.hermes/scripts/cs-research-sweep.py --dry-run
# Confirm: only valid CS category keys listed, no reasoning_planning/multilingual_fr/trending
```

## Run Traceability (Content-Addressed Run Identity)

Each interpreter run emits a content-addressed header via run-header.py, injected
automatically at the top of main() in cs-paper-interpreter.py and math-paper-interpreter.py.

Critical: run_id must NOT include timestamp. If timestamp is in the hash, two identical
runs have different run_id values, making drift detection useless.

Correct: run_id = sha256[:16] of (script_path + model + config_hash + skill_hashes).
Timestamp is a separate `ts` field for ordering only.

Use: compare run_id across two runs to determine if anything in the pipeline drifted.
If run_id differs, inspect script_hash, config_hash, and skill_hashes sub-fields to
identify what changed. Do NOT diff run_id directly as a change metric.

Log location: ~/.hermes/logs/run-headers.jsonl (append-only).

## Interpreter Overwrites Curated Spike Queue

cs-paper-interpreter.py writes its full output to cs-spike-queue.json on every run,
clobbing any manually curated entries. The same applies to math-paper-interpreter.py
and math-spike-queue.json.

Before any interpreter run that will produce a new spike queue:

```bash
cp ~/.hermes/cache/research/cs-spike-queue.json \
   ~/.hermes/cache/research/cs-spike-queue.json.bak-manual
```

After the run, restore manually curated entries from the backup and merge:

```python
import json
from pathlib import Path

queue_path = Path("~/.hermes/cache/research/cs-spike-queue.json").expanduser()
bak_path   = Path("~/.hermes/cache/research/cs-spike-queue.json.bak-manual").expanduser()

new_items  = json.loads(queue_path.read_text())["items"]
bak_items  = json.loads(bak_path.read_text())["items"]
curated    = [x for x in bak_items if x.get("promoted_by") == "manual"]
new_ids    = {x["arxiv_id"] for x in new_items}
curated    = [x for x in curated if x["arxiv_id"] not in new_ids]  # no dupes
merged     = curated + new_items

queue      = json.loads(queue_path.read_text())
queue["items"] = merged
queue_path.write_text(json.dumps(queue, indent=2))
```

Longer term: add a `--no-overwrite-curated` flag to the interpreter scripts so items
with `promoted_by="manual"` are preserved automatically.

## Dispatching Long-Running Interpreters

The interpreter takes ~1s/paper with real API calls. 400 papers = ~7 min, which exceeds
the foreground terminal cap (420s). Dispatch as a background subagent:

```python
delegate_task(action='spawn', tasks=[{
    'goal': 'Run cs-paper-interpreter.py --fetch-abstracts --limit 400 --input PATH',
    'context': 'Script uses anthropic package + ~/.hermes/.env for API key. '
               'Report verdict counts and all SYSTEMS-APPLICABLE/SPIKE items '
               'with title, category_key, confidence, and one-line rationale.'
}])
```

Run math and CS sweeps in parallel (one delegate_task call, shared group):

```python
tasks=[
    {'goal': 'Run math sweep + interpreter...', 'group': 'research-sweep'},
    {'goal': 'Run CS sweep + interpreter...',  'group': 'research-sweep'},
]
```

Both sweeps take 30-60 min; grouping them means one combined result message lands when
both finish, preventing a second review cycle.

## Manual Curation When Interpreter Fallback Fired

If a run produced all-0.3 outputs and the fix is not yet applied, recover signal
without re-sweeping:

1. Read all_papers from the sweep JSON; pick high-signal titles by domain knowledge.
2. Fetch abstracts: GET https://export.arxiv.org/abs/<arxiv_id>
   Parse `<blockquote class="abstract mathjax">` (reliable, no auth required).
3. Score manually:
   SYSTEMS-APPLICABLE = named Hermes component + concrete change described.
   SPIKE = specific Given/When/Then with measurable outcome.
   else SKIP.
4. Write chosen papers to spike queue JSON with confidence >= 0.65
   and promoted_by="manual" to distinguish from automated runs.

## Implementation Status Discipline (APPLIED / PARTIAL / PENDING)

When recording research findings in *-sweep-findings skills, use these status values:

- APPLIED: the Hermes runtime reads and acts on the change in its live code path.
  Verify with: `grep -r '<config_key>' ~/.hermes/hermes-agent/*.py`
  If grep returns nothing, it is not APPLIED.

- PARTIAL: an artifact exists (script, config comment, skill section) but the runtime
  does not call it. Works only if invoked manually. Example: tool-sandbox.sh exists but
  is not wired into Hermes tool dispatch.

- PENDING: rationale recorded, nothing built yet.

Pitfall: config.yaml blocks for keys the runtime doesn't read (e.g. delegation.retry_policy)
are PARTIAL at best. Comment them out and mark PARTIAL; do not claim APPLIED.
Real live knobs for retry: agent.api_max_retries in config.yaml.

## Adversarial Review of Sweep Implementations

After any session that implements research-paper proposals, dispatch a cold adversarial
reviewer before claiming the session complete. Key checks the reviewer should make:

1. For every config.yaml addition: grep hermes-agent source for the key; if unread, it's dead.
2. For every new script: does it actually run with real data? Check image/runtime assumptions
   for sandboxes (alpine has no python3; podman --memory cap needs cgroup v2 on host).
3. For every subprocess call with check=False: add timeout + stderr capture or it's a silent failure.
4. For content-hash scripts: confirm timestamp is NOT in the hash.
5. For any argparse script: test --help-adjacent flags (e.g. --train-probe-only) without
   all required args to catch ordering bugs before argparse parser runs.
6. For every status: APPLIED in findings skills: verify the runtime reads the key.

Dispatch pattern:
```python
delegate_task(action='spawn', tasks=[{
    'goal': 'Cold adversarial review of [list files changed]. Read every file fresh.
             Find bugs, silent failures, dead config, misleading docs.
             Report PASS/WARN/FAIL with exact file+line evidence.',
    'context': '[paste exact file list + what each change claimed to do]'
}])
```

Wait for the cold reviewer to finish before applying any fixes. Apply all FAIL fixes,
then WARN fixes, in a single pass.

## Adopt User-Owned Skills for Autonomous Curation

The following research skills are user-owned and block curator patches:
  hermes-cs-research, hermes-math-research, hermes-research,
  trajectory-research-synthesis-to-skills,
  hermes-cs-sweep-findings, hermes-math-sweep-findings,
  hermes-cron-and-agents

The pitfalls in this skill exist because those skills could not be patched.
To enable autonomous curation of them:

```bash
hermes curator adopt hermes-cs-research
hermes curator adopt hermes-math-research
hermes curator adopt hermes-research
hermes curator adopt trajectory-research-synthesis-to-skills
hermes curator adopt hermes-cs-sweep-findings
hermes curator adopt hermes-math-sweep-findings
hermes curator adopt hermes-cron-and-agents
```
