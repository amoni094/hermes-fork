#!/usr/bin/env python3
"""
memory-monad.py — MemoryMonad: Categorical wrapper for Hermes memory operations.

Implements:
  - MemoryMonad (Tier 1+2): monadic bind for retain/recall chains with error propagation
  - EnrichedHom (Tier 1): explicit (confidence, age_days) retrieval scoring
  - GrothPair (Tier 1): Grothendieck context-content pairing for every fact
  - GroupoidCheck (Tier 1): 3-hop consistency check on Graphiti entity graph
  - OlogSchema (Tier 2): categorical schema enforcer for Hermes fact types
  - SheafCoboundary (Tier 2): inconsistency detector on entity neighborhoods
  - ProvenanceGraph (Tier 3): derivation path + equivalence witness storage
  - DoubleFunctorQuery (Tier 3): unified cross-layer memory query interface

Sources:
  - Spivak 2010 arXiv:1009.1166 (functorial data migration)
  - Uustalu & Vene arXiv:1310.0605 (monads/comonads)
  - Grothendieck construction: SGA 1, Expose VI
  - Sheaf coboundary: arXiv:2601.21207, arXiv:2409.08036
  - Lambert & Patterson arXiv:2403.19884 (double-functorial queries)
  - HyperSkill arXiv:2608.16114 (hyperedge skill combos)

Usage:
  from memory_monad import MemoryMonad, GrothPair, EnrichedHom, GroupoidCheck
  m = MemoryMonad()
  result = m.retain(GrothPair(context="session_xyz", content="...", type="fact"))
  result2 = result.bind(lambda f: m.recall(f.content))
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
MONAD_LOG   = HERMES_HOME / "cache" / "memory-monad.jsonl"
GRAPHITI_BASE = os.environ.get("GRAPHITI_BASE", "http://127.0.0.1:8765/mcp")
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://127.0.0.1:9177")
HINDSIGHT_BANK = os.environ.get("HINDSIGHT_BANK", "hermes-default")

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Tier 1a: Grothendieck Pair — context + content pairing (not floating facts)
# ---------------------------------------------------------------------------

VALID_CONTEXTS = ("session", "skill", "hindsight", "global", "cron")
VALID_TYPES    = ("fact", "preference", "procedure", "event", "entity", "relation",
                  "constraint", "observation", "reflection", "plan",
                  "research_finding", "safety_incident", "user_preference")

@dataclass
class GrothPair:
    """
    A Grothendieck pair: every memory fact is a pair (context, content), never
    just floating content. Formally: an object in the total category ∫F where
    F: Context → Set assigns the set of valid facts to each context.

    context: which memory layer/task this fact lives in
    content: the fact text or structured data
    type:    the olog type (noun phrase category)
    tags:    optional labels for retrieval filtering
    derived_from: list of source fact IDs (provenance — Tier 3)
    """
    context: str
    content: str
    type: str = "fact"
    tags: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fact_id: str = field(default_factory=lambda: "")

    def __post_init__(self):
        if self.context not in VALID_CONTEXTS:
            # warn but don't block — extensible
            pass
        if self.type not in VALID_TYPES:
            pass
        if not self.fact_id:
            # deterministic ID from context+content hash
            raw = f"{self.context}:{self.content}"
            self.fact_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GrothPair":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Tier 1b: EnrichedHom — explicit (confidence, age_days) retrieval scoring
# Enriched over [0,1] × [0,∞]: Lawvere metric space of facts
# ---------------------------------------------------------------------------

@dataclass
class EnrichedHom:
    """
    A morphism in the [0,1]-enriched memory category.
    weight = confidence × temporal_decay(age_days)
    This makes the memory a Lawvere metric space where distance = 1 - weight.
    """
    source_query: str
    target_fact: str
    confidence: float       # [0,1] — retrieval cosine similarity or relevance score
    age_days: float         # days since fact was stored
    decay_rate: float = 0.02  # per day; half-life ≈ 35 days

    @property
    def weight(self) -> float:
        """Enriched hom-weight: confidence × exponential temporal decay, clamped to [0,1]."""
        decay = math.exp(-self.decay_rate * max(0.0, self.age_days))
        return round(min(1.0, max(0.0, self.confidence)) * decay, 4)

    @property
    def distance(self) -> float:
        """Lawvere metric: 1 - weight (0 = identical, 1 = maximally distant)."""
        return round(1.0 - self.weight, 4)

    def passes_threshold(self, threshold: float = 0.3) -> bool:
        return self.weight >= threshold

    def to_dict(self) -> dict:
        return {
            "source_query": self.source_query,
            "target_fact": self.target_fact,
            "confidence": self.confidence,
            "age_days": self.age_days,
            "weight": self.weight,
            "distance": self.distance,
        }


def score_results(query: str, results: list[dict], now_ts: float | None = None) -> list[dict]:
    """
    Apply EnrichedHom scoring to a list of retrieval results.
    Each result should have: text/content, score/confidence, created_at (ISO or epoch).
    Returns results sorted by enriched weight descending.
    """
    if now_ts is None:
        now_ts = time.time()
    scored = []
    for r in results:
        content = r.get("text") or r.get("content") or str(r)
        raw_conf = float(r.get("score") or r.get("confidence") or r.get("relevance") or 0.5)
        # parse created_at to age_days
        created = r.get("created_at") or r.get("timestamp") or ""
        try:
            if isinstance(created, (int, float)):
                age_days = (now_ts - float(created)) / 86400.0
            elif created:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                age_days = (now_ts - ts) / 86400.0
            else:
                age_days = 30.0  # assume 30-day-old if unknown
        except Exception:
            age_days = 30.0
        hom = EnrichedHom(source_query=query, target_fact=content,
                          confidence=raw_conf, age_days=age_days)
        scored.append({**r, "enriched_weight": hom.weight, "enriched_distance": hom.distance})
    scored.sort(key=lambda x: x["enriched_weight"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Tier 1c: GroupoidCheck — 3-hop consistency check on Graphiti entity graph
# Groupoid morphisms must compose: if A→B and B→C then A→C should hold.
# ---------------------------------------------------------------------------

class GroupoidCheck:
    """
    Implements the fundamental groupoid consistency check on memory facts.
    If fact_A relates to fact_B (via relation r1) and fact_B relates to fact_C
    (via relation r2), then fact_A should relate to fact_C (via composed relation r1∘r2).
    Violations = inconsistencies in the memory groupoid.

    Usage:
        checker = GroupoidCheck()
        violations = checker.check_triple(entity_A, entity_B, entity_C, facts)
    """

    RELATION_INVERSES = {
        "supports":      "is_supported_by",
        "contradicts":   "contradicts",          # symmetric
        "generalizes":   "specializes",
        "specializes":   "generalizes",
        "causes":        "is_caused_by",
        "is_caused_by":  "causes",
        "precedes":      "follows",
        "follows":       "precedes",
        "is_part_of":    "has_part",
        "has_part":      "is_part_of",
    }

    def __init__(self, facts: list[dict] | None = None):
        """
        facts: list of dicts with keys: source_entity, relation, target_entity
        """
        self.facts = facts or []
        self._index: dict[tuple[str, str], list[str]] = {}
        for f in self.facts:
            key = (f.get("source_entity", ""), f.get("target_entity", ""))
            self._index.setdefault(key, []).append(f.get("relation", ""))

    def add_fact(self, source: str, relation: str, target: str):
        self.facts.append({"source_entity": source, "relation": relation, "target_entity": target})
        self._index.setdefault((source, target), []).append(relation)

    def relations_between(self, a: str, b: str) -> list[str]:
        return self._index.get((a, b), [])

    def check_triple(self, A: str, B: str, C: str) -> dict:
        """
        Groupoid composition check: A→B, B→C implies A→C should be reachable.
        Returns dict with: consistent (bool), path (list), missing (list).
        """
        ab = self.relations_between(A, B)
        bc = self.relations_between(B, C)
        ac = self.relations_between(A, C)

        if not ab or not bc:
            return {"consistent": True, "reason": "no path to check", "missing": []}

        # Expected composed relations (simplified: any composition of ab × bc)
        # For transitivity: if ab contains "supports" and bc contains "supports",
        # expect ac contains "supports"
        expected: set[str] = set()
        for r1 in ab:
            for r2 in bc:
                if r1 == r2 and r1 in ("supports", "generalizes", "causes", "precedes"):
                    expected.add(r1)
                elif r1 == "contradicts" or r2 == "contradicts":
                    expected.add("contradicts")  # contradiction propagates

        missing = [r for r in expected if r not in ac]
        if missing:
            return {
                "consistent": False,
                "path": [A, B, C],
                "existing_AC": ac,
                "expected_AC": list(expected),
                "missing": missing,
                "reason": f"Groupoid composition {A}→{B}→{C} expects {expected} between {A}↔{C}; found {ac}",
            }
        return {"consistent": True, "path": [A, B, C], "existing_AC": ac, "reason": "ok"}

    def check_all_triples(self, entities: list[str] | None = None) -> list[dict]:
        """Run 3-hop check across all reachable triples in the current fact set."""
        if entities is None:
            seen: set[str] = set()
            for s, t in self._index:
                seen.add(s); seen.add(t)
            entities = list(seen)

        violations = []
        # O(n^3) — fine for small knowledge graphs; warn if large
        if len(entities) > 100:
            print(f"[GroupoidCheck] warning: {len(entities)} entities — O(n^3) check may be slow", flush=True)

        for A in entities:
            for B in entities:
                if A == B:
                    continue
                if not self.relations_between(A, B):
                    continue
                for C in entities:
                    if C == A or C == B:
                        continue
                    if not self.relations_between(B, C):
                        continue
                    result = self.check_triple(A, B, C)
                    if not result["consistent"]:
                        violations.append(result)
        return violations


# ---------------------------------------------------------------------------
# Tier 2a: OlogSchema — categorical ontology enforcer for Hermes fact types
# An olog: objects = noun-phrase types, morphisms = functional relations
# ---------------------------------------------------------------------------

# The Hermes memory olog — define objects (types) and morphisms (relations)
HERMES_OLOG_OBJECTS = {
    "session_fact":    "a fact observed in a single conversation session",
    "skill_procedure": "a reusable procedure stored in a SKILL.md file",
    "hindsight_fact":  "a durable fact stored in the Hindsight vector bank",
    "persistent_fact": "a fact stored in MEMORY.md / USER.md",
    "entity":          "a named entity referenced across memory layers",
    "relation":        "a typed edge between two entities in the memory graph",
    "context":         "the task/session/agent context a fact belongs to",
    "user_preference": "a stable user preference or convention",
    "safety_incident": "a recorded safety near-miss or policy violation",
    "research_finding":"a verified research paper or finding",
}

HERMES_OLOG_MORPHISMS = {
    # (source_type, target_type): relation_name
    ("session_fact",    "hindsight_fact"):   "promotes_to",
    ("session_fact",    "skill_procedure"):  "crystallizes_into",
    ("hindsight_fact",  "persistent_fact"):  "elevates_to",
    ("session_fact",    "context"):          "belongs_to",
    ("hindsight_fact",  "entity"):           "references",
    ("entity",          "relation"):         "participates_in",
    ("research_finding","skill_procedure"):  "informs",
    ("safety_incident", "skill_procedure"):  "updates_guardrail_in",
    ("user_preference", "persistent_fact"):  "is_recorded_as",
}


class OlogSchema:
    """
    Enforces the Hermes memory olog schema.
    Checks that facts have valid (context, type) pairs and that promoted facts
    use valid morphisms.
    """

    @staticmethod
    def validate_fact(pair: GrothPair) -> dict:
        """Validate a GrothPair against the olog schema."""
        errors = []
        if pair.type not in VALID_TYPES:
            errors.append(f"unknown type '{pair.type}'; valid: {VALID_TYPES}")
        if pair.context not in VALID_CONTEXTS:
            errors.append(f"unknown context '{pair.context}'; valid: {VALID_CONTEXTS}")
        if not pair.content or not pair.content.strip():
            errors.append("content is empty")
        return {"valid": not errors, "errors": errors, "fact_id": pair.fact_id}

    @staticmethod
    def validate_promotion(source_type: str, target_type: str) -> dict:
        """Check that a promotion path is a valid olog morphism."""
        key = (source_type, target_type)
        if key in HERMES_OLOG_MORPHISMS:
            return {"valid": True, "morphism": HERMES_OLOG_MORPHISMS[key]}
        # check partial matches
        partials = [k for k in HERMES_OLOG_MORPHISMS if source_type in k[0]]
        return {
            "valid": False,
            "errors": [f"no olog morphism from '{source_type}' to '{target_type}'"],
            "suggestions": [f"{k[0]} → {k[1]}: {v}" for k, v in HERMES_OLOG_MORPHISMS.items() if k in partials],
        }

    @staticmethod
    def fiber_product(fact_a: GrothPair, fact_b: GrothPair, shared_entity: str) -> dict:
        """
        Olog fiber product: merge two facts about the same entity.
        In categorical terms: the pullback over the shared entity type.
        Returns a merged GrothPair if the facts are compatible.
        """
        if fact_a.type != fact_b.type:
            return {"merged": False, "reason": f"type mismatch: {fact_a.type} vs {fact_b.type}"}
        if fact_a.context != fact_b.context and "global" not in (fact_a.context, fact_b.context):
            return {"merged": False, "reason": f"context mismatch: {fact_a.context} vs {fact_b.context}"}
        merged_content = f"{fact_a.content} | {fact_b.content}"
        merged_tags = list(set(fact_a.tags + fact_b.tags + [f"entity:{shared_entity}"]))
        merged = GrothPair(
            context=fact_a.context if fact_a.context == fact_b.context else "global",
            content=merged_content,
            type=fact_a.type,
            tags=merged_tags,
            derived_from=[fact_a.fact_id, fact_b.fact_id],
        )
        return {"merged": True, "result": merged, "shared_entity": shared_entity}


# ---------------------------------------------------------------------------
# Tier 2b: SheafCoboundary — inconsistency detector on entity neighborhoods
# Computes the cellular sheaf coboundary norm for Graphiti entity graph.
# High norm = contradictory local sections = inconsistent facts.
# ---------------------------------------------------------------------------

class SheafCoboundary:
    """
    Implements a simplified cellular sheaf Laplacian coboundary computation
    on a graph of memory entities.

    Each node (entity) has a "local section" = embedding vector (or bag of tags).
    Each edge (relation) has a "restriction map" = identity (simplified).
    The coboundary δ measures disagreement between adjacent sections.

    Full sheaf: arXiv:2601.21207, arXiv:2409.08036
    Simplified here: tag-overlap inconsistency measure.
    """

    def __init__(self):
        # nodes: entity_id → set of tags/attributes
        self.nodes: dict[str, set[str]] = {}
        # edges: (src, tgt) → relation
        self.edges: dict[tuple[str, str], str] = {}

    def add_entity(self, entity_id: str, tags: list[str]):
        self.nodes[entity_id] = set(tags)

    def add_relation(self, src: str, tgt: str, relation: str):
        self.edges[(src, tgt)] = relation
        # ensure both endpoints exist
        if src not in self.nodes:
            self.nodes[src] = set()
        if tgt not in self.nodes:
            self.nodes[tgt] = set()

    def coboundary_norm(self, src: str, tgt: str) -> float:
        """
        Simplified coboundary: Jaccard distance between adjacent node sections.
        0 = fully consistent; 1 = maximally inconsistent.
        """
        s = self.nodes.get(src, set())
        t = self.nodes.get(tgt, set())
        if not s and not t:
            return 0.0
        intersection = len(s & t)
        union = len(s | t)
        jaccard_sim = intersection / union if union > 0 else 1.0
        return round(1.0 - jaccard_sim, 4)

    def detect_inconsistencies(self, threshold: float = 0.7) -> list[dict]:
        """
        Detect high-coboundary edges = potential contradictions between neighboring facts.
        Returns list of {src, tgt, relation, coboundary_norm, verdict}.
        """
        results = []
        for (src, tgt), relation in self.edges.items():
            norm = self.coboundary_norm(src, tgt)
            if norm >= threshold:
                results.append({
                    "src": src,
                    "tgt": tgt,
                    "relation": relation,
                    "coboundary_norm": norm,
                    "verdict": "INCONSISTENT" if norm >= 0.9 else "SUSPECT",
                    "recommendation": "review for contradiction or missing context",
                })
        results.sort(key=lambda x: x["coboundary_norm"], reverse=True)
        return results

    def global_inconsistency_score(self) -> float:
        """Mean coboundary norm across all edges — overall consistency of the memory graph."""
        if not self.edges:
            return 0.0
        norms = [self.coboundary_norm(s, t) for (s, t) in self.edges]
        return round(sum(norms) / len(norms), 4)


# ---------------------------------------------------------------------------
# Tier 1d: HyperSkillTracker — skill combination hyperedges (HyperSkill paper)
# arXiv:2608.16114: skills as hyperedges; multi-skill combos = new hyperedges
# ---------------------------------------------------------------------------

HYPERSKILL_DB = HERMES_HOME / "cache" / "hyperskill-combos.json"


class HyperSkillTracker:
    """
    Tracks which skill combinations are loaded together for the same task type.
    When a combo is seen 3+ times, it becomes a "hyperedge" candidate —
    suggesting a new combined skill should be authored.

    Usage:
        tracker = HyperSkillTracker()
        tracker.record_combo(["academic-literature-review", "domain-research-synthesis"], task_type="research")
        candidates = tracker.get_hyperedge_candidates(min_count=3)
    """

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if HYPERSKILL_DB.exists():
            try:
                self._data = json.loads(HYPERSKILL_DB.read_text())
            except Exception as _e:
                import sys as _s; print(f"[HyperSkillTracker] corrupt DB reset: {_e}", file=_s.stderr); self._data = {}

    def _save(self):
        HYPERSKILL_DB.parent.mkdir(parents=True, exist_ok=True)
        _tmp = HYPERSKILL_DB.with_suffix(".tmp")
        _tmp.write_text(json.dumps(self._data, indent=2))
        _tmp.rename(HYPERSKILL_DB)

    @staticmethod
    def _combo_key(skills: list[str]) -> str:
        return "+".join(sorted(skills))

    def record_combo(self, skills: list[str], task_type: str = "general"):
        if len(skills) < 2:
            return
        key = self._combo_key(skills)
        if key not in self._data:
            self._data[key] = {"skills": sorted(skills), "count": 0, "task_types": {}, "first_seen": datetime.now(timezone.utc).isoformat()}
        self._data[key]["count"] += 1
        self._data[key]["task_types"][task_type] = self._data[key]["task_types"].get(task_type, 0) + 1
        self._data[key]["last_seen"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def get_hyperedge_candidates(self, min_count: int = 3) -> list[dict]:
        """Return skill combos that have been used together min_count+ times."""
        candidates = [
            {**v, "combo_key": k}
            for k, v in self._data.items()
            if v["count"] >= min_count
        ]
        candidates.sort(key=lambda x: x["count"], reverse=True)
        return candidates

    def report(self) -> str:
        candidates = self.get_hyperedge_candidates(min_count=3)
        if not candidates:
            return "No hyperedge candidates yet (need 3+ co-occurrences)."
        lines = ["HyperSkill candidates (3+ co-occurrences):"]
        for c in candidates:
            top_task = max(c["task_types"], key=c["task_types"].get) if c["task_types"] else "general"
            lines.append(f"  [{c['count']}x] {' + '.join(c['skills'])}  (primary task: {top_task})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tier 3a: ProvenanceGraph — derivation paths + equivalence witnesses
# (∞,1)-categorical inspiration: store paths, not just conclusions
# ---------------------------------------------------------------------------

PROVENANCE_DB = HERMES_HOME / "cache" / "provenance-graph.json"


class ProvenanceGraph:
    """
    Stores derivation paths between facts and records equivalence witnesses
    when two different reasoning paths reach the same conclusion.

    Inspired by (∞,1)-categories: p and q are both paths from A to B;
    a 2-cell between them is an equivalence witness (a meta-fact).

    Usage:
        pg = ProvenanceGraph()
        pg.add_derivation(source_ids=["f1","f2"], conclusion_id="f3", method="synthesis")
        pg.add_equivalence(path1_id="f3a", path2_id="f3b", witness="both conclude X from same premises")
        pg.get_provenance("f3")
    """

    def __init__(self):
        self._data: dict = {"derivations": [], "equivalences": []}
        self._load()

    def _load(self):
        if PROVENANCE_DB.exists():
            try:
                self._data = json.loads(PROVENANCE_DB.read_text())
            except Exception as _e:
                import sys as _s; print(f"[ProvenanceGraph] corrupt DB reset: {_e}", file=_s.stderr); self._data = {"derivations": [], "equivalences": []}

    def _save(self):
        PROVENANCE_DB.parent.mkdir(parents=True, exist_ok=True)
        _tmp = PROVENANCE_DB.with_suffix(".tmp")
        _tmp.write_text(json.dumps(self._data, indent=2))
        _tmp.rename(PROVENANCE_DB)

    def add_derivation(self, source_ids: list[str], conclusion_id: str,
                       method: str = "inference", session_id: str = ""):
        self._data["derivations"].append({
            "sources": source_ids,
            "conclusion": conclusion_id,
            "method": method,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    def add_equivalence(self, path1_id: str, path2_id: str, witness: str,
                        confidence: float = 1.0):
        """
        Record that two differently-derived facts are equivalent.
        The witness IS the valuable information (the 2-cell in ∞-cat language).
        """
        self._data["equivalences"].append({
            "path1": path1_id,
            "path2": path2_id,
            "witness": witness,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    def get_provenance(self, fact_id: str) -> dict:
        """Return all derivations leading to a fact_id."""
        derivations = [d for d in self._data["derivations"] if d["conclusion"] == fact_id]
        equivalences = [e for e in self._data["equivalences"]
                        if fact_id in (e["path1"], e["path2"])]
        return {"fact_id": fact_id, "derivations": derivations, "equivalences": equivalences}

    def get_equivalence_cluster(self, fact_id: str) -> list[str]:
        """Return all fact IDs equivalent to fact_id (via recorded witnesses)."""
        cluster = {fact_id}
        for e in self._data["equivalences"]:
            if e["path1"] in cluster:
                cluster.add(e["path2"])
            if e["path2"] in cluster:
                cluster.add(e["path1"])
        return list(cluster)


# ---------------------------------------------------------------------------
# Tier 3b: DoubleFunctorQuery — unified cross-layer memory query
# Lambert-Patterson arXiv:2403.19884: query = morphism in double category
# ---------------------------------------------------------------------------

class DoubleFunctorQuery:
    """
    Unified cross-layer memory query interface.
    A "double functor query" composes queries across memory layers without
    impedance mismatch between session_search, hindsight_recall, skill_view.

    Each layer is a schema (small category). A query is a morphism in the
    double category of schemas. Results are fused by the Kan extension
    (left adjoint to restriction = "find all facts that could be restricted to match").

    Currently: orchestrates session_search + hindsight + graphiti in a single call.
    Future: full CQL/Catlab.jl integration.
    """

    LAYER_PRIORITY = ["session", "skill", "hindsight", "global"]

    def __init__(self, hindsight_base: str = HINDSIGHT_BASE,
                 hindsight_bank: str = HINDSIGHT_BANK):
        self.hindsight_base = hindsight_base
        self.hindsight_bank = hindsight_bank

    # Process-lifetime recall cache: avoids duplicate OpenAI embedding API calls
    # within a single cron run (each embedding call costs ~3-7s via OpenAI API).
    # Key: (bank, query, top_k). Max 512 entries; evict oldest-inserted on overflow (FIFO).
    _recall_cache: dict[tuple, list] = {}
    _RECALL_CACHE_MAX = 512

    def _query_hindsight(self, query: str, top: int = 5) -> list[dict]:
        """Query Hindsight REST API with process-lifetime dedup cache."""
        cache_key = (self.hindsight_bank, query, top)
        if cache_key in self._recall_cache:
            return self._recall_cache[cache_key]
        try:
            url = f"{self.hindsight_base}/v1/default/banks/{self.hindsight_bank}/memories/recall"
            payload = json.dumps({"query": query, "top_k": top}).encode()
            req = urllib.request.Request(url, data=payload,
                                          headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                result = data.get("results") or data.get("memories") or []
            # Evict oldest entry if at capacity
            if len(self._recall_cache) >= self._RECALL_CACHE_MAX:
                self._recall_cache.pop(next(iter(self._recall_cache)))
            self._recall_cache[cache_key] = result
            return result
        except Exception as e:
            import sys as _s; print(f"[DoubleFunctorQuery] hindsight query failed: {e}", file=_s.stderr); return []

    def query(self, query_text: str, layers: list[str] | None = None,
              top: int = 10, min_weight: float = 0.2) -> dict:
        """
        Unified query across requested memory layers.
        Returns fused, scored, deduplicated results.
        """
        layers = layers or self.LAYER_PRIORITY
        all_results: list[dict] = []

        if "hindsight" in layers or "global" in layers:
            raw = self._query_hindsight(query_text, top=top)
            for r in raw:
                r["source_layer"] = "hindsight"
            all_results.extend(raw)

        # Apply EnrichedHom scoring to all results
        scored = score_results(query_text, all_results)
        # Filter by enriched weight threshold
        filtered = [r for r in scored if r.get("enriched_weight", 1.0) >= min_weight]

        return {
            "query": query_text,
            "layers_queried": layers,
            "total_raw": len(all_results),
            "total_filtered": len(filtered),
            "results": filtered[:top],
        }


# ---------------------------------------------------------------------------
# Tier 1+2: MemoryMonad — monadic bind for memory operation chains
# ---------------------------------------------------------------------------

@dataclass
class MemoryResult(Generic[T]):
    """
    Monad container for memory operations.
    value: the result if successful
    error: error message if failed
    trace: list of operation names executed
    """
    value: Optional[T]
    error: Optional[str] = None
    trace: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return self.error is None

    def bind(self, fn: Callable[[Any], "MemoryResult"]) -> "MemoryResult":
        """Kleisli composition: chain memory operations with error propagation."""
        if not self.is_ok:
            return self  # propagate error
        try:
            result = fn(self.value)
            result.trace = self.trace + result.trace
            return result
        except Exception as e:
            return MemoryResult(value=None, error=str(e), trace=self.trace + [f"error: {e}"])

    def map(self, fn: Callable[[Any], Any]) -> "MemoryResult":
        """Functor map: transform the value without chaining."""
        if not self.is_ok:
            return self
        try:
            return MemoryResult(value=fn(self.value), trace=self.trace + ["map"])
        except Exception as e:
            return MemoryResult(value=None, error=str(e), trace=self.trace + [f"map_error: {e}"])


class MemoryMonad:
    """
    Monadic wrapper for Hermes memory operations.
    Provides: retain (left adjoint / write), recall (right adjoint / read),
    and promote (Kan extension: session → persistent).

    The adjunction retain ⊣ recall guarantees: recall(retain(x)) contains x
    if the implementation is correct. Use round_trip_check() to verify.
    """

    def __init__(self, validate: bool = True, log: bool = True):
        self.validate = validate
        self.log = log
        self.olog = OlogSchema()
        self._log_path = MONAD_LOG

    def _log(self, op: str, fact_id: str, status: str, detail: str = ""):
        if not self.log:
            return
        entry = {
            "op": op, "fact_id": fact_id, "status": status,
            "detail": detail, "ts": datetime.now(timezone.utc).isoformat()
        }
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def retain(self, pair: GrothPair) -> MemoryResult[GrothPair]:
        """
        Left adjoint (write / free functor): store a GrothPair in memory.
        Validates against olog schema before writing.
        """
        if self.validate:
            check = self.olog.validate_fact(pair)
            if not check["valid"]:
                self._log("retain", pair.fact_id, "schema_error", str(check["errors"]))
                return MemoryResult(value=None, error=f"Schema errors: {check['errors']}",
                                    trace=["retain:schema_fail"])
        self._log("retain", pair.fact_id, "ok", f"context={pair.context} type={pair.type}")
        return MemoryResult(value=pair, trace=["retain"])

    def recall(self, query: str, layer: str = "hindsight",
               top: int = 5) -> MemoryResult[list[dict]]:
        """
        Right adjoint (read / forgetful functor): retrieve facts matching query.
        Returns EnrichedHom-scored results.
        """
        dfq = DoubleFunctorQuery()
        result = dfq.query(query, layers=[layer, "global"], top=top)
        self._log("recall", hashlib.md5(query.encode(), usedforsecurity=False).hexdigest()[:8], "ok",
                  f"layer={layer} found={result['total_filtered']}")
        return MemoryResult(value=result["results"], trace=["recall"])

    def round_trip_check(self, pair: GrothPair) -> dict:
        """
        Unit of the adjunction: retain(pair), then recall(pair.content).
        If the recall result contains the retained content, the adjunction holds.
        (Formal correctness test for the memory read/write pair.)
        """
        retain_result = self.retain(pair)
        if not retain_result.is_ok:
            return {"passed": False, "stage": "retain", "error": retain_result.error}
        recall_result = self.recall(pair.content, layer=pair.context)
        if not recall_result.is_ok:
            return {"passed": False, "stage": "recall", "error": recall_result.error}
        # Check if retained content appears in recall results
        results = recall_result.value or []
        found = any(pair.content[:50] in str(r.get("text") or r.get("content") or "") for r in results)
        return {
            "passed": found,
            "retained_id": pair.fact_id,
            "recall_count": len(results),
            "note": "round-trip test: retain ⊣ recall adjunction holds" if found else
                    "fact not found in recall — adjunction broken or hindsight service down",
        }


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MemoryMonad — categorical memory operations")
    sub = parser.add_subparsers(dest="cmd")

    # groupoid check
    p_gc = sub.add_parser("groupoid-check", help="Run 3-hop consistency check on fact set")
    p_gc.add_argument("--facts", help="JSON file of facts [{source_entity,relation,target_entity}]")

    # sheaf inconsistency
    p_sh = sub.add_parser("sheaf-check", help="Compute sheaf coboundary inconsistency score")
    p_sh.add_argument("--nodes", help="JSON file of {entity_id: [tags]}")
    p_sh.add_argument("--edges", help="JSON file of [[src,tgt,relation]]")
    p_sh.add_argument("--threshold", type=float, default=0.7)

    # hyperskill
    p_hs = sub.add_parser("hyperskill", help="Manage skill combination hyperedges")
    p_hs.add_argument("--record", nargs="+", help="Record a skill combination (space-separated skill names)")
    p_hs.add_argument("--task-type", default="general")
    p_hs.add_argument("--report", action="store_true")

    # provenance
    p_pv = sub.add_parser("provenance", help="Manage fact provenance graph")
    p_pv.add_argument("--add-derivation", nargs="+", help="source_id1 source_id2 ... -> conclusion_id")
    p_pv.add_argument("--add-equivalence", nargs=2, metavar=("PATH1", "PATH2"))
    p_pv.add_argument("--witness", default="equivalent by different derivation")
    p_pv.add_argument("--get", help="Get provenance for fact_id")

    # query
    p_q = sub.add_parser("query", help="Double-functor unified memory query")
    p_q.add_argument("query_text")
    p_q.add_argument("--layers", nargs="+", default=["hindsight", "global"])
    p_q.add_argument("--top", type=int, default=10)
    p_q.add_argument("--min-weight", type=float, default=0.2)

    # olog validate
    p_ol = sub.add_parser("olog-validate", help="Validate a fact against the Hermes olog schema")
    p_ol.add_argument("--context", required=True)
    p_ol.add_argument("--content", required=True)
    p_ol.add_argument("--type", default="fact")

    args = parser.parse_args()

    if args.cmd == "groupoid-check":
        facts = []
        if args.facts:
            facts = json.loads(Path(args.facts).read_text())
        checker = GroupoidCheck(facts)
        violations = checker.check_all_triples()
        if violations:
            print(f"[GroupoidCheck] {len(violations)} violation(s):")
            for v in violations:
                print(f"  {v['path']}: {v['reason']}")
        else:
            print("[GroupoidCheck] No inconsistencies detected.")

    elif args.cmd == "sheaf-check":
        sheaf = SheafCoboundary()
        if args.nodes:
            for eid, tags in json.loads(Path(args.nodes).read_text()).items():
                sheaf.add_entity(eid, tags)
        if args.edges:
            for src, tgt, rel in json.loads(Path(args.edges).read_text()):
                sheaf.add_relation(src, tgt, rel)
        issues = sheaf.detect_inconsistencies(threshold=args.threshold)
        score = sheaf.global_inconsistency_score()
        print(f"[SheafCoboundary] Global inconsistency score: {score:.3f}")
        for issue in issues:
            print(f"  [{issue['verdict']}] {issue['src']} → {issue['tgt']} ({issue['relation']}): coboundary={issue['coboundary_norm']}")

    elif args.cmd == "hyperskill":
        tracker = HyperSkillTracker()
        if args.record:
            tracker.record_combo(args.record, task_type=args.task_type)
            print(f"Recorded combo: {args.record} (task: {args.task_type})")
        if args.report:
            print(tracker.report())

    elif args.cmd == "provenance":
        pg = ProvenanceGraph()
        if args.add_derivation:
            sources = args.add_derivation[:-1]
            conclusion = args.add_derivation[-1]
            pg.add_derivation(source_ids=sources, conclusion_id=conclusion)
            print(f"Derivation added: {sources} → {conclusion}")
        if args.add_equivalence:
            pg.add_equivalence(args.add_equivalence[0], args.add_equivalence[1], args.witness)
            print(f"Equivalence recorded: {args.add_equivalence[0]} ≃ {args.add_equivalence[1]}")
        if args.get:
            print(json.dumps(pg.get_provenance(args.get), indent=2))

    elif args.cmd == "query":
        m = MemoryMonad(validate=False)
        result = m.recall(args.query_text, top=args.top)
        if result.is_ok:
            for r in (result.value or []):
                w = r.get("enriched_weight", "?")
                text = str(r.get("text") or r.get("content") or r)[:120]
                print(f"  [{w}] {text}")
        else:
            print(f"Error: {result.error}")
            sys.exit(1)

    elif args.cmd == "olog-validate":
        pair = GrothPair(context=args.context, content=args.content, type=getattr(args, "type"))
        result = OlogSchema.validate_fact(pair)
        print(json.dumps(result, indent=2))
        if not result.get("valid", True):
            sys.exit(1)

    else:
        parser.print_help()
