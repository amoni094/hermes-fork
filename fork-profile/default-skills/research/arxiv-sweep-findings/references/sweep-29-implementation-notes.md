# Sweep 29 Implementation Notes (Aug 2026)

Key learnings from the implementation session, not in any individual skill.

## Critical: Config Append Nesting Bug

When appending blocks to config.yaml, the YAML parser nests the appended
keys under the last open block in the file. If the file ends inside a
sequence or mapping block, all appended keys inherit that nesting depth.

**Symptom:** Keys appear in config.yaml but are not accessible as top-level
keys via `yaml.safe_load()`. They are buried under the last parent block.

**Fix pattern:**
```python
path = '/var/home/rainbow/.hermes/config.yaml'
with open(path) as f:
    content = f.read()
# Verify the last real block ends with a newline at column 0
# before appending new top-level keys.
# After appending, always verify:
parsed = yaml.safe_load(open(path))
assert 'my_new_key' in parsed, 'Key nested incorrectly'
```

**Root cause:** Many existing config blocks (e.g. cron_toolsets) are
sequence items. Appending after a sequence item without closing the sequence
causes YAML to treat new keys as continuation of the sequence.

**Prevention:** After any config.yaml append, immediately run:
```bash
python3 -c "import yaml; c=yaml.safe_load(open('~/.hermes/config.yaml')); print(list(c.keys()))"
```
and verify your new keys appear at the top level.

## am-sentry.py Wiring Pattern

The aggregation line that collects all scan flags uses a very specific exact
string. When adding new scan functions and wiring their flags, search for the
full existing aggregation expression:

```python
# Search for:
all_flags = db_flags + api_flags + action_flags + intent_flags + cred_flags + asi06_flags
# Then extend it with your new _flags variable
```

If `cred_flags` isn't in the file, the previous patch to wire scan_cred_leak
didn't land. Always grep for the actual wiring pattern, don't assume it exists.

## Tag-Not-Drop Quality Gate (ACL 2026)

Failed/error-propagating trajectories should be TAGGED (`[qual_warn]`), not dropped.
ACL 2026 finding: drop semantics lose the only record of what state the agent was in
when the failure occurred. This is essential for:
- Post-hoc rollback traceability via ATP provenance edges
- Downstream audit and filtering
- Contrastive skill improvement (success vs failure pairs)

Implemented in `l1-promote.py::quality_gate_flag()` — tags, never drops.

## Severity Tier Vocabulary (from am-sentry.py, Sweep 29)

```
SEVERITY_BLOCK   -> ATP reject immediately, no Guardian needed
SEVERITY_CONFIRM -> Proceed to Guardian LLM call
SEVERITY_LOG     -> Admit, log to lifecycle.db
SEVERITY_INFO    -> Bypass ATP entirely (Tier R reads)
```

This creates a unified severity vocabulary across sentry (detection) and
ATP admission layers. Reference when wiring new scan functions.

## Skills Needing `hermes curator adopt`

The following skills from this session (and prior sessions) are user-owned
(`created_by=None`) and cannot be patched by the background curator. Run
`hermes curator adopt <name>` to enable autonomous maintenance:

- `trajectory-risk-guardrail`
- `mnemosyne-atp-safety`
- `self-improve-agent`
- `autonomous-agent-loop-design`
- `hermes-memory-surface-selection`

Note: `hermes-agent-skill-authoring` is bundled (also off-limits).

## New Scripts Added This Session

- `~/.hermes/scripts/critique-bank.py` — CritICL critique bank for
  inference-time failure conditioning (arXiv:2608.27455). Maintains a
  JSONL bank of cheap-model failure traces with Jaccard-based retrieval.
  CLI: `critique-bank.py add|match|inject|list|stats`.
  Config: `config.yaml::critique_bank.bank_path + max_critiques`.

## New Config Sections Added This Session

All verified at top-level after the nesting bug fix:

- `harness_fingerprint` (2608.26218) — eval fingerprint for harness identity
- `critique_bank` (2608.27455) — CritICL critique bank
- `tool_slo` (2608.27401) — per-tool latency SLO targets
- `durable_file_write_gate` — write-gate for durable files from IFC labels
- `nl_permission_policies` (2608.27443) — 4-tuple compiled NL permissions
- `loop_harness` (2608.27141) — non-decaying risk floor
- `information_flow_control` (2608.26218) — IFC label enforcement
- `persona_execution_split` (2608.27427/SPA) — split persona from exec
