# Political Theory & Scholarly Dissertation Critique — Reference Sources

Compiled August 2026 from a session producing a critical response PDF to Bailey Gladman,
"Popular Sovereignty and the Phenomenology of Political Identity in Carl Schmitt's Constitutional Theory"
(LSE MSc Dissertation, August 2026).

## Research Entry Points

### Stanford Encyclopedia of Philosophy (SEP)
- **Schmitt entry**: https://plato.stanford.edu/entries/schmitt/
  Author: Lars Vinx (revised March 2025). Authoritative overview: sovereignty, constituent power,
  friend/enemy distinction, homogeneity, liberal democracy critique, Böckenförde's personalistic
  reading, constitutional guardian problem, the authoritarian logic internal to constituent power.
  Use as the first stop for any Schmitt secondary literature map.
- **Heidegger entry**: https://plato.stanford.edu/entries/heidegger/
  Author: Michael Wrathall (revised 2025). Covers Mitsein, historicity (Geschichtlichkeit),
  co-historicising (Mitgeschehen), Dasein's thrownness and destiny (Geschick).
  Key for the 1934-35 Hegel seminar period (Nazi rectorship context) — do NOT bracket this
  political context when using the seminar material.

### Democracy Journal
- **"It's Carl Schmitt's Moment"**, James Traub, Democracy Journal, issue 77 (2025):
  https://democracyjournal.org/magazine/77/its-carl-schmitts-moment/
  Best available popularist synthesis of Schmitt's full intellectual trajectory with contemporary
  political application. Use to document the popular reception of Schmittian thought (Trump,
  Orbán, post-liberal right). NOT a peer-reviewed source — cite as popular/intellectual press
  alongside academic references.

## Key Secondary Literature (Schmitt)

| Author | Work | Key relevance |
|---|---|---|
| Vinx, Lars | SEP entry (2025) | Constitutional guardian problem; constituent power's authoritarian logic; Böckenförde's personalistic reading |
| Rubinelli, Lucia | *Constituent Power: A History* (Cambridge, 2020), pp. 103-140 | Genealogy of pouvoir constituant from Sieyès through Schmitt; inherent ambiguity between popular authorization and elite leadership |
| Vatter, Miguel | *Divine Democracy: Political Theology After Carl Schmitt* (Oxford, 2020) | Post-Schmittian pluralist account of the people as constituent multitude; challenges homogeneity requirement |
| Böckenförde, Ernst-Wolfgang | "The Concept of the Political: A Key to Understanding Carl Schmitt's Constitutional Theory" (1998, in *State, Society and Liberty*) | The canonical personalistic decisionist reading; Gladman's main analytical target |
| Kalyvas, Andreas | *Democracy and the Politics of the Extraordinary* (Cambridge, 2008) | Strong-democratic reading of Schmitt; overstates democratic credentials |
| Dyzenhaus, David | *Legality and Legitimacy* (Oxford, 1997) | Critical-liberal reading of Schmitt-Kelsen-Heller; counter-weight to revisionist appropriation |
| Scheuerman, William | *The End of Law*, 2nd ed. (2020) | Continuity thesis between Weimar Schmitt and Nazi Schmitt; meta-methodological challenge to bracketing |
| Marder, Michael | *Groundless Existence* (2010) | Fullest existing phenomenological account of Schmitt's political ontology (Heidegger connection) |
| Radloff, Bernhard | "Heidegger and Carl Schmitt" (2005) | Establishes historicity as the Heidegger-Schmitt conceptual bridge |
| Cristi, Renato | *Carl Schmitt and Authoritarian Liberalism* (1998) | Personalistic reading; important interlocutor for the Böckenförde tradition |

## Task Pattern: Scholarly Dissertation Critique → PDF Response

Confirmed working workflow (August 2026):

1. **Read the dissertation in full** via `read_file` (Telegram-sourced documents land in
   `~/.hermes/cache/documents/` with a `doc_<hash>_<title>.pdf` naming pattern; find with
   `find ~/.hermes/cache/documents -name "*.pdf" -newer <reference_file>`).

2. **Parallel research** — batch 4 web_search queries for the main scholarly axes simultaneously,
   then web_extract the SEP entries and key journal pieces. SEP is reliably accessible and
   authoritative; Democracy Journal is open-access. For peer-reviewed secondary lit, check if
   SearXNG (port 8888) is up; if not, fall back to direct web_extract against known URLs
   (plato.stanford.edu, specific journal pages).

3. **Structure the response** around:
   - Introduction: two-sentence honest verdict (what's right + the two main lacunae)
   - Section per major claim: what's defensible, then specific pushbacks
   - Missed interlocutors section (named works the dissertation should have engaged)
   - Adversarial pass section (internal stress-tests of the dissertation's own claims)
   - Conclusion that returns to the political stakes

4. **Write via `pdf_create.py`** using a JSON spec with heading/paragraph/table elements.
   Verify with `pdf_read.py --meta` (page_count, not scanned). Install `pdfplumber` first:
   `python3 -m pip install pdfplumber` (bare `pip` not available on this system).

5. **Adversarial pass** — after drafting, re-read and stress-test:
   - Are secondary sources cited at the right tier (not as primary authorities)?
   - Does the phenomenological/theoretical framework hold for all cases in the text, not just the ones that fit neatly?
   - Is the rehabilitation risk (scholarly legitimation of dangerous thought) acknowledged?
   - Are historical/biographical contexts bracketed that cannot defensibly be bracketed?

## Cross-Session Document Retrieval (Telegram → CLI session)

When the user shares a document in the Telegram gateway session and asks for it from CLI:

```
# 1. Check session DB directly
python3 -c "
import sqlite3, json
conn = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
cur = conn.cursor()
# check schema first
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
print(json.dumps(cur.fetchall()))
"

# 2. Find recent PDFs in Hermes cache
find /var/home/rainbow/.hermes/cache/documents -name "*.pdf" -newer <reference_file> 2>/dev/null

# 3. Broader recent file search
find /var/home/rainbow -newer <reference_file> -type f ! -path "*/.git/*" ! -path "*/cache/*" 2>/dev/null | head -30
```

Documents shared via Telegram are saved to `~/.hermes/cache/documents/` with hashed filenames.
The session DB (state.db) stores messages including file metadata and can be queried directly
when session_search returns no results for a cross-gateway document.
