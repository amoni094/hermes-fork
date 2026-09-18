# Sweep 19 — Code-Reality Gap Audit (deleg_136df607, Aug 19 2026)

3-subagent parallel audit verifying HIGH-rated sweep findings against actual executable
code in /var/home/rainbow/.hermes/scripts/ — not skill docs.

## Audit Methodology

The correct methodology for verifying sweep implementation:
1. Read every named target file end-to-end (not just grep)
2. For each finding, identify the specific code artifact that MUST exist (function, param, tag, SQL column, etc.)
3. Check only executable evidence: a skill doc saying "do X" is NOT implementation
4. Report IMPLEMENTED / SKILL-ONLY / MISSING with specific line-number evidence

Grep patterns used:
- `grep -n 'def apply_turn_distance_rdm\|turn_rdm\|apply_turn_distance_rdm'` for RDM wiring
- `grep -n 'source_type\|--source-type'` for PSE tagging
- `sqlite3 lifecycle.db .schema` (or grep for CREATE TABLE) for DB columns
- `grep -n 'retry\|classify\|ErrorClass'` for retry classification

## Full Audit Results

### Task 1/3 — Runtime Behavior Findings

| # | Finding | Target | Status | Evidence |
|---|---------|--------|--------|----------|
| 1 | AMD 3-Tier Injection | unified-recall.py | SKILL-ONLY | L0/L1/L2 is output-tier display, not injection policy. No logic gating by tool-error events. |
| 2 | AgentMemBench EKV Dominance | l1-promote.py, config.yaml | MISSING | No EKV/long_horizon/kv_cache strings. No horizon-length threshold switching stores. |
| 3 | LycheeMemory Segment-Level | l1-extract.py | PARTIAL | l1-extract sends per-session prompt; no segment chunking before promote. |
| 4 | GPM TTL/expiry | lifecycle.db | PARTIAL | valid_to column exists in schema code but lifecycle.db had never been created on disk. |
| 5 | MindMemOS temporal structure | l1-graphiti-write.py | IMPLEMENTED | as_of_tag present; episodes include temporal context. |
| 6 | ERSkill trie/frontier retrieval | unified-recall.py | MISSING | RRF ranking only; no trie or frontier re-ranking. |
| 7 | Phase Transitions thresholds | l1-promote.py | MISSING | NLI thresholds are static constants. |
| 8 | MAP-Graph confidence scores | l1-graphiti-write.py | MISSING | Episodes carry no confidence score field. |
| 9 | GUIDE schema validation on receipt | subagent-output-contract skill | SKILL-ONLY | Skill says "validate on receipt" but no running validation code. |
| 10 | Dependency-Guided Rollback edges | memory-provenance.py | IMPLEMENTED | memory-provenance.py exists and writes memory_id→action_id edges. |

### Task 2/3 — Context/Retrieval/Config Findings

| # | Finding | Target | Status | Evidence |
|---|---------|--------|--------|----------|
| 1 | RACS Stability-Rank Ordering | config.yaml | MISSING | No prompt_block_order, stability_rank, or prefix_drift keys. |
| 2 | SEU Relevance-vs-Interference | unified-recall.py | MISSING* | *Actually implemented in this session — seu_filter() function exists with interference scoring |
| 3 | Evo-Harness Compilation | any script | MISSING | No script strips task artifacts and groups by cluster. |
| 4 | ai-memory 16KB caps/drop-before-spool | l1-promote.py | PARTIAL | 16KB cap enforced; no fast/slow split. |
| 5 | OpenViking L0/L1/L2 tiers | config.yaml, unified-recall.py | IMPLEMENTED | tier_thresholds in config; --tier param in unified-recall. |
| 6 | TRACE LLM-veto merge gate | l1-promote.py | PARTIAL | NLI check exists but is 3-state NLI, not LLM-veto. No chronological guard. |
| 7 | AgentSysBench tool dedup | config.yaml | IMPLEMENTED | tool_result_cache present in config.yaml. |
| 8 | BATON role-aware routing | config.yaml | MISSING | Flat single-model delegation; no role-aware routing. |
| 9 | CommitLore rejected_alternative type | l1-promote.py VALID_TYPES | IMPLEMENTED | 'rejected_alternative' in VALID_TYPES (added this session). |
| 10 | GPM TTL purge | memory-ttl-purge.py | IMPLEMENTED | Cron runs memory-ttl-purge.py daily at 3am. |

### Task 3/3 — Verification of Session Implementations

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| 7 | Content-hash dedup (l1-graphiti-write.py) | ✅ IMPLEMENTED | Line 269: hashlib.sha256(fact['text'][:200].encode()).hexdigest()[:12] |
| 8 | 3-state NLI SUPPLEMENTARY reachability | ✅ IMPLEMENTED | Lines 523, 817-820: full path reachable in contradiction_check() and process_date() |
| 9 | lifecycle.db schema | ✅ PARTIAL | memory_status ✅, valid_to ✅ (as TTL proxy), but 4 new columns (source_type, session_id, action_id, last_accessed_turn) added THIS session |
| 10 | config.yaml coverage | ✅ UPDATED | rdm.rdm_lambda, tier_thresholds, retry_budgets, default_toolset_policy added this session |
| 1 | PSE source_type end-to-end | ✅ IMPLEMENTED THIS SESSION | --source-type arg → process_date(source_type=) → write_to_staging(source_type=) → [source=...] tag → lifecycle.db |
| RDM | Turn-distance decay | ✅ IMPLEMENTED THIS SESSION | apply_turn_distance_rdm() defined at line 415; wired into recall(turn_rdm=True) at lines 478, 508-509 |
| Retry | 5-class retry budget | ✅ IMPLEMENTED THIS SESSION | retry-budget-guard.py created; wired via spec_from_file_location in both l1-promote + l1-graphiti-write |

## Python Pitfalls Discovered During Implementation

### Hyphenated Module Filenames: Use spec_from_file_location

Python's import system cannot resolve modules whose filenames contain hyphens:
```
# WRONG — ModuleNotFoundError even with sys.path manipulation:
sys.path.insert(0, "/path/to/scripts")
from retry_budget_guard import with_retry   # fails: no retry_budget_guard.py

# CORRECT — works for any filename, hyphenated or not:
import importlib.util
spec = importlib.util.spec_from_file_location(
    "retry_budget_guard",                    # logical module name (hyphens ok)
    "/path/to/scripts/retry-budget-guard.py" # actual filename with hyphens
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.with_retry(...)                          # use normally after loading
```

This affects any script with hyphens in its name (retry-budget-guard.py, memory-ttl-purge.py, etc.).
Always use spec_from_file_location for sibling-script dynamic imports in ~/.hermes/scripts/.

### ast-Based Function Extraction for exec() Testing

When testing a function from a script in isolation via exec(), the naive line-by-line
extractor breaks on multi-line type annotations (list[dict], etc.) because the
"stop when indentation drops" heuristic counts `(` before the body starts.

Use ast.parse + fn.lineno/end_lineno instead:

```python
import ast, textwrap

src = open("/path/to/script.py").read()
tree = ast.parse(src)

# Find the function node
fn_node = next(
    n for n in ast.walk(tree)
    if isinstance(n, ast.FunctionDef) and n.name == "my_function"
)

# Extract exact source lines (1-indexed)
lines = src.splitlines()
fn_src = "\n".join(lines[fn_node.lineno - 1 : fn_node.end_lineno])
fn_src = textwrap.dedent(fn_src)

ns = {"math": math}
exec(fn_src, ns)
result = ns["my_function"](...)
```

This is the only reliable method when functions have complex type annotations.

## Remaining Gaps Not Implemented This Session

These remain SKILL-ONLY or MISSING — require future sessions:

1. **AMD proactive/reactive injection policy** — requires agent-loop integration, not just a script change
2. **ERSkill trie/frontier re-ranking** — complex algorithm; needs dedicated implementation
3. **MAP-Graph confidence scores on Graphiti edges** — requires Graphiti schema extension
4. **BATON role-aware routing** — requires Hermes delegation config extension beyond what's currently supported
5. **RACS prefix-drift detection** — requires per-turn hash tracking, not yet implemented
6. **Evo-Harness cluster-based skill compilation** — novel pipeline component not yet built

## Audit Pattern: Use as Template for Future Gap Checks

When running a post-sweep code-reality gap audit:
1. Dispatch 2-3 subagents in parallel, each covering a different batch of findings
2. Have each subagent read target files end-to-end (not just grep)
3. Require evidence format: "file:line — specific code that proves it"
4. "Skill doc says X" is never sufficient evidence
5. Check lifecycle.db ACTUALLY EXISTS on disk (sqlite3 path .schema) vs. schema code that would create it
6. After audit: implement gaps in priority order (HIGH-rated, smallest code change first)
7. Write verification script that tests both code structure AND runtime behavior
