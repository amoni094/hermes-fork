#!/usr/bin/env python3
"""
hermes-research-sweep.py

Multi-source, multilingual academic research sweep across 51 canonical
AI-agent improvement categories identified from citation analysis (Sep 2026):

CORE AGENT CATEGORIES (1-7)
  1. Reasoning + Planning
  2. Tool Use / Function Calling
  3. Memory Architecture
  4. Multi-Agent Systems / Collaboration
  5. Agent Evaluation / Benchmarking
  6. Agent Evolution / Self-Improvement
  7. Agentic RAG / Context Management

CLASSICAL MATHEMATICS (8-26)
  8. Group Theory / Applied Algebra
  9. Category Theory / Applied CT
 10. Information Theory / Rate-Distortion
 11. Algebraic Topology / TDA
 12. Stochastic Processes / MDP
 13. Game Theory / Mechanism Design
 14. Spectral Graph Theory
 15. Online Learning / Regret Minimisation
 16. Dynamical Systems / Fixed-Point Theory
 17. Formal Logic / Proof Theory / Type Theory
 18. Information Geometry / Embedding Space Curvature
 19. Combinatorics / Approximation Theory for Context Compression
 20. Concentration Inequalities / PAC Learning
 21. ZK-Proofs / Verifiable Computation
 22. Singular Learning Theory / Algebraic Geometry
 23. Formal Language Theory / Automata
 24. Queuing Theory
 25. Computational Geometry
 26. Lattice Theory / Order Theory
 27. Convex Analysis
 28. Descriptive Complexity / Circuit Complexity
 29. Kolmogorov Complexity / Algorithmic Information Theory
 30. Robust Statistics
 31. Coding Theory / ECC
 32. Classical Graph Theory (Flows / Matching)

EXTENDED MATHEMATICS (33-49)
 33. Causal Inference
 34. Statistical Learning Theory (VC / Rademacher)
 35. Randomized Algorithms / Probabilistic Methods
 36. Streaming Algorithms
 37. Formal Methods / Model Checking
 38. Temporal Logic / Modal Logic
 39. Description Logics (OWL/DL)
 40. Homotopy Type Theory
 41. Random Matrix Theory
 42. Communication Complexity
 43. Interactive Proofs
 44. Mean Field Theory / Statistical Mechanics
 45. Proof Complexity
 46. Empirical Process Theory
 47. Persistent / Amortized Data Structures
 48. Diffusion Processes / SDEs
 49. Distributed Computing Theory
 50. Domain Theory
 51. Large Deviations Theory
 52. Monte Carlo Methods / MCMC
 53. Neural Networks Mathematical Theory
 54. Numerical Optimization Theory
 55. Scheduling Theory
 56. Computability / Recursion Theory
 57. Lie Groups / Equivariant Neural Networks
 58. Time Series Analysis
 59. Bifurcation Theory
 60. Fourier / Harmonic Analysis
 61. Morse Theory / Loss Landscape Topology
 62. Nonparametric Statistics
 63. Quantum Computing / Quantum Information
 64. Random Graphs
 65. Social Choice Theory
 66. Algorithmic Game Theory
 67. Reinforcement Learning Theory
 68. Optimal Transport Theory
 69. Neural Tangent Kernel Theory
 70. PAC-Bayes Theory
 71. Geometric Deep Learning
 72. Compressed Sensing / Sparse Recovery
 73. Matrix Completion / Low-Rank Recovery
 74. Tensor Decompositions / Multilinear Algebra
 75. In-Context Learning Theory
 76. Chain-of-Thought Theory
 77. Emergent Capabilities Theory
 78. Scaling Laws Theory
 79. Attention Mechanism Theory
 80. RLHF Theory
 81. Continual Learning Theory
 82. Meta-Learning Theory
 83. Representation Learning Theory
 84. Uncertainty Quantification / Conformal Prediction
 85. Active Learning Theory
 86. Safe RL / Constrained MDP Theory
 87. Information-Theoretic Learning Theory (IB)
 88. Algorithmic Fairness
 89. Mechanistic Interpretability Mathematics
 90. Mixture of Experts Theory
 91. Federated Learning Theory
 92. Reward Shaping Theory
 93. Multi-Task Learning Theory
 94. Curriculum Learning Theory
 95. Imitation Learning Theory
 96. Hierarchical RL Theory
 97. Inverse RL Theory
 98. Model-Based RL Theory

Sources (multilingual):
  - arXiv (cs.AI, cs.CL, cs.MA, cs.LG) — via web search + HTML search UI
  - Semantic Scholar (S2) API — citation-ranked recent papers
  - Papers With Code — trending leaderboards
  - Hugging Face Papers — community-voted recent releases
  - OpenAlex — open scholarly metadata
  - HAL (French/EU source)
  - CNKI proxy via arXiv (Chinese institution author search)
  - AMiner (Chinese AI/CS graph)
  - J-STAGE (Japanese)
  - CyberLeninka (Russian/Eastern European OA)

Output:
  ~/.hermes/cache/research/hermes-research-latest.json
  ~/.hermes/cache/research/hermes-research-YYYY-MM-DD.json
  Prints a plain-text digest to stdout if new papers found (cron delivery).
  Prints nothing if no new papers above threshold (silent cron tick).

Cache:
  ~/.hermes/cache/research/seen_papers.json  (rolling SHA256 of arXiv IDs)

Usage:
  python3 ~/.hermes/scripts/hermes-research-sweep.py [--dry-run] [--force]
  # As a cron script (no_agent=True for data collection phase)
"""

import json
import os
import sys
import hashlib
import html
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET


def _simhash(text, bits=64):
    """64-bit SimHash for near-duplicate detection. Source: randomized_data_structs primer."""
    tokens = re.sub(r'[^a-z0-9 ]', '', text.lower()).split()
    v = [0] * bits
    for tok in tokens:
        import hashlib as _hl
        h = int(_hl.md5(tok.encode()).hexdigest(), 16)
        for i in range(bits):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(bits) if v[i] > 0)


def _hamming(a, b):
    x = a ^ b
    c = 0
    while x:
        c += x & 1
        x >>= 1
    return c


_SIMHASH_SEEN = {}
SIMHASH_THRESHOLD = 3


def is_near_duplicate(title, abstract):
    """Return True if near-duplicate of a paper already seen this run."""
    text = (title + ' ' + abstract)[:500]
    h = _simhash(text)
    for seen_h in _SIMHASH_SEEN:
        if _hamming(h, seen_h) <= SIMHASH_THRESHOLD:
            return True
    _SIMHASH_SEEN[h] = title[:80]
    return False

# ── Paths ─────────────────────────────────────────────────────────────────
CACHE_DIR = Path.home() / ".hermes" / "cache" / "research"
SEEN_FILE = CACHE_DIR / "seen_papers.json"
OUTPUT_LATEST = CACHE_DIR / "hermes-research-latest.json"
OUTPUT_DATED = CACHE_DIR / f"hermes-research-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
MAX_SEEN = 2000   # rolling window

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

# ── Off-topic pre-filter ───────────────────────────────────────────────────
# Applied to title+source before adding to seen cache or output.
# Drops papers that are clearly outside CS/AI/math — medical, biology,
# climate, cosmology, social-science noise that bleeds in via broad arXiv cats.
# Keep: anything with no title (id-only entries from listing), short titles.
_OFFTOPIC_PATTERNS = re.compile(
    r'\b('
    # Medical / biology
    r'cancer|tumor|tumour|carcinoma|oncol|metastas|biopsy|genomic|genome|'
    r'protein|amino.acid|peptide|enzyme|RNA|DNA|CRISPR|molecular.biology|'
    r'medical.imaging|radiology|patholog|clinical.trial|patient|'
    r'drug.discovery|pharmaceutical|biomedical|therapeut|surgery|surgical|'
    r'hydrogel|biomaterial|tissue.engineering|wound.healing|'
    r'wearable.sensor|biosensor|microfluidic|organ.on.a.chip|'
    # Climate / earth science
    r'climate.change|carbon.emission|greenhouse|precipitation|hydrol|'
    r'seismic|earthquake|geolog|mineral|reservoir|petroleum|'
    r'renewable.energy|wind.farm|solar.panel|photovoltaic|'
    r'smart.grid|power.grid|energy.storage|battery.material|'
    # Cosmology / physics
    r'cosmolog|galaxy|stellar|black.hole|exoplanet|asteroid|'
    r'quantum.chemistry|force.field|molecular.dynamics|electrocatal|'
    # Medical / psychiatric
    r'psychiatric|schizophren|dementia|alzheimer|epilep|neurolog|'
    r'autism.spectrum|cognitive.load|educational.neuroscience|'
    # Social science
    r'sociology|anthropolog|political.science|ethnograph|archaeolog|'
    r'sustainability.report|greenwashing|ESG|'
    # Infectious disease
    r'COVID|SARS|influenza|pandemic|epidemiol|vaccine|antimicrobial|'
    # Materials science
    r'hydrogel|electrolyte|solid.state|nanorobot|gasification|'
    r'materials.discovery|catalyst.material|alloy|crystallin|'
    # Agriculture / food
    r'precision.farming|crop|livestock|food.safety|nutrition.omics|'
    # Finance noise
    r'financial.fraud|stock.market.prediction|crypto.price|'
    r'valvular.heart|autism.prevalence'
    r')\b',
    re.IGNORECASE,
)

def is_offtopic(paper: dict) -> bool:
    title = paper.get("title", "")
    if not title or title.startswith("[arXiv:"):
        return False  # id-only entries: keep, triage later
    if len(title) < 20:
        return False  # very short titles: keep safe
    return bool(_OFFTOPIC_PATTERNS.search(title))

# Search-chrome titles (arXiv HTML search page) are not papers.
# Index-pairing IDs with page-level title regexes mislabels real papers.
_JUNK_TITLE_RE = re.compile(
    r'(Showing\s+\d|results for all:|Search v\d|&nbsp;|Released \d{4})',
    re.I,
)

def clean_arxiv_title(title: str) -> str:
    """Strip HTML and drop search-chrome blobs that are not paper titles."""
    title = re.sub(r'<[^>]+>', '', title or '')
    title = html.unescape(title)
    title = re.sub(r'\s+', ' ', title).strip()
    if not title or _JUNK_TITLE_RE.search(title):
        return ""
    if len(title) > 300:
        return ""  # concatenated page blob, not a title
    return title

def _unique_arxiv_ids(ids_found: list[str]) -> list[str]:
    unique = []
    seen = set()
    for arxiv_id in ids_found:
        if not arxiv_id_valid(arxiv_id) or arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        unique.append(arxiv_id)
    return unique

# ── Research categories and search terms ──────────────────────────────────
CATEGORIES = {
    "reasoning_planning": {
        "label": "Reasoning + Planning",
        "queries": [
            "LLM agent reasoning planning chain of thought 2026",
            "language model planning task decomposition 2026",
            "tree of thoughts Monte Carlo LLM 2025 2026",
            "process reward model step verification LLM agent",
            "test-time compute scaling reasoning agent 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.CL", "cs.LG"],
    },
    "tool_use": {
        "label": "Tool Use / Function Calling",
        "queries": [
            "LLM tool use function calling agent 2026",
            "language model API tool learning 2026",
            "model context protocol MCP agent tool 2026",
            "tool creation agent CREATOR self-generated 2026",
            "multi-tool composition error recovery agent 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.CL"],
    },
    "memory": {
        "label": "Memory Architecture",
        "queries": [
            "LLM agent memory architecture episodic semantic 2026",
            "agent memory consolidation retrieval augmented 2026",
            "MemGPT long-term memory agent 2025 2026",
            "agent memory compression eviction strategy 2026",
            "self-evolving memory knowledge graph agent 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.CL", "cs.IR"],
    },
    "multi_agent": {
        "label": "Multi-Agent Systems / Collaboration",
        "queries": [
            "multi-agent LLM collaboration 2026",
            "multi-agent debate consensus reasoning 2026",
            "LLM agent orchestration workflow 2026",
            "agent communication protocol emergence 2026",
            "multiagent finetuning self-improvement 2026",
        ],
        "arxiv_cats": ["cs.MA", "cs.AI", "cs.CL"],
    },
    "evaluation": {
        "label": "Agent Evaluation / Benchmarking",
        "queries": [
            "LLM agent benchmark evaluation 2026",
            "agent trajectory evaluation process reward 2026",
            "LLM judge evaluation metric agent 2026",
            "SWE-bench WebArena OSWorld agent evaluation 2026",
            "agent evaluation alignment safety benchmark 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.CL", "cs.SE"],
    },
    "self_improvement": {
        "label": "Agent Evolution / Self-Improvement",
        "queries": [
            "LLM agent self-improvement fine-tuning 2026",
            "agent skill learning from experience trajectory 2026",
            "autonomous agent evolution curriculum 2026",
            "reinforcement learning LLM agent policy improvement 2026",
            "agent self-reflection verbal reinforcement 2025 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.LG", "cs.CL"],
    },
    "agentic_rag": {
        "label": "Agentic RAG / Context Management",
        "queries": [
            "agentic RAG retrieval augmented generation agent 2026",
            "long context management compression agent 2026",
            "knowledge graph retrieval agent 2026",
            "adaptive retrieval agent orchestration 2026",
            "context window management agent memory 2026",
        ],
        "arxiv_cats": ["cs.IR", "cs.AI", "cs.CL"],
    },
    "group_theory": {
        "label": "Group Theory / Applied Algebra",
        "queries": [
            "group theory knowledge graph topology 2025 2026",
            "Cayley graph neural network GNN 2025 2026",
            "groupoid memory consistency temporal reasoning 2025 2026",
            "representation theory graph embedding agent 2025 2026",
            "cohomology obstruction knowledge base consistency 2025 2026",
        ],
        "arxiv_cats": ["math.GR", "math.AT", "cs.DM"],
    },
    "category_theory": {
        "label": "Category Theory / Applied CT",
        "queries": [
            "applied category theory knowledge representation 2025 2026",
            "functor adjunction memory retrieval agent 2025 2026",
            "topos theory language model reasoning 2025 2026",
            "sheaf neural network knowledge graph 2025 2026",
            "monad comonad compositional AI agent 2025 2026",
        ],
        "arxiv_cats": ["math.CT", "cs.LO", "cs.PL"],
    },
    "information_theory": {
        "label": "Information Theory / Rate-Distortion / Kolmogorov Complexity / IB",
        "queries": [
            "rate distortion memory compaction LLM agent 2025 2026",
            "Kolmogorov complexity incompressibility agent memory compression 2025 2026",
            "information bottleneck Tishby representation LLM 2025 2026",
            "minimum description length knowledge compression agent 2025 2026",
            "mutual information retrieval knowledge graph agent 2025 2026",
        ],
        "arxiv_cats": ["cs.IT", "cs.LG", "cs.AI"],
    },
    "algebraic_topology": {
        "label": "Algebraic Topology / TDA for Knowledge Graphs",
        "queries": [
            "persistent homology knowledge graph agent memory 2025 2026",
            "topological data analysis TDA LLM embedding clustering 2025 2026",
            "mapper algorithm skill embedding topological summary 2025 2026",
            "Betti number graph health diagnostic agent 2025 2026",
            "simplicial complex nerve agent memory layer 2025 2026",
        ],
        "arxiv_cats": ["math.AT", "cs.CG", "cs.LG"],
    },
    "stochastic_causal": {
        "label": "Probability / Stochastic Processes / Causal Inference for Agent Runtime",
        "queries": [
            "Markov decision process retrieval routing agent 2025 2026",
            "causal inference do-calculus LLM agent planning world model 2025 2026",
            "Bayesian network causal memory agent knowledge graph 2025 2026",
            "martingale stopping termination agent loop 2025 2026",
            "counterfactual reasoning agent planning intervention 2025 2026",
        ],
        "arxiv_cats": ["cs.AI", "math.PR", "cs.LG", "stat.ME"],
    },
    "game_theory": {
        "label": "Game Theory / Mechanism Design / Social Choice for Multi-Agent Systems",
        "queries": [
            "Shapley value credit assignment agent memory retrieval 2025 2026",
            "price of anarchy multi-agent LLM coordination 2025 2026",
            "Arrow impossibility theorem multi-agent consensus LLM 2025 2026",
            "stable matching query skill routing agent 2025 2026",
            "online auction agent resource allocation 2025 2026",
        ],
        "arxiv_cats": ["cs.GT", "econ.TH", "cs.MA"],
    },
    "spectral_graph_theory": {
        "label": "Spectral Graph Theory for KG Health",
        "queries": [
            "spectral graph theory Laplacian knowledge graph health 2025 2026",
            "Fiedler value graph connectivity agent memory 2025 2026",
            "spectral clustering knowledge graph community detection 2025 2026",
            "treewidth query complexity knowledge graph retrieval 2025 2026",
            "expander graph robust retrieval agent 2025 2026",
        ],
        "arxiv_cats": ["math.CO", "cs.DS", "cs.IR"],
    },
    "online_learning": {
        "label": "Online Learning / Regret Minimisation for Adaptive Routing",
        "queries": [
            "online learning regret minimization adaptive routing agent 2025 2026",
            "EXP3 multiplicative weights skill selection agent 2025 2026",
            "bandit algorithm retrieval source selection agent 2025 2026",
            "convex optimisation retrieval scoring skill selection 2025 2026",
            "compressed sensing sparse memory storage agent LLM 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "cs.IR"],
    },
    "dynamical_systems": {
        "label": "Dynamical Systems / Fixed-Point / Bifurcation / Loss Landscape Topology",
        "queries": [
            "fixed-point theorem convergence iterative self-improvement LLM agent 2025 2026",
            "bifurcation theory phase transition agent self-improvement 2025 2026",
            "Morse theory critical point loss landscape neural network 2025 2026",
            "stability analysis recursive self-modification AI agent 2025 2026",
            "chaotic divergence iterative refinement LLM reasoning loop 2025 2026",
        ],
        "arxiv_cats": ["math.DS", "cs.AI", "cs.LG", "math.DG"],
    },
    "formal_verification_agent": {
        "label": "Formal Verification / Model Checking / Temporal Logic for Agent Safety",
        "queries": [
            "formal verification LLM agent proof assistant Lean Coq 2025 2026",
            "model checking LTL CTL agent loop safety verification 2025 2026",
            "LTL linear temporal logic agent behavior specification 2025 2026",
            "type-safe tool calling formal contract agent 2025 2026",
            "bounded model checking AI agent constraint satisfaction 2025 2026",
        ],
        "arxiv_cats": ["cs.LO", "cs.PL", "cs.AI", "cs.SE"],
    },
    "logic_semantics_agent": {
        "label": "Description Logics / Computability / Domain Theory / Proof Complexity for Agents",
        "queries": [
            "description logic OWL ontology reasoning agent knowledge graph 2025 2026",
            "Rice theorem agent behavior undecidability halting 2025 2026",
            "domain theory Scott topology fixpoint agent program semantics 2025 2026",
            "proof complexity resolution system LLM chain of thought 2025 2026",
            "homotopy type theory HoTT univalence agent program composition 2025 2026",
        ],
        "arxiv_cats": ["cs.AI", "cs.LO", "cs.IR", "math.LO"],
    },
    "information_geometry": {
        "label": "Information Geometry / Optimal Transport / Embedding Space Curvature",
        "queries": [
            "information geometry Fisher metric embedding retrieval LLM 2025 2026",
            "Wasserstein distance optimal transport agent memory alignment 2025 2026",
            "Riemannian manifold semantic embedding curvature agent memory 2025 2026",
            "Sinkhorn algorithm agent knowledge graph update 2025 2026",
            "natural gradient optimisation language model agent 2025 2026",
        ],
        "arxiv_cats": ["math.DG", "stat.ML", "cs.LG", "math.OC"],
    },
    "combinatorics_approx": {
        "label": "Combinatorics / Approximation Theory for Context Compression",
        "queries": [
            "approximation theory error bound lossy summarization LLM context 2025 2026",
            "combinatorial optimisation chunk boundary context window agent 2025 2026",
            "rate-distortion context compression truncation safety LLM 2025 2026",
            "set cover greedy retrieval selection agent memory 2025 2026",
            "Johnson-Lindenstrauss dimensionality reduction agent embedding 2025 2026",
        ],
        "arxiv_cats": ["math.CO", "cs.DS", "cs.IR"],
    },
    "generalization_theory": {
        "label": "Generalization Theory: Concentration / PAC / PAC-Bayes / Empirical Processes",
        "queries": [
            "concentration inequality Hoeffding Bernstein LLM agent evaluation 2025 2026",
            "VC dimension Rademacher complexity LLM generalization bound 2025 2026",
            "PAC-Bayes bound McAllester foundation model generalization 2025 2026",
            "empirical process theory Glivenko-Cantelli agent evaluation 2025 2026",
            "uniform convergence generalization bound LLM agent 2025 2026",
        ],
        "arxiv_cats": ["stat.ML", "cs.LG", "math.ST"],
    },
    "verifiability": {
        "label": "Verifiable Computation / ZK-Proofs / Interactive Proofs / Coding Theory for Agent Integrity",
        "queries": [
            "zero-knowledge proof LLM agent tool call attestation zkML 2025 2026",
            "interactive proof system verifier-prover agent LLM 2025 2026",
            "error correcting code fault tolerant neural network agent memory 2025 2026",
            "SNARK STARK verifiable inference language model 2025 2026",
            "PCP probabilistically checkable proof agent verification 2025 2026",
        ],
        "arxiv_cats": ["cs.CR", "cs.AI", "cs.CL", "cs.CC"],
    },
    "singular_learning_theory": {
        "label": "Singular Learning Theory / Algebraic Geometry for LLMs",
        "queries": [
            "singular learning theory Watanabe WBIC language model 2025 2026",
            "algebraic geometry neural network loss landscape 2025 2026",
            "real log canonical threshold RLCT transformer 2025 2026",
            "Bayesian information criterion singular model LLM 2025 2026",
            "loss landscape algebraic variety neural network 2025 2026",
        ],
        "arxiv_cats": ["math.AG", "stat.ML", "cs.LG"],
    },
    "formal_language_automata": {
        "label": "Formal Language Theory / Automata for Structured Output",
        "queries": [
            "grammar-constrained decoding LLM structured output 2025 2026",
            "finite state automaton tool call sequence agent 2025 2026",
            "context-free grammar generation language model constrained 2025 2026",
            "pushdown automaton formal language structured generation LLM 2025 2026",
            "regular expression constrained decoding agent output 2025 2026",
        ],
        "arxiv_cats": ["cs.FL", "cs.CL", "cs.AI"],
    },
    "multiagent_systems_theory": {
        "label": "Multi-Agent Systems Theory: Queuing / Scheduling / Distributed / Communication Complexity",
        "queries": [
            "queuing theory M/M/1 agent concurrency tool call latency 2025 2026",
            "job shop scheduling makespan multi-agent task assignment 2025 2026",
            "CAP theorem consistency availability multi-agent LLM 2025 2026",
            "communication complexity multi-agent coordination protocol 2025 2026",
            "Paxos Raft consensus distributed agent memory 2025 2026",
        ],
        "arxiv_cats": ["cs.PF", "cs.MA", "math.PR", "cs.DS"],
    },
    "computational_geometry": {
        "label": "Computational Geometry for Embedding Space Navigation",
        "queries": [
            "HNSW navigable small world approximate nearest neighbour embedding 2025 2026",
            "Voronoi diagram retrieval partition embedding space agent 2025 2026",
            "computational geometry approximate nearest neighbour LLM 2025 2026",
            "locality sensitive hashing embedding retrieval agent 2025 2026",
            "geometric data structure vector search agent memory 2025 2026",
        ],
        "arxiv_cats": ["cs.CG", "cs.IR", "cs.DS"],
    },
    "lattice_order_theory": {
        "label": "Lattice Theory / Order Theory for Planning and Ontologies",
        "queries": [
            "lattice theory partial order planning agent knowledge 2025 2026",
            "Galois connection ontology hierarchy agent reasoning 2025 2026",
            "complete lattice fixpoint semantics agent program 2025 2026",
            "knowledge lattice skill dependency agent planning 2025 2026",
            "Boolean lattice concept learning agent knowledge graph 2025 2026",
        ],
        "arxiv_cats": ["math.OA", "cs.AI", "cs.LO"],
    },
    "convex_analysis": {
        "label": "Convex Analysis for Agent Planning and Optimisation",
        "queries": [
            "convex optimisation LP relaxation agent planning 2025 2026",
            "Lagrangian duality constrained agent resource optimisation 2025 2026",
            "robust convex optimisation agent decision under uncertainty 2025 2026",
            "Frank-Wolfe projected gradient descent agent policy 2025 2026",
            "subdifferential nonsmooth optimisation agent reward 2025 2026",
        ],
        "arxiv_cats": ["math.OC", "cs.LG", "stat.ML"],
    },
    "descriptive_complexity": {
        "label": "Descriptive Complexity / Circuit Complexity of Transformers",
        "queries": [
            "circuit complexity transformer expressivity AC0 2025 2026",
            "descriptive complexity LLM reasoning limits formal 2025 2026",
            "transformer computational class TC0 formal language 2025 2026",
            "constant depth circuit language model provable limitation 2025 2026",
            "NC circuit class neural network expressivity 2025 2026",
        ],
        "arxiv_cats": ["cs.CC", "cs.LG", "cs.LO"],
    },
    "robust_stats": {
        "label": "Robust / Nonparametric Statistics for Agent Evaluation",
        "queries": [
            "robust statistics influence function M-estimator agent evaluation 2025 2026",
            "nonparametric test Mann-Whitney KS agent benchmark 2025 2026",
            "breakdown point adversarial benchmark contamination LLM 2025 2026",
            "distribution-free evaluation LLM agent performance 2025 2026",
            "trimmed mean median robustness agent evaluation metric 2025 2026",
        ],
        "arxiv_cats": ["stat.ME", "cs.LG", "stat.ML"],
    },
    "graph_flows_matching": {
        "label": "Classical Graph Theory: Flows and Matching for Agent Routing",
        "queries": [
            "max-flow min-cut tool routing agent resource allocation 2025 2026",
            "bipartite matching task agent assignment optimisation 2025 2026",
            "network flow agent pipeline scheduling 2025 2026",
            "Hungarian algorithm optimal assignment multi-agent 2025 2026",
            "min-cost flow agent workload distribution 2025 2026",
        ],
        "arxiv_cats": ["cs.DS", "cs.MA", "math.CO"],
    },
    "randomized_data_structs": {
        "label": "Randomized Algorithms / Streaming / Persistent Data Structures for Agent Memory",
        "queries": [
            "locality sensitive hashing approximate memory lookup agent 2025 2026",
            "Count-Min sketch streaming agent memory bounded space 2025 2026",
            "persistent data structure agent memory versioning rollback 2025 2026",
            "Bloom filter deduplication agent memory stream 2025 2026",
            "sketching algorithm fast approximate retrieval LLM 2025 2026",
        ],
        "arxiv_cats": ["cs.DS", "cs.IR", "cs.LG", "cs.PL"],
    },
    "sparse_lowrank": {
        "label": "Compressed Sensing / Matrix Completion / Tensor Decompositions for Agent Compression",
        "queries": [
            "compressed sensing RIP sparse recovery agent memory 2025 2026",
            "matrix completion nuclear norm low-rank attention approximation 2025 2026",
            "Tucker CP tensor decomposition KV-cache attention LLM 2025 2026",
            "basis pursuit LASSO sparse agent context representation 2025 2026",
            "tensor train TT decomposition language model compression 2025 2026",
        ],
        "arxiv_cats": ["cs.IT", "eess.SP", "cs.LG", "stat.ML"],
    },
    "neural_theory": {
        "label": "Neural Network Theory: NTK / Expressivity / Random Matrix / Overparameterization",
        "queries": [
            "neural tangent kernel NTK transformer fine-tuning theory 2025 2026",
            "universal approximation theorem transformer depth width 2025 2026",
            "random matrix Marchenko-Pastur transformer weights spectrum 2025 2026",
            "double descent benign overfitting language model 2025 2026",
            "feature learning beyond NTK regime transformer 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "math.ST", "math.PR"],
    },
    "geometric_dl": {
        "label": "Geometric Deep Learning / Lie Groups / Equivariant Neural Networks",
        "queries": [
            "geometric deep learning equivariance symmetry LLM agent 2025 2026",
            "equivariant neural network Lie group symmetry transformer 2025 2026",
            "G-CNN group equivariant convolution knowledge graph 2025 2026",
            "Bronstein geometric deep learning blueprint 2025 2026",
            "Lie algebra invariant representation learning 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "math.GR", "cs.AI", "stat.ML"],
    },
    "llm_emergence_theory": {
        "label": "LLM Theory: In-Context Learning / CoT / Emergence / Scaling Laws / Attention",
        "queries": [
            "in-context learning theory gradient descent transformer 2025 2026",
            "chain-of-thought theory formal analysis why CoT works 2025 2026",
            "grokking phase transition emergent capability LLM 2025 2026",
            "Chinchilla scaling law compute optimal training LLM 2025 2026",
            "attention mechanism kernel regression theory transformer 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "cs.CL", "stat.ML", "cs.CC"],
    },
    "rlhf_theory": {
        "label": "RLHF Theory: Reward Model Learning and KL-Constrained Optimisation",
        "queries": [
            "RLHF theory reward model learning KL constraint 2025 2026",
            "constitutional AI mathematical foundation RLHF 2025 2026",
            "DPO direct preference optimization theory 2025 2026",
            "reward hacking overoptimization theory RLHF 2025 2026",
            "KL-regularized reinforcement learning LLM theory 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "cs.AI", "stat.ML"],
    },
    "agent_adaptation_theory": {
        "label": "Agent Adaptation Theory: Meta-Learning / Continual / Curriculum / Multi-Task / Imitation",
        "queries": [
            "MAML convergence theory meta-learning agent adaptation 2025 2026",
            "catastrophic forgetting theory plasticity stability LLM agent 2025 2026",
            "curriculum learning theory competence ordering agent skill 2025 2026",
            "multi-task learning theory task similarity negative transfer agent 2025 2026",
            "imitation learning behavioral cloning DAgger theory agent 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "cs.AI"],
    },
    "rl_theory_comprehensive": {
        "label": "RL Theory: PAC-MDP / Safe RL / Reward Shaping / Hierarchical / Inverse / Model-Based",
        "queries": [
            "PAC-MDP sample complexity reinforcement learning agent 2025 2026",
            "constrained MDP safe reinforcement learning Lyapunov agent 2025 2026",
            "options framework temporal abstraction hierarchical RL theory 2025 2026",
            "inverse reinforcement learning theory reward inference agent 2025 2026",
            "model-based reinforcement learning theory Dyna world model agent 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "math.OC", "cs.AI"],
    },
    "representation_interp": {
        "label": "Representation Learning Theory / Mechanistic Interpretability Mathematics",
        "queries": [
            "linear representation hypothesis LLM internal structure 2025 2026",
            "mechanistic interpretability circuit superposition LLM 2025 2026",
            "disentanglement theory representation learning agent 2025 2026",
            "sparse autoencoder mechanistic interpretation LLM 2025 2026",
            "latent space geometry representation theory LLM 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "cs.AI", "cs.CL"],
    },
    "eval_uncertainty_fairness": {
        "label": "Uncertainty Quantification / Active Learning / Algorithmic Fairness for Agent Evaluation",
        "queries": [
            "conformal prediction uncertainty quantification LLM agent 2025 2026",
            "active learning query complexity agent information gathering 2025 2026",
            "algorithmic fairness impossibility theorem agent evaluation 2025 2026",
            "calibration theory epistemic aleatoric uncertainty agent 2025 2026",
            "demographic parity equalized odds agent benchmark 2025 2026",
        ],
        "arxiv_cats": ["stat.ML", "cs.LG", "cs.AI"],
    },
    "moe_theory": {
        "label": "Mixture of Experts Theory: Routing and Load Balancing",
        "queries": [
            "mixture of experts routing theory load balancing LLM 2025 2026",
            "MoE capacity factor expert collapse theory 2025 2026",
            "sparse MoE gating theory agent skill routing 2025 2026",
            "expert specialization theory mixture of experts 2025 2026",
            "MoE token dropping routing theory 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "cs.CL", "stat.ML"],
    },
    "federated_learning_theory": {
        "label": "Federated Learning Theory for Distributed Agent Learning",
        "queries": [
            "federated learning convergence theory heterogeneous data agent 2025 2026",
            "FedAvg privacy utility tradeoff distributed agent 2025 2026",
            "federated fine-tuning LLM agent distributed 2025 2026",
            "differential privacy federated learning convergence 2025 2026",
            "communication efficient federated learning agent 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "cs.DC", "stat.ML"],
    },
    "diffusion_processes": {
        "label": "Diffusion Processes / SDEs for Agent World Models and Exploration",
        "queries": [
            "Langevin dynamics diffusion agent exploration noise injection 2025 2026",
            "score-based diffusion model agent world model planning 2025 2026",
            "stochastic differential equation agent policy optimization 2025 2026",
            "DDPM diffusion language model agent 2025 2026",
            "flow matching agent trajectory generation 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "stat.ML", "math.PR"],
    },
    "monte_carlo_methods": {
        "label": "Monte Carlo Methods / MCMC for Agent Belief and Planning",
        "queries": [
            "MCMC Markov chain Monte Carlo agent belief estimation 2025 2026",
            "importance sampling agent policy evaluation 2025 2026",
            "particle filter sequential Monte Carlo agent 2025 2026",
            "Monte Carlo tree search MCTS LLM agent planning 2025 2026",
            "Sequential Monte Carlo agent world model belief 2025 2026",
        ],
        "arxiv_cats": ["stat.CO", "cs.AI", "cs.LG"],
    },
    "numerical_optimization": {
        "label": "Numerical Optimization Theory for Agent Fine-Tuning",
        "queries": [
            "SGD Adam convergence theory LLM fine-tuning 2025 2026",
            "second order optimization Hessian language model training 2025 2026",
            "optimization landscape saddle point transformer 2025 2026",
            "learning rate schedule convergence agent reward model 2025 2026",
            "sharpness aware minimization SAM LLM fine-tuning 2025 2026",
        ],
        "arxiv_cats": ["math.OC", "cs.LG", "stat.ML"],
    },
    "fourier_harmonic": {
        "label": "Fourier / Harmonic Analysis for Positional Encodings and Context",
        "queries": [
            "Fourier positional encoding transformer random Fourier feature 2025 2026",
            "harmonic analysis multiresolution context window LLM 2025 2026",
            "wavelet transform multiresolution agent context 2025 2026",
            "frequency domain analysis transformer attention 2025 2026",
            "NTK neural tangent kernel random Fourier feature agent 2025 2026",
        ],
        "arxiv_cats": ["cs.LG", "math.CA", "stat.ML"],
    },
    "time_series_analysis": {
        "label": "Time Series Analysis for Agent Performance Monitoring",
        "queries": [
            "time series analysis agent performance trend monitoring 2025 2026",
            "change point detection agent behavior anomaly 2025 2026",
            "Kalman filter agent state estimation temporal 2025 2026",
            "ARIMA temporal agent memory access pattern 2025 2026",
            "spectral analysis periodic agent behavior tool call 2025 2026",
        ],
        "arxiv_cats": ["stat.ME", "cs.LG", "eess.SP"],
    },
    "mean_field_large_dev": {
        "label": "Mean Field Theory / Large Deviations for Multi-Agent Emergence and Failure Rates",
        "queries": [
            "mean field theory multi-agent LLM emergent behavior 2025 2026",
            "large deviations Cramer theorem rare event agent failure 2025 2026",
            "statistical mechanics energy landscape transformer training 2025 2026",
            "Sanov theorem empirical measure agent evaluation tail 2025 2026",
            "free energy principle agent belief update 2025 2026",
        ],
        "arxiv_cats": ["cond-mat.dis-nn", "cs.AI", "cs.MA", "math.PR"],
    },
    "quantum_computing": {
        "label": "Quantum Computing / Quantum Information for Future Agent Architectures",
        "queries": [
            "quantum machine learning LLM agent quantum advantage 2025 2026",
            "variational quantum eigensolver VQE agent optimization 2025 2026",
            "quantum attention mechanism transformer 2025 2026",
            "quantum natural language processing QNLP 2025 2026",
            "quantum neural network agent future architecture 2025 2026",
        ],
        "arxiv_cats": ["quant-ph", "cs.ET", "cs.LG"],
    },
    "measure_theory_ergodic": {
        "label": "Measure Theory / Ergodic Theory for Agent Memory Invariants",
        "queries": [
            "ergodic theory stationary distribution agent memory 2025 2026",
            "measure theory LLM context window convergence 2025 2026",
            "mixing time Markov chain agent state retrieval 2025 2026",
            "sigma-algebra filtration agent planning under uncertainty 2025 2026",
            "invariant measure neural network trajectory stability 2025 2026",
        ],
        "arxiv_cats": ["math.DS", "math.PR", "cs.LG"],
    },
    "nonlinear_control": {
        "label": "Nonlinear Control Theory / Lyapunov / CLF for Agent Loop Stability",
        "queries": [
            "Lyapunov function LLM agent loop stability 2025 2026",
            "control barrier function agent constraint satisfaction planning 2025 2026",
            "CLF safe reinforcement learning agent 2025 2026",
            "contraction theory neural network agent convergence 2025 2026",
            "input-to-state stability agent feedback loop 2025 2026",
        ],
        "arxiv_cats": ["math.OC", "cs.SY", "eess.SY", "cs.AI"],
    },
    "optimal_transport_geometry": {
        "label": "Optimal Transport / Wasserstein Geometry for Agent Memory and Routing",
        "queries": [
            "optimal transport Wasserstein LLM knowledge graph 2025 2026",
            "Sinkhorn divergence embedding space agent memory consolidation 2025 2026",
            "earth mover distance skill retrieval semantic routing 2025 2026",
            "Wasserstein barycenter memory distribution merging agent 2025 2026",
            "unbalanced optimal transport agent context compression 2025 2026",
        ],
        "arxiv_cats": ["math.OC", "math.PR", "cs.LG", "cs.AI"],
    },
    "tropical_geometry": {
        "label": "Tropical Geometry / Max-Plus Algebra for Agent Planning",
        "queries": [
            "tropical semiring max-plus planning agent 2025 2026",
            "tropical geometry neural network decision boundary 2025 2026",
            "max-plus algebra skill graph shortest path agent 2025 2026",
            "tropical optimization routing LLM workflow 2025 2026",
            "idempotent semiring dynamic programming agent planning 2025 2026",
        ],
        "arxiv_cats": ["math.AG", "cs.DM", "cs.AI", "math.OC"],
    },
    "harmonic_analysis_wavelets": {
        "label": "Wavelet / Time-Frequency Analysis for Sequence and Context Compression",
        "queries": [
            "wavelet transform token sequence compression LLM 2025 2026",
            "multi-resolution analysis agent trajectory 2025 2026",
            "time-frequency representation agent memory 2025 2026",
            "discrete wavelet transform context compression 2025 2026",
            "scattering transform agent state representation 2025 2026",
        ],
        "arxiv_cats": ["math.CA", "cs.IT", "cs.LG"],
    },
    "complexity_theory_agent": {
        "label": "Complexity Theory / Oracle Computability for Agent Skill Boundaries",
        "queries": [
            "oracle complexity LLM tool use agent 2025 2026",
            "BPP interactive proof complexity agent workflow 2025 2026",
            "hardness planning problem LLM agent 2025 2026",
            "query complexity language model in-context learning 2025 2026",
            "communication complexity multi-agent protocol 2025 2026",
        ],
        "arxiv_cats": ["cs.CC", "cs.LO", "cs.AI"],
    },
    "abstract_algebra_rings": {
        "label": "Ring / Module Theory for Structured Memory Scoring and Retrieval",
        "queries": [
            "ring module algebra memory retrieval scoring 2025 2026",
            "polynomial ring query expansion information retrieval 2025 2026",
            "algebraic structure knowledge representation agent 2025 2026",
            "module homomorphism format-invariant retrieval 2025 2026",
            "graded algebra agent knowledge graph 2025 2026",
        ],
        "arxiv_cats": ["math.RA", "math.AC", "cs.IR"],
    },
    "number_theory_cryptography": {
        "label": "Number Theory / Cryptography for Verifiable Agent Integrity",
        "queries": [
            "zero-knowledge proof LLM agent tool output attestation 2025 2026",
            "homomorphic evaluation agent skill integrity 2025 2026",
            "hash chain provenance agent memory 2025 2026",
            "post-quantum cryptography agent security 2025 2026",
            "commitment scheme verifiable agent computation 2025 2026",
        ],
        "arxiv_cats": ["cs.CR", "math.NT", "cs.AI"],
    },
    "random_graphs": {
        "label": "Random Graphs for Knowledge Graph Growth and Robustness",
        "queries": [
            "Erdos-Renyi random graph knowledge graph growth agent 2025 2026",
            "preferential attachment scale-free KG agent memory 2025 2026",
            "random graph phase transition robustness agent network 2025 2026",
            "small world network agent knowledge graph topology 2025 2026",
            "random geometric graph embedding space agent retrieval 2025 2026",
        ],
        "arxiv_cats": ["math.CO", "cs.SI", "cs.AI"],
    }
}


# Multilingual supplementary sources
MULTILINGUAL_SOURCES = {
    "zh": {
        "label": "Chinese (via AMiner / arXiv Chinese institutions)",
        "aminer_queries": [
            "agent memory architecture",
            "multi-agent LLM collaboration",
            "LLM reasoning planning",
            "agent self-improvement trajectory",
            "agentic RAG retrieval",
            "agent evaluation benchmark",
            "LLM tool use function calling",
            "causal inference LLM agent",
            "reinforcement learning theory agent",
            "optimal transport embedding alignment",
            "scaling law neural network",
            "continual learning catastrophic forgetting",
            "formal verification agent safety",
            "knowledge graph description logic",
            "attention mechanism theory transformer",
        ],
    },
    "ja": {
        "label": "Japanese (J-STAGE)",
        "jstage_queries": [
            "LLM agent",
            "language model planning",
            "multi-agent system",
            "agent memory retrieval",
            "causal inference agent",
            "reinforcement learning theory",
            "formal verification language model",
            "knowledge graph reasoning",
        ],
    },
    "fr": {
        "label": "French (HAL)",
        "hal_queries": [
            "agent LLM raisonnement planification",
            "agent mémoire architecture",
            "système multi-agent LLM",
            "agent amélioration automatique",
            "évaluation agent langage",
            "théorie des groupes graphes topologie",
            "théorie des catégories représentation des connaissances",
            "théorie de l'information compression mémoire agent",
            "topologie algébrique graphe de connaissances",
            "processus stochastique décision agent Markov",
            "théorie des jeux routage multi-agent",
            "inférence causale agent planification",
            "théorie apprentissage statistique généralisation LLM",
            "systèmes distribués consensus agent mémoire",
            "transport optimal alignement mémoire agent",
            "lois d'échelle apprentissage profond LLM",
            "apprentissage par renforcement théorie agent",
            "logique temporelle vérification formelle agent",
            "logique de description graphe de connaissances",
            "géométrie différentielle apprentissage profond",
            "inégalité de concentration apprentissage PAC",
            "preuves à divulgation nulle agent attestation",
            "complexité de circuit expressivité transformeur",
            "algorithmes aléatoires mémoire agent approximatif",
            "apprentissage continu oubli catastrophique agent",
        ],
    },
    "ru": {
        "label": "Russian (CyberLeninka)",
        "cyberleninka_queries": [
            "языковая модель агент рассуждение",
            "мультиагентная система LLM",
            "LLM agent memory",
            "agent self-improvement reinforcement",
            "теория групп граф топология знания",
            "теория категорий представление знаний агент",
            "теория информации сжатие памяти агент",
            "топологический анализ данных граф знаний",
            "стохастический процесс принятие решений агент",
            "теория игр маршрутизация многоагентный",
            "причинный вывод планирование агент",
            "статистическая теория обучения обобщение нейросеть",
            "оптимальный транспорт выравнивание памяти",
            "масштабирование нейронные сети закономерности",
            "обучение с подкреплением теория агент",
            "формальная верификация безопасность агент",
            "логика описания граф знаний онтология",
            "концентрационное неравенство PAC обучение",
            "рандомизированные алгоритмы память агент",
            "непрерывное обучение катастрофическое забывание",
        ],
    },
    "ko": {
        "label": "Korean (via arXiv Korean institutions)",
        "arxiv_queries": [
            "agent LLM KAIST Seoul National University 2026",
            "language model reasoning POSTECH Korea 2026",
            "multi-agent system Korean university 2025 2026",
        ],
    },
}

# HuggingFace Papers trending URL
HF_PAPERS_URL = "https://huggingface.co/papers"
# Papers With Code trending
PWC_TRENDING = "https://paperswithcode.com/latest"

# ── Helpers ───────────────────────────────────────────────────────────────

def paper_key(arxiv_id: str) -> str:
    return hashlib.sha256(arxiv_id.encode()).hexdigest()[:16]


def load_seen() -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text())
        except Exception as e:
            import sys as _s
            print(f"[hermes-research-sweep] WARNING: seen_papers.json corrupt ({e}), renaming and starting fresh", file=_s.stderr)
            try:
                SEEN_FILE.rename(SEEN_FILE.with_suffix(".corrupt"))
            except Exception:
                pass
            return {}
    return {"seen": [], "last_updated": None, "last_sweep": None}


def save_seen(seen: dict) -> None:
    if len(seen["seen"]) > MAX_SEEN:
        seen["seen"] = seen["seen"][-MAX_SEEN:]
    seen["last_updated"] = datetime.now(timezone.utc).isoformat()
    _tmp = SEEN_FILE.with_suffix(".tmp")
    _tmp.write_text(json.dumps(seen, indent=2))
    _tmp.replace(SEEN_FILE)


def fetch(url: str, timeout: int = 15) -> str:
    """Fetch URL, return text or empty string on error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HermesResearch/1.0 (research-sweep; mailto:research@hermes.local)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] fetch failed for {url!r}: {e}", file=_s.stderr)
        return ""


def arxiv_id_valid(arxiv_id: str) -> bool:
    """Filter out fake DOI-derived IDs like 9027.37650."""
    try:
        parts = arxiv_id.split(".")
        return int(parts[0]) < 10000
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] arxiv_id_valid error: {e}", file=_s.stderr)
        return False


# ── arXiv listing sweep (most reliable for recency) ───────────────────────

def sweep_arxiv_listings(categories: list[str]) -> list[dict]:
    """Walk arXiv category listing pages for very recent papers."""
    papers = []
    for cat in set(categories):
        url = f"https://arxiv.org/list/{cat}/recent"
        html = fetch(url, timeout=20)
        if not html:
            continue
        # Dedup IDs (abs+pdf). Pair titles only when counts match — else placeholder.
        ids_found = _unique_arxiv_ids(re.findall(r'arXiv:(\d{4}\.\d{4,5})', html))
        titles = [clean_arxiv_title(t) for t in re.findall(
            r'class="title[^"]*"[^>]*>\s*<span[^>]*>Title:</span>\s*(.*?)</span>', html)]
        titles = [t for t in titles if t]
        pair_ok = len(titles) == len(ids_found)
        for i, arxiv_id in enumerate(ids_found):
            title = titles[i] if pair_ok else ""
            papers.append({
                "id": arxiv_id,
                "title": title or f"[arXiv:{arxiv_id}]",
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "source": f"arxiv-listing:{cat}",
                "category": None,  # assigned by caller
            })
        time.sleep(0.5)
    return papers


# ── arXiv HTML search (keyword-matched, date-sorted) ──────────────────────

def search_arxiv_html(query: str, max_results: int = 10) -> list[dict]:
    """Use arXiv HTML search interface (not API — API hangs on this host)."""
    q = urllib.parse.quote(query)
    url = f"https://arxiv.org/search/?searchtype=all&query={q}&start=0&order=-submitted_date"
    html = fetch(url, timeout=20)
    if not html:
        return []
    results = []
    seen = set()
    # Pair ID+title from the same result card. Global index pairing mislabels papers
    # because arXiv:ID appears twice per hit (abs + pdf) and chrome matches 'title'.
    blocks = re.findall(r'class="arxiv-result"(.*?)</li>', html, re.DOTALL | re.I)
    for block in blocks:
        m = re.search(r'arXiv:(\d{4}\.\d{4,5})', block)
        if not m:
            continue
        arxiv_id = m.group(1)
        if arxiv_id in seen or not arxiv_id_valid(arxiv_id):
            continue
        tm = re.search(r'class="title[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
        title = clean_arxiv_title(tm.group(1) if tm else "")
        seen.add(arxiv_id)
        results.append({
            "id": arxiv_id,
            "title": title or f"[arXiv:{arxiv_id}]",
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "source": "arxiv-search",
            "category": None,
        })
        if len(results) >= max_results:
            break
    if results:
        return results
    # Fallback: unique IDs, never invent a title from page chrome.
    for arxiv_id in _unique_arxiv_ids(re.findall(r'arXiv:(\d{4}\.\d{4,5})', html))[:max_results]:
        results.append({
            "id": arxiv_id,
            "title": f"[arXiv:{arxiv_id}]",
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "source": "arxiv-search",
            "category": None,
        })
    return results


# ── Semantic Scholar API ───────────────────────────────────────────────────

def search_semantic_scholar(query: str, max_results: int = 5) -> list[dict]:
    """Query S2 search API. Unauthenticated: 1 req/sec limit."""
    q = urllib.parse.quote(query)
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={q}&limit={max_results}"
           f"&fields=title,externalIds,year,citationCount,influentialCitationCount")
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for p in data.get("data", []):
            arxiv_id = p.get("externalIds", {}).get("ArXiv", "")
            if not arxiv_id or not arxiv_id_valid(arxiv_id):
                continue
            papers.append({
                "id": arxiv_id,
                "title": p.get("title", ""),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "source": "semantic-scholar",
                "citations": p.get("citationCount", 0),
                "year": p.get("year"),
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] semantic_scholar parse error: {e}", file=_s.stderr)
        return []


# ── HAL (French/EU) ───────────────────────────────────────────────────────

def search_hal(query: str, max_results: int = 5) -> list[dict]:
    q = urllib.parse.quote(query)
    url = (f"https://api.archives-ouvertes.fr/search/"
           f"?q={q}&rows={max_results}&fl=title_s,authFullName_s,uri_s,doiId_s,producedDate_s&wt=json&sort=producedDate_s+desc")
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for doc in data.get("response", {}).get("docs", []):
            title = doc.get("title_s", [""])[0] if isinstance(doc.get("title_s"), list) else doc.get("title_s", "")
            uri = doc.get("uri_s", "")
            papers.append({
                "id": uri,
                "title": title,
                "url": uri,
                "source": "hal",
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] hal parse error: {e}", file=_s.stderr)
        return []


# ── AMiner (Chinese AI/CS) ────────────────────────────────────────────────

def search_aminer(query: str, max_results: int = 5) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://api.aminer.org/api/search/pub?query={q}&size={max_results}"
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for p in data.get("result", [])[:max_results]:
            title = p.get("title", "")
            urls = p.get("urls", [])
            link = urls[0] if urls else ""
            # Try to extract arXiv ID
            arxiv_id = ""
            for u in urls:
                m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', u)
                if m and arxiv_id_valid(m.group(1)):
                    arxiv_id = m.group(1)
                    break
            papers.append({
                "id": arxiv_id or link,
                "title": title,
                "url": link or f"https://www.aminer.org/search?q={q}",
                "source": "aminer",
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] aminer parse error: {e}", file=_s.stderr)
        return []


# ── OpenAlex ──────────────────────────────────────────────────────────────

def search_openalex(query: str, max_results: int = 5) -> list[dict]:
    q = urllib.parse.quote(query)
    # Filter for recent (2025+) CS papers only (concept C41008148 = Computer Science)
    # Excludes medical/biology/physics noise from broad OpenAlex indexing
    url = (f"https://api.openalex.org/works?search={q}&per-page={max_results}"
           f"&filter=publication_year:2025|2026,concepts.id:C41008148&sort=cited_by_count:desc"
           f"&mailto=research@hermes.local")
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for w in data.get("results", []):
            title = w.get("title", "")
            doi = w.get("doi", "")
            # Try to get arXiv ID from locations
            arxiv_id = ""
            for loc in w.get("locations", []):
                lurl = loc.get("landing_page_url", "") or loc.get("pdf_url", "") or ""
                m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', lurl)
                if m and arxiv_id_valid(m.group(1)):
                    arxiv_id = m.group(1)
                    break
            link = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else doi or ""
            papers.append({
                "id": arxiv_id or doi or title[:40],
                "title": title,
                "url": link,
                "source": "openalex",
                "citations": w.get("cited_by_count", 0),
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] openalex parse error: {e}", file=_s.stderr)
        return []


# ── Crossref (DOI-based, high quality) ───────────────────────────────────

def search_crossref(query: str, max_results: int = 5) -> list[dict]:
    # Tighten query to CS/AI domain — suppresses medical/physics/cosmology noise
    # Crossref doesn't have a subject filter, so bake it into the query string
    cs_query = f'({query}) AND (agent OR LLM OR "language model" OR "neural network")'
    q = urllib.parse.quote(cs_query)
    url = (f"https://api.crossref.org/works?query={q}&rows={max_results}"
           f"&filter=from-pub-date:2025&sort=is-referenced-by-count&order=desc"
           f"&mailto=research@hermes.local")
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for item in data.get("message", {}).get("items", []):
            titles = item.get("title", [""])
            title = titles[0] if titles else ""
            doi = item.get("DOI", "")
            url_out = item.get("URL", "") or f"https://doi.org/{doi}"
            papers.append({
                "id": doi or title[:40],
                "title": title,
                "url": url_out,
                "source": "crossref",
                "citations": item.get("is-referenced-by-count", 0),
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] crossref parse error: {e}", file=_s.stderr)
        return []


# ── J-STAGE (Japanese) ────────────────────────────────────────────────────

def search_jstage(query: str, max_results: int = 5) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://api.jstage.jst.go.jp/articles/_search?text={q}&count={max_results}&lang=en"
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        root = ET.fromstring(text)
        papers = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            title = title_el.text if title_el is not None else ""
            link = link_el.get("href", "") if link_el is not None else ""
            papers.append({
                "id": link or title[:40],
                "title": title,
                "url": link,
                "source": "jstage",
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] jstage parse error: {e}", file=_s.stderr)
        return []


# ── CyberLeninka (Russian/Eastern European OA) ───────────────────────────

def search_cyberleninka(query: str, max_results: int = 5) -> list[dict]:
    q = urllib.parse.quote(query)
    url = f"https://cyberleninka.ru/api/1/search?q={q}&size={max_results}"
    text = fetch(url, timeout=15)
    if not text:
        return []
    try:
        data = json.loads(text)
        papers = []
        for item in data.get("response", {}).get("docs", [])[:max_results]:
            title = item.get("article_name", "")
            link = item.get("url", "")
            papers.append({
                "id": link or title[:40],
                "title": title,
                "url": f"https://cyberleninka.ru{link}" if link.startswith("/") else link,
                "source": "cyberleninka",
                "category": None,
            })
        return papers
    except Exception as e:
        import sys as _s
        print(f"[hermes-research-sweep] cyberleninka parse error: {e}", file=_s.stderr)
        return []


# ── HuggingFace Papers (community-voted trending) ─────────────────────────

def scrape_hf_papers(max_results: int = 15) -> list[dict]:
    """Scrape HuggingFace daily papers page for arXiv IDs."""
    html = fetch(HF_PAPERS_URL, timeout=20)
    if not html:
        return []
    ids = re.findall(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', html)
    papers = []
    for arxiv_id in ids[:max_results]:
        if arxiv_id_valid(arxiv_id):
            papers.append({
                "id": arxiv_id,
                "title": f"[arXiv:{arxiv_id}]",
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "source": "huggingface-papers",
                "category": "trending",
            })
    return papers


# ── Papers With Code (trending leaderboards) ──────────────────────────────

def scrape_pwc(max_results: int = 15) -> list[dict]:
    """Scrape Papers With Code latest page for arXiv IDs."""
    html = fetch(PWC_TRENDING, timeout=20)
    if not html:
        return []
    ids = re.findall(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', html)
    papers = []
    seen_ids: set[str] = set()
    for arxiv_id in ids:
        if arxiv_id_valid(arxiv_id) and arxiv_id not in seen_ids:
            seen_ids.add(arxiv_id)
            papers.append({
                "id": arxiv_id,
                "title": f"[arXiv:{arxiv_id}]",
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "source": "papers-with-code",
                "category": "trending",
            })
        if len(papers) >= max_results:
            break
    return papers


# ── Main sweep ────────────────────────────────────────────────────────────

def run_sweep() -> tuple[list[dict], list[dict]]:
    """
    Returns (all_papers, new_papers).
    all_papers: every paper found this run
    new_papers: papers not in the seen cache
    """
    seen = load_seen()
    seen_keys = set(seen["seen"])
    all_papers: list[dict] = []

    print(f"[hermes-research-sweep] Starting sweep at {datetime.now(timezone.utc).isoformat()}", file=sys.stderr)
    print(f"[hermes-research-sweep] Known papers: {len(seen_keys)}", file=sys.stderr)

    fetched_arxiv_cats: set[str] = set()  # track already-fetched listing pages

    # Direct cs.AI/cs.CL/cs.MA/cs.LG/cs.SE listing pages — ensures core agent papers
    # are always harvested regardless of per-category query matching
    print("[hermes-research-sweep] Direct CS/AI listing pages...", file=sys.stderr)
    core_cs_cats = ["cs.AI", "cs.CL", "cs.MA", "cs.LG", "cs.SE"]
    listing_papers = sweep_arxiv_listings(core_cs_cats)
    for p in listing_papers:
        p["category"] = "reasoning_planning"  # default bucket; human triage resolves
        fetched_arxiv_cats.add(p.get("arxiv_cat", ""))
    all_papers.extend(listing_papers)
    time.sleep(0.5)

    for cat_key, cat in CATEGORIES.items():
        print(f"[hermes-research-sweep] Category: {cat['label']}", file=sys.stderr)

        # 1. arXiv listing walk (most recent, pre-search-engine)
        # Deduplicate cats before listing — cs.AI appears across multiple categories
        # and sweep_arxiv_listings already deduplicates internally per run but we skip
        # re-fetching listings already done by a prior category in THIS sweep
        arxiv_cats: list[str] = [c for c in (cat.get("arxiv_cats") or []) if c not in fetched_arxiv_cats]
        fetched_arxiv_cats.update(arxiv_cats)
        listing_papers = sweep_arxiv_listings(arxiv_cats)
        for p in listing_papers:
            p["category"] = cat_key
        all_papers.extend(listing_papers)
        time.sleep(1)

        # 2. arXiv HTML search per query — all 5 queries, not just 3
        for query in cat["queries"]:
            papers = search_arxiv_html(query, max_results=8)
            for p in papers:
                p["category"] = cat_key
            all_papers.extend(papers)
            time.sleep(1.2)

        # 3. Semantic Scholar (top citations) — all 5 queries, not just 2
        for query in cat["queries"]:
            papers = search_semantic_scholar(query, max_results=5)
            for p in papers:
                p["category"] = cat_key
            all_papers.extend(papers)
            time.sleep(1.5)  # S2 rate limit

        # 4. OpenAlex (citation-ranked, recent) — top 2 queries
        for query in cat["queries"][:2]:
            papers = search_openalex(query, max_results=5)
            for p in papers:
                p["category"] = cat_key
            all_papers.extend(papers)
            time.sleep(1)

        # 5. Crossref (DOI-backed, high quality) — top query per category
        papers = search_crossref(cat["queries"][0], max_results=5)
        for p in papers:
            p["category"] = cat_key
        all_papers.extend(papers)
        time.sleep(1)

    # 5. Multilingual sources
    print("[hermes-research-sweep] Multilingual sweep...", file=sys.stderr)

    # HAL (French)
    for q in MULTILINGUAL_SOURCES["fr"]["hal_queries"]:
        papers = search_hal(q, max_results=3)
        for p in papers:
            p["category"] = "multilingual_fr"
        all_papers.extend(papers)
        time.sleep(0.8)

    # AMiner (Chinese)
    for q in MULTILINGUAL_SOURCES["zh"]["aminer_queries"]:
        papers = search_aminer(q, max_results=3)
        for p in papers:
            p["category"] = "multilingual_zh"
        all_papers.extend(papers)
        time.sleep(1)

    # J-STAGE (Japanese)
    for q in MULTILINGUAL_SOURCES["ja"]["jstage_queries"]:
        papers = search_jstage(q, max_results=3)
        for p in papers:
            p["category"] = "multilingual_ja"
        all_papers.extend(papers)
        time.sleep(0.8)

    # CyberLeninka (Russian)
    for q in MULTILINGUAL_SOURCES["ru"]["cyberleninka_queries"]:
        papers = search_cyberleninka(q, max_results=3)
        for p in papers:
            p["category"] = "multilingual_ru"
        all_papers.extend(papers)
        time.sleep(0.8)

    # Korean (via arXiv institution search — no native API)
    print("[hermes-research-sweep] Korean (arXiv institution search)...", file=sys.stderr)
    for q in MULTILINGUAL_SOURCES["ko"]["arxiv_queries"]:
        papers = search_arxiv_html(q, max_results=5)
        for p in papers:
            p["category"] = "multilingual_ko"
        all_papers.extend(papers)
        time.sleep(1)

    # HuggingFace Papers (trending — broad signal, post-filter by apply job)
    print("[hermes-research-sweep] HuggingFace Papers trending...", file=sys.stderr)
    hf_papers = scrape_hf_papers(max_results=20)
    all_papers.extend(hf_papers)
    time.sleep(1)

    # Papers With Code (leaderboard trending)
    print("[hermes-research-sweep] Papers With Code trending...", file=sys.stderr)
    pwc_papers = scrape_pwc(max_results=20)
    all_papers.extend(pwc_papers)
    time.sleep(1)

    # Deduplicate by ID, drop off-topic
    seen_this_run: set[str] = set()
    unique_papers: list[dict] = []
    filtered_count = 0
    for p in all_papers:
        pid = p["id"]
        if pid and pid not in seen_this_run:
            seen_this_run.add(pid)
            if is_offtopic(p):
                filtered_count += 1
                continue
            if is_near_duplicate(p.get('title', ''), p.get('abstract', '')):
                continue
            unique_papers.append(p)

    print(f"[hermes-research-sweep] Off-topic filtered: {filtered_count}", file=sys.stderr)

    # Filter to new papers only
    new_papers = [p for p in unique_papers if paper_key(p["id"]) not in seen_keys]

    print(f"[hermes-research-sweep] Total unique: {len(unique_papers)}, new: {len(new_papers)}", file=sys.stderr)

    # Update seen cache
    if not DRY_RUN:
        for p in new_papers:
            key = paper_key(p["id"])
            if key not in seen_keys:
                seen["seen"].append(key)
        seen["last_sweep"] = datetime.now(timezone.utc).isoformat()
        save_seen(seen)

    return unique_papers, new_papers


def build_output(new_papers: list[dict], all_papers: list[dict]) -> dict:
    """Build structured JSON output for the cron system and apply job."""
    by_category: dict[str, list[dict]] = {}
    for p in new_papers:
        cat = p.get("category", "unknown")
        by_category.setdefault(cat, []).append(p)

    return {
        "sweep_date": datetime.now(timezone.utc).isoformat(),
        "new_paper_count": len(new_papers),
        "total_scanned": len(all_papers),
        "categories": {k: v["label"] for k, v in CATEGORIES.items()},
        "new_papers_by_category": by_category,
        "new_papers_flat": new_papers,
    }


def format_digest(output: dict) -> str:
    """Plain-text digest for cron delivery."""
    lines = [
        f"=== Hermes Research Sweep — {output['sweep_date'][:10]} ===",
        f"{output['new_paper_count']} new papers across {output['total_scanned']} scanned",
        "",
    ]
    for cat_key, papers in output["new_papers_by_category"].items():
        cat_label = CATEGORIES.get(cat_key, {}).get("label", cat_key)
        lines.append(f"[{cat_label}] ({len(papers)} new)")
        for p in papers[:5]:  # top 5 per category in digest
            cites = f" [{p.get('citations', 0)} cites]" if p.get("citations") else ""
            lines.append(f"  - {p['title'][:80]}{cites}")
            lines.append(f"    {p['url']}")
        if len(papers) > 5:
            lines.append(f"  ... and {len(papers)-5} more (see JSON output)")
        lines.append("")
    lines.append(f"Full output: {OUTPUT_LATEST}")
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    all_papers, new_papers = run_sweep()
    output = build_output(new_papers, all_papers)

    if not DRY_RUN:
        _out_json = json.dumps(output, indent=2)
        _out_tmp = OUTPUT_LATEST.with_suffix(".tmp")
        _out_tmp.write_text(_out_json)
        _out_tmp.replace(OUTPUT_LATEST)
        _dated_tmp = OUTPUT_DATED.with_suffix(".tmp")
        _dated_tmp.write_text(_out_json)
        _dated_tmp.replace(OUTPUT_DATED)
        print(f"[hermes-research-sweep] Wrote {OUTPUT_LATEST}", file=sys.stderr)

    # Stdout: deliver digest only if new papers found (silent cron tick if empty)
    if new_papers or FORCE:
        print(format_digest(output))
    else:
        print(f"[hermes-research-sweep] No new papers found — silent tick", file=sys.stderr)


if __name__ == "__main__":
    main()
