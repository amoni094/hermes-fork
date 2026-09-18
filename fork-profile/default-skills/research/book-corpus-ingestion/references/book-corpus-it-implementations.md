# IT/Math Book Corpus Implementations in Hermes Scripts

Produced from 9-wave book corpus study (Waves 1–9, Sep 2026). All patches are additive,
diagnostic-only or flag-gated, backward-compatible. py_compile verified on all.

## working-memory.py (9 patches)

| Patch ID | Source | Subcommand/Flag | Algorithm |
|---|---|---|---|
| GALLAGER-4 | Gallager ITRC | bigrams | P(next\|current) skill-transition table from skill-sequences.jsonl; Laplace smoothed; MI field; cold-start guard at n<10 sessions |
| COVSHA-4 | Cover-Thomas + Shannon | set-belief / get-belief / belief-chain | Belief store; parent_key provenance; hop count; conf = min(conf, parent.conf) at hops≥2; DPI flag |
| HARRISON-1 | Harrison Practical Logic | check-constraints | Parse WM constraints as key:value; detect same-key different-value contradictions; diagnostic_only |
| HARRISON-2 | Harrison Practical Logic | belief-syndrome | Scan beliefs for conf > parent.conf; emit violation_magnitude |
| CATTHY-1 | Mac Lane Category Theory | belief-limit | Lowest-conf belief (tiebreak: highest hops, then alpha key) = categorical limit |
| CATTHY-2 | Mac Lane Category Theory | belief-colimit | Token union across all belief texts = categorical colimit |
| GALLAGER-1r | Gallager (revived) | skill-entropy | H = -Σp·log2(p) over active_skills per session; low_diversity flag when H < mean_H - 2·std_H |
| COVSHA-1r | Cover-Thomas (revived) | skill-mi | MI(A;B) from skill-sequences.jsonl joint/marginal co-occurrence; synergistic/competitive flags |

## metacognitive-harness.py (12 patches)

| Patch ID | Source | Subcommand/Flag | Algorithm |
|---|---|---|---|
| GALLAGER-2 | Gallager | laplace | (s+1)/(n+2) smoothed rates |
| GALLAGER-3 | Gallager | dB evidence | 10·log10(LR) log-odds field |
| COVSHA-3 | Cover-Thomas | causal-weight | OBS/DO causal distinction flag |
| MACKAY-1 | MacKay | occam-specificity | 1/n_task_types specialist penalty |
| MACKAY-2 | MacKay | beta-variance | Beta posterior variance diagnostic |
| WALD-1 | Wald | sprt | A=(1-β)/α, B=β/(1-α) exact thresholds |
| CLRS-5 | CLRS | skill-precond | Bayes net: match + history_ok → p_consistent; noisy-OR |
| CLRS-6 | CLRS | EU (--eu flag) | E[U] deliver vs escalate; JOL as p_correct; irreversibility penalty |
| COVSHA-2 | Cover-Thomas | chernoff n_star | Min samples vs threshold; underpowered flag |
| WALD-3 | Wald | CI width | ci_width = 2·1.96·sqrt(p(1-p)/n); ci_stable when < MH_CI_EPSILON (default 0.2) |
| CATTHY-3 | Mac Lane (Yoneda) | skill-hom | Cosine sim of Laplace vectors on shared task_types; isomorphic at sim≥0.95, n≥3 |
| MACKAY-3r | MacKay (revived) | calibrate | Bin skill_profiles by Laplace_rate decile; actual vs predicted; underpowered bins flagged |

## loop-pid.py (9 patches)

| Patch ID | Source | Subcommand/Flag | Algorithm |
|---|---|---|---|
| CLRS-3 | CLRS | anti-windup | PID integral clamped at saturation |
| CLRS-4 | CLRS | span-check + upcrossings | Oscillation: upcrossings in [0.50, 0.80], n≥10 sets oscillating=True |
| CLRS-9 | CLRS | hyp-check | p90 from session history; escalation advisory |
| CATTHY-4 | LTL model checking | ltl-check | ≤3 actions per hypothesis; ESCALATE on violation |
| COVSHA-6 | Cover-Thomas | action_log | {action, hypotheses_tried, ts} on cmd_step; trim to 50 |
| CROSS-E | Cross-corpus synergy | causal-taint | Look back --horizon steps before ESCALATE; escalation_precursors list |
| CROSS-H | Flight Recorder + ltl-check | verify-chain | SHA256 hash-chain on action_log; tamper detection |
| CROSS-H2 | Flight Recorder | cmd_step hash | prev_hash = SHA256(json.dumps(prev_entry, sort_keys=True)) per entry |

## occam-skill-ranker.py (6 patches)

| Patch ID | Source | Subcommand/Flag | Algorithm |
|---|---|---|---|
| GALLAGER-5 | Gallager | TF cache | In-process MD5 cache; hits/misses counters |
| MACKAY-1 | MacKay | coverage (Occam) | coverage(q,s) = |q∩s|/|s|; specialist scores higher; --legacy-score flag |
| CLRS-10 | CLRS | dp-route | DP skill sequence planner; diagnostic_only |
| LINCOST-1 | Lin-Costello | --hamming | 1.0 - (|A|+|B|-2|A∩B|)/max(1,|vocab|); always emitted as diagnostic field |
| CATTHY-5 | Category Theory | routing-nt | Per-task-type ranker policy via ranker-policy.json; valid: occam/legacy/hamming |

## skill-graph-walk.py (4 patches)

| Patch ID | Source | Subcommand/Flag | Algorithm |
|---|---|---|---|
| CLRS-7 | CLRS | topo | 3-color DFS; cycle detection GRAY→GRAY; finish-time order |
| CLRS-8 | CLRS | capability-reach | BFS over provides from provides-taxonomy.json |
| CLRS-8b | CLRS | alt-path (or_deps) | Dijkstra over depends_on (AND) + or_deps (OR-alternative) |
| CROSS-D | Sheaf / Cat Theory | sheaf-check | Triples A→B→C: reach(A)∩reach(C) ⊆ reach(B); emit violations |

## rr_compaction_spike.py (4 patches) | constraint-binding-lint.py (1) | l1-promote.py (1 gate)

| Patch ID | Script | Description |
|---|---|---|
| SHANNON-1 | rr_compaction_spike.py | NCD-based demotion: removal delta on compressed context |
| SHANNON-2 | rr_compaction_spike.py | must-constraint veto: keyword match protects from demotion |
| GALLAGER-6 | rr_compaction_spike.py | F_n ordering invariant |
| GALLAGER-7 | rr_compaction_spike.py | Compression gate: reject if delta gain below threshold |
| CROSS-G | constraint-binding-lint.py | --subsumption: numeric constraint subsumption via operator lattice |
| CROSS-F | l1-promote.py | underpowered guard: blocks stable-tier promotion when skill_profiles total < Chernoff n_star |

## Kill Revival Thresholds

Kills based on MISSING INFRASTRUCTURE are revisable. Kills based on VOCABULARY ABUSE or WRONG MATHEMATICAL OBJECT are permanent.

Revival conditions: (a) blocking file/subcommand now exists in production, (b) implementation is additive and diagnostic-only.

## Invariant Thresholds (do not change without evidence)

| Parameter | Value | Source |
|---|---|---|
| Complementary filter α | 0.3 | WM smoothing |
| Laplace denominator | total + 2 | Gallager / MacKay |
| Occam specificity | 1/max(1, n_task_types) | MacKay |
| dB evidence | 10·log10(LR) | Gallager |
| Upcrossings band | [0.50, 0.80], n≥10 | Wald |
| CI threshold | MH_CI_EPSILON default 0.2 | Wald |
| DPI conf cap | min(conf_arg, parent.conf) at hops≥2 | Cover-Thomas |
| Hamming sim | 1 - (|A|+|B|-2|A∩B|)/max(1,|vocab|) | Lin-Costello |
| LTL action limit | 3 per hypothesis | LTL checking |
| skill-hom isomorphic | sim≥0.95, shared_types n≥3 | Mac Lane Yoneda |
| Routing-nt default | "occam" | pragmatic |
| Chernoff n_star | ceil(log(2/0.05)/(2·0.01)) | Cover-Thomas |
