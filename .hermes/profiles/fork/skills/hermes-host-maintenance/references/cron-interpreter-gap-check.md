# Cron Interpreter Gap Check

## Background

Hermes cron scripts do NOT run in the fork's in-tree venv (Python 3.11). They run under the
PM's managed dependency venv (`project_python(repo)`) — currently Python 3.14, at a path like
`~/.hermes/installs/<hash>/environments/<hash>/venv/bin/python`.

The bootstrap is `_POSIX_SCRIPT_BOOTSTRAP` in `cron/scheduler_script.py`: it adds the repo
root to `sys.path` and runs the script directly. No PYTHONPATH inheritance.

## Identify the cron interpreter

```bash
python3 -c "
import sys; sys.path.insert(0,'$HOME/.hermes/hermes-fork')
from pm.environments import project_python; from pathlib import Path
print(project_python(Path('$HOME/.hermes/hermes-fork')))
"
```

## Check all scheduled scripts for import gaps

```bash
CRON_PY=$(python3 -c "
import sys; sys.path.insert(0,'$HOME/.hermes/hermes-fork')
from pm.environments import project_python; from pathlib import Path
print(project_python(Path('$HOME/.hermes/hermes-fork')))
")

python3 -c "
import json, subprocess, sys
with open('$HOME/.hermes/profiles/fork/cron/jobs.json') as f:
    data = json.load(f)
jobs = data.get('jobs', data) if isinstance(data, dict) else data
scripts = [j['script'] for j in jobs if j.get('script','').endswith('.py')]
bad = []
for s in scripts:
    probe = '''
import ast, sys, importlib.util
with open(SCRIPT) as f: src = f.read()
tree = ast.parse(src)
mods = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for a in node.names: mods.add(a.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom) and node.module:
        mods.add(node.module.split(".")[0])
missing = [m for m in mods if m not in sys.stdlib_module_names
           and __import__("importlib.util").util.find_spec(m) is None]
if missing: print("MISSING:", missing)
'''.replace('SCRIPT', repr(s))
    r = subprocess.run(['$CRON_PY', '-c', probe], capture_output=True, text=True)
    if 'MISSING:' in r.stdout:
        bad.append(f'{s.split("/")[-1]}: {r.stdout.strip()}')
if bad:
    print('\n'.join(bad))
else:
    print('all scheduled scripts: imports OK')
" 2>/dev/null
```

## Known available packages in managed venv (Python 3.14)

- `requests` — HTTP
- `ruamel.yaml` — YAML parsing (preferred over PyYAML on 3.14)
- `httpx`, `pydantic`, `anthropic`, and all hermes core deps

## Known absent packages

- `pyyaml` (import name `yaml`) — NOT in managed venv; use `ruamel.yaml` instead
- `pypdf` — not available; handle with `try/except ImportError`
- `numpy` — not available; scripts importing it unconditionally will crash
- `gepa` — optional optimizer; only needed for `--optimize` mode, not default cron

## PyYAML → ruamel.yaml fallback pattern

When a cron script uses `import yaml` (PyYAML API) and PyYAML is absent:

```python
try:
    import yaml
except ImportError:
    try:
        from ruamel.yaml import YAML as _RYAML
        import io as _io
        class yaml:  # type: ignore
            @staticmethod
            def safe_load(s: str):
                return _RYAML().load(_io.StringIO(s))
    except ImportError:
        print("PyYAML or ruamel.yaml required: pip install pyyaml", file=sys.stderr)
        sys.exit(2)
```

`ruamel.yaml` is in the managed venv, so the inner `ImportError` branch only fires if both
are absent — which should not happen in normal operation.

## Verifying a script runs cleanly under cron Python

The cron bootstrap sets up sys.path identically to how the scheduler does:

```bash
$CRON_PY -c "
import importlib.machinery, os, sys, types
repo='/var/home/rainbow/.hermes/hermes-fork'
script='/path/to/script.py'
sys.argv = [script]
sys.path[0:1] = [os.path.dirname(script), repo]
main = types.ModuleType('__main__')
main.__file__ = script
main.__loader__ = importlib.machinery.SourceFileLoader('__main__', script)
main.__builtins__ = __builtins__
sys.modules['__main__'] = main
with open(script, 'rb') as f:
    code = compile(f.read(), script, 'exec')
exec(code, main.__dict__)
" 2>&1 | head -20
```

## Common false positives in import gap scan

- `shadow_telemetry`: loaded via `sys.path.insert` at runtime in the script itself (path resolves
  to `~/.hermes/scripts/shadow_telemetry.py`). The static AST scan flags it but it works at runtime.
- `gepa`: only imported inside `try/except ImportError` in `--optimize` mode, not default cron.
- `__future__`: stdlib, not a package. The AST scanner may include it; filter it out.
