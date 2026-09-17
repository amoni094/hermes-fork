# Semantic Proximity Force Layout for Knowledge Graph Visualizers

Reference for D3.js and 3d-force-graph semantic force tuning.
Derived from THOTH (https://github.com/amoni094/thoth) — comparative religion KG, Jul 2026.

## Core principle

Link distance = inversely proportional to semantic tightness.
Bridge/structural edges (fromTradition, containsMotif) use LONG springs to avoid
distorting semantic clusters they're only connecting structurally.

## Tuned parameters (religion corpus — 285 node summary, 847 full)

| Relation | Distance | Strength | Notes |
|---|---|---|---|
| sameConceptAs | 35px | 0.95 | Near-touching — equivalent concepts |
| cognateOf | 45px | 0.90 | Deity cognates cluster together (Zeus/Jupiter/Dyaus) |
| parallelPassage | 70px | 0.75 | Near-identical text passages |
| influencedBy | 90px | 0.65 | Historical lineage |
| deityFunctionOf | 80px | 0.55 | Deity→tradition anchor |
| strongMotif | 110px | 0.45 | Primary motif expression |
| parallelTo | 130px | 0.35 | Loose structural parallel |
| hasThemeVocab | 175px | 0.20 | Theme spoke — long so themes breathe |
| sharesConcept | 160px | 0.15 | Capped bridge edge |
| fromTradition | 190px | 0.12 | Bridge-only structural link |
| containsMotif | 200px | 0.10 | Bridge-only structural link |

## Degree-scaled charge

Flat charge gives hubs and leaves the same repulsion — hubs crowd their neighbours.
Scale by degree so hubs breathe:

```javascript
d3.forceManyBody().strength(n => {
  const base = isSummary ? -180 : -60;
  return base * (1 + Math.log((n._deg || 1) + 1) * 0.4);
}).distanceMax(500)
```

Hub with degree 20 repels ~3× more than leaf with degree 1.

## Degree-scaled collision

```javascript
d3.forceCollide().radius(n => nodeR(n) * 2.2 + 4).strength(0.7)
```

## alphaDecay

0.015 (vs D3 default 0.028) — longer settling finds a better energy minimum.
Worth the extra ~2s for semantic graphs where cluster positioning matters.

## Jaccard Similarity Force (node_similarity.json)

Nodes with high shared-neighbour overlap attract without a direct edge.
Target distance = 40 + (1-jaccard) × 120px.
Jaccard 1.0 (karma↔dualism, dharma↔karma) → 40px (near-touching).
Jaccard 0.25 (threshold) → 130px (mild pull).

```javascript
// Load at startup
const jaccardPairs = await fetch('ontology/node_similarity.json').then(r=>r.json());
window._jaccardPairs = jaccardPairs;

// Build per-tier (after graph data loaded and nodeById populated)
const activePairs = (window._jaccardPairs || [])
  .filter(p => nodeById[p.source] && nodeById[p.target])
  .map(p => ({a: nodeById[p.source], b: nodeById[p.target], jac: p.jaccard}));

// 2D force
simulation.force('jaccard', alpha => {
  for (const {a, b, jac} of activePairs) {
    const dx = b.x-a.x, dy = b.y-a.y;
    const dist = Math.sqrt(dx*dx + dy*dy) || 1;
    const target = 40 + (1-jac) * 120;
    const f = (dist-target)/dist * alpha * jac * 0.3;
    a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f;
  }
});

// 3D force (add vz component)
Graph.d3Force('jaccard', alpha => {
  for (const {a, b, jac} of activePairs) {
    const dx=b.x-a.x, dy=b.y-a.y, dz=(b.z||0)-(a.z||0);
    const dist = Math.sqrt(dx*dx+dy*dy+dz*dz) || 1;
    const target = 40 + (1-jac) * 140;
    const f = (dist-target)/dist * alpha * jac * 0.25;
    a.vx+=dx*f; a.vy+=dy*f; a.vz=(a.vz||0)+dz*f;
    b.vx-=dx*f; b.vy-=dy*f; b.vz=(b.vz||0)-dz*f;
  }
});
```

## Build node_similarity.json

```python
from collections import defaultdict
import json

adj = defaultdict(set)
for l in links:
    adj[l['source']].add(l['target']); adj[l['target']].add(l['source'])

SEMANTIC_TYPES = {'NarrativeMotif', 'Concept', 'Theme'}
candidates = [n for n in nodes if n.get('type') in SEMANTIC_TYPES]
pairs = []
for i, a in enumerate(candidates):
    for b in candidates[i+1:]:
        shared = len(adj[a['id']] & adj[b['id']])
        if shared < 2: continue
        union = len(adj[a['id']] | adj[b['id']])
        jac = shared / union if union else 0
        if jac >= 0.25:
            pairs.append({'source': a['id'], 'target': b['id'],
                          'jaccard': round(jac,3), 'shared': shared,
                          'relation': 'jaccard_sim'})

# Deduplicate + cap
seen, deduped = set(), []
for p in sorted(pairs, key=lambda x: -x['jaccard']):
    key = tuple(sorted([p['source'], p['target']]))
    if key not in seen: seen.add(key); deduped.append(p)

with open('ontology/node_similarity.json','w') as f:
    json.dump(deduped[:300], f, separators=(',',':'))
```

## 3D graph CDN

```html
<script src="https://unpkg.com/three@0.158.0/build/three.min.js"></script>
<script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>
```

Same `{nodes, links}` JSON format as D3. Key differences:
- `.nodeVal()` = volume (not radius); use `Math.pow(r,2) * 0.5`
- Canvas sprite labels via `THREE.Sprite + CanvasTexture`; set `.nodeThreeObjectExtend(true)`
- Auto-rotate: `Graph.onEngineTick(() => { angle+=0.002; Graph.cameraPosition({x:600*sin(angle), z:600*cos(angle)}); })`
- Camera fly-to: `Graph.cameraPosition({x:nx*r, y:ny*r, z:nz*r}, node, 1200)`
- Forces: `Graph.d3Force('charge', d3.forceManyBody()...)` — identical D3 API

## GitHub publish checklist for a local KG project

1. Export to clean dir (NOT the home-dir git root if that exists)
2. Include: HTML viewers, ontology/ JSONs + TTLs, curated scripts
3. Exclude: raw corpus (copyright + size), vector DB, logs, state files, old versions
4. .gitignore: corpus dirs, chroma_db, *.log, vectorize_state.json, download_state.json
5. README: name+acronym, how to run (python3 -m http.server), node/edge tables, methodology
6. `git init && git add -A && git commit -m "Initial release: <name>"`
7. `gh repo create <user>/<name> --public --source=. --remote=origin --push`
8. Verify: `gh repo view --json name,visibility,url`

Typical size for ontology-only export (no corpus): 2-5MB.
