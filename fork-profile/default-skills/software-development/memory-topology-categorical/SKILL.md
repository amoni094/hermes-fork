---
name: memory-topology-categorical
description: >-
  Use when designing, extending, or debugging Hermes memory topology using
  group theory and category theory principles. Covers GrothPair context pairing,
  EnrichedHom scoring, GroupoidCheck consistency, SheafCoboundary inconsistency
  detection, OlogSchema validation, MemoryMonad composition, HyperSkillTracker,
  ProvenanceGraph, and DoubleFunctorQuery.
category: software-development
triggers:
  - memory topology
  - category theory memory
  - groupoid consistency
  - sheaf inconsistency
  - olog schema
  - memory monad
  - provenance graph
  - hyperskill
  - enriched hom
  - grothendieck context
related_skills:
  - hermes-memory-surface-selection
  - hindsight-stack-operations
  - memory-layer-gate
  - graphiti-mcp-setup
  - agent-memory-consolidation
---

# Memory Topology — Categorical & Group-Theoretic Design

Script: `~/.hermes/scripts/memory-monad.py`
Research report: `/tmp/group_cat_theory_memory_topology.md` (41KB, 26 verified papers)

## Components and Usage

### Tier 1a: GrothPair — Grothendieck context pairing

Every memory fact is a pair (context, content), never floating content.
Formally: an object in the total category ∫F (Grothendieck construction).

```python
from memory_monad import GrothPair
p = GrothPair(context="session", content="...", type="research_finding")
# fact_id is deterministic SHA-256[:16] of context+content
```

Valid contexts: session, skill, hindsight, global, cron
Valid types: fact, preference, procedure, event, entity, relation, constraint,
             observation, reflection, plan, research_finding, safety_incident, user_preference

### Tier 1b: EnrichedHom — (confidence, age_days) scoring

Enriches memory retrieval over [0,1]: weight = confidence × exp(-0.02 × age_days).
Half-life ≈ 35 days. Already wired into unified-recall.py fuse_results().

```python
from memory_monad import EnrichedHom, score_results
hom = EnrichedHom(source_query="...", target_fact="...", confidence=0.85, age_days=5)
print(hom.weight)      # 0.7691
print(hom.distance)    # 0.2309 (Lawvere metric)
```

unified-recall.py now emits `enriched_weight` and `enriched_distance` on every result.

### Tier 1c: GroupoidCheck — 3-hop consistency

If A→B and B→C exist with relation "supports", then A→C should also have "supports".
Violations = inconsistencies in the memory groupoid.

```python
from memory_monad import GroupoidCheck
c = GroupoidCheck()
c.add_fact("A", "supports", "B")
c.add_fact("B", "supports", "C")
violations = c.check_all_triples()  # returns list of violation dicts

# CLI:
python3 ~/.hermes/scripts/memory-monad.py groupoid-check --facts facts.json
```

Supported relations and their inverses: supports/is_supported_by, contradicts (symmetric),
generalizes/specializes, causes/is_caused_by, precedes/follows, is_part_of/has_part.

### Tier 1d: HyperSkillTracker — skill combination hyperedges

When the same skill combo is loaded 3+ times for the same task type, flag as
hyperedge candidate (suggests authoring a combined skill). (arXiv:2608.16114)

```bash
# Record from working-memory.py (automatically wires into WM session doc):
python3 ~/.hermes/scripts/working-memory.py record-skill-combo \
  --skills academic-literature-review domain-research-synthesis \
  --task-type research --session SESSION_ID

# Report candidates:
python3 ~/.hermes/scripts/memory-monad.py hyperskill --report
```

Data stored at: `~/.hermes/cache/hyperskill-combos.json`

### Tier 2a: OlogSchema — categorical ontology enforcer

Validates facts against the Hermes memory olog (small category).
Objects = noun-phrase types; morphisms = functional relations between types.
Fiber product = fact merge over shared entity.

```python
from memory_monad import OlogSchema, GrothPair
result = OlogSchema.validate_fact(pair)           # {"valid": bool, "errors": [...]}
result = OlogSchema.validate_promotion("session_fact", "hindsight_fact")  # check morphism
merge  = OlogSchema.fiber_product(p1, p2, shared_entity="entity_name")   # pullback

# CLI:
python3 ~/.hermes/scripts/memory-monad.py olog-validate \
  --context session --content "..." --type research_finding
```

### Tier 2b: SheafCoboundary — inconsistency detector

Computes cellular sheaf coboundary norm on entity neighborhoods.
High norm (>0.7) = contradictory facts between adjacent entities. (arXiv:2601.21207)

```python
from memory_monad import SheafCoboundary
sh = SheafCoboundary()
sh.add_entity("entity_id", ["tag1", "tag2"])
sh.add_relation("src", "tgt", "supports")
issues = sh.detect_inconsistencies(threshold=0.7)   # list of {src, tgt, norm, verdict}
score  = sh.global_inconsistency_score()            # 0 = consistent, 1 = maximal contradiction

# CLI:
python3 ~/.hermes/scripts/memory-monad.py sheaf-check \
  --nodes nodes.json --edges edges.json --threshold 0.7
```

### Tier 2c: MemoryMonad — monadic bind for memory operation chains

Wraps retain/recall as a monad with error propagation. Kleisli composition
chains memory operations; bind() threads errors. OlogSchema validation on retain.

```python
from memory_monad import MemoryMonad, GrothPair
m = MemoryMonad()
result = m.retain(GrothPair(context="session", content="...", type="fact"))
result2 = result.bind(lambda f: m.recall(f.content))
check = m.round_trip_check(pair)  # adjunction correctness test
```

round_trip_check() verifies retain ⊣ recall adjunction: writes then reads back.
If failed, memory service may be down or content too short for retrieval.

### Tier 3a: ProvenanceGraph — derivation paths + equivalence witnesses

Stores derivation paths between facts and equivalence witnesses (2-cells).
Two different reasoning paths reaching the same conclusion should both be stored
along with a witness asserting their equivalence. (∞,1)-category inspiration.

```python
from memory_monad import ProvenanceGraph
pg = ProvenanceGraph()
pg.add_derivation(source_ids=["f1","f2"], conclusion_id="f3", method="synthesis")
pg.add_equivalence("f3a", "f3b", witness="both conclude X from same premises")
prov = pg.get_provenance("f3")
cluster = pg.get_equivalence_cluster("f3a")  # all equivalent fact IDs

# CLI:
python3 ~/.hermes/scripts/memory-monad.py provenance \
  --add-derivation f1 f2 f3 --get f3
```

Data stored at: `~/.hermes/cache/provenance-graph.json`

### Tier 3b: DoubleFunctorQuery — unified cross-layer memory query

Queries multiple memory layers (session, skill, hindsight, global) in one call.
Fuses results with EnrichedHom scoring. Inspired by arXiv:2403.19884 (Topos Institute).
Currently: hindsight REST API with enriched scoring. Future: full CQL/Catlab.jl.

```python
from memory_monad import DoubleFunctorQuery
dfq = DoubleFunctorQuery()
result = dfq.query("query text", layers=["hindsight", "global"], top=10, min_weight=0.2)

# CLI:
python3 ~/.hermes/scripts/memory-monad.py query "what is the A1-localization?" \
  --layers hindsight global --top 10 --min-weight 0.2
```

## Integration Points

unified-recall.py: EnrichedHom scoring wired into fuse_results() (lines 397-421).
  Every result now has: enriched_weight, enriched_distance, _age_days.

working-memory.py: Schema v3 adds groth_context and skill_combos_recorded fields.
  New subcommand: record-skill-combo for HyperSkill tracking.

l1-hypermem-promote.py: HyperMem episode hyperedge grouping (arXiv:2604.08256).
  Run at session end: python3 l1-hypermem-promote.py [--dry-run] [--min-entities 3]
  Groups co-occurring Graphiti episodes into HYPEREDGE nodes for n-ary retrieval.

concept-lattice-index.py: ContextRAG FCA concept lattice nightly index (arXiv:2605.19735).
  Nightly cron: python3 concept-lattice-index.py [--clusters 16] [--min-support 3]
  Builds fuzzy concept lattice; writes bridge nodes back to Hindsight.
  Query activation: concept_lattice_index.query_activate(query_text) for retrieval expansion.

profinite-thread-check.py: Profinite thread-validity + H^2 obstruction + Galois view lattice.
  python3 profinite-thread-check.py check --fact "..." --layer session
  python3 profinite-thread-check.py obstruction-report
  python3 profinite-thread-check.py triple-check --fact-a A --fact-b B --fact-c C
  python3 profinite-thread-check.py view-lattice

## Mathematical Sources (verified papers)

Category theory:
  arXiv:1009.1166  Spivak (2010) — functorial data migration
  arXiv:2403.19884 Lambert & Patterson (2024) — double-functorial semantics
  arXiv:1102.1889  Spivak & Kent (2011) — ologs
  arXiv:1310.0605  Uustalu & Vene — monads/comonads
  arXiv:2508.08293 Mahadevan (2025) — topos theory for LLMs
  arXiv:2601.21207 Hu (2026) — sheaf-theoretic GNNs
  arXiv:2409.08036 Braithwaite et al. (2024) — heterogeneous sheaf NNs

Group theory:
  arXiv:2606.26212 Weissblat (2026) — GNNs on Cayley graphs
  arXiv:2608.22513 Zhang & Zhang (2026) — Galois equivalent representations
  ACM CIKM 2021   — KG embeddings as groupoid representations
  arXiv:1909.05100 — group rep theory for KG embedding

Applied memory:
  arXiv:2604.08256 HyperMem (ACL 2026) — hypergraph conversational memory, 92.7% LoCoMo
  arXiv:2608.16114 HyperSkill (Aug 2026) — skill hypergraph, +11 GAIA
  arXiv:2602.05665 Graph-based Agent Memory survey (Feb 2026) — taxonomy
  arXiv:2605.19735 ContextRAG (May 2026) — FCA concept lattice, +3.9 pp F1
  arXiv:2607.01773 Verifiable FCA (2026) — ontology gate via implications
  arXiv:2605.14033 Sheaf obstruction (May 2026) — transport vs extend gate
  arXiv:2301.12929 Knowledge Persistence (WWW 2023) — PH barcode as KG health metric

Group theory (subagent-verified nLab + arXiv):
  arXiv:2502.18663 CayleyPy (2026) — RL pathfinding on Cayley graphs
  arXiv:2307.14658 Jain et al. (2026) — H^2(BG;A) classifies extensions
  arXiv:2302.01583 Holkar-Hossain (2023) — topological fundamental groupoid
  arXiv:2309.05039 Li-Zhang (2025) — inverse-limit topology / profinite descent
  arXiv:2302.13719 Wittenberg (2025) — inverse Galois problem  arXiv:2608.16114 — HyperSkill (skill hyperedge tracking)
  arXiv:2604.08256 — HyperMem (hypergraph long-term memory)
  arXiv:2602.05665 — graph-based agent memory survey

## Pitfalls

- GroupoidCheck is O(n^3) in entities — only run on focused subgraphs (<100 entities).
- SheafCoboundary uses tag-Jaccard as a proxy for section disagreement.
  Full implementation requires vector embeddings per entity (see arXiv:2601.21207).
- ProvenanceGraph is session-local; cross-session provenance requires Graphiti episodes.
- DoubleFunctorQuery requires Hindsight REST API at localhost:9177.
  Check with: hindsight-ensure.sh before calling.
- round_trip_check() often fails if Hindsight is not running — not a bug in the monad.
- memory-monad.py must be loaded via importlib with a named ModuleType (not importlib alone)
  due to Python 3.14 dataclass __module__ behavior. See /tmp/test_memory_monad.py for pattern.

## Extending

Add new olog types: extend VALID_TYPES tuple and HERMES_OLOG_OBJECTS dict.
Add new relations: extend GroupoidCheck.RELATION_INVERSES dict.
Add new morphisms: extend HERMES_OLOG_MORPHISMS dict.
Full sheaf implementation: pip install sheaf-nn (PyTorch Geometric extension).
