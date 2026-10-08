# Regex Bypass Pattern Classes — governance-hard-block

This file documents the recurring classes of Python regex bypass that arise in iterative adversarial audits of the governance-hard-block plugin. Each class is a generalizable attack family, not a session-specific incident.

## Coverage-Layer Map

Every dangerous callable family must be covered in ALL of these interception layers simultaneously. Missing any one layer costs a full wave:

1. Direct call: `os.remove('...')` — primary module.func pattern
2. Paren-wrap: `(os.remove)('...')` — grouped callable
3. List-wrap: `[os.remove][0]('...')` — list-subscript callable (positive and negative index)
4. sys.modules: `sys.modules['os'].remove('...')` — module dict lookup + optional submodule hop
5. getattr positional: `getattr(os, 'remove')('...')` — 2nd arg string
6. getattr name=: `getattr(os, name='remove')('...')` — keyword form
7. vars/__dict__: `vars(os).get('remove')('...')`, `os.__dict__['remove']('...')` — attribute dict access
8. dot-whitespace: `os .remove('...')`, `os\t.remove('...')` — whitespace around the dot

When adding a new callable family (e.g. sqlite3.connect, gzip.GzipFile), add it to ALL 8 layers in the same wave. Verify each layer with an inline test before committing.

## Recurring Bypass Families

### Paren-wrap / List-wrap
- `(module.func)(args)` — the function is grouped in parens before being called
- `[module.func][N](args)` — the function is placed in a list then subscripted (positive or negative N)
- `[module.func][-1](args)` — negative index works identically
- Inner whitespace: `[ module.func ][0](args)` — \s* must be inside the brackets
- Multi-segment paths: `(dbm.gnu.open)(args)` — three-segment module.sub.func needs explicit alternation or a broader pattern

### sys.modules chain
- `sys.modules['mod'].func(args)` — basic subscript
- `sys.modules.get('mod').func(args)` — .get() accessor
- `sys.modules.get('mod').submod.func(args)` — one extra hop for submodule (e.g. dbm.gnu); add `(?:\.\s*\w+)?` before the final dot
- Deep chain `sys.modules['mod'].__dict__.get('func')(args)` — multi-layer; hard to cover with regex alone

### getattr forms
- Positional: `getattr(obj, 'func')` — second argument as string literal
- Keyword: `getattr(obj, name='func')` — named keyword form
- Nested obj: `getattr(Path('x').parent, 'write_text')` — complex object expression in first arg
- Star-unpack: `getattr(*[obj, 'func'])` — documented miss (requires AST)

### vars / __dict__ access
- `vars(mod)['func']` / `vars(mod).get('func')` — vars() with subscript or .get()
- `mod.__dict__['func']` / `mod.__dict__.get('func')` — direct __dict__ access
- Name list must include all callable families: open, write_text, write_bytes, remove, unlink, rename, replace, truncate, system, popen, execv*, Popen, mknod, connect, BZ2File, LZMAFile, GzipFile, ZipFile, TarFile, PyZipFile, DbfilenameShelf, rmtree, move, copy, copy2, copyfile, link, symlink, symlink_to, hardlink_to, run, check_output, check_call, FileIO

Rule: every time a new class constructor is added to a direct pattern, add its name to ALL secondary access layers (vars, __dict__, getattr positional, getattr name=, sys.modules) in the same wave. Constructor names lag behind function names unless explicitly included.

### Dot-whitespace
- `os .system(args)` — space between module name and dot
- `os\t.system(args)` — tab between module name and dot
- `os\s*.\s*system` — both sides of the dot need \s*
- Also applies to type().\s*__call__, open.\s*__call__, types.\s*BuiltinFunctionType

### Quote escaping in raw strings
- `['"]{1,3}` inside `r"..."` — the `"` inside terminates the r-string early
- Use `[\x27\x22]{1,3}` instead — hex escapes for quote chars work correctly in raw strings
- Verify with py_compile immediately after any patch that touches a quote alternation in a regex pattern

### Module.open aliases — paren/list wrap
The paren/list wrap for `os.open` (W35) does NOT automatically cover these write-capable `.open` callables:
- `gzip.open`, `builtins.open`, `io.open`, `bz2.open`, `lzma.open`, `codecs.open`, `wave.open`, `tarfile.open`

These need a SEPARATE paren/list wrap alternation: `(?:gzip|builtins|io|bz2|lzma|codecs|wave|tarfile)\.open`. The W31-003 catch-all does NOT cover them because those module names are not in its module list.

### Multi-segment module paths in paren/list wrap
- `(dbm.gnu.open)(args)` — three-segment path; needs `dbm\.\s*(?:gnu|dumb|ndbm|sqlite3)\.\s*open` in the paren/list alternation explicitly
- Submodule variants must be added both to the ungrouped dotted pattern AND to the paren/list wrap alternation — they are separate patterns
- `dbm.sqlite3` (CPython 3.14+) must be added alongside `dbm.gnu`, `dbm.dumb`, `dbm.ndbm`

### Class constructors and classmethods needing paren/list wrap coverage
When a class constructor or classmethod (not a module-level function) is the dangerous callable, it needs explicit entries in the paren/list wrap alternation. Every wave adds new missed names:
- `zipfile.ZipFile` — blocked unwrapped, bypassed when grouped as `(zipfile.ZipFile)('x','w')`
- `zipfile.PyZipFile` — subclass of ZipFile, same bypass gap; must be added alongside ZipFile in every pattern (direct, paren, list, star-unpack, **, getattr, vars, __dict__, sys.modules)
- `tarfile.TarFile` — direct constructor; also has classmethod form `tarfile.TarFile.open` which needs its own entry: `tarfile\.\s*TarFile\s*\.\s*open` in both paren and list wrap
- `shelve.DbfilenameShelf` — underlying implementation class; `shelve.open` was covered but not the direct constructor

Rule: when adding a new class to ZipFile-like patterns, add BOTH the constructor form AND any classmethod `.open` form. Classmethods accessed as `Class.open` are a separate dotted path that the constructor pattern does not cover.

### Grouped path method — (path_expr.open)(mode)
`(pathlib.Path('x').open)('w')` — grouping a method reference before calling it. Cover with:
`\(\s*(?:Path\s*\([^)]{0,200}\)|pathlib\.\s*Path\s*\([^)]{0,200}\)|[a-zA-Z_]\w*(?:[/\\][^\s)]{1,80})?)\s*\.\s*open\s*\)\s*\(`
Note: `[^\)]{1,100}` inside a character class ends with `\)` which closes the outer group during concatenation — use `[^\s)]{1,80}` instead.

The **list-wrap** form also needs a separate pattern: `[Path('x').open][0]('w')`. Paren-wrap and list-wrap are distinct alternations; adding paren-wrap does not cover list-wrap.

### fileinput write mode — separate from inplace
`fileinput.input(files='x',mode='w')` is a distinct bypass from `inplace=True`. The existing inplace= pattern does not catch keyword `mode='w'/'a'/'wb'`.

Three distinct pitfalls in this pattern:

1. **`[^)]*` stops at first `)` in args**: `fileinput.input(('x'),mode='w')` places a parenthesized tuple as the first arg, and `[^)]*` halts at the inner `)` before reaching `mode=`. Use `(?:[^()]|\([^)]*\))*` for one-level nesting and `(?:[^()]|\((?:[^()]|\([^)]*\))*\))*` for two-level nesting. In valid Python, `(('x'))` is just `'x'` (grouping, not tuple), so extra parens are legal and must be covered. Prefer the two-level form to handle both `('x')` and `(('x'))` without opening catastrophic backtracking.

2. **Mode charset gaps**: The explicit alternation `w|a|x|wb|ab|xb|r+|w+|a+` misses `wt`, `at`, `xt`, `r+b`, `w+b`, `wb+`, etc. Use a generalized charset: `[waxr][btw+]{0,3}` which covers two-letter and three-letter mode combinations without enumerating each.

3. **Paren/list wrap bypasses the mode= and inplace= gates entirely**: `(fileinput.input)(files='x',mode='w')` calls through a grouped reference that bypasses both gate patterns. Add dedicated alternations:
   - Paren-wrap: `\(\s*fileinput\s*\.\s*(?:input|FileInput)\s*\)\s*\(`
   - List-wrap: `\[\s*fileinput\s*\.\s*(?:input|FileInput)\s*\]\s*\[[^\]]*\]\s*\(`

Full safe pattern:
`fileinput\.(?:input|FileInput)\s*\((?:[^()]|\([^)]*\))*mode\s*=\s*[bBfFrRuU]{0,2}[\x27\x22](?:w|a|x|r\+|w\+|a\+|[waxr][btw\+]{0,3})[\x27\x22]`

### Combined-regex compilation is the real gate — py_compile is NOT sufficient
py_compile validates Python syntax but does NOT compile the regex pattern string. A paren added to one alternation of a multi-part `re.compile(r"..." r"|..." r"|...")` can create an unbalanced group in the concatenated pattern that py_compile misses entirely. After any patch to a regex pattern:
1. Run `python3 -m py_compile` (catches Python syntax)
2. ALSO import the module and let `re.compile` run: `spec.loader.exec_module(m)` at the top of the verify script will catch regex errors at load time
The module-import verify step catches paren-balance errors that py_compile never sees.

### getattr keyword form — name= first (object= second)
`getattr(name='ZipFile', object=zipfile)` is a distinct form from the standard `getattr(obj, 'ZipFile')`. The W24-008 pattern that handles this form only checked for the `object=` keyword trigger, and its name alternation list was not updated when new callable families were added. Rule: when extending the positional getattr name alternation, ALSO extend the W24-008 name-first keyword alternation — they are separate pattern branches.

The keyword form to cover:
`getattr\s*\(\s*(?:object\s*=|name\s*=\s*[bBfFrRuU]{0,2}['"][^'"]*(?:funcname|..)[^'"]*['"])`

Critical: the `name=` branch requires `\s*` AFTER the `=` — `name\s*=` without the trailing `\s*` misses PEP8-spaced forms like `name = 'ZipFile'` (space before and after `=`) and tab-after-`=` forms. The pattern must be `name\s*=\s*`, not `name\s*=`. The `object=` branch fires without checking the name literal, so it only needs `object\s*=\s*` (any attribute name following is dangerous); the `name=` branch must match the name literal itself with `\s*` on both sides of `=`.

Both the `object=` trigger (fires for any name containing a blocked word) and the `name=` trigger (checks the string literal) must include the same extended name set: ZipFile, TarFile, PyZipFile, DbfilenameShelf, GzipFile, BZ2File, LZMAFile, FileIO, mknod, Popen, connect.

### getattr double-star dict-unpack (`**{...}` form)
`getattr(**{'name':'ZipFile','object':zipfile})` passes arguments as a dict literal unpack. The star-unpack `getattr(*[obj, 'func'])` pattern only covers the single-star positional-list form. The double-star dict form is a separate attack. Cover with:
`getattr\s*\(\s*\*\*\s*\{[^}]*\b(?:name|__name__)\s*['"]?\s*[=:]\s*['"](?:dangerous-name-list)`

Key design choices:
- `\b(?:name|__name__)` — matches the dict key (string key or bare identifier)
- `[=:]` — matches both Python keyword-arg notation (never appears in dict literal) and dict colon
- The name string immediately follows — requires the danger name to be a literal, not a variable
- Key order: `{'name':'ZipFile','object':zipfile}` vs `{'object':zipfile,'name':'ZipFile'}` — both must match; `[^}]*` before the key name absorbs any preceding keys

Documented miss: `n = 'ZipFile'; getattr(**{'name': n, 'object': zipfile})` uses a variable as the name value — requires runtime tracking; accepted.

### Class classmethod variants — TarFile.open
`tarfile.TarFile.open(path, mode='w:gz')` is a three-segment dotted path distinct from both `tarfile.open(...)` (two-segment) and `(tarfile.TarFile.open)(...)` (grouped form). The ungrouped classmethod path must be added to the primary tarfile dotted pattern:
`tarfile\.\s*(?:open|TarFile|TarFile\s*\.\s*open)\s*\(`

Compression mode strings like `'w:gz'`, `'w:xz'`, `'a:bz2'`, `'x:gz'` contain `[wax]` as the first character, so the existing `[\x27\x22][wxa][^)]*\)` pattern covers them once the classmethod path is included.

Rule: when a class has a classmethod `.open` alternative to the constructor, add BOTH to every layer — constructor form AND `Class.open` form are separate dotted paths.

### gzip.GzipFile exclusive-create mode (x/xb)
`gzip.GzipFile('x.py', 'x')` and `gzip.GzipFile('x.py', 'xb')` — exclusive-create modes. The character class `[wa]b?` (covering write/append modes) missed `x`/`xb`. Extend to `[wax]b?t?` to cover exclusive-create in any binary/text combination. The `gzip.open()` function for mode `'x'` is caught by the generic open() pattern; it is only `GzipFile` that falls through because it does not end in `open(`.

Rule: whenever the generic `open()` mode pattern is extended to include a new mode letter, also extend the GzipFile-specific mode character class — they do not inherit from each other.

### Nested-paren depth in path args — upgrade must be batch-applied
`[^)]*` in a path argument stops at the first `)`, missing any nested call like `os.path.join('plugins','evil.py')` or `pathlib.Path('dir') / 'file'`. When upgrading from `[^)]*` to one-level nested `(?:[^()]|\([^)]*\))*`, apply the upgrade to ALL families that share the same structural gap in the same wave:

- `gzip.GzipFile(join(),'wb')` — gzip pattern
- `tarfile.TarFile(join(),'w')` — tarfile constructor
- `tarfile.TarFile.open(join(),mode='w:gz')` — tarfile classmethod
- `bz2.BZ2File(join(),'w')` — bz2 pattern
- `lzma.LZMAFile(join(),'w')` — lzma pattern

If any one of these is upgraded while the others are left at `[^)]*`, the next audit wave will find the remaining families in a separate but identical finding. Upgrade all in one wave.

Nested paren depth tracking for fileinput (mode= pattern):
- Level 1: `(?:[^()]|\([^)]*\))*` — handles `(x)` — catches `fileinput.input(('x'),mode='w')`
- Level 2: `(?:[^()]|\((?:[^()]|\([^)]*\))*\))*` — handles `((x))` — catches `fileinput.input(((x)),mode='w')`
- Level 3: `(?:[^()]|\((?:[^()]|\((?:[^()]|\([^)]*\))*\))*\))*` — handles `(((x)))` — current fileinput boundary
- Level 4+: documented miss — extending further risks ReDoS; HR-token gate covers high-value targets regardless

Rule: always ReDoS-test the new depth level with a 5000-char padded input after upgrading. A linear-time result (<10ms) is safe; exponential backtracking (>1s) means the pattern must be restructured.

### Finite quantifier bypass (`{0,N}` in path arg)
A pattern using `{0,N}` for the path argument (e.g. `(?:[^()]|\([^)]*\)){0,100}`) allows an attacker to bypass detection by providing a path argument longer than N characters. The gate fails open at N+1 chars.

Rule: choose N large enough that no realistic plugin path ever reaches it. `{0,100}` is bypassable with a 101-char filename; `{0,300}` is the safe minimum for ZipFile and similar patterns where the path is the first argument. If the path could be constructed via string operations, raise N or switch to a format that does not cap. When in doubt, use `[^)]*` (bounded by the natural `)` of the call) with nested-paren upgrades rather than `{0,N}` — the `)` boundary is always tighter than a fixed cap for single-segment paths.

Verify: after setting `{0,N}`, test with a path of length N+1 and length N+50 to confirm both block.
- `functools.partial(os.remove, ...)` and `functools.reduce(getattr, ...)` chains
- Lambda-bound callables: `f = lambda p: open(p, 'w'); f('plugins/x.py')`
- Backslash-newline continuation: `os\\\nremove('...')`
- Grouped dunder: `(types.BuiltinFunctionType.__call__)(open, '...')` — infinite regress
- `inspect.getattr_static`, `__subclasses__()` traversal, ctypes, dynamic imports via `__import__`/`importlib`
- exec() string evaluation, string concatenation of module name, variable-bound mode string

## Name-List Lag Principle

When a new callable family is introduced to primary patterns, it will be absent from every secondary layer (paren-wrap, list-wrap, sys.modules, getattr, vars, __dict__). This "name-list lag" produces one finding per missing layer per audit wave. Eliminate it by patching ALL layers in the same wave and verifying with explicit test cases for each.

Checklist per new callable family:
- [ ] Primary direct-call pattern (`module.func(`)
- [ ] Paren-wrap alternation (for both simple `module.func` AND multi-segment `module.sub.func`)
- [ ] List-wrap alternation (same scope as paren-wrap)
- [ ] sys.modules method alternation string (add `(?:\.\s*\w+)?` hop if submodule access needed)
- [ ] getattr positional name alternation `[\x27\x22]{1,3}name[\x27\x22]{1,3}`
- [ ] getattr name= keyword positional alternation (W24-008 name-first form is a SEPARATE branch from getattr positional — must update both)
- [ ] vars() name alternation `\bname\b`
- [ ] __dict__ name alternation `\bname\b`
- [ ] Grouped method variant if it is a method (not just a module-level callable): `(obj.func)(args)`
- [ ] Classmethod `.open` form if the class has one: e.g. `TarFile.open` is separate from both `TarFile(...)` and `tarfile.open(...)`
