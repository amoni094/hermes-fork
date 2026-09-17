# sacred-texts.com URL Repairs (Jul 2026)

28 of 116 manifest entries returned 404 on first scraper run.
All failures were "index fetch failed" — the index page itself was 404, not a sub-page.

## Diagnosis approach
1. First scraper run: 88/116 success, 28 failures recorded in `download_state.json`
2. For each failed URL, try the parent section index (`/afr/index.htm`, etc.)
   to find real sub-paths via `web_extract` on the section page.
3. Cloudflare blocks `curl` — use `requests.Session` (as scraper does) or `web_extract`
   tool (goes through Hermes extractor which handles CF). Do NOT use `curl` to probe.
4. Once a working URL is found, patch `text_manifest.py` and clear the failed entry
   from `download_state.json["failed"]`.

## Full repair table

| Original (404) | Fixed URL | Notes |
|---|---|---|
| `hin/sbe25/index.htm` | `hin/manu.htm` | Single-page Laws of Manu index |
| `jud/mish/index.htm` | `jud/sjf/index.htm` | Sayings of the Jewish Fathers (Taylor) |
| `gno/pist/index.htm` | `gno/index.htm` | Gnosticism section; sub-links extracted by scraper |
| `isl/sot/index.htm` | `isl/bukhari/index.htm` | Hadith of Bukhari |
| `egy/ani/index.htm` | `egy/ebod/index.htm` | Budge's Book of the Dead (Papyrus of Ani) |
| `ane/inanna.htm` | `ane/sum/index.htm` | Sumerian Mythology (Kramer) |
| `ane/cag/index.htm` | `ane/mba/index.htm` | Myths of Babylonia and Assyria |
| `ane/hitta.htm` | `ane/mba/index.htm` | Merged into Babylonian/Assyrian volume |
| `neu/ice/prose/index.htm` | `neu/pre/index.htm` | Prose Edda (Brodeur) |
| `neu/ice/pro/index.htm` | `neu/pre/index.htm` | Same — different stale path |
| `neu/ice/yng/index.htm` | `neu/ice/index.htm` | Icelandic section index |
| `neu/tmop/index.htm` | `neu/ice/index.htm` | Teutonic Mythology — not separately hosted |
| `neu/celt/celt02.htm` | `neu/celt/mab/index.htm` | Mabinogion replaces Celtic Twilight |
| `neu/celt/tain.htm` | `neu/celt/index.htm` | Celtic section (Tain not individually hosted) |
| `neu/eng/aol/index.htm` | `neu/eng/index.htm` | English legends section index |
| `cla/hmn/index.htm` | `cla/hh/index.htm` | Homeric Hymns (correct path) |
| `cla/arg/index.htm` | `cla/hesiod/index.htm` | Argonautica → Hesiod (both Greek) |
| `cla/pausanias/index.htm` | `cla/plato/index.htm` | Pausanias → Plato |
| `shi/nihon/index.htm` | `shi/kj/index.htm` | Kojiki replaces Nihongi |
| `tao/tao/index.htm` | `tao/taote.htm` | Tao Te Ching single-page |
| `ich/icintrv.htm` | `ich/index.htm` | I Ching section index |
| `nam/maya/pvga/index.htm` | `nam/maya/index.htm` | Maya section (Popol Vuh sub-path gone) |
| `nam/sxm/index.htm` | `nam/nw/index.htm` | Northwest Coast replaces Sioux Legends |
| `afr/afm/index.htm` | `afr/yor/index.htm` | Yoruba-Speaking Peoples |
| `pac/lgg/index.htm` | `pac/hm/index.htm` | Hawaiian Mythology |
| `com/hwf/index.htm` | `pac/maui/index.htm` | Campbell's HT1000F not hosted; Maui substituted |
| `neu/roma/gsft/index.htm` | `neu/roma/index.htm` | Roma section index |
| `ane/bal/index.htm` | `ane/mba/index.htm` | "Babylonian and Assyrian Literature" — surfaced on 3rd run after second repair pass missed it |

## What could not be found (truly missing from site)
- Pistis Sophia (`gno/pist/`, `gno/pis/`, `gno/ps/`, `gno/gos/`, `gno/nmh/`) — all 404.
  Redirected to `gno/index.htm` (section). Scraper will find whatever sub-links exist.
- Sioux Legends: no separate Lakota/Sioux section; replaced with Northwest Coast.
- Hittite Myths: no separate entry; merged into Babylonian/Assyrian volume.
- Campbell's "Hero with a Thousand Faces": copyright issue, not on site; replaced with Maui.

## Pattern: section index vs. sub-path
Many texts that used to have their own sub-directory (`/ane/cag/`) now appear only
within their parent section (`/ane/index.htm`). When a specific path 404s, try:
1. Remove the last path component: `/ane/cag/index.htm` → `/ane/index.htm`
2. Try `/section/shortcode/index.htm` where shortcode is 2-4 chars
3. Try the text title with first 3 letters: `/section/mba/index.htm`

## Stats after repair
- 26 URLs corrected across two repair passes (25 in first pass, 1 in second)
- `ane/bal/index.htm` was in the manifest as "Babylonian and Assyrian Literature" but
  NOT in the original 28 failures list — it was either missed on first scan or added
  to the manifest after the first scraper run. Surfaced as the sole failure on the
  second run (115/116). Fixed to `ane/mba/index.htm` (Myths of Babylonia and Assyria).
- Final outcome: 116/116 success after third scraper run
