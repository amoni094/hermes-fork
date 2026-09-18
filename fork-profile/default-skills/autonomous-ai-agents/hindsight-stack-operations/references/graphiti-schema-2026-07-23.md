# Graphiti Schema Changes — 2026-07-23

Prompted by review of Microsoft Ontology-Playground (https://github.com/microsoft/Ontology-Playground).

## What was added

### New entity type: Constraint
- Fields: scope (str|None), constraint_type (str|None), description (str)
- Distinct from Requirement: "what must not be violated" vs "what must exist"
- Use for: hard limits, security boundaries, architectural rules, policy constraints
- Added to config-hermes.yaml entity_types list

### New edge type: Governs
- Fields: enforcement (str|None)
- Connects Constraint/Procedure → Project/Task/Tool/Entity
- Added to config-hermes.yaml edge_types + edge_type_map

### Requirement: added `priority` field
- Optional str field (e.g. "critical", "high", "medium", "low")

### Enriched previously-bare edge types (were `...`, now have contextual fields)
| Edge | Fields Added |
|------|-------------|
| LocatedAt | since (str\|None), context (str\|None) |
| ParticipatesIn | role (str\|None), status (str\|None) |
| Owns | since (str\|None), context (str\|None) |
| Configures | parameter (str\|None), value (str\|None) |
| BelongsTo | role (str\|None) |
| Produces | output_type (str\|None) |

## Key lesson from Ontology-Playground review

The main insight from the RDF ontology catalogue was **typed properties on relationships** —
bare edge types produce no extractable attributes. The OWL pattern consistently shows that
useful graphs need edge-level attributes, not just node-level ones.

The Constraint/Requirement split was also a clear pattern across finance (FIBO) and healthcare
ontologies: "what must exist" (Requirement) vs "what must not be violated" (Constraint).

## What was NOT worth implementing
- OWL class hierarchy / rdfs:subClassOf (Graphiti uses LLM extraction, not OWL inference)
- RDF/XML export (irrelevant to this stack)
- Azure Fabric IQ data source mappings (Azure-specific)
- Cardinality annotations (Graphiti handles multiplicity at query time)
- Domain-specific entity types (retail Customer, Order, Product etc.) — not relevant

## File locations
- Entity types: ~/graphiti/mcp_server/src/models/entity_types.py
- Edge types: ~/graphiti/mcp_server/src/models/edge_types.py
- Config: ~/graphiti/mcp_server/config/config-hermes.yaml
