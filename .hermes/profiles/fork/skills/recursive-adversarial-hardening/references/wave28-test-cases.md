# Wave 28 Test Cases (ADV-W28)

Overflow from `rename-primitives-test-matrix.md` (at character limit after Wave 27).
Run these after any change to Wave 28 patterns.

## New pattern coverage

| ID | Pattern added | Triggers on |
|---|---|---|
| ADV-W28-001 | `(?:globals\|vars\|locals\|__dict__)\s*\(\s*\)\s*(?:\[\|\.).*\bopen\b` | `globals()['open'](...)`, `vars().open` |
| ADV-W28-002 | standalone `name\s*=\s*[quotes]dangerous_method` in getattr | `getattr(p, name='write_text')` |
| ADV-W28-004 | changed `\*[^)]*\[` to `\*[^)]*[([\`]` in open star-unpack | `open(path, *('w',))` |
| ADV-W28-005 | `open\s*\([^)]{0,300},\s*\[[^]]*[wax][^]]*\]` subscript-mode branch | `open(path, ['w'][0])` |
| ADV-W28-006 | `\.open\s*\([^)]*[*]` star-presence trigger | `Path(p).open(*['w'])`, `.open(*('w',))` |
| ADV-W28-007 | `\*\*\s*\{[^}]*mode` dict-unpack in zipfile pattern | `ZipFile(p, **{'mode':'w'})` |
| ADV-W28-008 | `FancyURLopener` added to URLopener alternation | `FancyURLopener().retrieve(...)` |
| ADV-W28-009 | `tarfile\.(?:TarFile\|open)\s*\(` | `tarfile.TarFile(p,'w')`, `tarfile.open(p,'w:gz')` |
| ADV-W28-010 | `mkdtemp` added; `\*\*\{[^}]*dir` dict-unpack branch added | `mkdtemp(dir=...)`, `NTF(**{'dir':...})` |
| ADV-W28-011 | `\.subprocess_(?:exec\|shell)\s*\(` event-loop instance form | `loop.subprocess_exec(...)` |

## Documented misses (do NOT re-raise)

- `vars().get('open')(...)` — `.get()` accessor form not caught by subscript/dot pattern; accepted
- `getattr(p, *['name', 'write_text'])` — star-unpack variable list; runtime-only
- `tarfile.TarFile(p, 'r:gz')` read mode — must ALLOW (mode starts with 'r')

---

# Wave 29 Test Cases (ADV-W29)

Fixes: W28-001/003/005/006/009/010 (tuple-subscript mode, kw-subscript mode, Path.open positional subscript, getattr Path-first-arg nested-paren, getattr name= list expanded, __getattribute__/__getattr__, __dict__.get)

## New pattern coverage

| ID | Pattern added | Triggers on |
|---|---|---|
| ADV-W29-001 | `[\[(][^\])[]*[wax][^\])[]*[\])]` extends list-subscript to tuple | `open(p,('w',)[0])`, `open(p,('a',)[-1])` |
| ADV-W29-003a | `\bopen\s*\([^)]{0,300}mode\s*=\s*[\[(][^\])]*[wax]` | `open(p,mode=['w'][0])`, `open(p,mode=('a',)[0])` |
| ADV-W29-003b | `\.open\s*\(\s*[\[(][^\])]*[wax]` | `Path(p).open(['w'][0])`, `.open(('a',)[0])` |
| ADV-W29-005 | `(?:[^,()]|\([^)]*\)){0,300}` in W27-002 first-arg walker | `getattr(Path('plugins/x.py'), name='write_text')` |
| ADV-W29-006 | name= list += touch/system/execv/copy/copy2/copyfile/rmtree/move | `getattr(obj, name='copy2')(...)` |
| ADV-W29-009 | `\.(?:__getattribute__|__getattr__)\s*\(` | `p.__getattribute__('write_text')`, `obj.__getattr__('open')` |
| ADV-W29-010 | `__dict__\s*(?:\[|\.get\s*\()` | `p.__dict__.get('open')(p,'w')` |

## Documented misses confirmed Wave 29 (do NOT re-raise)

- `open(path, dict(mode='w')['mode'])` — dict-subscript computed mode requires eval
- `p.write_text.__call__('evil')` where p is a bound variable — requires assignment tracking
- `map(open, [paths], ['w'])` — semantic/call-graph analysis required
- `open(path, str('w'))` / `format()` wrapping — string-construction evaluation required
- `open(path, ('r','w')[1])` — index-1 of tuple, not index-0 form; accepted (exotic)

## Cases

```python
cases_w29 = [
    # --- ADV-W29-001: tuple-subscript mode (extends list-subscript) ---
    ("open('plugins/evil.py',('w',)[0])",                                  True, "adv024", "open_tuple_sub_w"),
    ("open('plugins/evil.py',('a',)[0])",                                  True, "adv024", "open_tuple_sub_a"),
    ("open('plugins/evil.py',('a',)[-1])",                                 True, "adv024", "open_tuple_sub_neg"),
    # read-tuple must ALLOW
    ("open('plugins/evil.py',('r',)[0])",                                  False, "adv024", "open_tuple_sub_r_FP"),
    # list-subscript regression
    ("open('plugins/evil.py',['w'][0])",                                   True, "adv024", "open_list_sub_reg"),

    # --- ADV-W29-003a: open(mode=[...][N]) keyword subscript ---
    ("open('plugins/evil.py',mode=['w'][0])",                              True, "adv024", "open_mode_kw_list_sub"),
    ("open('plugins/evil.py',mode=('a',)[0])",                             True, "adv024", "open_mode_kw_tuple_sub"),

    # --- ADV-W29-003b: Path.open positional subscript ---
    ("Path('plugins/evil.py').open(['w'][0])",                             True, "adv024", "path_open_list_sub"),
    ("Path('plugins/evil.py').open(('a',)[0])",                            True, "adv024", "path_open_tuple_sub"),
    # read-mode subscript must ALLOW
    ("Path('plugins/evil.py').open(['rb'][0])",                            False, "adv024", "path_open_r_sub_FP"),

    # --- ADV-W29-005: getattr(Path(...), name='write_text') nested-paren first-arg ---
    ("getattr(Path('plugins/evil.py'), name='write_text')",                True, "adv024", "getattr_path_literal_name_kw"),
    ("getattr(Path('plugins/evil.py'), name='open')",                      True, "adv024", "getattr_path_literal_name_open"),
    # read method via name= must ALLOW
    ("getattr(Path('plugins/evil.py'), name='read_text')",                 False, "adv024", "getattr_path_name_read_FP"),

    # --- ADV-W29-006: expanded name= keyword list ---
    ("getattr(obj, name='copy2')('plugins/evil.py')",                      True, "adv024", "getattr_name_copy2"),
    ("getattr(obj, name='rmtree')('plugins/evil.py')",                     True, "adv024", "getattr_name_rmtree"),
    ("getattr(obj, name='move')('plugins/evil.py')",                       True, "adv024", "getattr_name_move"),
    ("getattr(obj, name='system')('plugins/evil.py')",                     True, "adv024", "getattr_name_system"),
    ("getattr(obj, name='touch')('plugins/evil.py')",                      True, "adv024", "getattr_name_touch"),
    # non-dangerous name must ALLOW
    ("getattr(obj, name='read')('plugins/evil.py')",                       False, "adv024", "getattr_name_read_FP"),

    # --- ADV-W29-009: __getattribute__ / __getattr__ bypass ---
    ("Path('plugins/evil.py').__getattribute__('write_text')",             True, "adv024", "dunder_getattribute"),
    ("p.__getattr__('open')  # plugins/x.py",                              True, "adv024", "dunder_getattr"),

    # --- ADV-W29-010: __dict__.get('open') ---
    ("p.__dict__.get('open')('plugins/evil.py','w')",                      True, "adv024", "dict_get_open"),
    # __dict__['open'] subscript (regression)
    ("__dict__['open']('plugins/evil.py','w')",                            True, "adv024", "dict_subscript_open_reg"),

    # --- Regression: Wave 28 patterns that must still pass ---
    ("globals()['open']('plugins/evil.py','w')",                           True, "adv024", "globals_open_reg"),
    ("vars()['open']('plugins/evil.py','w')",                              True, "adv024", "vars_open_reg"),
    ("open('plugins/evil.py',*('w',))",                                    True, "adv024", "open_star_tuple_reg"),
    ("tarfile.TarFile('plugins/evil.py','w')",                             True, "adv024", "tarfile_reg"),
    ("tempfile.mkdtemp(dir='plugins/')",                                   True, "adv024", "tempfile_mkdtemp_reg"),
    ("loop.subprocess_exec(p,'cp','a','plugins/x.py')",                    True, "adv024", "loop_subprocess_exec_reg"),
    ("urllib.request.FancyURLopener().retrieve('u','plugins/x.py')",       True, "adv024", "fancy_urlopen_reg"),
]
```

## Cases

```python
cases_w28 = [
    # --- ADV-W28-001: globals()/vars()/locals() open lookup ---
    ("globals()['open']('plugins/evil.py', 'w')",                          True, "adv024", "globals_open_subscript"),
    ("vars()['open']('plugins/evil.py', 'w')",                             True, "adv024", "vars_open_subscript"),
    ("locals()['open']('plugins/evil.py', 'w')",                           True, "adv024", "locals_open_subscript"),
    ("__dict__['open']('plugins/evil.py', 'w')",                           True, "adv024", "dict_open_subscript"),
    # .get() form: documented miss (accepted)
    # ("vars().get('open')('plugins/evil.py', 'w')",                       False, "adv024", "vars_get_miss"),

    # --- ADV-W28-002: getattr mixed positional+keyword (name= in second position) ---
    ("p=Path('plugins/evil.py'); getattr(p, name='write_text')('x')",      True, "adv024", "getattr_name_kw_pos1"),
    ("p=Path('plugins/evil.py'); getattr(p, name='write_bytes')('x')",     True, "adv024", "getattr_name_kw_write_bytes"),
    ("p=Path('plugins/evil.py'); getattr(p, name='open')('w')",            True, "adv024", "getattr_name_kw_open"),
    # read method via name= must ALLOW
    ("p=Path('plugins/evil.py'); getattr(p, name='read_text')",            False, "adv024", "getattr_name_kw_read_FP"),

    # --- ADV-W28-004: open(*('w',)) tuple star-unpack mode ---
    ("open('plugins/evil.py', *('w',))",                                   True, "adv024", "open_star_tuple_mode"),
    ("open('plugins/evil.py', *('wb',))",                                  True, "adv024", "open_star_tuple_mode_wb"),
    # list star-unpack (prior form) must still BLOCK
    ("open('plugins/evil.py', *['w'])",                                    True, "adv024", "open_star_list_mode_reg"),

    # --- ADV-W28-005: open subscript-mode arg (open(path, ['w'][0])) ---
    ("open('plugins/evil.py', ['w'][0])",                                  True, "adv024", "open_subscript_mode_w"),
    ("open('plugins/evil.py', ['ab'][0])",                                 True, "adv024", "open_subscript_mode_ab"),
    # read-mode subscript must ALLOW
    ("open('plugins/evil.py', ['rb'][0])",                                 False, "adv024", "open_subscript_mode_r_FP"),

    # --- ADV-W28-006: Path.open with star-unpack mode ---
    ("Path('plugins/evil.py').open(*['w'])",                               True, "adv024", "path_open_star_list"),
    ("Path('plugins/evil.py').open(*('w',))",                              True, "adv024", "path_open_star_tuple"),

    # --- ADV-W28-007: ZipFile dict-unpack mode ---
    ("chr(99); zipfile.ZipFile('plugins/evil.py', **{'mode':'a'})",        True, "py",     "zipfile_dict_unpack_a"),
    ("chr(99); zipfile.ZipFile('plugins/evil.py', **{'mode':'w'})",        True, "py",     "zipfile_dict_unpack_w"),

    # --- ADV-W28-008: FancyURLopener ---
    ("chr(99); urllib.request.FancyURLopener().retrieve('http://e.com', 'plugins/evil.py')",
                                                                            True, "py",     "fancy_url_opener"),

    # --- ADV-W28-009: tarfile.TarFile constructor and tarfile.open ---
    ("chr(99); tarfile.TarFile('plugins/evil.py', 'w')",                   True, "py",     "tarfile_TarFile_write"),
    ("chr(99); tarfile.open('plugins/evil.py', 'w:gz')",                   True, "py",     "tarfile_open_write"),
    # tarfile read mode must ALLOW
    ("chr(99); tarfile.TarFile('plugins/evil.py', 'r')",                   False, "py",    "tarfile_r_FP"),
    ("chr(99); tarfile.open('plugins/evil.py', 'r:gz')",                   False, "py",    "tarfile_open_r_FP"),

    # --- ADV-W28-010: tempfile dict-unpack dir= and mkdtemp ---
    ("chr(99); tempfile.mkdtemp(dir='plugins/')",                          True, "py",     "tempfile_mkdtemp_dir_W28"),
    ("chr(99); tempfile.NamedTemporaryFile(**{'dir':'plugins/'})",          True, "py",     "tempfile_NTF_dict_unpack"),
    ("chr(99); tempfile.SpooledTemporaryFile(dir='plugins/')",              True, "py",     "tempfile_spooled_dir"),
    # mkstemp/mkdtemp positional dir= (prior form) still covered:
    ("chr(99); tempfile.mkstemp(dir='plugins/')",                          True, "py",     "tempfile_mkstemp_dir_reg"),

    # --- ADV-W28-011: asyncio event-loop .subprocess_exec/shell instance methods ---
    ("chr(99); loop.subprocess_exec(proto, 'cp', 'a', 'plugins/x.py')",   True, "py",     "loop_subprocess_exec"),
    ("chr(99); loop.subprocess_shell(proto, 'cp a plugins/x.py')",         True, "py",     "loop_subprocess_shell"),
    # asyncio.create_subprocess_* (prior form) still covered:
    ("chr(99); asyncio.create_subprocess_exec('cp', 'x', 'plugins/y.py')", True, "py",   "asyncio_subprocess_exec_reg"),
    ("chr(99); asyncio.create_subprocess_shell('cp x plugins/y.py')",      True, "py",    "asyncio_subprocess_shell_reg"),

    # --- Regression: prior Wave 27 cases that must still pass ---
    ("builtins.open('plugins/evil.py', 'w')",                              True, "adv024", "builtins_open_reg"),
    ("open.__call__('plugins/evil.py', 'w')",                              True, "adv024", "open_dunder_call_reg"),
    ("chr(99); tarfile.TarFile('plugins/evil.py', 'w')",                   True, "py",     "tarfile_W27_reg"),
    ("chr(99); asyncio.create_subprocess_exec('cp', 'x', 'plugins/y.py')", True, "py",   "asyncio_W27_reg"),
]
```

---

# Wave 30 Test Cases (ADV-W30)

Fixes: W29-002 (r+/rb+/rt+ update modes in subscript forms), W29-003 (__dict__ expanded to full dangerous-name list), W29-007 (__globals__['open'] dunder-globals bypass).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W30-002 | `[wax+]` (added `+`) in list/tuple-subscript, mode= kw, Path.open positional subscript | `open(p,['r+'][0])`, `open(p,mode=('r+',)[0])`, `Path(p).open(['w+'][0])` |
| ADV-W30-003 | `__dict__\s*(?:\[\|\.get\s*\().*\b(?:open\|write_text\|...\|system)\b` full name list | `Path.__dict__.get('write_text')(...)`, `type(p).__dict__['rename'](...)` |
| ADV-W30-007 | `\b__globals__\s*(?:\[\|\.get\s*\().*\bopen\b` | `(lambda:0).__globals__['open'](p,'w')`, `f.__globals__.get('open')(p,'w')` |

## Documented misses confirmed Wave 30 (do NOT re-raise)

- `functools.reduce(getattr, ['write_text'], Path('plugins/x.py'))` — call-graph semantics
- `partial(getattr, p)('write_text')`, `(getattr)(p, 'write_text')`, `[getattr][0](p, 'write_text')` — grouped/partial getattr bypass
- `getattr(Path('plugins/x.py').parent / 'y.py', 'write_text')` — Path.__truediv__ chain as positional first arg
- `[['w']][0][0]` double-nested subscript — exotic
- `open(path, dict(mode='w')['mode'])` — dict-subscript computed mode
- `(lambda:0).__globals__['write_text']` — __globals__ only gates 'open'; other names require runtime tracking

## Cases

```python
cases_w30 = [
    # --- ADV-W30-002: r+/rb+/rt+ update modes in subscript forms ---
    ("open('plugins/evil.py',['r+'][0])",                                  True, "adv024", "open_list_sub_rplus"),
    ("open('plugins/evil.py',('r+',)[0])",                                 True, "adv024", "open_tuple_sub_rplus"),
    ("open('plugins/evil.py',mode=['r+'][0])",                             True, "adv024", "open_mode_kw_list_rplus"),
    ("open('plugins/evil.py',mode=('r+',)[0])",                            True, "adv024", "open_mode_kw_tuple_rplus"),
    ("Path('plugins/evil.py').open(['r+'][0])",                            True, "adv024", "path_open_list_rplus"),
    ("Path('plugins/evil.py').open(['w+'][0])",                            True, "adv024", "path_open_list_wplus"),
    # read-only subscript must ALLOW
    ("open('plugins/evil.py',['rb'][0])",                                  False, "adv024", "open_list_sub_rb_FP"),
    ("Path('plugins/evil.py').open(['rb'][0])",                            False, "adv024", "path_open_rb_FP"),

    # --- ADV-W30-003: __dict__ expanded dangerous-name list ---
    ("Path.__dict__.get('write_text')(Path('plugins/evil.py'),'x')",       True, "adv024", "dict_get_write_text"),
    ("Path.__dict__['rename'](Path('plugins/evil.py'),'x')",               True, "adv024", "dict_subscript_rename"),
    ("type(Path('plugins/evil.py')).__dict__.get('write_text')('x')",      True, "adv024", "type_dict_get_write_text"),
    ("Path.__dict__['unlink'](Path('plugins/evil.py'))",                   True, "adv024", "dict_subscript_unlink"),
    ("Path.__dict__['rmtree'](Path('plugins/evil.py'))",                   True, "adv024", "dict_subscript_rmtree"),
    # read method must ALLOW
    ("Path.__dict__.get('read_text')(Path('plugins/evil.py'))",            False, "adv024", "dict_read_text_FP"),
    # __dict__['open'] regression
    ("__dict__['open']('plugins/evil.py','w')",                            True, "adv024", "dict_subscript_open_reg"),
    ("p.__dict__.get('open')('plugins/evil.py','w')",                      True, "adv024", "dict_get_open_reg"),

    # --- ADV-W30-007: __globals__ bypass ---
    ("(lambda:0).__globals__['open']('plugins/evil.py','w')",              True, "adv024", "globals_dunder_subscript"),
    ("(lambda:0).__globals__.get('open')('plugins/evil.py','w')",          True, "adv024", "globals_dunder_get"),
    ("f.__globals__['open']('plugins/evil.py','w')",                       True, "adv024", "func_globals_subscript"),
    # documented miss: __globals__['write_text'] (not 'open') must ALLOW
    # ("(lambda:0).__globals__['write_text']",                             False, "adv024", "globals_write_text_miss"),

    # Regression: prior Wave 29 patterns still pass
    ("open('plugins/evil.py',('w',)[0])",                                  True, "adv024", "open_tuple_sub_w_reg"),
    ("getattr(Path('plugins/evil.py'), name='write_text')",                True, "adv024", "getattr_path_name_kw_reg"),
    ("Path('plugins/evil.py').__getattribute__('write_text')",             True, "adv024", "dunder_getattribute_reg"),
    ("globals()['open']('plugins/evil.py','w')",                           True, "adv024", "globals_subscript_reg"),
    ("open('plugins/evil.py','w')",                                        True, "adv024", "open_baseline_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
]
```

---

# Wave 31 Test Cases (ADV-W31)

Fixes: W30-001 (open(*['r+']) star-unpack + **{'mode':'r+'} dict-unpack update modes), W30-003 (vars(cls)['write_text'] one-arg form), W30-005 (__dict__ name list += FileIO/touch/symlink_to/hardlink_to/symlink/popen/execv/copyfile), W30-006 (operator.getitem / operator.itemgetter).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W31-001 | `[wax+]` (added +) in open star-unpack and dict-unpack patterns | `open(p,*['r+'])`, `open(p,*('r+',))`, `open(p,**{'mode':'r+'})` |
| ADV-W31-003 | `vars/globals/locals([^)]+)\s*(?:\[|\.get\s*\().*\b<dangerous>\b` one-arg form | `vars(Path)['write_text']`, `vars(io).get('FileIO')(...)` |
| ADV-W31-005 | `__dict__` name list += FileIO/touch/symlink_to/hardlink_to/symlink/popen/execv/copyfile | `io.__dict__.get('FileIO')(...)`, `Path.__dict__['symlink_to'](...)` |
| ADV-W31-006 | `operator\.(?:getitem\|itemgetter)\s*\(` | `operator.getitem(d,'write_text')`, `operator.itemgetter('write_text')(d)` |

## Documented misses confirmed Wave 31 (do NOT re-raise)

- `__dict__.__getitem__('write_text')` / `__globals__.__getitem__('open')` — method-call form of `[]`; requires detecting `.` + `__getitem__` chained on `__dict__`/`__globals__` (W30-002)
- `inspect.getattr_static` / `inspect.getmembers` — stdlib-level bypass; exploiting still returns descriptor, not bound method (W30-004)
- `(lambda:0).__globals__['write_text']` — `__globals__` only gates 'open'; other names via `__globals__` require runtime tracking (W30 partial miss, not fixed)
- All prior documented misses from Waves 25–30 carry forward

## Cases

```python
cases_w31 = [
    # --- ADV-W31-001: r+ in star-unpack and dict-unpack ---
    ("open('plugins/evil.py',*['r+'])",                                    True, "adv024", "open_star_list_rplus"),
    ("open('plugins/evil.py',*('r+',))",                                   True, "adv024", "open_star_tuple_rplus"),
    ("open('plugins/evil.py',**{'mode':'r+'})",                            True, "adv024", "open_dictunpack_rplus"),
    ("open('plugins/evil.py',*['w+'])",                                    True, "adv024", "open_star_list_wplus"),
    # read-only star-unpack must ALLOW
    ("open('plugins/evil.py',*['rb'])",                                    False, "adv024", "open_star_rb_FP"),

    # --- ADV-W31-003: vars(cls)[dangerous] one-arg form ---
    ("vars(Path)['write_text']  # plugins/x.py",                           True, "adv024", "vars_class_write_text"),
    ("vars(io).get('FileIO')('plugins/evil.py','w')",                      True, "adv024", "vars_io_fileio"),
    # safe attr must ALLOW
    ("vars(Path)['__name__']",                                             False, "adv024", "vars_class_safe_FP"),

    # --- ADV-W31-005: __dict__ extended name list ---
    ("io.__dict__.get('FileIO')('plugins/evil.py','w')",                   True, "adv024", "dict_get_fileio"),
    ("Path.__dict__['symlink_to'](Path('plugins/evil.py'),'x')",           True, "adv024", "dict_subscript_symlink_to"),
    ("os.__dict__.get('popen')('plugins/evil.py','w')",                    True, "adv024", "dict_get_popen"),
    # safe attr must ALLOW
    ("os.__dict__.get('getcwd')()",                                        False, "adv024", "dict_getcwd_FP"),

    # --- ADV-W31-006: operator.getitem / operator.itemgetter ---
    ("import operator; operator.getitem(Path.__dict__,'write_text')  # plugins/x.py",
                                                                           True, "adv024", "operator_getitem"),
    ("operator.itemgetter('write_text')(Path.__dict__)  # plugins/x.py",   True, "adv024", "operator_itemgetter"),

    # Regression: prior Wave 30 patterns still pass
    ("(lambda:0).__globals__['open']('plugins/evil.py','w')",              True, "adv024", "globals_dunder_reg"),
    ("open('plugins/evil.py',['r+'][0])",                                  True, "adv024", "open_list_sub_rplus_reg"),
    ("Path.__dict__.get('write_text')(Path('plugins/evil.py'),'x')",       True, "adv024", "dict_write_text_reg"),
    ("globals()['open']('plugins/evil.py','w')",                           True, "adv024", "globals_open_reg"),
    ("open('plugins/evil.py','w')",                                        True, "adv024", "open_baseline_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
]
```

---

# Wave 32 Test Cases (ADV-W32)

Fixes: W31-001 (vars()/dict name list += symlink_to/hardlink_to), W31-002 (__dict__/vars() name list += link/run/check_output/check_call/call/chmod), W31-003 (dot-whitespace bypass via blanket module\s*\.\s*func catch-all), W31-004 (type(open).__call__ / open.__class__.__call__ meta-class call bypass).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W32-001 | vars/dict name list += `symlink_to\|hardlink_to` | `vars(Path)['symlink_to']  # plugins/x.py` |
| ADV-W32-002 | vars/dict name list += `link\|run\|check_output\|check_call\|call\|chmod` | `os.__dict__.get('link')(...)  # plugins/` |
| ADV-W32-003 | `(?:os\|subprocess\|shutil\|operator\|pathlib)\s*\.\s*(?:system\|run\|...)\s*\(` blanket dot-whitespace | `os .system('cmd')  # plugins/x.py` |
| ADV-W32-004 | `(?:type\s*\(open\)\|open\.__class__)\s*\.__call__\s*\(` | `type(open).__call__(open,'plugins/x.py','w')` |

## Documented misses confirmed Wave 32 (do NOT re-raise)

- All prior documented misses from Waves 25–31 carry forward
- `subprocess .run(...)` with 3+ whitespace chars — blanket pattern uses `\s*` which covers any count; no known bypass
- `type(int).__call__(int, 5)` with no HR token — must ALLOW (no HR token present)

## Cases

```python
cases_w32 = [
    # --- ADV-W32-001: vars()/dict name list += symlink_to/hardlink_to ---
    ("vars(Path)['symlink_to']  # plugins/x.py",                           True, "adv024", "vars_class_symlink_to"),
    ("vars(Path)['hardlink_to']  # plugins/x.py",                          True, "adv024", "vars_class_hardlink_to"),
    ("os.__dict__.get('symlink_to')('plugins/evil.py','x')",               True, "adv024", "dict_get_symlink_to"),
    ("os.__dict__['hardlink_to']('plugins/evil.py','x')",                  True, "adv024", "dict_sub_hardlink_to"),
    # safe attrs still ALLOW
    ("vars(Path)['__name__']",                                             False, "adv024", "vars_class_name_FP"),

    # --- ADV-W32-002: vars()/dict name list += link/run/check_output/check_call/call/chmod ---
    ("os.__dict__.get('link')('plugins/evil.py','y')",                     True, "adv024", "dict_get_link"),
    ("subprocess.__dict__['run'](['cp','a','plugins/x.py'])",              True, "adv024", "dict_sub_run"),
    ("subprocess.__dict__.get('check_call')(['cp','a','plugins/x.py'])",   True, "adv024", "dict_get_check_call"),
    ("os.__dict__['chmod']('plugins/evil.py', 0o777)",                     True, "adv024", "dict_sub_chmod"),
    # safe attrs still ALLOW
    ("os.__dict__.get('getcwd')()",                                        False, "adv024", "dict_getcwd_FP_reg"),

    # --- ADV-W32-003: dot-whitespace bypass (module .<space>func) ---
    ("os .system('cmd')  # plugins/x.py",                                  True, "adv024", "os_dot_space_system"),
    ("subprocess .run(['cp','a','plugins/x.py'])",                         True, "adv024", "subprocess_dot_space_run"),
    ("shutil .copy('a','plugins/x.py')",                                   True, "adv024", "shutil_dot_space_copy"),
    ("os.system('ls')",                                                    False, "adv024", "os_system_no_hr_FP"),

    # --- ADV-W32-004: type(open).__call__ / open.__class__.__call__ ---
    ("type(open).__call__(open,'plugins/x.py','w')",                       True, "adv024", "type_open_call"),
    ("open.__class__.__call__(open,'plugins/x.py','w')",                   True, "adv024", "open_class_call"),
    # no HR token: must ALLOW
    ("type(int).__call__(int, 5)",                                         False, "adv024", "type_int_no_hr_FP"),

    # Regression: prior Wave 31 patterns still pass
    ("open('plugins/evil.py',*['r+'])",                                    True, "adv024", "open_star_list_rplus_reg"),
    ("vars(Path)['write_text']  # plugins/x.py",                           True, "adv024", "vars_write_text_reg"),
    ("operator.getitem(Path.__dict__,'write_text')  # plugins/x.py",       True, "adv024", "operator_getitem_reg"),
    ("open('plugins/evil.py','w')",                                        True, "adv024", "open_baseline_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
]
```

---

# Wave 33 Test Cases (ADV-W33)

Fixes: W32-001 (types.BuiltinFunctionType.__call__), W32-002 (open . __call__ dot-whitespace), W32-003 (sys.modules['mod'].func), W32-004 (posix.system/remove/link/open), W32-007 ((os.remove)(...) grouped dotted primitive), W32-009 (Popen in vars/__dict__ name lists), W32-010 (sqlite3.connect, shelve.open, bz2.BZ2File/lzma.LZMAFile write-mode, dbm.open, os.mknod).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W33-001 | `types\.(?:BuiltinFunctionType\|BuiltinMethodType)\s*\.\s*__call__\s*\(` | `types.BuiltinFunctionType.__call__(open,'plugins/x.py','w')` |
| ADV-W33-002 | `\bopen\s*\.[\s]*__call__\s*\(` | `open . __call__('plugins/x.py','w')` |
| ADV-W33-003 | `sys\.modules\s*\[[^\]]*\]\s*\.[\s]*(?:open\|remove\|...)\s*\(` | `sys.modules['os'].remove('plugins/x.py')` |
| ADV-W33-004 | `posix\s*\.[\s]*(?:system\|popen\|remove\|...)\s*\(` | `posix.system('rm plugins/x.py')`, `posix.remove(...)` |
| ADV-W33-007 | `\((?:os\|subprocess\|shutil\|posix)\s*\.\s*(?:system\|run\|...)\)\s*\(` | `(os.remove)('plugins/x.py')`, `(subprocess.run)([...])` |
| ADV-W33-009 | `Popen` added to vars/__dict__ name lists | `vars(subprocess).get('Popen')([...])`, `subprocess.__dict__['Popen']([...])` |
| ADV-W33-010 | sqlite3/shelve/bz2/lzma/dbm/mknod patterns | `sqlite3.connect('plugins/x.py')`, `shelve.open(...)`, `bz2.BZ2File(...,'wb')`, etc. |

## Documented misses confirmed Wave 33 (do NOT re-raise)

- `[os.remove][0]('plugins/x.py')` — list-wrapped dotted primitive; W32-007 only covers paren form (W33-008 documented miss)
- `posix.__dict__['remove']` combined form — posix + __dict__ without the `posix.` prefix pattern
- `nt.remove(...)` — Windows-only module, not imported on Linux
- `fcntl.open(...)` — file descriptor level, not a file-path write primitive in the plugin-path sense
- `io.FileIO.__new__(io.FileIO,'plugins/x.py','w')` — __new__ bypass (same class as (io.FileIO)() grouped, W32-005)
- `os\\n.system(...)` backslash-newline continuation — tokenizer-level, regex can't see it (W32-006)
- All prior documented misses from Waves 25–32 carry forward

## Cases

```python
cases_w33 = [
    # --- ADV-W33-001: types.BuiltinFunctionType.__call__ ---
    ("types.BuiltinFunctionType.__call__(open,'plugins/x.py','w')",        True, "adv024", "types_bft_call"),
    ("types.BuiltinMethodType.__call__(open,'plugins/x.py','w')",          True, "adv024", "types_bmt_call"),
    # no HR token must ALLOW
    ("types.BuiltinFunctionType.__call__(open, 'safe.py', 'w')",           False, "adv024", "types_bft_no_hr_FP"),

    # --- ADV-W33-002: open . __call__ dot-whitespace ---
    ("open . __call__('plugins/x.py','w')",                                True, "adv024", "open_dot_space_call"),
    ("open  .  __call__('plugins/x.py','w')",                              True, "adv024", "open_dot_multi_space_call"),
    # original no-space form regression
    ("open.__call__('plugins/x.py','w')",                                  True, "adv024", "open_dunder_call_reg"),

    # --- ADV-W33-003: sys.modules['mod'].func ---
    ("sys.modules['os'].remove('plugins/x.py')",                           True, "adv024", "sysmod_os_remove"),
    ("sys.modules['builtins'].open('plugins/x.py','w')",                   True, "adv024", "sysmod_builtins_open"),
    ("sys.modules['io'].FileIO('plugins/x.py','w')",                       True, "adv024", "sysmod_io_fileio"),
    ("sys.modules['subprocess'].run(['cp','a','plugins/x.py'])",           True, "adv024", "sysmod_subprocess_run"),
    ("sys.modules['os'].system('cp src plugins/x.py')",                    True, "adv024", "sysmod_os_system"),

    # --- ADV-W33-004: posix.system/remove ---
    ("posix.system('rm plugins/x.py')",                                    True, "adv024", "posix_system"),
    ("posix.remove('plugins/x.py')",                                       True, "adv024", "posix_remove"),
    ("posix.open('plugins/x.py', os.O_WRONLY)",                            True, "adv024", "posix_open"),
    ("posix.link('a','plugins/x.py')",                                     True, "adv024", "posix_link"),

    # --- ADV-W33-007: (os.remove)(...) grouped dotted primitive ---
    ("(os.remove)('plugins/x.py')",                                        True, "adv024", "grouped_os_remove"),
    ("(os.system)('cp src plugins/x.py')",                                 True, "adv024", "grouped_os_system"),
    ("(subprocess.run)(['cp','a','plugins/x.py'])",                        True, "adv024", "grouped_subprocess_run"),
    ("(shutil.rmtree)('plugins/x.py')",                                    True, "adv024", "grouped_shutil_rmtree"),
    # list-wrapped form: documented miss (ALLOW expected)
    ("[os.remove][0]('plugins/x.py')",                                     False, "adv024", "list_os_remove_miss"),

    # --- ADV-W33-009: Popen in vars/__dict__ lists ---
    ("vars(subprocess).get('Popen')(['rm','plugins/x.py'])",               True, "adv024", "vars_subprocess_popen"),
    ("subprocess.__dict__['Popen'](['rm','plugins/x.py'])",                True, "adv024", "dict_sub_popen"),

    # --- ADV-W33-010: stdlib file-creating constructors ---
    ("sqlite3.connect('plugins/x.py')",                                    True, "adv024", "sqlite3_connect"),
    ("shelve.open('plugins/x.py')",                                        True, "adv024", "shelve_open"),
    ("bz2.BZ2File('plugins/x.py','wb')",                                   True, "adv024", "bz2_write"),
    ("lzma.LZMAFile('plugins/x.py','wb')",                                 True, "adv024", "lzma_write"),
    ("dbm.open('plugins/x.py','n')",                                       True, "adv024", "dbm_open_create"),
    ("os.mknod('plugins/x.py')",                                           True, "adv024", "os_mknod"),
    # bz2 read-mode must ALLOW
    ("bz2.BZ2File('plugins/x.py','rb')",                                   False, "adv024", "bz2_read_FP"),

    # Regression: prior Wave 32 patterns still pass
    ("type(open).__call__(open,'plugins/x.py','w')",                       True, "adv024", "type_open_call_reg"),
    ("os .system('cmd')  # plugins/x.py",                                  True, "adv024", "os_dot_space_system_reg"),
    ("vars(Path)['symlink_to']  # plugins/x.py",                           True, "adv024", "vars_symlink_to_reg"),
    ("os.__dict__.get('link')('plugins/evil.py','y')",                     True, "adv024", "dict_link_reg"),
    ("open('plugins/x.py','w')",                                           True, "adv024", "open_baseline_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
    ("open('plugins/x.py','r')",                                           False, "adv024", "open_read_FP_reg"),
]
```

---

# Wave 34 Test Cases (ADV-W34)

Fixes: W33-001 ([os.remove][0] list-wrap), W33-002 (sys.modules.get/pop/setdefault access forms), W33-003 (getattr Popen/mknod), W33-004 (posix.mknod), W33-005 (dbm.gnu/dumb/ndbm.open), W33-006 (bz2/lzma dot-whitespace), W33-007 (types.Builtin first-dot whitespace).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W34-001 | list-wrap extended to `[os.remove][N](...)` | `[os.remove][0]('plugins/x.py')`, `[os.mknod][0](...)`, `[posix.remove][0](...)` |
| ADV-W34-002 | sys.modules `.get()` / `.pop()` / `.setdefault()` accessors | `sys.modules.get('os').remove('plugins/x.py')`, `sys.modules.pop('subprocess').run([...])` |
| ADV-W34-003 | getattr name= list += Popen, mknod | `getattr(obj, name='Popen')([...])`, `getattr(obj, name='mknod')('plugins/x.py')` |
| ADV-W34-004 | posix pattern += mknod | `posix.mknod('plugins/x.py')`, `posix . mknod('plugins/x.py')` |
| ADV-W34-005 | dbm.gnu.open / dbm.dumb.open / dbm.ndbm.open | `dbm.gnu.open('plugins/x.py','n')`, `dbm.dumb.open('plugins/x.py','c')` |
| ADV-W34-006 | bz2\s*\.\s*BZ2File, lzma\s*\.\s*LZMAFile (dot-whitespace) | `bz2 . BZ2File('plugins/x.py','wb')`, `lzma . LZMAFile('plugins/x.py','wb')` |
| ADV-W34-007 | types\s*\.\s*(?:BuiltinFunctionType\|BuiltinMethodType) (first-dot whitespace) | `types . BuiltinFunctionType.__call__(open,'plugins/x.py','w')` |

## Documented misses confirmed Wave 34 (do NOT re-raise)

- `sys.modules['os'].__dict__['remove']('plugins/x.py')` — sys.modules + __dict__ combo; W32-003 stops at function-call level (W34 candidate if re-found)
- `getattr(sys.modules['os'],'remove')('plugins/x.py')` — getattr + sys.modules without name= keyword; positional getattr pattern may or may not catch depending on first-arg walker depth
- `(sqlite3.connect)('plugins/x.py')` / `[sqlite3.connect][0](...)` — paren/list-wrap for W32-010 stdlib constructor names not included in grouped pattern
- `(bz2.BZ2File)('plugins/x.py','wb')` — paren-grouped constructor bypass for bz2
- `sys.modules.get('bz2').BZ2File('plugins/x.py','wb')` — sys.modules + bz2 constructor chain
- `dbm.gnu . open('plugins/x.py','n')` — dot-whitespace inside dbm.gnu.open (three-dot chain)
- All prior documented misses from Waves 25–33 carry forward

## Cases

```python
cases_w34 = [
    # --- ADV-W34-001: [os.remove][0] list-wrap ---
    ("[os.remove][0]('plugins/x.py')",                                     True, "adv024", "list_os_remove_0"),
    ("[os.system][0]('echo x > plugins/x.py')",                            True, "adv024", "list_os_system_0"),
    ("[subprocess.run][0](['cp','a','plugins/x.py'])",                     True, "adv024", "list_subprocess_run_0"),
    ("[os.remove][-1]('plugins/x.py')",                                    True, "adv024", "list_os_remove_neg1"),
    ("[os.mknod][0]('plugins/x.py')",                                      True, "adv024", "list_os_mknod_0"),
    ("[posix.remove][0]('plugins/x.py')",                                  True, "adv024", "list_posix_remove_0"),
    # paren-grouped form must still BLOCK (regression)
    ("(os.remove)('plugins/x.py')",                                        True, "adv024", "paren_os_remove_reg"),

    # --- ADV-W34-002: sys.modules.get/pop/setdefault ---
    ("sys.modules.get('os').remove('plugins/x.py')",                       True, "adv024", "sysmod_get_os_remove"),
    ("sys.modules.get('posix').remove('plugins/x.py')",                    True, "adv024", "sysmod_get_posix_remove"),
    ("sys.modules.get('subprocess').run(['cp','a','plugins/x.py'])",       True, "adv024", "sysmod_get_subprocess_run"),
    # subscript form must still BLOCK (regression)
    ("sys.modules['os'].remove('plugins/x.py')",                           True, "adv024", "sysmod_subscript_reg"),

    # --- ADV-W34-004: posix.mknod dot-whitespace ---
    ("posix.mknod('plugins/x.py')",                                        True, "adv024", "posix_mknod"),
    ("posix . mknod('plugins/x.py')",                                      True, "adv024", "posix_mknod_dot_space"),

    # --- ADV-W34-005: dbm.gnu/dumb/ndbm.open ---
    ("dbm.gnu.open('plugins/x.py','n')",                                   True, "adv024", "dbm_gnu_open_create"),
    ("dbm.dumb.open('plugins/x.py','c')",                                  True, "adv024", "dbm_dumb_open_create"),
    # dbm.gnu read mode must ALLOW
    ("dbm.gnu.open('plugins/x.py','r')",                                   False, "adv024", "dbm_gnu_read_FP"),
    # top-level dbm.open regression
    ("dbm.open('plugins/x.py','n')",                                       True, "adv024", "dbm_top_open_reg"),

    # --- ADV-W34-006: bz2/lzma dot-whitespace ---
    ("bz2 . BZ2File('plugins/x.py','wb')",                                 True, "adv024", "bz2_dot_space_wb"),
    ("lzma . LZMAFile('plugins/x.py','wb')",                               True, "adv024", "lzma_dot_space_wb"),
    # bz2 read-mode dot-whitespace must ALLOW
    ("bz2 . BZ2File('plugins/x.py','rb')",                                 False, "adv024", "bz2_dot_space_rb_FP"),
    # no-space form must still BLOCK (regression)
    ("bz2.BZ2File('plugins/x.py','wb')",                                   True, "adv024", "bz2_nospace_reg"),

    # --- ADV-W34-007: types.Builtin first-dot whitespace ---
    ("types . BuiltinFunctionType.__call__(open,'plugins/x.py','w')",      True, "adv024", "types_dot_space_bft_call"),
    ("types . BuiltinMethodType.__call__(open,'plugins/x.py','w')",        True, "adv024", "types_dot_space_bmt_call"),
    # no-space form must still BLOCK (regression)
    ("types.BuiltinFunctionType.__call__(open,'plugins/x.py','w')",        True, "adv024", "types_bft_call_reg"),

    # Regression: prior Wave 33 patterns still pass
    ("open('plugins/x.py','w')",                                           True, "adv024", "open_baseline_reg"),
    ("os.remove('plugins/x.py')",                                          True, "adv024", "os_remove_reg"),
    ("posix.remove('plugins/x.py')",                                       True, "adv024", "posix_remove_reg"),
    ("sqlite3.connect('plugins/x.py')",                                    True, "adv024", "sqlite3_connect_reg"),
    ("shelve.open('plugins/x.py')",                                        True, "adv024", "shelve_open_reg"),
    ("bz2.BZ2File('plugins/x.py','wb')",                                   True, "adv024", "bz2_write_reg"),
    ("os.mknod('plugins/x.py')",                                           True, "adv024", "os_mknod_reg"),
    ("type(open).__call__(open,'plugins/x.py','w')",                       True, "adv024", "type_open_call_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
    ("open('plugins/x.py','r')",                                           False, "adv024", "open_read_FP_reg"),
]
```

---

# Wave 35 Test Cases (ADV-W35)

Fixes: W34-001 ([os.mknod][0] + mknod in paren-wrap), W34-002 ([sqlite3.connect][0] / (sqlite3.connect)() paren+list wrap for W32-010 constructors), W34-003 (sys.modules method alternation += connect/BZ2File/LZMAFile/GzipFile), W34-004 (getattr positional name list += mknod/Popen/connect/BZ2File/LZMAFile via hex-escaped quotes), W34-005 (inner-bracket whitespace in list-wrap `[ os.remove ][0]`), W34-006 (vars()/getattr() name list += mknod).

## New pattern coverage

| ID | Pattern added / changed | Triggers on |
|---|---|---|
| ADV-W35-001 | paren-wrap + list-wrap extended with mknod/openat/unlinkat | `[os.mknod][0]('plugins/x.py')`, `(os.mknod)('plugins/x.py')` |
| ADV-W35-002 | `(sqlite3.connect)(...)` / `[sqlite3.connect][0](...)` paren+list for W32-010 names | `(sqlite3.connect)('plugins/x.py')`, `[shelve.open][0]('plugins/x.py')` |
| ADV-W35-003 | sys.modules method alternation += connect/BZ2File/LZMAFile/GzipFile | `sys.modules.get('sqlite3').connect('plugins/x.py')` |
| ADV-W35-004 | getattr positional name list += mknod/Popen/connect/BZ2File/LZMAFile (hex-escaped quote in raw string) | `getattr(obj, 'mknod')('plugins/x.py')`, `getattr(obj, 'connect')('plugins/x.py')` |
| ADV-W35-005 | `\s*` inside list-wrap brackets for `[ os.remove ][0]` inner-whitespace | `[ os.remove ][0]('plugins/x.py')`, `[os.remove ][-1](...)` |
| ADV-W35-006 | vars() / `__dict__` / getattr name lists += mknod | `vars(os)['mknod']('plugins/x.py')`, `os.__dict__.get('mknod')('plugins/x.py')` |

## Documented misses confirmed Wave 35 (do NOT re-raise)

- `(types.BuiltinFunctionType.__call__)(...)` — paren/list-wrap of arbitrary dotted dunder chains; same class as W32-005 (io.FileIO grouped) and W29-006 (partial). Requires infinite name list or AST-level analysis. Accept.
- All prior documented misses from Waves 25–34 carry forward.

## Key implementation note: hex-escaped quotes in raw strings

When adding name alternations inside raw-string regex patterns (e.g. `r'...'`) that must match both `'name'` and `"name"` quote forms, use `[\x27\x22]` (hex escapes for `'` and `"`) NOT `['"]` (which terminates the raw string early if the delimiter is `'`). Verify by inspecting the compiled `.pattern` attribute — a misparse produces a truncated or wrong alternation without a `compile()` error.

## Cases

```python
cases_w35 = [
    # --- ADV-W35-001: [os.mknod][0] and (os.mknod)() ---
    ("[os.mknod][0]('plugins/x.py')",                                      True, "adv024", "list_os_mknod_0"),
    ("(os.mknod)('plugins/x.py')",                                         True, "adv024", "paren_os_mknod"),
    ("[os.openat][0](dirfd,'plugins/x.py',flags)",                         True, "adv024", "list_os_openat_0"),
    ("[os.unlinkat][0](dirfd,'plugins/x.py')",                             True, "adv024", "list_os_unlinkat_0"),
    # prior mknod form (W33) must still BLOCK
    ("os.mknod('plugins/x.py')",                                           True, "adv024", "os_mknod_reg"),

    # --- ADV-W35-002: (sqlite3.connect)() / [sqlite3.connect][0]() paren+list ---
    ("(sqlite3.connect)('plugins/x.py')",                                  True, "adv024", "paren_sqlite3_connect"),
    ("[sqlite3.connect][0]('plugins/x.py')",                               True, "adv024", "list_sqlite3_connect_0"),
    ("(shelve.open)('plugins/x.py')",                                      True, "adv024", "paren_shelve_open"),
    ("[bz2.BZ2File][0]('plugins/x.py','wb')",                              True, "adv024", "list_bz2_BZ2File_0"),
    ("(lzma.LZMAFile)('plugins/x.py','wb')",                               True, "adv024", "paren_lzma_LZMAFile"),
    # plain form regression
    ("sqlite3.connect('plugins/x.py')",                                    True, "adv024", "sqlite3_connect_reg"),
    ("bz2.BZ2File('plugins/x.py','wb')",                                   True, "adv024", "bz2_write_reg"),

    # --- ADV-W35-003: sys.modules.get('sqlite3').connect() ---
    ("sys.modules.get('sqlite3').connect('plugins/x.py')",                 True, "adv024", "sysmod_get_sqlite3_connect"),
    ("sys.modules['bz2'].BZ2File('plugins/x.py','wb')",                    True, "adv024", "sysmod_sub_bz2_BZ2File"),
    ("sys.modules.get('lzma').LZMAFile('plugins/x.py','wb')",              True, "adv024", "sysmod_get_lzma_LZMAFile"),
    # sys.modules + os.remove regression
    ("sys.modules['os'].remove('plugins/x.py')",                           True, "adv024", "sysmod_os_remove_reg"),

    # --- ADV-W35-004: getattr positional += mknod/Popen/connect/BZ2File ---
    ("getattr(os, 'mknod')('plugins/x.py')",                              True, "adv024", "getattr_pos_mknod"),
    ("getattr(subprocess, 'Popen')(['rm','plugins/x.py'])",                True, "adv024", "getattr_pos_popen"),
    ("getattr(sqlite3, 'connect')('plugins/x.py')",                        True, "adv024", "getattr_pos_connect"),
    ("getattr(bz2, 'BZ2File')('plugins/x.py','wb')",                       True, "adv024", "getattr_pos_bz2file"),
    # safe method via positional still ALLOWS
    ("getattr(obj, 'read_text')('plugins/x.py')",                          False, "adv024", "getattr_pos_read_FP"),

    # --- ADV-W35-005: [ os.remove ] (inner whitespace) ---
    ("[ os.remove][0]('plugins/x.py')",                                    True, "adv024", "list_os_remove_lead_space"),
    ("[os.remove ][0]('plugins/x.py')",                                    True, "adv024", "list_os_remove_trail_space"),
    ("[ os.remove ][-1]('plugins/x.py')",                                  True, "adv024", "list_os_remove_both_space"),
    # no-space form regression
    ("[os.remove][0]('plugins/x.py')",                                     True, "adv024", "list_os_remove_0_reg"),

    # --- ADV-W35-006: vars()/getattr() + mknod ---
    ("vars(os)['mknod']('plugins/x.py')",                                  True, "adv024", "vars_os_mknod"),
    ("os.__dict__.get('mknod')('plugins/x.py')",                           True, "adv024", "dict_get_mknod"),
    # safe attrs still ALLOW
    ("vars(Path)['__name__']",                                             False, "adv024", "vars_name_FP_reg"),
    ("os.__dict__.get('getcwd')()",                                        False, "adv024", "dict_getcwd_FP_reg"),

    # Regression: prior Wave 34 patterns still pass
    ("[os.remove][0]('plugins/x.py')",                                     True, "adv024", "list_os_remove_reg"),
    ("sys.modules.get('os').remove('plugins/x.py')",                       True, "adv024", "sysmod_get_os_remove_reg"),
    ("bz2 . BZ2File('plugins/x.py','wb')",                                 True, "adv024", "bz2_dot_space_wb_reg"),
    ("types . BuiltinFunctionType.__call__(open,'plugins/x.py','w')",      True, "adv024", "types_dot_space_reg"),
    ("open('plugins/x.py','w')",                                           True, "adv024", "open_baseline_reg"),
    ("open('plugins/x.py','r')",                                           False, "adv024", "open_read_FP_reg"),
    ("list.remove(x)",                                                     False, "adv024", "list_remove_FP_reg"),
]
```

## How to run

```python
import importlib.util, re
spec = importlib.util.spec_from_file_location(
    "gov",
    "/var/home/rainbow/.hermes/profiles/fork/plugins/governance-hard-block/__init__.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

F = []
for blob, want, ctx, label in cases_w28:
    result = mod.evaluate_write('execute_code', {'code': blob})
    fired = result is not None and result.get('action') == 'block'
    if fired != want:
        F.append(f'{label}: fired={fired} want={want}')
print(f'{len(cases_w28)-len(F)}/{len(cases_w28)} OK')
for x in F:
    print(f'  FAIL {x}')
```

---

# Wave 36 Test Cases (ADV-W36)

Fixes: W35-001 (gzip/builtins/io/tarfile/bz2/lzma/codecs/wave .open paren+list wrap), W35-002 (dbm.sqlite3.open dotted+paren+list), W35-004 (fileinput mode='w'/'a'/'wb' without inplace), W35-005 (zipfile.ZipFile/tarfile.TarFile paren+list), W35-006 (path.open grouped paren-wrap), W35-007 (shelve.DbfilenameShelf bare constructor). W35-003 documented miss (paren/list wrap of arbitrary dotted dunder chains).

## New pattern coverage

| ID | Pattern added | Triggers on |
|---|---|---|
| ADV-W36-001 | `(?:gzip\|builtins\|io\|bz2\|lzma\|codecs\|wave\|tarfile)\.open` paren+list | `(gzip.open)('plugins/x.py','wb')`, `[io.open][0]('plugins/x.py','w')` |
| ADV-W36-002 | `dbm\.sqlite3\.open` dotted+paren+list | `dbm.sqlite3.open('plugins/x.py','n')`, `(dbm.sqlite3.open)('plugins/x.py','n')` |
| ADV-W36-004 | `fileinput\.(?:input\|FileInput)\s*\(.*mode\s*=\s*['"][waxr][^'"]*['"]` | `fileinput.input(files='x.py',mode='w')` |
| ADV-W36-005 | `zipfile\.(?:ZipFile\|PyZipFile)` and `tarfile\.TarFile` paren+list | `(zipfile.ZipFile)('plugins/x.py','w')`, `[tarfile.TarFile][0]('plugins/x.py','w')` |
| ADV-W36-006 | `(path_expr\.open)('w')` grouped method paren-wrap | `(pathlib.Path('x.py').open)('w')`, `(Path('x.py').open)('w')` |
| ADV-W36-007 | `shelve\.DbfilenameShelf\s*\(` bare constructor | `shelve.DbfilenameShelf('plugins/x.py')` |

## Documented misses confirmed Wave 36 (do NOT re-raise)

- `(types.BuiltinFunctionType.__call__)(...)` — paren/list-wrap of arbitrary dotted dunder chains; requires infinite name list or AST.

## Cases (sample)

```python
cases_w36_sample = [
    ("(gzip.open)('plugins/x.py','wb')",                         True, "adv024", "paren_gzip_open"),
    ("[io.open][0]('plugins/x.py','w')",                         True, "adv024", "list_io_open"),
    ("(codecs.open)('plugins/x.py','w')",                        True, "adv024", "paren_codecs_open"),
    ("[wave.open][0]('plugins/x.py','wb')",                      True, "adv024", "list_wave_open"),
    ("dbm.sqlite3.open('plugins/x.py','n')",                     True, "adv024", "dbm_sqlite3_open"),
    ("(dbm.sqlite3.open)('plugins/x.py','n')",                   True, "adv024", "paren_dbm_sqlite3_open"),
    ("fileinput.input(files='x.py',mode='w')",                   True, "adv024", "fileinput_mode_w"),
    ("fileinput.FileInput(files='x.py',mode='a')",               True, "adv024", "fileinput_mode_a"),
    ("(zipfile.ZipFile)('plugins/x.py','w')",                    True, "adv024", "paren_zipfile_ZipFile"),
    ("[tarfile.TarFile][0]('plugins/x.py','w')",                 True, "adv024", "list_tarfile_TarFile"),
    ("(pathlib.Path('plugins/x.py').open)('w')",                 True, "adv024", "paren_path_open"),
    ("shelve.DbfilenameShelf('plugins/x.py')",                   True, "adv024", "shelve_dbfilenameShelf"),
]
```

---

# Wave 37 Test Cases (ADV-W37)

Fixes: W36-001 (ZipFile/TarFile/PyZipFile/DbfilenameShelf to getattr/vars/__dict__/sys.modules lists), W36-002 ([path.open][0] list-wrap), W36-004 (fileinput mode= nested-paren safe `(?:[^()]|\([^)]*\))*`), W36-005 (fileinput mode charset `[waxr][btw+]{0,3}`), W36-006 ((fileinput.input) paren/list-wrap), W36-007 (PyZipFile in all zipfile patterns), W36-008 ((TarFile.open) classmethod wrap). W36-003 documented miss (variable-bound method reference).

## New pattern coverage

| ID | Pattern added | Triggers on |
|---|---|---|
| ADV-W37-001 | getattr/vars/__dict__/sys.modules name lists += ZipFile/TarFile/PyZipFile/DbfilenameShelf | `getattr(zipfile,'ZipFile')('plugins/x.py','w')` |
| ADV-W37-002 | `[path.open][0]('w')` list-wrap | `[Path('plugins/x.py').open][0]('w')` |
| ADV-W37-004 | fileinput mode= uses `(?:[^()]\|\([^)]*\))*` | `fileinput.input(('x.py'),mode='w')` |
| ADV-W37-005 | fileinput mode charset `[waxr][btw+]{0,3}` | `fileinput.input(files='x.py',mode='wt')`, `mode='r+b'` |
| ADV-W37-006 | `(fileinput.input)(...)` / `[fileinput.input][0](...)` | grouped fileinput call bypasses mode gate |
| ADV-W37-007 | `zipfile.PyZipFile` in all zipfile patterns | `(zipfile.PyZipFile)('plugins/x.py','w')` |
| ADV-W37-008 | `(tarfile.TarFile.open)(...)` / `[tarfile.TarFile.open][0](...)` | classmethod wrap bypass |

## Documented misses confirmed Wave 37 (do NOT re-raise)

- `(p.write_text)('x')` where p is a variable — variable-bound method reference; requires assignment tracking.

## Cases (sample)

```python
cases_w37_sample = [
    ("getattr(zipfile,'ZipFile')('plugins/x.py','w')",              True, "adv024", "getattr_pos_ZipFile"),
    ("getattr(tarfile,'TarFile')('plugins/x.py','w')",              True, "adv024", "getattr_pos_TarFile"),
    ("vars(zipfile)['ZipFile']('plugins/x.py','w')",                True, "adv024", "vars_ZipFile"),
    ("sys.modules['zipfile'].ZipFile('plugins/x.py','w')",          True, "adv024", "sysmod_ZipFile"),
    ("[Path('plugins/x.py').open][0]('w')",                         True, "adv024", "list_path_open"),
    ("fileinput.input(('x.py'),mode='w')",                          True, "adv024", "fileinput_nested_paren_mode"),
    ("fileinput.input(files='x.py',mode='wt')",                     True, "adv024", "fileinput_mode_wt"),
    ("fileinput.input(files='x.py',mode='r+b')",                    True, "adv024", "fileinput_mode_rplusb"),
    ("(fileinput.input)(files='x.py',mode='w')",                    True, "adv024", "paren_fileinput_input"),
    ("[fileinput.input][0](files='x.py',mode='w')",                 True, "adv024", "list_fileinput_input"),
    ("zipfile.PyZipFile('plugins/x.py','w')",                       True, "adv024", "zipfile_PyZipFile_direct"),
    ("(zipfile.PyZipFile)('plugins/x.py','w')",                     True, "adv024", "paren_zipfile_PyZipFile"),
    ("(tarfile.TarFile.open)('plugins/x.py','w:gz')",               True, "adv024", "paren_TarFile_open"),
    ("[tarfile.TarFile.open][0]('plugins/x.py','w:gz')",            True, "adv024", "list_TarFile_open"),
]
```

---

# Wave 38 Test Cases (ADV-W38)

Fixes: W37-001 (getattr(name=...) keyword form extended for ZipFile/TarFile/PyZipFile/DbfilenameShelf/GzipFile/mknod/Popen/connect/BZ2File/LZMAFile/FileIO), W37-002 (tarfile.TarFile.open ungrouped classmethod in tarfile primary pattern), W37-003 (dot-whitespace `\s*\.\s*` in zipfile/gzip/tarfile/fileinput all contexts), W37-004 (fileinput two-level nested paren), W37-006 (gzip.GzipFile mode `[wax]b?t?`). W37-005 documented miss (computed mode chr(119)/['w'][0]).

## New pattern coverage

| ID | Pattern added | Triggers on |
|---|---|---|
| ADV-W38-001 | getattr(name=...) keyword form name list += ZipFile/TarFile/PyZipFile/DbfilenameShelf/GzipFile/BZ2File/LZMAFile/FileIO/mknod/Popen/connect | `getattr(name='ZipFile', object=zipfile)('plugins/x.py','w')` |
| ADV-W38-002 | `tarfile\.\s*TarFile\s*\.\s*open` ungrouped classmethod in primary tarfile pattern | `tarfile.TarFile.open('plugins/x.py','w:gz')` |
| ADV-W38-003 | `\s*\.\s*` dot-whitespace in zipfile.ZipFile/PyZipFile/Path, gzip.GzipFile/open, tarfile.open/TarFile, fileinput.input/FileInput | `zipfile .ZipFile('plugins/x.py','w')`, `tarfile .TarFile('plugins/x.py','w')` |
| ADV-W38-004 | fileinput two-level nested paren: `(?:[^()]\|\((?:[^()]\|\([^)]*\))*\))*` | `fileinput.input(('x.py'),mode='w')` at depth=2 |
| ADV-W38-006 | gzip.GzipFile mode `[wax]b?t?` | `gzip.GzipFile('plugins/x.py','x')`, `gzip.GzipFile('plugins/x.py','xb')` |

## Documented misses confirmed Wave 38 (do NOT re-raise)

- `chr(119)` / `['w'][0]` computed modes on fileinput/ZipFile — same class as W27-005; requires runtime/AST analysis.

## Cases (sample)

```python
cases_w38_sample = [
    ("getattr(name='ZipFile', object=zipfile)('plugins/x.py','w')", True, "adv024", "getattr_name_kw_ZipFile"),
    ("getattr(name='TarFile', object=tarfile)('plugins/x.py','w')", True, "adv024", "getattr_name_kw_TarFile"),
    ("getattr(name='GzipFile', object=gzip)('plugins/x.py','wb')",  True, "adv024", "getattr_name_kw_GzipFile"),
    ("tarfile.TarFile.open('plugins/x.py','w:gz')",                 True, "adv024", "tarfile_TarFile_open_direct"),
    ("tarfile.TarFile.open('plugins/x.py','w:xz')",                 True, "adv024", "tarfile_TarFile_open_xz"),
    ("tarfile.TarFile.open('plugins/x.py','a:bz2')",                True, "adv024", "tarfile_TarFile_open_abz2"),
    ("zipfile .ZipFile('plugins/x.py','w')",                        True, "adv024", "zipfile_dot_space_ZipFile"),
    ("tarfile .TarFile('plugins/x.py','w')",                        True, "adv024", "tarfile_dot_space_TarFile"),
    ("gzip .GzipFile('plugins/x.py','w')",                          True, "adv024", "gzip_dot_space_GzipFile"),
    ("fileinput .input(files='x.py',mode='w')",                     True, "adv024", "fileinput_dot_space"),
    ("fileinput.input(('x.py'),mode='w')",                          True, "adv024", "fileinput_two_level_paren"),
    ("gzip.GzipFile('plugins/x.py','x')",                           True, "adv024", "gzip_GzipFile_x_mode"),
    ("gzip.GzipFile('plugins/x.py','xb')",                          True, "adv024", "gzip_GzipFile_xb_mode"),
    ("gzip.GzipFile('plugins/x.py','r')",                           False, "adv024", "gzip_GzipFile_r_FP"),
]
```
