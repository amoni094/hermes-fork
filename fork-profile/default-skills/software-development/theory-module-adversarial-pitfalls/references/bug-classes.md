# Bug Classes: Theory-Grounded Pure-Stdlib Modules

Full catalogue with code patterns and canonical fixes. Referenced from SKILL.md checklist.

---

## 1. Hand-authored lookup tables -- verify by ground-truth sampling

**Failure mode:** Manually transcribed tables (Allen composition, truth tables,
transition matrices) contain silent wrong entries. A 13x13 Allen composition table
copied from a reference paper can have >50% wrong entries. Tests written by the
same agent as the table cover only the entries transcribed correctly.

**Fix:**
1. Write a ground-truth function from first principles (boundary comparisons, no
   table lookup). For Allen: `allen_relation(a_s, a_e, b_s, b_e) -> IntervalRelation`.
2. Sample 50,000+ concrete float intervals covering all 13 relation pairs,
   recording allen_relation(a,b)->r1, allen_relation(b,c)->r2, allen_relation(a,c)->r_ac.
3. Build the correct table empirically: for each (r1, r2) pair, collect all
   observed r_ac values into a set.
4. Replace the static table entirely -- never patch individual entries.

Never accept a table produced by copying a paper figure without this verification.

---

## 2. Floating-point epsilon leaking into boundary cases

**Failure mode:** `p * log2(p + _EPS)` when `p = 1.0` gives a positive value,
making `-sum(...)` a small negative. Passes `>= -tolerance` guard tests but
silently violates entropy non-negativity.

```python
# WRONG -- eps leaks at boundary
entropy = -sum(p * math.log2(p + _EPS) for p in probs)

# CORRECT -- Cover & Thomas section 2.1: 0*log2(0) = 0 by convention
entropy = -sum(p * math.log2(p) for p in probs if p > 0)
```

Regression tests to add for every entropy variant:
```python
assert entropy_score([1.0]) == pytest.approx(0.0, abs=1e-12)
assert entropy_score([0.0, 1.0]) == pytest.approx(0.0, abs=1e-12)
assert entropy_score([1.0]) >= 0
assert vote_entropy([[1.0, 0.0], [1.0, 0.0]]) == pytest.approx(0.0, abs=1e-12)
```

---

## 3. SDL duality -- F(p)+F(~p) is a conflict

**Failure mode:** SDL conflict detection checks O+O and F+O pairs but omits F+F.
Via duality F(p) = O(~p), so F(p)+F(~p) = O(~p)+O(p) -- a DUAL_OBLIGATION_CONFLICT.

```python
if m1 is DeonticModality.FORBIDDEN and m2 is DeonticModality.FORBIDDEN:
    if _is_negation_of(p1, p2):
        conflicts.append(SDLConflict(type="DUAL_FORBIDDEN_CONFLICT", norms=(norm1, norm2)))
```

Test: `check_sdl_consistency([F("p"), F("~p")])` must return a conflict.

---

## 4. Condition string matching -- normalise whitespace

**Failure mode:** CTD detection builds `"~" + primary.proposition` and compares
with `==`. A formula with `condition="~ p"` (space after ~) silently fails to match.

```python
cond = (remedial.formula.condition or "").replace(" ", "")
expected = ("~" + primary.formula.proposition).replace(" ", "")
return cond == expected
```

Apply to any condition/proposition comparison where the value is user/LLM-supplied.

---

## 5. First-match classification drops multi-obligation clauses

**Failure mode:** A classifier that returns at the first matched pattern silently
discards additional obligations in compound clauses ("must hold AFS licence AND
maintain IDR procedure").

Fix: provide a `classify_all_X` variant that collects ALL matches into a list.
Use it in downstream audit functions. Export from `__init__.py`.

---

## 6. Pearl backdoor criterion -- two distinct G_x constructions (false-positive trap)

Two constructions; an adversarial reviewer may confuse them:

- G_x^in (remove incoming to X): for P(Y|do(X)) per Theorem 3.3.2
- G_x^out (remove outgoing from X): for testing whether Z blocks backdoor paths
  by severing the forward causal path, then checking d_sep({X},{Y},{Z})

G_x^out is correct for the criterion test. Verify with C->X->Y, C->Y, Z={C}:
- G_x^out: X isolated. d_sep({X},{Y},{C}) in {C->Y}: C blocks. Returns True. Correct.
- G_x^in: X->Y and C->Y remain. X->Y open. Returns False. Wrong.

Before accepting a directional-surgery finding, run this three-node counterexample.

---

## 7. execute_code truncation for large reconstruction scripts

**Failure mode:** `execute_code` silently truncates stdout to ~1 line for scripts
over ~200 lines. File-writing scripts appear to succeed but produce corrupted output.

Fix: use `terminal` with a shell heredoc, or use `write_file` with reconstructed content:

```bash
python3 << 'EOF'
import pathlib, subprocess
orig = subprocess.check_output(
    ["git", "show", "HEAD:src/path/to/file.py"],
    cwd="/path/to/repo", text=True
)
lines = orig.split("\n")
# find table bounds: locate type-annotation header, then track brace depth
# a closing } at column 0 is the outermost table close; inner } lines are indented
table_start = next(i for i, l in enumerate(lines) if "TABLE_NAME" in l and "Dict" in l)
depth = 0; end = None
for i, line in enumerate(lines[table_start:], table_start):
    for ch in line:
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: end = i; break
    if end is not None: break
new_content = "\n".join(lines[:table_start]) + "\n" + NEW_TABLE + "\n" + "\n".join(lines[end+1:])
pathlib.Path("/path/to/file.py").write_text(new_content)
EOF
```

---

## 8. CTD vs Forrester -- contradictory verdicts from separate code paths

**Failure mode:** `find_ctd_clusters` and `forrester_paradox_check` each implement
the CTD pair definition independently and drift apart.

Fix: extract a shared predicate that both call:
```python
def _is_contrary_to_duty_pair(primary: DeonticNorm, remedial: DeonticNorm) -> bool:
    if primary.formula.modality is not DeonticModality.OBLIGATORY: return False
    if remedial.formula.modality is not DeonticModality.OBLIGATORY: return False
    if remedial.formula.condition is None: return False
    expected = ("~" + primary.formula.proposition).replace(" ", "")
    actual = remedial.formula.condition.replace(" ", "")
    return actual == expected
```
One definition, one code path, zero contradictions.
