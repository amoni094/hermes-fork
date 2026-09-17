# Native-Language Primary Source Fetching
# July 2026 — comparative mythology corpus extension

## The Problem

sacred-texts.com's "native language" pages are often HTML shells with
zero actual script content. When the scraper downloads them, the `.txt`
files contain only navigation markup. Confirmed zero-content languages
after scraping (checked with Python Unicode range scan):

- Hebrew Tanakh: bare verse numbers only, no Hebrew Unicode (U+05D0–U+05EA)
- Arabic Quran: HTML entity-mangled, 0 Arabic chars (U+0600–U+06FF)
- Sanskrit Rig-Veda: redirect pages only, 0 Devanagari (U+0900–U+097F)
- Old Norse Prose Edda: actually the English Brodeur translation, mislabelled

Implication: ALL motif analysis, cross-linking, and structural schema analysis
was performed on English translations. Features that only exist in the original
language (gematria, root morphology, meter, character semantics) are invisible.

---

## Confirmed Working APIs and Sources

### 1. Hebrew — Sefaria REST API
**URL pattern**: `https://www.sefaria.org/api/texts/{book}.{chapter}?lang=he&context=0&pad=0`
**Books**: Standard book names (Genesis, Exodus, Isaiah, Psalms, etc.)
**Returns**: JSON with `he` array of verse strings (HTML-tagged nikud; strip with `re.sub(r'<[^>]+>', '', s)`)
**Rate**: Polite 1s delay; no auth needed for public texts
**Confirmed working** (Jul 2026): Genesis, Exodus, Psalms, Sefer Yetzirah (6 chapters)
**Sefer Yetzirah path**: `Sefer_Yetzirah.{ch}` (chapters 1-6)

Sample:
```python
r = requests.get('https://www.sefaria.org/api/texts/Genesis.1?lang=he&context=0', timeout=15)
verses = r.json().get('he', [])  # ['בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים...', ...]
```

### 2. Arabic — quran.com API v4
**URL pattern**: `https://api.quran.com/api/v4/quran/verses/uthmani?chapter_number={N}`
**Returns**: JSON with `verses` array, each having `text_uthmani` (fully vowelled Uthmani script)
**Chapters endpoint**: `https://api.quran.com/api/v4/chapters` → 114 suras with Arabic names
**No auth needed**; rate-limit-friendly with 1s delay
**Confirmed working** (Jul 2026): Sura 1 (Al-Fatiha) → `بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ`

Sample:
```python
r = requests.get('https://api.quran.com/api/v4/quran/verses/uthmani?chapter_number=1', timeout=15)
verses = r.json().get('verses', [])
text = verses[0]['text_uthmani']  # Arabic Uthmani script
```

### 3. Sanskrit — GRETIL mirror on GitHub (IAST, convert to Devanagari)
**Repo**: `INDOLOGY/GRETIL-mirror` on GitHub
**CRITICAL**: `_u` suffix means "Unicode" but the content is **IAST Latin transliteration**
  (ā, ī, ū, ṛ, ṭ, ḍ, ṇ, ś, ṣ, ḥ, ṃ), NOT Devanagari Unicode. Zero chars in U+0900–U+097F.
**To get Devanagari**: convert IAST → Devanagari using `indic-transliteration`:
  ```bash
  pip install indic-transliteration
  ```
  ```python
  from indic_transliteration import sanscript
  from indic_transliteration.sanscript import transliterate
  deva = transliterate(iast_text, sanscript.IAST, sanscript.DEVANAGARI)
  ```
**Rigveda path**: `gretil.../1_sanskr/1_veda/1_sam/1_rv/rv_{N:02d}_u.htm` (N=01–10)
**Additional Sanskrit**: Mahabharata `1_sanskr/2_epic/mbh/mbh_0{N}_u.htm`; Ramayana
  `1_sanskr/2_epic/ramayana/ram_0{N}_u.htm`; Samaveda `1_sanskr/1_veda/1_sam/samavedu.htm`;
  Atharvaveda `1_sanskr/1_veda/1_sam/avs___u.htm`; Yoga Sutras `1_sanskr/6_sastra/3_phil/yoga/patyog_u.htm`
**Pali additional**: Digha Nikaya `2_pali/1_tipit/2_sut/1_digh/dighan{N}u.htm`;
  Majjhima `2_sut/2_majjh/majjhi1u.htm`; Vinaya `2_pali/1_tipit/1_vin/mahavg_u.htm`
  (**NOT** `2_pali/2_canon/4_kn/dhp___pu.htm` — that path returns 404)
**Extraction pattern**:
  ```python
  soup = BeautifulSoup(r.content.decode('utf-8', errors='replace'), 'html.parser')
  for tag in soup(['script', 'style', 'head', 'table']): tag.decompose()
  text = soup.get_text('\n')
  # Skip GRETIL header (lines with: GRETIL, TEXT FILE, COPYRIGHT, Unicode, UTF-8, etc.)
  lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 3
           and not any(kw in l for kw in ['GRETIL', 'TEXT FILE', 'COPYRIGHT', 'Unicode',
                                           'UTF-8', 'Input by', 'research-only'])]
  ```

### 4. Classical Chinese — Kanripo GitHub (ctext.org BLOCKED)
**ctext.org**: Returns **HTTP 403** to automated requests as of Jul 2026. Do not use.
**Use Kanripo instead**: `github.com/kanripo/{REPO}` — all public, no auth, no bot blocking.
**URL pattern**: `https://raw.githubusercontent.com/kanripo/{REPO}/master/{REPO}_{N:03d}.txt`
**Key repos**:
  - KR5c0057 = Tao Te Ching (老子, 2 fascicles — **INCOMPLETE**, only 2/81 chapters)
  - KR1a0001 = I Ching (易經, 10 fascicles — only 10/64 hexagrams)
  - KR1h0004 = Analects (論語, 10 fascicles — 10/20 books)
  - KR5c0126 = Zhuangzi (莊子, 10 fascicles)
  - KR1h0001 = Mencius (孟子, 7 fascicles)
  - KR1b0001 = Shu King (書經, ~20 fascicles)
  - KR1d0052 = Li Ji (禮記)
  - KR5c0124 = Liezi (列子)
**Kanripo files are FRAGMENTS**: TLS edition files are scholarly samples, not complete texts.
  For full TTC: `curl -sL "https://www.gutenberg.org/files/7337/7337-0.txt"` (Wang Bi tradition)
**Markup**: Strip `<pb:...>¶` page markers, `#+TITLE/#+PROPERTY` headers, `** N 章` chapter markers, `¶` pilcrows

### 5. Old Norse — Heimskringla.no wiki
**URL pattern**: `https://heimskringla.no/wiki/{Title}` (uses Norwegian wiki conventions)
**Available sections**: Gylfaginning, Skáldskaparmál, Háttatal, Völuspá, Hávamál
**Parse**: Find `<div id="mw-content-text">`, get_text(), filter lines with ≥1
  Old Norse chars (ð, Ð, þ, Þ, æ, Æ, ö, á, í, ó, ú, ý)
**Confirmed working** (Jul 2026): Gylfaginning (127KB page, 4451 Norse chars)
**Note**: voluspa.org returns 404 for Gylfaginning; use heimskringla.no instead
**Note**: Direct `/wiki/Gylfaginning_(Norrønt)` path returns 404; use base path

### 6. Pali — GRETIL mirror
**Path**: `gretil.sub.uni-goettingen.de/gretil/2_pali/2_canon/4_kn/dhp___pu.htm`
**Content**: Dhammapada in Pali (Latin-extended charset: ā, ī, ū, ṭ, ḍ, ṇ, ṅ, ñ, etc.)
**Filter**: Lines with ≥5 characters; Pali has no unique Unicode block — filter by length + content

---

## Output Structure

```
~/Religion/native_lang/
  hebrew/
    tanakh/
      genesis_he.txt
      exodus_he.txt
      ...
    kabbalah/
      sefer_yetzirah_he.txt
  arabic/
    quran/
      sura_001.txt
      sura_002.txt
      ...
  sanskrit/
    rigveda/
      rigveda_book01.txt
      ...
  classical_chinese/
    tao-te-ching/
      tao-te-ching_zh.txt
    book-of-changes/
      book-of-changes_zh.txt
  old_norse/
    Gylfaginning_on.txt
    V_lusp__on.txt
    H_vam_l_on.txt
  pali/
    dhammapada_pali.txt
```

---

## Additional Confirmed-Working Sources (July 2026)

### 7. Ancient Greek — Perseus Digital Library
**Repo**: `PerseusDL/canonical-greekLit` on GitHub
**URL pattern**: `https://raw.githubusercontent.com/PerseusDL/canonical-greekLit/master/data/tlg{AUTHOR}/tlg{WORK}/tlg{AUTHOR}.tlg{WORK}.perseus-grc2.xml`
**Key TLG numbers**: Iliad tlg0012/tlg001, Odyssey tlg0012/tlg002, Hesiod tlg0020/tlg001,
  Homeric Hymns tlg0013/tlg001, Argonautica tlg0001/tlg001, Pausanias tlg0525/tlg001,
  Plato Republic tlg0059/tlg030
**Parse**: BeautifulSoup XML mode; strip `<note>`, `<milestone>`, `<pb>`, `<lb>` tags;
  find `<text>` or `<body>` element; get_text(separator='\n'); filter lines >5 chars
**Confirmed working** (Jul 2026): all listed texts return HTTP 200

### 8. Latin — Perseus Digital Library
**Repo**: `PerseusDL/canonical-latinLit` on GitHub
**URL pattern**: `.../data/phi{AUTHOR}/phi{WORK}/phi{AUTHOR}.phi{WORK}.perseus-lat2.xml`
**Key PHI numbers**: Aeneid phi0690/phi003, Metamorphoses phi0959/phi006
**Parse**: Same pattern as Greek above
**Confirmed working** (Jul 2026): both texts HTTP 200

### 9. Old Irish / Middle Welsh — CELT Corpus
**Base URL**: `https://celt.ucc.ie/published/T{ID}.html`
**Key IDs**: T301012 (Tain Bo Cuailnge, Old Irish), T300010 (Cath Maige Tuired),
  T301042 (Acallam na Senorach), T102003 (Mabinogion, Middle Welsh)
**Parse**: Find `div.text` or `div#text`; fall back to `body`; get_text(separator='\n')
**Confirmed working** (Jul 2026): T301012 (Tain) HTTP 200; T102003 (Mabinogion) confirmed

### 10. Old Japanese — Japanese Wikisource
**URL pattern**: `https://ja.wikisource.org/wiki/{TITLE}`
**Titles**: `古事記` (Kojiki), `日本書紀` (Nihon Shoki)
**Parse**: Find `div#mw-content-text`; remove `div.noprint` and `span.mw-editsection`;
  get_text(separator='\n'); filter lines >3 chars
**Content check**: Count CJK chars (U+4E00–U+9FFF, U+3040–U+30FF) — should be >1000 for real content

### 11. Arabic Hadith
**URL**: `https://api.hadith.gading.dev/books/bukhari?range=1-50`
**Returns**: JSON with `.data.hadiths[].arab` field containing Arabic text
**No auth needed**; returns small batches; iterate range parameters for more hadiths

### 12. Punjabi/Gurmukhi — Shabados Database
**Repo**: `github.com/shabados/database` (74 stars)
**Structure**: `collections/lines/` directory contains JSON files with `gurmukhi` field per line
**Auth**: None; GitHub raw access works
**Note**: The database uses a Node.js build process; raw JSON files are in collections/

### Not Yet Reachable (Jul 2026)
- **Ge'ez/Ethiopic** (Kebra Nagast): No machine-readable source found; ethiopic Unicode
  block U+1200–U+137F. Try: `geez.org`, `EMML` (Ethiopian Manuscript Microfilm Library)
- **Ardhamagadhi Prakrit** (Jain Sutras): `jainlibrary.org` requires auth; GRETIL's
  `2_prakrt/` directory was empty or inaccessible
- **Cuneiform Akkadian/Sumerian**: CDLI provides ATF (ASCII Transliteration Format),
  not Unicode cuneiform (U+12000–U+1237F). The ATF bulk file is accessible at
  `github.com/cdli-gh/data/cdliatf_unblocked.atf` but is Latin script only

## Fetch Scripts
- `~/Religion/scripts/fetch_native_languages.py` — initial 6 languages
- `~/Religion/scripts/fetch_native_lang_patch.py` — patches Sanskrit (IAST→Devanagari), Chinese (Kanripo), Pali
- `~/Religion/scripts/fetch_all_native_languages.py` — comprehensive: all 116 texts, 15+ languages

Run with:
```bash
python3 fetch_native_languages.py             # all languages
python3 fetch_native_languages.py --only hebrew
python3 fetch_native_languages.py --only arabic
python3 fetch_native_languages.py --only sanskrit
python3 fetch_native_languages.py --only chinese
python3 fetch_native_languages.py --only norse
python3 fetch_native_languages.py --only pali
```
Estimated run time: ~45-60 min total (Hebrew Torah alone ~187 API calls at 1s each).

---

## Structural Schema Analysis — What Requires Native Language

These features are invisible in English translation and require the native texts:

| Feature | Language | Why it matters |
|---------|----------|----------------|
| Gematria (letter=number) | Hebrew | The Zohar's "32 Elohim" count only works in Hebrew |
| Root morphology (triliteral) | Hebrew, Arabic | Semantic field overlap across words with shared root |
| Chandas (syllable meter) | Sanskrit | Gayatri (3×8=24) is cosmologically constitutive |
| Sura/Aya counting (base-19) | Arabic | Rashad Khalifa's structural analysis invisible in translation |
| Hexagram binary structure | Classical Chinese | 64-hexagram logic survives translation but character semantics don't |
| Runic character shape | Old Norse | Elder Futhark letter-meanings are shape-semantic, not phonetic |

After fetching native texts, the structural schema analysis proceeds by:
1. Hebrew: count Elohim occurrences in Genesis (should be 32), count letter frequencies
2. Arabic: count Bismillah repetitions, Sura lengths vs. numerical position
3. Sanskrit: identify Gayatri-metered verses by syllable count (3 padas × 8 syllables)
4. Classical Chinese: hexagram binary sequence analysis, key character etymologies
5. Old Norse: cosmological number enumeration (9/3/12 structure in Gylfaginning)
