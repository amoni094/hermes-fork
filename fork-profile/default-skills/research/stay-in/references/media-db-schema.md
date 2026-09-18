# Media DB Schema — /var/home/rainbow/media_sample_db

Discovered 2026-07-20. Record here to avoid failed inserts from CHECK constraint violations.

## Files

- `media_items.csv` — flat catalog of all items (same columns as `media_item` table)
- `verify.db` — SQLite database (canonical source)
- `schema.sql`, `seed.sql` — definitions and seed data
- `README.txt` — project notes

## Tables

### media_item

Primary catalog. Slug is PK.

```sql
CREATE TABLE media_item (
  slug TEXT PRIMARY KEY,
  title_display TEXT NOT NULL,
  title_canonical TEXT NOT NULL,
  media_type TEXT NOT NULL CHECK (media_type IN ('film','tv_series','miniseries','tv_season')),
  release_year INTEGER NOT NULL,
  end_year INTEGER,
  country TEXT,
  original_language TEXT,
  original_title TEXT,
  director_or_creator TEXT,
  based_on TEXT,
  franchise_slug TEXT REFERENCES franchise(slug),
  series_parent_slug TEXT,
  season_scope TEXT,
  genres TEXT,
  summary TEXT NOT NULL,
  notes TEXT
)
```

**CHECK constraint: media_type must be one of:**
  `film`, `tv_series`, `miniseries`, `tv_season`

Do NOT use: `tv`, `movie`, `series`, `TV`, etc. These will silently fail with OR IGNORE.

### user_media_feedback

Stores seen/rated history.

```sql
CREATE TABLE user_media_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title_slug TEXT NOT NULL REFERENCES media_item(slug),
  user_label TEXT NOT NULL DEFAULT 'default_user',
  seen INTEGER NOT NULL CHECK (seen IN (0,1)) DEFAULT 1,
  preference TEXT NOT NULL CHECK (preference IN ('liked','disliked','mixed')),
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**CHECK constraint: preference must be one of:**
  `liked`, `disliked`, `mixed`

Do NOT use numeric scores (6, 7, etc.) or text like 'rated'. Map ratings to:
  - 8+ → `liked`
  - 6-7 → `mixed`
  - <6 → `disliked`

`title_slug` is a FK to `media_item(slug)` — the item MUST exist in media_item before inserting feedback.

### franchise

```sql
franchise columns: slug, name, kind
```

## Pitfalls

1. `OR IGNORE` silently swallows CHECK constraint failures — always test inserts without OR IGNORE first to see the real error message.
2. Feedback insert will silently fail if the media_item row doesn't exist yet (FK constraint). Insert media_item first, then feedback.
3. CSV and SQLite must be kept in sync manually — the CSV is not auto-generated from the DB.
4. `release_year` and `end_year` are INTEGER in DB but TEXT in CSV — use integers for DB inserts.
