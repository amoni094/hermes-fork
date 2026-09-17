# Python pyc Interpreter Mismatch — Diagnosis and Fix

## Symptom
`ImportError: bad magic number in '<module>': b'+\x0e\r\n'`
Script runs fine when called directly but fails when launched by the Hermes cron runner or a daemon.

## Root cause
The Hermes venv runs Python 3.11 (magic `a70d0d0a`) but the `.pyc` files were compiled for Python 3.14 (magic `2b0e0d0a`). Each minor version has a unique 4-byte magic; a mismatch causes the bytecode loader to reject the file.

## Diagnosis
```bash
# 1. Identify which Python the failing process uses
ps aux | grep hermes  # look for venv path in command

# 2. Compare versions
~/.hermes/hermes-agent/venv/bin/python3 --version
/usr/bin/python3 --version

# 3. Check pyc magic
python3 -c "print(open('path/to/file.pyc','rb').read(4).hex())"
python3 -c "import importlib.util; print(importlib.util.MAGIC_NUMBER.hex())"

# 4. Check for tiny stub overwriting real logic (wrapper recompile)
ls -lh ~/.hermes/scripts/__pycache__/l1-*.pyc         # should be ~4KB if stub
ls -lh ~/.hermes/scripts/references/*.pyc.bak          # should be 35-71KB real logic
```

## Fix — three parts

### 1. Prefer the .bak reference over __pycache__/
In any loader script with a `_PYC_CANDIDATES` list, put the `references/*.pyc.bak` path FIRST:
```python
_PYC_CANDIDATES = [
    SCRIPT_DIR / "references" / "l1-extract.cpython-314.pyc.bak",   # canonical, real logic
    SCRIPT_DIR / "__pycache__" / "l1-extract.cpython-314.pyc",       # wrapper stub, fallback
]
```

### 2. Use SourcelessFileLoader (not spec_from_file_location alone)
`spec_from_file_location` returns `None` for `.bak` and other non-standard extensions.
Use `SourcelessFileLoader` with the path and pass it as the explicit loader:
```python
import importlib.machinery, importlib.util

def _load_pyc(name: str, path) -> types.ModuleType:
    loader = importlib.machinery.SourcelessFileLoader(name, str(path))
    spec = importlib.util.spec_from_file_location(name, str(path), loader=loader)
    if spec is None:
        raise ImportError(f"Could not create spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

### 3. Re-exec guard for cron scripts
When a script is launched by a daemon venv but must run under system python3:
```python
import os, sys

_SYS_PYTHON = "/usr/bin/python3"

def _reexec_if_wrong_python():
    if os.path.realpath(sys.executable) != os.path.realpath(_SYS_PYTHON):
        os.execv(_SYS_PYTHON, [_SYS_PYTHON] + sys.argv)

# Call at the top of main():
_reexec_if_wrong_python()
```

## Pitfall: silent spec_from_file_location failure
`spec_from_file_location(name, path)` returns `None` for unknown extensions — the next call
`module_from_spec(None)` throws `AttributeError: 'NoneType' has no attribute 'loader'`.
Always use SourcelessFileLoader as the loader arg, or check `spec is not None`.

## Pitfall: __pycache__ recompile shadow
When a wrapper script (e.g. `l1-extract.py`) is imported under the wrong Python, it recompiles
a small stub (~4KB) into `__pycache__/l1-extract.cpython-314.pyc` that masks the real logic
byte-for-byte at the same cache path. Check file size: if `__pycache__/*.pyc` is 4KB and
the real logic in `references/*.pyc.bak` is 35KB+, the cache slot is a stub.
