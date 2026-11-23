#!/usr/bin/env python3
"""
cs-primers-overnight.py

Generates primer files for each CS research category used by cs-paper-interpreter.py.
Primers provide category context so the interpreter can make better SYSTEMS-APPLICABLE /
SPIKE / SKIP decisions without loading a large model every time.

Each primer is ~800 words covering:
  - What this CS category is (core concepts, methods)
  - Why it's relevant to Hermes (concrete component analogues)
  - Key terminology the interpreter needs to recognise
  - Representative techniques / algorithms to watch for

Usage:
  python3 ~/.hermes/scripts/cs-primers-overnight.py           # generate missing primers
  python3 ~/.hermes/scripts/cs-primers-overnight.py --force   # regenerate all
  python3 ~/.hermes/scripts/cs-primers-overnight.py --category software_testing
  python3 ~/.hermes/scripts/cs-primers-overnight.py --list    # list primer status

Output:
  ~/.hermes/cache/research/cs-primers/<category_key>.txt
  ~/.hermes/cache/research/cs-primers/INDEX.txt
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PRIMERS_DIR = Path("~/.hermes/cache/research/cs-primers").expanduser()
PRIMERS_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = PRIMERS_DIR / "INDEX.txt"

# ── Category definitions ──────────────────────────────────────────────────────

# Each entry: (label, hermes_relevance_tier, key_concepts, hermes_analogues)
CS_PRIMER_SPECS = {
    "software_testing": (
        "Software Testing and Verification",
        "HIGH",
        ["fuzzing", "property-based testing", "mutation testing", "coverage-guided fuzzing",
         "symbolic execution", "concolic testing", "automated test repair", "test generation LLM",
         "regression testing", "differential testing", "oracle problem", "AFL", "LibFuzzer"],
        ["skill test harness: verifying skill outputs are correct",
         "agent output verification: asserting tool call sequences match spec",
         "regression baseline: detect if a patch breaks existing behaviour"],
    ),
    "program_analysis": (
        "Program Analysis and Synthesis",
        "HIGH",
        ["static analysis", "abstract interpretation", "data flow analysis",
         "taint analysis", "pointer analysis", "type inference", "program synthesis",
         "code generation", "program repair", "decompilation", "LLVM IR", "AST analysis"],
        ["skill dependency graph analysis: find which skills call which",
         "tool output validation: static checks on tool result shapes",
         "code generation quality: analysing LLM-generated code for bugs"],
    ),
    "pl_design": (
        "Programming Language Design",
        "MED",
        ["type system", "effect system", "dependent types", "gradual typing",
         "linear types", "session types", "ownership types", "algebraic effects",
         "domain-specific language", "type inference", "subtyping", "polymorphism"],
        ["structured output schemas: typed contracts for tool call outputs",
         "skill authoring DSL: a mini-language for expressing skill workflows",
         "tool parameter types: grounding tool schemas in type theory"],
    ),
    "compilers_runtime": (
        "Compilers and Runtime Systems",
        "MED",
        ["JIT compilation", "AOT compilation", "register allocation", "IR optimisation",
         "garbage collection", "WebAssembly", "MLIR", "LLVM", "bytecode", "inlining",
         "loop optimisation", "profile-guided optimisation", "memory safety compiler"],
        ["Hermes venv startup time: faster Python startup via compiled entrypoints",
         "tool call latency: reduce overhead in the hot dispatch path",
         "context compression: compiler-style IR for compacting context windows"],
    ),
    "software_architecture": (
        "Software Architecture and Modularity",
        "HIGH",
        ["microservices", "plugin architecture", "module system", "dependency injection",
         "service mesh", "API design", "hexagonal architecture", "CQRS", "event sourcing",
         "component-based design", "interface segregation", "coupling metrics"],
        ["plugin architecture: how Hermes skills and tools are composed",
         "toolset modularity: isolating tool concerns into discrete plugins",
         "skill layering: skill families as architectural boundaries"],
    ),
    "devops_ci": (
        "DevOps and Continuous Integration",
        "HIGH",
        ["CI/CD pipeline", "containerisation", "reproducible builds", "GitOps",
         "infrastructure as code", "deployment automation", "DevSecOps", "rollback",
         "blue-green deployment", "canary release", "build cache", "hermetic build"],
        ["hermes CI pipeline: automated skill validation on PR",
         "skill deployment: safe rollout of skill patches",
         "cron job automation: reproducible script deployment"],
    ),
    "distributed_systems": (
        "Distributed Systems Fundamentals",
        "HIGH",
        ["consensus", "Raft", "Paxos", "eventual consistency", "CRDT", "fault tolerance",
         "distributed transaction", "two-phase commit", "Byzantine fault", "leader election",
         "CAP theorem", "linearisability", "causal consistency", "vector clocks"],
        ["delegate_task fault tolerance: what happens when a subagent crashes",
         "cron job reliability: exactly-once delivery guarantees",
         "multi-agent coordination: ordering guarantees between parallel agents"],
    ),
    "operating_systems": (
        "Operating Systems",
        "MED",
        ["scheduling", "preemption", "cgroups", "namespaces", "eBPF", "unikernel",
         "memory management", "virtual memory", "page table", "filesystem journaling",
         "real-time OS", "priority inversion", "lock contention", "syscall overhead"],
        ["async agent loop scheduling: cron priority and preemption",
         "resource isolation: sandboxing tool execution via cgroups",
         "eBPF hooks: low-overhead tracing of agent tool calls"],
    ),
    "computer_architecture": (
        "Computer Architecture",
        "MED",
        ["cache hierarchy", "NUMA", "vectorisation", "SIMD", "RISC-V", "branch prediction",
         "out-of-order execution", "memory bandwidth", "prefetching", "pipeline stall",
         "heterogeneous computing", "GPU memory hierarchy", "DRAM latency"],
        ["embedding computation speed: cache-aware context ops",
         "parallel tool execution: NUMA-aware data placement",
         "inference throughput: memory bandwidth utilisation"],
    ),
    "parallel_concurrent": (
        "Parallel and Concurrent Programming",
        "MED",
        ["lock-free data structure", "compare-and-swap", "transactional memory",
         "actor model", "CSP", "async/await", "SPMD", "race condition", "memory model",
         "linearisability", "obstruction-freedom", "work-stealing scheduler"],
        ["parallel tool execution: safe concurrent tool calls",
         "thread safety in delegate_task: shared state between subagents",
         "lock-free skill routing: contention-free index lookups"],
    ),
    "cloud_serverless": (
        "Cloud Computing and Serverless",
        "MED",
        ["serverless", "function-as-a-service", "cold start", "auto-scaling",
         "multi-cloud", "spot instance", "container orchestration", "Kubernetes",
         "resource provisioning", "SLO", "billing model", "event-driven architecture"],
        ["Hermes cloud deploy: running Hermes in a serverless environment",
         "agent worker scaling: auto-scaling based on task queue depth",
         "cold start optimisation: faster agent initialisation"],
    ),
    "edge_embedded": (
        "Edge and Embedded Systems",
        "MED",
        ["TinyML", "IoT protocol", "embedded AI", "model compression",
         "energy efficiency", "RTOS", "microcontroller", "edge inference",
         "quantisation", "pruning for embedded", "federated edge learning"],
        ["Hermes on Termux/mobile: lightweight operation on Pixel 8a",
         "model routing to small local models: edge inference patterns",
         "battery-aware agent scheduling: energy-efficient cron"],
    ),
    "cryptography_eng": (
        "Cryptography Engineering",
        "MED",
        ["post-quantum cryptography", "TLS", "key management", "threshold signature",
         "zero-knowledge proof", "homomorphic encryption", "cryptographic protocol",
         "HMAC", "key derivation", "certificate management", "secure channel"],
        ["API key management: secure credential rotation patterns",
         "Hermes gateway TLS: transport security configuration",
         "l1-tracegrant HMAC: decision hash integrity verification"],
    ),
    "system_security": (
        "System Security",
        "HIGH",
        ["sandboxing", "privilege separation", "supply chain security", "TEE",
         "memory safety", "control flow integrity", "ASLR", "exploit mitigation",
         "fuzzing vulnerability", "CVE analysis", "least privilege", "seccomp"],
        ["sandboxed code execution: isolating tool execution environment",
         "tool privilege separation: per-tool capability grants",
         "supply chain security: verifying skill and script provenance"],
    ),
    "privacy_engineering": (
        "Privacy Engineering",
        "HIGH",
        ["differential privacy", "GDPR", "k-anonymity", "l-diversity",
         "data minimisation", "privacy-preserving ML", "anonymisation",
         "re-identification risk", "consent management", "PII detection"],
        ["memory data minimisation: pruning PII from Hindsight and Graphiti",
         "PII handling in tools: redaction before storage",
         "GDPR-compliant memory TTL: right-to-erasure implementation"],
    ),
    "secure_mpc": (
        "Secure Multi-Party Computation",
        "MED",
        ["MPC protocol", "secret sharing", "oblivious RAM", "ORAM",
         "private information retrieval", "garbled circuit", "GMW protocol",
         "threshold cryptography", "function secret sharing"],
        ["federated memory with privacy: multi-party skill evaluation without sharing raw data",
         "private skill retrieval: retrieve skills without revealing query to server"],
    ),
    "network_security": (
        "Network Security",
        "MED",
        ["intrusion detection", "zero-trust", "firewall policy", "DDoS mitigation",
         "network anomaly detection", "TLS inspection", "DNS security", "VPN security",
         "lateral movement", "network segmentation", "SIEM"],
        ["gateway transport security: Hermes gateway hardening",
         "webhook auth: validating incoming event signatures",
         "zero-trust for tool calls: deny-by-default network access"],
    ),
    "database_systems": (
        "Database Systems",
        "HIGH",
        ["query optimisation", "MVCC", "columnar storage", "vector database",
         "LSM-tree", "B-tree", "learned index", "OLAP", "distributed SQL",
         "transaction isolation", "write-ahead log", "buffer pool management"],
        ["hermes_state.db query optimisation: faster state reads",
         "vector DB for skill retrieval: ANN search for skill matching",
         "memory TTL database: efficient expired-entry purging"],
    ),
    "data_streaming": (
        "Data Streaming and Processing",
        "MED",
        ["stream processing", "windowing", "exactly-once semantics", "Flink",
         "Kafka", "stateful streaming", "CEP", "watermarks", "late data",
         "backpressure", "checkpointing", "event time vs processing time"],
        ["session event streaming: real-time tool call event delivery",
         "cron output delivery: exactly-once digest delivery",
         "live research feed: streaming arXiv updates as they arrive"],
    ),
    "information_retrieval": (
        "Information Retrieval",
        "HIGH",
        ["dense retrieval", "BM25", "hybrid search", "re-ranking", "bi-encoder",
         "cross-encoder", "BEIR", "embedding retrieval", "learned sparse retrieval",
         "query expansion", "relevance feedback", "RAG", "ColBERT", "DPR"],
        ["skill retrieval ranking: finding the most relevant skill for a trigger",
         "memory semantic search: Hindsight retrieval optimisation",
         "hybrid search for research: combining keyword + embedding for sweep triage"],
    ),
    "knowledge_representation": (
        "Knowledge Representation and Reasoning",
        "HIGH",
        ["knowledge graph", "ontology", "RDF", "OWL", "SPARQL", "entity linking",
         "relation extraction", "description logic", "knowledge base construction",
         "triple store", "property graph", "taxonomy", "schema.org"],
        ["Graphiti KG schema: entity/edge schema design for agent memory",
         "skill taxonomy ontology: formal hierarchy of skill families",
         "entity linking in memory: resolving the same entity across sessions"],
    ),
    "ui_design": (
        "User Interface Design",
        "MED",
        ["accessibility", "WCAG", "usability evaluation", "responsive design",
         "UI testing", "user study", "interaction design", "adaptive UI",
         "cognitive load", "affordance", "progressive disclosure"],
        ["Hermes TUI accessibility: keyboard-navigable terminal interface",
         "dashboard usability: local dashboard layout and information hierarchy",
         "Galina LXQt UI: low-complexity UI patterns for low-tech-confidence users"],
    ),
    "conversational_ai": (
        "Conversational AI and Dialogue Systems",
        "HIGH",
        ["task-oriented dialogue", "dialogue state tracking", "slot filling",
         "intent detection", "NLU", "end-to-end dialogue", "response generation",
         "conversation management", "out-of-domain detection", "DST", "belief state"],
        ["intent detection in CLI: classifying user requests to skills",
         "dialogue state in gateway: tracking multi-turn conversation context",
         "out-of-domain recovery: handling requests Hermes can't handle"],
    ),
    "collaborative_systems": (
        "Collaborative Systems",
        "MED",
        ["operational transformation", "CRDT", "real-time collaboration",
         "conflict resolution", "shared document", "version control UX",
         "synchronous collaboration", "awareness", "co-editing", "merge algorithm"],
        ["multi-agent coordination: merging parallel subagent outputs",
         "shared session state: concurrent skill edits from multiple agents",
         "version control UX: presenting skill diff/merge to user clearly"],
    ),
    "network_protocols": (
        "Network Protocols",
        "MED",
        ["QUIC", "HTTP/3", "HTTP/2", "TCP congestion control", "BGP", "OSPF",
         "named data networking", "transport protocol", "flow control",
         "multiplexing", "head-of-line blocking", "network coding"],
        ["Hermes gateway protocol: transport choice for CLI↔gateway",
         "webhook streaming: HTTP/2 server-sent events vs WebSocket",
         "research API efficiency: QUIC for arXiv/S2 batch queries"],
    ),
    "wireless_mobile": (
        "Wireless and Mobile Networks",
        "MED",
        ["5G", "WiFi 6", "mesh networking", "handoff", "resource allocation",
         "beamforming", "OFDM", "energy harvesting", "mobile protocol",
         "spectrum management"],
        ["Termux/mobile reliability: Hermes behaviour on cellular + WiFi transitions",
         "Pixel 8a agent scheduling: battery-aware on-device tasks"],
    ),
    "content_delivery": (
        "Content Delivery and Caching",
        "MED",
        ["CDN", "cache eviction", "LRU", "LFU", "ARC", "edge caching",
         "prefetching", "TTL", "content-aware caching", "cache coherence",
         "cache warming", "write-through vs write-back"],
        ["skill content caching: caching rendered skill content between loads",
         "primer cache eviction: TTL and eviction policy for CS/math primers",
         "research result caching: avoiding redundant arXiv API calls"],
    ),
    "quantum_systems": (
        "Quantum Computing Systems",
        "LOW",
        ["quantum error correction", "variational quantum algorithm", "NISQ",
         "quantum circuit optimisation", "quantum software stack",
         "qubit", "quantum advantage", "surface code", "quantum memory"],
        ["future compute substrate: when quantum co-processors become available",
         "quantum-safe crypto migration: post-quantum TLS/key exchange"],
    ),
    "neuromorphic": (
        "Neuromorphic and Novel Computing",
        "LOW",
        ["spiking neural network", "in-memory computing", "photonic computing",
         "analog computing", "neuromorphic chip", "memristor", "event-driven inference",
         "Loihi", "BrainScaleS"],
        ["energy-efficient inference: neuromorphic patterns for edge models",
         "novel hardware routing: routing to neuromorphic co-processors"],
    ),
    "formal_specification": (
        "Formal Specification and Model Checking",
        "HIGH",
        ["TLA+", "Alloy", "model checking", "Coq", "Isabelle", "Lean",
         "seL4", "verified compiler", "formal invariant", "temporal logic",
         "LTL", "CTL", "refinement", "proof assistant", "bounded model checking"],
        ["agent loop invariants: formally specifying cron loop termination",
         "verified tool contracts: pre/post conditions on tool calls",
         "skill correctness: Alloy model of skill trigger exclusivity"],
    ),
}


def load_api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "")


def call_api(prompt: str) -> str:
    """Call Anthropic API to generate primer text."""
    api_key = load_api_key()
    if not api_key:
        return ""
    try:
        import urllib.request
        payload = json.dumps({
            "model": "claude-haiku-4-5",
            "max_tokens": 1200,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
        return result["content"][0]["text"].strip()
    except Exception as e:
        print(f"  [warn] API error: {e}", file=sys.stderr)
        return ""


def make_primer_prompt(key: str, label: str, tier: str,
                       concepts: list, analogues: list) -> str:
    concepts_str = ", ".join(concepts[:10])
    analogues_str = "\n".join(f"  - {a}" for a in analogues)
    return f"""Write a concise technical primer for a category of computer science research.
This primer will be used by an AI interpreter (Hermes) to classify academic papers and
decide whether each paper is applicable to improving the Hermes agent system.

Category: {label} (key: {key})
Hermes relevance tier: {tier}

Key concepts / techniques to cover (include these):
  {concepts_str}

Known Hermes analogues (what components in Hermes are relevant):
{analogues_str}

Write the primer in plain text (no markdown headers). Structure:
1. One paragraph: what this CS domain is, its core problems and methods.
2. One paragraph: why papers in this domain are relevant to Hermes specifically — name the
   actual Hermes components (skills, scripts, cron jobs, memory pipeline, plugin system).
3. A dense terminology list: the 15-20 most important terms an interpreter needs to
   recognise to classify papers correctly. Format: TERM — brief meaning.
4. One paragraph: what a HIGH-value paper in this domain looks like for Hermes
   (concrete system result, measurable improvement, implementation path).

Keep the total under 900 words. Be specific and direct. No filler."""


def make_fallback_primer(key: str, label: str, tier: str,
                         concepts: list, analogues: list) -> str:
    """Generate a static primer without API call."""
    concepts_str = "\n".join(f"  - {c}" for c in concepts)
    analogues_str = "\n".join(f"  - {a}" for a in analogues)
    return f"""CS Category: {label}
Hermes Relevance Tier: {tier}
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} (static fallback — no API key)

CORE DOMAIN
{label} covers a set of computer science problems and techniques. Papers in this category
address foundational and applied problems using both theoretical and empirical methods.

HERMES RELEVANCE
Papers in this category may improve the following Hermes components:
{analogues_str}

KEY CONCEPTS (terms to recognise in paper titles/abstracts):
{concepts_str}

HIGH-VALUE PAPER CHARACTERISTICS
A high-value paper for Hermes has: (1) a concrete implementation or system prototype,
(2) measurable results (latency, reliability, accuracy), (3) a technique that maps to
an existing Hermes component, and (4) an implementation path that doesn't require
training a new model.

NOTE: This primer was generated without an Anthropic API key. For richer context,
set ANTHROPIC_API_KEY and re-run with --force.
"""


def generate_primer(key: str, force: bool = False) -> bool:
    """Generate primer for a single category. Returns True if written."""
    primer_path = PRIMERS_DIR / f"{key}.txt"

    if primer_path.exists() and not force:
        print(f"  [{key}] EXISTS — skip (use --force to regenerate)")
        return False

    spec = CS_PRIMER_SPECS.get(key)
    if not spec:
        print(f"  [{key}] UNKNOWN category key — skip", file=sys.stderr)
        return False

    label, tier, concepts, analogues = spec
    print(f"  [{key}] Generating primer for: {label} (tier={tier})")

    api_key = load_api_key()
    if api_key:
        prompt = make_primer_prompt(key, label, tier, concepts, analogues)
        text = call_api(prompt)
        if not text:
            print(f"  [{key}] API returned empty; using fallback")
            text = make_fallback_primer(key, label, tier, concepts, analogues)
    else:
        text = make_fallback_primer(key, label, tier, concepts, analogues)

    header = (f"# CS Primer: {label}\n"
              f"# Key: {key} | Tier: {tier}\n"
              f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n")
    primer_path.write_text(header + text, encoding="utf-8")
    print(f"  [{key}] Written: {primer_path.name} ({len(text)} chars)")
    return True


def update_index():
    """Write INDEX.txt listing all primer files with generation date."""
    lines = [f"CS Primers Index — updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"]
    for key in sorted(CS_PRIMER_SPECS.keys()):
        label, tier, _, _ = CS_PRIMER_SPECS[key]
        primer_path = PRIMERS_DIR / f"{key}.txt"
        if primer_path.exists():
            mtime = datetime.fromtimestamp(primer_path.stat().st_mtime, tz=timezone.utc)
            status = f"OK  {mtime.strftime('%Y-%m-%d')}"
        else:
            status = "MISSING"
        lines.append(f"  {status}  [{tier:4}]  {key:<30}  {label}")
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nIndex updated: {INDEX_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", help="Generate/regenerate a single category primer")
    parser.add_argument("--force", action="store_true", help="Overwrite existing primers")
    parser.add_argument("--list", action="store_true", help="List primer status and exit")
    parser.add_argument("--clean", action="store_true",
                        help="Remove primer files whose category key is no longer in CS_PRIMER_SPECS. "
                             "Safe to run after category removals; prints what it would delete first.")
    parser.add_argument("--yes", action="store_true",
                        help="Skip interactive confirmation for --clean (safe for cron/unattended use).")
    args = parser.parse_args()

    if args.clean:
        known_keys = set(CS_PRIMER_SPECS.keys())
        stale = [p for p in PRIMERS_DIR.glob("*.txt")
                 if p.stem not in known_keys and p.name != "INDEX.txt"]
        if not stale:
            print("[cs-primers] --clean: no stale primers found.")
            return
        print(f"[cs-primers] --clean: {len(stale)} stale primer(s) found:")
        for p in stale:
            print(f"  DELETE {p.name}")
        if args.yes:
            confirmed = True
        else:
            import sys as _sys
            if not _sys.stdin.isatty():
                print("[cs-primers] --clean: no TTY and --yes not set; aborting. "
                      "Re-run with --yes to delete non-interactively.")
                return
            confirmed = input("Delete these files? [y/N] ").strip().lower() == "y"
        if confirmed:
            for p in stale:
                p.unlink()
                print(f"  Deleted {p.name}")
            update_index()
            print("[cs-primers] --clean: done.")
        else:
            print("[cs-primers] --clean: aborted.")
        return

    if args.list:
        print(f"CS Primers directory: {PRIMERS_DIR}")
        print(f"{'STATUS':<8} {'TIER':<5} {'KEY':<32} LABEL")
        for key in sorted(CS_PRIMER_SPECS.keys()):
            label, tier, _, _ = CS_PRIMER_SPECS[key]
            primer_path = PRIMERS_DIR / f"{key}.txt"
            status = "OK" if primer_path.exists() else "MISSING"
            print(f"  {status:<6} {tier:<5} {key:<32} {label}")
        return

    if args.category:
        if args.category not in CS_PRIMER_SPECS:
            print(f"Unknown category: {args.category}", file=sys.stderr)
            print(f"Valid keys: {', '.join(sorted(CS_PRIMER_SPECS.keys()))}", file=sys.stderr)
            sys.exit(1)
        generate_primer(args.category, force=True)
        update_index()
        return

    # Generate all missing (or all if --force)
    api_key = load_api_key()
    if not api_key:
        print("[cs-primers] No ANTHROPIC_API_KEY — will use static fallback primers")
    else:
        print(f"[cs-primers] API key found — generating rich primers via claude-haiku-4-5")

    print(f"[cs-primers] Generating CS primers for {len(CS_PRIMER_SPECS)} categories")
    print(f"[cs-primers] Output: {PRIMERS_DIR}")
    print()

    written = 0
    for key in sorted(CS_PRIMER_SPECS.keys()):
        ok = generate_primer(key, force=args.force)
        if ok:
            written += 1
            if api_key:
                time.sleep(0.5)  # rate limit

    update_index()
    print(f"\n[cs-primers] Done: {written} primers written, "
          f"{len(CS_PRIMER_SPECS) - written} skipped (already exist)")


if __name__ == "__main__":
    main()
