# Jaccard Similarity Force (node_similarity.json)

Nodes with many shared neighbours should attract even without a direct edge.
Build a JSON file of high-Jaccard pairs and apply as a custom D3 force.

## Build node_similarity.json (Python)

```python
from collections import defaultdict
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
                          'jaccard': round(jac,3), 'shared': shared})
# Deduplicate + cap at 300
seen, deduped = set(), []
for p in sorted(pairs, key=lambda x: -x['jaccard']):
    key = tuple(sorted([p['source'], p['target']]))
    if key not in seen: seen.add(key); deduped.append(p)
with open('ontology/node_similarity.json','w') as f:
    json.dump(deduped[:300], f, separators=(',',':'))
```

## Apply as custom D3 force (browser)

```javascript
// Load alongside graph JSON: fetch('ontology/node_similarity.json')
// Build activePairs from pairs whose both nodes are in current vis
const activePairs = jaccardPairs
  .filter(p => nodeById[p.source] && nodeById[p.target])
  .map(p => ({a: nodeById[p.source], b: nodeById[p.target], jac: p.jaccard}));

simulation.force('jaccard', alpha => {
  for (const {a, b, jac} of activePairs) {
    const dx=b.x-a.x, dy=b.y-a.y, dist=Math.sqrt(dx*dx+dy*dy)||1;
    const target = 40 + (1-jac)*120;  // Jaccard 1.0 → 40px, 0.25 → 130px
    const f = (dist-target)/dist * alpha * jac * 0.3;
    a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f;
  }
});
// For 3D: same logic + vz component
```

## Real examples from religion corpus

- `karma↔dualism` (Jaccard 1.0) — these sit near-touching in the layout
- `dharma↔karma` (0.86)
- `virgin birth↔world egg` (0.86)

## 3D Graph (3d-force-graph + Three.js)

CDN — no install needed:
```html
<script src="https://unpkg.com/three@0.158.0/build/three.min.js"></script>
<script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>
```

Data format: same `{nodes, links}` JSON as D3 — no conversion needed.
Key differences from 2D:
- `.nodeVal()` controls sphere volume (not radius)
- Labels use `THREE.Sprite` + `CanvasTexture` (see `references/religion-graph-v3-spec.md`)
- Auto-rotate via `.onEngineTick()` — increment angle, set `Graph.cameraPosition()`
- Camera fly-to: `Graph.cameraPosition({x,y,z}, focusNode, durationMs)`
- Forces set via `Graph.d3Force('charge', d3.forceManyBody()...)` — identical API

Semantic proximity forces apply identically in 3D. The Jaccard force adds a `vz` component.
See `references/religion-graph-v3-spec.md` §3D Viewer for full API patterns.
