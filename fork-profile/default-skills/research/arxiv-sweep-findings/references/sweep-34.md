# Sweep 34 — 2026-09-10

Boundary: 2609.09150 (sweep-33 high) -> 2609.08832 (highest new ID)
Math corpus sweep: 18 IDs, 2 CHAIN-partial, 4 abstract-CHAIN / full-chain SKIP, N REVIEW, 8 SKIP

Abstracts fetched 2026-09-11 from `https://arxiv.org/abs/{ID}`. Full-chain verdicts already in `hermes-math-sweep-findings` (2026-09-10, full text). Abstract triage CHAIN does **not** override full-chain SKIP.

## Abstract-triage CHAIN candidates (full-chain result: SKIP for 4, PARTIAL for 2)

### arXiv:2609.08832
Title: Closing the Consistency Gap: Self-Evolving Agents That Learn to Stay on Course
Applicability: Abstract maps to episodic memory from unstable ReAct steps (Consistency Analyzer + Guideline Generator; +16pp all-five-runs on AppWorld). Full text is a FRAMEWORK (N=30 resample, SBERT/Jaccard, Fang 2026 dual-index memory). No named Hermes log field for pass^k; "write tips from traces" already implicit in memory write. Not a runtime/config edit.
Target: `agent-memory-consolidation` (would-be); do not implement
Action: Do not add a consistency-analyzer loop. Revisit only if Hermes logs per-task pass^k and a <50 LOC guideline injector exists.
Feasibility: SPIKE_FIRST
Status: PENDING (full-chain SKIP at Step 1 FRAMEWORK)
(kept in CHAIN section: has partial Hermes analogue)

### arXiv:2609.04059
Title: Batched Pandora's Box
Applicability: Abstract: batched Weitzman / Pandora for parallelizable stochastic search (LLM inference-time scaling). Maps to `delegate_task` batch size vs setup cost. Full-chain: ALGORITHM, Step 3 pass, formula SPIKE, Step 6 critic DOWNGRADE → SKIP (needs finite-support (v,p) rewards and scalar costs; Hermes returns unbounded strings, no V_i). Formal α_NR / α_R do not transfer. Heuristic remainder ("batch parallel search until good enough") already covered by `delegation.max_concurrent_children=10`.
Target: `hermes-cron-and-agents` + `dispatching-parallel-agents`
Action: Spike already run (`~/.hermes/cache/research/spikes/005-pandoras-box-query-batching`, verdict PARTIAL). Specified q=0 instance beat greedy ≥5%; Hermes-calibrated q=0.04 missed the bar; k*=2 not 3 when per-delegate cost is real. **Done:** reservation-table experiment. **Remaining:** do not ship a new fixed k; add a skill rule only after measuring live T/q (round-setup vs per-delegate token cost), then `k*` from batch-reservation σ(B_k). Variance-calibrated k is **not** in skills.
Feasibility: SPIKE_FIRST (spike PARTIAL; production rule still blocked on live T/q)
Status: PARTIAL
(kept in CHAIN section: has partial Hermes analogue)

## REVIEW (read list)

Boundary log named **4 REVIEW** IDs but did not persist them (only the 6 CHAIN IDs were enumerated). Not recovered from `references/` or math-interpreter cache. Do not invent IDs.

Informative-but-not-actionable from this CHAIN-6 (full-chain SKIP, still worth a read if designing related systems):

- 2609.08832 — consistency-gap / episodic guidelines (memory-write intuition already present)
- 2609.03161 — NL→LTL_f automata refinement (no Hermes DFA stack)

## SKIP

### arXiv:2609.07787
Title: The Price of Feasibility: Greedy Approximation Bounds for String Supermodular Optimization over Oracle-Conditioned Greedoids
Applicability: Theorem on monotone supermodular minimization over graphic-greedoid bases with a physics look-ahead oracle (FORWARD / radial network reconfiguration). No greedoid, physics oracle, or feeder objective in Hermes. Bound does not tighten a named PARAM_DEFAULT.
Target: none
Action: Do not implement. Companion Algorithm 1 is the analysis vehicle, not a Hermes procedure.
Feasibility: SPIKE_FIRST
Status: PENDING (full-chain SKIP at Step 1 THEOREM)

### arXiv:2609.03161
Title: NeuroSTAR: Automata-guided Neuro-symbolic Specification Formalization
Applicability: NL→LTL_f via diverse generators + DFA difference traces. No LTL_f / AP library / Spot-class DFA toolchain in Hermes. Task-brief abstract (token-constrained decoding) did **not** match full text (post-hoc DFA differencing + textual feedback).
Target: none (not `isa` / TLA+ contracts)
Action: Do not implement. Formal-spec interest is already covered at heuristic level by `isa` / `formal_specification` mapping.
Feasibility: SPIKE_FIRST
Status: PENDING (full-chain SKIP at Step 1 FRAMEWORK)

### arXiv:2609.01963
Title: Aggregating Neighbor Embedding Projection and Rank-Based Manifold Learning for Image Retrieval
Applicability: UMAP + rank-based re-rank + Borda on CNN/Swin/DINOv2 **image** features for CBIR. Hermes retrieval is query-time kNN over text traces (Hindsight/Graphiti/session_search), not all-pairs visual manifold. fea=0 (UMAP+BallTree+all-pairs is new infra). Borda alone is 1781, not this paper's contribution.
Target: none
Action: Do not implement. Do not reuse Borda as a pretext to import UMAP.
Feasibility: SPIKE_FIRST
Status: PENDING (full-chain SKIP, des=1 fea=0)

### arXiv:2604.16416
Title: Tensor Manifold-Based Graph-Vector Fusion for AI-Native Academic Literature Retrieval
Applicability: Tensor-manifold unification of literature graph topology + vector embedding; four modules (temporal diffusion signature, hierarchical temporal encoding, Riemannian index, programmable retrieval). Graphiti is not a Riemannian literature index. Task-brief abstract (dual-stream encoder / hierarchical cross-attention) did **not** match full text. New modules >>50 LOC.
Target: none (not Graphiti)
Action: Do not implement. Linear-complexity claims do not map onto existing KG APIs.
Feasibility: SPIKE_FIRST
Status: PENDING (full-chain SKIP at Step 1 FRAMEWORK)

Post-chain SKIP of the CHAIN-6 (do not re-evaluate unless full text or Hermes runtime changes):

- 2609.08832 — FRAMEWORK / Step 1
- 2609.04059 — SPIKE formula then Step 6 critic DOWNGRADE (reward distributions missing); spike PARTIAL only
- 2609.07787 — THEOREM / Step 1 (greedoid + physics oracle)
- 2609.03161 — FRAMEWORK / Step 1 (LTL_f / DFA toolchain)
- 2609.01963 — ALGORITHM, fea=0 (image CBIR infra)
- 2604.16416 — FRAMEWORK / Step 1 (Riemannian literature index)

Same-day adjacent chain SKIP (not in the CHAIN-6, listed so it is not re-queued as sweep-34 REVIEW):

- 2609.03685 — PTAS for non-adaptive stochastic top-k sum

Original **8 SKIP** IDs from abstract triage: **not persisted** in the boundary log.

## Defer matrix

| Item | Benefit | Partial coverage | Cost/risk | Revisit trigger |
|---|---|---|---|---|
| 2609.04059 variance-calibrated k | Better delegate batch net vs fixed k=3 | Spike 005 PARTIAL; `max_concurrent_children=10` | Shipping k without live T/q repeats the q=0 degeneracy (k*=n) | Measure round-setup T vs per-delegate token cost q; unequal delegate variance |
| 2609.08832 consistency guidelines | Raise pass^k on repeated tasks | Memory write / Graphiti episodes | New resampler + SBERT + dual index >>50 LOC | Hermes logs per-task pass^k and a <50 LOC injector exists |
| 2609.07787 CSGA / price of feasibility | None in current object taxonomy | none | Greedoid + physics oracle | Hermes grows a constrained combinatorial selector with a look-ahead feasibility oracle |
| 2609.03161 NeuroSTAR | Spec formalization | `isa` / formal_specification mapping | Spot/Syft DFA toolchain | Agent loop needs LTL_f contracts with a DFA checker already in-tree |
| 2609.01963 UMAP+Borda retrieval | None (wrong object: images) | Hindsight/Graphiti/session_search | New visual manifold infra | Retrieval corpus becomes a closed image set |
| 2604.16416 tensor-manifold IR | None (wrong index geometry) | Graphiti | Riemannian index + DEC/Hodge modules | Literature-graph product with a real Riemannian index requirement |
| 4 REVIEW + 8 SKIP IDs (unnamed) | Catalog completeness | CHAIN-6 evaluated | Guessing IDs pollutes the bank | Recover from the 2026-09-10 math-sweep session transcript |
