# Python Runtime Pitfalls — Hermes Scripts (Aug 2026)

Discovered during implementation of retry-budget-guard.py and verification harness.

## 1. Hyphenated Filenames Cannot Be Imported via sys.path

Python's import system resolves module names to filenames by replacing `.` with `/` and
appending `.py`. It does NOT handle hyphens — `import retry_budget_guard` looks for
`retry_budget_guard.py`, not `retry-budget-guard.py`.

**Pattern that FAILS (even with sys.path manipulation):**
```python
import sys
sys.path.insert(0, "/var/home/rainbow/.hermes/scripts")
from retry_budget_guard import with_retry   # ModuleNotFoundError
```

**Pattern that WORKS for any filename:**
```python
import importlib.util

def load_sibling(logical_name: str, filepath: str):
    spec = importlib.util.spec_from_file_location(logical_name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

rbg = load_sibling(
    "retry_budget_guard",
    "/var/home/rainbow/.hermes/scripts/retry-budget-guard.py"
)
rbg.with_retry(...)
```

**Applies to ALL hyphenated script names in ~/.hermes/scripts/:**
- retry-budget-guard.py
- memory-ttl-purge.py
- memory-provenance.py
- unified-recall.py (no hyphens, standard import works)

**Template used in l1-promote.py and l1-graphiti-write.py:**
```python
try:
    import importlib.util as _ilu
    _guard_path = str(FACTS_DIR.parent / "scripts" / "retry-budget-guard.py")
    _spec = _ilu.spec_from_file_location("retry_budget_guard", _guard_path)
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
    return _mod.with_retry(_call, classify_fn=_mod.classify_anthropic_error, label="...")
except Exception:
    return _call()   # graceful degradation
```

## 2. Function Body Extraction for exec() Testing

When extracting a single function from a script to test in isolation via exec(),
the naive "collect lines until indentation drops" approach fails on multi-line
type annotations containing `(`:

```python
# WRONG — breaks at list[dict] type annotation:
for line in src.splitlines():
    if line.startswith("def my_func("): capture = True
    if capture:
        if line and not line[0].isspace() and not line.startswith("def my"):
            break   # triggers on the annotation '(' before the body starts
        fn_lines.append(line)
```

**CORRECT — use ast.parse + lineno/end_lineno:**
```python
import ast, textwrap

src = open("/path/to/script.py").read()
tree = ast.parse(src)

fn_node = next(
    n for n in ast.walk(tree)
    if isinstance(n, ast.FunctionDef) and n.name == "my_func"
)

lines = src.splitlines()
fn_src = textwrap.dedent("\n".join(lines[fn_node.lineno - 1 : fn_node.end_lineno]))

ns = {"math": math, "datetime": datetime}   # inject required stdlib
exec(fn_src, ns)
result = ns["my_func"](...)
```

The `end_lineno` attribute is available in Python 3.8+ (ast.FunctionDef).
This handles: multi-line type annotations, default values, decorators, docstrings.

## 3. 5-Class Retry Budget Pattern (Self-Healing Failure Taxonomy)

Implemented as `retry-budget-guard.py` at `/var/home/rainbow/.hermes/scripts/`.

**Classification table:**
| ErrorClass | Trigger | max_attempts | base_delay | Examples |
|------------|---------|--------------|------------|---------|
| TRANSIENT | ConnectionError, TimeoutError | 5 | 2.0s (2x backoff) | network flap, rate limit |
| RESOURCE | 429, 503, "quota exceeded" | 2 | 30.0s (flat) | quota exhausted |
| SEMANTIC | ValueError, JSONDecodeError, parse | 2 | 1.0s (flat) | bad model output |
| AUTH | 401, 403, PermissionError, "unauthorized" | 1 | 5.0s | wrong API key |
| FATAL | AssertionError, SystemExit, corruption | 0 | — | data corruption, explicit abort |

**Usage:**
```python
from retry_budget_guard import with_retry, classify_anthropic_error

result = with_retry(
    lambda: client.messages.create(...),
    classify_fn=classify_anthropic_error,  # or classify_http_error
    label="my_operation"
)
```

**Loading from hyphenated filename (the correct pattern):**
```python
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("retry_budget_guard", "/path/retry-budget-guard.py")
_mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
_mod.with_retry(fn, classify_fn=_mod.classify_http_error, label="my_label")
```

## 4. Idempotent SQLite Schema Migration Pattern

When adding columns to an existing SQLite table, use `ALTER TABLE ADD COLUMN` wrapped in
try/except — SQLite raises an error if the column already exists (no IF NOT EXISTS support):

```python
MIGRATIONS = [
    "ALTER TABLE fact_lifecycle ADD COLUMN source_type TEXT DEFAULT 'internal'",
    "ALTER TABLE fact_lifecycle ADD COLUMN session_id TEXT DEFAULT ''",
    "ALTER TABLE fact_lifecycle ADD COLUMN action_id TEXT DEFAULT ''",
    "ALTER TABLE fact_lifecycle ADD COLUMN last_accessed_turn INTEGER DEFAULT 0",
]

with sqlite3.connect(str(DB_PATH)) as conn:
    _ensure_schema(conn)   # CREATE TABLE IF NOT EXISTS for main schema
    for migration in MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass   # column already exists — idempotent
    conn.commit()
```

This is safe to run on every startup — columns that already exist are silently skipped.
Used in lifecycle.db schema evolution in l1-promote.py (_lifecycle_db_ensure_schema).
