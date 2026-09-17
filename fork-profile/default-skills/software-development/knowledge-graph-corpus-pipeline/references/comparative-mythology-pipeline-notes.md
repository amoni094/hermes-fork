# Comparative Mythology Pipeline — Session Notes (Jul 2026)

## Project location
~/Religion/scripts/

## Files written
- text_manifest.py   116 entries across 25 traditions
- scraper.py         rate-limited HTML scraper (1.5-3s delay)
- ontology.py        OWL/CIDOC-CRM schema (542 base triples)
- vectorize.py       ChromaDB + OpenAI text-embedding-3-small
- graph_enrich.py    RDF graph population + semantic discovery
- query.py           CLI (motif/text/deity/influence/similar/sparql/shell)
- build.sh           pipeline runner
~/Religion/README.md

## Scraper run outcome (Jul 22-23 2026)
- 116 texts attempted, 88 success, 28 failures (all 404s — dead URLs on sacred-texts.com)
- 17,563 files on disk across 26 tradition directories
- Runtime: ~14 hours total (overnight stall ~23:14-09:39 due to read timeout; scraper self-recovered)
- Watchdog cron (every 10m) required manual `cronjob(action='run')` to prime after creation
- Multiple orphaned instances from prior sessions killed before final clean run
- Next steps: vectorize.py then graph_enrich.py

## Ontology stats (base, pre-download)
- 12 OWL classes, 20 object properties, 10 datatype properties
- 25 narrative motifs (Thompson Motif Index codes included)
- 20 theological concepts
- 25 traditions
- 542 base triples

## Enriched graph stats (base, pre-download)
- 116 text nodes, 47 deity nodes, 33 deity-cognate pairs
- 1331 text-motif links, 661 text-concept links
- 13 motif parallel pairs, 21 influence links
- 4022 total triples
- NetworkX: 293 nodes, 2338 edges

## Tradition coverage (25 traditions)
hinduism(15), buddhism(13), norse-icelandic(6), zoroastrianism(6),
native-american(6), celtic(6), greek-roman(9), egyptian(5), judaism(5),
islam(4), christianity(4), confucianism(4), pacific-oceanic(4),
taoism(3), african(3), australian-aboriginal(3), comparative(3),
ancient-near-east(7), jainism(2), shinto(2), gnosticism(2),
sikhism(1), shamanism(1), basque(1), roma(1)

## Source site
sacred-texts.com — selection criteria: ancient/established traditions only,
original language preferred (Sanskrit, Avestan, Pali, Classical Greek/Latin),
most complete version (full Apocrypha, no expurgated editions).
Excluded: Scientology, UFO cults, Theosophy, Neopaganism, New Thought,
Mormonism, Swedenborg, Thelema, Grimoires, Necronomicon.

## Key ontology design decisions

### Why CIDOC-CRM
ISO 21127 is the standard for cultural heritage information. It models
E73 Information Object (texts), E21 Person (deities as mythological persons),
E53 Place (sacred places), E5 Event (narrative events) — all applicable.
OWL-DL level maintains SPARQL queryability without a full OWL-Full reasoner.

### Why not schema.org / Dublin Core alone
DC is good for bibliographic metadata but lacks event/actor/place structure.
CIDOC-CRM gives the full cross-tradition comparative structure we need.

### Thompson Motif Index
25 core motifs each mapped to TMI codes (A-series cosmogony, B-series animals,
C-series taboo, E-series underworld, F-series marvels, K-series deception,
L-series reversal of fortune, T-series sex). Codes stored as `myth:thompsonCode`
datatype property — used for academic cross-referencing.

### Deity cognate pairs (33 pairs, curated)
Key PIE (Proto-Indo-European) cognates:
- Zeus = Jupiter = Dyaus Pita = (structurally) Odin/Tyr = Indra = Marduk
- Thor = Indra (thunder/storm deity with weapon)
- Thoth = Hermes Trismegistus (explicit ancient syncretism)
- Osiris = Dionysus (Plutarch's explicit comparison in De Iside)
- Amaterasu = Ra (solar deity, structural parallel)
- Ahura Mazda → Varuna (PIE *asura)

### Concept equivalences seeded
- dharma ~ logos (universal order principles, cross-tradition)
- karma ~ cosmic_order
- tao ~ logos (Matteo Ricci's 17th-c. translation insight)
- moksha ~ soul_immortality

## Second scraper run (Jul 23 2026) — URL repair pass (25 fixes)
- Scraper exited with code 1 after first full run: 88/116 success, 28 failures
- All 28 failures were genuine 404s on sacred-texts.com (restructured paths)
- Diagnosed by probing section index pages via web_extract (curl blocked by Cloudflare)
- Fixed 25 of 28 URLs in text_manifest.py; 3 are content gaps (no longer on site)
- State repair: cleared `failed=[]`, removed failed entries from `downloaded` list
- Restarted scraper — picks up from entry 12+ (88 already-done entries skipped)
- See references/sacred-texts-url-repairs-2026.md for full repair table
- Result: 115/116 success, 1 failure (`ane/bal/index.htm` missed in first repair pass)

## Third scraper run (Jul 23 2026) — final 1-entry repair
- Failure: `ane/bal/index.htm` ("Babylonian and Assyrian Literature") — not in the
  original 28-failure list; surfaced only after second run completed
- Fixed to `ane/mba/index.htm` (Myths of Babylonia and Assyria — confirmed live)
- Cleared `failed=[]`, removed entry from `downloaded`, restarted
- Result: 116/116 success, 0 failures — corpus complete

## Runtime issues encountered and fixed

1. `NameError: name 'Path' is not defined` in ontology.py
   - Cause: `from pathlib import Path` was missing; `Path` only used in `__main__`
   - Fix: added import at file top with other imports
   - Lesson: always import at file level, not implicitly inside `__main__`

2. Pyright `reportArgumentType` on chromadb `OpenAIEmbeddingFunction`
   - Not a runtime error; chromadb's type stubs are loose
   - Suppressed by ignoring (not a functional issue)

3. Multiple orphaned scraper instances from prior sessions
   - Cause: new session started scraper without checking existing processes
   - Fix: `pgrep -f "python3 scraper.py" | sort -n | tail -n +2 | xargs kill`
   - Symptom: duplicate log lines, same page fetched 3x concurrently

4. Watchdog cron didn't fire after creation
   - Cause: scheduler didn't advance next_run_at until manually triggered
   - Fix: immediately follow `cronjob(action='create')` with `cronjob(action='run', job_id=...)`
   - The ~10 hour overnight stall wasn't caught by the watchdog because of this

5. DNS resolution failures (transient)
   - `Name or service not known` on ~3 pages mid-run
   - Scraper retried automatically and recovered — no intervention needed

6. ~24% of curated URLs were 404 after first full run
   - Cause: sacred-texts.com restructured paths since manifest was written
   - Fix: probe section indexes, try sibling paths, patch manifest, reset state
   - curl is blocked by Cloudflare — use web_extract tool or requests.Session instead
   - 25 URLs corrected; 3 genuine content gaps (Campbell, Sioux, Pistis Sophia)
   - Full repair table: references/sacred-texts-url-repairs-2026.md

## ChromaDB collection name: sacred_texts
## Embedding model: text-embedding-3-small (same as Hindsight)
## OPENAI_API_KEY: available via hermes config (confirmed)
