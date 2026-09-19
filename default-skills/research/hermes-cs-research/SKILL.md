---
name: hermes-cs-research
description: 'Use when running the Hermes CS systems/engineering sweep. Not for querying past CS verdicts/spikes (use hermes-cs-sweep-findings). Not for core agent cats 1-7 (use hermes-research).'
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [research, arxiv, cs, systems, engineering, sweep, primers, pipeline]
    related_skills:
      - hermes-research
      - hermes-cs-sweep-findings
      - hermes-math-research
      - arxiv-sweep-findings
      - trajectory-research-synthesis-to-skills
      - spike
      - math-cs-applicability-reasoning
      - transfer-applicability-chain
triggers:
  - hermes CS research
  - CS sweep
  - run CS papers
  - computer science research sweep
  - CS primers
  - cs-paper-interpreter
  - run CS research pipeline
  - cs-research-sweep.py
  - CS cron sweep
  - ACM CCS research
  - systems engineering papers
  - NOT for core agent paper sweep (use hermes-research)
  - NOT for CS findings bank (use hermes-cs-sweep-findings)
  - NOT for math/theory papers (use hermes-math-research)
related_skills:
  - hermes-research
  - hermes-cs-sweep-findings
  - hermes-math-research
  - arxiv-sweep-findings
  - trajectory-research-synthesis-to-skills
  - spike
  - math-cs-applicability-reasoning
---

# Hermes CS Research

CS systems/engineering sweep pipeline: 30 categories aligned to the ACM Computing
Classification System (CCS 2012). Runs separately from the core agent sweep and math
sweep, with its own seen-papers cache, interpreter layer, and primers directory.

NOT for core agent categories 1-7 (use hermes-research).
NOT for math/theory categories 8-51 (use hermes-math-research).
NOT for past findings (use hermes-cs-sweep-findings).

## Model Routing

Use **deepseek-v4-pro** (via `deepseek` provider) for long-horizon CS synthesis tasks:

  Eligible: summarising/synthesising papers, literature review, category mapping,
  idea-to-script translation when the output is text (no execute_code/terminal loops).
  Command: `hermes chat -m deepseek-v4-pro --provider deepseek -q "..."`

  NOT eligible: interpreter runs (cs-paper-interpreter.py), execute_code loops,
  multi-turn agentic tool chains — reasoning_content 400 bug in multi-turn tool calls.

  Fallback: grok-4.6 (delegate_task default) when DeepSeek is unavailable or rate-limited.
  Avoid Beijing peak hours (09:00-12:00, 14:00-18:00 CST) — 2x pricing surge.
  Non-think mode only (do not pass reasoning param).

## Why This Domain

The ACM CCS covers systems infrastructure that Hermes runs on and operates through.
CS papers in these categories can improve:
  - Agent reliability (distributed systems, OS scheduling, fault tolerance)
  - Security posture (sandboxing, supply chain, privacy engineering)
  - Data layer (database query optimisation, vector retrieval, streaming)
  - Toolchain (compilers, program analysis, formal verification)
  - Protocol layer (network protocols, content delivery, edge computing)
  - HCI layer (conversational AI, collaborative systems, accessibility)

## CS Categories (30 total, ACM CCS-aligned)

### Software Engineering / PL
  CS-1.  software_testing      — Fuzzing, property-based testing, automated test repair
  CS-2.  program_analysis      — Static analysis, abstract interpretation, synthesis
  CS-3.  pl_design             — Type systems, effect systems, DSLs, session types
  CS-4.  compilers_runtime     — JIT, MLIR, GC, WebAssembly, LLVM optimisation
  CS-5.  software_architecture — Microservices, plugin systems, modularity
  CS-6.  devops_ci             — CI/CD pipelines, reproducible builds, GitOps

### Systems / Distributed
  CS-7.  distributed_systems   — Consensus (Raft/Paxos), CRDT, fault tolerance, TXN
  CS-8.  operating_systems     — Scheduling, eBPF, cgroups, kernel design, unikernels
  CS-9.  computer_architecture — Cache, NUMA, SIMD, RISC-V, branch prediction
  CS-10. parallel_concurrent   — Lock-free structures, actor model, async/await
  CS-11. cloud_serverless      — Serverless, auto-scaling, cold-start, Kubernetes
  CS-12. edge_embedded         — TinyML, IoT, embedded AI, RTOS, energy efficiency

### Security / Privacy
  CS-13. cryptography_eng      — Post-quantum crypto, TLS, key management, ZK-proofs
  CS-14. system_security       — Sandboxing, privilege separation, supply chain, TEE
  CS-15. privacy_engineering   — Differential privacy, GDPR, k-anonymity, PETs
  CS-16. secure_mpc            — MPC protocols, homomorphic encryption, secret sharing
  CS-17. network_security      — IDS, zero-trust, VPN, DDoS, network anomaly detection

### Data Management
  CS-18. database_systems      — Query optimisation, MVCC, columnar, vector DBs, LSM
  CS-19. data_streaming        — Stream processing, Flink, Kafka, exactly-once semantics
  CS-20. information_retrieval — Dense retrieval, hybrid search, BM25, re-ranking, RAG
  CS-21. knowledge_representation — KGs, ontologies, RDF/OWL, SPARQL, entity linking

### HCI
  CS-22. ui_design             — Accessibility, usability, adaptive UI, TUI design
  CS-23. conversational_ai     — Task-oriented dialogue, intent detection, NLU pipelines
  CS-24. collaborative_systems — OT, CRDT for collaboration, shared document, pair tools

### Networks
  CS-25. network_protocols     — QUIC, HTTP/3, TCP congestion, BGP, NDN
  CS-26. wireless_mobile       — 5G, WiFi 6, mesh networking, handoff
  CS-27. content_delivery      — CDN, cache eviction, edge caching, TTL optimisation

### Emerging
  CS-28. quantum_systems       — Quantum error correction, VQA, quantum software stack
  CS-29. neuromorphic          — SNN hardware, in-memory computing, photonic, analog AI
  CS-30. formal_specification  — TLA+, Alloy, Coq, seL4, model checking distributed

## Hermes Relevance Tiers

HIGH priority (directly improves Hermes components today):
  software_testing, program_analysis, software_architecture, devops_ci,
  distributed_systems, system_security, privacy_engineering, database_systems,
  information_retrieval, knowledge_representation, conversational_ai, formal_specification

MED priority (useful foundations, may drive spikes):
  pl_design, compilers_runtime, operating_systems, parallel_concurrent,
  cloud_serverless, cryptography_eng, secure_mpc, data_streaming,
  ui_design, collaborative_systems, network_protocols, content_delivery

LOW priority (monitor; foundational, low near-term application):
  computer_architecture, edge_embedded, network_security, wireless_mobile,
  quantum_systems, neuromorphic

## Scripts

### cs-research-sweep.py
Runs the core sweep restricted to CS categories CS-1 through CS-30.
Separate seen-papers cache (seen_papers_cs.json) from the agent + math sweeps.
Suppresses arxiv listing harvests for broad cs.SE/cs.PL/cs.NI (too noisy);
keyword searches drive CS coverage.

```bash
python3 ~/.hermes/scripts/cs-research-sweep.py [--dry-run] [--limit N]
```

Outputs:
  ~/.hermes/cache/research/hermes-cs-sweep-latest.json
  ~/.hermes/cache/research/seen_papers_cs.json  (separate dedup cache)

### cs-paper-interpreter.py
Takes the CS sweep JSON, reads each paper's abstract, and produces one of three verdicts:

  SYSTEMS-APPLICABLE — CS technique directly improves a Hermes system component.
                       Produces before/after spec for the target module.
  SPIKE              — CS technique describes an approach Hermes doesn't use yet.
                       Produces Given/When/Then spike candidate.
  SKIP               — No plausible Hermes analogue.

```bash
python3 ~/.hermes/scripts/cs-paper-interpreter.py [--dry-run] [--limit N] [--input PATH]
python3 ~/.hermes/scripts/cs-paper-interpreter.py --fetch-abstracts  # slower, better
```

Outputs:
  ~/.hermes/cache/research/cs-interpretation-latest.json  (all verdicts)
  ~/.hermes/cache/research/cs-spike-queue.json            (pending items)

### cs-primers-overnight.py
Generates or refreshes primer files for each CS category. Primers are loaded by
cs-paper-interpreter.py during interpretation to provide category context.

```bash
python3 ~/.hermes/scripts/cs-primers-overnight.py [--category KEY] [--force]
```

Primers: ~/.hermes/cache/research/cs-primers/<category_key>.txt
Index:   ~/.hermes/cache/research/cs-primers/INDEX.txt

## CS Paper Interpretation Layer

Three verdict types (parallel to math interpreter but CS-specific):

  SYSTEMS-APPLICABLE — CS technique maps to a specific Hermes component.
  SPIKE              — CS technique is worth a throwaway experiment in Hermes.
  SKIP               — No plausible Hermes improvement after honest assessment.

## Authoritative Interpretation Chain (manual / agent-assisted review)

For any paper that survives the initial abstract triage and is a candidate for
SYSTEMS-APPLICABLE or SPIKE, run the applicability reasoning chain.

Trigger criteria:
  - Script output is SYSTEMS-APPLICABLE or SPIKE -> always run chain.
  - Script output is SKIP but a human reviewer suspects false-negative
    (abstract mentions a concrete algorithm or heuristic applicable to a
    named Hermes component) -> run chain.
  - Script output is SKIP with no reviewer doubt -> do not run chain.
  - LOW-priority tier papers (quantum_systems, neuromorphic, etc.): skip
    chain unless the paper explicitly proposes a concrete algorithm (not
    just a bound or framework). Most will SKIP at Step 1 (THEOREM/FRAMEWORK).

  skill_view(name='math-cs-applicability-reasoning')

This is the authoritative source for final verdicts on borderline papers.
Full text is required (abstract-only = DEFER).

Note on cs-paper-interpreter.py: the script runs a SIMPLIFIED version only
(feasibility gate + structural analogy check, no full 7-step chain, no deterministic
verdict formula). The script's verdicts are first-pass filters. Any SPIKE or
SYSTEMS-APPLICABLE from the script that will be actioned requires a FRESH full-text
run of the chain (load full paper, start from Step 0) — do NOT feed script output
fields into the chain formula. Chain verdict is terminal (one-pass); a chain SPIKE
does not re-trigger the chain.

### Interpretation Orientation (complement to the chain, not a substitute)

1. Ask "what existing Hermes component has analogous structure?" first.
   The chain's Step 2 COMPONENT_MAP (closed object/operation taxonomy of 18 Hermes
   runtime components, defined in math-cs-applicability-reasoning) is the authoritative
   list. cs-paper-interpreter.py may have its own simplified mapping table —
   treat that as a subset only.

2. SYSTEMS-APPLICABLE / OPTIMIZATION (chain equivalent): need a concrete component
   name and what changes — not just 'this improves reliability.' Write the current
   approach and what the paper substitutes.
   (SYSTEMS-APPLICABLE = script verdict; OPTIMIZATION = chain verdict for the same
   outcome. The Handoff maps chain OPTIMIZATION -> recorded as SYSTEMS-APPLICABLE.)
   Chain Step 4 requires naming an existing Hermes metric. Step 5 requires an
   estimated delta grounded in paper numbers (for des=2, same metric/same task setting).

3. SPIKE: must specify:
   - Given: which Hermes component currently uses a naive/heuristic approach
   - When: which CS technique from the paper we apply
   - Then: a measurable improvement (latency, reliability, correctness)
   Output to ~/.hermes/research/spikes/.
   Chain produces SPIKE when feasibility=1 (one or two uncertain assumptions with
   verification tests) or when a HEURISTIC has no named Hermes tunable parameter yet.

4. Workflow: run interpreter -> review SPIKE/SYSTEMS-APPLICABLE queue -> run chain
   (fresh full-text run from Step 0; see Authoritative Interpretation Chain above;
   chain verdict is terminal — one-pass only) -> confirm with user -> run spike
   experiment (if SPIKE; see spike skill for experiment protocol) ->
   VALIDATED (spike confirms): patch target -> INVALIDATED (spike disconfirms): log to
   hermes-cs-sweep-findings.
   4. For any chain OPTIMIZATION (recorded as SYSTEMS-APPLICABLE in the findings bank),
      run adversarial-review before patching. adversarial-review object: the proposed
      implementation (target component, current behavior, intended change, affected
      surface) — not the chain reasoning itself.

5. Theoretical CS papers (complexity proofs, survey-only) = SKIP unless there's
   a concrete implementation result.
   Chain Step 1: THEOREM or EMPIRICAL without a secondary algorithm or heuristic
   contribution = SKIP.

### CS -> Hermes Component Map (summary)

  software_testing      -> skill test harness, agent output verification
  program_analysis      -> skill dependency analysis, tool validation
  distributed_systems   -> delegate_task fault tolerance, cron job reliability
  system_security       -> sandboxed code execution, tool privilege separation
  privacy_engineering   -> memory data minimisation, PII handling in tools
  database_systems      -> hermes_state.db optimisation, vector DB retrieval
  information_retrieval -> skill retrieval ranking, memory semantic search
  knowledge_representation -> Graphiti KG schema, skill taxonomy ontology
  conversational_ai     -> intent detection, dialogue state in gateway
  formal_specification  -> agent loop invariants, verified tool contracts
  cloud_serverless      -> agent worker scaling, auto-scaling patterns
  operating_systems     -> async agent loop scheduling, cron priority tuning
  (full map: COMPONENT_MAP in math-cs-applicability-reasoning, Step 2)

## Cron Integration

Sweep job:
  cron name: hermes-cs-sweep
  script:    cs-research-sweep.py
  no_agent:  true (pure Python)
  frequency: weekly (Thursdays, offset from math sweep run)

Interpreter job:
  cron name: hermes-cs-interpret
  script:    cs-paper-interpreter.py
  no_agent:  true (pure Python)
  deliver:   spike-queue digest to user
  frequency: weekly (day after CS sweep)

Primers job (one-off, then quarterly):
  cron name: hermes-cs-primers
  script:    cs-primers-overnight.py
  no_agent:  true (pure Python)
  frequency: quarterly (or on-demand with --force)

## Cron Status (as of 2026-09-09)

All three CS cron jobs are active (hermes cron list to verify):

  cron name: cs-research-weekly       — Thursdays 02:00
  cron name: cs-research-interpret    — Thursdays 06:30 (after sweep)
  cron name: cs-primers-quarterly     — quarterly on-demand

To re-create if missing:
```bash
hermes cron create "0 2 * * 4" --name cs-research-weekly --script cs-research-sweep.py --no-agent --deliver local
hermes cron create "30 6 * * 4" --name cs-research-interpret --script cs-paper-interpreter.py --no-agent --deliver local
```

## Running Manually

```bash
# Dry-run sweep (no cache writes):
python3 ~/.hermes/scripts/cs-research-sweep.py --dry-run

# Full CS sweep:
python3 ~/.hermes/scripts/cs-research-sweep.py

# Interpret latest sweep output:
python3 ~/.hermes/scripts/cs-paper-interpreter.py

# Interpret with abstract fetching (slower, more accurate):
python3 ~/.hermes/scripts/cs-paper-interpreter.py --fetch-abstracts

# Generate primers for all CS categories:
python3 ~/.hermes/scripts/cs-primers-overnight.py

# Regenerate a single primer:
python3 ~/.hermes/scripts/cs-primers-overnight.py --category software_testing --force
```

## Handoff

These steps assume chain re-evaluation has already run for SYSTEMS-APPLICABLE and
SPIKE verdicts (see 'CS Paper Interpretation Layer / Authoritative Interpretation
Chain' section above). Do not route to findings banks without first running the chain.

- SYSTEMS-APPLICABLE: chain re-evaluation required first (see Authoritative
  Interpretation Chain section). Chain emits OPTIMIZATION/SPIKE/SKIP — it never
  emits SYSTEMS-APPLICABLE. Mapping:
    Chain OPTIMIZATION -> record in hermes-cs-sweep-findings as SYSTEMS-APPLICABLE.
    Chain SPIKE        -> record as SPIKE (chain overrides script verdict).
    Chain SKIP         -> record as SKIP with override reason.
    Chain DEFER        -> retrieve full text and re-run.
  Chain verdict always overrides script verdict; SYSTEMS-APPLICABLE label is
  only the bank's storage name, not a chain output token.
  Run adversarial-review (on the implementation plan, not a patch) before any change.
  Then -> hermes-cs-sweep-findings.
- SPIKE: chain re-evaluation required. Chain SPIKE -> log to hermes-cs-sweep-findings
  (pending) with paper ID and chain reasoning. Then: confirm with user -> run spike
  experiment (see spike skill) -> VALIDATED (spike confirms): patch via
  trajectory-research-synthesis-to-skills (adversarial-review before patch) ->
  INVALIDATED (spike disconfirms): update findings entry with reason.
  VALIDATED/INVALIDATED: see 'spike' skill for the experiment process.
- SKIP/DEFER: log to hermes-cs-sweep-findings with reason.
  DEFER (abstract-only): re-run interpreter with --fetch-abstracts, then re-run chain.
  Log DEFER with 'requeue' note, not final.
- Core agent findings (cs.AI/cs.CL/cs.MA) -> arxiv-sweep-findings
- Math/theory findings -> hermes-math-sweep-findings

## Skill Write Ownership (Class H safety)

  hermes-cs-research -> read/routing only, no skill_manage writes
  trajectory-research-synthesis-to-skills -> owns all skill_manage writes

Never call skill_manage directly from this skill.
