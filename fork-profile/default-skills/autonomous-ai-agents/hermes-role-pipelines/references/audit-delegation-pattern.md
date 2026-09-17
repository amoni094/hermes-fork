# Audit Delegation Pattern

Use this pattern when you need a deep, systematic assessment of a large domain (config, architecture, security, performance, workflow) and you want high-quality structured output + implementation orchestration.

## Pattern shape

1. **Context gather** (5-10 min local reads)
   - Read key config files, policies, hooks, relevant skills
   - List directory structures to understand organization
   - Do NOT read everything — focus on active config, policies, and key examples
   - Output: mental model of what's live

2. **Audit dimensions** (explicit scope)
   - List 5-7 areas the audit will cover (e.g., token optimization, security, skills, multi-agent)
   - For each area, include 2-3 specific things to look for (e.g., "api_max_retries is very low, may fail on blips")
   - This narrows the auditor's focus and prevents off-topic tangents

3. **Context packet construction**
   - Write a compact brief (500-800 words) that includes:
     - Key config highlights with line-by-line interpretation
     - Budget policy and hook architecture
     - Current skills structure + categories
     - Active toolsets and integrations
     - Known gaps or concerns
   - Format: "==" section headers, bullet points, concise
   - Include specific config values (e.g., "prompt_caching.cache_ttl: 5m") so auditor can check them directly
   - Point auditor to actual files to read (e.g., "Read ~/.hermes/veto/rules/ to check blocking patterns")

4. **Delegate with explicit output schema**
   - Specify output file path and JSON structure upfront
   - Include at least these fields:
     - `audit_ts`, `auditor` (model/identifier)
     - `summary` (3-4 sentence overall assessment)
     - `priority_improvements` array with: id, area, severity, title, finding, recommendation, optional config_patch, effort estimate
     - `config_patches` array (ready-to-apply key/old/new/rationale)
     - `skill_actions` array (create/patch/consolidate suggestions)
     - `security_findings` (explicit security items)
     - `multiagent_patterns` (if domain-relevant)
   - Instruct auditor to "Read actual files before finalizing" and "Be critical and specific. Do not be lenient."

5. **Task ledger entry**
   - Write a single entry to ~/.hermes/logs/hermes-task-ledger.jsonl with:
     - task name, initiated_by, phases (e.g., "audit(opus-4-8)", "implement(sonnet orchestrator + subagents)"), status
   - This tracks long-running work across sessions

6. **Implementation orchestration prep** (optional, do in parent)
   - While auditor runs in background, draft an orchestrator plan that will:
     - Parse the report JSON on return
     - Fan out implementation subagents by area (config, skills, security, multiagent)
     - Keep implementation work parallel where independent
     - Collect results and produce a final commit
   - Do NOT execute orchestration until auditor finishes
   - Reserve separate parallel subagent batch for implementation; do not re-use audit subagent

## Example: Hermes holistic audit (2026-06-30)

**Context gather** (10 min):
```bash
cat ~/.hermes/config.yaml | head -200
ls ~/.hermes/skills/ && ls ~/.hermes/plugins/
cat ~/.hermes/budget-policy.yaml
cat ~/.hermes/hooks/*.py | head -sections
```

**Dimensions**:
- Token optimization (cache TTL, compression ratio, tool output limits)
- Workflow efficiency (max_turns, retries, timeouts, skill sprawl)
- Security (veto rules, destructive limits, browser access, secrets)
- Skills architecture (55+ skills, consolidation opportunities, class-level organization)
- Multi-agent patterns (delegation depth, context packets, swarm coordination)
- Key files (veto rules, shell allowlist, TOOLS.md, role pipelines)

**Context packet** (700 words):
```
== KEY CONFIG ==
model: anthropic/claude-sonnet-4-6, context_length: 128000
agent.max_turns: 150, agent.reasoning_effort: low
compression: enabled, threshold:0.5, target_ratio:0.2, protect_last_n:20
[... full packet with specific callouts and file pointers ...]
```

**Delegation** (to the configured delegation model — currently `mistral-small-latest`;
see `claude-routing-hierarchy` for verified ground truth):
```python
delegate_task(
  goal="Perform a holistic Hermes configuration audit across: workflow efficiency, token optimization, security posture, skills architecture, multi-agent/swarm design, and key configuration files...",
  context="[full packet above]",
  toolsets=["terminal", "file", "web"]
)
# Returns background delegation_id immediately
```

**Output schema** (told to auditor):
```json
{
  "audit_ts": "ISO timestamp",
  "auditor": "claude-sonnet-4-6",
  "summary": "...",
  "priority_improvements": [
    {
      "id": "IMP-001",
      "area": "token_optimization|workflow|security|skills|multiagent",
      "severity": "high|medium|low",
      "title": "...",
      "finding": "...",
      "recommendation": "...",
      "config_patch": {"path": "...", "key": "...", "old": "...", "new": "..."},
      "effort": "trivial|small|medium|large"
    }
  ],
  ...
}
```

**Result**: Auditor produces structured JSON to `/var/home/rainbow/.hermes/logs/hermes-audit-report.json`, parent orchestrator parses and implements changes in parallel subagents.

## Verification checkpoints

After the audit completes and before launching implementation:

1. **Report schema check**
   - Validate that the report file exists and parses as JSON
   - Verify all required fields are present (audit_ts, summary, priority_improvements, config_patches, skill_actions)
   - Count findings and patches — should be 5-15 items; fewer = under-scoped, more = audit bloat

2. **Config patches are machine-readable**
   - Each patch must have: path, key, old value, new value, and rationale
   - Dry-run patches against live config before subagent implementation (read the actual file, check old value matches)
   - Do NOT assume patches apply cleanly; YAML structure can change between runs

3. **Skill actions are specific**
   - Creates should include name, category, description, and at least a 2-sentence scope
   - Patches should list exact sections/fields to modify
   - Consolidations should name the umbrella and list the deprecated skills

4. **Security findings are actionable**
   - Each security finding must include a specific hard rule, not a generic concern
   - Example: "Add block-find-delete pattern to veto/rules/hermes-hard-blocks.yaml" (specific)
   - Bad: "Improve security hardening" (vague)

## Implementation orchestration

After verification:

1. **Spawn implementation subagents in separate batch** (not re-using audit subagent)
   - One subagent per major area (config, security, skills, multiagent)
   - Each gets a compact context packet with prior_findings_refs pointing to the report
   - Budget: max_tool_calls=30, max_turns=8 per subagent

2. **Parallel execution**
   - Config subagent applies all config_patches in sequence with live verification
   - Security subagent creates veto rule files, patches hooks
   - Skills subagent creates new skills, patches existing ones (use skill_manage)
   - Multiagent subagent creates new skills, updates role pipelines

3. **Merge results**
   - Collect outputs from all subagents (finding files from ~/.hermes/agent-workspace/)
   - If subagents touched the same files/config, use `hermes-agent-sync` for idempotent merging
   - Commit results to a private repo (e.g., hermes-config) with a clear commit message

4. **Post-implementation verification**
   - Run `hermes config check` and `hermes doctor` to verify no breakage
   - Spot-check a few config changes with `hermes config get <key>`
   - Verify new skills are installed: `hermes skills list | grep <new_skill_name>`

## Pitfalls

1. **Context packet too long**: Auditor will skim instead of read. Cap at 800 words, keep only active config and specific numbers. Point to files for long content.

2. **Dimensions too vague** ("'review everything'"). List explicit areas and specific things to check. Narrows focus.

3. **Output schema missing**: Auditor invents format. Provide exact JSON structure upfront.

4. **No "read actual files" instruction**: Auditor will hallucinate config values. Tell them explicitly to read ~/.hermes/config.yaml, ~/.hermes/veto/rules/, etc.

5. **Trying to implement during audit**: Let audit finish first. Only then spawn implementation subagents. Mixing phases loses structure.

6. **Ignoring severity/effort in prioritization**: Audit produces IMP-001, IMP-002 etc. Implementation should respect severity ordering and batch similar efforts. A "trivial" security fix should not wait behind a "large" refactor.

7. **Applying config patches without reading actual files**: Subagents will fail or corrupt config if the file structure changed. Parent should dry-run patches before subagent dispatch. Have subagents read the actual file and verify the "old" value matches before patching.

8. **Git workflow assumptions**: If implementation results are committed to a repo:
   - Check if the repo already exists (may have divergent branches from prior runs)
   - Do not assume force-push will work — may be blocked by guardrails
   - Use `git pull --rebase=false` + conflict resolution if branches diverge
   - Verify repo visibility/permissions before committing sensitive config

9. **File permission or write-lock issues**: Subagents may fail to patch/create files due to permissions or lock files. Parent should check file state before subagent dispatch or allow subagent to back off and report. Do not assume a-priori file accessibility.

10. **Subagent batch size**: Parallel subagents all touch the same config or skill files. If more than 3-4 subagents write to overlapping paths, risk collisions. Use `hermes-agent-sync` for deterministic merge or reduce batch size.

## When to use this pattern

- Architectural review of a complex system (Hermes config, multi-agent setup, CI/CD pipeline)
- Security or compliance audit across a domain
- Performance/token optimization pass on large agent setup
- Skills/workflow consolidation and rationalization
- Any assessment where you need structured findings + implementation roadmap in one pass

DO NOT use for:
- Quick bug investigation (use `systematic-debugging` instead)
- Single-file code review (use `scoped-pr-fix-and-verification`)
- Simple feature implementation (use `subagent-driven-development`)
