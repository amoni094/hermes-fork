#!/usr/bin/env python3
"""
math-primers-overnight.py

Generates math/AI category primers for the Hermes research pipeline.
Calls Anthropic API directly (no hermes -z subprocess dependency).
Skips categories already written (>=500 bytes). Safe to re-run.

Output:
  ~/.hermes/cache/research/primers/<cat_key>.txt
  ~/.hermes/skills/research/hermes-research/references/primer-<cat_key>.txt
"""

import os, sys, time
from pathlib import Path
from dotenv import load_dotenv

# Load API key from hermes .env
load_dotenv(Path("~/.hermes/.env").expanduser(), override=False)

import anthropic

PRIMERS_DIR = Path("~/.hermes/cache/research/primers").expanduser()
SKILL_REFS_DIR = Path("~/.hermes/skills/research/hermes-research/references").expanduser()
PRIMERS_DIR.mkdir(parents=True, exist_ok=True)
SKILL_REFS_DIR.mkdir(parents=True, exist_ok=True)

HERMES_CONTEXT = """Hermes is a local multi-model AI agent on Linux. Key components:
- Per-turn tool-call loop (ReAct pattern, max_turns guard)
- Skills: procedural knowledge files loaded per task type
- Memory pipeline: l1-extract -> l1-promote -> hindsight (long-term)
- Model routing: Claude/GPT/Grok/Mistral/Mistral-Small chosen per subtask
- delegate_task: spawns parallel subagents (max 10 concurrent)
- Cron agents: ~25 scheduled jobs (research sweep, apply, monitoring)
- Context compression: summarize/prune conversation history
- Tool approval gates: security scan on terminal/file ops
- hermes-swarm-consensus: multi-model verdict aggregation
- skillopt: quality scorer for skills
- Adversarial review: cold subagent challenges proposed changes
- Token budget allocation across multi-step tasks"""

TASK_SPECS = {
    "reasoning_planning": {
        "title": "Reasoning and Planning in LLM Agents",
        "field_desc": "Chain-of-thought, tree-of-thought, MCTS planning, program synthesis, symbolic reasoning integration with LLMs",
        "key_results": "CoT scaling laws, ToT search optimality, MCTS exploration-exploitation in language space, symbolic-neural integration",
        "hermes_components": "agent loop planning, task decomposition, delegate_task subtask design, multi-step tool sequences",
    },
    "tool_use": {
        "title": "Tool Use and Function Calling in LLM Agents",
        "field_desc": "Tool selection, API calling, structured output, error recovery, tool composition, ReAct pattern",
        "key_results": "ReAct superiority over CoT-only, tool error recovery strategies, structured output grammars",
        "hermes_components": "tool call loop, tool approval gate, terminal/browser/file tools, error handling, structured output",
    },
    "memory": {
        "title": "Memory Architectures for LLM Agents",
        "field_desc": "Episodic memory, semantic memory, working memory, retrieval-augmented generation, memory consolidation, forgetting",
        "key_results": "RAG retrieval quality bounds, memory consolidation strategies, episodic vs semantic trade-offs",
        "hermes_components": "l1-extract, l1-promote, hindsight, memory-layer-gate, working memory, skill knowledge base",
    },
    "multi_agent": {
        "title": "Multi-Agent LLM Coordination",
        "field_desc": "Agent communication protocols, coordination strategies, role assignment, emergent behavior, debate and critique",
        "key_results": "Society of Mind scaling, debate improves truthfulness, role specialization benefits",
        "hermes_components": "delegate_task, hermes-swarm-consensus, adversarial-review, context packets, subagent orchestration",
    },
    "evaluation": {
        "title": "LLM Agent Evaluation and Benchmarking",
        "field_desc": "Agent benchmarks, evaluation metrics, contamination, robustness testing, automated evaluation, human preference",
        "key_results": "Benchmark saturation, LLM-as-judge reliability, contamination detection methods",
        "hermes_components": "skillopt scoring, adversarial review, verification-before-completion, research sweep triage",
    },
    "self_improvement": {
        "title": "Agent Self-Improvement and Meta-Learning",
        "field_desc": "Reflexion, self-critique, iterative refinement, prompt optimization, skill acquisition from experience",
        "key_results": "Reflexion memory improves pass@1, self-play scaling, prompt optimization convergence",
        "hermes_components": "self-improve-agent skill, skillopt, skill authoring from traces, ralph-loops, preact-trajectory",
    },
    "agentic_rag": {
        "title": "Agentic Retrieval-Augmented Generation",
        "field_desc": "Query decomposition, iterative retrieval, knowledge graph RAG, multi-hop reasoning, retrieval quality",
        "key_results": "Iterative RAG > single-shot, knowledge graph traversal improves multi-hop, retrieval confidence calibration",
        "hermes_components": "hermes-research sweep, arxiv-sweep-findings, skill retrieval, firecrawl-research, web_extract",
    },
    "group_theory": {
        "title": "Group Theory",
        "field_desc": "Groups, subgroups, homomorphisms, symmetry groups, representation theory, Cayley graphs, group actions",
        "key_results": "Lagrange theorem, first isomorphism theorem, Burnside lemma, Schur's lemma for representations",
        "hermes_components": "structured transformations in agent pipelines, symmetry in skill composition, permutation invariance in multi-agent aggregation",
    },
    "category_theory": {
        "title": "Category Theory",
        "field_desc": "Categories, functors, natural transformations, monads, adjunctions, limits/colimits, Yoneda lemma",
        "key_results": "Yoneda lemma, monad laws (unit/associativity), adjunction universality, free/forgetful functors",
        "hermes_components": "memory pipeline as functor composition, skill application as morphisms, monad structure of tool-call chains, context as a category",
    },
    "algebraic_topology": {
        "title": "Algebraic Topology / Topological Data Analysis (TDA)",
        "field_desc": "Simplicial complexes, homology groups, persistent homology, Betti numbers, Mapper algorithm, Vietoris-Rips filtration",
        "key_results": "Stability theorem for persistence diagrams, Mapper visualization, persistent homology computation complexity",
        "hermes_components": "TDA on skill embedding space to detect redundant/clustered skills, topology of session trajectory space, knowledge graph structure analysis",
    },
    "spectral_graph_theory": {
        "title": "Spectral Graph Theory",
        "field_desc": "Graph Laplacian, eigenvalues, spectral clustering, Cheeger inequality, graph signal processing, PageRank",
        "key_results": "Cheeger inequality, spectral gap and mixing time, normalized cut and spectral clustering optimality",
        "hermes_components": "skill dependency graph analysis, knowledge graph health metrics, skill clustering, citation network analysis in research sweep",
    },
    "dynamical_systems": {
        "title": "Dynamical Systems and Control Theory",
        "field_desc": "Fixed points, stability analysis, Lyapunov functions, attractors, chaos, bifurcations, PID control, LQR",
        "key_results": "Lyapunov stability theorem, LaSalle invariance, controllability/observability, Pontryagin maximum principle",
        "hermes_components": "agent loop convergence/divergence detection, context compression as a dynamical system, skill scoring stability, cron agent feedback control",
    },
    "formal_verification_agent": {
        "title": "Formal Verification for Agent Safety",
        "field_desc": "Model checking, temporal logic (LTL/CTL), theorem proving, abstract interpretation, runtime verification, safety properties",
        "key_results": "LTL model checking decidability, CEGAR refinement, abstract interpretation soundness, runtime monitor correctness",
        "hermes_components": "tool approval gate formal properties, cron agent safety guarantees, trajectory-risk-guardrail, mnemosyne-atp-safety",
    },
    "logic_semantics_agent": {
        "title": "Logic and Formal Semantics for Agents",
        "field_desc": "First-order logic, modal logic, epistemic logic, description logics, belief revision, argumentation theory",
        "key_results": "AGM belief revision postulates, description logic decidability, modal logic Kripke semantics",
        "hermes_components": "skill preconditions/postconditions, memory consistency, belief update on new facts, agent knowledge representation",
    },
    "information_geometry": {
        "title": "Information Geometry",
        "field_desc": "Statistical manifolds, Fisher information metric, natural gradient, alpha-connections, exponential/mixture families, geodesics in probability space",
        "key_results": "Natural gradient invariance, Amari-Chentsov theorem, dually flat manifolds, EM as mirror descent",
        "hermes_components": "model routing optimization using natural gradient, probability distribution geometry in uncertainty estimates, embedding space geometry for skill retrieval",
    },
    "combinatorics_approx": {
        "title": "Combinatorics and Approximation Algorithms",
        "field_desc": "Counting, graph algorithms, greedy approximations, set cover, knapsack, bin packing, FPTAS, randomized rounding",
        "key_results": "Set cover ln(n) approximation, greedy matroid optimality, FPTAS for knapsack, Lovász Local Lemma",
        "hermes_components": "context window packing (bin packing variant), token budget allocation (knapsack), skill selection (set cover), cron scheduling",
    },
    "verifiability": {
        "title": "Verifiability and Auditability in AI Systems",
        "field_desc": "Explainability, interpretability, audit trails, cryptographic verification, zero-knowledge proofs for ML, watermarking",
        "key_results": "LIME/SHAP soundness, ZK-proof for ML inference, watermarking detection bounds, audit log integrity",
        "hermes_components": "TraceGrant lifecycle.db, decision_hash integrity, tool approval audit trail, apply report evidence chain",
    },
    "singular_learning_theory": {
        "title": "Singular Learning Theory (SLT)",
        "field_desc": "Real log canonical threshold (RLCT), Watanabe's free energy formula, Bayesian information criteria for singular models, phase transitions in learning",
        "key_results": "WBIC approximates log evidence, RLCT measures model complexity for singular models, neural networks are singular statistical models",
        "hermes_components": "model complexity estimation for skill scoring, Bayesian model selection in routing, understanding phase transitions in LLM capability",
    },
    "computational_geometry": {
        "title": "Computational Geometry",
        "field_desc": "Convex hulls, Voronoi diagrams, Delaunay triangulation, range trees, nearest neighbor search, geometric algorithms",
        "key_results": "Convex hull O(n log n), Voronoi O(n log n), ANN approximation guarantees, locality-sensitive hashing",
        "hermes_components": "embedding space nearest-neighbor search for skill retrieval, geometric clustering of research papers, spatial indexing for knowledge graphs",
    },
    "lattice_order_theory": {
        "title": "Lattice Theory and Order Theory",
        "field_desc": "Partially ordered sets, lattices, Galois connections, fixed-point theorems (Tarski, Kleene), formal concept analysis",
        "key_results": "Tarski fixed-point theorem, Kleene fixed-point for least fixpoints, Galois connection adjunctions, FCA concept lattice",
        "hermes_components": "skill hierarchy/dependency ordering, memory promotion as monotone operator fixed point, concept lattice for knowledge organization",
    },
    "convex_analysis": {
        "title": "Convex Analysis and Optimization",
        "field_desc": "Convex sets/functions, subgradients, duality (Lagrangian, Fenchel), proximal operators, mirror descent, Frank-Wolfe",
        "key_results": "Strong duality (Slater condition), proximal gradient convergence, mirror descent regret bounds, Frank-Wolfe linear convergence",
        "hermes_components": "skill scoring optimization, token budget allocation as convex program, model routing cost minimization, resource-constrained scheduling",
    },
    "descriptive_complexity": {
        "title": "Descriptive Complexity and Computational Complexity",
        "field_desc": "P vs NP, circuit complexity, communication complexity, query complexity, descriptive complexity (FO/SO logics)",
        "key_results": "Fagin's theorem (NP = existential SO), Immerman-Szelepcsényi (NSPACE closed under complement), natural proofs barrier",
        "hermes_components": "limits of what agent policies can compute efficiently, skill selection complexity, communication complexity of subagent coordination",
    },
    "robust_stats": {
        "title": "Robust Statistics",
        "field_desc": "Breakdown point, influence functions, M-estimators, trimmed means, median-of-means, outlier detection, heavy-tailed distributions",
        "key_results": "Median-of-means achieves sub-Gaussian rates without sub-Gaussian assumption, Tukey median breakdown 1/3, influence function characterization",
        "hermes_components": "robust aggregation in hermes-swarm-consensus, outlier paper detection in research triage, robust skill scoring against adversarial evals",
    },
    "graph_flows_matching": {
        "title": "Graph Algorithms: Flows, Matching, and Paths",
        "field_desc": "Max-flow min-cut, bipartite matching (Hungarian, Hopcroft-Karp), shortest paths (Dijkstra, Bellman-Ford), minimum spanning trees",
        "key_results": "Max-flow min-cut theorem, perfect matching existence (Hall's theorem), Dijkstra O((V+E)log V), MST Borůvka/Prim",
        "hermes_components": "task assignment to subagents (matching), dependency resolution in skill loading (shortest path), information flow in multi-agent pipelines",
    },
    "randomized_data_structs": {
        "title": "Randomized Algorithms and Data Structures",
        "field_desc": "Bloom filters, skip lists, reservoir sampling, hashing (consistent, locality-sensitive), random projections, streaming algorithms",
        "key_results": "Bloom filter false positive rate, Johnson-Lindenstrauss lemma, reservoir sampling exactness, Count-Min sketch guarantees",
        "hermes_components": "dedup cache in research sweep (Bloom filter), LSH for skill similarity, reservoir sampling for eval subset selection, streaming paper triage",
    },
    "sparse_lowrank": {
        "title": "Sparse and Low-Rank Methods",
        "field_desc": "LASSO, compressed sensing (RIP), matrix completion, nuclear norm minimization, sparse coding, dictionary learning",
        "key_results": "RIP condition for sparse recovery, nuclear norm as convex relaxation of rank, incoherence for matrix completion",
        "hermes_components": "sparse skill activation (few skills per task), low-rank approximation of skill embedding matrices, compressed sensing for efficient knowledge retrieval",
    },
    "neural_theory": {
        "title": "Theory of Neural Networks",
        "field_desc": "Universal approximation, expressivity, depth separation, overparameterization (NTK, mean-field), loss landscape, double descent",
        "key_results": "Universal approximation theorem, NTK kernel convergence, double descent risk curve, lottery ticket hypothesis",
        "hermes_components": "understanding LLM capability scaling, fine-tuning theory for task adaptation, overparameterization insights for model routing decisions",
    },
    "geometric_dl": {
        "title": "Geometric Deep Learning",
        "field_desc": "Graph neural networks (message passing, expressivity), equivariance, symmetry groups in DL, Weisfeiler-Leman hierarchy",
        "key_results": "WL test and GNN expressivity limits, equivariant network universality, geometric priors improve sample efficiency",
        "hermes_components": "GNN over skill dependency graph, equivariant representations for structured tool outputs, knowledge graph embeddings",
    },
    "llm_emergence_theory": {
        "title": "Emergence and Scaling in LLMs",
        "field_desc": "Scaling laws (Chinchilla, Kaplan), emergent capabilities, in-context learning theory, chain-of-thought emergence, grokking",
        "key_results": "Chinchilla optimal compute allocation, emergent capabilities at scale thresholds, ICL as implicit Bayesian inference",
        "hermes_components": "model selection for routing (which model has which capabilities), scaling budget decisions, understanding when to escalate to stronger models",
    },
    "rlhf_theory": {
        "title": "RLHF and Alignment Theory",
        "field_desc": "Reward modeling, preference learning, PPO for LLMs, DPO (Direct Preference Optimization), constitutional AI, reward hacking",
        "key_results": "DPO equivalence to reward model + RL, reward hacking under distributional shift, KL-constrained RL optimality",
        "hermes_components": "user correction as preference signal, skillopt scoring as implicit reward, adversarial review as constitutional AI analog",
    },
    "agent_adaptation_theory": {
        "title": "Agent Adaptation: Meta-Learning, Continual Learning, Curriculum",
        "field_desc": "MAML, Reptile, few-shot learning, catastrophic forgetting, EWC, progressive neural networks, curriculum learning theory",
        "key_results": "MAML convergence, EWC quadratic penalty prevents forgetting, curriculum learning improves sample efficiency",
        "hermes_components": "skill generalization across task types, memory pipeline preventing catastrophic forgetting, curriculum for cron agent training",
    },
    "representation_interp": {
        "title": "Representation Learning and Interpretability",
        "field_desc": "Disentanglement, probing classifiers, mechanistic interpretability, circuits, superposition hypothesis, feature visualization",
        "key_results": "Superposition theorem, linear representation hypothesis, probing accuracy as representation quality, circuit faithfulness",
        "hermes_components": "skill embedding quality, interpretability of routing decisions, understanding what model features drive tool selection",
    },
    "eval_uncertainty_fairness": {
        "title": "Evaluation, Uncertainty, and Fairness in ML",
        "field_desc": "Calibration, proper scoring rules, conformal prediction, fairness metrics (demographic parity, equalized odds), dataset shift",
        "key_results": "Brier score propriety, temperature scaling calibration, demographic parity impossibility under unequal base rates",
        "hermes_components": "skill eval calibration, confidence thresholds in verification gates, fair model routing across providers, dataset shift in research sweep",
    },
    "moe_theory": {
        "title": "Mixture of Experts Theory",
        "field_desc": "Sparse gating, load balancing, expert routing, capacity factor, EM for MoE, conditional computation",
        "key_results": "Load balancing loss necessity, top-k routing approximation, MoE scaling laws, expert specialization emergence",
        "hermes_components": "model routing as sparse MoE (each LLM is an expert), skill selection as expert routing, load balancing across API providers",
    },
    "federated_learning_theory": {
        "title": "Federated and Distributed Learning Theory",
        "field_desc": "FedAvg convergence, communication rounds, data heterogeneity (non-iid), differential privacy, secure aggregation",
        "key_results": "FedAvg convergence under non-iid data, communication-computation tradeoff, DP-SGD privacy accounting",
        "hermes_components": "distributed skill updates across sessions, privacy-preserving memory consolidation, multi-device Hermes synchronization",
    },
    "diffusion_processes": {
        "title": "Diffusion Processes and Score-Based Models",
        "field_desc": "Stochastic differential equations (SDEs), score matching, denoising diffusion, Langevin dynamics, Fokker-Planck equation",
        "key_results": "Anderson's time-reversal of diffusion, score matching equivalence to denoising, DDPM convergence",
        "hermes_components": "sampling from skill distributions, Langevin MCMC for memory consolidation sampling, diffusion-based data augmentation for eval",
    },
    "monte_carlo_methods": {
        "title": "Monte Carlo Methods and Sampling",
        "field_desc": "MCMC (Metropolis-Hastings, HMC), importance sampling, sequential Monte Carlo, variational inference, ELBO",
        "key_results": "Metropolis-Hastings detailed balance, HMC acceptance rate, IS variance reduction, ELBO as lower bound on log evidence",
        "hermes_components": "belief estimation via sampling in agent uncertainty, memory consolidation via MCMC, variational approximation for Bayesian skill scoring",
    },
    "numerical_optimization": {
        "title": "Numerical Optimization",
        "field_desc": "Gradient descent variants (SGD, Adam, AdaGrad), second-order methods (Newton, L-BFGS), line search, convergence rates",
        "key_results": "SGD O(1/sqrt(T)) convergence, Adam adaptive learning rates, Newton quadratic convergence near optimum",
        "hermes_components": "skillopt score optimization, fine-tuning convergence, prompt optimization (discrete optimization), hyperparameter tuning for cron agents",
    },
    "fourier_harmonic": {
        "title": "Fourier Analysis and Harmonic Analysis",
        "field_desc": "DFT, FFT, convolution theorem, wavelets, Fourier analysis on groups, uncertainty principle, spectral methods",
        "key_results": "Convolution theorem, Parseval's theorem, wavelet multiresolution analysis, group Fourier transform",
        "hermes_components": "time-series analysis of agent performance metrics, spectral analysis of cron job patterns, frequency-domain analysis of token usage",
    },
    "time_series_analysis": {
        "title": "Time Series Analysis and Forecasting",
        "field_desc": "ARIMA, state space models, Kalman filter, change point detection, spectral density, Granger causality, online forecasting",
        "key_results": "Kalman filter optimality (linear Gaussian), CUSUM change detection, Granger causality F-test, online forecasting regret bounds",
        "hermes_components": "cron job performance trending, research paper citation growth forecasting, agent failure rate change detection, token cost monitoring",
    },
    "mean_field_large_dev": {
        "title": "Mean Field Theory and Large Deviations",
        "field_desc": "Mean field approximation, variational free energy, large deviation principle (Cramér, Sanov), rate functions, Gibbs measures",
        "key_results": "Cramér's theorem, Sanov's theorem for empirical distributions, mean field variational Bayes, Gibbs variational principle",
        "hermes_components": "large-fleet agent failure rate estimation, mean-field approximation for multi-agent behavior, rare event analysis for cron safety",
    },
    "quantum_computing": {
        "title": "Quantum Computing and Quantum Information",
        "field_desc": "Qubits, quantum gates, quantum circuits, Grover's algorithm, Shor's algorithm, quantum error correction, variational quantum algorithms",
        "key_results": "Grover O(sqrt(N)) search, Shor polynomial factoring, quantum error correction threshold theorem, QAOA approximation",
        "hermes_components": "quantum-inspired sampling algorithms (not actual quantum hardware), future-proofing cryptographic assumptions, quantum ML algorithms for embeddings",
    },
    "random_graphs": {
        "title": "Random Graphs and Network Theory",
        "field_desc": "Erdős–Rényi model, configuration model, phase transitions, giant component, percolation, preferential attachment, small world",
        "key_results": "Giant component threshold p=1/n, small-world Watts-Strogatz model, preferential attachment power law, percolation critical exponents",
        "hermes_components": "knowledge graph robustness analysis, skill library growth as preferential attachment, research citation network structure, agent communication network topology",
    },
}

PRIMER_PROMPT_TEMPLATE = """Write a dense, practically-focused primer on {title} for an AI agent engineer.

The primer is for someone building and optimizing a multi-model AI agent system called Hermes with these components:
{hermes_context}

Structure your primer as follows:

1. FIELD OVERVIEW (~150 words)
   What this field is about. Core objects of study. Why it matters mathematically.
   Field: {field_desc}

2. KEY RESULTS (~200 words)
   The most important theorems, bounds, and algorithms. State them precisely enough to use.
   Key results to cover: {key_results}

3. STANDARD PRACTITIONER TOOLS (~100 words)
   What engineers actually compute/implement from this field. Libraries, algorithms, formulas.

4. HERMES APPLICATIONS — this is the most important part (~400-600 words)
   For each of these Hermes components: {hermes_components}
   
   For EACH component write:
   (a) What is the mathematical structure from {title} that applies here?
   (b) What does Hermes currently do (heuristic/naive approach)?
   (c) What would a principled approach from {title} do differently — be concrete, give the formula or algorithm name?
   (d) Honest value assessment: is it worth implementing? What would it take? What's the risk of the math not transferring?

5. SPIKE CANDIDATES (~100 words)
   List 1-3 concrete experiments you could run in a weekend to test whether {title} ideas improve Hermes.
   Each spike: name, hypothesis, how to measure success/failure in one sentence.

Output format: plain text only (no markdown, no asterisks, no headers with #).
Start the VERY FIRST LINE with exactly: PRIMER: {title}
Total length: 900-1400 words.
Be honest. If the math does not transfer, say so clearly rather than inventing connections."""


def build_prompt(cat_key: str, spec: dict) -> str:
    return PRIMER_PROMPT_TEMPLATE.format(
        title=spec["title"],
        field_desc=spec["field_desc"],
        key_results=spec["key_results"],
        hermes_components=spec["hermes_components"],
        hermes_context=HERMES_CONTEXT,
    )


def run_primer(cat_key: str, spec: dict, client: anthropic.Anthropic) -> bool:
    out_path = PRIMERS_DIR / f"{cat_key}.txt"
    if out_path.exists() and out_path.stat().st_size >= 500:
        print(f"  SKIP {cat_key} (already exists, {out_path.stat().st_size} bytes)")
        return True

    print(f"  RUNNING {cat_key}...")
    prompt = build_prompt(cat_key, spec)

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        from anthropic.types import TextBlock
        block = msg.content[0]
        text = (block.text if isinstance(block, TextBlock) else str(block)).strip()

        if not text.startswith("PRIMER:"):
            # Prepend if model forgot
            text = f"PRIMER: {spec['title']}\n\n{text}"

        out_path.write_text(text)
        ref_path = SKILL_REFS_DIR / f"primer-{cat_key}.txt"
        ref_path.write_text(text)
        print(f"  OK {cat_key}: {len(text)} chars -> {out_path}")
        print(f"  -> Saved skill ref: primer-{cat_key}.txt")
        return True

    except Exception as e:
        print(f"  ERROR {cat_key}: {e}")
        return False


def main():
    print("Math Primers Overnight Run")
    print(f"Output dir: {PRIMERS_DIR}")
    print(f"Skill refs: {SKILL_REFS_DIR}")
    print(f"Total categories: {len(TASK_SPECS)}")
    print()

    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from env

    ok = 0
    fail = 0
    skip = 0
    for i, (cat_key, spec) in enumerate(TASK_SPECS.items(), 1):
        print(f"[{i}/{len(TASK_SPECS)}] {cat_key}")
        out_path = PRIMERS_DIR / f"{cat_key}.txt"
        if out_path.exists() and out_path.stat().st_size >= 500:
            print(f"  SKIP {cat_key} ({out_path.stat().st_size} bytes)")
            skip += 1
            continue

        success = run_primer(cat_key, spec, client)
        if success:
            ok += 1
        else:
            fail += 1
        # Small pause to avoid rate limits
        time.sleep(1)

    print()
    print(f"Done: {ok} written, {skip} skipped, {fail} failed")
    total = len(list(PRIMERS_DIR.glob("*.txt")))
    print(f"Total primers on disk: {total}")


if __name__ == "__main__":
    main()
