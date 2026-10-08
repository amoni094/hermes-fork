#!/usr/bin/env python3
"""
cs-research-sweep.py

Sweeps arXiv and academic sources for CS systems/engineering papers
across 30 ACM CCS-aligned categories useful for improving Hermes.

Usage:
  python3 ~/.hermes/scripts/cs-research-sweep.py [--dry-run] [--limit N]

Output:
  ~/.hermes/cache/research/hermes-cs-sweep-latest.json
  ~/.hermes/cache/research/seen_papers_cs.json  (separate dedup cache)

This script is modelled on hermes-math-sweep.py. It loads hermes-research-sweep.py
as a module but supplies its own CS-specific CATEGORIES and uses a separate seen
cache so CS dedup is independent from the agent and math sweeps.
"""

import sys
import json
import importlib.util
import argparse
from pathlib import Path
from datetime import datetime, timezone

# ── Load the core sweep module ──────────────────────────────────────────────

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

SCRIPTS = Path("~/.hermes/scripts").expanduser()
CACHE   = Path("~/.hermes/cache/research").expanduser()

try:
    sweep = load_module("sweep", SCRIPTS / "hermes-research-sweep.py")
except Exception as e:
    print(f"[cs-research-sweep] ERROR: cannot load hermes-research-sweep.py: {e}", file=sys.stderr)
    sys.exit(1)

# ── CS-specific CATEGORIES ───────────────────────────────────────────────────
# 30 ACM CCS-aligned categories. Each entry matches the shape used by
# hermes-research-sweep.py: {label, arxiv_cats, keywords, s2_query}.

CS_CATEGORIES = {
    # SOFTWARE ENGINEERING / PL
    "software_testing": {
        "label": "Software Testing and Verification",
        "arxiv_cats": ["cs.SE", "cs.PL"],
        "keywords": [
            "fuzzing LLM", "property-based testing", "mutation testing", "test generation",
            "coverage-guided fuzzing", "symbolic execution", "concolic testing",
            "automated test repair", "formal verification software"
        ],
        "s2_query": "software testing verification fuzzing 2026",
    },
    "program_analysis": {
        "label": "Program Analysis and Synthesis",
        "arxiv_cats": ["cs.PL", "cs.SE"],
        "keywords": [
            "static analysis", "abstract interpretation", "program synthesis",
            "code generation LLM", "program repair", "taint analysis",
            "data flow analysis", "pointer analysis", "type inference"
        ],
        "s2_query": "program analysis synthesis repair 2026",
    },
    "pl_design": {
        "label": "Programming Language Design",
        "arxiv_cats": ["cs.PL"],
        "keywords": [
            "type system", "effect system", "gradual typing", "dependent types",
            "domain-specific language", "algebraic effects", "ownership types",
            "session types", "linear types"
        ],
        "s2_query": "programming language type system design 2026",
    },
    "compilers_runtime": {
        "label": "Compilers and Runtime Systems",
        "arxiv_cats": ["cs.PL", "cs.AR"],
        "keywords": [
            "JIT compilation", "IR optimization", "garbage collection", "WebAssembly",
            "MLIR", "LLVM optimization", "ahead-of-time compilation", "register allocation"
        ],
        "s2_query": "compiler optimization runtime JIT 2026",
    },
    "software_architecture": {
        "label": "Software Architecture and Modularity",
        "arxiv_cats": ["cs.SE"],
        "keywords": [
            "microservices", "plugin architecture", "module system", "dependency injection",
            "service mesh", "API design", "software modularity", "component-based"
        ],
        "s2_query": "software architecture modularity microservices 2026",
    },
    "devops_ci": {
        "label": "DevOps and Continuous Integration",
        "arxiv_cats": ["cs.SE"],
        "keywords": [
            "CI/CD pipeline", "containerization", "build systems", "reproducible builds",
            "infrastructure as code", "GitOps", "deployment automation", "DevSecOps"
        ],
        "s2_query": "DevOps CI/CD automation containerization 2026",
    },
    # SYSTEMS / DISTRIBUTED
    "distributed_systems": {
        "label": "Distributed Systems Fundamentals",
        "arxiv_cats": ["cs.DC"],
        "keywords": [
            "consensus protocol", "Raft", "Paxos", "eventual consistency",
            "CRDT", "fault tolerance", "distributed transaction", "two-phase commit",
            "Byzantine fault", "leader election"
        ],
        "s2_query": "distributed systems consensus fault tolerance 2026",
    },
    "operating_systems": {
        "label": "Operating Systems",
        "arxiv_cats": ["cs.OS", "cs.DC"],
        "keywords": [
            "OS scheduling", "memory management", "filesystem", "kernel design",
            "container isolation", "cgroups", "eBPF", "unikernel", "real-time OS"
        ],
        "s2_query": "operating systems scheduling memory kernel 2026",
    },
    "computer_architecture": {
        "label": "Computer Architecture",
        "arxiv_cats": ["cs.AR"],
        "keywords": [
            "cache hierarchy", "NUMA", "vectorization SIMD", "RISC-V",
            "heterogeneous computing", "memory bandwidth", "prefetching hardware",
            "branch prediction", "out-of-order execution"
        ],
        "s2_query": "computer architecture memory cache performance 2026",
    },
    "parallel_concurrent": {
        "label": "Parallel and Concurrent Programming",
        "arxiv_cats": ["cs.DC", "cs.PL"],
        "keywords": [
            "lock-free data structure", "transactional memory", "async await",
            "actor model", "SPMD programming", "parallelism abstraction",
            "race condition detection", "memory model"
        ],
        "s2_query": "parallel concurrent programming lock-free 2026",
    },
    "cloud_serverless": {
        "label": "Cloud Computing and Serverless",
        "arxiv_cats": ["cs.DC", "cs.NI"],
        "keywords": [
            "serverless computing", "function as a service", "auto-scaling",
            "cold start optimization", "multi-cloud", "spot instance scheduling",
            "container orchestration", "Kubernetes resource management"
        ],
        "s2_query": "cloud serverless function latency scaling 2026",
    },
    "edge_embedded": {
        "label": "Edge and Embedded Systems",
        "arxiv_cats": ["cs.DC", "cs.AR"],
        "keywords": [
            "edge computing", "TinyML", "IoT protocol", "embedded AI",
            "energy-efficient inference", "model compression embedded",
            "RTOS", "microcontroller ML"
        ],
        "s2_query": "edge computing embedded TinyML energy efficiency 2026",
    },
    # SECURITY / PRIVACY
    "cryptography_eng": {
        "label": "Cryptography Engineering",
        "arxiv_cats": ["cs.CR"],
        "keywords": [
            "post-quantum cryptography", "TLS implementation", "key management",
            "threshold signature", "zero-knowledge proof system", "homomorphic encryption",
            "cryptographic protocol", "secure channel"
        ],
        "s2_query": "cryptography engineering post-quantum TLS 2026",
    },
    "system_security": {
        "label": "System Security",
        "arxiv_cats": ["cs.CR"],
        "keywords": [
            "sandboxing", "privilege separation", "supply chain security",
            "exploit mitigation", "trusted execution environment", "TEE",
            "memory safety", "control flow integrity", "fuzzing vulnerability"
        ],
        "s2_query": "system security sandboxing privilege exploit 2026",
    },
    "privacy_engineering": {
        "label": "Privacy Engineering",
        "arxiv_cats": ["cs.CR"],
        "keywords": [
            "differential privacy application", "GDPR technical compliance",
            "k-anonymity", "data minimization", "privacy-preserving ML",
            "anonymization", "re-identification risk"
        ],
        "s2_query": "privacy engineering differential privacy compliance 2026",
    },
    "secure_mpc": {
        "label": "Secure Multi-Party Computation",
        "arxiv_cats": ["cs.CR"],
        "keywords": [
            "secure multi-party computation", "MPC protocol", "homomorphic encryption",
            "secret sharing", "oblivious RAM", "private information retrieval"
        ],
        "s2_query": "secure multi-party computation MPC protocol 2026",
    },
    "network_security": {
        "label": "Network Security",
        "arxiv_cats": ["cs.CR", "cs.NI"],
        "keywords": [
            "intrusion detection system", "protocol analysis", "zero-trust",
            "VPN security", "DDoS mitigation", "network anomaly detection",
            "firewall policy"
        ],
        "s2_query": "network security intrusion detection zero-trust 2026",
    },
    # DATA MANAGEMENT
    "database_systems": {
        "label": "Database Systems",
        "arxiv_cats": ["cs.DB"],
        "keywords": [
            "query optimization", "MVCC", "columnar storage", "vector database",
            "LSM-tree", "B-tree optimization", "learned index", "database concurrency",
            "distributed SQL", "OLAP performance"
        ],
        "s2_query": "database query optimization vector storage 2026",
    },
    "data_streaming": {
        "label": "Data Streaming and Processing",
        "arxiv_cats": ["cs.DB", "cs.DC"],
        "keywords": [
            "stream processing", "windowing operator", "exactly-once semantics",
            "Flink optimization", "Kafka consumer", "stateful stream", "CEP"
        ],
        "s2_query": "stream processing exactly-once stateful 2026",
    },
    "information_retrieval": {
        "label": "Information Retrieval",
        "arxiv_cats": ["cs.IR"],
        "keywords": [
            "dense retrieval", "BM25", "hybrid search", "re-ranking", "learned index",
            "retrieval augmented generation", "bi-encoder", "cross-encoder",
            "embedding retrieval", "BEIR benchmark"
        ],
        "s2_query": "information retrieval dense retrieval hybrid search 2026",
    },
    "knowledge_representation": {
        "label": "Knowledge Representation and Reasoning",
        "arxiv_cats": ["cs.AI", "cs.DB"],
        "keywords": [
            "knowledge graph", "ontology engineering", "RDF OWL", "SPARQL optimization",
            "entity linking", "relation extraction", "knowledge base construction",
            "description logic"
        ],
        "s2_query": "knowledge graph ontology reasoning 2026",
    },
    # HCI
    "ui_design": {
        "label": "User Interface Design",
        "arxiv_cats": ["cs.HC"],
        "keywords": [
            "accessibility WCAG", "usability evaluation", "responsive design",
            "UI testing", "user study", "interaction design", "adaptive UI"
        ],
        "s2_query": "user interface design accessibility usability 2026",
    },
    "conversational_ai": {
        "label": "Conversational AI and Dialogue Systems",
        "arxiv_cats": ["cs.CL", "cs.HC"],
        "keywords": [
            "task-oriented dialogue", "dialogue state tracking", "slot filling",
            "intent detection", "NLU pipeline", "conversation management",
            "end-to-end dialogue", "response generation"
        ],
        "s2_query": "conversational AI task-oriented dialogue state tracking 2026",
    },
    "collaborative_systems": {
        "label": "Collaborative Systems",
        "arxiv_cats": ["cs.HC", "cs.DC"],
        "keywords": [
            "operational transformation", "CRDT collaboration", "real-time collaboration",
            "conflict resolution shared document", "version control UX",
            "pair programming tool"
        ],
        "s2_query": "collaborative systems operational transformation CRDT 2026",
    },
    # NETWORKS
    "network_protocols": {
        "label": "Network Protocols",
        "arxiv_cats": ["cs.NI"],
        "keywords": [
            "QUIC protocol", "HTTP/3", "TCP congestion control", "BGP routing",
            "named data networking", "transport protocol", "low-latency network"
        ],
        "s2_query": "network protocol QUIC transport latency 2026",
    },
    "wireless_mobile": {
        "label": "Wireless and Mobile Networks",
        "arxiv_cats": ["cs.NI"],
        "keywords": [
            "5G optimization", "WiFi 6", "mesh networking", "mobile protocol",
            "handoff optimization", "resource allocation wireless"
        ],
        "s2_query": "wireless mobile network 5G protocol optimization 2026",
    },
    "content_delivery": {
        "label": "Content Delivery and Caching",
        "arxiv_cats": ["cs.NI", "cs.DC"],
        "keywords": [
            "CDN design", "cache eviction policy", "edge caching", "prefetching",
            "cache coherence", "content-aware caching", "TTL optimization"
        ],
        "s2_query": "CDN caching content delivery prefetching 2026",
    },
    # EMERGING
    "quantum_systems": {
        "label": "Quantum Computing Systems",
        "arxiv_cats": ["cs.ET", "quant-ph"],
        "keywords": [
            "quantum error correction", "variational quantum algorithm",
            "quantum software stack", "quantum circuit optimization",
            "NISQ algorithm", "quantum resource estimation"
        ],
        "s2_query": "quantum computing systems error correction software 2026",
    },
    "neuromorphic": {
        "label": "Neuromorphic and Novel Computing",
        "arxiv_cats": ["cs.ET", "cs.AR"],
        "keywords": [
            "spiking neural network hardware", "in-memory computing",
            "photonic computing", "neuromorphic chip", "analog computing AI"
        ],
        "s2_query": "neuromorphic computing spiking in-memory 2026",
    },
    "formal_specification": {
        "label": "Formal Specification and Model Checking",
        "arxiv_cats": ["cs.LO", "cs.SE"],
        "keywords": [
            "TLA+ specification", "Alloy model checking", "Coq proof",
            "verified compiler", "seL4 microkernel", "formal invariant",
            "model checking distributed", "proof assistant"
        ],
        "s2_query": "formal specification model checking TLA+ verified 2026",
    },
}

# Core sweep (hermes-research-sweep.py) iterates cat["queries"].
# CS cats are defined with keywords + s2_query; map them so run_sweep() works.
for _cat in CS_CATEGORIES.values():
    if "queries" not in _cat:
        kws = list(_cat.get("keywords") or [])
        s2 = (_cat.get("s2_query") or "").strip()
        qs = kws[:5]
        if s2 and s2 not in qs:
            qs = (qs[:4] + [s2]) if len(qs) >= 5 else qs + [s2]
        _cat["queries"] = qs or [s2 or _cat["label"]]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would run, no API calls")
    parser.add_argument("--limit", type=int, default=0, help="Max papers to process (0=all)")
    args = parser.parse_args()

    print(f"[hermes-cs-sweep] CS sweep: {len(CS_CATEGORIES)} categories")
    print(f"[hermes-cs-sweep] Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would sweep categories:")
        for k, v in sorted(CS_CATEGORIES.items()):
            print(f"  {k}: {v['arxiv_cats']} — {len(v['keywords'])} keywords")
        return

    # Temporarily patch sweep module to use CS cats + separate seen cache
    original_cats     = sweep.CATEGORIES
    original_seen     = sweep.SEEN_FILE
    original_output   = sweep.OUTPUT_LATEST
    original_dated    = sweep.OUTPUT_DATED

    sweep.CATEGORIES  = CS_CATEGORIES
    sweep.SEEN_FILE   = CACHE / "seen_papers_cs.json"
    sweep.OUTPUT_LATEST = CACHE / "hermes-cs-sweep-latest.json"
    sweep.OUTPUT_DATED  = CACHE / f"hermes-cs-sweep-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"

    # Suppress ALL listing-page harvests for the CS sweep — they run the parent sweep's
    # listing harvester which hard-codes category="reasoning_planning" for cs.AI/cs.CL
    # results, flooding the output with non-CS papers. Keyword searches drive CS coverage.
    original_listings = sweep.sweep_arxiv_listings
    sweep.sweep_arxiv_listings = lambda arxiv_cats: []

    try:
        all_papers, new_papers = sweep.run_sweep()
    finally:
        sweep.CATEGORIES           = original_cats
        sweep.SEEN_FILE            = original_seen
        sweep.OUTPUT_LATEST        = original_output
        sweep.OUTPUT_DATED         = original_dated
        sweep.sweep_arxiv_listings = original_listings

    # Post-filter: drop any paper whose category isn't a known CS category key.
    # Off-topic papers slip in when the parent sweep's dedup logic tags them with its
    # own categories (reasoning_planning, multilingual_fr, trending, etc.).
    valid_cs_cats = set(CS_CATEGORIES.keys())
    all_papers  = [p for p in all_papers  if p.get("category") in valid_cs_cats]
    new_papers  = [p for p in new_papers  if p.get("category") in valid_cs_cats]

    print(f"[hermes-cs-sweep] Done: {len(new_papers)} new CS papers ({len(all_papers)} total, after category filter)")

    # Save a CS-specific timestamped output
    cs_out = CACHE / "hermes-cs-sweep-latest.json"
    _cs_tmp = cs_out.with_suffix(".tmp")
    _cs_tmp.write_text(json.dumps({
        "sweep_date": datetime.now(timezone.utc).isoformat(),
        "new_paper_count": len(new_papers),
        "new_papers_flat": new_papers,
        "all_papers": all_papers,
    }, indent=2, default=str))
    _cs_tmp.replace(cs_out)
    print(f"[hermes-cs-sweep] Saved: {cs_out}")


if __name__ == "__main__":
    main()
