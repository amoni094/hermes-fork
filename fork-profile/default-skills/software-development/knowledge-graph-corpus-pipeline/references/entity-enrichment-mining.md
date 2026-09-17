# Entity Enrichment Mining from motif_analysis.json

## Problem

Ontology graphs produced by `graph_enrich.py` often leave typed entity nodes (Deity,
MythologicalFigure, Concept) poorly connected. In the comparative religion corpus,
the base ontology gives **Deity nodes only two relation types**:
- `cognateOf` (deity↔deity cross-tradition equivalences)
- `deityFunctionOf` (deity→tradition)

Zero text→deity or deity→motif edges exist in the base graph. Deities cluster in
isolation in any force-directed visualization — the layout is correct, the data is sparse.

## Source: motif_analysis.json

`~/Religion/analysis/motif_analysis.json` contains structured LLM output per text.
Each key is `"tradition/Full Title (notes)"` and the value is a dict with:

```json
{
  "key_figures": ["Indra", "Varuna", "Agni", "Surya"],
  "motifs_present": [
    {"id": "serpent_dragon_chaos", "confidence": "high",
     "evidence": "Indra repeatedly defeats Vritra, a serpentine chaos-demon..."},
    {"id": "solar_deity", "confidence": "high",
     "evidence": "Surya and other solar deities are prominent throughout..."}
  ],
  "themes": ["Cosmic order emerging from chaos", ...],
  "narrative_episodes": [...],
  "text_character": "..."
}
```

**Critical**: `motifs_present` entries are **dicts**, not strings. `confidence` is
`"high"/"medium"/"low"`. `evidence` is a free-text string that often names deities.

## Key Normalization: Text Label Matching

motif_analysis keys vs graph node labels use incompatible formats:
- motif_analysis: `"hinduism/Rig-Veda (Sanskrit)"`
- graph node label: `"hinduism_Rig-Veda__Sanskrit_"`

**Naive match hits 46/116. Full normalization hits 116/116.**

```python
import re

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

# Build map: normalized label → node id
text_norm_map = {norm(n['label']): n['id'] for n in nodes if n.get('type')=='ReligiousText'}

def find_text(key):
    kn = norm(key)
    if kn in text_norm_map:
        return text_norm_map[kn]
    # fallback: strip tradition prefix from key, partial match
    if '/' in key:
        rest_n = norm(key.split('/', 1)[1])
        for tn, tid in text_norm_map.items():
            if rest_n in tn or tn in rest_n:
                return tid
    return None
```

## Deity Name Map

Build from graph deity nodes, stripping tradition prefix:

```python
deity_by_name = {}
for d in [n for n in nodes if n.get('type') == 'Deity']:
    label = d['label']  # e.g. "greek-roman_Aphrodite"
    parts = label.split('_', 1)
    bare = parts[-1].lower() if len(parts) > 1 else label.lower()
    deity_by_name[bare] = d['id']      # "aphrodite" → id
    deity_by_name[norm(label)] = d['id']  # also normalized full label
```

Only match names longer than 3 chars to avoid false positives (`set`, `anu`, `ra`).

## Motif Node Map

```python
motif_id_map = {n['label'].lower(): n['id'] for n in nodes if n.get('type') == 'NarrativeMotif'}
```

Motif ids in `motifs_present[i]['id']` match motif node labels exactly (e.g. `"solar_deity"`,
`"serpent_dragon_chaos"`, `"trickster"`).

## Full Mining Script

```python
import re, json
from collections import Counter

def norm(s): return re.sub(r'[^a-z0-9]', '', s.lower())

with open('analysis/motif_analysis.json') as f:
    motif_data = json.load(f)
with open('ontology/graph.json') as f:
    g = json.load(f)

nodes = g['nodes']
links = g['links']
nodeById = {n['id']: n for n in nodes}
existing = {(l['source'], l['target'], l['relation']) for l in links}

# Build maps
text_norm_map = {norm(n['label']): n['id'] for n in nodes if n.get('type')=='ReligiousText'}
motif_id_map  = {n['label'].lower(): n['id'] for n in nodes if n.get('type')=='NarrativeMotif'}
deity_by_name = {}
for d in [n for n in nodes if n.get('type')=='Deity']:
    parts = d['label'].split('_', 1)
    bare = parts[-1].lower() if len(parts) > 1 else d['label'].lower()
    deity_by_name[bare] = d['id']

def find_text(key):
    kn = norm(key)
    if kn in text_norm_map: return text_norm_map[kn]
    if '/' in key:
        rest_n = norm(key.split('/',1)[1])
        for tn, tid in text_norm_map.items():
            if rest_n in tn or tn in rest_n: return tid
    return None

new_links = []

for text_key, info in motif_data.items():
    if not isinstance(info, dict): continue
    text_id = find_text(text_key)
    if not text_id: continue

    # 1. featuresDiety (text → deity)
    for fig in (info.get('key_figures') or []):
        if not isinstance(fig, str): continue
        fl = fig.lower().strip()
        for dname, did in deity_by_name.items():
            if len(dname) > 3 and dname in fl:
                k = (text_id, did, 'featuresDiety')
                if k not in existing:
                    new_links.append({'source': text_id, 'target': did, 'relation': 'featuresDiety'})
                    existing.add(k)
                break

    # 2. deityExemplifiesMotif (deity → motif) — from evidence strings
    for m in (info.get('motifs_present') or []):
        if not isinstance(m, dict): continue
        mid = motif_id_map.get(m.get('id', '').lower())
        if not mid: continue
        evidence = m.get('evidence', '').lower()
        for dname, did in deity_by_name.items():
            if len(dname) > 3 and dname in evidence:
                k = (did, mid, 'deityExemplifiesMotif')
                if k not in existing:
                    new_links.append({'source': did, 'target': mid, 'relation': 'deityExemplifiesMotif'})
                    existing.add(k)

# Dedup
seen = set()
deduped = []
for l in new_links:
    k = (l['source'], l['target'], l['relation'])
    if k not in seen:
        seen.add(k)
        deduped.append(l)

print(f"New links: {len(deduped)}")
print(dict(Counter(l['relation'] for l in deduped)))
```

## Pass 2: Full-Text Disk Scan (higher recall)

After the motif_analysis pass, scan the actual text files on disk for deity name occurrences.
This yields ~2-3× more `featuresDiety` links. The motif_analysis key_figures lists are
hand-curated and incomplete; the text files contain the full corpus.

```python
import os, re

# Build word-boundary patterns for each deity
deity_patterns = {}
for d in [n for n in nodes if n.get('type') == 'Deity']:
    parts = d['label'].split('_', 1)
    bare = parts[-1].replace('_', ' ') if len(parts) > 1 else d['label']
    # Add known name variants
    variants = {
        'Dyaus Pita': ['Dyaus', 'Dyaus Pita'],
        'Ahura Mazda': ['Ahura Mazda', 'Ahura', 'Mazda'],
        'Ra': ['Ra', 'Re'], 'Ea': ['Ea', 'Enki'],
        'Inanna': ['Inanna', 'Ishtar'],
    }.get(bare, [bare])
    deity_patterns[d['id']] = [
        re.compile(r'\b' + re.escape(n) + r'\b', re.IGNORECASE)
        for n in variants if len(n) >= 2
    ]

# Map text nodes → on-disk directory (fuzzy: normalized label vs folder name)
text_dir_map = {}
base = '/var/home/rainbow/Religion'  # adjust to your corpus root
for n in [x for x in nodes if x.get('type') == 'ReligiousText']:
    trad, rest = n['label'].split('_', 1) if '_' in n['label'] else (n['label'], '')
    tdir = os.path.join(base, trad)
    if not os.path.isdir(tdir): continue
    title_n = norm(rest)
    best, best_score = None, 0
    for sd in os.listdir(tdir):
        score = sum(1 for c in title_n if c in norm(sd)) / max(len(title_n), len(norm(sd)), 1)
        if score > best_score: best_score, best = score, sd
    if best_score > 0.5:
        text_dir_map[n['id']] = os.path.join(tdir, best)

# Scan each text's files for deity mentions (threshold=2 to filter noise)
scan_links = []
for text_id, dir_path in text_dir_map.items():
    # Skip _1.txt duplicates; read first 200KB per file
    txt_files = [f for f in os.listdir(dir_path)
                 if f.endswith('.txt') and not f.endswith('_1.txt')][:5]
    full_text = ''.join(
        open(os.path.join(dir_path, tf), errors='replace').read(200_000)
        for tf in txt_files)
    if not full_text: continue
    for deity_id, patterns in deity_patterns.items():
        if sum(len(p.findall(full_text)) for p in patterns) >= 2:
            k = (text_id, deity_id, 'featuresDiety')
            if k not in existing:
                scan_links.append({'source': text_id, 'target': deity_id,
                                   'relation': 'featuresDiety'})
                existing.add(k)
```

**Note**: When ChromaDB collections are corrupted (`InternalError: Failed to apply logs...`),
the disk scan is the only way to get deity-text links. This was the case for `sacred_texts`
in `chroma_db` as of July 2026. The disk scan works regardless of ChromaDB state.

## Pass 3: Curated Scholarly Mapping (deity→motif)

For deities that don't appear in motif evidence strings, add links from comparative
mythology scholarship (Jung, Eliade, Campbell, etc.) as a curated dict:

```python
DEITY_MOTIF_MAP = [
    ('Odin',       ['world_tree', 'oracle_prophecy', 'shapeshifting', 'sacred_kingship']),
    ('Thor',       ['great_battle_apocalypse', 'serpent_dragon_chaos', 'slaying_monster']),
    ('Isis',       ['great_mother', 'dying_rising_deity', 'sacred_marriage']),
    ('Osiris',     ['dying_rising_deity', 'afterlife_judgment', 'underworld_descent']),
    ('Zeus',       ['sacred_kingship', 'divine_wrath', 'sacred_marriage']),
    ('Dionysus',   ['dying_rising_deity', 'trickster', 'sacred_marriage']),
    ('Hermes',     ['trickster', 'underworld_descent', 'shapeshifting']),
    ('Indra',      ['serpent_dragon_chaos', 'slaying_monster', 'sacred_kingship']),
    ('Ahura Mazda',['dualism', 'sacred_law_revelation', 'great_battle_apocalypse']),
    ('Jesus',      ['dying_rising_deity', 'divine_child', 'sacred_kingship', 'scapegoat']),
    # ... see comparative-religion-corpus skill for full list
]
# Apply same deity_by_name + motif_id_map lookup as Pass 1
```

## Results (July 2026 — Religion corpus, all 3 passes combined)

| Pass | Method | New links | Notes |
|------|--------|-----------|-------|
| 1 | motif_analysis key_figures | 59 featuresDiety | High precision |
| 1 | motif_analysis evidence strings | 70 deityExemplifiesMotif | High precision |
| 2 | Disk text scan (threshold=2) | 133 featuresDiety | 2-3× higher recall |
| 3 | Curated scholarly mapping | ~70 deityExemplifiesMotif | Fills remaining gaps |
| — | **Total after dedup** | **332 → 203 unique** | With existing graph |

Coverage after all passes:
- 44/47 deities with text connections (was 0/47)
- 36/47 deities with motif connections (was 0/47)
- Brigid, Freya, Tyr remain text-isolated (names too rare/variant in this corpus)

Sample outputs:
- `norse-icelandic_Prose_Edda → norse-icelandic_Thor` (featuresDiety, disk scan)
- `hinduism_Rig-Veda → hinduism_Indra` (featuresDiety, both passes)
- `norse-icelandic_Loki → trickster` (deityExemplifiesMotif)
- `hinduism_Indra → serpent_dragon_chaos` (deityExemplifiesMotif)
- `hinduism_Surya → solar_deity` (deityExemplifiesMotif)
- `greek-roman_Hades → underworld_descent` (deityExemplifiesMotif)
- `egyptian_Isis → dying_rising_deity` (deityExemplifiesMotif)
- `christianity_Jesus → [14 texts, 9 motifs]` (combined)

## Injecting into an Existing Visualization HTML

After mining, inject into the HTML without re.sub (JSON unicode escapes break regex):

```python
# Find data block by walking brace depth
idx = html.find('const GRAPH_DATA = {')
depth, i = 0, idx + len('const GRAPH_DATA = ')
while i < len(html):
    if html[i] == '{': depth += 1
    elif html[i] == '}':
        depth -= 1
        if depth == 0: break
    i += 1
# Extend the links array
data['links'].extend(deduped)
new_data_json = json.dumps(data, separators=(',',':'))
html = html[:idx] + 'const GRAPH_DATA = ' + new_data_json + html[i+1:]
```

## Generalizing to Other Entity Types

The same pattern applies to MythologicalFigure and Concept nodes:
- `key_figures` often contains figure names that match figure node labels
- `themes` strings can be matched against Concept node labels
- The `narrative_episodes` list can yield figure→episode edges

The core technique: **mine structured LLM output (motif_analysis.json) to bridge
entity nodes that the ontology pipeline left disconnected from the main graph body.**
