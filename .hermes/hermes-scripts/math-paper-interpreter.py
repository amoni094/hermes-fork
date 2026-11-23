#!/usr/bin/env python3
"""
math-paper-interpreter.py

Interpretation layer for mathematical research papers found by hermes-research-sweep.

Takes the sweep JSON output, filters to math/theory categories, reads each paper's
abstract (or --full-text from ar5iv/PDF), and produces one of three outputs per paper:

  OPTIMIZATION  — the math sharpens an existing Hermes heuristic/threshold/policy.
                  Produces a concrete replacement formula or bound.

  SPIKE         — the math describes a structure that Hermes doesn't exploit yet.
                  Produces a Given/When/Then spike candidate with hypothesis + metric.

  SKIP          — the paper's math has no plausible Hermes analogue after honest
                  assessment.

Output: ~/.hermes/cache/research/math-interpretation-latest.json
        ~/.hermes/cache/research/math-spike-queue.json  (SPIKE entries only, for review)

Usage:
    python3 math-paper-interpreter.py [--dry-run] [--limit N] [--input PATH] [--full-text]

The interpreter does NOT apply patches itself. It produces spike candidates and
optimization proposals for human review, then the apply job or a separate session
implements them after review.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── Paths ─────────────────────────────────────────────────────────────────────

def track_skip_rate(total, skipped):
    """Anytime-valid SKIP-rate anomaly flag. Flag only; never halt H1 search.

    Source: arXiv:2608.15810 (anytime-valid admission) applied as the recorded
    viable alternative to SPRT early-stop — detect an interpreter bug or an
    overly restrictive filter, do not stop processing.
    """
    if total < 20:
        return
    skip_rate = skipped / total
    if skip_rate > 0.85:
        print(
            f"SKIP rate {skip_rate:.0%} exceeds anytime-valid anomaly threshold - possible interpreter bug or overly restrictive filter",
            file=sys.stderr,
        )


CACHE_DIR = Path("~/.hermes/cache/research").expanduser()
SWEEP_LATEST = CACHE_DIR / "hermes-math-sweep-latest.json"
OUTPUT_LATEST = CACHE_DIR / "math-interpretation-latest.json"
SPIKE_QUEUE = CACHE_DIR / "math-spike-queue.json"
SPIKE_QUEUE_DIR = Path("~/.hermes/research/spikes").expanduser()
PRIMERS_DIR = Path("~/.hermes/cache/research/primers").expanduser()

# ── Math category keys (from consolidated 51-cat sweep) ───────────────────────

MATH_CATS = {
    # Classical mathematics
    "group_theory", "category_theory", "information_theory", "algebraic_topology",
    "stochastic_causal", "game_theory", "spectral_graph_theory", "online_learning",
    "dynamical_systems", "formal_verification_agent", "logic_semantics_agent",
    "information_geometry", "combinatorics_approx", "generalization_theory",
    "verifiability", "singular_learning_theory", "formal_language_automata",
    "multiagent_systems_theory", "computational_geometry", "lattice_order_theory",
    "convex_analysis", "descriptive_complexity", "graph_flows_matching",
    "robust_stats",
    # Computational math / ML foundations
    "randomized_data_structs", "sparse_lowrank", "neural_theory", "geometric_dl",
    "llm_emergence_theory", "rlhf_theory", "agent_adaptation_theory",
    "rl_theory_comprehensive", "representation_interp", "eval_uncertainty_fairness",
    "moe_theory", "federated_learning_theory", "diffusion_processes",
    # Specialized
    "monte_carlo_methods", "numerical_optimization", "fourier_harmonic",
    "time_series_analysis", "mean_field_large_dev", "quantum_computing",
    "random_graphs",
    # New categories (2026-09-15)
    "measure_theory_ergodic", "nonlinear_control", "optimal_transport_geometry",
    "tropical_geometry", "harmonic_analysis_wavelets", "complexity_theory_agent",
    "abstract_algebra_rings", "number_theory_cryptography",
}

# ── Hermes component map ───────────────────────────────────────────────────────
# Maps math domains to Hermes components where the math might apply.
# Used to seed the interpretation prompt and structure spike hypotheses.

COMPONENT_MAP = {
    "group_theory":           ["skill embeddings (symmetry/invariance)", "structured output schemas"],
    "category_theory":        ["memory pipeline composition", "skill routing as functor", "tool-call sequences as morphisms"],
    "information_theory":     ["context compression ratio", "skill selection entropy", "memory retention scoring"],
    "algebraic_topology":     ["skill library redundancy detection (TDA)", "knowledge graph topology", "session trajectory topology"],
    "stochastic_causal":      ["memory write decisions", "tool-call side-effect modeling", "agent loop state transitions"],
    "game_theory":            ["multi-agent coordination", "resource allocation across delegate workers", "adversarial review design"],
    "spectral_graph_theory":  ["skill dependency graph", "knowledge graph health metrics", "session graph analysis"],
    "online_learning":        ["adaptive model routing", "skill success rate tracking (bandit)", "regret-minimizing cron scheduling"],
    "dynamical_systems":      ["agent loop fixed-point detection", "memory attractor states", "context compression stability"],
    "formal_verification_agent": ["tool-call sequence correctness", "agent output verification", "structured output validation"],
    "logic_semantics_agent":  ["agent reasoning traces", "formal description logics for ontologies", "proof-carrying tool results"],
    "information_geometry":   ["embedding space curvature for retrieval", "skill routing geometry", "memory clustering"],
    "combinatorics_approx":   ["context packing (bin-packing analogy)", "skill selection approximation", "token budget optimization"],
    "generalization_theory":  ["agent evaluation confidence bounds", "benchmark generalization", "skill transfer guarantees"],
    "verifiability":          ["tool output integrity", "agent action audit trail", "ZK-style verifiable computation"],
    "singular_learning_theory": ["model selection for fine-tuning", "loss landscape analysis", "LLM training phase transitions"],
    "formal_language_automata": ["structured output grammars", "tool-call FSM modeling", "agent state machine design"],
    "multiagent_systems_theory": ["cron job scheduling theory", "delegate task queue modeling", "distributed agent coordination"],
    "computational_geometry": ["embedding space navigation", "nearest-neighbor retrieval geometry", "skill clustering geometry"],
    "lattice_order_theory":   ["skill dependency partial orders", "planning ontology lattices", "memory fact ordering"],
    "convex_analysis":        ["agent optimization objectives", "loss landscape convexity assumptions", "planning as convex program"],
    "descriptive_complexity": ["transformer expressivity bounds", "circuit complexity of agent reasoning", "what agents can and cannot compute"],
    "graph_flows_matching":   ["agent task routing", "skill matching", "context retrieval as matching"],
    "robust_stats":           ["agent evaluation robustness", "outlier paper detection in sweep", "robust skill performance metrics"],
    "randomized_data_structs": ["memory cache design", "approximate retrieval data structures", "streaming paper dedup"],
    "sparse_lowrank":         ["context compression (low-rank attention)", "skill embedding compression", "memory fact compression"],
    "neural_theory":          ["understanding model behavior", "NTK-informed fine-tuning decisions", "expressivity of agent architectures"],
    "geometric_dl":           ["equivariant skill representations", "Lie group structure in embedding spaces"],
    "llm_emergence_theory":   ["scaling decisions for Hermes models", "emergence thresholds for task classes", "ICL mechanism improvements"],
    "rlhf_theory":            ["reward model calibration", "preference optimization for skill selection", "KL budget for model routing"],
    "agent_adaptation_theory": ["meta-learning for skill routing", "continual learning of user preferences", "curriculum for agent tasks"],
    "rl_theory_comprehensive": ["safe agent action bounds", "PAC-MDP for cron agent design", "reward shaping for skill scoring"],
    "representation_interp":  ["mechanistic interpretability of agent decisions", "latent space of skill embeddings"],
    "eval_uncertainty_fairness": ["calibrated agent evaluation", "conformal prediction for task success", "fairness in benchmark design"],
    "moe_theory":             ["model routing as MoE", "sparse activation in delegate patterns", "expert selection theory"],
    "federated_learning_theory": ["distributed skill learning", "privacy-preserving memory updates"],
    "diffusion_processes":    ["agent world model exploration", "stochastic planning", "memory decay modeling"],
    "monte_carlo_methods":    ["agent belief estimation", "MCMC for memory consolidation", "uncertainty sampling in active learning"],
    "numerical_optimization": ["agent fine-tuning convergence", "optimization of skill scoring functions"],
    "fourier_harmonic":       ["positional encoding theory", "context window frequency analysis", "temporal pattern detection in sessions"],
    "time_series_analysis":   ["agent performance monitoring over time", "drift detection in skill quality", "session pattern analysis"],
    "mean_field_large_dev":   ["multi-agent emergence modeling", "failure rate estimation for large agent fleets"],
    "quantum_computing":      ["future agent architectures (long-horizon)", "quantum-inspired optimization heuristics"],
    "random_graphs":          ["knowledge graph robustness", "skill library graph growth modeling", "random connectivity in agent networks"],
    # New categories (2026-09-15)
    "measure_theory_ergodic":        ["memory retention guarantees", "ergodic session-independent recall", "agent state stationarity proofs",
                                      "new: measure-theoretic memory compaction with distortion bounds", "new: concentration-inequality TTL guarantees"],
    "nonlinear_control":             ["loop-pid.py Lyapunov stability extension", "CBF-based planning constraint satisfaction", "ISS for agent feedback loops",
                                      "new: CBF constraint layer for irreversible-action prevention", "new: Lyapunov energy function as turn-budget regulator"],
    "optimal_transport_geometry":    ["KG embedding drift detection (Wasserstein)", "memory merge as barycenter", "Sinkhorn skill routing weights",
                                      "new: Wasserstein-distance memory drift alarm", "new: OT-based skill-library deduplication (transport plan = merge map)"],
    "tropical_geometry":             ["skill-graph min-cost routing (max-plus)", "idempotent planning semiring", "tropical shortest-path for multi-hop skill chains",
                                      "new: tropical semiring planner for multi-hop tool-call cost minimisation"],
    "harmonic_analysis_wavelets":    ["multi-resolution context compression", "wavelet-domain token stream analysis", "non-stationary trajectory representation",
                                      "new: wavelet multi-resolution context compressor", "new: non-stationary session drift detector via DWT"],
    "complexity_theory_agent":       ["hardness bounds for agent planning", "query complexity of skill retrieval", "oracle model of LLM tool access",
                                      "new: query-complexity certificate for skill-router (provable call-count bound)", "new: hardness classification for agent task types"],
    "abstract_algebra_rings":        ["ring-based memory score fusion", "polynomial query expansion for retrieval", "graded algebra for fact prioritisation",
                                      "new: polynomial retrieval kernel over memory facts", "new: graded-ring fact expiry policy"],
    "number_theory_cryptography":    ["ZKP tool-output attestation", "hash-chain integrity in l1-tracegrant.py", "homomorphic evaluation of skill quality",
                                      "new: ZK-attestation layer for tool outputs (verifiable tool-call proofs)", "new: hash-chain integrity for l1-tracegrant audit log"],
    # Cross-category new-capability targets (not tied to a single math field)
    # These appear when interpret_paper sets target = "new: <name>" via Step 2b:
    #   new: formal plan verification     → pre-execution action-sequence checker
    #   new: causal error attribution      → session post-mortem causal graph
    #   new: optimal stopping (subagents)  → commit threshold for fan-out results
    #   new: calibrated uncertainty over retrieved facts → confidence intervals on recall
    #   new: online convex opt for params  → adaptive per-turn hyperparameter tuner
}

# ── ArXiv abstract fetcher ─────────────────────────────────────────────────────

def fetch_abstract(arxiv_id: str, retries: int = 2) -> dict:
    """Fetch title + abstract from arXiv API."""
    url = f"https://export.arxiv.org/abs/{arxiv_id}"
    headers = {"User-Agent": "hermes-math-interpreter/1.0 (research tool)"}
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            title_m = re.search(r'<h1 class="title[^"]*"[^>]*>(?:Title:)?\s*(.*?)</h1>', html, re.DOTALL)
            abs_m = re.search(r'<blockquote class="abstract[^"]*"[^>]*>(?:Abstract:)?\s*(.*?)</blockquote>', html, re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
            abstract = re.sub(r'<[^>]+>', ' ', abs_m.group(1)).strip() if abs_m else ""
            abstract = re.sub(r'\s+', ' ', abstract)
            return {"title": title, "abstract": abstract, "id": arxiv_id}
        except (URLError, HTTPError):
            if attempt < retries:
                time.sleep(2 ** attempt)
    return {"title": "", "abstract": "", "id": arxiv_id}


def _html_to_text(html: str) -> str:
    """Strip tags from ar5iv HTML; skip script/style/nav/svg."""
    from html.parser import HTMLParser

    class _Extractor(HTMLParser):
        SKIP = {"script", "style", "nav", "svg", "noscript"}

        def __init__(self):
            super().__init__()
            self.skip = 0
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag in self.SKIP:
                self.skip += 1

        def handle_endtag(self, tag):
            if tag in self.SKIP and self.skip:
                self.skip -= 1
            if self.skip == 0 and tag in {
                "p", "div", "h1", "h2", "h3", "h4", "li", "br",
                "section", "article", "blockquote",
            }:
                self.parts.append("\n")

        def handle_data(self, data):
            if self.skip == 0:
                self.parts.append(data)

    parser = _Extractor()
    parser.feed(html)
    text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def fetch_ar5iv_text(arxiv_id: str, retries: int = 2) -> str:
    """Fetch full paper HTML from ar5iv. Empty string on failure."""
    url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
    headers = {"User-Agent": "hermes-math-interpreter/1.0 (research tool)"}
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            if len(html) < 2000:
                return ""
            text = _html_to_text(html)
            return text if len(text) >= 500 else ""
        except (URLError, HTTPError, TimeoutError, OSError):
            if attempt < retries:
                time.sleep(2 ** attempt)
    return ""


def fetch_pdf_text(arxiv_id: str) -> str:
    """Fallback: arXiv PDF → pdftotext (first 8 pages), then pypdf."""
    import io
    import subprocess
    import tempfile

    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    headers = {"User-Agent": "hermes-math-interpreter/1.0 (research tool)"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as resp:
            pdf_bytes = resp.read()
    except (URLError, HTTPError, TimeoutError, OSError):
        return ""
    if not pdf_bytes.startswith(b"%PDF"):
        return ""

    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "paper.pdf"
        txt_path = Path(td) / "paper.txt"
        pdf_path.write_bytes(pdf_bytes)
        try:
            subprocess.run(
                ["pdftotext", "-q", "-layout", "-f", "1", "-l", "8",
                 str(pdf_path), str(txt_path)],
                check=True, timeout=30, capture_output=True,
            )
            if txt_path.exists():
                text = txt_path.read_text(errors="replace")
                text = re.sub(r"[ \t]+", " ", text)
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                if len(text) >= 500:
                    return text
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = [(page.extract_text() or "") for page in reader.pages[:8]]
        text = re.sub(r"[ \t]+", " ", "\n".join(parts))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text if len(text) >= 500 else ""
    except Exception:
        return ""


def fetch_full_text(arxiv_id: str):
    """Return (text, source) with source in {'ar5iv','pdf'}. Empty text on failure."""
    text = fetch_ar5iv_text(arxiv_id)
    if text:
        return text, "ar5iv"
    text = fetch_pdf_text(arxiv_id)
    if text:
        return text, "pdf"
    return "", ""


# ── Interpretation logic ───────────────────────────────────────────────────────

def load_primer(cat_key: str) -> str:
    """Load the field primer for a category as context for interpretation."""
    primer_path = PRIMERS_DIR / f"{cat_key}.txt"
    if primer_path.exists() and primer_path.stat().st_size > 200:
        return primer_path.read_text()
    return ""


def _llm_client():
    """Lazy Anthropic client with key loaded from ~/.hermes/.env."""
    import os
    from pathlib import Path as _P
    env_path = _P("~/.hermes/.env").expanduser()
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    import anthropic
    return anthropic.Anthropic()


_CLIENT = None


def _deterministic_verdict(parsed: dict) -> str:
    """
    Compute the final verdict from structured model outputs.
    The model's self-reported 'result' is IGNORED — this function owns the verdict.

    Research basis: AutoLR (arXiv:2609.04871) + RAIL (arXiv:2608.13428):
    LLMs fill structured slots; a deterministic controller owns scores and verdict.
    This eliminates authority laundering and confidence calibration failure.

    Rules:
      OPTIMIZATION: algorithm/heuristic + structural match + feasibility==2
                    + no feasibility violations + desirability>=1 + disanalogy present
      SPIKE:        algorithm + structural match + feasibility>=1 + desirability>=1
                    + no hard feasibility violations
      SKIP:         everything else
    """
    abstraction = parsed.get("abstraction_level", "").upper()
    structural_match = bool(parsed.get("structural_match", False))
    violations = parsed.get("feasibility_violations", [])
    has_violations = bool(violations)
    desirability = int(parsed.get("desirability", 0))
    feasibility = int(parsed.get("feasibility", 0))
    disanalogy = (parsed.get("disanalogy", "") or "").strip()
    has_disanalogy = len(disanalogy) > 5  # anything meaningful (not empty or placeholder)
    metric = (parsed.get("metric", "") or "").strip()
    has_metric = len(metric) > 5

    algorithm_levels = {"ALGORITHM", "HEURISTIC"}

    # Hard gates
    if not structural_match:
        return "SKIP"
    if has_violations:
        return "SKIP"
    if abstraction not in algorithm_levels and abstraction != "FRAMEWORK":
        # THEOREM → SKIP; FRAMEWORK → SKIP (needs too much infra)
        return "SKIP"
    if abstraction not in algorithm_levels:
        # FRAMEWORK: require both high feasibility and desirability
        if feasibility < 2 or desirability < 2:
            return "SKIP"
    if desirability == 0:
        return "SKIP"

    # Missing disanalogy = shallow match → downgrade or skip
    if not has_disanalogy:
        return "SKIP"

    # Verdict from feasibility score
    if feasibility == 2 and has_metric and abstraction in algorithm_levels:
        return "OPTIMIZATION"
    elif feasibility >= 1:
        return "SPIKE"
    else:
        return "SKIP"


def interpret_paper(paper: dict, cat_key: str) -> dict:
    """
    LLM-based interpretation of a math paper for Hermes relevance.

    Uses haiku-4-5 with the category primer as context so it can reason about
    whether a pure mathematics paper (that never mentions 'agent' or 'LLM')
    still has ideas applicable to the Hermes pipeline.

    Returns a dict with:
      result:       OPTIMIZATION | SPIKE | SKIP
      confidence:   high | medium | low
      hypothesis:   str
      metric:       str
      target:       str (Hermes component)
      spike_given / spike_when / spike_then: str
      reasoning:    str
    """
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _llm_client()

    title = paper.get("title", "") or ""
    abstract = paper.get("abstract", "") or ""
    full_text = paper.get("full_text", "") or ""
    primer = paper.get("primer", "") or ""
    components = COMPONENT_MAP.get(cat_key, ["hermes agent pipeline"])
    components_str = "\n".join(f"  - {c}" for c in components)

    # Fast-skip: no title, abstract, or full text — nothing to judge
    if not title and not abstract and not full_text:
        return {
            "result": "SKIP",
            "confidence": "high",
            "reasoning": "No title or abstract available — cannot classify.",
            "hypothesis": "", "metric": "", "target": "",
            "spike_given": "", "spike_when": "", "spike_then": "",
        }

    if full_text:
        paper_body = f"Full text (first 4000 chars):\n{full_text[:4000]}"
    elif abstract:
        paper_body = f"Abstract: {abstract[:1500]}"
    else:
        paper_body = "(no abstract — judge from title only)"

    prompt = f"""You are a senior AI systems engineer evaluating mathematical research papers
for applicability to Hermes, a production multi-model AI agent framework.

Hermes constraints — ABSOLUTE blockers only (gradient computation, weight access, continuous training):
  - NO gradient computation or backpropagation (cannot fine-tune or train models)
  - NO access to model weights or activations
  - NO continuous training signal (cannot update model parameters between turns)

  IMPORTANT — these are NOT blockers. Hermes CAN build infrastructure for:
  - Iterative state accumulation → persist in JSON/SQLite, update each cron run
  - Discrete/tabular structures → represent as Python dicts, graphs, or databases
  - Scoring functions → implement as Python functions run each turn or cron
  - Multi-step algorithms → run as cron jobs, multi-turn loops, or subagents
  - Statistical estimators → compute from session history logs
  - Graph/eigenvalue computation → numpy at inference time (no training needed)
  - UCB/bandit state → update a JSON state file each cron run
  - Sampling procedures → run as background processes
  Default to "can Hermes build infrastructure for this?" before firing a SKIP at Step 3.

FIELD PRIMER (what this math field IS — its objects, operations, and typical results):
NOTE: Use the primer to understand the math, NOT as evidence that the field is relevant.
Shared vocabulary between the primer and Hermes is not a match signal.
{primer[:2000] if primer else "(no primer available)"}

HERMES SYSTEM FACTS (concrete runtime constraints, inject as ground truth):
  - Local-first: no GPU cluster, no distributed training, runs on a single laptop
  - Prompt-only: no weight updates, no fine-tuning, no gradient computation
  - Context = a sequence of text turns, not a vectorized embedding matrix
  - Memory = file/graph retrieval (SQLite, JSON, markdown); not differentiable
  - Skills = markdown documents + tool calls; not a learned policy
  - Can persist arbitrary state (JSON, SQLite, numpy arrays) between runs via cron
  - Can run numpy/scipy at inference time for graph/spectral/statistical computation
  - Can implement bandit/UCB/scoring state as a JSON file updated each cron run
  - Interactive latency target: < 30s per turn; batch/cron jobs have no latency limit
  - No access to model internals (weights, activations, attention maps)

HERMES COMPONENTS this math field could affect (candidate list only, not relevance signal):
{components_str}

PAPER TO EVALUATE:
Title: {title or "(unknown)"}
{paper_body}

CALIBRATION (match strictness; do not copy labels):
SKIP: Tabular RL — Q-learning converges in tabular MDPs. THEOREM; no Hermes parameter. SKIP at Step 1.
SPIKE: Herrmann & Schmidhuber (2605.14831) ranks by future compression progress. ALGORITHM; scored candidates match; needs bit-level K-complexity Hermes lacks. SPIKE (weak).

REASONING CHAIN — work through EACH step in order before the JSON.
Start with disqualifiers (Steps 1, 3). Do NOT form a positive verdict until Step 4 is done.

STEP 0 — CLAIM IN DOMAIN-NEUTRAL LANGUAGE (required, prevents vocabulary anchoring):
  Restate what the paper actually contributes in ONE sentence using NO Hermes words
  (no "agent", "routing", "memory", "context", "skill"). If you cannot do this, SKIP.
  Example: "Proves that greedy set cover finds a (1-1/e) approximation in O(nk) time."
  NOT: "Provides an agent routing optimization for multi-component memory systems."

STEP 1 — ABSTRACTION LEVEL: What is the paper's primary contribution?
  THEOREM: existence/bound proof only, no runnable algorithm → default SKIP
  ALGORITHM: concrete procedure with steps (could be coded today) → SPIKE candidate
    Quote the key invariant/guarantee the steps must preserve (proof-to-code alignment).
    A proof that a parameter exists, without a usable value or computing procedure, is THEOREM not ALGORITHM.
    Asymptotic ranking without named constants is not implementable.
  HEURISTIC: practical rule with empirical validation → OPTIMIZATION candidate
  FRAMEWORK: conceptual architecture needing substantial engineering → default SKIP
  → Companion algorithm rule: appendix algorithm counts ONLY if the PRIMARY
    contribution IS that algorithm. Theorem-primary + appendix algorithm = THEOREM → SKIP.

STEP 3 — FEASIBILITY GATE (ABSOLUTE blockers only — run BEFORE Step 2):
  Only fire if the paper's CORE CONTRIBUTION fundamentally requires:
    (a) Gradient computation / backpropagation / weight updates
    (b) Direct access to model weights or activations
    (c) A continuous online training signal (parameters update every turn)
  Do NOT fire for: discrete structures, iterative algorithms, state accumulation,
  scoring functions, tabular data, sampling, graph computation, eigenvalues —
  Hermes can build infrastructure (JSON state, SQLite, numpy, cron) for all of these.
  State each violated constraint explicitly. Fire SKIP only if (a), (b), or (c) is violated.

STEP 2 — STRUCTURAL ANALOGY (only after Step 3 clears): Name the OBJECT and OPERATION; then a 3-part DISANALOGY.
  Use ONLY this closed object taxonomy (do not invent entries). Object → Hermes counterpart:
    sequence of tokens/turns → context window, session history
    probability distribution (discrete) → skill selection, model routing
    directed graph → skill dependency graph, knowledge graph
    metric/embedding space → memory retrieval, semantic clustering
    set of scored/ranked candidates → spike prioritization list, retrieved memory candidates
    bounded prediction sequence → N subagent verdicts, N tool results, N memory retrievals per turn
  Operation taxonomy: select/argmax/rank; aggregate/combine/ensemble; compress/summarize;
    retrieve/search; schedule/allocate; write/persist.
  BOTH object AND operation must match a Hermes component OR a plausible new Hermes capability.
  Does NOT match: tabular state space; weight matrix/gradients; image/audio; continuous manifold; oracle reward.

STEP 2b — NEW CAPABILITY CHECK (run if Step 2 finds no existing-component match):
  Ask: does the paper's core algorithm or result enable a capability Hermes could ADD — even if
  that capability does not exist today? Examples of valid new capabilities:
    - Formal verification of agent action sequences before execution
    - Causal attribution of session errors to specific memory or skill sources
    - Optimal stopping (when to stop sampling subagents and commit)
    - Information-theoretic compression with provable distortion bounds
    - Online convex optimisation for adaptive per-turn hyperparameters
    - Adversarial robustness certificates for skill-routing decisions
    - Measure-theoretic memory retention policies with concentration guarantees
    - Uncertainty quantification over retrieved facts (calibrated confidence intervals)
  If yes → verdict is SPIKE (new capability prototype needed), target = "new: <short capability name>".
  The disanalogy check still applies — paper must pass all three disanalogy parts.

  REQUIRED DISANALOGY — must pass ALL THREE (else the match is invalid → SKIP):
    (a) Name a LOAD-BEARING assumption AND quote or close-paraphrase it from the paper.
        Load-bearing = if it fails, the paper's core result does not apply.
    (b) Name a specific Hermes property that violates that assumption.
        "Hermes doesn't support X" alone is insufficient.
    (c) The assumption is paper-specific, not universal (not "a model exists" / "has inputs").
  Weak: "it's from a different field" / "paper uses matrix notation". Strong: "assumes i.i.d. samples; Hermes session turns are correlated."



STEP 4 — MEASURABILITY: Name ONE concrete metric that would change in the Hermes codebase.
  Must be a named script output, function result, or observable count.
  "Better quality" → SKIP.  "skill-router recall@5 on a 50-query eval set" → valid.

STEP 5 — SCORES (used by the calling script to compute the verdict):
  desirability: 2=high value if it worked, 1=marginal, 0=no value
  feasibility:  2=all gates pass + measurable, 1=uncertain/needs infra, 0=gates fail

NOTE: The JSON "result" field is IGNORED by the calling script — the script computes
the verdict from desirability, feasibility, abstraction_level, structural_match, and
feasibility_violations. Fill it in as your best guess, but the script overrides it.

Do NOT require the paper to mention agents, LLMs, or AI. Judge structural transfer.
Show step-by-step reasoning inline, then end with a single JSON object (no fences):
{{
  "result": "OPTIMIZATION" | "SPIKE" | "SKIP",
  "confidence": "high" | "medium" | "low",
  "abstraction_level": "THEOREM" | "ALGORITHM" | "HEURISTIC" | "FRAMEWORK",
  "neutral_claim": "<domain-neutral one-sentence claim from Step 0>",
  "object_operation": "<math object> + <math operation>",
  "structural_match": true | false,
  "disanalogy": "<required: one concrete way this does NOT fit Hermes>",
  "feasibility_violations": ["<list of violated constraints, or empty>"],
  "desirability": 0 | 1 | 2,
  "feasibility": 0 | 1 | 2,
  "target": "<most relevant Hermes component from the list above>",
  "reasoning": "<2-3 sentences: what maps, what doesn't, and why>",
  "hypothesis": "<if not SKIP: concrete hypothesis about what would improve>",
  "metric": "<if not SKIP: specific named measurable proxy>",
  "spike_given": "<if SPIKE: current Hermes state>",
  "spike_when": "<if SPIKE: what experiment to run>",
  "spike_then": "<if SPIKE: expected measurable outcome>"
}}"""

    try:
        from anthropic.types import TextBlock as _TB
        msg = _CLIENT.messages.create(
            model="claude-haiku-4-5",
            max_tokens=700,  # Runs only on MAYBE papers (post-prefilter); structured output fits in 700
            timeout=20.0,    # Hard per-call timeout; prevents one hung call from killing the run
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (msg.content[0].text if isinstance(msg.content[0], _TB) else str(msg.content[0])).strip()
        # Strip markdown fences if model adds them
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        # New prompt asks for inline reasoning then JSON — find the LAST valid { } block
        # that contains a "result" key (the first { may appear in prose examples).
        json_positions = [i for i, c in enumerate(raw) if c == '{']
        parsed = None
        for json_start in reversed(json_positions):
            try:
                candidate, _ = json.JSONDecoder().raw_decode(raw, idx=json_start)
                if isinstance(candidate, dict) and "result" in candidate:
                    parsed = candidate
                    break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            # Fallback: try first { block, then truncate at last }
            json_start = raw.find("{")
            if json_start == -1:
                raise ValueError("no JSON object in response")
            try:
                parsed, _ = json.JSONDecoder().raw_decode(raw, idx=json_start)
            except json.JSONDecodeError:
                json_end = raw.rfind("}")
                parsed = json.loads(raw[json_start:json_end + 1]) if json_end > json_start else {}
        # Ensure required keys present
        for k in ("result", "confidence", "abstraction_level", "neutral_claim",
                  "object_operation", "structural_match", "disanalogy",
                  "feasibility_violations", "desirability", "feasibility",
                  "target", "reasoning", "hypothesis", "metric",
                  "spike_given", "spike_when", "spike_then"):
            if k == "structural_match":
                parsed.setdefault(k, False)
            elif k == "feasibility_violations":
                parsed.setdefault(k, [])
            elif k in ("desirability", "feasibility"):
                parsed.setdefault(k, 0)
            else:
                parsed.setdefault(k, "")

        # ── Deterministic verdict (overrides model's self-reported result) ──────
        # Research basis: AutoLR/RAIL pattern — scores computed in code, model
        # only fills structured slots. Eliminates LLM authority-laundering.
        parsed["result"] = _deterministic_verdict(parsed)

        if parsed["result"] not in ("OPTIMIZATION", "SPIKE", "SKIP"):
            parsed["result"] = "SKIP"
        return parsed
    except Exception as e:
        return {
            "result": "SKIP",
            "confidence": "low",
            "reasoning": f"LLM classification error: {e}",
            "hypothesis": "", "metric": "", "target": "",
            "spike_given": "", "spike_when": "", "spike_then": "",
        }


def theorem_ideate(paper: dict, category: str) -> dict | None:
    """Stage 3: theorem-to-implementation ideation for full-chain SKIPs.

    When a paper reaches full chain but is classified SKIP (no direct component
    match found), this stage asks: can we BUILD something new that embodies the
    theorem's mathematical structure, even if no existing Hermes component maps
    to it? Returns a GENERATED_IDEA record or None on error.

    The key difference from SPIKE: a SPIKE means the paper maps to an existing
    Hermes component gap. A GENERATED_IDEA means we are *inventing* a new artifact
    seeded by the theorem's structure — it doesn't exist yet and nothing prompted it
    except the math.
    """
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or paper.get("text", "")[:1000]

    prompt = (
        f"Paper: {title}\n"
        f"Category: {category}\n"
        f"Abstract: {abstract[:600]}\n\n"
        "This paper was SKIP in direct component matching. Your job is STAGE 3: theorem-to-implementation ideation.\n\n"
        "HERMES CONTEXT:\n"
        "  - Hermes is an AI agent framework: prompt-only, local-first, Python scripts, SQLite, numpy, cron jobs, JSON state.\n"
        "  - It has: memory layers (episodic/semantic/procedural), skill routing, tool orchestration, cron scheduling,\n"
        "    context compaction, RAG recall, multi-agent delegation, session management.\n"
        "  - We can BUILD infrastructure: JSON state, SQLite, numpy/scipy, cron loops, Python scripts, CLI tools.\n"
        "  - ABSOLUTE limits only: no gradient computation, no weight updates, no model internals access.\n\n"
        "TASK: Extract the theorem's MATHEMATICAL STRUCTURE (the invariant, bound, operator, or transform at its core).\n"
        "Then propose ONE concrete Hermes artifact that EMBODIES that structure — something we could build in a Python\n"
        "script or skill that uses the same mathematical object.\n\n"
        "Examples of good ideation:\n"
        "  - A fixed-point theorem → a convergence checker for skill-routing scores (iterate until stable)\n"
        "  - A spectral gap bound → an eigenvalue-based session-coherence alarm on memory embeddings\n"
        "  - A Lyapunov function → a session-health monitor that tracks a decreasing energy quantity over turns\n"
        "  - An ergodic theorem → a long-run frequency estimator for tool-call patterns across sessions\n"
        "  - A minimax theorem → a worst-case context-budget allocator under adversarial input length\n\n"
        "If the theorem's structure is truly irreducible (e.g. requires continuous-time dynamics with no discrete analogue,\n"
        "or a topological invariant with no computable embedding), say so briefly and return null.\n\n"
        "Respond in JSON only:\n"
        "{\n"
        "  \"math_structure\": \"<one sentence: the core invariant/operator/bound>\",\n"
        "  \"hermes_artifact\": \"<name of the thing to build, e.g. 'eigenvalue-coherence-alarm.py'>\",\n"
        "  \"artifact_type\": \"<script|skill|config|cron>\",\n"
        "  \"implementation_sketch\": \"<3-5 sentences: what it does, what math object it computes, what data it reads/writes>\",\n"
        "  \"hermes_benefit\": \"<one sentence: concrete improvement to Hermes behaviour>\",\n"
        "  \"null_reason\": \"<empty string unless truly irreducible — then explain why>\"\n"
        "}"
    )
    try:
        from anthropic.types import TextBlock as _TB
        _ideate_client = _CLIENT if _CLIENT else _llm_client()
        msg = _ideate_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=400,
            timeout=15.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (msg.content[0].text if isinstance(msg.content[0], _TB) else str(msg.content[0])).strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        json_start = raw.find("{")
        if json_start == -1:
            return None
        idea = json.loads(raw[json_start:raw.rfind("}") + 1])
        # Discard if model returned null_reason (truly irreducible)
        if idea.get("null_reason", "").strip():
            return None
        if not idea.get("hermes_artifact", "").strip():
            return None
        return idea
    except Exception:
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Math paper interpretation layer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=40, help="Max papers to interpret per run (default 40; two-stage filter at ~5s avg/paper = ~200s, safe under 300s cron budget)")
    parser.add_argument("--input", type=str, default=str(SWEEP_LATEST))
    parser.add_argument("--fetch-abstracts", action="store_true",
                        help="Fetch missing abstracts from arXiv (slower but better)")
    parser.add_argument("--full-text", action="store_true",
                        help="Fetch full paper text from ar5iv (PDF fallback); pass first 4000 chars to LLM")
    args = parser.parse_args()

    # Emit content-addressed run header (arXiv:2608.23610 traceability)
    import subprocess as _sp
    _rh = _sp.run(
        [sys.executable, str(Path("~/.hermes/scripts/run-header.py").expanduser()),
         "--script", "math-paper-interpreter.py",
         "--model", "claude-haiku-4-5",
         "--skill", "hermes-math-research",
         "--note", f"fetch-abstracts={args.fetch_abstracts} full-text={args.full_text} limit={args.limit}"],
        capture_output=True, text=True, timeout=30,
    )
    if _rh.returncode != 0:
        print(f"[math-interpreter] run-header failed: {_rh.stderr.strip()}", file=sys.stderr)
    else:
        print(f"[math-interpreter] run-header: {_rh.stdout.strip()}", file=sys.stderr)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[math-interpreter] input file not found: {input_path} — run hermes-math-sweep.py first", file=sys.stderr)
        sys.exit(1)  # exit 1 so cron treats missing sweep output as an error, not silent success
    sweep = json.loads(input_path.read_text())
    flat = sweep.get("new_papers_flat", [])

    # Filter to math categories only
    math_papers = [p for p in flat if p.get("category") in MATH_CATS]
    print(f"[math-interpreter] {len(math_papers)} math-category papers from sweep", file=sys.stderr)

    # Deduplicate by ID
    seen_ids = set()
    unique = []
    for p in math_papers:
        pid = p.get("id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            unique.append(p)
    print(f"[math-interpreter] {len(unique)} unique after dedup", file=sys.stderr)

    # Seen-paper tracking: advance window each run so we don't re-screen the same papers
    seen_path = CACHE_DIR / "math-seen-papers.json"
    seen_processed: set = set()
    if seen_path.exists():
        try:
            _d = json.loads(seen_path.read_text())
            seen_processed = set(_d.get("seen", []))
        except Exception:
            pass
    unseen = [p for p in unique if p.get("id", "") not in seen_processed]
    if not unseen:
        print("[math-interpreter] All known papers already processed — resetting seen cache", file=sys.stderr)
        seen_processed = set()
        unseen = unique
    print(f"[math-interpreter] {len(unseen)} unseen papers (skipping {len(unique)-len(unseen)} already processed)", file=sys.stderr)

    # Limit to batch size
    batch = unseen[:args.limit]

    # Extract arXiv IDs for abstract fetching
    arxiv_re = re.compile(r'(\d{4}\.\d{4,5})')

    results = []
    spikes = []
    optimizations = []
    generated_ideas = []  # Stage 3 theorem-to-implementation ideas from full-chain SKIPs
    skipped = 0
    _loop_start = time.time()
    _last_i = -1  # tracks last completed paper index for seen-cache write

    for i, paper in enumerate(batch):
        cat = paper.get("category", "")
        title = paper.get("title", "")
        url = paper.get("url", "")
        pid = paper.get("id", url)

        # Try to get abstract / full text
        abstract = paper.get("abstract", "")
        arxiv_m = arxiv_re.search(url or "") or arxiv_re.search(str(pid or ""))
        arxiv_id = arxiv_m.group(1) if arxiv_m else None

        if args.fetch_abstracts and arxiv_id and not abstract:
            if i % 10 == 0:
                print(f"[math-interpreter] Fetching abstracts {i}/{len(unique)}...", file=sys.stderr)
            fetched = fetch_abstract(arxiv_id)
            if fetched["title"]:
                title = title or fetched["title"]
            abstract = fetched["abstract"]
            time.sleep(0.8)

        full_text = ""
        text_source = "abstract" if abstract else "title"
        if args.full_text and arxiv_id:
            if i % 10 == 0:
                print(f"[math-interpreter] Fetching full text {i}/{len(unique)}...", file=sys.stderr)
            ft, src = fetch_full_text(arxiv_id)
            if ft:
                full_text = ft
                text_source = src
            time.sleep(0.8)

        if (i + 1) % 5 == 0 or i == 0:
            _elapsed = time.time() - _loop_start
            print(f"[math-interpreter] Progress: {i+1}/{len(batch)} papers ({_elapsed:.0f}s elapsed)", file=sys.stderr)
            # Budget guard: stop early if < 30s remain in the 270s soft budget
            # Prevents exit 124 by gracefully writing partial results
            _SOFT_BUDGET = 270  # leave 30s for output writing
            if _elapsed > _SOFT_BUDGET:
                print(f"[math-interpreter] Budget guard: {_elapsed:.0f}s > {_SOFT_BUDGET}s — stopping at paper {i+1}/{len(batch)}", file=sys.stderr)
                # Flush ideas queue now so budget-guard exits don't lose generated ideas
                if not args.dry_run and generated_ideas:
                    _iqp = CACHE_DIR / "math-ideas-queue.json"
                    _ei = []
                    if _iqp.exists():
                        try: _ei = json.loads(_iqp.read_text()).get("ideas", [])
                        except Exception: pass
                    _ea = {x.get("hermes_artifact", "") for x in _ei}
                    _ni = [x for x in generated_ideas if x.get("hermes_artifact", "") not in _ea]
                    _tmp__iqp = _iqp.with_suffix('.tmp')
                    _tmp__iqp.write_text(json.dumps({"last_updated": datetime.now(timezone.utc).isoformat(), "total_ideas": len(_ei)+len(_ni), "ideas": _ei+_ni}, indent=2))
                    _tmp__iqp.replace(_iqp)
                    print(f"[math-interpreter] Budget-guard ideas flush: {len(_ni)} new ideas written", file=sys.stderr)
                break

        _last_i = i  # mark this paper as reached (pre-filter or full-chain)

        # ── Two-stage pre-filter (speed fix: max_tokens=5, ~0.8s vs 17s full chain) ──
        # Stage 1: fast SKIP/MAYBE gate — runs on every paper
        # Stage 2: full interpret_paper — runs only on MAYBE (~5-15% of papers)
        # Reduces cron runtime from ~1300s to ~120s for 75 papers. (arXiv:2609.11390 pattern)
        if abstract or title:
            _prefilter_prompt = (
                "Screen this math paper for a prompt-only LLM agent framework (no training, "
                "no weights, no GPU, text-only memory).\n"
                f"Title: {title}\nCategory: {cat}\nAbstract: {abstract[:600]}\n\n"
                "Reply MAYBE if: (A) it improves an existing agent capability (routing, "
                "memory, compression, retrieval, trust, skill selection), OR (B) it could "
                "enable a NEW capability not yet in the framework (e.g. formal plan "
                "verification, causal tracing, optimal information gathering, adversarial "
                "robustness bounds, measure-theoretic compaction, uncertainty quantification, "
                "online convex optimization for adaptive parameters).\n"
        "Hard SKIP only if core contribution requires: (a) gradient computation/backpropagation, "
        "(b) direct model weight access, or (c) continuous per-turn training signal. "
        "Do NOT skip for: iterative algorithms, discrete structures, state accumulation, "
        "scoring functions, graph/eigenvalue computation, bandit state — Hermes can build "
        "infrastructure (JSON, SQLite, numpy, cron) for all of these.\n"
        "Reply with exactly one word: SKIP or MAYBE."
            )
            try:
                _pf_client = _CLIENT if _CLIENT else _llm_client()
                _pf_msg = _pf_client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=5,
                    timeout=10.0,  # Hard per-call timeout for pre-filter gate
                    messages=[{"role": "user", "content": _prefilter_prompt}],
                )
                from anthropic.types import TextBlock as _TB
                _pf_raw = _pf_msg.content[0]
                _pf_verdict = (_pf_raw.text if isinstance(_pf_raw, _TB) else "").strip().upper()
                if "SKIP" in _pf_verdict and "MAYBE" not in _pf_verdict:
                    skipped += 1
                    results.append({
                        "id": pid, "arxiv_id": arxiv_id, "url": url,
                        "title": title or f"[{pid}]", "category": cat,
                        "source": paper.get("source", ""), "citations": paper.get("citations", 0),
                        "text_source": text_source, "result": "SKIP", "confidence": "high",
                        "reasoning": "Pre-filter gate: hard constraint violation detected.",
                        "hypothesis": "", "metric": "", "target": "",
                        "spike_given": "", "spike_when": "", "spike_then": "",
                    })
                    continue
            except Exception:
                pass  # pre-filter error: fall through to full chain

        paper_with_abstract = {**paper, "title": title, "abstract": abstract}
        if full_text:
            paper_with_abstract["full_text"] = full_text
        primer = load_primer(cat)
        if primer:
            paper_with_abstract["primer"] = primer[:2000]  # first 2000 chars as context
        interpretation = interpret_paper(paper_with_abstract, cat)

        record = {
            "id": pid,
            "arxiv_id": arxiv_id,
            "url": url,
            "title": title or f"[{pid}]",
            "category": cat,
            "source": paper.get("source", ""),
            "citations": paper.get("citations", 0),
            "text_source": text_source,
            **interpretation,
        }
        results.append(record)

        if interpretation["result"] == "SPIKE":
            spikes.append(record)
        elif interpretation["result"] == "OPTIMIZATION":
            optimizations.append(record)
        else:
            skipped += 1
            # Stage 3: theorem-to-implementation ideation on full-chain SKIPs
            # Pre-filter SKIPs (hard SKIP) are excluded — only papers that
            # passed Stage 1 but failed Stage 2 matching get ideated.
            if interpretation.get("reasoning", "") != "Pre-filter gate: hard constraint violation detected.":
                idea = theorem_ideate(paper_with_abstract, cat)
                if idea:
                    idea["source_paper_id"] = pid
                    idea["source_title"] = title or f"[{pid}]"
                    idea["source_category"] = cat
                    idea["source_url"] = url
                    generated_ideas.append(idea)
                    print(f"  [Stage 3 IDEA] {idea.get('hermes_artifact','')} — {idea.get('hermes_benefit','')[:80]}", file=sys.stderr)

    # Sort spikes by confidence then citations
    conf_order = {"high": 0, "medium": 1, "low": 2}
    spikes.sort(key=lambda x: (conf_order.get(x["confidence"], 3), -x.get("citations", 0)))
    optimizations.sort(key=lambda x: (conf_order.get(x["confidence"], 3), -x.get("citations", 0)))

    print(f"[math-interpreter] Results: {len(spikes)} spikes, {len(optimizations)} optimizations, {skipped} skipped, {len(generated_ideas)} generated ideas", file=sys.stderr)
    track_skip_rate(len(unique), skipped)

    output = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "sweep_date": sweep.get("sweep_date", ""),
        "math_papers_processed": len(results),  # actual count processed, not total unique (budget guard may stop early)
        "spike_count": len(spikes),
        "optimization_count": len(optimizations),
        "skipped_count": skipped,
        "generated_ideas_count": len(generated_ideas),
        "spikes": spikes,
        "optimizations": optimizations,
        "generated_ideas": generated_ideas,
    }

    spike_queue_output = {
        "run_date": output["run_date"],
        "pending_spikes": [
            {
                "id": s["arxiv_id"] or s["id"],
                "title": s["title"],
                "category": s["category"],
                "target": s["target"],
                "confidence": s["confidence"],
                "given": s["spike_given"],
                "when": s["spike_when"],
                "then": s["spike_then"],
                "structures": s.get("spike_structures", []),
                "url": s["url"],
                "status": "pending",
            }
            for s in spikes
        ],
        "pending_optimizations": [
            {
                "id": o["arxiv_id"] or o["id"],
                "title": o["title"],
                "category": o["category"],
                "target": o["target"],
                "confidence": o["confidence"],
                "hypothesis": o["hypothesis"],
                "metric": o["metric"],
                "opt_type": o.get("opt_type", ""),
                "url": o["url"],
                "status": "pending",
            }
            for o in optimizations
        ],
    }

    if not args.dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _tmp = OUTPUT_LATEST.with_suffix('.tmp')
        _tmp.write_text(json.dumps(output, indent=2))
        _tmp.replace(OUTPUT_LATEST)
        _tmp = SPIKE_QUEUE.with_suffix('.tmp')
        _tmp.write_text(json.dumps(spike_queue_output, indent=2))
        _tmp.replace(SPIKE_QUEUE)
        # Write generated ideas queue
        ideas_queue_path = CACHE_DIR / "math-ideas-queue.json"
        existing_ideas = []
        if ideas_queue_path.exists():
            try:
                existing_ideas = json.loads(ideas_queue_path.read_text()).get("ideas", [])
            except Exception:
                pass
        # Dedupe by hermes_artifact name
        existing_artifacts = {i.get("hermes_artifact", "") for i in existing_ideas}
        new_ideas = [i for i in generated_ideas if i.get("hermes_artifact", "") not in existing_artifacts]
        all_ideas = existing_ideas + new_ideas
        _tmp = ideas_queue_path.with_suffix('.tmp')
        _tmp.write_text(json.dumps({
            "last_updated": output["run_date"],
            "total_ideas": len(all_ideas),
            "ideas": all_ideas,
        }, indent=2))
        _tmp.replace(ideas_queue_path)
        print(f"[math-interpreter] Written: {OUTPUT_LATEST}", file=sys.stderr)
        print(f"[math-interpreter] Spike queue: {SPIKE_QUEUE}", file=sys.stderr)
        if generated_ideas:
            print(f"[math-interpreter] Ideas queue: {ideas_queue_path} ({len(new_ideas)} new, {len(all_ideas)} total)", file=sys.stderr)

        # Update seen-paper cache unconditionally — advance window even if all-SKIP
        # so subsequent runs don't re-screen the same dead batch
        n_processed = _last_i + 1 if _last_i >= 0 else len(batch)
        processed_ids = [p.get("id", "") for p in batch[:n_processed] if p.get("id")]
        seen_processed.update(processed_ids)
        _tmp = seen_path.with_suffix('.tmp')
        _tmp.write_text(json.dumps({"seen": sorted(seen_processed), "last_updated": output["run_date"]}, indent=2))
        _tmp.replace(seen_path)
        print(f"[math-interpreter] Seen cache: {len(seen_processed)} total papers processed across runs", file=sys.stderr)

    # Print digest
    print(f"\n=== Math Paper Interpretation — {output['run_date'][:10]} ===")
    print(f"{len(batch)} papers in batch: {len(spikes)} spikes, {len(optimizations)} optimizations, {skipped} skipped, {len(generated_ideas)} ideas\n")

    if optimizations:
        print("OPTIMIZATIONS (replace existing heuristics):")
        for o in optimizations[:10]:
            print(f"  [{o['confidence'].upper()}] [{o['category']}] {o['title'][:70]}")
            print(f"    Target: {o['target']}")
            print(f"    Hypothesis: {o['hypothesis'][:120]}")
            print()

    if spikes:
        print("SPIKE CANDIDATES (new structures to explore):")
        for s in spikes[:15]:
            print(f"  [{s['confidence'].upper()}] [{s['category']}] {s['title'][:70]}")
            print(f"    Target: {s['target']}")
            print(f"    Given: {s['spike_given']}")
            print(f"    When: {s['spike_when'][:80]}")
            print(f"    Then: {s['spike_then'][:80]}")
            print()

    print(f"Full output: {OUTPUT_LATEST}")
    print(f"Spike queue: {SPIKE_QUEUE}")

    if generated_ideas:
        print(f"\n--- Generated ideas from theorem structures ({len(generated_ideas)} new) ---")
        for idea in generated_ideas[:10]:
            print(f"  [{idea.get('artifact_type','?')}] {idea.get('hermes_artifact','')}")
            print(f"    Math: {idea.get('math_structure','')[:90]}")
            print(f"    Benefit: {idea.get('hermes_benefit','')[:90]}")
            print()


if __name__ == "__main__":
    main()
