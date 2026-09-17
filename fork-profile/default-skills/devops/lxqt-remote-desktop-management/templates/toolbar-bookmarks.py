#!/usr/bin/env python3
"""Add bookmarks to Firefox bookmarks toolbar via direct SQLite write.

Usage: close Firefox first, then sudo python3 toolbar-bookmarks.py
"""
import sqlite3, time, shutil
from datetime import datetime
from urllib.parse import urlparse

PROFILE = '/home/galina/.mozilla/firefox/cedyyfvu.default-release'
DB = PROFILE + '/places.sqlite'

# Short label, full URL — keep labels terse so more fit on the bar
TOOLBAR_BOOKMARKS = [
    ('Gmail',        'https://mail.google.com/'),
    ('YouTube',      'https://www.youtube.com/'),
    ('Lenta.ru',     'https://lenta.ru/'),
    ('Zahav.ru',     'https://zahav.ru/'),
    ('Wikipedia',    'https://www.wikipedia.org/'),
    ('Google',       'https://www.google.com/'),
    ('Translate',    'https://translate.google.com/'),
    ('Google News',  'https://news.google.com/'),
    ('newsru.com',   'https://www.newsru.com/'),
    ('newsru.co.il', 'https://www.newsru.co.il/'),
    ('SBS Russian',  'https://www.sbs.com.au/language/russian'),
    ('ILTV',         'https://www.iltv.tv/'),
]

# Backup
backup = DB + '.bak_toolbar_' + datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(DB, backup)
print(f'Backed up to {backup}')

conn = sqlite3.connect(DB)
c = conn.cursor()

# Get toolbar container id
c.execute("SELECT id FROM moz_bookmarks WHERE guid='toolbar_____'")
row = c.fetchone()
if not row:
    raise RuntimeError('Toolbar container not found — is this a fresh profile?')
toolbar_id = row[0]
print(f'Toolbar container id: {toolbar_id}')

# Current max position in toolbar
c.execute('SELECT MAX(position) FROM moz_bookmarks WHERE parent=?', (toolbar_id,))
max_pos = c.fetchone()[0] or -1

now_micro = int(time.time() * 1_000_000)

for i, (label, url) in enumerate(TOOLBAR_BOOKMARKS):
    parsed = urlparse(url)
    rev_host = parsed.netloc[::-1] + '.'

    # Upsert place
    c.execute('SELECT id FROM moz_places WHERE url=?', (url,))
    row = c.fetchone()
    if row:
        place_id = row[0]
    else:
        c.execute(
            'INSERT INTO moz_places (url, title, rev_host, visit_count, hidden, typed, guid) '
            'VALUES (?, ?, ?, 0, 0, 0, lower(hex(randomblob(9))))',
            (url, label, rev_host)
        )
        place_id = c.lastrowid

    # Insert bookmark in toolbar
    c.execute(
        'INSERT INTO moz_bookmarks (type, fk, parent, position, title, dateAdded, lastModified, guid) '
        'VALUES (1, ?, ?, ?, ?, ?, ?, lower(hex(randomblob(9))))',
        (place_id, toolbar_id, max_pos + 1 + i, label, now_micro, now_micro)
    )
    print(f'  Added: {label}')

conn.commit()
conn.close()
print('Done. Start Firefox — toolbar will show all items.')
