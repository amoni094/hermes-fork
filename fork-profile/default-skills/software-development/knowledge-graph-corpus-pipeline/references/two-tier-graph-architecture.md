# Two-Tier Graph Architecture — Design Notes
*Session: 2026-07-31. Religion DB ontology consolidation.*

## Problem

The `myth_knowledge_graph.ttl` (847 nodes, 3787 links) rendered as an
unnavigable hairball. Root cause: three edge types created dense hubs with no
navigational signal:

| Edge | Count | Hub effect |
|------|-------|-----------|
| containsMotif | 1874 | Every text → every motif; underworld_descent degree=87 |
| sharesConcept | 661 | Every text → every concept; cosmic_order degree=85 |
| hasFigure | 561 | 523 MythologicalFigure nodes, all degree-1 leaves |

Max hub degree before: 87 (underworld_descent motif)
Max hub degree after summary: 47 (Theme: Divine-Human Relations)

## Design Decisions

### 1. Two output files, not one
- `ontology/graph_summary.json` — curated, 285 nodes, 1162 links (connectivity-fixed)
- `ontology/graph_full.json` — complete, 847 nodes, 3787 links

Both served via `fetch()` in the browser; tier toggle swaps active dataset.
No data is ever lost — full graph is always available.

### 2. Replace `sharesConcept` with `hasThemeVocab` in summary
`sharesConcept` (20 dense concept hubs, max degree 85) → `hasThemeVocab`
(20 broad Theme nodes, max degree 47). Both serve the "what does this text
discuss abstractly?" navigation need, but themes are coarser → less crowded.

**However**: `hasThemeVocab` is stored as a Turtle literal in the TTL, not
as an object edge. Must be parsed from TTL blocks and injected as synthetic
edges in `build_tiered_graph.py`. Key parsing pattern:
```python
blocks = re.split(r'\.\s*\n\s*\n', ttl_text)
for block in blocks:
    subj_m = re.match(r'\s*(text:\S+)', block)
    tv_m = re.search(r'myth:hasThemeVocab\s+((?:myth:Theme_\w+[\s,]*)+)', block)
    if subj_m and tv_m:
        theme_keys = re.findall(r'myth:(Theme_\w+)', tv_m.group(1))
        ...
```
489 pairs parsed from TTL → 365 kept in summary (124 dropped with Theme_other).

### 3. Drop Theme_other from summary
`Theme_other` was degree=81 — the single biggest hub. It's a junk-bin category
assigned to texts that didn't map cleanly to the 20 defined themes.
Lesson: always check for junk-bin nodes (very-high-degree catch-all categories)
in any graph simplification. They aggregate noise, not signal.

### 4. Drop MythologicalFigure nodes from summary
523 figure nodes, nearly all degree-1 leaves. They show up in Full as `hasFigure`
edges. For the summary navigation layer, named figures provide little cross-tradition
insight compared to Motifs/Concepts/Themes. Keep in full graph.

### 5. Edge selection rationale

High-signal (summary):
- `strongMotif` — confirmed dominant motif, not just any occurrence
- `hasThemeVocab` — broad theme assignment, replaces dense sharesConcept
- `cognateOf` — deity equivalence cross-tradition (Zeus=Jupiter etc.)
- `influencedBy` + `parallelPassage` + `parallelTo` — textual relationships
- `deityFunctionOf` — anchors deities to their tradition
- `sameConceptAs` — concept equivalences across traditions
- `fromTradition` — BRIDGE: keeps Deity/Tradition component connected (see §7)

Full-only (too dense for summary):
- `containsMotif` — all motif mentions, not just primary
- `sharesConcept` — all concept overlaps (capped version used as bridge, see §7)
- `hasFigure` — all named figure appearances

### 6. Fix `type` field on nodes
`graph.json` had `relation` on links but not `type` (needed by browser).
Also 12 nodes missing `type` entirely (CIDOC-CRM import stubs).
Both fixed in `build_tiered_graph.py` before writing output files.

---

## PITFALL 40 — Summary graph disconnected components (verified 2026-07-31)

After the initial summary build, the graph had **6 disconnected components**:

| Component | Nodes | Why isolated |
|-----------|-------|--------------|
| Main (texts/themes/motifs) | 178 | Connected via strongMotif + hasThemeVocab |
| Deity + Tradition | 63 | `fromTradition` was dropped from summary |
| Concept (7 nodes) | 7 | `sharesConcept` was dropped from summary |
| taoism + confucianism | 2 | fromTradition dropped + no strongMotif links |
| soul_immortality + moksha | 2 | sharesConcept dropped |
| sacred_mountain + world_tree | 2 | ZERO `strongMotif` in full graph — only `containsMotif` |

**Root cause analysis script:**
```python
from collections import defaultdict, deque, Counter
adj = defaultdict(set)
for l in links:
    s = l['source'] if isinstance(l['source'],str) else l['source']['id']
    t = l['target'] if isinstance(l['target'],str) else l['target']['id']
    adj[s].add(t); adj[t].add(s)

visited, components = set(), []
for nid in (n['id'] for n in nodes):
    if nid in visited: continue
    comp, queue = [], deque([nid])
    visited.add(nid)
    while queue:
        cur = queue.popleft(); comp.append(cur)
        for nb in adj[cur]:
            if nb not in visited: visited.add(nb); queue.append(nb)
    components.append(comp)
components.sort(key=lambda c: -len(c))
for i, comp in enumerate(components):
    types = Counter(id_map.get(nid,{}).get('type','?') for nid in comp)
    print(f"Component {i+1}: {len(comp)} nodes — {dict(types)}")
```

**Fix applied in `build_tiered_graph.py`:**
1. `fromTradition` added back to `SUMMARY_RELATIONS` — bridges Deity/Tradition
   component to main text component (116 edges, modest, high signal)
2. `sharesConcept` re-added **capped** (5 texts/concept, top by full-graph degree) —
   connects the 7-node Concept component without the 661-edge hairball
3. `containsMotif` added **capped** (6 texts/motif) for motifs with ZERO `strongMotif`
   edges (sacred_mountain, world_tree had no strongMotif in the full graph at all)

After fix: **1 connected component** (283 nodes) + 1 genuine isolated pair
(Roma tradition + 1 text — zero cross-connections in source data, not a bug).

**Roma isolation is a data gap**, not a graph bug. The Roma corpus has only one
text with no motif parallels, concept links, or deity connections tagged yet.
Always verify isolated components in source data before "fixing" — some reflect
genuine corpus sparsity, not graph construction errors.

**Sorting pitfall in capped-edge selection:**
```python
# WRONG — TypeError when comparing dicts:
top = sorted(scored, reverse=True)[:N]

# RIGHT — sort by score only (first element of tuple):
top = sorted(scored, key=lambda x: x[0], reverse=True)[:N]
```

---

## OWL Ontology Changes (myth_ontology.ttl)

```turtle
myth:Theme a owl:Class ;
    rdfs:label "Broad Theme"@en ;
    rdfs:comment "High-level thematic category (20 themes). Summary-tier nav nodes."@en .

myth:hasThemeVocab a owl:ObjectProperty ;
    rdfs:domain myth:ReligiousText ;
    rdfs:range myth:Theme .

myth:graphLayer a owl:DatatypeProperty ;
    rdfs:comment "Values: 'summary' or 'full'. Declares viz tier for each property."@en .
```

20 Theme instances added with `myth:themeKey` (machine key) and `rdfs:label`.
`Theme_other` intentionally excluded — it's a junk-bin, not in summary.

---

## Build Script

`~/Religion/scripts/build_tiered_graph.py`
- Input: `ontology/graph.json` + `ontology/myth_knowledge_graph.ttl`
- Output: `ontology/graph_summary.json`, `ontology/graph_full.json`, updates `ontology/graph.json`

Run after any graph_enrich.py rebuild:
```bash
cd ~/Religion && python3 scripts/build_tiered_graph.py
```

Expected output (post-connectivity fix):
```
Loading ontology/graph.json...
  Parsed 489 hasThemeVocab pairs from TTL
  hasThemeVocab edges added to summary: 489
  Motifs needing containsMotif bridge: 15
Summary graph: 285 nodes, 1162 links
  365  hasThemeVocab
  174  parallelPassage
  124  strongMotif
  116  fromTradition
   95  sharesConcept
   79  containsMotif
   68  parallelTo
   66  cognateOf
   47  deityFunctionOf
   21  influencedBy
    7  sameConceptAs
```

---

## Semantic Proximity Force Layout (2026-07-31)

The key insight: **link distance should be inversely proportional to semantic
strength**. Strong semantic relationships = nodes physically close. Structural
bridge edges = long and weak (don't distort clusters).

### Calibrated force parameters

| Relation | Strength | Distance | Rationale |
|----------|----------|----------|-----------|
| sameConceptAs | 0.95 | 35px | Literally the same concept |
| cognateOf | 0.90 | 45px | Same deity, different tradition |
| parallelPassage | 0.75 | 70px | Near-identical narrative |
| influencedBy | 0.65 | 90px | Direct literary lineage |
| deityFunctionOf | 0.55 | 80px | Deity embodies function |
| strongMotif | 0.45 | 110px | Text's primary motif |
| parallelTo | 0.35 | 130px | Loose structural parallel |
| hasThemeVocab | 0.20 | 175px | Theme spoke — soft, keeps themes central |
| sharesConcept | 0.15 | 160px | Abstract bridge |
| fromTradition | 0.12 | 190px | Tradition hub stands apart |
| containsMotif | 0.10 | 200px | Bridge-only — minimal pull |

**Degree-scaled charge** (hubs repel more):
```javascript
.force('charge', d3.forceManyBody()
    .strength(n => {
        const deg = n._deg || 1;
        const base = isSummary ? -180 : -60;
        return base * (1 + Math.log(deg + 1) * 0.4);
    })
    .distanceMax(400))
```
High-degree hubs (Themes, Traditions, dense Motifs) repel ~3× more than leaf nodes.
This gives each semantic cluster room without blowing the graph apart.

**Degree-scaled collision** (hubs need breathing room):
```javascript
.force('collide', d3.forceCollide(n => nodeR(n, n._deg) * 2.2 + 4).strength(0.7))
```

**Slower alphaDecay** = more time to find minimum:
```javascript
.alphaDecay(0.015)   // was 0.02 — 25% longer settling time
.velocityDecay(0.35) // moderate damping, avoids overshooting
```

### Jaccard Similarity Force

Pairs of nodes with many shared neighbours attract even without a direct edge.
This pulls semantically equivalent concepts/motifs physically close.

**Compute pairs** (precomputed at build time, stored in `ontology/node_similarity.json`):
```python
for i in range(len(eligible)):
    for j in range(i+1, len(eligible)):
        a, b = eligible[i]['id'], eligible[j]['id']
        inter = len(nbr[a] & nbr[b])
        if inter < 2: continue
        union = len(nbr[a] | nbr[b])
        jac = inter / union
        if jac >= 0.25:
            pairs.append({'source': a, 'target': b, 'jaccard': jac, 'shared': inter})
# Sort by jaccard descending, cap at 300 pairs to avoid bloating
```

Top pairs in religion corpus (Jaccard 1.0):
- karma ↔ dualism (6 shared texts)
- oracle_prophecy ↔ eschatology (5 shared)
- virgin_birth_divine ↔ world_egg (6 shared)

**Apply as custom D3 force** (both 2D and 3D graphs):
```javascript
simulation.force('jaccard', (alpha) => {
    for (const {a, b, jac} of activePairs) {
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        // Target: 40px (jac=1.0) to 160px (jac=0.25)
        const targetDist = 40 + (1 - jac) * 120;
        const force = (dist - targetDist) / dist * alpha * jac * 0.3;
        a.vx += dx * force; a.vy += dy * force;
        b.vx -= dx * force; b.vy -= dy * force;
    }
});
```

Load `node_similarity.json` alongside the graph JSONs:
```javascript
window._jaccardPairs = await fetch('ontology/node_similarity.json').then(r=>r.json()).catch(()=>[]);
```

**For 3D graph**, same logic with z component added:
```javascript
a.vz = (a.vz||0) + dz * force;
b.vz = (b.vz||0) - dz * force;
```

---

## Node Annotation Enrichment (node_annotations.json)

Built from TTL rdfs:label/comment + graph-derived fields. Served via fetch()
alongside graph JSONs. Coverage in religion corpus: all 285 summary nodes.

**Computed enrichment fields** added on top of TTL annotations:
- `traditions_present` (motifs/themes): which traditions appear in neighbourhood
- `top_connections`: top 5 hub neighbours by full-graph degree
- `cognates`: deity cognate list — **must deduplicate by id** (bidirectional
  `cognateOf` edges cause every deity to list cognates twice; 47/47 affected)
- `text_count`, `deity_count`: for Tradition nodes
- `motif_count`: for ReligiousText nodes

Rebuild: run `build_tiered_graph.py` (annotation step is included), or
run the annotation enrichment script standalone.

---

## D3.js 2D Visualizer (religion_graph_v3.html)

Key design choices:
- Loads both JSON files + `node_annotations.json` + `node_similarity.json` on startup
- Default tier = Summary; toggle button swaps and restarts simulation
- **Info pane** (320px, left of canvas, collapsible): home state shows project description,
  node/edge legend, methodology; node-selected state shows scholarly description +
  graph-derived significance + clickable neighbour chips
- Theme nodes: orange (#fb923c), r=8-9 — biggest nodes in summary by design
- `hasFigure`, `containsMotif`, etc. shown faint (alpha ~0.2) in full graph
- Header links to 3D view: `<a href="religion_graph_3d.html">`

### Info pane home state sections
1. Title + tagline (node counts)
2. Navigation guide (click nodes, filters, tier toggle)
3. Node types legend (colour-coded dots + descriptions)
4. Edge types legend (coloured swatches + descriptions)
5. How this was built (methodology text)
6. Source traditions (2-column grid with colour dots)

### Info pane node-selected state
1. Type badge (coloured pill)
2. Clean display name
3. Tradition badge
4. Description from node_annotations.json `comment` field (full text)
5. Graph significance (degree, traditions_present, cognates, text_count)
6. Connections grouped by relation type — clickable chips calling panToNode()
7. "← Back to home" button

### Node display name cleaning
Strip URI prefix, replace underscores with spaces. For ReligiousText nodes
strip the leading tradition name ("hinduism Vishnu Purana" → "Vishnu Purana"):
```javascript
function cleanLabel(n) {
    if (n.display_label) return n.display_label;
    let s = n.label.replace(/^.*\//, '').replace(/_/g,' ');
    if (n.type === 'ReligiousText') {
        // strip known tradition prefix (up to 3 words)
        const known = ['hinduism','buddhism',...];
        for (let w=3;w>=1;w--) {
            if (known.includes(parts.slice(0,w).join(' ').toLowerCase()))
                { s = parts.slice(w).join(' '); break; }
        }
    }
    return s.trim();
}
```

### simLinks pattern
D3 force simulation mutates link objects (source/target → resolved node objects).
Store them on `simulation._simLinks` after `startSim()` for use by detail panel
and neighbour-dimming logic. Both functions read `simulation._simLinks || []`.

---

## 3D Visualizer (religion_graph_3d.html)

Added 2026-07-31. Uses `3d-force-graph` (vasturiano) + Three.js from CDN —
no install needed. CDN refs:
```html
<script src="https://unpkg.com/three@0.158.0/build/three.min.js"></script>
<script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>
```

Data: same `ontology/graph_summary.json` / `ontology/graph_full.json` — identical
node/link schema, same fetch() paths.

**Key API pattern:**
```javascript
const Graph = ForceGraph3D()(document.getElementById('graph-container'))
  .backgroundColor('#0d1117')
  .nodeColor(n => NODE_COLORS[n.type] || '#888')
  .nodeVal(n => Math.pow(nodeR(n, n._deg), 2) * 0.5)  // volume, not radius
  .nodeThreeObject(n => makeNodeObj(n))  // canvas sprite labels
  .nodeThreeObjectExtend(true)           // add sprite ALONGSIDE sphere, not replacing it
  .linkColor(l => EDGE_COLORS[l.relation] || '#ffffff11')
  .linkWidth(l => widthMap[l.relation] || 0.5)
  .linkDirectionalParticles(l => particlesOn && ... ? 2 : 0)
  .onNodeClick(onNodeClick)
  .onNodeHover(onNodeHover)
  .onBackgroundClick(clearSelection);
```

**Canvas sprite labels** (Three.js):
- Create `HTMLCanvasElement`, draw text with `ctx.fillText()`, wrap in `THREE.CanvasTexture`
- Use `THREE.Sprite` with `SpriteMaterial({map: texture, transparent: true, depthWrite: false})`
- Scale: `sprite.scale.set(canvas.width * 0.12, canvas.height * 0.12, 1)`
- Position: `sprite.position.set(0, nodeR + 3, 0)` — float above the sphere
- Only show for hub nodes + Themes/Traditions to avoid clutter

**Camera auto-rotate:**
```javascript
let angle = 0;
Graph.onEngineTick(() => {
    if (!autoRotate) return;
    angle += 0.002;
    Graph.cameraPosition({ x: 600 * Math.sin(angle), z: 600 * Math.cos(angle) });
});
```

**Focus camera on click:**
```javascript
const dist = 120;
const distRatio = 1 + dist / Math.hypot(node.x||1, node.y||1, node.z||1);
Graph.cameraPosition(
    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
    node,    // lookAt
    1200     // transition ms
);
```

**Force tuning for 3D (same semantic proximity principle as 2D):**
```javascript
Graph
    .d3Force('charge', d3?.forceManyBody?.()
        .strength(n => { const base = isSummary ? -160 : -55;
                         return base * (1 + Math.log((n._deg||1)+1) * 0.4); })
        .distanceMax(500))
    .d3Force('link', d3?.forceLink?.()
        .id(n => n.id)
        .strength(l => ({sameConceptAs:0.95, cognateOf:0.90, ...}[l.relation] || 0.15))
        .distance(l => ({sameConceptAs:35, cognateOf:45, ...}[l.relation] || 160)))
    .d3Force('collide', d3?.forceCollide?.().radius(n => nodeR(n,n._deg)*2.5+5).strength(0.7))
    .d3AlphaDecay(0.015)
    .d3VelocityDecay(0.35);
```

**Tradition clustering force (3D):**
```javascript
const clusterForce = (alpha) => {
    data.nodes.forEach(node => {
        const pos = tradPos[(node.tradition||'').toLowerCase().replace(/ /g,'_')];
        if (!pos) return;
        node.vx += (pos.x - node.x) * 0.08 * alpha;
        node.vy += (pos.y - node.y) * 0.08 * alpha;
        node.vz += (pos.z - node.z) * 0.08 * alpha;
    });
};
Graph.d3Force('cluster', clusterForce);
Graph.d3ReheatSimulation();
```

**Highlight on click (3D):**
```javascript
Graph
    .nodeColor(n => neighbourIds.has(n.id) ? NODE_COLORS[n.type] : '#333333')
    .nodeOpacity(n => neighbourIds.has(n.id) ? 0.9 : 0.08)
    .linkColor(l => isAdjacentLink(l, node) ? EDGE_COLORS[l.relation] : '#ffffff08');
```
Note: `.nodeOpacity()` accepts a number OR a function in 3d-force-graph ≥1.73.

**Sidebar collapse toggle** — slide sidebar off-screen and resize canvas:
```javascript
function toggleSidebar() {
    sb.classList.toggle('collapsed');
    setTimeout(() => {
        Graph.width(document.getElementById('graph-container').clientWidth);
    }, 220);  // wait for CSS transition
}
```

**Features vs 2D:**
| Feature | 2D (v3) | 3D |
|---------|---------|-----|
| Tier toggle | ✓ | ✓ |
| Tradition filters | ✓ | ✓ |
| Node/edge filters | ✓ | ✓ |
| Search + pan | ✓ | ✓ (camera fly-to) |
| Info pane | ✓ (left, 320px) | right detail panel |
| Group by tradition | ✓ (forceX/Y) | ✓ (custom 3D force) |
| Auto-rotate | — | ✓ |
| Flow particles | — | ✓ (linkDirectionalParticles) |
| Freeze/reheat | ✓ | via reheatSimulation() |
| Labels | SVG text | Three.js sprites |
| Semantic proximity | ✓ Jaccard force | ✓ Jaccard force |

**Serve from:** `python3 -m http.server 9191` in `~/Religion/`.
Both files at: `http://localhost:9191/religion_graph_v3.html` (2D) and
`http://localhost:9191/religion_graph_3d.html` (3D), with cross-links in headers.

**Port conflict note:** Port 8765 is occupied by another service (Hermes WebUI or similar).
Use 9191 or any other available port instead.
