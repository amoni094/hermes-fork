---
name: hermes-research-ops
version: 1.0.0
author: Hermes Agent (curator)
platforms: [linux]
description: "Use when checking status, re-running, or dispatching the apply job for an already-configured Hermes research pipeline. Not for category taxonomy, source config, or applying sweep findings (use hermes-research). Not for querying past findings (use arxiv-sweep-findings)."
triggers:
  - has the hermes research completed
  - check research status
  - do another round of the research pipeline
  - re-run the research sweep
  - dispatch the apply job
  - check the apply report
  - research pipeline status
  - NOT for configuring sweep categories or sources (hermes-research skill)
  - NOT for math domain sweep ops (same pattern; see hermes-math-research)
  - NOT for CS domain sweep ops (same pattern; see hermes-cs-research)
  - NOT for applying findings to skills (trajectory-research-synthesis-to-skills)
tags: [research, pipeline, operations, sweep, apply]
related_skills:
  - hermes-research
  - hermes-math-research
  - hermes-cs-research
  - trajectory-research-synthesis-to-skills
  - arxiv-sweep-findings
  - hermes-math-sweep-findings
  - hermes-cs-sweep-findings
---

# Hermes Research Pipeline — Operations

This skill covers day-to-day operation: checking status, re-running, and dispatching
the apply job. For the category taxonomy, source configuration, and apply protocol
see the `hermes-research` skill.

## Key Output Files

```
~/.hermes/cache/research/
  hermes-research-apply-latest.md    ← primary status signal (what was patched)
  hermes-research-sweep-run.log      ← raw paper counts, source coverage
  hermes-research-latest.json        ← full sweep output (large)
  hermes-research-YYYY-MM-DD.json    ← dated archive
  seen_papers.json                   ← dedup cache (rolling, max 2000)
```

## Checking Status

1. Check file timestamps:
   ```bash
   ls -lt ~/.hermes/cache/research/ | head -10
   ```

2. Read the apply report — this is the definitive signal:
   ```python
   read_file('~/.hermes/cache/research/hermes-research-apply-latest.md')
   ```
   Lists HIGH findings with patches applied, MED logged, LOW skipped, adversarial verdicts.

3. Sweep log is secondary — useful for per-category paper counts and off-topic bleed rate:
   ```python
   read_file('~/.hermes/cache/research/hermes-research-sweep-run.log')
   ```

**Pitfall:** Core agent categories (cs.AI, cs.CL, cs.MA) historically showed 0-2 papers
because the sweep lacked a direct pre-loop listing call for those cats. Fix applied Sep 2026.
If core category counts look suspiciously low, verify the explicit pre-loop listing exists
in hermes-research-sweep.py.

## Domain Sub-Pipeline Operations

As of Sep 2026, the research pipeline has three separate domain sweeps, each with its
own seen-papers cache and output files. Mixing caches across domains causes cross-domain
dedup suppression — do not share seen_papers*.json files.

| Domain    | Sweep script              | Seen-cache              | Findings skill           |
|-----------|--------------------------|-------------------------|---------------------------|
| Core (1-7) | hermes-research-sweep.py | seen_papers.json        | arxiv-sweep-findings      |
| Math (8-51)| hermes-math-sweep.py     | seen_papers_math.json   | hermes-math-sweep-findings|
| CS (30 cats)| cs-research-sweep.py   | seen_papers_cs.json     | hermes-cs-sweep-findings  |

To re-run a domain sub-pipeline manually, follow the same Step 1-3 pattern above
but substitute the appropriate script and findings skill.

Math interpreter: python3 ~/.hermes/scripts/math-paper-interpreter.py
CS interpreter:   python3 ~/.hermes/scripts/cs-paper-interpreter.py
CS primers:       python3 ~/.hermes/scripts/cs-primers-overnight.py --list

## skill_manage Create Pitfall (silent failure on description length)

skill_manage(action='create') silently returns name=? with no error when the description
field is too long for the routing-display limit (~57 chars for the trigger first-sentence).
Fallback: use write_file directly to ~/.hermes/skills/<category>/<name>/SKILL.md —
write_file accepts the full 1024-char description without truncation. The skill loads
normally in the next session regardless of which write method was used.

## skill_manage write_file Pitfall (non-existent skill directory)

skill_manage(action='write_file', file_path='references/sweep-NN.md', name='some-skill')
silently fails if the skill's directory doesn't exist in the ACTIVE profile. It returns
success=false with name=? but no clear error. Symptoms: sweep log file is missing after
the call. Fix: use write_file() directly with the full path:
  write_file('/var/home/rainbow/.hermes/profiles/fork/skills/<cat>/<name>/references/sweep-NN.md', content)
This bypasses the skill_manage directory lookup and writes reliably regardless of profile.
Always verify the file exists after write_file before calling the step done.


## Manual Re-Run ("Do another round")

### Step 1 — Run the sweep

Always use `--force` for user-requested re-runs. Without it the sweep silently exits
if no new papers have arrived since the last run.

```python
terminal(
    command="python3 ~/.hermes/scripts/hermes-research-sweep.py --force 2>&1 | tee ~/.hermes/cache/research/hermes-research-sweep-run.log",
    background=True,
    notify=True
)
```

Wait for the completion notification before proceeding.

### Step 2 — Dispatch the apply job

The apply job is context-heavy — always dispatch as a subagent, not inline.

Critical context to include:
- Path to previous apply report (`hermes-research-apply-latest.md`)
- Explicit list of already-applied findings from the previous report
- Instruction to NOT re-apply those findings
- Skills to load: `hermes-research, trajectory-research-synthesis-to-skills,
  arxiv-sweep-findings, adversarial-review, verification-before-completion,
  hermes-system-audit, hermes-operating-pattern`

**Pitfall:** Omitting the deduplication context causes the apply subagent to re-apply
findings from the prior run — skills get double-patched, script patches fail on exact-match,
and the report becomes misleading.

### Step 2b — Sweep log update (parent-side, NOT delegated)

After triaging paper candidates and before or concurrently with dispatching implementation
subagents, write the sweep log from the parent session:

1. Write `references/sweep-NN.md` into the appropriate skill's references/ dir
   (arxiv-sweep-findings, hermes-math-sweep-findings, or hermes-cs-sweep-findings):
   - Boundary (cutoff arXiv ID), sweep date, source file + size
   - Per-category paper counts
   - HIGH/MED/SKIP tally, one row per finding (arXiv ID, title, targets)
   - Math/CS results section: fill after math/CS interpreter subagent returns
2. Add a new boundary row to the SKILL.md table in that skill.
3. Do NOT delegate step 2b — it requires the parent's in-memory triage results.
   Subagents cannot access intermediate execute_code state.

**Pitfall:** Math/CS sweep results arrive as a separate async subagent. Leave the
math/CS section as a placeholder in the sweep log, then patch it in when the
subagent's result message arrives — do not wait to write the sweep log until both
are available.

Subagent goal template:
```
Load ~/.hermes/cache/research/hermes-research-latest.json.
Before triaging, read ~/.hermes/cache/research/hermes-research-apply-latest.md
and do NOT re-apply any finding already listed there (previously applied:
<list key finding names here>).

For each HIGH: extract transferable insight → identify ALL affected targets
(skills/scripts/config/hooks/cron/SOUL.md/budget-policy.yaml) → apply patches →
run adversarial-review cross-check → apply only if passed.
For MED: add to arxiv-sweep-findings.
For LOW: log skip note.

Write report to ~/.hermes/cache/research/hermes-research-apply-latest.md.
Load skills: hermes-research, trajectory-research-synthesis-to-skills,
arxiv-sweep-findings, adversarial-review, verification-before-completion,
hermes-system-audit, hermes-operating-pattern.

## Feature Watch Pipeline Pattern (Denuto Pattern)

Source: Denuto `feature_watch/` directory.

Automated competitive intelligence pipeline: seed → submit → poll → normalize → publish.
This is the concrete implementation of what hermes-research-ops should do for ongoing monitoring.

```python
# Step 1: seed_context — load baseline
context = {
    "mode": "daily",        # daily | weekly
    "run_date": "2026-09-16",
    "baseline_path": "~/.hermes/cache/research/baseline.json",
}
baseline = load_baseline(context["baseline_path"])

# Step 2: submit_research — build prompt + submit
prompt = build_prompt_from_template(
    template="~/.hermes/scripts/research_prompt_template.md",
    context={**context, "baseline": baseline},
)
job_id = submit_to_llm_api(prompt, model="default")  # returns job ID

# Step 3: poll_research — poll until complete
import time
MAX_WAIT = 300  # seconds
POLL_INTERVAL = 10
deadline = time.time() + MAX_WAIT
result = None
while time.time() < deadline:
    result = poll_job(job_id)
    if result["status"] == "complete":
        break
    time.sleep(POLL_INTERVAL)

# Step 4: normalize_findings — dedupe, classify novelty
def normalize_findings(raw_findings: list[dict], baseline: dict) -> list[dict]:
    """
    Dedupe and classify each finding as new/known/extended.
    Fingerprint by (vendor, feature, canonical_match) for deduplication.
    """
    seen = set()
    normalized = []
    for f in raw_findings:
        fp = (f.get("vendor"), f.get("feature"), f.get("canonical_match"))
        if fp in seen:
            continue
        seen.add(fp)
        known = fp in baseline.get("known_findings", set())
        f["novelty"] = "known" if known else "new"
        normalized.append(f)
    return normalized

# Step 5: publish — write to Obsidian vault
# See hermes-obsidian-sync for the exact write pattern
publish_to_obsidian(normalized, vault_path="~/Documents/SecondBrain/research/")
```

### Cron Integration

This pipeline runs as a daily cron job. Template:
```yaml
# ~/.hermes/profiles/fork/cron/feature-watch.yaml
id: feature_watch_daily
schedule: "0 8 * * *"    # 8am daily
script: ~/.hermes/scripts/feature_watch_run.py
args:
  - --mode=daily
  - --output=~/.hermes/cache/research/feature_watch_latest.jsonl
```

### Novelty Classification

| Novelty | Meaning | Action |
|---------|---------|--------|
| `new` | Not seen before, not in baseline | Surface immediately |
| `known` | Matches a baseline fingerprint | Skip unless significantly updated |
| `extended` | Known finding with new details | Update baseline entry |

See also: `hermes-obsidian-sync` for the publish step, `hermes-research` for sweep configuration.
```

### Step 3 — Verify

After the subagent completes, read the updated apply report:
- HIGH findings with adversarial verdicts
- No re-applications of previous findings
- Report timestamp is current

## Cron Job Names

```
hermes-research-weekly   → runs hermes-research-sweep.py
hermes-research-apply    → apply job (context_from sweep)
```

Check: `hermes cron list | grep -i research`
