# Named-Check Catalogue Pattern

For auditing a system with many interacting surfaces (scripts, skills, config, feature lists)
where a narrative review pass would miss cross-surface drift.

## Catalogue structure

Each check is a 4-tuple: `(id, severity, label, fn)` where `fn() -> (bool, detail)`.

```python
checks = []

# D1 — CLI correctness
def check_d1_01():
    r = subprocess.run(
        ["python3", str(S/"metacognitive-harness.py"), "boundary-check", "--help"],
        capture_output=True, text=True)
    return r.returncode == 0, r.stderr[:200]
checks.append(("D1-01", "CRIT", "boundary-check --help exits 0", check_d1_01))

# D2 — AST validity
def check_d2_01():
    try:
        ast.parse((S/"metacognitive-harness.py").read_text())
        return True, "clean"
    except SyntaxError as e:
        return False, str(e)
checks.append(("D2-01", "CRIT", "AST metacognitive-harness.py", check_d2_01))

# D3 — Config key presence (read from the correct YAML path)
def check_d3_01():
    cfg = yaml.safe_load((H/"config.yaml").read_text())
    # Navigate to the canonical path, NOT a top-level shortcut
    rs = (cfg.get("reasoning_research", {})
               .get("reasoning_frameworks", {})
               .get("reasoning_selection", {}))
    present = "cascade_order" in rs.get("conflict_resolution", {})
    return present, f"path: reasoning_research.reasoning_frameworks.reasoning_selection"
checks.append(("D3-01", "HIGH", "config cascade_order present at canonical path", check_d3_01))
```

## Run loop

```python
def run_audit(checks):
    results = []
    for id_, sev, label, fn in checks:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"EXCEPTION: {e}"
        results.append((id_, sev, label, ok, detail))
    return results

def print_results(results):
    fails = [(id_, sev, label, detail) for id_, sev, label, ok, detail in results if not ok]
    print(f"{len(results)-len(fails)}/{len(results)} PASS  |  CRIT={sum(1 for _,s,*_ in fails if s=='CRIT')} HIGH={sum(1 for _,s,*_ in fails if s=='HIGH')} MED={sum(1 for _,s,*_ in fails if s=='MED')}")
    for id_, sev, label, detail in fails:
        print(f"  FAIL [{sev}] {id_}: {label}")
        print(f"       \u2514\u2500 {detail[:120]}")
    if not fails:
        print("ALL CRIT/HIGH/MED RESOLVED")
```

## Recursive fix loop

```python
for wave in range(1, 8):
    results = run_audit(checks)
    print_results(results)
    fails = [r for r in results if not r[3]]
    if not fails:
        break
    # Fix the fails here (patch scripts, skills, config)
    # Then rebuild the kernel to avoid stale function references:
    # next execute_code block rebuilds `checks` from scratch
```

## Severity levels

- CRIT: failure means the system cannot function correctly (AST error, required flag missing, cascade order wrong)
- HIGH: failure means a documented contract is broken but the system may limp along (wrong flag name in skill, wrong YAML path in check)
- MED: failure means a quality or completeness issue (duplicate entry, missing entry, relative path where absolute is required)

## Naming convention

`D<dimension>-<seq>` where dimensions are:
- D1: CLI behaviour (exit codes, required flags, output keys)
- D2: AST / syntax validity
- D3: Config key presence and values
- D4: Cascade order consistency
- D5: Skill invocation flags (correct argparse flags in skill prose)
- D6: Hook runner scripts exist and function
- D7: Feature index completeness
- D8: Cross-surface consistency (same constant in N files)

Stable IDs enable oscillation detection: same ID failing in wave N and wave N+1 = the fix
did not take (wrong YAML path, stale kernel, wrong regex).

## Pitfalls

- **Wrong YAML path**: config has multiple nested blocks; a top-level shortcut key added in a
  prior session can shadow the canonical path. Always navigate from root and confirm the
  path matches what the consuming code actually reads.
- **Single-line regex on multi-line commands**: a CLI invocation split with `\` continuation
  will not match a single-line `re.search`. Scan a N-line block window instead:
  ```python
  text_blob = "\n".join(lines[i:i+8])  # join the block
  if re.search(r'conflict-resolve.*--framework-a', text_blob, re.DOTALL):
      ...
  ```
- **Stale kernel**: after fixing a check function, the `checks` list in a prior `execute_code`
  call still holds the old function object. Rebuild the catalogue in a fresh block (`reset=True`
  or a new top-level execute_code call).
- **Variable casing mismatch**: if the constant is `CASCADE_ORDER` (uppercase) and the regex
  checks for `cascade_order` (lowercase), the check always PASSes as a false-PASS.
  Match exact casing and bracket syntax (`[...]` vs `(...)`).
