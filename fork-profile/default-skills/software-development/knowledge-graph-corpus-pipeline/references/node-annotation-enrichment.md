# Node Annotation Enrichment (node_annotations.json)

For browser visualizations that need per-node scholarly content (descriptions,
cognates, tradition coverage), extract annotations from the TTL and enrich them
with graph-derived fields.

## Step 1 — Extract rdfs:label/comment from TTL

The naive `re.findall(r'rdfs:comment\s+"([^"]+)"', text)` misses most entries
because TTL uses subject blocks, not flat triple lists. Use a block-splitting approach:

```python
def parse_ttl_annotations(path):
    with open(path) as f:
        text = f.read()
    # Parse @prefix declarations
    prefixes = {}
    for m in re.finditer(r'@prefix\s+(\w*):\s+<([^>]+)>', text):
        prefixes[m.group(1)+':'] = m.group(2)
    def expand(token):
        token = token.strip().rstrip(';,.')
        if token.startswith('<') and token.endswith('>'): return token[1:-1]
        for p, uri in prefixes.items():
            if token.startswith(p): return uri + token[len(p):]
        return token
    # Remove comments, split on '. \n' statement boundaries
    text_clean = re.sub(r'#[^\n]*', '', text)
    result = {}
    for block in re.split(r'\s*\.\s*\n', text_clean):
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines: continue
        tok_m = re.match(r'^(<[^>]+>|[\w]+:[\w\-\._%]+)\s*(.*)', lines[0])
        if not tok_m: continue
        subj_raw = tok_m.group(1)
        pred_text = tok_m.group(2) + ' ' + ' '.join(lines[1:])
        lbl_m = re.search(r'rdfs:label\s+"([^"]+)"', pred_text)
        cmt_m = re.search(r'rdfs:comment\s+"([^"]+)"', pred_text)
        skos_m = re.search(r'skos:(?:definition|scopeNote)\s+"([^"]+)"', pred_text)
        if lbl_m or cmt_m or skos_m:
            result[expand(subj_raw)] = {
                'label': lbl_m.group(1) if lbl_m else None,
                'comment': cmt_m.group(1) if cmt_m else None,
                'definition': skos_m.group(1) if skos_m else None,
            }
    return result
```

Merge annotations from both `myth_ontology.ttl` and `myth_knowledge_graph.ttl`.
Expected coverage for religion corpus: all 285 summary nodes annotated (label or comment).

## Step 2 — Enrich with graph-derived fields

After building the base annotations, add fields computed from graph topology:

```python
# For NarrativeMotif and Theme nodes:
ann[nid]['traditions_present'] = sorted({
    n.get('tradition','').title()
    for oid, rel in adj[nid]
    for n in [id_to_node.get(oid, {})]
    if n.get('tradition') or n.get('type') == 'Tradition'
})
ann[nid]['top_connections'] = [
    {'id': oid, 'label': clean_label(id_to_node[oid]), 'relation': rel, 'degree': full_degree[oid]}
    for oid, rel in sorted(adj[nid], key=lambda x: -full_degree[x[0]])[:5]
]

# For Deity nodes:
ann[nid]['cognates'] = list({c['id']: c for c in [
    {'id': oid, 'label': clean_label(id_to_node.get(oid,{'id':oid}))}
    for oid, rel in adj[nid] if rel == 'cognateOf'
]}.values())  # deduplicate by id — bidirectional edges create duplicates

# For Tradition nodes:
ann[nid]['text_count'] = sum(1 for oid, rel in adj[nid] if id_to_node.get(oid,{}).get('type')=='ReligiousText')
ann[nid]['deity_count'] = sum(1 for oid, rel in adj[nid] if id_to_node.get(oid,{}).get('type')=='Deity')
```

**Deduplication pitfall**: bidirectional `cognateOf` edges (A→B and B→A both in graph)
cause every deity to list its cognates twice. Always deduplicate by `id` after collecting.
In the religion corpus this affected 47/47 deity nodes (all had duplicates).

## Step 3 — Write and serve

```python
with open('ontology/node_annotations.json', 'w') as f:
    json.dump(merged, f, separators=(',',':'))
```

Serve via the same HTTP server as the graph JSONs. Load in browser with:
```javascript
const nodeAnnotations = await fetch('ontology/node_annotations.json').then(r=>r.json());
// Look up by node URI: nodeAnnotations[node.id] -> {label, comment, traditions_present, cognates, ...}
```

## Info pane pattern (browser)

For a knowledge graph visualization with a left-side info pane:

**Home state** (no node selected): show project description, node/edge type legend,
methodology, source traditions. Pre-write as static HTML, inject on page load.

**Node selected state**: look up `nodeAnnotations[node.id]`, render:
1. Type badge (coloured pill)
2. Clean display name (`display_label` or cleaned `label`)
3. Tradition badge
4. `comment` or `definition` field (full text, not truncated)
5. Graph-derived significance: degree, traditions_present, cognate list, text_count
6. Connections grouped by relation type — clickable chips that pan/fly to the neighbour
7. "← Back to home" button to clear selection

**Back to home** must call `clearSelection()` which restores full graph opacity and
re-renders the home content. The info pane replaces the old right-side detail panel.
