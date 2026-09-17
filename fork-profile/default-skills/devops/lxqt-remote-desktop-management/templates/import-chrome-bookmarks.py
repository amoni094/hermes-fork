#!/usr/bin/env python3
"""Import Chrome bookmarks (from Takeout HTML) into Firefox places.sqlite.

Usage:
    Close Firefox first, then:
    sudo python3 import-chrome-bookmarks.py

Defaults to Galina's profile. Edit PROFILE and HTML paths as needed.
"""
import sqlite3
import os
import shutil
import time
from html.parser import HTMLParser
from datetime import datetime
from urllib.parse import urlparse

# --- EDIT THESE ---
PROFILE = '/home/galina/.mozilla/firefox/cedyyfvu.default-release'
HTML    = '/home/galina/Downloads/takeout/Takeout/Chrome/Bookmarks.html'
FOLDER_NAME = 'Imported from Chrome'
# ------------------

DB = os.path.join(PROFILE, 'places.sqlite')


class ChromeBookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bookmarks = []
        self.in_a = False
        self.current_url = None
        self.current_title = ''
        self.current_date = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.in_a = True
            self.current_url = attrs.get('href', '')
            add_date = attrs.get('add_date', '0')
            try:
                self.current_date = int(add_date)
            except Exception:
                self.current_date = int(time.time())
            self.current_title = ''

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_a:
            if self.current_url and self.current_url.startswith(('http', 'https', 'ftp')):
                self.bookmarks.append({
                    'url': self.current_url,
                    'title': self.current_title.strip(),
                    'date_added': self.current_date
                })
            self.in_a = False
            self.current_url = None

    def handle_data(self, data):
        if self.in_a:
            self.current_title += data


# Parse bookmarks HTML
parser = ChromeBookmarkParser()
with open(HTML, 'r', encoding='utf-8') as f:
    parser.feed(f.read())
bookmarks = parser.bookmarks
print(f'Parsed {len(bookmarks)} bookmarks')

# Backup DB
backup_path = DB + '.bak_' + datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(DB, backup_path)
print(f'DB backed up to {backup_path}')

conn = sqlite3.connect(DB)
c = conn.cursor()

# Find the "Other Bookmarks" / unfiled root
c.execute("SELECT id FROM moz_bookmarks WHERE guid='unfiledBookmarks'")
row = c.fetchone()
if not row:
    c.execute("SELECT id FROM moz_bookmarks WHERE type=2 AND title='unfiled'")
    row = c.fetchone()
unfiled_id = row[0] if row else 5
print(f'Unfiled folder id: {unfiled_id}')

# Create import folder
now_micro = int(time.time() * 1_000_000)
c.execute('SELECT MAX(position) FROM moz_bookmarks WHERE parent=?', (unfiled_id,))
max_pos = c.fetchone()[0] or 0
c.execute(
    "INSERT INTO moz_bookmarks (type, parent, position, title, dateAdded, lastModified, guid) "
    "VALUES (2, ?, ?, ?, ?, ?, lower(hex(randomblob(9))))",
    (unfiled_id, max_pos + 1, FOLDER_NAME, now_micro, now_micro)
)
folder_id = c.lastrowid
print(f'Created folder "{FOLDER_NAME}" id: {folder_id}')

# Insert bookmarks
inserted = skipped = 0
for i, bm in enumerate(bookmarks):
    url   = bm['url']
    title = bm['title'] or url
    date_micro = bm['date_added'] * 1_000_000

    # Get or create place (URL entry)
    c.execute('SELECT id FROM moz_places WHERE url=?', (url,))
    row = c.fetchone()
    if row:
        place_id = row[0]
    else:
        try:
            parsed   = urlparse(url)
            rev_host = parsed.netloc[::-1] + '.'
            c.execute(
                "INSERT INTO moz_places (url, title, rev_host, visit_count, hidden, typed, guid) "
                "VALUES (?, ?, ?, 0, 0, 0, lower(hex(randomblob(9))))",
                (url, title, rev_host)
            )
            place_id = c.lastrowid
        except Exception as e:
            print(f'  Skip place: {url[:60]} — {e}')
            skipped += 1
            continue

    # Insert bookmark
    try:
        c.execute(
            "INSERT INTO moz_bookmarks (type, fk, parent, position, title, dateAdded, lastModified, guid) "
            "VALUES (1, ?, ?, ?, ?, ?, ?, lower(hex(randomblob(9))))",
            (place_id, folder_id, i, title, date_micro, now_micro)
        )
        inserted += 1
    except Exception as e:
        print(f'  Skip bookmark: {title[:40]} — {e}')
        skipped += 1

conn.commit()
conn.close()
print(f'Done: {inserted} inserted, {skipped} skipped')
