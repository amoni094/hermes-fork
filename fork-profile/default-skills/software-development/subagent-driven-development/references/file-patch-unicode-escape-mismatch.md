# Pitfall: Unicode Escape Byte-Mismatch When Patching Python Files

## Symptom

`patch` tool or `str.replace()` in `execute_code` reports "NOT FOUND" or "MISS"
even though the target string is visually present in the file.

## Root Cause

Python source files written by a subagent (or any tool that serialises strings)
sometimes store **literal escape sequences** rather than actual Unicode characters.
For example, a file might contain the four bytes `\u2192` (backslash u 2 1 9 2)
rather than the arrow character →. When the patch tool or a Python snippet in
`execute_code` encodes the old_string through JSON/shell layers, the escape gets
decoded into a real codepoint, so the resulting bytes don't match the file.

## Diagnosis

Inspect the exact bytes before constructing a patch string:

```bash
python3 - << 'PYEOF'
import pathlib
target = "text you're trying to match"
for i, l in enumerate(pathlib.Path("file.py").read_text().splitlines(), 1):
    if target[:15] in l:
        print(i, repr(l))
PYEOF
```

If `repr()` shows `\\\\u2192` (four-char sequence), the file stores the escape.
If it shows `\\u2192` (decoded arrow), the file stores the real character.

## Fix

Construct `old_string` / `new_string` to match what the file actually contains.

- If the file uses **literal escapes** (`\\u2192`), your Python source string
  needs `\\\\u2192` (four backslashes) so that Python's string layer leaves two,
  which then match the file's `\u2192` two-char sequence.
- Use a terminal heredoc with `<< 'PYEOF'` (single-quoted) to suppress shell
  interpolation, then do `str.replace()` directly in Python:

```bash
python3 - << 'PYEOF'
path = "/path/to/file.py"
with open(path) as f:
    src = f.read()

old = 'text(mx, PH - 74, "Matrix logic  (if x \\u2192 then y)", size=12'
new = 'text(mx, PH - 74, "Matrix logic  (if x \\u2192 then y)", size=11'

if old in src:
    src = src.replace(old, new, 1)
    print("OK")
else:
    print("MISS — check repr of file bytes")

with open(path, "w") as f:
    f.write(src)
PYEOF
```

Always run a `repr()` check first if the first patch attempt misses. Do not
assume the match is correct because the visual string looks right.
