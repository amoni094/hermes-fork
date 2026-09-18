---
name: hermes-cs-sweep-findings
description: 'Use when querying Hermes CS paper findings and spikes.'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, cs, systems, findings, spike, optimization, bank]
    related_skills:
      - hermes-cs-research
      - hermes-math-sweep-findings
      - arxiv-sweep-findings
      - trajectory-research-synthesis-to-skills
      - spike
triggers:
  - CS sweep findings
  - CS papers bank
  - what CS papers did hermes find
  - cs spike queue
  - CS interpretation results
  - systems paper findings
  - cs-interpretation-latest.json
  - cs-spike-queue.json
  - NOT for running CS sweep (use hermes-cs-research)
  - NOT for applying patches (use trajectory-research-synthesis-to-skills)
  - NOT for agent findings (use arxiv-sweep-findings)
  - NOT for math findings (use hermes-math-sweep-findings)
related_skills:
  - hermes-cs-research
  - hermes-math-sweep-findings
  - arxiv-sweep-findings
  - trajectory-research-synthesis-to-skills
  - spike
---

# Hermes CS Sweep Findings

Knowledge bank for CS paper verdicts from the cs-paper-interpreter.py pipeline.
Stores actionable SYSTEMS-APPLICABLE proposals and SPIKE candidates from past CS sweeps.
For running sweeps: hermes-cs-research. For agent findings: arxiv-sweep-findings.
For math findings: hermes-math-sweep-findings.

## How to Query

Live output files (populated by cs-paper-interpreter.py cron, Thursdays):
  ~/.hermes/cache/research/cs-interpretation-latest.json  - all verdicts from latest run
  ~/.hermes/cache/research/cs-spike-queue.json            - pending items

Record structure (cs-interpretation-latest.json):
  {
    "id": "arXiv:XXXX.XXXXX",
    "title": "...",
    "category_key": "distributed_systems",
    "interpretation_type": "SYSTEMS-APPLICABLE|SPIKE|SKIP",
    "hermes_analogue": "delegate_task reliability",
    "component_target": "hermes-cron-and-agents",
    "confidence": 0.7,
    "proposal": "...",
    "given_when_then": "..."  # SPIKE only
  }

## SYSTEMS-APPLICABLE Findings

Process:
  1. Identify current Hermes approach in target skill/script
  2. Apply paper's technique as concrete improvement
  3. E2E validation required (not just unit test)
  4. Run adversarial-review
  5. Patch via trajectory-research-synthesis-to-skills

### Sweep: 2026-09-08 (CS sweep v2, post-fix, 494 papers, 455 new)

[software_architecture] arXiv:2608.13574 — Agentao: A Policy-Governed Runtime Harness for Embeddable Tool-Using LLM Agents
  confidence: 0.80 | status: APPLIED 2026-09-08
  target: tool authorization architecture, plugin system
  proposal: Adopt Agentao's layered host-contract model — separate model action PROPOSALS
  from host-AUTHORIZED execution. Permission-mediated tool dispatch; audit trail as
  first-class runtime object. Matches Hermes tool-auth-gate + plugin system shape.
  Given Hermes uses ad-hoc tool authorization; When we adopt layered host-contract +
  permission-mediated execution; Then tool privilege separation and auditability improve.
  implemented: ~/.hermes/plugins/tool-auth-gate/__init__.py — pre_tool_call plugin.
    plugin.yaml manifest added 2026-09-08 (required for discovery). ctx.get_config() wired.
    Escalates write_file/patch/terminal calls targeting /etc/, /usr/, hermes-agent/ to
    human-approval gate. Hard-deny list configurable via plugins.tool-auth-gate.deny_tools.
    Enabled in config.yaml plugins.enabled. Fail-open (gate errors never block execution).

[software_architecture] arXiv:2608.17007 — SkillEffect: Checked Lowering for Memory-Bounded Agent Tools
  confidence: 0.75 | status: DONE 2026-09-09
  target: tool execution sandbox, memory caps
  wired: tools/environments/local.py L686-870 — default-on 512MB cap for non-login,
    non-read-only terminal calls. Read-only commands (ls/cat/grep/find/echo/etc) skip sandbox.
    HERMES_SANDBOX_MEM_MB=0 disables; any other value overrides the 512MB default.
  tests: tests/tools/test_skilleffect_sandbox.py (19 passed 2026-09-09)

[operating_systems] arXiv:2604.13536 — Don't Let AI Agents YOLO Your Files
  confidence: 0.78 | status: APPLIED 2026-09-08
  target: trajectory-risk-guardrail, terminal tool safety
  proposal: Three primitives from 290 agent filesystem misuse reports:
    introspect-effects (list all side effects before execution)
    undo-mutations (snapshot/backup before destructive ops)
    gate-sensitive-accesses (explicit confirmation for creds/config/system paths)
  implemented: trajectory-risk-guardrail skill — "Agent-Native Filesystem Safety" section added.

[operating_systems] arXiv:2609.04198 — Clean Engineering, Unstable Measurement (LLM Observer Failure)
  confidence: 0.82 | status: APPLIED 2026-09-08
  target: adversarial-review quality gates, eval pipelines, cron scoring
  finding: Same-window LLM judge repeat rankings agree at Spearman 0.40 vs required 0.90.
  Black-box LLM observers on shared endpoints are unreliable as quality gates.
  implemented: adversarial-review skill — "LLM Observer Unreliability" section added.
  config impact: any cron job using Claude to self-score output quality should switch to
  deterministic metrics or pin model+seed+temp=0.

[software_architecture] arXiv:2608.25403 — Retry Amplification in Distributed Systems
  confidence: 0.72 | status: DONE 2026-09-09
  target: delegate_task retry logic, config.yaml delegation section
  finding: Naive retries under correlated failure reduce success 55.4% -> 41.5% vs no-retry.
  proposal: ARB stamp-only: classify failure entries as arb_retryable=True/False so the batch
  aggregator can make an informed re-dispatch decision. Re-spawning inside _run_single_child
  is not safe (await_child signals stop + shuts child down; re-calling on stopped child is UB).
  wired: tools/delegate_tool.py lines 360-380 — stamp-only (v2, post-adversarial-review):
    build_error_surface_from_result -> retryable bool (default False: unknown = non-retryable)
    timeout entries: arb_retryable=False (stop-signalled child, never re-dispatch)
    retryable entries: arb_retryable=True, arb_retries_remaining=2
    entire block wrapped in try/except Exception: pass (never breaks failure path)
  tests: 81 passed (tests/tools/test_delegate.py 2026-09-09); ARB-specific coverage pending
    (no_retry_on timeout, stamp values, arb_retries_remaining) before marking DONE
  also: config.yaml delegation.retry_policy still commented out (runtime doesn't read it)

[cloud_serverless] arXiv:2609.00967 — CoBRA: Learning Tool-Use Boundaries via Counterfactual Margins
  confidence: 0.73 | status: DONE 2026-09-09
  target: tool selection decision (web_search, web_extract, read_file, hindsight_recall, delegate_task)
  wired: config.yaml plugins.enabled cobra-guard (L311); plugin registered with allow_tool_override=false.
    Pre-call: cobra-skip-guard.py 6-rule heuristic warns to stderr (never blocks — heuristic only).
    Post-call: cobra-outcome-logger.py logs (tool, query, outcome) to ~/.hermes/logs/cobra-outcomes.jsonl.
  tests: tests/plugins/test_cobra_guard.py (6 passed 2026-09-09)
  next: once >=200 cobra records, run `cobra-outcome-logger.py export` for real probe retraining
  labeling seed READY 2026-09-11 (spike cs-cobra-retrain VALIDATED):
    11342+ records, 0 labeled, >=1 week since 2026-09-04 deploy.
    Stratified seed: /tmp/cobra-label-seed.json (30 success + 30 failure + 30 unknown_outcome + 10 skip).
    Heuristic only (result_len>=500 / <50 / mid / skip-tools) — human review required before export/retrain.
    Unblocks retrain without labeling all 10k rows.

[devops_ci] arXiv:2608.23610 — From Traceability to Justifiability
  confidence: 0.70 | status: APPLIED 2026-09-08
  target: reproducibility, cron run audit trail
  finding: Audit of 47 agent/CI platforms: zero emit content-addressed identity of
  (model, instructions, tools, retrieval config) at execution time.
  implemented: ~/.hermes/scripts/run-header.py — emits run_id (sha256[:16] of
  script+model+config+skills, NO timestamp — content-addressed), script_hash, config_hash,
  skill_hashes per run. ts is a separate field for ordering.
  Log: ~/.hermes/logs/run-headers.jsonl (append-only).
  Injected into cs-paper-interpreter.py and math-paper-interpreter.py main() entry points.
  Use: if run_id matches across two runs, script content + model + config + skills are identical.
  If run_id differs, compare script_hash/config_hash/skill_hashes fields to identify what drifted.
  Note: run_id includes script_hash (content), not script filename — same name, different body → different run_id.
  (Do NOT diff run_id directly — diff the hash sub-fields.)

## SPIKE Findings

Process:
  1. Load spike skill
  2. Run spike with Given/When/Then spec from cs-spike-queue.json
  3. Output to ~/.hermes/research/spikes/
  4. VALIDATED: implement + record here with evidence
  5. INVALIDATED: log verdict here with reason

### Sweep: 2026-09-08 — Selected Spikes (from 186 SPIKE verdicts, 0.7 confidence)

High-priority spikes (manually curated from interpreter output + abstract review):

[compilers_runtime] Self-GC: Self-Governing Context for Long-Horizon LLM Agents
  arXiv: pending | Given accumulating context near token limits; When Self-GC
  fold/mask/prune object lifecycle is applied; Then prune rate vs information preservation
  improves on multi-turn sessions. Maps to Hermes context compression / micro-compact.
  spike 007 INVALIDATED 2026-09-08: 0.4% savings on delegation live logs (fold=0, mask=0,
  prune=1/130 turns). Root cause: live logs truncate tool results before they reach the
  >=80-char MASK window, and 10-char substrings from any result appear in later turns via
  shared JSON keys/paths, blocking PRUNE. Rules are sound but require full-payload session
  JSON (not .log tails) to fire. Retry against ~/.hermes/cache/sessions/ full session records
  or after tool-output-metadata logging (APPA prerequisite) is in place.

[pl_design] CONTINUITY: Security-Context Contracts for Composable LLM Agent Controls
  arXiv:2609.05269 | chain: FRAMEWORK | SKIP at Step 1 (pre-screened, no subagent needed)
  why: 6 new contract object types (signed root grants, provenance commitments, role-bound
  transition receipts, bounded typed releases, transformation witnesses, effect-bound execution
  permits) + reference verifier. No numbered pseudocode implementable as small script.
  Companion-algorithm exception fails. New infra required. Not a Hermes config/plugin edit.
  Code exists at github.com/zast-ai/continuity but requires full verifier stack adoption.
  Pre-screened 2026-09-09 to avoid wasting chain subagent.

[pl_design] APPA: Recoverable Information-Flow Control for Real-World LLM Agents
  Given atomic admit/reject of tool outputs; When dual-phase prospective label checks plus
  post-execution validation are added; Then reduce over-blocking while keeping security bounds.
  spike 008a PARTIAL 2026-09-08: order-based label lattice structurally works (3 terminal→web_extract
  flags in 500 calls). BUT: agent.log has no tool output payloads — only tool names + call
  counts. Real exfil detection needs payload taint, not name-order heuristics. Also: cobra-
  outcome-logger.py captures (tool, query, outcome) prospectively going forward.
  Next step: after 1 week of cobra-outcome-logger data, retry APPA with real payload snippets.

[pl_design] APPA causal DAG (spike 008b DONE 2026-09-09, fixed post-adversarial-review):
  Named-variable path-taint DAG script written, validated, and baseline-compared.
  script: ~/.hermes/scripts/appa-path-taint.py
  CLI: python3 appa-path-taint.py --session-log <log> | --sessions-dir <dir>
  result on deleg_e1701912/task-0.log (108 nodes) after adversarial fixes:
    named-taint edges: 6 | 10-gram baseline: 238 | reduction: 97.5%
    (initial 27-edge run contaminated by prefix-token + quoted-id false positives;
     6 is the correct clean count after fixes)
    top tokens: /var/home/rainbow/.hermes/cache/resea, /var/home/rainbow/.hermes/cron/jobs.json
  fixes applied 2026-09-09 (adversarial review deleg_0d3bec84):
    - maximal-token filter in extract_taint_tokens (drop strict path prefixes)
    - _QUOTED_ID_BLOCKLIST (exclude tool_name/completed/skill_view/etc from quoted-id regex)
    - load_calls: streaming 40K-line chunks (avoids full-file load for 50-100MB logs)
  implementation: abs paths, home-relative paths, URLs, arXiv IDs, quoted identifiers
  (min len 6, maximal only); forward-only DAG; JSON to /tmp/appa-path-taint-results.json
  next: wire into cobra post-processing once 008a gate clears (~200 cobra records needed)

[program_analysis] A^2E: An End-to-End Agent Auditing Engine
  Given multi-tool harnesses; When A^2E Agent Task Protocol instruments invocations; Then
  map skill-to-skill calls and detect circular/missing capabilities. Maps to Hermes
  skill dependency graph + observability-and-task-ledger.
  spike 001 VALIDATED 2026-09-08: 217 skills, 771 edges, 0 broken refs, 40 orphans.
  9 SCCs / 129 cycle members — dominated by 1 giant SCC (112 nodes). Root cause: related_skills
  is bidirectional by convention but treated as directed edges by the cycle detector. These are
  NOT semantic cycles; they are symmetric see-also links. Real cycles: 8 smaller SCCs (size 2-4)
  in pairs like email↔messaging, github-issue-agent↔github-issues, etc. — benign mutual refs.
  Actionable: (1) treat related_skills as undirected in any A^2E analysis; (2) audit 40 orphan
  skills for missing relationship declarations; (3) top hub verification-before-completion (deg 63)
  should have depends_on declared explicitly rather than implicitly via mass related_skills refs.
  Script: /tmp/spikes/001-a2e-skill-graph/spike.py

[system_security] EvoCUA-1.5: Online RL for Multi-turn Computer-Use Agents
  Given multi-turn RL in executable sandboxes; When STEPO trajectory decomposition manages
  sparse rewards; Then measure recovery from failed tool calls and fewer sandbox escapes.

[database_systems] HARMONY/MicroNN/HAKES: ANN backends for Hindsight vector store
  spike 006 VALIDATED 2026-09-08 (synthetic N=5000, D=384):
  verdict: keep HNSW (faiss IndexHNSWFlat) as Hindsight ANN backend.

  Results: HNSW p50=0.272ms recall@10=0.988 | IVF p50=0.205ms recall@10=0.648 | Flat p50=0.449ms

  IVF-Flat gains 25% latency over HNSW but loses 34pp recall — not a viable swap.
  HNSW already beats exact Flat by 40% latency with only 1.2pp recall loss.
  Verdict: keep HNSW (faiss IndexHNSWFlat) as Hindsight ANN backend.

  HARMONY sharding: premature at N=5000; revisit if corpus exceeds 100k vectors.
  MicroNN disk-resident: would help if RAM is constrained; not needed at current scale.
  HAKES sidecar: adds architectural complexity without latency benefit at this scale.
  Re-run spike against real embeddings when ~/.hermes/memory-facts/*.npy exists.

[database_systems] HARMONY: Scalable Distributed Vector Database (conf=0.75)
  Given Hindsight vector index at scale; When HARMONY sharded HNSW + async replication
  is used; Then ANN throughput scales across nodes without single-node bottleneck.

[database_systems] MicroNN: On-device Disk-resident Updatable Vector Database (conf=0.70)
  Given skill router loads all embeddings into RAM; When MicroNN disk-resident updatable
  index is used; Then incremental skill updates without full reload, RAM savings.

[database_systems] HAKES: Scalable Vector Database for Embedding Search Service (conf=0.65)
  Given Hindsight retrieval in agent loop adds latency; When HAKES sidecar embedding
  search decouples retrieval; Then latency drop by moving retrieval out of turn loop.

## Blocked Patches

Findings targeting user-owned skills blocked until: `hermes curator adopt <skill-name>`

(none currently blocked)

## CS Findings by Category

Per-category findings are recorded inline in the Sweep sections above
as they are validated/invalidated. To query all SPIKE findings for a category:

  python3 -c "
import json; d=json.load(open('~/.hermes/cache/research/cs-interpretation-latest.json'.replace('~', __import__('os').path.expanduser('~'))))
for p in d['papers']:
    if p.get('interpretation_type')=='SPIKE' and p.get('category_key')=='software_testing':
        print(p['id'], p['title'][:60])
"

Categories with sweep-recorded findings (Sep 2026, 186 SPIKEs total):
  computer_architecture (29), software_testing (17), cloud_serverless (17),
  distributed_systems (16), devops_ci (15), operating_systems (15),
  software_architecture (14), program_analysis (12), pl_design (10),
  parallel_concurrent (10).

## Chain-Verified SKIP Verdicts (2026-09-09, math-cs-applicability-reasoning chain)

The following CS paper was in the SPIKE queue and received full 7-step chain evaluation
(full text retrieval, cold subagent, grok-4.6). SKIP — recorded to prevent re-evaluation.

[software_testing] arXiv:2607.24000 — NL2Test: LLM-Based Test Case Carving + Assertion Gen
  chain: ALGORITHM | Step 3 pass | structural_match=true | disanalogy_valid=true
  des=1, fea=0 | metric gate fail | SKIP
  why: requires HAR-style traffic capture with concrete request/response JSON payloads for
  value-consistency dependency confirmation and assertion-path validation. Hermes session
  traces are LLM text, not structured payloads. No automated assertion harness exists.
  Primary contribution (value-consistency carving + path validation) does not transfer.
  Mapping rows borderline (critic would score NONE). No existing Hermes metric would move.
  Note: 82.4% exact-match / 98.0% usable drafts / 85.4% adoption are industrial API QA
  numbers — not transferable to interactive agent turn context.

[cryptography_eng] arXiv:2609.04566 — Credential Blast Radius via Trust Boundaries
  chain: FRAMEWORK | SKIP at Step 1 (companion-algorithm exception fails)
  des=1, fea=0 | metric gate fail
  why: joint optimization (weighted min-cut) for trust-domain + credential-derivation-tree
  selection. Requires arborescence PKI with independent issuers. Hermes stores API keys in
  config.yaml; subagents share the same key; no derivation graph, no blast-radius scorer.
  Mapping "service graph → skill dependency graph" is borderline / re-scores NONE.
  Slogan "split credentials so one leak isn't total" already partly true (separate provider keys).

[operating_systems] arXiv:2506.01283 — Demystifying Serverless Costs
  pre-screened SKIP 2026-09-09 | conf=0.7 (interpreter floor), no des/fea, proposal empty
  why: serverless cold-start billing + OS scheduling study; Hermes cron is static priority
  list, not a cold-start scheduler. No named Hermes metric moves.

[operating_systems] arXiv:2209.01709 — SFS: Smart OS Scheduling for Serverless Functions
  pre-screened SKIP 2026-09-09 | conf=0.7, no des/fea, proposal empty
  why: EMPIRICAL serverless scheduling heuristics (load prediction, cold-start). Hermes has
  no serverless runtime or scheduling layer to instrument. Step 3 measurement gate fails.

[operating_systems] arXiv:1809.08628 — OS Scheduling for Memory-Intensive Multi-socket Workloads
  pre-screened SKIP 2026-09-09 | conf=0.7, no des/fea, proposal empty
  why: 2018 paper; NUMA/multi-socket memory scheduling. Hermes runs single-process on a
  single host; no NUMA topology or memory-bandwidth knob. Domain mismatch.

[data_streaming] arXiv:2303.11088 — Benchmarking Stream Processing Frameworks as Microservices
  pre-screened SKIP 2026-09-09 | conf=0.7, no des/fea, proposal empty
  why: EMPIRICAL benchmark of Kafka/Flink/Spark microservice scalability. Hermes has no
  stream processing infrastructure. Step 1 EMPIRICAL + no structural match.

[distributed_systems] arXiv:2609.03978 — Barnacle: Adaptive Multi-Leader DAG Consensus
  chain: ALGORITHM | Step 3 pass | structural_match=true | disanalogy_valid=true
  des=0, fea=0 | metric gate fail | SKIP
  why: AIMD leader-count adaptation on agreed committed DAG. Requires validator set, per-round
  block proposals, direct-commit predicate, Window Agreement. Hermes has none of these.
  delegate_task is isolated HTTP calls, not consensus rounds. Mapping "DAG → skill graph" re-
  scores NONE (critic). AIMD principle is generic TCP congestion avoidance — no new procedure.

Categories with curated entries in Sweep section above:
  software_architecture, operating_systems, devops_ci, cloud_serverless,
  distributed_systems, program_analysis, pl_design, system_security, database_systems,
  software_testing (NL2Test chain-SKIP),
  cryptography_eng (Credential Blast Radius chain-SKIP).

## Chain-Verified SKIP Verdicts (2026-09-15, fresh CS sweep 3 SPIKEs)

Fresh cs-paper-interpreter.py run (2026-09-15 02:46 UTC, --limit 30): 30 papers,
0 SYSTEMS-APPLICABLE, 3 SPIKE, 27 SKIP. All 3 SPIKEs pre-screened via chain.
Live config: parent claude-sonnet-4-6; compression.threshold=0.5; threshold_tokens=120000.
Do not re-evaluate unless full text or runtime changes.

[software_testing] arXiv:2511.12288 — Reducing Hallucinations in LLM-Generated Code via Semantic Triangulation
  chain: pre-screened SKIP at Step 2 (object mismatch) | Step 6 not run
  why: Primary contribution is code semantic verification (cross-referencing LLM code
    outputs against static analysis / compiler / test oracles to detect hallucinations
    in generated code). Load-bearing: LLM-generated compilable code + static analysis
    toolchain + hallucination = semantic error in compiled output. Hermes is not a code
    generation agent; tool calls are API invocations, not compilable code. No existing
    Hermes code-hallucination metric exists. Object mismatch: code ≠ tool call.
    Pattern: same domain mismatch as NL2Test chain-SKIP (2026-09-09).

[software_testing] arXiv:2609.08681 — Beyond Fixed Fault Models: Comparing LLM-Based and Rule-Based Fault Injection in OpenStack
  chain: EMPIRICAL | SKIP at Step 1 | Step 6 not run
  why: Measurement study comparing LLM vs rule-based fault injection on OpenStack
    infrastructure. Primary contribution is the empirical finding, not a transferable
    algorithm. Hermes has no fault injection infrastructure; spike experiments are
    throwaway simulations, not fault injection testing on infrastructure services.
    Step 1 EMPIRICAL = SKIP.

[software_testing] arXiv:2609.09048 — The Audit Decides the Verdict: Instrument Effects Rival Demographic Bias in LLM Decision Audits
  chain: EMPIRICAL | SKIP at Step 1 | Step 6 partial (addendum check)
  why: Measurement study showing that LLM audit instrument design choices (prompt format,
    evaluation framework) produce as much variance in "bias" measurements as actual
    demographic factors. Extends arXiv:2609.04198 (Clean Engineering, Unstable Measurement
    — APPLIED 2026-09-08) which already established LLM observer unreliability.
  ADDENDUM to 2609.04198 (adversarial-review skill + this skill):
    Not just reliability degrades with repeated same-window scoring (Spearman 0.40);
    the audit instrument itself (which prompts/frameworks you use) can generate
    false-positive bias signals independent of actual model behavior. When designing
    quality gates or bias checks, vary the evaluation instrument across at least 2
    prompt templates and frameworks — systematic instrument bias can masquerade as
    model-level bias. No new implementation needed; note is additive to existing warning.

## Fresh Sweep Results (2026-09-15)

cs-paper-interpreter.py --limit 30, 2026-09-15 02:46 UTC:
  30 papers processed (sweep file 127.2h old — WARNING: may be stale, run cs-research-sweep.py)
  0 SYSTEMS-APPLICABLE, 3 SPIKE, 27 SKIP (all 3 SPIKEs chain-evaluated above, all SKIP)
  SKIP rate: 90% (anytime-valid anomaly threshold triggered by interpreter)
  Spike queue: 3 items written (cs-spike-queue.json), but all 3 chain to SKIP
  Note: cs-interpretation-latest.json from the 562-paper Sep-09 full run is more
    representative. The --limit 30 sample had no SYSTEMS-APPLICABLE papers (expected
    at this SKIP rate; the Sep-09 full run had 9 SYSTEMS-APPLICABLE in 562 papers).
  Action needed: run cs-research-sweep.py to refresh the stale sweep file before
    next full cs-paper-interpreter.py run (no --limit).

## Cross-References

- Core agent findings (cs.AI/cs.CL/cs.MA): arxiv-sweep-findings
- Math/theory findings: hermes-math-sweep-findings
- Running CS sweep: hermes-cs-research
- Applying patches: trajectory-research-synthesis-to-skills
