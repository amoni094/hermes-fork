#!/usr/bin/env python3
"""
cs-paper-interpreter.py

Interpretation layer for CS systems/engineering papers found by cs-research-sweep.py.

Takes the CS sweep JSON, reads each paper's abstract, and produces one of three outputs:

  SYSTEMS-APPLICABLE — the CS technique directly improves a Hermes system component.
                       Produces a concrete before/after spec for the target module.

  SPIKE              — the CS technique describes an approach Hermes doesn't use yet.
                       Produces a Given/When/Then spike candidate.

  SKIP               — no plausible Hermes analogue after honest assessment.

Output:
  ~/.hermes/cache/research/cs-interpretation-latest.json
  ~/.hermes/cache/research/cs-spike-queue.json

Usage:
  python3 cs-paper-interpreter.py [--dry-run] [--limit N] [--input PATH]
  python3 cs-paper-interpreter.py --fetch-abstracts

The interpreter does NOT apply patches. It produces candidates for human review.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── Paths ─────────────────────────────────────────────────────────────────────

CACHE_DIR      = Path("~/.hermes/cache/research").expanduser()
SWEEP_LATEST   = CACHE_DIR / "hermes-cs-sweep-latest.json"
OUTPUT_LATEST  = CACHE_DIR / "cs-interpretation-latest.json"
SPIKE_QUEUE    = CACHE_DIR / "cs-spike-queue.json"
SPIKE_DIR      = Path("~/.hermes/research/spikes").expanduser()
PRIMERS_DIR    = CACHE_DIR / "cs-primers"

SPIKE_DIR.mkdir(parents=True, exist_ok=True)
PRIMERS_DIR.mkdir(parents=True, exist_ok=True)

# ── CS category keys ──────────────────────────────────────────────────────────

CS_CATS = {
    "software_testing", "program_analysis", "pl_design", "compilers_runtime",
    "software_architecture", "devops_ci", "distributed_systems", "operating_systems",
    "computer_architecture", "parallel_concurrent", "cloud_serverless", "edge_embedded",
    "cryptography_eng", "system_security", "privacy_engineering", "secure_mpc",
    "network_security", "database_systems", "data_streaming", "information_retrieval",
    "knowledge_representation", "ui_design", "conversational_ai", "collaborative_systems",
    "network_protocols", "wireless_mobile", "content_delivery", "quantum_systems",
    "neuromorphic", "formal_specification",
}

# ── Hermes component map ──────────────────────────────────────────────────────

COMPONENT_MAP = {
    "software_testing":       ["agent output verification", "skill test harness"],
    "program_analysis":       ["static tool validation", "skill dependency graph analysis"],
    "pl_design":              ["structured output schemas", "DSL for skill authoring"],
    "compilers_runtime":      ["hermes venv startup time", "Python runtime optimization"],
    "software_architecture":  ["plugin architecture", "toolset modularity", "skill layering"],
    "devops_ci":              ["hermes CI pipeline", "skill deployment automation"],
    "distributed_systems":    ["delegate_task fault tolerance", "cron job reliability"],
    "operating_systems":      ["async agent loop scheduling", "cron priority tuning"],
    "computer_architecture":  ["embedding computation speed", "cache-aware context ops"],
    "parallel_concurrent":    ["parallel tool execution", "thread safety in delegate"],
    "cloud_serverless":       ["Hermes cloud deploy", "auto-scaling agent workers"],
    "edge_embedded":          ["Hermes on Termux/mobile", "lightweight model routing"],
    "cryptography_eng":       ["API key management", "secure credential rotation"],
    "system_security":        ["sandboxed code execution", "tool privilege separation"],
    "privacy_engineering":    ["memory data minimization", "PII handling in tools"],
    "secure_mpc":             ["federated memory with privacy", "multi-party skill eval"],
    "network_security":       ["gateway transport security", "webhook auth hardening"],
    "database_systems":       ["hermes_state.db query optimization", "vector DB for retrieval"],
    "data_streaming":         ["session event streaming", "real-time cron delivery"],
    "information_retrieval":  ["skill retrieval ranking", "memory semantic search tuning"],
    "knowledge_representation": ["Graphiti KG schema", "skill taxonomy ontology"],
    "ui_design":              ["Hermes TUI accessibility", "dashboard usability"],
    "conversational_ai":      ["intent detection in CLI", "dialogue state in gateway"],
    "collaborative_systems":  ["multi-agent coordination", "shared session state"],
    "network_protocols":      ["gateway transport protocol", "webhook streaming"],
    "wireless_mobile":        ["Termux/mobile reliability", "mobile-first features"],
    "content_delivery":       ["skill content caching", "primer cache eviction policy"],
    "quantum_systems":        ["future compute substrate", "quantum-safe crypto migration"],
    "neuromorphic":           ["energy-efficient inference", "novel hardware routing"],
    "formal_specification":   ["agent loop invariants", "verified tool contracts TLA+",
                               "new: formal plan verifier (pre-execution action-sequence checker)",
                               "new: TLA+-style liveness proof for cron agent loops"],
    "system_security":        ["sandboxed code execution", "tool privilege separation",
                               "new: ZK-attestation layer for tool outputs",
                               "new: capability-based tool permission model"],
    "cryptography_eng":       ["API key management", "secure credential rotation",
                               "new: hash-chain integrity log for l1-tracegrant audit trail",
                               "new: homomorphic skill-quality evaluation"],
    "information_retrieval":  ["skill retrieval ranking", "memory semantic search tuning",
                               "new: calibrated uncertainty (confidence intervals) over retrieved facts",
                               "new: optimal stopping for retrieval fan-out (when to commit to top-k)"],
    "distributed_systems":    ["delegate_task fault tolerance", "cron job reliability",
                               "new: optimal stopping for subagent fan-out (commit threshold)",
                               "new: causal attribution of delegate failures"],
    "knowledge_representation": ["Graphiti KG schema", "skill taxonomy ontology",
                                 "new: causal error attribution graph (post-mortem session analysis)",
                                 "new: provenance tracking for memory facts"],
    "software_architecture":  ["plugin architecture", "toolset modularity", "skill layering",
                               "new: adversarial robustness certificates for skill-routing decisions"],
    "database_systems":       ["hermes_state.db query optimization", "vector DB for retrieval",
                               "new: online convex optimisation for adaptive query parameters"],
}


def load_primer(category_key: str) -> str:
    """Load CS primer for a category, or empty string if not yet generated."""
    primer_file = PRIMERS_DIR / f"{category_key}.txt"
    if primer_file.exists():
        return primer_file.read_text(encoding="utf-8")
    return ""


def fetch_abstract(arxiv_id: str) -> str:
    """Fetch abstract from arXiv API."""
    clean_id = re.sub(r"^arXiv:", "", arxiv_id, flags=re.IGNORECASE)
    url = f"https://export.arxiv.org/abs/{clean_id}"
    try:
        req = Request(url, headers={"User-Agent": "Hermes-CS-Interpreter/1.0"})
        with urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Extract abstract from HTML
        m = re.search(r'<blockquote class="abstract mathjax">\s*<span class="descriptor">Abstract:</span>(.*?)</blockquote>',
                      html, re.DOTALL)
        if m:
            abstract = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            return abstract[:2000]
    except Exception:
        pass
    return ""


def _load_env() -> None:
    """Load ~/.hermes/.env into os.environ (idempotent, setdefault)."""
    from pathlib import Path as _P
    env_path = _P("~/.hermes/.env").expanduser()
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def call_api(prompt: str, model: str = "claude-haiku-4-5", max_tokens: int = 512, timeout: float = 20.0) -> str:
    """Call Anthropic API for interpretation. Returns empty string on failure."""
    _load_env()
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  [warn] API call failed: {e}", file=sys.stderr)
        return ""


def prefilter_paper(title: str, abstract: str, cat: str) -> str:
    """Two-stage pre-filter Stage 1: fast SKIP/MAYBE gate (~0.8s, max_tokens=5).

    Passes MAYBE for Track A (improves existing component) OR Track B (new capability).
    Hard SKIP only for papers requiring training loops, tabular MDPs, or oracle rewards.
    Returns 'MAYBE' or 'SKIP'.
    """
    _load_env()
    if not title and not abstract:
        return "SKIP"
    prompt = (
        "Screen this CS paper for a prompt-only LLM agent framework (no training, "
        "no weights, no GPU, text-only memory).\n"
        f"Title: {title}\nCategory: {cat}\nAbstract: {abstract[:600]}\n\n"
        "Reply MAYBE if: (A) it improves an existing agent capability (routing, memory, "
        "compression, retrieval, trust, skill selection, tool execution, security, scheduling), "
        "OR (B) it could enable a NEW capability not yet in the framework (e.g. formal plan "
        "verification, causal error attribution, optimal stopping for subagents, adversarial "
        "robustness certificates, verifiable tool-call proofs, calibrated uncertainty over "
        "retrieved facts, online adaptive hyperparameter tuning).\n"
        "Hard SKIP only if core contribution requires: (a) gradient computation/backpropagation, "
        "(b) direct model weight access, or (c) continuous per-turn training signal. "
        "Do NOT skip for: iterative algorithms, discrete structures, state accumulation, "
        "scoring functions, graph/eigenvalue computation, bandit/UCB state — Hermes can build "
        "infrastructure (JSON state, SQLite, numpy, cron jobs) for all of these.\n"
        "Reply with exactly one word: SKIP or MAYBE."
    )
    try:
        import anthropic
        from anthropic.types import TextBlock as _TB
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=5,
            timeout=10.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0]
        verdict = (raw.text if isinstance(raw, _TB) else "MAYBE").strip().upper()
        return "SKIP" if verdict.startswith("SKIP") else "MAYBE"
    except Exception as e:
        print(f"  [warn] pre-filter failed ({e}), defaulting MAYBE", file=sys.stderr)
        return "MAYBE"


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


def interpret_paper(paper: dict, fetch_abstracts: bool = False) -> dict:
    """Produce SYSTEMS-APPLICABLE / SPIKE / SKIP verdict for one paper."""
    cat_key   = paper.get("category_key") or paper.get("category") or "unknown"
    title     = paper.get("title", "")
    abstract  = paper.get("abstract", "")
    paper_id  = paper.get("id", "")

    if fetch_abstracts and not abstract and paper_id:
        abstract = fetch_abstract(paper_id)
        time.sleep(0.3)  # rate limit arXiv

    components = COMPONENT_MAP.get(cat_key, ["(no mapping)"])
    primer     = load_primer(cat_key)

    primer_snippet = f"\n\nCS PRIMER for {cat_key}:\n{primer[:800]}" if primer else ""

    prompt = f"""You are Hermes, a personal AI agent system. A new CS paper was found in the
category '{cat_key}' during the weekly CS sweep.

Paper: {title}
ID:    {paper_id}
Abstract: {abstract[:1000] if abstract else '(not available)'}

Hermes components this category maps to:
  {chr(10).join('  - ' + c for c in components)}{primer_snippet}

Hermes hard constraints — ABSOLUTE blockers only:
  - NO gradient computation or backpropagation (cannot train/fine-tune models)
  - NO access to model weights or activations
  - NO continuous per-turn training signal

  NOT blockers — Hermes CAN build infrastructure for:
  - Iterative state accumulation → JSON/SQLite updated each cron run
  - Discrete/tabular structures → Python dicts, graphs, databases
  - Scoring/ranking functions → Python functions run each turn or cron
  - Graph/eigenvalue computation → numpy at inference time
  - Bandit/UCB state → JSON state file updated each run
  - Sampling, statistical estimators → computed from session logs
  Ask "can Hermes build infrastructure for this?" before firing SKIP.

Before classifying, answer two questions internally:
  1. STRUCTURAL MATCH: What CS object/data structure does this technique operate on?
     Does Hermes have a component that handles that same type of data?
  2. NEW CAPABILITY CHECK: If no existing component matches, does this paper enable a capability
     Hermes could add? Examples: formal plan verification, causal error attribution, optimal
     stopping for subagent fan-out, ZK verifiable tool outputs, calibrated uncertainty over
     retrieved facts, adversarial robustness certificates for routing decisions.
     If yes, use target = "new: <short capability name>".
  3. FEASIBILITY: Does this require any of the hard constraints above?

Then classify as exactly ONE of:

SYSTEMS-APPLICABLE — The paper's technique can directly improve a specific Hermes component.
  Must pass: structural match = yes, no feasibility violations, specific module named.
  Respond with: SYSTEMS-APPLICABLE | <component_name> | <one sentence what changes>

SPIKE — The paper describes an approach worth a throwaway experiment in Hermes.
  Covers BOTH: (A) existing component improvement, and (B) new capability prototype.
  For new capabilities: component_name = "new: <capability>" (e.g. "new: formal plan verifier").
  Must pass: structural match or new-capability match, no feasibility violations.
  Respond with: SPIKE | <component_name> | Given <current state>, When <technique applied>, Then <measurable result>

SKIP — No plausible Hermes improvement, or feasibility violation, or structural mismatch.
  Respond with: SKIP | <one sentence why>

Rules:
- Vocabulary match ("agent", "routing") alone is NOT a structural match.
  A tabular-MDP paper that mentions agents = SKIP. A sequence-compression paper = possible match.
- Do not say SYSTEMS-APPLICABLE unless you can name the specific module/function to change.
- Do not say SPIKE unless you can write a concrete Given/When/Then.
- Default to SKIP for theorem-only papers with no implementation path.
- Answer in ONE line only."""

    response = call_api(prompt)

    if not response:
        # Fallback: keyword-based heuristic
        title_lower = title.lower()
        keywords_sys = ["implementation", "system", "framework", "tool", "benchmark",
                        "deployment", "production", "engineering", "practical"]
        if any(k in title_lower for k in keywords_sys):
            verdict = "SPIKE"
            component = components[0] if components else "unknown"
            detail = f"Given Hermes uses ad-hoc approach, When applying {title}, Then improved reliability"
        else:
            verdict = "SKIP"
            component = ""
            detail = "No clear Hermes implementation path identified (heuristic fallback)"
    else:
        parts = [p.strip() for p in response.split("|", 2)]
        verdict = parts[0] if parts else "SKIP"
        if verdict not in ("SYSTEMS-APPLICABLE", "SPIKE", "SKIP"):
            verdict = "SKIP"
        component = parts[1] if len(parts) > 1 else (components[0] if components else "")
        detail = parts[2] if len(parts) > 2 else ""

    return {
        "id": paper_id,
        "title": title,
        "category_key": cat_key,
        "interpretation_type": verdict,
        "hermes_analogue": component,
        "component_target": component,
        "confidence": 0.7 if response else 0.3,
        "proposal": detail if verdict == "SYSTEMS-APPLICABLE" else "",
        "given_when_then": detail if verdict == "SPIKE" else "",
        "skip_reason": detail if verdict == "SKIP" else "",
        "abstract_snippet": abstract[:300] if abstract else "",
    }


# ── Stage 3: Theorem-to-implementation ideation ────────────────────────────────

def cs_theorem_ideate(title: str, abstract: str, category: str) -> dict | None:
    """Stage 3 for CS papers: generate implementable Hermes artifact from a full-chain SKIP."""
    prompt = (
        f"Paper: {title}\n"
        f"Category: {category}\n"
        f"Abstract: {abstract[:600]}\n\n"
        "This CS paper was SKIP in direct component matching. STAGE 3: theorem/technique-to-implementation ideation.\n\n"
        "HERMES CONTEXT: AI agent framework — prompt-only, local-first, Python scripts, SQLite, numpy, cron, JSON state.\n"
        "Has: memory layers, skill routing, tool orchestration, cron scheduling, context compaction, RAG recall, multi-agent delegation.\n"
        "Can BUILD: JSON state, SQLite, numpy/scipy, cron loops, Python scripts, CLI tools.\n"
        "ABSOLUTE limits: no gradient computation, no weight updates, no model internals access.\n\n"
        "TASK: Extract the paper's core technique/invariant/algorithm structure. Propose ONE concrete Hermes artifact\n"
        "that embodies that structure — a Python script, skill, or config we could build.\n\n"
        "Good examples:\n"
        "  - A query-rewriting algorithm → a skill-query normaliser that rewrites ambiguous skill lookups before BM25\n"
        "  - A cache eviction policy → a memory-layer TTL manager using the same priority function\n"
        "  - A dependency graph traversal → a skill-dependency resolver for multi-skill task plans\n"
        "  - An anomaly scoring method → a session-health alarm that scores tool-call patterns\n\n"
        "Return null_reason if truly irreducible (requires real-time OS integration, GPU kernel, or similar).\n\n"
        "JSON only:\n"
        "{\n"
        "  \"math_structure\": \"<core technique/invariant in one sentence>\",\n"
        "  \"hermes_artifact\": \"<filename or skill name to build>\",\n"
        "  \"artifact_type\": \"<script|skill|config|cron>\",\n"
        "  \"implementation_sketch\": \"<3-5 sentences: what it does, what it computes, what data it reads/writes>\",\n"
        "  \"hermes_benefit\": \"<one sentence: concrete improvement>\",\n"
        "  \"null_reason\": \"\"\n"
        "}"
    )
    try:
        import anthropic
        client = anthropic.Anthropic()
        from anthropic.types import TextBlock as _TB
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=400,
            timeout=15.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = (msg.content[0].text if isinstance(msg.content[0], _TB) else str(msg.content[0])).strip()
        import re as _re
        raw = _re.sub(r'^```(?:json)?\s*', '', raw, flags=_re.MULTILINE)
        raw = _re.sub(r'\s*```$', '', raw, flags=_re.MULTILINE)
        json_start = raw.find("{")
        if json_start == -1:
            return None
        idea = json.loads(raw[json_start:raw.rfind("}") + 1])
        if idea.get("null_reason", "").strip():
            return None
        if not idea.get("hermes_artifact", "").strip():
            return None
        return idea
    except Exception:
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=40,
                        help="Max papers to interpret per run (default 40; two-stage filter ~5s avg/paper = ~200s, safe under 300s cron budget)")
    parser.add_argument("--input", type=Path, default=SWEEP_LATEST)
    parser.add_argument("--seen-cache", type=Path, default=None,
                        help="Override seen-paper cache path (default: auto-derived from --input filename)")
    parser.add_argument("--all-categories", action="store_true",
                        help="Skip CS category filter — process all papers in the input file")
    parser.add_argument("--fetch-abstracts", action="store_true")
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip first N papers before applying --limit (enables windowed batching over large corpora)")
    args = parser.parse_args()

    # Emit content-addressed run header (arXiv:2608.23610 traceability)
    import subprocess as _sp
    _rh = _sp.run(
        [sys.executable, str(Path("~/.hermes/scripts/run-header.py").expanduser()),
         "--script", "cs-paper-interpreter.py",
         "--model", "claude-haiku-4-5",
         "--skill", "hermes-cs-research",
         "--note", f"fetch-abstracts={args.fetch_abstracts} limit={args.limit}"],
        capture_output=True, text=True, timeout=30,
    )
    if _rh.returncode != 0:
        print(f"[cs-interpreter] run-header failed: {_rh.stderr.strip()}", file=sys.stderr)
    else:
        print(f"[cs-interpreter] run-header: {_rh.stdout.strip()}", file=sys.stderr)

    input_path = args.input
    if not input_path.exists():
        print(f"[cs-interpreter] Input not found: {input_path}", file=sys.stderr)
        print("[cs-interpreter] Run cs-research-sweep.py first.", file=sys.stderr)
        sys.exit(1)

    sweep_data = json.loads(input_path.read_text())

    # Derive output file paths from input stem (so core/CS/math each have separate outputs)
    _inp_stem = input_path.stem.replace("hermes-", "").replace("-latest", "").replace("-sweep", "")
    output_latest  = CACHE_DIR / f"{_inp_stem}-interpretation-latest.json"
    spike_queue_path = CACHE_DIR / f"{_inp_stem}-spike-queue.json"
    ideas_queue_p  = CACHE_DIR / f"{_inp_stem}-ideas-queue.json"

    # Stale-data guard: warn if sweep file is older than 48 hours (sweep hangs silently).
    # Source: Wave 1 adversarial review Sep 2026.
    import time as _time
    sweep_age_h = (_time.time() - input_path.stat().st_mtime) / 3600
    if sweep_age_h > 48:
        print(f"[cs-interpreter] WARNING: sweep file is {sweep_age_h:.1f}h old (>{48}h) — may be stale. "
              "Run cs-research-sweep.py to refresh.", file=sys.stderr)

    papers = sweep_data.get("new_papers_flat", sweep_data.get("all_papers", []))

    # Filter to CS categories only (sweep writes `category`; accept `category_key` too)
    # Skip filter when --all-categories is set (e.g. for core agent sweep input)
    if args.all_categories:
        cs_papers = papers
    else:
        cs_papers = [p for p in papers if (p.get("category_key") or p.get("category") or "") in CS_CATS]

    if args.limit:
        cs_papers = cs_papers[args.offset: args.offset + args.limit]

    # Seen-paper tracking: derive cache path from input file if not overridden
    if args.seen_cache:
        cs_seen_path = args.seen_cache
    else:
        # Auto-derive: hermes-research-latest.json → core-seen-papers.json
        stem = input_path.stem.replace("hermes-", "").replace("-latest", "").replace("-sweep", "")
        cs_seen_path = CACHE_DIR / f"{stem}-seen-papers.json"
    cs_seen_processed: set = set()
    if cs_seen_path.exists():
        try:
            _d = json.loads(cs_seen_path.read_text())
            cs_seen_processed = set(_d.get("seen", []))
        except Exception:
            pass
    cs_unseen = [p for p in cs_papers if (p.get("id") or p.get("arxiv_id", "")) not in cs_seen_processed]
    if not cs_unseen:
        if args.offset:
            # In offset mode, don't reset — the slice is already a fresh window
            print("[cs-interpreter] All papers in this offset window already processed", file=sys.stderr)
        else:
            print("[cs-interpreter] All papers already processed — resetting seen cache", file=sys.stderr)
            cs_seen_processed = set()
            cs_unseen = cs_papers
    print(f"[cs-interpreter] {len(cs_unseen)} unseen papers (skipping {len(cs_papers)-len(cs_unseen)} already processed)")
    cs_papers = cs_unseen

    print(f"[cs-interpreter] {len(cs_papers)} CS papers to interpret")

    if args.dry_run:
        print("[DRY RUN] Would interpret:")
        for p in cs_papers[:10]:
            print(f"  {p.get('category_key','?')} | {p.get('title','?')[:60]}")
        return

    results = []
    spike_queue = []
    generated_ideas = []  # Stage 3 theorem-to-implementation ideas
    skipped_prefilter = 0
    _loop_start = time.time()
    _SOFT_BUDGET = 270  # seconds; leave 30s for file writes before outer timeout

    for i, paper in enumerate(cs_papers, 1):
        title   = paper.get("title", "") or ""
        title   = title.removeprefix("Title:").strip()  # strip sweep prefix
        abstract = paper.get("abstract", "") or ""
        cat     = paper.get("category_key") or paper.get("category") or ""

        # Budget guard — stop early and write results rather than dying in timeout
        _elapsed = time.time() - _loop_start
        if _elapsed > _SOFT_BUDGET:
            print(f"[cs-interpreter] Budget guard: {_elapsed:.0f}s > {_SOFT_BUDGET}s — stopping at paper {i}/{len(cs_papers)}", file=sys.stderr)
            break

        if (i - 1) % 5 == 0:
            print(f"[cs-interpreter] Progress: {i}/{len(cs_papers)} papers ({_elapsed:.0f}s elapsed)", file=sys.stderr)

        # Stage 1: fast pre-filter (~0.8s) — skip if neither Track A nor Track B match
        _pf = prefilter_paper(title, abstract, cat)
        if _pf == "SKIP":
            skipped_prefilter += 1
            continue

        print(f"  [{i}/{len(cs_papers)}] {title[:60]}...")
        verdict = interpret_paper(paper, fetch_abstracts=args.fetch_abstracts)
        results.append(verdict)
        if verdict["interpretation_type"] in ("SYSTEMS-APPLICABLE", "SPIKE"):
            spike_queue.append(verdict)
        elif verdict["interpretation_type"] == "SKIP":
            # Stage 3: theorem-to-implementation ideation on full-chain SKIPs
            idea = cs_theorem_ideate(title, abstract, cat)
            if idea:
                idea["source_title"] = title
                idea["source_category"] = cat
                idea["source_url"] = paper.get("url", "")
                generated_ideas.append(idea)
                print(f"  [Stage 3 IDEA] {idea.get('hermes_artifact','')} — {idea.get('hermes_benefit','')[:70]}")
        time.sleep(0.1)

    # Save outputs
    now = datetime.now(timezone.utc).isoformat()
    output_latest.write_text(json.dumps({
        "interpreted_at": now,
        "paper_count": len(results),
        "prefilter_skipped": skipped_prefilter,
        "systems_applicable": sum(1 for r in results if r["interpretation_type"] == "SYSTEMS-APPLICABLE"),
        "spikes": sum(1 for r in results if r["interpretation_type"] == "SPIKE"),
        "skips": sum(1 for r in results if r["interpretation_type"] == "SKIP"),
        "generated_ideas_count": len(generated_ideas),
        "new_capabilities": [r for r in results if r.get("component", "").startswith("new:")],
        "papers": results,
        "generated_ideas": generated_ideas,
    }, indent=2))
    print(f"[cs-interpreter] Saved: {output_latest}")

    spike_queue_path.write_text(json.dumps({
        "generated_at": now,
        "pending_count": len(spike_queue),
        "items": spike_queue,
    }, indent=2))
    print(f"[cs-interpreter] Spike queue: {spike_queue_path} ({len(spike_queue)} items)")

    # Write CS ideas queue (append-dedupe)
    ideas_queue_path = ideas_queue_p
    existing_ideas = []
    if ideas_queue_path.exists():
        try:
            existing_ideas = json.loads(ideas_queue_path.read_text()).get("ideas", [])
        except Exception:
            pass
    existing_artifacts = {i.get("hermes_artifact", "") for i in existing_ideas}
    new_ideas = [i for i in generated_ideas if i.get("hermes_artifact", "") not in existing_artifacts]
    all_ideas = existing_ideas + new_ideas
    ideas_queue_path.write_text(json.dumps({
        "last_updated": now,
        "total_ideas": len(all_ideas),
        "ideas": all_ideas,
    }, indent=2))
    if generated_ideas:
        print(f"[cs-interpreter] Ideas queue: {ideas_queue_path} ({len(new_ideas)} new, {len(all_ideas)} total)")

    # Update seen-paper cache
    processed_ids = [p.get("id") or p.get("arxiv_id", "") for p in cs_papers if p.get("id") or p.get("arxiv_id")]
    cs_seen_processed.update(processed_ids)
    cs_seen_path.write_text(json.dumps({"seen": sorted(cs_seen_processed), "last_updated": now}, indent=2))
    print(f"[cs-interpreter] Seen cache: {len(cs_seen_processed)} total papers processed across runs")

    # Summary
    sa  = sum(1 for r in results if r["interpretation_type"] == "SYSTEMS-APPLICABLE")
    sp  = sum(1 for r in results if r["interpretation_type"] == "SPIKE")
    sk  = sum(1 for r in results if r["interpretation_type"] == "SKIP")
    track_skip_rate(len(results), sk)
    print(f"\n[cs-interpreter] Results: {sa} SYSTEMS-APPLICABLE, {sp} SPIKE, {sk} SKIP")

    if spike_queue:
        print("\n--- Pending CS spikes/proposals ---")
        for item in spike_queue[:5]:
            t = item["interpretation_type"]
            print(f"  {t} [{item['category_key']}] {item['title'][:60]}")
            if t == "SPIKE":
                print(f"    -> {item.get('given_when_then', '')[:80]}")
            else:
                print(f"    -> {item.get('proposal', '')[:80]}")


if __name__ == "__main__":
    main()
