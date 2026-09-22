# Patterns — deriving analyses for Hermes scripts

## Pattern: pick the 2×2 cell from the English question

```
                  MAY (∃ path, ∪, ⊆)           MUST (∀ paths, ∩, ⊇)
FORWARD           Reaching definitions          Available expressions
                  uninit, dead write           CSE, redundant compute
BACKWARD          Live variables               Very busy expressions
                  unused import, dead store    hoist definite work
```

If the question is not in this table, *build a monotone framework* (new L, gen/kill or f_ℓ) rather than overloading LV.

## Pattern: bottleneck scanner as dataflow

1. Parse script → labelled While (assignments, tests, calls-as-blocks).
2. RD: alarm if `gen_RD(ℓ)` is killed before any `use` (dead write of flags, env, cache).
3. LV: alarm if an import/name is not live at its def (unused import). Seed `final` with names the *environment* observes (`export`, exit code, written files).
4. AE: alarm if a heavy expression (hash, HTTP, jq) is available at ℓ — skip recompute.
5. Report `(analysis, ℓ, gen, kill, lattice join)`. No CFG ⇒ no alarm.

## Pattern: skill router as CFA

1. Terms: skill values, `skill_view(name)`, dynamic dispatch.
2. Run **0-CFA**. Result `Ĉ` is the may-call graph.
3. Alarm: required skill not in any `Ĉ(ℓ)` of reachable labels (with the caveat that 0-CFA is may — absence is a *must-not-called* fact, which *is* sound for unused-skill cleanup).
4. If two cron contexts smash, rebuild with **1-CFA** (call-site contour).
5. Layer LV/effects on the discovered graph (Ch 3 compose Ch 2 / Ch 5).

## Pattern: gate-audit as abstract interpretation

1. Concrete C = `P(Z)` exit codes.
2. Abstract A = flat `{⊥, ok, cold, error, ⊤}` (or severity chain).
3. Write `α, γ`. Sequential composition = `f^#` composition. Branches = ⊔.
4. Soundness: never promote `⊤` to `ok`. Mixed 0 and 75 ⇒ `⊤` (flat) or `cold-start` (chain, if 75 > 0).
5. Loops on counters: widen the *counter* domain, not the exit lattice (exit lattice already has finite height).

## Pattern: cron → script → library (interprocedural)

1. Call graph from static names; unknown `eval` / `bash -c "$var"` ⇒ CFA or ⊤ callee.
2. Default: **context-insensitive** summaries (one abstract map per function).
3. If a helper is called from ok-path and error-path, **call-string k=1** so the exit lattice does not smash.
4. Alias at boundaries: env vars, lockfiles, cwd — may-alias of writers vs readers.
5. Effects `φ` union along the chain; `spawn` in a library taints the cron unless CFA proves the call dead.

## Pattern: new analysis in one page

```
Question:  ________________________________
May or must?  direction?  ________________
L = (carrier, ⊑, ⊔, ⊥, ⊤)
F = flow or flow^R ;  E = init or final ;  ι = ___
f_ℓ(S) = (S \ kill(B^ℓ)) ∪ gen(B^ℓ)   # or custom monotone map
Solver: worklist from (ι at E, ⊥ elsewhere)
Soundness: α(CS(ℓ)) ⊑ Analysis(ℓ)
```

If L has infinite height, add: widen points = back-edges; then narrow.

## Pattern: dead code before effects

May-effects (`∪`) taint from dead branches. Sequence:

1. CFA / constant-propagation (AI) to drop impossible edges.
2. LV to drop unused functions.
3. Then type/effect inference.

Do not certify “no net” on a script that still contains a dead `web_search`.

## Pattern: widening only at back-edges

```
for each CFG node n:
    in = ⊔ { out(p) | p → n }          # ordinary join
    if n is loop header:
        in = old_in(n) ∇ in            # widen
    out(n) = f_n(in)
```

After stability, replay with `∆` at the same headers.

## Anti-patterns (kill these)

- Alarms without labels.
- `∪` on a must question.
- MOP by unrolling `while`.
- 1-CFA “because higher-order is scary” with no collision.
- Must-alias used to prove *absence* of races (need may-alias for that).
- Narrow then widen.
- Forgetting env/export as LV uses at `final`.
