# Knowledge Graph Browser Visualization — Best Practices

*Research compiled July 2026 from arxiv:2304.01311, arxiv:2412.05289, yFiles DH guide,
Graphology/Sigma.js docs, Palladio/nodegoat/Kumu comparisons, and a working D3-canvas
implementation for the Comparative Religion corpus (789 nodes, 3709 edges).*

Full research notes also at: `~/knowledge-graph-best-practices.md`

---

## Library Selection by Scale

| Nodes | Edges | Recommended                | Notes                                                  |
|-------|-------|----------------------------|--------------------------------------------------------|
| <300  | <2K   | D3 SVG force-directed       | Simple, debuggable, good for publications              |
| 300–2K| 2K–10K| **D3 Canvas** (this corpus) | 10–50× faster than SVG; no new deps                   |
| 2K–50K| 10K+  | Sigma.js v2/v3 + Graphology | WebGL renderer; humanities pedigree (Gephi ecosystem)  |
| 50K+  | 100K+ | Three.js / Pixi.js          | Full GPU; needs custom layout & interaction work       |

**Practical observation (789n/3709e):** D3 Canvas at 60fps with no issues. SVG at this
count would be sluggish — the canvas switch is the single highest-impact change.
WebGL (Sigma.js) would be faster but adds dependency complexity for marginal gain.

---

## Data Structure: Typed Adjacency Index

Build at load time (O(e) once → O(1) per query):

```javascript
// Map<nodeId, Map<relationType, neighborId[]>>
const adjIndex = new Map();
allNodes.forEach(n => adjIndex.set(n.id, new Map()));
allLinks.forEach(l => {
  if (!adjIndex.get(l.source).has(l.relation))
    adjIndex.get(l.source).set(l.relation, []);
  adjIndex.get(l.source).get(l.relation).push(l.target);
  // same for target → source (undirected)
});

// Usage: get all parallelPassage neighbors in O(1)
const parallels = adjIndex.get(nodeId).get('parallelPassage') ?? [];
```

Don't scan the edge array for hover/click events — at 3700 edges firing at 60fps,
this is 222,000 scans/second.

---

## JSON Injection Pitfall (Self-Contained HTML)

When embedding a large JSON blob as a JS variable in an HTML template,
**do NOT use `re.sub()`** — JSON contains `\u` unicode escapes and backslashes
that Python's regex engine treats as invalid escape sequences:

```python
# WRONG — fails with re.PatternError: bad escape \u at position N
html = re.sub(r'const DATA = {.*?};', f'const DATA = {data_json};', html, flags=re.DOTALL)

# RIGHT — walk brace depth manually
idx = html.find('const GRAPH_DATA = {')
depth, i = 0, idx + len('const GRAPH_DATA = ')
while i < len(html):
    if html[i] == '{': depth += 1
    elif html[i] == '}':
        depth -= 1
        if depth == 0: break
    i += 1
html = html[:idx] + 'const GRAPH_DATA = ' + data_json + html[i+1:]

# OR — use a unique non-JSON sentinel that re.sub can safely replace
# In template: const GRAPH_DATA = __GRAPH_DATA_PLACEHOLDER__;
html = html.replace('__GRAPH_DATA_PLACEHOLDER__', data_json)
# replace() is literal string matching — no regex engine, no escape issues
```

The sentinel approach (`__GRAPH_DATA_PLACEHOLDER__`) is cleanest and most robust.

---

## Community Detection: Python-Side Louvain

**Pre-compute communities in Python** (not in-browser JS):

```python
import community as community_louvain  # python-louvain package
import networkx as nx

pip_install = "python3 -m pip install python-louvain networkx"

G = nx.Graph()
for l in links:
    w = {'strongMotif':4,'parallelPassage':5,'cognateOf':3,
         'fromTradition':3,'sameConceptAs':4,'influencedBy':2,
         'sharesConcept':2,'containsMotif':1}.get(l['relation'], 1)
    G.add_edge(l['source'], l['target'], weight=w)

# Remove isolated nodes (Louvain requires connected graph)
connected = [n for n in G.nodes() if G.degree(n) > 0]
G_conn = G.subgraph(connected)
partition = community_louvain.best_partition(G_conn, weight='weight', random_state=42)
# Returns: {node_id: community_int}
# For 789n/3709e: 11 communities in ~0.1s
```

**Back-fill isolated/figure nodes** (they're connected via hasFigure which is excluded
from the community graph for quality):

```python
for n in nodes:
    if n.get('community') is None and n['type'] == 'MythologicalFigure':
        for l in links:
            if l['relation'] == 'hasFigure' and (l['source']==n['id'] or l['target']==n['id']):
                peer_id = l['target'] if l['source']==n['id'] else l['source']
                peer = nodeById.get(peer_id)
                if peer and peer.get('community') is not None:
                    n['community'] = peer['community']
                    break
    if n.get('community') is None:
        n['community'] = 0  # fallback
```

Community quality note: for 789n/3709e the algorithm produces 11 communities that
roughly correspond to cultural clusters (Indo-European, Semitic, East Asian, etc.) plus
thematic groupings. Resolution tuning is not usually needed at this scale.

---

## Level-of-Detail (LOD) Semantic Zoom

4 levels triggered by D3 transform scale `k`:

| Level   | k range   | Show                                            |
|---------|-----------|-------------------------------------------------|
| OVERVIEW| k < 0.5   | Traditions + NarrativeMotifs only               |
| BROWSE  | 0.5–1.2   | All types except MythologicalFigure             |
| EXPLORE | 1.2–3.0   | All node types                                  |
| FOCUS   | k > 3.0   | All types, all labels, full detail               |

```javascript
function currentLOD() {
  if (transform.k < 0.5)  return 'OVERVIEW';
  if (transform.k < 1.2)  return 'BROWSE';
  if (transform.k < 3.0)  return 'EXPLORE';
  return 'FOCUS';
}
```

Show a text indicator in the UI ("Overview — traditions only") — users orientation
confusion drops dramatically when they know what zoom level they're at.

---

## Node Shape Encoding

Shape + color together encodes type unambiguously (helps colorblind users):

| Type               | Shape    | Canvas path                             |
|--------------------|----------|-----------------------------------------|
| Tradition          | Diamond  | 4-point polygon                          |
| NarrativeMotif     | Star     | 5-point star (inner radius 0.42×)        |
| Concept            | Square   | `ctx.roundRect(x-s, y-s, 2s, 2s, s*0.2)`|
| ReligiousText      | Circle   | `ctx.arc()`                              |
| Deity              | Diamond  | Same as Tradition, smaller               |
| MythologicalFigure | Ring     | Hollow circle (stroke only)              |

```javascript
// Star path
function drawStar(ctx, x, y, r) {
  const inner = r * 0.42;
  for (let i = 0; i < 10; i++) {
    const rad = (i * Math.PI / 5) - Math.PI / 2;
    const ri = i % 2 === 0 ? r : inner;
    if (i === 0) ctx.moveTo(x + Math.cos(rad)*ri, y + Math.sin(rad)*ri);
    else ctx.lineTo(x + Math.cos(rad)*ri, y + Math.sin(rad)*ri);
  }
  ctx.closePath();
}
```

---

## Edge Visual Encoding

| Relation type   | Color     | Style   | Width | Alpha |
|-----------------|-----------|---------|-------|-------|
| fromTradition   | #a78bfa   | solid   | 1.8   | 0.7   |
| strongMotif     | #f97316   | solid   | 1.5   | 0.8   |
| containsMotif   | #f97316   | dashed  | 0.6   | 0.2   |
| parallelPassage | #60a5fa   | solid   | 1.4   | 0.7   |
| cognateOf       | #fbbf24   | solid   | 1.3   | 0.7   |
| sameConceptAs   | #34d399   | solid   | 1.3   | 0.8   |
| influencedBy    | #fb7185   | solid   | 1.0   | 0.6   |
| sharesConcept   | #34d399   | dashed  | 0.5   | 0.15  |
| hasFigure       | #94a3b8   | dashed  | 0.4   | 0.12  |

**containsMotif (1874 edges = 50% of all edges)** must be dashed + low alpha — it's
the dominant relation by count and will create an unreadable hairball if solid.

Always call `ctx.setLineDash([])` after drawing dashed edges, or all subsequent
strokes inherit the dash pattern.

---

## Degree-Scaled Node Radii

```javascript
const maxDeg = Math.max(...degree.values());
n._r = baseRadius * (0.7 + 0.8 * Math.sqrt(deg / maxDeg));
// sqrt scaling: keeps hub nodes ~2× not ~5× the size of leaf nodes
```

---

## Canvas Performance Tips

1. Store resolved `_s`/`_t` node objects on links at load — avoid `Map.get()` in render loop
2. Check LOD type set (`Set.has()`) before any draw call
3. `ctx.setLineDash([])` after every dashed-edge draw
4. `ctx.roundRect` available in Canvas 2D API (no manual corner math needed)
5. Don't blend SVG labels over Canvas — they desync from the canvas transform; draw labels in canvas

---

## Ego-Network Mode (Alt+Click)

2-hop neighborhood, everything else dimmed:

```javascript
function egoNetwork(n) {
  const ids = new Set([n.id]);
  adjIndex.get(n.id)?.forEach(nbrs => nbrs.forEach(id => {
    ids.add(id);
    adjIndex.get(id)?.forEach(nbrs2 => nbrs2.forEach(id2 => ids.add(id2)));
  }));
  egoSet = ids; // render loop: ctx.globalAlpha = egoSet && !egoSet.has(n.id) ? 0.05 : 1
}
```

Bind Alt+click separately from Shift+click (1-hop highlight) and plain click (info panel).

---

## Tradition Clustering Force

Spatially separate tradition groups using D3 position forces:

```javascript
simulation.force('tx', d3.forceX().x(d => {
  const idx = trads.indexOf(d.tradition || d.label);
  return ((idx % cols) + 0.5) * W / cols;
}).strength(0.25));
// strength 0.25 clusters without fighting link forces
```

Toggle on/off — organic layout is better for discovery; cluster for tradition comparison.

---

## Delivery: Self-Contained HTML

For offline/local use, embed D3 from CDN + all data inline.
- Full corpus (789n/3709e) → ~860KB JSON → ~900KB HTML total
- Verify CDN reachability: `curl -sL --max-time 5 "https://d3js.org/d3.v7.min.js" | wc -c`
  (should be ~279706; if <100, CDN blocked → embed D3 inline)

---

## Platform Comparison (Humanities DH)

| Tool      | Stars | Renderer | DH Usage | Best for |
|-----------|-------|----------|----------|----------|
| Sigma.js  | 11k   | WebGL    | Stanford/EPFL DH | >2K nodes; WebGL |
| Cytoscape | 10k   | Canvas   | Bioinformatics crossover | Compound nodes, expand/collapse |
| D3 force  | 107k  | Canvas   | Ubiquitous | Full control, custom shapes |
| Kumu.io   | SaaS  | WebGL    | Humanities narratives | Hosted, strong UX |
| Palladio  | 1.5k  | SVG      | Stanford DH flagship | Simple field-based; read-only |
| Gephi     | offline| –       | Best analysis | Pre-compute & export |

---

## Key Pitfalls

1. `re.sub()` on JSON data blobs fails — use sentinel `replace()` or brace-walk
2. `containsMotif` edges (1874) must be dashed+low-alpha or they dominate rendering
3. `ctx.setLineDash([])` after dashed edges — always reset
4. Louvain in-browser (jLouvain) is 45× slower than `python-louvain` — pre-compute
5. Labels past 200 visible nodes become noise — show only for large-r nodes at low zoom
6. Don't use `hasFigure` edges in community graph — they create noise (523 figure nodes)

---

## References
- arxiv:2304.01311 — KG practitioners study (2023), recommends progressive disclosure
- arxiv:2412.05289 — KG visualization survey (2024)
- Blondel et al. 2008 — Original Louvain paper
- Munzner 2014 — *Visualization Analysis and Design*
- graphology Louvain: `graphology.github.io/standard-library/communities-louvain`
- D3 force web worker: `observablehq.com/@d3/force-directed-web-worker`
- Okabe-Ito palette (colorblind-safe): `jfly.uni-koeln.de/color/`
