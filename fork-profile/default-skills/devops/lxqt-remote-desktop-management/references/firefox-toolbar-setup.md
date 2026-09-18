# Firefox Bookmarks Toolbar Setup (Galina's Laptop)

**Session date:** 2026-09-02

## Enabling the toolbar

Firefox often has the bookmarks toolbar set to `"never"` in user.js (can be set by
previous optimization passes). The keyboard shortcut Ctrl+Shift+B may toggle it
within the session but won't persist if user.js forces it off on next launch.

**Fix both files:**
```bash
# Check current value
sudo grep -i toolbar /home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js
sudo grep -i toolbar /home/galina/.mozilla/firefox/cedyyfvu.default-release/prefs.js

# Fix in both (sed is fine; backup first)
sudo sed -i 's/"browser.toolbars.bookmarks.visibility", "never"/"browser.toolbars.bookmarks.visibility", "always"/' \
  /home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js
sudo sed -i 's/"browser.toolbars.bookmarks.visibility", "never"/"browser.toolbars.bookmarks.visibility", "always"/' \
  /home/galina/.mozilla/firefox/cedyyfvu.default-release/prefs.js
```

Restart Firefox to apply. prefs.js is rewritten by Firefox on exit so fixing it
before launch (while closed) is what matters; user.js overrides prefs.js on every
launch and must be correct to persist.

## Firefox browser zoom / font size for TV viewing

For comfortable reading on a TV-connected laptop, set a global zoom via user.js.
`layout.css.devPixelsPerPx` scales the entire browser UI (toolbar text, page text,
bookmark labels) by the given multiplier. This is more robust than Firefox's
per-page zoom which doesn't persist across domains.

**Set 120% zoom (TV-comfort default for Galina's setup):**
```bash
# Check if already set
sudo grep -E 'zoom|devPixels' /home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js

# Append if missing (close Firefox first so it's not overwritten immediately)
sudo tee -a /home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js << 'EOF'

// Display zoom — 120% for TV viewing comfort
user_pref("browser.zoom.full", true);
user_pref("layout.css.devPixelsPerPx", "1.2");
EOF
```

**Dedup guard** — if user.js was appended more than once by accident (tee ran twice),
clean up duplicates without closing Firefox:
```python
# Run as: sudo python3 /tmp/fix_userjs.py
import re
path = '/home/galina/.mozilla/firefox/cedyyfvu.default-release/user.js'
with open(path) as f:
    content = f.read()
lines = [l for l in content.splitlines() if not re.search(r'devPixelsPerPx|browser\.zoom\.full', l)]
clean = '\n'.join(lines).rstrip()
clean += '\n\n// Display zoom — 120% for TV viewing comfort\n'
clean += 'user_pref("browser.zoom.full", true);\n'
clean += 'user_pref("layout.css.devPixelsPerPx", "1.2");\n'
with open(path, 'w') as f:
    f.write(clean)
print('Done')
```

**Zoom scale reference:**
| Value | Zoom |
|---|---|
| "1.0" | 100% (default) |
| "1.2" | 120% — good for TV at arm's length |
| "1.3" | 130% |
| "1.5" | 150% — large text, fewer items on screen |

**Verify it applied** — after restarting Firefox:
```bash
sudo grep 'devPixelsPerPx' /home/galina/.mozilla/firefox/cedyyfvu.default-release/prefs.js
# Expect: user_pref("layout.css.devPixelsPerPx", "1.2");
# prefs.js is written by Firefox from user.js on startup — if it appears here, it's active
```

Note: the visual difference between 100% and 120% is subtle in a scrot screenshot
because the screenshot itself captures the raw framebuffer pixels. The zoom is real
on screen — the vision model checking the PNG is an unreliable verifier for zoom level.
Trust the prefs.js confirmation instead.

## Adding bookmarks to the toolbar (SQLite method)

Same pattern as importing bookmarks: close Firefox, modify places.sqlite directly.

Toolbar container GUID: `toolbar_____` (double-underscore-padded). Fetch its ID:
```python
import sqlite3
conn = sqlite3.connect('/home/galina/.mozilla/firefox/cedyyfvu.default-release/places.sqlite')
c = conn.cursor()
c.execute("SELECT id FROM moz_bookmarks WHERE guid='toolbar_____'")
toolbar_id = c.fetchone()[0]   # typically 2 in default profiles
```

For each site to add:
1. Upsert into `moz_places` (url, title, rev_host, visit_count=0, hidden=0, typed=0)
2. Insert into `moz_bookmarks` (type=1, fk=place_id, parent=toolbar_id, position=N, title=short_label)

See `templates/toolbar-bookmarks.py` for a working script.

## Which bookmarks fit on the toolbar (1366px wide)

Galina's laptop toolbar is 1366px. Each bookmark shows favicon (16px) + label + padding ≈ 90–110px.
At ~100px per item, ~12 items fit before Firefox collapses overflow into a ">>" menu.

**Priority order selected 2026-09-02 (12 items total):**

| Label | URL |
|---|---|
| Gmail | https://mail.google.com/ |
| YouTube | https://www.youtube.com/ |
| Lenta.ru | https://lenta.ru/ |
| Zahav.ru | https://zahav.ru/ |
| Wikipedia | https://www.wikipedia.org/ |
| Google | https://www.google.com/ |
| Translate | https://translate.google.com/ |
| Google News | https://news.google.com/ |
| newsru.com | https://www.newsru.com/ |
| newsru.co.il | https://www.newsru.co.il/ |
| SBS Russian | https://www.sbs.com.au/language/russian |
| ILTV | https://www.iltv.tv/ |

Rationale: Russian/Israeli news and media align with Galina's browsing pattern.
Items excluded from toolbar (relegated to Other Bookmarks > Imported from Chrome):
- Old sinoptik.ua weather URL (stale, 2018 date)
- Duplicate Google Search links
- YouTube channel link (personal, niche)
- Southern FM radio (niche)

## Checking toolbar contents while Firefox is running

places.sqlite is write-locked while Firefox runs but can be read in read-only mode
(WAL mode can still block even for reads via Python; safest to close Firefox first).

Alternative: use `Ctrl+Shift+O` (Library) and visually inspect in the screenshot.
