# Title normalization examples

Use these patterns when curating user-supplied movie/TV lists into canonical catalog rows.

## 1) Typo-driven requests

If the intended title is obvious, normalize to the canonical release title and keep a short note only when the correction matters for future readers.

Examples:
- `Idiocrac` -> `Idiocracy`
- `He Died with a Felafel in his Hand` -> canonical release spelling for the film title

Suggested note shape:
- `Interpreted from your typo "Idiocrac" as Idiocracy.`

Do not preserve the typo in the main title fields.

## 2) Wrong media type, obvious intent

If the user names a TV series that does not exist but clearly means a known franchise or film set, map to the real catalog scope.

Example:
- `Pirates of the Caribbean TV series` -> franchise-linked film entries

Suggested note shape:
- `Included as a Pirates of the Caribbean franchise entry; no TV series exists.`

Only keep this note when the mismatch would otherwise confuse later readers.

## 3) Ambiguous title/version requests

When multiple notable versions exist, choose the version only if the user signaled enough intent; otherwise use a concise disambiguation note.

Examples:
- `3:10 to Yuma` -> `3:10 to Yuma (2007)` with `Interpreted as the 2007 film.`
- `Alexander (2004 movie)` -> `Alexander` with slug `alexander-2004` and note `2004 film.`

## 4) Scope notes for TV and miniseries

Use notes for scope when the row type alone is not enough or when the request explicitly constrained the entry.

Examples:
- `Limited series.`
- `Stored as Season 1 only, per your scope note.`
- `TV series.` when needed only to preserve a user-specified distinction

## 5) Notes discipline

Keep notes only when they add catalog value:
- disambiguation
- scope
- franchise context
- adaptation/source context
- canonicalization decisions that would not be obvious later

Remove notes that merely restate:
- genre
- tone
- premise already covered by the summary
- obvious facts already represented in structured columns

Good:
- `Original Argentine film; not the 2015 remake.`
- `Part of the Die Hard film franchise.`

Bad:
- `Crime drama film.`
- `Dark thriller.`

## 6) Verification after normalization

After adding and normalizing titles:
- reload the seed into a real database
- confirm total row count
- confirm non-empty summaries when the field exists
- check representative normalized rows
- check duplicate title/year groups are zero unless intentionally preserved
