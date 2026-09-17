# Multi-Phase Config/Infrastructure Orchestration

## Use Case

Delegating large-scale infrastructure or config upgrades that span **multiple sequential phases** (audit → implementation → export → validation → push) to a single orchestrator subagent that manages its own sub-phases and verifies outputs internally.

## When This Pattern Emerged

Session of 2026-07-01: Hermes workflow+security+token-efficiency upgrade pass.
User request: "enable claude code skill and use claude 5 fable as orchestrator to research and implement upgrades to hermes workflow, security, token efficiency, and config more generally. Push to the hermes config git once implemented locally."

## Pattern Structure

```
User →[orchestrator context packet]→ Orchestrator subagent
    ├── Phase 1: Security Audit (read veto rules, check agent hooks)
    ├── Phase 2: Token Efficiency (research thresholds, patch config)
    ├── Phase 3: Workflow Upgrades (review budget policy, cron jobs, delegation depth)
    ├── Phase 4: General Config Cleanup (hygiene, missing settings)
    └── Phase 5: Export + Validate + Push (git operations)
        ├── Sanitize config (strip secrets)
        ├── Generate/update docs
        ├── Run validation script
        ├── Commit and push
```

Each phase includes identification, patching, and documentation. The orchestrator runs serially but independently verifies outputs before moving to the next phase.

## Context Packet for Multi-Phase Config Work

Good structure (from session):

```
ROLE: Orchestrator for [domain] upgrades

ENVIRONMENT:
- Config path: /path/to/config.yaml
- Git repo: /path/to/repo (origin: https://...)
- Related files: /path/to/skills/, /path/to/hooks/
- Budget policy: /path/to/policy.yaml

CONTEXT FROM [REPO]:
- Current state snapshot (from docs/current-workflow.md)
- Existing research (adversarial-critique.md, remediation-pass-3.md)
- Config highlights (model, delegation, compression, etc.)

TASK — implement ALL of the following upgrades in sequence:

1. [PHASE 1]: [specific goals]
   a. [read step]
   b. [identify gaps]
   c. [patch]
   d. [document]

2. [PHASE 2]: [specific goals]
   [same structure]

3. [PHASE 3]: [same structure]

4. [PHASE 4]: [same structure]

5. [PHASE 5: EXPORT]
   a. [run existing scripts]
   b. [sanitize outputs]
   c. [validate]
   d. [commit with message]

CONSTRAINTS:
- Use `hermes config set KEY VALUE` for config changes (do not directly edit)
- Do NOT commit API keys, tokens, base_urls with auth, or personal data
- Read existing docs before writing new ones
- Prefer conservative/restrictive on security choices
- Run validate_repo.py before pushing
- Keep commit messages descriptive

TOOLS AVAILABLE: terminal, file (read_file, write_file, patch, search_files), web

Return: summary of all changes, files modified, and git commit hash.
```

## Durable Pitfalls — Parent Hand-off

**The orchestrator produces research, findings, and a local commit. The parent must handle:**

### 1. Final documentation generation

The orchestrator typically writes the commit message and internal research notes. But the parent should write a **durable upgrade doc** for future reference that captures:
- What was changed and why (rationale per finding)
- Categorization by risk (CRITICAL / HIGH / MEDIUM / LOW)
- What was skipped and why
- Specific commands for reproducibility (e.g., `hermes config set agent.tool_use_enforcement strict`)

File path pattern: `docs/upgrade-pass-{DATE}.md` (e.g., `upgrade-pass-2026-07-01.md`)

Why the parent owns this:
- The parent has broader context about user intent and project history
- Upgrade docs are read by humans later; they need narrative structure, not just checklist items
- The orchestrator focuses on mechanical implementation; the parent owns the story

Example from session:
```markdown
# Hermes Upgrade Pass — 2026-07-01

Orchestrated by claude-fable-5 / claude-sonnet-4-6 subagent. All changes applied via
`hermes config set` or direct edits to veto/hook files. No secrets committed.

## 1. Security Hardening

### 1a. Veto hard-block rules (+6 new rules)

[table of rules with rationale]

### 1b. Veto warn rules (+3 new rules)

[table of rules with rationale]
```

### 2. Git push and conflict resolution

The orchestrator will `git commit` but may not push if the remote has diverged. The parent must:

1. After the orchestrator finishes, run:
   ```bash
   cd /path/to/repo && git status --short --branch
   git log --oneline -3
   ```

2. If push failed with a remote divergence error ("reject... fetch first"), the parent must:
   ```bash
   git pull --rebase
   # resolve any conflicts manually or with "git checkout --ours <file>" for mechanical merges
   git rebase --continue
   git push
   ```

3. Verify the final state:
   ```bash
   git log --oneline -3
   git push  # should succeed now
   ```

Why the parent owns this:
- Rebase conflicts require human judgment about which version is authoritative
- The orchestrator cannot interact with the user to decide "ours vs theirs"
- The parent has the original intent and can make the right call

Example from session:
```
[deleg_d05e13cc returned. Orchestrator committed but push was rejected.]

Parent runs:
  git pull --rebase
  # conflict in config.sanitized.yaml — our version is correct
  git checkout --ours config.sanitized.yaml && git add config.sanitized.yaml
  GIT_EDITOR=true git rebase --continue
  git push
  
Result: commit b16dbd7 is live at https://github.com/amoni094/hermes-config
```

### 3. Verification of exported artifacts

Before claiming success, the parent should verify:

- Config sanitization succeeded (no API keys in the exported .yaml)
- Scripts exist and are executable
- Git history is clean (commit hash is reachable and push succeeded)
- New docs are present and readable

Commands:
```bash
cd /var/home/rainbow/hermes-config
grep -i "api_key\|auth\|token" config.sanitized.yaml  # should be quiet (no matches)
ls -la scripts/sanitize_config.py  # should exist and be +x
git log --oneline -1  # should show the upgrade commit
git show HEAD -- docs/upgrade-pass-*.md  # should show the new doc
```

## Advantages

1. **Single context** — orchestrator owns all phases and can cross-reference findings
2. **Internal verification** — each phase validates outputs before the next starts
3. **Document generation** — orchestrator writes research summaries; parent writes durable docs
4. **Audit trail** — git commit with structured message captures what changed and why
5. **No context drift** — no user interruptions or context resets between phases

## Disadvantages

1. **Token use** — long orchestrator session may cost more than parallel workers
2. **Debugging if blocked** — harder to inspect mid-phase failures if the orchestrator hangs or loops
3. **Background wait** — parent session must wait for orchestrator result before seeing outcomes
4. **Hand-offs needed** — parent must finish documentation, conflict resolution, and push verification

## Routing: Model Choice

> **LIVE 2026-08-25:** parent `grok-4.5`, leaves `mistral-small-latest`. Canonical
> `claude-routing-hierarchy`. The 2026-07-06 note below is a historical correction
> about Anthropic model *existence*, not current wiring.

> Note (corrected 2026-07-06): `claude-opus-4-8` and `claude-sonnet-4-6` DO exist and are
> live-callable on this account. Neither is wired as `model.default` or `delegation.model`.
> Using Opus for a specific phase requires a dedicated session or a temporary
> `delegation.model` override that is restored to `mistral-small-latest` immediately after spawn.

For config/infrastructure upgrades:
- **Security audit phases:** parent `grok-4.6` or dedicated `claude-opus-4-8` session; Fable only on explicit ask
- **Token efficiency / mechanical phases:** already on `mistral-small-latest` leaves
- **Adversarial pass:** dedicated `gpt-5.6-sol` session, not Grok grading Grok

## Hermes-Specific Export Pattern

The hermes-config repo (`/var/home/rainbow/hermes-config`) has established export/validation automation:

- **scripts/validate_repo.py** — checks redaction (no API keys, tokens, auth in URLs), export hygiene, Python script integrity
- **scripts/generate_skill_inventory.py** — generates authoritative skill inventory from live files + CLI + usage reconciliation
- **scripts/sanitize_config.py** — strips api_key, auth, and sensitive base_urls from live config.yaml (new in 2026-07-01 upgrade)
- **config.sanitized.yaml** — exported from live config.yaml with secrets stripped
- **docs/** — upgrade/research reports, current-workflow snapshot, adversarial critiques, remediation passes

For future config exports:
1. Read existing docs (current-workflow.md, adversarial-critique.md, latest remediation pass)
2. Dispatch orchestrator on upgrade phases
3. After orchestrator completes:
   a. Write upgrade doc (parent responsibility — see "Final documentation generation" above)
   b. Run `scripts/validate_repo.py` to verify no secrets leaked
   c. Resolve any git conflicts (parent responsibility — see "Git push and conflict resolution" above)
   d. Verify final push succeeded

## Verification Checklist

Before parent claims orchestrator succeeded:
- [ ] Orchestrator returned commit message and file list
- [ ] Run `cd /path/to/repo && git log --oneline -5` to verify commit was made locally
- [ ] Write durable upgrade doc with rationale (see "Final documentation generation" above)
- [ ] Commit again if needed: `git add docs/upgrade-pass-*.md && git commit -m "docs: ..."`
- [ ] Run `git pull --rebase && git push` to handle remote divergence
- [ ] Run `git show <hash>` to inspect what changed
- [ ] Spot-check config.yaml for redacted secrets (no API keys visible in config.sanitized.yaml)
- [ ] Check that `scripts/validate_repo.py` passed (inspect log output from orchestrator or run fresh)
- [ ] Read the generated upgrade doc to understand rationale
- [ ] If toolsets include web, check web_search/web_extract results for stale/dead links

## Related Skills

- `hermes-operating-pattern` — broader Hermes workflow and security patterns
- `hermes-context-budgeting` — token-efficiency tuning (relevant to phase 2)
- `subagent-driven-development` — parent skill for orchestrator delegation
- `verification-before-completion` — parent verification checklist after orchestrator finishes
- `config-audit-and-hardening` — for security-only audit passes without the full multi-phase workflow
