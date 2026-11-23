# Regex Argument-Capture for File-Write Detection

## The Core Problem

File-open pattern regexes that match literal string arguments fail when an attacker
wraps the path argument in nested function calls or extra parentheses. Each extra
level of nesting is a bypass if the pattern uses a fixed-depth nested-paren macro.
Arms-racing depth one wave at a time (1→2→3→4 levels) wastes audit rounds on
predictable bypasses and never terminates — there is always one more wrap.

## Correct Solution: Four-Part Design

Three separate concerns for positional/keyword arms, plus one for `**`-unpack arms:

**Post-paren absorber** — use `[ \t\n]?` immediately after `\(`:
- Absorbs a single whitespace character (space, tab, or newline) that PEP8/Black formatters
  insert when wrapping a long call to the next line: `gzip.GzipFile(\n'path','wb')`
- Applies to all constructor patterns: gzip, zipfile, tarfile, bz2/lzma, dbm, io.FileIO, io.open
- `open()` already had this absorber from earlier waves; add it explicitly to every other family
- `[ \t\n]?` absorbs exactly ONE whitespace character; two or more newlines after `(` is a documented miss

**Path argument** — use `[^\n]*` (no cap, newline-terminated):
- Depth-unlimited: matches any expression on one line regardless of nesting depth
- O(n) scan: `[^\n]` is a simple char class, terminates at first newline, no exponential backtracking
- No cap bypass: the regex tries all start positions, so even a 5000-char first arg yields a match if mode follows

**Comma-to-mode gap** — use `,[\s\S]{0,20}` between the last argument and the mode string:
- Handles `,'\n...mode'` (newline after comma, black-style)
- `{0,20}` cap: 20 newlines/chars covers any realistic formatter; 21+ is a documented miss
- Only applied to the separator, not the path — keeps path matching fast and bypass-free

**mode-first kwargs** — add a parallel `mode=` (or `flag=` for dbm) pattern branch:
- Positional patterns fail when the caller passes mode as the FIRST keyword arg:
  `gzip.GzipFile(mode='wb', filename='plugins/evil.py')`
- Add a sibling pattern for each family that anchors on `mode=` / `flag=`, using
  `[ \t\n]?[^\n]*mode\s*=[\s\S]{0,20}` so the absorber + comma-gap apply here too
- Families needing mode= alts: gzip, bz2/lzma, tarfile (`mode=`), dbm (`flag=`)
- zipfile already had mode= alt; open()/io.FileIO already had mode= alt from earlier waves
- io.FileIO mode= pattern also needs the `[ \t\n]?` absorber — it is easy to add the
  positional absorber but forget the mode= branch; apply them together

**dict-literal `**` unpack — Wave 53 final form (supersedes Wave 49/50/51/52):**

Do NOT enumerate wrapping forms (`{...}`, `({...})`, `dict({...})`, `dict(dict({...}))`) as
alternation branches — every new wrapper depth adds another bypass wave. Use a single
unified arm with a comment-aware multiline traversal on both sides of `**` and a bounded
gap absorber between the mode key colon and its value.

Evolution of bypasses and fixes:
- **Wave 49** (`[^)]*\*\*[^)]*`): stopped at first `)` of any inner call.
- **Wave 50** (`[^)]*(?:\([^)]*\)[^)]*)*`): allowed one level of inner `()`, but two nested
  calls (e.g., `dict(list())`) still bypassed. Also missed: paren-wrapped key/value, r+ modes.
- **Wave 51** (`[^\n]{0,300}`): Same-line scan eliminated paren-depth issues.
  Added `\)?` for paren key, `\(?` for paren value, dedicated r+ arm.
  **Bypassed by**: (a) multiline dict (mode on line 2+); (b) `# comment\n    'wb'` after
  colon — `[^\n]` stops before value on next line; (c) 300+ char padding.
- **Wave 52** (`[\s\S]{0,500}` pre+post + `(?:[ \t]*#[^\n]*)?` comment-gap): Fixed multiline
  and 300-char padding. **Bypassed by**: (a) two consecutive `#` lines after colon — only one
  comment-gap group; (b) backslash continuation `\\\n` between colon and value; (c) `#` between
  key and colon; (d) double-paren value `(('wb'))`; (e) double-paren key `(('mode'))`;
  (f) false positive — `[\s\S]{0,500}` pre-** scanned through `# 'mode':'w'` comment lines
  and picked up commented-out mode keys, causing false-positive BLOCK on read-only calls.
- **Wave 53** (CMT `(?:[^\n]|\n(?![ \t]*#)){0,2000}` + GAP `[\s\S]{0,80}`): CURRENT FINAL FORM.
  CMT stops at comment lines (any indentation) — fixes the false-positive. 2000-char cap
  covers any realistic padding on a single line or blank-line continuation. GAP absorbs
  arbitrary junk (multiple `#` lines, `\\\n`, extra parens) between colon and value, up to
  80 chars. Paren key handled by `\)*` (zero or more closes). All W52 findings now BLOCK.

**Wave 56 canonical form — positional and keyword-mode arms only (supersedes Wave 55; **-unpack arms superseded by Wave 57 AST checker):**

Wave 56 makes two targeted fixes over Wave 55 and retains everything else:

1. **CMT reverted to `[\s\S]{0,2000}` (simple, both sides of `**`)** — Wave 55's comment-aware CMT `(?:[^\n#]|#[^\n]*\n|\n){0,2000}` had a hidden stall: the `[^\n#]` alternative rejects `#`, and `#[^\n]*\n` requires a trailing newline. When a `#` appeared INSIDE a quoted string value on a line that continued (no newline immediately after `#`), CMT would stall mid-line and fail to reach the mode key. Example: `{'encoding': 'utf-8#', 'mode': 'w'}` — CMT stops before `'mode'` because neither alt matches `#` without a following newline. Fix: revert to `[\s\S]{0,2000}` which matches every character, never stalls, and always reaches the mode key.
   Trade-off: ADV-004 FP (** inside a code comment causes false-positive BLOCK on following read-mode unpack) and ADV-006 FP (commented `'mode':'w'` before real `'mode':'r'` causes false-positive BLOCK) both return. Both are safe-side over-blocking, not security bypasses. Documented as intentional.

2. **KEY_JUNK uses truly disjoint alternatives, cap raised to {0,60}** — Wave 55's KEY_JUNK `(?:[ \t]*#[^\n]*\n|[ \t]*\\[ \t]*\n|[ \t\r\n]|\))*` had overlapping prefixes: `[ \t]*#[^\n]*\n` and `[ \t\r\n]` both start with a space or tab. For input ` #\n` (space + hash + newline), the engine tries the space/tab alternative first, consumes only the space, then cannot complete the `#` alternative and backtracks. With 40 such tokens and no `[=:]` after them, this causes exponential backtracking (>1.5 s on 40 repetitions, timeout on 50).
   Fix: remove the `[ \t]*` prefix from the comment alternative, making it start with `#`. All five alternatives now have disjoint first characters:
   - `#[^\n]*\n` (starts with `#`)
   - `[ \t]*\\[ \t]*\n` (starts with space/tab or backslash; `\\` is always followed by `\n` so no overlap with comment)
   - `[ \t]` (single space/tab)
   - `\n` (bare newline)
   - `)` (closing paren)
   No two alternatives share a common prefix, eliminating backtrack ambiguity. Cap raised from {0,30} (Wave 55) to {0,60} for more nesting headroom.

3. **PFX `[fFrRbBuU]{0,2}` retained** — unchanged from Wave 55; absorbs r/u/f/b string prefixes before value quote.

4. **GAP `(?:[ \t\r\n\\()]|#[^\n]*){0,80}` retained** — unchanged from Wave 54/55.

Documented intentional FPs (over-blocking, safe-side, NOT security bypasses):
- ADV-004: `**` token inside a Python `#` comment causes `[\s\S]` CMT to latch on it, FP BLOCKing the following real read-mode unpack on the same source span.
- ADV-006: `# 'mode':'w'\n    'mode':'r'` — commented write-mode key before real read-only key causes FP BLOCK.

Documented miss (stable across all waves — not a real security bypass):
- `open(**{'file': '''plugins/evil.py\n#''', 'mode': 'w'})` — triple-quoted filename containing a LITERAL newline. The `**` arm's scan still reaches `'mode':'w'` via `[\s\S]`; mode-first dicts BLOCK. Low/informational only.
- Content >2000 chars before mode key — CMT `{0,2000}` cap terminates; ALLOW (documented).

    # CMT: simple [\s\S] — matches everything, never stalls on '#' in string values
    # KEY_JUNK: disjoint alternatives, capped — no ReDoS from prefix overlap
    # PFX: string prefix absorber before every value quote
    # GAP: no quotes, no letters — absorbs ws/bs/paren/comment-to-EOL only

    CMT      = r"[\s\S]{0,2000}"                                              # simple; both sides
    GAP      = r"(?:[ \t\r\n\\()]|#[^\n]*){0,80}"                           # no quotes/letters
    PFX      = r"[fFrRbBuU]{0,2}"                                             # r/u/f/b prefix
    KEY_JUNK = r"(?:#[^\n]*\n|[ \t]*\\[ \t]*\n|[ \t]|\n|\)){0,60}"         # disjoint, capped

    def make_suffix(val_chars, include_rplus=True):
        key = (r"[\x27\x22]+mode[\x27\x22]+" + KEY_JUNK + r"[=:]" + GAP + PFX)
        val = r"[\x27\x22]+" + val_chars
        rp  = PFX + r"[\x27\x22]+r[bt]*\+[bt]*[\x27\x22]"
        kw  = r"mode\s*=\s*" + GAP + PFX
        if include_rplus:
            return r"(?:" + key + val + r"|" + key + rp + r"|" + kw + rp + r"|" + kw + val + r")"
        return r"(?:" + key + val + r"|" + kw + val + r")"

    def make_fd_suffix():
        key = (r"[\x27\x22]+(?:flag|mode)[\x27\x22]+" + KEY_JUNK + r"[=:]" + GAP + PFX)
        val = r"[\x27\x22]+[ncw]"
        kw  = r"(?:flag|mode)\s*=\s*" + GAP + PFX
        return r"(?:" + key + val + r"|" + kw + val + r")"

    # Pattern for each family = namespace + CMT + r"\*\*" + CMT + suffix

    # gzip, bz2/lzma, tarfile, zipfile (charset [wax] or [wxa]):
    r"gzip\s*\.\s*(?:open|GzipFile)\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wax]")
    r"(?:bz2\s*\.\s*BZ2File|lzma\s*\.\s*LZMAFile)\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wxa]")
    r"tarfile\s*\.\s*(?:open|TarFile|TarFile\s*\.\s*open)\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wxa]")
    r"zipfile\s*\.\s*(?:ZipFile|PyZipFile|Path)\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wxa]")

    # dbm.open / dbm.gnu (flag or mode key; r=read excluded; charset [ncw]; no r+ arm):
    r"dbm\s*\.\s*open\s*\(" + CMT + r"\*\*" + CMT + make_fd_suffix()
    r"dbm\s*\.\s*(?:gnu|dumb|ndbm|sqlite3)\s*\.\s*open\s*\(" + CMT + r"\*\*" + CMT + make_fd_suffix()

    # io.FileIO, io.open, open() (charset [wax+] or [awx]; include r+ arm):
    r"io\.FileIO\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wax+]")
    r"io\.open\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[awx]")
    r"\bopen\s*\(" + CMT + r"\*\*" + CMT + make_suffix("[wax+]")

Corollary: **never enumerate paren/dict-wrap depths as alternation branches, never use
`[^)]*` with inner-paren absorbers, and never use `[^\n]{0,N}` for the `**`-unpack scan.**
All three approaches arms-race with no convergence. For `**`-unpack specifically, use the AST checker (`_ast_has_starstar_write`) instead of any regex arm — the AST approach terminates the arms race entirely by delegating to Python's own parser. Where CMT + KEY_JUNK + GAP + PFX regex arms are still used (positional/kw-mode):
CMT (`[\s\S]{0,2000}`) traverses any content on both sides of `**` without stalling;
GAP (no-quote charset) absorbs junk between colon and value without skipping dict value literals;
KEY_JUNK (disjoint alternatives, capped) handles any depth of comment/paren/backslash before `[=:]`;
PFX absorbs r/u/f/b string prefixes before the value quote;
paren depth is irrelevant; all caps prevent ReDoS.

**AST checker canonical architecture (Waves 57–61 — current final design; do not revert to regex for ** detection):**

Four helpers compose `_ast_has_starstar_write(code: str) -> bool`:

- `_get_const_str(node)` — returns `str` if node is `ast.Constant(str)`, or **recurses via `while isinstance(node, ast.NamedExpr): node = node.value`** before the `isinstance(node, ast.Constant)` check. This handles any depth of walrus wrapping: `(m := 'w')` → `'w'`, `(a := (b := 'w'))` → `'w'`. Returns `None` for `Call`, `JoinedStr` (f-string), `BinOp`, `IfExp` — accepted misses.
- `_extract_kv_from_dict(d)` — builds `{str: str}` from `ast.Dict`, **recursing into `**inner` when `inner` is reachable via `_unwrap_to_dict(v)`** — catches `open(**{**{'mode':'w'}, ...})`, walrus-wrapped spreads, and BitOr/BoolOp-wrapped spreads. Skips `**variable` (non-Dict after unwrapping).
- `_resolve_func_name(func)` — returns `(func_name, is_dbm, is_opaque)`:
  - `ast.Name` → `(id, False, False)`
  - `ast.Attribute` with `attr == '__call__'` → walk chain; **if terminus is non-Name (Attribute, Call, Subscript) → `is_opaque=True`** (catches `open.__class__.__call__`, `type(open).__call__`)
  - `ast.Attribute` with `attr != '__call__'` → `(attr, is_dbm, False)` with dbm-chain detection
  - `ast.Call` / `ast.Subscript` / anything else → `is_opaque=True` (catches `getattr(open,'__call__')(**{...})`)
- `_dict_has_write_mode(kv)` — checks `'mode'`/`'flag'` key against `{'w','a','x','n','c','r+'}` prefixes.

In the walker: for each `ast.Call` with `**kwargs` where `kw.arg is None`, **call `_unwrap_to_dict(kw.value)`** which: (1) peels any NamedExpr layers with a while-loop, (2) returns the `ast.Dict` directly, or (3) recursively resolves `BinOp(BitOr)`, `BoolOp`, `IfExp`, and constant-indexed `Subscript` wrappers into a synthetic merged `ast.Dict`. Only then check `isinstance(kw_val, ast.Dict)`. This catches `open(**(d := {'mode':'w',...}))`, double-nested walrus, `open(**({} | {'mode':'w',...}))`, `open(**(x or {'mode':'w',...}))`, `open(**({'mode':'w',...} if c else {}))`, and `open(**[{'mode':'w',...}][0])`. Continue (skip) if still not `ast.Dict` after unwrapping.
- `is_opaque=True` → `_dict_has_write_mode` catch-all
- `is_dbm=True` → check `flag`/`mode` against DBM write set
- `func_name in _AST_WRITE_FUNCS` → check `mode` key
- `func_name in ('type','__call__','callable')` → meta-caller catch-all via `_dict_has_write_mode`
- unknown named func → no catch-all (FP risk)

Fallback: `_STARSTAR_REGEX_FALLBACK` fires on `ast.SyntaxError` (partial/truncated snippet).

**Accepted static misses (all unfixable without runtime inspection — do not add new regex arms for these):**
- `**variable` — `kw.value` is `ast.Name` after unwrapping; not `ast.Dict`
- `chr(119)` / `'w'[0]` / `f'w'` / `b'w'` as mode value — `Call`/`Subscript`/`JoinedStr`/`Constant(bytes)`
- `'mo'+'de'` key concat — `BinOp`
- `unknown_func(**{'mode':'w',...})` — no catch-all for unknown names
- `(lambda: 'w')()` as mode — `ast.Call`, not `Constant`
- `'mode' if cond else 'file'` IfExp key — `_get_const_str` returns `None` for `IfExp`; that kv pair is skipped

Blocked as of Wave 60 (was a documented miss in W57–59):
- `open(**(d := {'mode':'w',...}))` — walrus-wrapped `**` operand; walker now unwraps `NamedExpr` on `kw.value` before `isinstance(kw.value, ast.Dict)` check
- `open(**(a := (b := {'mode':'w',...})))` — double-nested walrus; while-loop unwinds all levels

**Bypass class → wave that caught it (historical record; each is now blocked):**
- CR/CRLF/FF in key position → Wave 57 (AST normalises)
- 61+ spaces between key and colon → Wave 57 (AST has no cap)
- `#` inside quoted string value stalling CMT → Wave 56 (unified CMT)
- `open(**{**{'mode':'w'},...})` nested spread → Wave 58 (`_extract_kv_from_dict` recursion)
- `open.__call__.__call__(**{...})` / paren-wrapped `__call__` → Wave 58 (`__call__` chain walk)
- `open(**{'mode':(m:='w'),...})` walrus mode value → Wave 59 (`_get_const_str` unwraps `NamedExpr`)
- `open.__class__.__call__(open,**{...})` / `type.__call__(FileIO,**{...})` → Wave 59 (non-Name terminus opaque; meta-caller set)
- `open(**(d := {'mode':'w',...}))` walrus-wrapped `**` operand → Wave 60 (`_ast_has_starstar_write` and `_extract_kv_from_dict` unwrap `NamedExpr` on `kw.value` via while-loop before `isinstance(kw.value, ast.Dict)` check)
- `open(**({} | {'mode':(m:='w'),...}))` / `open(**(x or {'mode':'w',...}))` / IfExp / `[{...}][0]` wrappers with walrus-valued mode → Wave 61 (`_unwrap_to_dict` helper peels BinOp(BitOr), BoolOp, IfExp, Subscript[int] — see below)
- 1000-call timing regression on walrus blobs (8000ms) → Wave 61 (`_ast_starstar_hit` short-circuits before `_RENAME_PRIMITIVES`)

**GAP charset must exclude quote characters.** `[\s\S]{0,80}` as GAP can match quote chars and span
across a dict value literal — e.g., skipping `'r', 'file': ` to latch onto `'agent/foo.py'` matching
`[wax+]` via `a`. Use `(?:[ \t\r\n\\()]|#[^\n]*){0,80}` instead: absorbs ws/bs/paren/comment-to-EOL
only. Prevents false positives on read-mode calls with multi-key dicts.

**CMT must use `[\s\S]{0,2000}`, NOT a comment-aware alternation.** A pattern like `(?:[^\n#]|#[^\n]*\n|\n){0,2000}` stalls when `#` appears inside a quoted string value on a line that does not end with a newline immediately after `#`. Neither `[^\n#]` (rejects `#`) nor `#[^\n]*\n` (requires trailing newline) can advance past `#` in `'utf-8#'` when more content follows on the same line. CMT stops mid-line and fails to reach the mode key. Use `[\s\S]{0,2000}` — it matches every character, never stalls, and always reaches the mode key regardless of `#` placement in string values. Accept that ADV-004/ADV-006 FPs (over-blocking commented writes) return — these are safe-side.

**KEY_JUNK alternatives must be truly disjoint: no two may share a common first character.** `(?:[ \t]*#[^\n]*\n|[ \t\r\n]|\))*` is ReDoS-vulnerable: `[ \t]*#[^\n]*\n` and `[ \t\r\n]` both start with a space or tab. For input ` #\n` (space + hash + newline), the engine tries consuming just the space with the second alt, fails to match `#` next, and backtracks; with 40+ such tokens and no `[=:]` after them, this causes exponential backtracking. Fix: remove the `[ \t]*` prefix from the comment alt so it starts with `#` — then space/tab always picks `[ \t]` (single char) and hash always picks `#[^\n]*\n`. Combine with a hard cap (e.g., `{0,60}`) to bound worst-case work.

**Do NOT split CMT into CMT_PRE / CMT_POST — use a single unified CMT on both sides.** The Wave 54 split (`[\s\S]{0,2000}` pre + `(?:[^\n]|\n(?![ \t]*#)){0,2000}` post) had two residual bugs: (a) CMT_POST stopped at a real comment line BETWEEN `**` and the mode key, causing a false ALLOW when the mode key appeared after a code comment; (b) CMT_PRE latched `**` inside a comment line, causing a false BLOCK of a following read-mode unpack. The correct unified form `(?:[^\n#]|#[^\n]*\n|\n){0,2000}` consumes comment lines as indivisible `#[^\n]*\n` units on BOTH sides, solving both problems simultaneously.

**KEY_JUNK before `[=:]` must be a repeating class, not one-shot comment absorbers.** Pattern `(?:[ \t]*#[^\n]*)?\s*\)*(?:[ \t]*#[^\n]*)?\s*` (Wave 54) absorbs at most one comment before `)*` and one after. Two comment lines before `)*`, or a backslash continuation before `:`, both bypass it. Use `(?:[ \t]*#[^\n]*|[ \t]*\\[ \t]*\n|\s|\))*` (Wave 55) — a repeating alternation that absorbs any combination and any number of comments, backslash-newline continuations, whitespace, and closing parens.

**Add PFX absorber `[fFrRbBuU]{0,2}` between GAP and the opening quote on ALL value arms.** Without it, `r'w'`, `u'w'`, `f'w'`, `R'wb'`, `fr'w'`, `r'r+'` all bypass detection because GAP (which excludes letter chars) cannot consume the prefix letter before the quote. Insert PFX immediately before `[\x27\x22]+` on the key_arm value, kw_arm value, AND r+arm. Do NOT put PFX inside GAP — that would reintroduce the W53-ADV-003 overconsume false positive (GAP spanning dict value literals).

    # Positional and mode-first kwarg arms are unchanged:
    r"open\s*\([ \t\n]?[^\n]*,[\s\S]{0,20}[\x27\x22][^\x27\x22]*[wax+]"
    r"io\.FileIO\s*\([ \t\n]?[^\n]*,[\s\S]{0,20}[\x27\x22][^\x27\x22]*[wax+]"
    r"io\.FileIO\s*\([ \t\n]?[^\n]*\bmode\s*=[\s\S]{0,20}(?:[^\n]*[wax+]|chr\s*\()"
    r"dbm\s*\.\s*open\s*\([ \t\n]?[^\n]*,[\s\S]{0,20}[\x27\x22][ncw]"
    r"dbm\s*\.\s*open\s*\([ \t\n]?[^\n]*flag\s*=[\s\S]{0,20}[\x27\x22][ncw]"
    r"gzip\s*\.\s*(?:open|GzipFile)\s*\([ \t\n]?[^\n]*,[\s\S]{0,20}[\x27\x22][wax]b?t?[\x27\x22]"
    r"gzip\s*\.\s*(?:open|GzipFile)\s*\([ \t\n]?[^\n]*mode\s*=[\s\S]{0,20}[\x27\x22][wax]b?t?[\x27\x22]"

Apply the full four-part design to all patterns: `gzip.GzipFile/open`, `tarfile.TarFile/open/TarFile.open`,
`bz2.BZ2File`, `lzma.LZMAFile`, `zipfile.ZipFile/PyZipFile`, `dbm.open/gnu/dumb/ndbm/sqlite3`,
`io.FileIO`, `io.open`, and all `open()` variants.

## Newline Handling: Path vs Comma Gap vs Post-Paren

`[^\n]*` misses embedded newlines in argument expressions — three distinct cases:

    gzip.GzipFile(\n'plugins/evil.py','wb') # ONE newline IMMEDIATELY AFTER (
                                            # BLOCK with [ \t\n]? absorber

    gzip.GzipFile(\n\n'plugins/evil.py','wb')# TWO newlines after (
                                            # ALLOW — documented miss (absorber cap=1)

    gzip.GzipFile('plugins/evil.py',       # newline AFTER COMMA (black-style)
        'wb')                              # BLOCK with ,[\s\S]{0,20} on comma gap

    open('plugins/evil.py',               # newline BEFORE mode= keyword
        mode='w')                          # BLOCK with mode\s*=[\s\S]{0,20} on kw gap

    gzip.GzipFile((os.path.join(           # newline INSIDE PATH expression
        'plugins','evil.py')),'wb')         # ALLOW — documented miss (newline in join arg)

Fix the post-paren case with `[ \t\n]?` absorber; fix the comma gap with `,[\s\S]{0,20}`;
accept 2+ newlines after `(` and newlines inside path expressions as documented misses.

**Do not** extend `[\s\S]{0,N}` to the path arg itself — see below.

## Why NOT Nested-Paren Macros

The old 2-level and 3-level macros:

    # 2-level (DEPRECATED — bypassed by 3-level wrapping)
    (?:[^()]|\((?:[^()]|\([^)]*\))*\))*

    # 3-level (DEPRECATED — bypassed by 4-level wrapping)
    (?:[^()]|\((?:[^()]|\((?:[^()]|\([^)]*\))*\))*\))*

These have two fatal flaws:
1. Each fixed depth is bypassed by adding one more paren wrap — the arms race never ends.
2. The nested alternation `(?:[^()]|\(...)*)` exhibits exponential backtracking on
   unmatched-paren inputs > ~5000 chars. Measured: >10s on `'a'*5000` payloads.

Do not re-introduce these macros.

## Why NOT `[^\n]{0,300}` as the `**`-unpack scan (Wave 51 pitfall)

The same-line scan `[^\n]{0,300}` (Wave 51) is still bypassed in three ways:

1. **Multiline dict** — Python allows `gzip.GzipFile(**{\n    'mode':'wb',\n    ...\n})`;
   the newline between `{` and `'mode'` causes `[^\n]` to stop before the key. Any
   Black-formatted multi-line dict literal is a bypass.
2. **Comment after colon** — `{'mode': # comment\n    'wb'}` — the pattern sees `mode':`
   then the comment text, then a newline, and `[^\n]` terminates before `'wb'` on line 2.
3. **Cap bypass** — `{0,300}` allows exactly 300 chars between `**` and mode. A filename
   value padded to 301+ chars before `'mode'` pushes the key past the cap.

The fix for all three is `[\s\S]{0,500}` (multiline, 500-char cap) plus a comment-gap absorber
`(?:[ \t]*#[^\n]*)?` between the key's `[=:]` and the value. `[\s\S]{0,500}` is safe because
the cap is hard: the engine tries at most 500×500 = 250k char pairs per anchor position,
not unbounded exponential backtracking. Measured: <100ms on 50k-char no-match payloads
across all 9 families.

**Do not** use `[^\n]{0,N}` for `**`-unpack scans when N < 500 — any cap N is a padding bypass.
Use `[\s\S]{0,500}` or raise the cap past practical filename/expression lengths.

**Do not** use the same `[\s\S]{0,500}` for PATH argument capture — reserve it for the `**`-unpack
pre/post scan only. For path args use `[ \t\n]?[^\n]*` (absorber + newline-terminated, no cap).

## ReDoS Safety

`[ \t\n]?[^\n]*` terminates at the first newline — no multi-line backtracking. For a
50k-char single-line input with no mode match, the engine scans once and gives up.
Measured: ~20–30 ms on the full combined `_RENAME_PRIMITIVES` pattern at 50k chars.

`[\s\S]{0,2000}` (Wave 56 CMT, both sides): each position tries at most 2000 chars; the engine scans linearly forward — no alternation backtracking. Cap is the sole bound. Measured: <60ms on 50k-char no-match payloads (same-line, multiline, comment-dense) across all 9 families.

`(?:#[^\n]*\n|[ \t]*\\[ \t]*\n|[ \t]|\n|\)){0,60}` (Wave 56 KEY_JUNK, disjoint): all five alternatives start with distinct first characters (`#`, space/tab-then-backslash, space/tab, newline, `)`). No shared prefix — the engine makes exactly one choice per step with no backtracking. Cap `{0,60}` bounds worst-case steps to 60 per anchor position. Measured: 40-repetition no-colon probe completes in <1ms (was >1.5s with overlapping W55 alts).

`(?:[ \t\r\n\\()]|#[^\n]*){0,80}` (Wave 54/55 GAP unchanged): 80-char hard cap, charset excludes quotes and letters. No combinatorial explosion. No-quote restriction prevents spanning across dict value literals — prevents the greedily-skipping-to-next-write-value false positive (W53-ADV-003). Measured: negligible contribution to overall latency.

`[\s\S]{0,20}` on the comma gap is safe because the cap is tiny (20 chars) and applies
only to the short separator region, not the full argument.

`(?:[ \t]*#[^\n]*)?` key-comment absorber: `[^\n]*` is O(n) and the whole group is optional
(zero or one occurrence), so no combinatorial explosion.

Test recipe:

    import time, re

    # Test 1: positional O(n) on long same-line input
    p = re.compile(r"gzip\s*\.\s*(?:open|GzipFile)\s*\([ \t\n]?[^\n]*,[\s\S]{0,20}[\x27\x22][wax]b?t?[\x27\x22]")
    t0 = time.monotonic()
    for _ in range(20): p.search("gzip.GzipFile(" + "a"*50000 + ")")
    print(f"{(time.monotonic()-t0)/20*1000:.1f}ms avg")  # expect < 50 ms

    # Test 2: newlines stop [^\n]* quickly after absorber
    for _ in range(20): p.search("gzip.GzipFile(" + "\n"*2000 + ")")
    print(f"{(time.monotonic()-t0)/20*1000:.1f}ms avg")  # expect < 10 ms

    # Test 3: 20-newline comma gap catches cross-line mode
    assert p.search("gzip.GzipFile('plugins/x.py'," + "\n"*20 + "'wb')")
    assert not p.search("gzip.GzipFile('plugins/x.py'," + "\n"*21 + "'wb')")

    # Test 4: single newline-after-( is now blocked
    assert p.search("gzip.GzipFile(\n'plugins/x.py','wb')")
    assert not p.search("gzip.GzipFile(\n\n'plugins/x.py','wb')")  # 2 newlines = miss

    # Test 5: mode-first kwarg branch (absorber + \s\S gap)
    pm = re.compile(r"gzip\s*\.\s*(?:open|GzipFile)\s*\([ \t\n]?[^\n]*mode\s*=[\s\S]{0,20}[\x27\x22][wax]b?t?[\x27\x22]")
    assert pm.search("gzip.GzipFile(mode='wb',filename='plugins/x.py')")
    assert pm.search("gzip.GzipFile(\nmode='wb',filename='plugins/x.py')")  # absorber

    # Test 6: **-unpack Wave 52 form ([\s\S]{0,500} multiline + comment-gap)
    CMT = r"(?:[ \t]*#[^\n]*)?\s*"
    KEY = r"[\x27\x22]+mode[\x27\x22]+\)?\s*[=:]"
    VAL = CMT + r"\(?\s*[bBfFrRuU]{0,2}[\x27\x22]+[wax]"
    VRP = CMT + r"\(?\s*[\x27\x22]+r[bt]*\+[bt]*[\x27\x22]"
    KW  = r"mode\s*=\s*" + CMT + r"\(?\s*[bBfFrRuU]{0,2}[\x27\x22]+[wax]"
    KWR = r"mode\s*=\s*" + CMT + r"\(?\s*[\x27\x22]+r[bt]*\+[bt]*[\x27\x22]"
    pu = re.compile(
        r"gzip\s*\.\s*(?:open|GzipFile)\s*\([\s\S]{0,500}\*\*[\s\S]{0,500}(?:"
        + KEY + VAL + r"|" + KEY + VRP + r"|" + KWR + r"|" + KW + r")"
    )
    # All wrapping forms blocked:
    assert pu.search("gzip.GzipFile(**{'mode':'wb','filename':'plugins/x.py'})")  # bare dict
    assert pu.search("gzip.GzipFile(**dict(mode='wb',filename='plugins/x.py'))")  # dict() kw form
    assert pu.search("gzip.GzipFile(**({'mode':'wb','filename':'plugins/x.py'}))")  # paren-wrap
    assert pu.search("gzip.GzipFile(**(dict({'mode':'wb','filename':'plugins/x.py'})))")  # dict({}) wrap
    assert pu.search("gzip.GzipFile(**(dict(dict({'mode':'wb','filename':'plugins/x.py'}))))")  # double dict wrap
    assert pu.search("gzip.GzipFile(**(list() or {'mode':'wb','filename':'plugins/x.py'}))")  # list() bypass
    assert pu.search("gzip.GzipFile(**((None) or {'mode':'wb','filename':'plugins/x.py'}))")  # (None) bypass
    assert pu.search("gzip.GzipFile(**(dict(list()) or {'mode':'wb','filename':'plugins/x.py'}))")  # two-level inner
    assert pu.search("gzip.GzipFile(**{'''mode''':'wb','filename':'plugins/x.py'})")  # triple-quote key
    assert pu.search("gzip.GzipFile(**{'mode':r'wb','filename':'plugins/x.py'})")  # r-prefix value
    assert pu.search("gzip.GzipFile(**{('mode'):'wb','filename':'plugins/x.py'})")  # paren-wrapped key
    assert pu.search("gzip.GzipFile(**{'mode':('wb'),'filename':'plugins/x.py'})")  # paren-wrapped value
    assert pu.search("gzip.GzipFile(**{'mode':'r+b','filename':'plugins/x.py'})")   # r+ read-write
    assert pu.search("gzip.GzipFile(**{'mode':'rb+','filename':'plugins/x.py'})")   # rb+ read-write
    # Wave 52 new blocks:
    assert pu.search("gzip.GzipFile(**{\n    'mode':'wb','filename':'plugins/x.py'\n})")  # multiline dict
    assert pu.search("gzip.GzipFile(**{' '*300 + \"'mode':'wb'\"})"[:-1] + "}")  # 300-char padding
    assert pu.search("gzip.GzipFile(**{'mode': # comment\n    'wb','filename':'plugins/x.py'})")  # comment after :
    # Still allow:
    assert not pu.search("gzip.GzipFile(**{'mode':'rb','filename':'plugins/x.py'})")  # read-only
    assert not pu.search("d=kw; gzip.GzipFile(**d)")  # variable-bound
    # ReDoS: [\s\S]{0,500} multiline 50k no-match <200ms:
    t0 = time.monotonic()
    for _ in range(10): pu.search("gzip.GzipFile(**{" + "a"*50000 + "})")
    assert (time.monotonic()-t0)/10*1000 < 200, "ReDoS regression on 50k no-match"
    for _ in range(10): pu.search("gzip.GzipFile(**{\n" + "a"*50000 + "})")
    assert (time.monotonic()-t0)/10*1000 < 200, "ReDoS regression on 50k newline-heavy"

## Wave 58: AST-Based **-Unpack Detection Refinements (Current Final Design)

### Wave 58 additions over Wave 57

Two new findings from the Wave 57 cold audit required targeted fixes to the AST checker:

**ADV-001 — Spread sub-dict not recursed**: `open(**{**{'mode': 'w'}, 'file': 'plugins/evil.py'})` was ALLOW because, when a dict literal contains a `**inner` spread (key=None in `ast.Dict`), the original code skipped it with `continue`. The inner `{'mode': 'w'}` is never inspected. Fix: recurse into any `None`-keyed value that is itself an `ast.Dict`, accumulating its key/value pairs alongside the outer dict's direct pairs.

    def _extract_kv_from_dict(d: ast.Dict) -> dict[str, str]:
        kv = {}
        for k, v in zip(d.keys, d.values):
            if k is None:
                if isinstance(v, ast.Dict):   # **inner_dict — recurse
                    kv.update(_extract_kv_from_dict(v))
                continue                       # **variable — skip (documented miss)
            k_s = _get_const_str(k)
            v_s = _get_const_str(v)
            if k_s and v_s:
                kv[k_s] = v_s
        return kv

**ADV-002 — `__call__` chains and opaque callees not resolved**: Patterns like `(open.__call__)(**{'mode':'w',...})`, `open.__call__.__call__(**{...})`, and `getattr(open,'__call__')(**{...})` were ALLOW because:
- `(open.__call__)` → `func` is `ast.Attribute(value=Name('open'), attr='__call__')` → `func_name='__call__'` → not in `_AST_WRITE_FUNCS` → skipped
- `open.__call__.__call__` → nested Attribute chain → same
- `getattr(open,'__call__')` → `func` is `ast.Call` → `func_name=None` → old code did `continue`

Fix: `_resolve_func_name(func)` helper that (a) walks `__call__` attribute chains to find the base callable name, (b) marks `Call`/`Subscript`/`IfExp` base nodes as `is_opaque=True`, and (c) applies a catch-all `_dict_has_write_mode()` check for opaque callees.

    def _resolve_func_name(func):
        # Returns (func_name, is_dbm, is_opaque)
        if isinstance(func, ast.Name):
            return func.id, False, False
        if isinstance(func, ast.Attribute):
            if func.attr == '__call__':
                val = func.value
                while isinstance(val, ast.Attribute) and val.attr == '__call__':
                    val = val.value
                if isinstance(val, ast.Name):
                    return val.id, False, False
                if isinstance(val, ast.Attribute):
                    return _resolve_func_name(val)  # re-resolve inner attr
                return None, False, True            # opaque base
            # Normal attr: detect dbm chain
            attr = func.attr
            if attr == 'open':
                val, chain = func.value, []
                while isinstance(val, ast.Attribute):
                    chain.append(val.attr); val = val.value
                if isinstance(val, ast.Name): chain.append(val.id)
                chain.reverse()
                if chain and chain[0] == 'dbm':
                    return attr, True, False
            return attr, False, False
        return None, False, True  # Call / Subscript / IfExp — opaque

    # In the main loop:
    func_name, is_dbm, is_opaque = _resolve_func_name(node.func)
    if is_opaque:
        if _dict_has_write_mode(kv):   # catch-all: any write-mode dict from unknown callee
            return True
        continue
    # ... existing is_dbm / func_name checks ...

**Opaque catch-all scoping**: the catch-all fires for ANY callee that cannot be statically resolved (`Call`, `Subscript`, `IfExp` as base). This catches `getattr(open,'__call__')(**{...})`, `[open.__call__][0](**{...})`, `type(open).__call__(**{...})`, etc. It does NOT fire for unknown plain names (`some_func(**{'mode':'w'})`) — those go through the `func_name in _AST_WRITE_FUNCS` check and fall through silently, avoiding FPs on legitimate unknown callables.

**`_dict_has_write_mode` helper**: centralises the mode/flag write-mode check.

    _AST_ALL_WRITE_STARTS = frozenset({'w', 'a', 'x', 'n', 'c', 'r+'})

    def _dict_has_write_mode(kv: dict[str, str]) -> bool:
        for key in ('mode', 'flag'):
            v = kv.get(key)
            if v and any(v.startswith(m) for m in _AST_ALL_WRITE_STARTS):
                return True
        return False

### Wave 58 additional documented misses

- `open(**{**d, 'mode': 'w'})` — spread of a variable `d` is skipped (not `ast.Dict`), but `'mode':'w'` as a direct key is still caught. Net: BLOCK.
- `open.__class__.__call__(**{'mode':'w',...})` — `__call__` walk reaches `Attribute('open','__class__')`, re-resolves to `func_name='__class__'`, not in `_AST_WRITE_FUNCS`, no catch-all for named funcs. ALLOW (exotic indirection, no practical security impact).
- `open(**{**{**{'mode':'w'}}, 'file':'...'})` — triple spread. `_extract_kv_from_dict` recurses: outer None-key → inner `{**{'mode':'w'}}` (ast.Dict) → recurse again → innermost `{'mode':'w'}` → caught. BLOCK (recursion covers arbitrary nesting depth).

## AST Checker: NamedExpr (Walrus) Unwrapping Rules

**Use a while-loop, not an if-check, everywhere NamedExpr is unwrapped.** Walrus operators can be nested arbitrarily: `(a := (b := 'w'))`. An `if isinstance(node, ast.NamedExpr)` check unwraps exactly one level, leaving `(b := 'w')` (still a `NamedExpr`) to fail the `isinstance(node, ast.Constant)` check. Apply `while isinstance(node, ast.NamedExpr): node = node.value` in:
- `_get_const_str` — before the `isinstance(node, ast.Constant)` check
- `_ast_has_starstar_write` walker — on `kw.value` via `_unwrap_to_dict` (see below), which peels NamedExpr while-loop first
- `_extract_kv_from_dict` — on each spread (`None`-keyed) value via `_unwrap_to_dict`

**Unwrap NamedExpr on the `**` operand itself (kw.value level), not just inside dict keys/values.** The bypass `open(**(d := {'mode':'w',...}))` places the walrus at the keyword-argument level: `kw.value` is `ast.NamedExpr`, not `ast.Dict`. Unwrapping inside `_get_const_str` or `_extract_kv_from_dict` does not help — those are only called after `isinstance(kw.value, ast.Dict)` passes. The `kw.value` unwrap must happen FIRST in the main walker loop, before the `isinstance(kw.value, ast.Dict)` guard.

**When adding any new NamedExpr unwrap, immediately apply it recursively (while-loop) and add a PoC for double-nested walrus.** A single-level fix always leaves a gap. The test pattern is `open(**(a := (b := {'mode':'w','file':'plugins/evil.py'})))` — if it ALLOWs, the unwrap is not recursive.

## Wave 61: _unwrap_to_dict and Short-Circuit Timing Fix

### _unwrap_to_dict — generalised operand unwrapper

`BitOr/BoolOp/IfExp/Subscript` wrappers around dict literals (with walrus-valued mode) were ALLOW because after the `while NamedExpr` peel, `kw.value` was `BinOp(BitOr)` or `BoolOp` — not `ast.Dict` — so the `isinstance(kw.value, ast.Dict)` guard skipped it. Example:

    open(**({} | {'mode': (m := 'w'), 'file': 'plugins/evil.py'}))  # was ALLOW

Fix: replace the bare NamedExpr while-loop at `kw.value` with a call to `_unwrap_to_dict(kw.value)`, and similarly in `_extract_kv_from_dict` for spread values. `_unwrap_to_dict` returns an `ast.Dict | None`:

    def _unwrap_to_dict(node):
        """Peel NamedExpr/BitOr/BoolOp/IfExp/Subscript to reach an ast.Dict, or None."""
        if node is None:
            return None
        # Peel walrus layers first (recursive)
        while isinstance(node, ast.NamedExpr):
            node = node.value
        if isinstance(node, ast.Dict):
            return node
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # {} | {'mode': 'w'} — merge both sides (right wins, matches Python semantics)
            left = _unwrap_to_dict(node.left)
            right = _unwrap_to_dict(node.right)
            if left is None and right is None:
                return None
            merged_keys, merged_vals = [], []
            for d in (left, right):
                if d is not None:
                    merged_keys.extend(d.keys)
                    merged_vals.extend(d.values)
            return ast.Dict(keys=merged_keys, values=merged_vals)
        if isinstance(node, ast.BoolOp):
            # (x or {...}) or (x and {...}) — return first dict found in values
            for val in node.values:
                d = _unwrap_to_dict(val)
                if d is not None:
                    return d
            return None
        if isinstance(node, ast.IfExp):
            # {'mode':'w'} if cond else {} — try body then orelse
            d = _unwrap_to_dict(node.body)
            return d if d is not None else _unwrap_to_dict(node.orelse)
        if isinstance(node, ast.Subscript):
            # [{'mode':'w'}][0] — integer-indexed list/tuple literal
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                idx = node.slice.value
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    try:
                        return _unwrap_to_dict(node.value.elts[idx])
                    except IndexError:
                        return None
        return None  # Name, Call, and other non-static nodes remain documented misses

Apply in the main walker:

    kw_val = _unwrap_to_dict(kw.value)   # replaces bare while-NamedExpr + isinstance check
    if not isinstance(kw_val, ast.Dict):
        continue   # **variable or unresolvable wrapper — documented miss

Apply in `_extract_kv_from_dict` for spread entries:

    inner = _unwrap_to_dict(v)   # replaces bare while-NamedExpr + isinstance check
    if isinstance(inner, ast.Dict):
        kv.update(_extract_kv_from_dict(inner))

**BoolOp returns the FIRST dict found, not a merge.** For `x or {'mode':'w'}` the first dict wins regardless of runtime truthiness. This is intentional: if any static branch has a write-mode dict, block it. A BoolOp whose FIRST value is the write-mode dict blocks; if only later values are write-mode, those also block (loop visits all values). The merge-first-wins heuristic is safe-side.

**Negative-index Subscript is supported.** `[{'mode':'w'}][-1]` — Python list indexing allows negatives; `elts[idx]` with `idx=-1` works correctly in Python. This is covered by the same code path.

**Non-constant Subscript slice remains a documented miss.** `d[some_expr]` where the slice is not `ast.Constant(int)` — too dynamic to resolve statically. `_unwrap_to_dict` returns `None`.

### Short-circuit timing fix

When `_ast_starstar_hit` is already `True`, running `_RENAME_PRIMITIVES.search(code_blob)` on a 50k-char blob costs ~8000ms because the pattern contains `[\s\S]{0,2000}` CMT arms that scan the full blob. Fix: move `_ast_starstar_hit` to the TOP of the `or`-chain in `evaluate_write`'s HR-token gate, so it short-circuits before the expensive regex:

    if hr_tokens_present and (
        _ast_starstar_hit   # fast path: skip expensive regex when AST already confirmed
        or looks_like_rename_or_copy({"code": code_blob})
        or _RENAME_PRIMITIVES.search(code_blob)
    ):

Effect: 1000 walrus-value calls in one blob: 8000ms → 31ms. 100 BitOr+walrus calls: 820ms → 3ms.

**Whenever adding a new short-circuit bool to the HR gate or-chain, put it first.** Any non-regex predicate that is already determined before the gate should short-circuit the expensive regex, not follow it. The original order (`looks_like... or RENAME... or _ast_starstar_hit`) negated this entirely.



After Wave 56 hit an irreducible ceiling — `\r`/`\f`/`\f` in source, 61+ whitespace units before colon, and ongoing ReDoS fragility from quantifier cap games — the `**`-unpack arms were replaced with a single AST-based checker. This terminates the regex arms race for this class of detection.

### Why AST wins here

The regex approach for `**`-unpack patterns must approximate Python's whitespace and string-literal rules. Python's own parser already handles all of this exactly: `\r`, `\f`, `\t`, CRLF, 1000 spaces before a colon, `r'w'`/`u'w'` string prefixes, nested parens around dict keys — all are transparent after `ast.parse`. There is no ReDoS risk because `ast.parse` is O(n), not a backtracking NFA.

### Implementation

    import ast

    _AST_WRITE_FUNCS = {
        "open":      frozenset({"w", "a", "x", "r+", "w+", "a+", "x+"}),
        "GzipFile":  frozenset({"w", "a", "x"}),
        "ZipFile":   frozenset({"w", "x", "a"}),
        "PyZipFile": frozenset({"w", "x", "a"}),
        "TarFile":   frozenset({"w", "x", "a"}),
        "BZ2File":   frozenset({"w", "a", "x"}),
        "LZMAFile":  frozenset({"w", "a", "x"}),
        "FileIO":    frozenset({"w", "a", "x", "r+", "w+"}),
    }
    _AST_DBM_WRITE = frozenset({"n", "c", "w"})

    def _get_const_str(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _ast_has_starstar_write(code: str) -> bool:
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError:
            return False   # caller falls back to regex
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg is not None:
                    continue   # regular kwarg, not **
                if not isinstance(kw.value, ast.Dict):
                    continue   # **variable — documented miss
                kv = {}
                for k, v in zip(kw.value.keys, kw.value.values):
                    if k is None: continue   # **x inside dict display
                    k_s = _get_const_str(k)
                    v_s = _get_const_str(v)
                    if k_s and v_s:
                        kv[k_s] = v_s
                func = node.func
                func_name = None
                is_dbm = False
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                    if func_name == "open":
                        val, chain = func.value, []
                        while isinstance(val, ast.Attribute):
                            chain.append(val.attr); val = val.value
                        if isinstance(val, ast.Name): chain.append(val.id)
                        if chain and chain[-1] == "dbm": is_dbm = True
                if func_name is None: continue
                if is_dbm:
                    for key in ("flag", "mode"):
                        v_s = kv.get(key)
                        if v_s and any(v_s.startswith(m) for m in _AST_DBM_WRITE):
                            return True
                elif func_name in _AST_WRITE_FUNCS:
                    v_s = kv.get("mode")
                    if v_s and any(v_s.startswith(m) for m in _AST_WRITE_FUNCS[func_name]):
                        return True
        return False

Wire into `evaluate_write` for `execute_code` by setting `_ast_starstar_hit = _ast_has_starstar_write(code_blob)` before the HR-token gate, then OR it into the rename+HR condition. Keep `_STARSTAR_REGEX_FALLBACK` (a simple, non-quantifier-heavy pattern) for the SyntaxError fallback path.

### Documented misses (same structural limits as regex, unfixable statically)

- `open(**d)` — `d` is `ast.Name`, not `ast.Dict`; no dict literal visible
- `open(**{chr(109)+'ode': 'w'})` — key is `ast.BinOp(ast.Call, ...)`, not `ast.Constant`
- `open(**{'mode': f'w'})` — value is `ast.JoinedStr`, not `ast.Constant`
- `open(**{'mode': 'w' if True else 'r'})` — value is `ast.IfExp`, not `ast.Constant`
- `open(**{'mode': b'w'})` — value is `ast.Constant(bytes)`, not `str`; TypeError at runtime anyway
- `open(**{'mo'+'de': 'w'})` — key is `ast.BinOp`, not `ast.Constant`

None of these are new — they were all documented regex misses too. The regex fallback (`_STARSTAR_REGEX_FALLBACK`) and other gates (HR-token, path-extraction, encode-primitive) provide partial coverage for some.

### What AST newly fixes over Wave 56 regex

- `\r`, `\f`, `\r\n` between key name and colon — Python parser normalises, AST sees `'mode'` always
- 61+ spaces/tabs/newlines between key and colon — AST doesn't count them
- `#` inside a quoted string value (e.g., `'utf-8#'`) — regex CMT stalled; AST parses the full string
- String prefixes `r'w'`, `u'w'`, `Rf'w'` — `ast.Constant.value` is always the bare string `'w'`
- Any quantity of syntactic noise between tokens — Python's tokeniser handles it all
- No ReDoS: `ast.parse` is O(n), no backtracking

## Pattern Editing Pitfalls (When Modifying the Plugin File)

**`[^)]*` in `**`-unpack patterns stops at the first `)` of ANY inner call — use `[\s\S]{0,500}` instead.**
Any expression before or after `**` that contains its own `)` (e.g., `list()`, `(None)`, `dict(list())`,
`type('',(),{})()`) terminates `[^)]*` before the mode key is reached. The one-level absorber
`[^)]*(?:\([^)]*\)[^)]*)*` (Wave 50) only handles one depth of nested call — two-level nesting
(e.g., `dict(list())`) still bypasses it. The same-line scan `[^\n]{0,300}` (Wave 51) is better
but bypassed by multiline dicts, comment lines, and 300+ char padding. The correct current form is
`[\s\S]{0,500}` (Wave 52) on both sides of `\*\*`, which handles all wrapping forms and multiline
expressions without paren-depth tracking.

**`[^\n]{0,300}` for `**`-unpack scan has three residual bypasses — do not use it.**
Multiline dict (mode on line 2), `# comment\n` after the mode colon, and 300+ char padding before
the mode key all bypass it. Replace with Wave 56 `[\s\S]{0,2000}` on either side of `**` (simple,
never stalls on `#` in string values), KEY_JUNK `(?:#[^\n]*\n|[ \t]*\\[ \t]*\n|[ \t]|\n|\)){0,60}`
(disjoint alts, capped) after the key, and GAP `(?:[ \t\r\n\\()]|#[^\n]*){0,80}`
(no-quote charset) after the colon/= separator.

**Triple-quoted string keys bypass single-quote patterns.** `['"']mode['"']` requires exactly one
quote on each side; `'''mode'''` has three. Use `[\x27\x22]+mode[\x27\x22]+` (one or more quotes) to
match single, double, triple, and sextuple quoted forms. Failure mode: a Python dict literal whose
key is written as `'''mode'''` or `"""mode"""` passes through undetected.

**Add a mode-value string-prefix absorber `[bBfFrRuU]{0,2}` before the opening quote of the mode value.**
Python allows `r'wb'`, `b'w'`, `u'x'`, `br'w'` etc. as string literals. Without the prefix absorber,
`{'mode':r'wb'}` is ALLOW because the regex expects `'` immediately after `=:`. The absorber `[bBfFrRuU]{0,2}`
matches zero to two prefix characters, covering all two-letter combinations (rb, br, etc.). Apply it to
both the colon-key (`[=:]\s*[bBfFrRuU]{0,2}['"]+`) and keyword-arg (`=\s*[bBfFrRuU]{0,2}['"]+`) branches.

**Never use `str.replace()` in execute_code to replace regex pattern strings.** The Python string
representation of a raw regex like `r"\s*"` in the file is the literal characters `\s*`. When you
build a replacement snippet in execute_code, Python interprets the backslashes again, so what you
write as `\\s*` in the snippet becomes `\\s*` in the file (double-escaped), not `\s*`. This silently
corrupts every pattern in the replacement without raising any error. The file may pass `py_compile`
because the string syntax is valid, but the patterns no longer compile correctly at runtime.

Use the `patch` tool for all regex line edits. It operates on literal file text, has no string
escaping layer, and shows a diff for verification. After any patch, verify the affected line in the
file with read_file or grep to confirm backslash count is correct.

**After patching, verify git HEAD is still as expected before running an audit subagent.** A failed
patch that writes no change is easy to miss; the next subagent will audit stale code and report
findings as unfixed.

**Never use nested-paren depth macros.** Fixed-depth nested-paren alternation is bypassed
by one extra wrap AND causes exponential backtracking on long inputs. The arms race has no
floor. Use `[ \t\n]?[^\n]*` for the path arg — depth-unlimited, O(n), no cap bypass.

**Never use `[\s\S]{0,N}` for path argument capture — use `[ \t\n]?[^\n]*` instead.**
Even a bounded cap N creates a bypass: a path padded to N+1 chars pushes the mode token
beyond the cap, evading detection. `[\s\S]{0,500}` is for `**`-unpack pre/post scan only,
not for path arg capture. Reserve `[\s\S]{0,20}` exclusively for the comma-to-mode separator.

**Add `[ \t\n]?` absorber after `\(` in every constructor pattern.** Without it, a
newline immediately after the opening paren (PEP8/Black wrapping style) causes `[^\n]*`
to match the empty first line and miss the path arg entirely. Only `open()` had this
absorber by default; every other family (gzip, zipfile, tarfile, bz2/lzma, dbm,
io.FileIO, io.open) needs it explicitly. Absorber cap is one char — two+ newlines after
`(` is a documented miss.

**Add `mode=` / `flag=` keyword-first alternatives for every positional-mode pattern.**
Patterns requiring a comma before the mode token fail when mode is passed as the FIRST
keyword argument: `gzip.GzipFile(mode='wb', filename='plugins/evil.py')`. Add a sibling
alternation branch anchored on the keyword using the same `[ \t\n]?[^\n]*mode\s*=[\s\S]{0,20}`
shape so the absorber applies here too. Families needing this: gzip, bz2/lzma,
tarfile (`mode=`), dbm (`flag=`). Zipfile and open/io.FileIO already had mode= alts.

**Add `**{...}` dict-literal unpack alternatives for every mode= pattern family.**
`gzip.GzipFile(**{'mode':'wb','filename':'plugins/evil.py'})` bypasses both positional
and mode= patterns because neither sees a literal `mode=` token nor a comma before a
quoted mode string. Add the Wave 52 `[\s\S]{0,500}\*\*[\s\S]{0,500}` arm to each family.
Only variable-bound `**d` (pre-built dict) and `**vars()` remain documented misses.
Families: gzip, bz2/lzma, tarfile, dbm (flag or mode key);
zipfile, io.FileIO, and open() already had `**{...}` alts.

**Apply the absorber to the mode= branch of io.FileIO as well as the positional branch.**
When adding a `[ \t\n]?` absorber to a constructor's positional pattern, simultaneously
add it to the same constructor's mode= pattern — they are separate regex arms and missing
one from either leaves a gap: `io.FileIO(\nmode='w',name='plugins/evil.py')` was ALLOW
until Wave 47.

**dbm mode charset must exclude `r`.** Use `[ncw]` (n=new, c=create, w=write), not `[ncrw]`.
dbm.open(...,'r') is read-only and must ALLOW. Including `r` causes a false positive.

**For `**`-unpack patterns, use Wave 52 `[\s\S]{0,500}` scan — do NOT enumerate paren/dict-wrap forms.**
Adding `\(*` absorber + alternation branches for `{...}`, `({...})`, `dict({...})`, `dict(dict({...}))` is a
dead-end arms race: `**( ({...}))`, `dict(dict({...}))`, triple-wrap all bypass one wave at a time.
The correct single pattern: `[\s\S]{0,500}\*\*[\s\S]{0,500}(?:KEY[=:]CMT_VAL|mode=CMT_VAL)`
scans ANY content around `**` and matches on the literal `'mode'` key — no wrapping form can
avoid the literal mode key appearing in the source text. Apply to all nine families.

**getattr `**` variants need `\(*` not `\(?.`**
- `getattr(**dict(...))` — no extra parens
- `getattr(**(dict(...)))` — one paren wrap
- `getattr(**((dict(...))))` — two paren wraps (still a live bypass if `\(?` used)
Use `\(*` (zero or more) after `**` to cover any depth of wrapping.

**getattr keyword spacing.** PEP-8-compliant callers write `name = 'ZipFile'` with spaces around `=`.
Use `\s*=\s*` not bare `=` in keyword argument patterns.

**`patch` tool may fail with 'multiple matches' when the same line suffix appears in several families.**
When the old_string is too short and matches e.g. both io.FileIO and io.open lines, provide more
context (include more of the line) or patch both lines together as a single old_string.

## Accepted/Documented Bypasses (Not Fixable by Regex)

The following are structurally undetectable by static regex and are documented as accepted risk:

- Two+ newlines immediately after `(`: `gzip.GzipFile(\n\n'path','wb')` — absorber cap=1; HR-token check partially mitigates
- Two-level nested calls before `**`: `gzip.GzipFile(**(type('',(),{})() or {'mode':'wb',...}))` — complex wrapping
- Variable-bound `**d` where `d` is a pre-built dict: `d={'mode':'wb','filename':...}; gzip.GzipFile(**d)` — no literal mode token visible
- `**vars()` with mode in scope — dynamically computed, undetectable
- `**dict(mode='wb',...)` and `**{'mode':'wb',...}` are now BLOCKED (Wave 47+ `**` unpack patterns)
- `**({...})`, `**(dict({...}))`, `**( ({...}))`, `**(dict(dict({...})))` and all other single-level wrapping forms are now BLOCKED (Wave 50 unified form)
- `**(list() or {...})`, `**((None) or {...})`, `**(dict(list()) or {...})` and ALL single-same-line wrapping forms including two-level inner calls are now BLOCKED (Wave 51 `[^\n]{0,300}` same-line scan / Wave 52 `[\s\S]{0,500}`)
- `**{'''mode''':'wb',...}` triple-quoted key is now BLOCKED (Wave 50/51 `[\x27\x22]+` quantifier)
- `**{'mode':r'wb',...}` / `**{'mode':b'w',...}` r/b/u prefix values are now BLOCKED (Wave 50/51 `[bBfFrRuU]{0,2}` prefix absorber)
- `**{('mode'):'wb',...}` parenthesized key is now BLOCKED (Wave 51 `\)?` after closing key quote)
- `**{'mode':('wb'),...}` parenthesized value is now BLOCKED (Wave 51 `\(?` before value prefix)
- `**{'mode':'r+','file':...}` / `r+b` / `rb+` read-write modes are now BLOCKED (Wave 51 dedicated r+ arm)
- Multiline dict `gzip.GzipFile(**{\n    'mode':'wb',...})` is now BLOCKED (Wave 52 `[\s\S]{0,500}`)
- `# comment\n    'wb'` after mode colon is now BLOCKED (Wave 52 `(?:[ \t]*#[^\n]*)?` comment-gap absorber)
- 300-char padding before mode key is now BLOCKED (Wave 52 `[\s\S]{0,500}` uncapped)
- False positive from commented-out mode keys: `# 'mode':'w'\n    'mode':'r'` — now fixed (Wave 55 unified CMT consumes the comment line as `#[^\n]*\n` unit; the commented text is unreachable by key_arm; the real read-only key ALLOWs)
- Triple-quoted filename with embedded literal newline: `open(**{'file': '''plugins/evil.py\n#''', 'mode': 'w'})` — CMT_POST stops at `\n#` inside the triple-quoted string; `'mode':'w'` is unreachable by the `**`-unpack arm. **Not a real bypass**: the write target is a path containing a literal newline character, which is a DIFFERENT filesystem path than `plugins/evil.py`. mode-first dicts still BLOCK. Informational/low only.
- Same-line content >2000 chars before mode key — CMT `{0,2000}` cap terminates; ALLOW (documented miss)
- `\x6dode` or `\u006dode` hex/unicode escape for `mode` key — regex sees literal `\x6d`, not `m`; ALLOW (documented miss)
- `chr(109)+'ode'` dynamic key construction — no literal `mode` token; ALLOW (documented miss)
- `pathlib.Path('plugins')/'evil.py'` — truediv creates Path object; regex sees source string only
- `(gzip.GzipFile)(...)` / `[gzip.GzipFile][0](...)` — callee paren/list-wrap
- `getattr(gzip, 'GzipFile')(...)` — positional two-arg getattr (separate from keyword form)
- `getattr(Path(...).parent / 'evil.py', 'write_text')` — truediv chaining
- `partial(open, 'plugins/evil.py', 'w')` — functools.partial indirect binding
- `lambda: open('plugins/evil.py', 'w')` — lambda-bound
- `exec("open('plugins/evil.py','w')")` — runtime eval
- `vars(gzip).get('GzipFile')(...)` — dict-lookup indirection
- `sys.modules['gzip'].GzipFile(...)` — sys.modules subscript
- Computed mode strings: `chr(119)`, `['w'][0]`, variable bound
- String concat paths: `'plugins' + '/evil.py'` — no literal path token
- Class hierarchy traversal: `__subclasses__()` chains
- Unicode escape keys: `{'\u006dode':'wb'}` — `\u006d` = 'm' at runtime, but regex sees literal `\u006d`
- Bytes literal mode: `{'mode':b'wb'}` — `b'wb'` is a bytes object, not a string literal token
