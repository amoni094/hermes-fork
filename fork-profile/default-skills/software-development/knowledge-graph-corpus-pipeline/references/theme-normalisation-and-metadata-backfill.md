# RDF Theme Normalisation & ChromaDB Metadata Backfill Patterns

Session: July 2026 — Religion corpus engine improvements

---

## hasTheme Controlled Vocabulary Normalisation

### Problem
LLM-generated `myth:hasTheme` triples accumulate near-duplicate free-text strings.
In this corpus: 685 triples → 672 near-unique strings → theme GROUP BY is impossible.

### Design Decisions

**Additive, not destructive.** Keep original `myth:hasTheme` triples for full-text search.
Add `myth:hasThemeVocab` URIs on top. Both predicates coexist.

**Theme URI pattern:** `myth:Theme_<key>` — e.g. `myth:Theme_heroism_quest`

**Theme node structure:**
```turtle
myth:Theme_heroism_quest
    rdf:type myth:Theme ;
    rdfs:label "Heroism & Quest"@en ;
    myth:themeLabel "Heroic deeds and heroes"@en ;   # original free-text
    myth:themeLabel "The heroic journey"@en .         # another mapped string
```

**Unmapped strings:** → `myth:Theme_other` with label "Other / Uncategorised"

### Keyword Scoring Algorithm

Multi-word phrases score higher than single words, which prevents single-letter false matches:

```python
scores: dict[str, int] = defaultdict(int)
for theme_key, info in MASTER_THEMES.items():
    for kw in info["keywords"]:
        if kw.lower() in theme_lower:
            scores[theme_key] += len(kw.split())  # weight by phrase length

if not scores:
    return None  # unmapped

best_score = max(scores.values())
candidates = [k for k, v in scores.items() if v == best_score]
# Tie-break by priority order (THEME_PRIORITY list)
for priority_theme in THEME_PRIORITY:
    if priority_theme in candidates:
        return priority_theme
```

### 25 Master Themes (July 2026)

| Key | Label | Top keywords |
|-----|-------|-------------|
| creation_cosmogony | Creation & Cosmogony | creation, cosmogony, origin, primordial |
| destruction_apocalypse | Destruction & Apocalypse | destruction, flood, catastrophe, ragnarok |
| divine_human_relations | Divine-Human Relations | divine intervention, mortal, deity, divine punishment |
| heroism_quest | Heroism & Quest | hero, quest, adventure, warrior |
| death_afterlife | Death & Afterlife | death, afterlife, underworld, immortality |
| sacred_ritual | Sacred Ritual & Ceremony | ritual, sacrifice, ceremony, initiation |
| cosmic_order_law | Cosmic Order & Law | cosmic order, dharma, justice, maat |
| knowledge_wisdom | Knowledge & Wisdom | wisdom, gnosis, enlightenment, revelation |
| transformation_change | Transformation & Change | transformation, shapeshifting, metamorphosis |
| fertility_nature | Fertility & Nature | fertility, vegetation, seasons, harvest |
| fate_destiny | Fate & Destiny | fate, destiny, prophecy, oracle |
| power_kingship | Power & Kingship | king, kingship, sovereignty, royal |
| love_union | Love & Sacred Union | love, sacred marriage, union, hieros gamos |
| evil_chaos | Evil & Chaos | evil, monster, demon, malevolent |
| liberation_salvation | Liberation & Salvation | liberation, salvation, moksha, nirvana |
| community_society | Community & Society | community, tribe, ancestors, kinship |
| language_word | Language & Sacred Word | word, logos, mantra, speech |
| time_cycles | Time & Cosmic Cycles | time, cycle, yuga, eternal return |
| suffering_trial | Suffering & Trial | suffering, ordeal, hardship, endurance |
| dualism_opposition | Dualism & Opposition | dualism, duality, good and evil, polar |
| transcendence_mysticism | Transcendence & Mysticism | transcendence, mysticism, oneness, ineffable |
| trickery_cunning | Trickery & Cunning | trickster, cunning, deception, trick |
| war_conflict | War & Conflict | war, battle, conflict, conquest |
| ancestor_spirits | Ancestor Spirits & Veneration | ancestors, spirits, veneration, ghost |
| paradox_mystery | Paradox & Mystery | paradox, mystery, unknowable, emptiness |

### Results (July 2026)
- Total `hasTheme` triples: 685
- Mapped to controlled vocab: 530 (77.4%)
- Unmapped → `Theme_other`: 155
- Graph growth: 10,024 → 11,237 triples (+1,213)
- Top themes: divine_human_relations (86), sacred_ritual (66), cosmic_order_law (46)

Unmapped strings tended to be highly specific philosophical or cross-tradition themes
not anticipated in the initial vocabulary (e.g. "loss of innocence", "sacred landscape
and place", "moral consequence and ethical responsibility").

### Script Location
`~/Religion/scripts/normalise_themes.py`

---

## ChromaDB Metadata Backfill — Nested Source ID Path Matching

### Problem
`secondary_literature` collection had `archetype_ids=''` for all 12,747 chunks.
Needed to backfill from an ARCHETYPE_MAP keyed by author names.

### Source ID Structure (actual paths)
```
secondary/layer2_traditional_commentary/midrash/midrash_psalms_en.txt
secondary/layer3_analytical_frameworks/campbell/campbell_masks_primitive.txt
secondary/layer2_traditional_commentary/tafsir/ibn_kathir_en.txt
```

NOT flat. A naive `source_id.replace('secondary/', '')` gives `layer3_analytical_frameworks/campbell/...`
which does NOT match the key `'campbell'` in ARCHETYPE_MAP.

### Two-Level Matching (filename stem + parent directory)

```python
from pathlib import PurePosixPath

def get_archetype_ids(source_id: str) -> str:
    p = PurePosixPath(source_id)
    stem = p.stem          # 'campbell_masks_primitive'
    parent = p.parent.name # 'campbell'

    # 1. Exact stem match (e.g. 'jung_aion_cw9ii' → no exact match)
    if stem in ARCHETYPE_MAP:
        return ARCHETYPE_MAP[stem]

    # 2. Stem prefix match — sort by length desc to match most specific key first
    #    Prevents 'van' matching before 'van_gennep', 'levi' before 'levi_strauss'
    for key in sorted(ARCHETYPE_MAP, key=len, reverse=True):
        if stem.startswith(key):
            return ARCHETYPE_MAP[key]

    # 3. Exact parent-dir match (e.g. 'campbell', 'eliade', 'midrash')
    if parent in ARCHETYPE_MAP:
        return ARCHETYPE_MAP[parent]

    # 4. Parent prefix match
    for key in sorted(ARCHETYPE_MAP, key=len, reverse=True):
        if parent.startswith(key):
            return ARCHETYPE_MAP[key]

    return ''
```

### Source ID → Parent Directory Map (this corpus)

| Parent dir | ARCHETYPE_MAP key | Archetype IDs |
|------------|-------------------|---------------|
| jung | jung | Self,Shadow,Anima,Animus,GreatMother,WiseSenex,Trickster,Hero,Child,Persona |
| campbell | campbell | Hero,Child,Trickster,GreatMother,WiseSenex |
| eliade | eliade | AxisMundi,CentreSymbol,SacredTime,Hierophany |
| aras | aras | Shadow,Anima,GreatMother,Self,Mandala,Trickster,Hero,Child |
| frazer | frazer | DyingRising,VegetationSpirit,SacredKing |
| dumezil | dumezil | Sovereign,Warrior,Provider |
| otto | otto | Numinous,HolyOther,Tremendum |
| van_gennep | van_gennep | Threshold,Liminal,Transition |
| turner | turner | Liminal,Communitas,Threshold |
| neumann | neumann | GreatMother,Shadow,Hero,Self,Uroboros |
| levi_strauss | levi_strauss | BinaryOpposition,Mediator |
| midrash | midrash | Prophet,Torah,Community |
| pali_commentary | visuddhimagga (stem) | Liberation,Meditation,Consciousness |
| tafsir | ibn_kathir / tabari (stem) | Prophet,DivineWill,Judgment |
| vedantic_commentary | shankara / sayana (stem) | varies |
| biblical_scholarship | wellhausen (stem) | Prophet,Law,Covenant |
| church_fathers | augustine / origen / clement (stem) | varies |
| zoroastrian_commentary | denkard (stem) | DualPrinciple,Prophet,CosmicBattle |

### Batch Update Pattern
```python
# Load all metas at once
result = col.get(include=['metadatas'])
all_ids = result.get('ids') or []
all_metas = result.get('metadatas') or []

# Build update lists
to_update_ids, to_update_metas = [], []
for chunk_id, meta in zip(all_ids, all_metas):
    if meta.get('archetype_ids', ''):
        continue  # already set
    new_ids = get_archetype_ids(meta.get('source_id', ''))
    if new_ids:
        updated = dict(meta)
        updated['archetype_ids'] = new_ids
        to_update_ids.append(chunk_id)
        to_update_metas.append(updated)

# Update in batches of 500
BATCH_SIZE = 500
for start in range(0, len(to_update_ids), BATCH_SIZE):
    col.update(ids=to_update_ids[start:start+BATCH_SIZE],
               metadatas=to_update_metas[start:start+BATCH_SIZE])
```

**Do NOT re-embed.** `col.update()` only modifies the fields you pass; all other
metadata fields (source_id, label, tradition, chunk_index, etc.) are preserved.

### Results (July 2026)
- 9,346 chunks updated in 19 batches
- Final: 12,747/12,747 (100%) chunks have non-empty `archetype_ids`
- Script: `~/Religion/scripts/backfill_archetype_ids.py`

### sys.path Required
The ChromaDB installation is in a non-standard location:
```python
sys.path.insert(0, '/var/home/rainbow/.local/lib/python3.14/site-packages')
```
Add this BEFORE any `import chromadb` line.

---

## Paragraph-Aware Chunker (ingest_new_secondary.py)

The paragraph-aware chunker from `vectorize.py` should be kept in sync with
`ingest_new_secondary.py`. Both use `CHUNK_SIZE=800`, `CHUNK_OVERLAP=80`.

Key difference from naive word-split chunker:
- Splits on `\n{2,}` paragraph breaks first
- For oversized paragraphs (> 2× chunk_size), further splits on sentence boundaries
  (`(?<=[.!?])\s+(?=[A-Z\u201C\u2018])`)
- Handles safety cap: chunks > 4500 words get force-split regardless
- Minimum: discards chunks < 30 words

Without this, dense commentary (Midrash, Tafsir, Origen) with few paragraph breaks
produces oversized chunks that exceed the OpenAI 8192-token embed limit.
