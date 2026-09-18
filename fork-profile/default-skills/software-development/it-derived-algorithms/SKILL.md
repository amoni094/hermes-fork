---
name: it-derived-algorithms
description: "Use when deriving Hermes algorithms from IT theorems."
related_skills:
  - rr-compaction-scorer
  - math-cs-applicability-reasoning
  - hermes-internals-source-recon
  - hermes-context-budgeting
---

# IT-Derived Algorithms for Hermes

Information theory theorems are existence proofs — they don't transfer directly as
algorithms. But they motivate correct *directions* and *measures* even when formal
guarantees require assumptions (i.i.d., known distribution, continuous random variables)
that don't hold in Hermes's discrete-choice / natural-language environment.

This skill covers the derivation pattern and the five algorithms produced from the
6-book analysis (Shannon 1948, MacKay ITILA, Cover & Thomas EIT, Li & Vitanyi,
Gallager ITRC, Lin & Costello ECC).

## When to Use

- Evaluating whether an IT theorem suggests a Hermes improvement
- Implementing or tuning one of the 5 IT-derived algorithms below
- Adding a new algorithm candidate to the library
- Debugging unexpected behavior in compaction scoring, skill routing, or memory writes

## The Derivation Pattern

Theorems that SKIP the math-cs-applicability-reasoning 7-step chain (desirability=0
or no implementable algorithm) can still yield practical algorithms by relaxing the
formal guarantee requirement and borrowing the shape and measure:

1. **Identify the measure** the theorem uses (entropy, KL divergence, compression ratio,
   Occam factor, channel rate). This is the operational signal.
2. **Find a computable proxy** for that measure in Hermes's environment. Kolmogorov
   complexity K is uncomputable — gzip ratio is not. True KL over unknown distributions
   is uncomputable — KL over empirical unigram counts from skill-state observations is
   not (and that history is not currently written by runtime skill loads).
3. **Identify the direction** the theorem implies (high entropy → keep; low KL to session
   → relevant skill; tight rate budget → accept higher distortion).
4. **Apply with modest weight.** These are motivating signals, not proven optima.
   Weight the new sub-signal at 0.10–0.20 against existing signals — enough to break
   ties, not enough to override strong semantic signals.
5. **Verify with an ad-hoc test suite** covering key monotonicity properties:
   - More redundant block → lower score.
   - Tighter budget → higher aggressiveness.
   - Shorter skill at equal cosine → higher Occam score.
   - KL(p, p) = 0; KL(p, q) > 0 for orthogonal distributions.

Pitfall: assert thresholds against the actual math. `1 - exp(-3) = 0.9502`, so
`assert result > 0.95` fails by epsilon. Compute the exact value first and use
`>= expected - 1e-4`.

## The Five Algorithms

### Algorithm 1: Typicality-Gated Info Density
**Theorem basis**: AEP + Shannon source coding
**Target**: Phase-1 RR demotion scorer (_rr_score in context_compressor.py)
**Status**: PATCHED INTO PRODUCTION

Gzip compression ratio as proxy for information density. High-compressibility
(repetitive/redundant) blocks score lower and are demoted first.

    pp = 0.40 * density      # tool-type semantic density
       + 0.10 * info_density  # gzip ratio, clamped to <= 1.0; fallback = density
       + 0.30 * recency
       + 0.20 * proximity

Verified in context_compressor.py: `import gzip` at module top (line 7);
`gzip.compress(..., compresslevel=1)` inside `_rr_score` (~2882).
`_info_density = min(len(_gz) / max(len(_raw), 1), 1.0)` — no 0.1 floor.
On exception, fallback is `density`, not a constant 0.6.
Config: compression.use_rr_scorer: true, rr_scorer_lambda: 0.2.

Constraints and bypass logic (as of 2026-09-10 patch):
- Short blocks (<80 chars) OR structured content (JSON: starts with { or [, code fences,
  HTML, markdown tables, shell scripts, class/def/import): gzip bypassed, fallback=density.
  Rationale: LZ77 compresses structured content well despite high semantic value; bypassing
  prevents unfair demotion of high-value tool results (search_files, web_search, skill_view).
- Clamp: max(0.10, min(ratio, 1.0)) -- floor prevents header-inflation near-zero on tiny blocks.
- Fallback on exception: density (not 0.6; that was stale docs).
- Comment in code: 'LZ-redundancy *proxy*' (not AEP; that label was corrected).

### Algorithm 2: KL-Divergence Skill Prior
**Theorem basis**: Method of types + Sanov's theorem (shape only; script is not Sanov)
**Script**: ~/.hermes/scripts/kl-skill-prior.py
**Status**: Standalone CLI. NOT wired into routing. Do not claim it is.

Bag-of-words unigrams (tokens >2 chars), not bigrams. Scores D(query || skill-obs)
in bits with epsilon=1e-8 smoothing on Q (not 1e-9). Score = 2^{-KL}. Skills with
no observation tokens are omitted.

    python3 ~/.hermes/scripts/kl-skill-prior.py 'compaction scoring context' --top 5
    # positional queries [queries ...]; --top (default 10)
    # NO --queries, --skill-state-dir, --top-k, or --lambda-blend

Verified run (same command): one hit only — hermes-operating-pattern, kl=24.9905,
score=0.0, n_obs=1. That is not a useful prior; it is the only skill with any
observation tokens.

#### skill-state data gap (blocking)

Dir: ~/.hermes/cache/skill-state/ — **2 files, both dummy wiring tests from 2026-08-29/30**:
- wiring-test-001__hermes-operating-pattern.json — observations: []
- wt002__hermes-operating-pattern.json — one dummy obs: "opened config file"

config.yaml has `skill_state.enabled: true` and `dir: cache/skill-state`, but
hermes-agent contains **zero** callers of skill-state.py. Writers: the CLI script
itself, a hint string in working-memory.py, and GC from skill_prune_audit.py.
Nothing logs skill_view / skill dispatch history. This is not a stale cache; the
write path was never connected.

#### Why Alg 2 was not patched into routing (<50-line bar)

hermes-semantic-skill-routing is a **documentation** skill for subagent context
packets (messages-layer top-K). There is no Python rank_skills / embedding router
in hermes-agent to patch. Main-session skill injection is the full system-prompt
listing; mutating it mid-conversation breaks prefix cache (routing skill: do not
use on the main session).

Wiring for real would need: (1) skill_view/load instrumentation writing
observations, (2) a ranker that consumes them, (3) a subagent injection point
that does not touch the system prompt. Far more than 50 lines, and with n=1 dummy
obs the prior would always return hermes-operating-pattern. Adding a "run this
script" paragraph to the routing skill would be cargo-cult, not wiring.

Until skill-state is written by runtime skill loads, treat this as a lab CLI.

Pitfall: KL undefined when P(x)>0 but Q(x)=0. Script adds epsilon=1e-8 to Q
counts and does not renormalise. Do not remove the smoothing.

### Algorithm 3: Rate-Distortion Adaptive Compaction Aggressiveness
**Theorem basis**: Shannon R(D) (shape only; tokens are not Gaussian)
**Script**: ~/.hermes/scripts/rd-compaction-advisor.py
**Status**: Standalone advisor. NOT wired into context_compressor.py.

Live curve (do not invert):

    remaining = 1 - min(current/threshold, 1)
    aggressiveness = exp(-k * remaining)   # k default 3.0
    # remaining=1 (empty) -> exp(-3) ~ 0.0498 (minimal)
    # remaining=0 (full)  -> 1.0 (aggressive)
    # aggressive (>=0.75) only when remaining ≲ 0.10

The previously documented `1 - exp(-3 * fill_fraction)` is **wrong** relative to
the live script (that form would report 0.88 / "aggressive" at 71% fill).

    python3 ~/.hermes/scripts/rd-compaction-advisor.py \
        --current-tokens 85000 --threshold 120000
    # --current-tokens, --threshold (not --threshold-tokens), --k, --from-log
    # --threshold omitted -> reads compression.threshold_tokens from config.yaml

Verified output:

    current_tokens=85000, threshold_tokens=120000, budget_fraction=0.708,
    remaining_fraction=0.292, aggressiveness=0.417, level=light
    focus_topic_prefix: "Summarise older tool results but keep key decisions and outputs."

#### Compressor hook points (inspected, not patched)

- `_rr_score` (~2853): ranks WHICH messages to demote. R(D) is HOW aggressive.
  Do not fold aggressiveness into pp; that conflates two axes. Recency already
  uses `exp(-3.0 * (1 - i/n))` — similar shape, different meaning.
- `_demotion_budget` (~2901): `max(1, min(8, prune_boundary // 3))` — the natural
  place to scale how many Phase-1 demotions happen. Not connected.
- `compress(..., focus_topic=)` / `_generate_summary`: advisor emits
  `focus_topic_prefix`; compressor already accepts `focus_topic` (manual
  `/compress <focus>`). No caller prepends the advisor prefix.
- Script docstring: there is no `run_compress_context()` symbol. `--from-log` is
  best-effort and off unless requested.

Wiring would be a production compressor change (config flag + tests). Not done.

### Algorithm 4: Occam-Weighted Skill Injection
**Theorem basis**: MacKay Ch 28 Occam factor
**Script**: ~/.hermes/scripts/occam-skill-ranker.py
**Status**: Standalone ranker. NOT wired into skill injection.

Default path is **coverage Occam**, not the cosine-minus-log-length formula.
`--legacy-score` activates length/1000 penalty. `--lambda` default is **0.25**
(legacy path only). `--ranker {occam,legacy,hamming}`.

    python3 ~/.hermes/scripts/occam-skill-ranker.py 'compaction scoring' --top 3
    # positional query; also --query FLAG; --top (not --top-k); --lambda
    # NO --skills-dir. Optional: --metric {cosine,l1,blend}, --coverage,
    # --uncovered, --hamming, --skills-json, routing-nt / dp-route subcommands

Verified output (`--top 3`, metric=blend, cache_hits=0, cache_misses=232):

    1. information-theory-for-agents  cosine=0.1508 score=0.0759 length_tokens=2976
    2. rr-compaction-scorer           cosine=0.1414 score=0.0712 length_tokens=1609
    3. academic-literature-review     cosine=0.0    score=0.0    length_tokens=6912

`routing-nt` is a per-task-type ranker-policy lookup (~/.hermes/cache/ranker-policy.json),
not a Hermes skill-injection hook.

Pitfall: test lambda=0 with IDENTICAL descriptions (same cosine) to verify
penalty isolation. Different descriptions give different cosine even at lambda=0.

Pitfall: lambda above 0.3 lets stubs out-rank legitimately comprehensive skills.
Legacy default 0.25 is already less conservative than the old 0.1 docs.

### Algorithm 5: Redundancy Memory Gate
**Theorem basis**: Shannon channel capacity / feedback redundancy (proxy only)
**Script**: ~/.hermes/scripts/memory-redundancy-gate.py
**Status**: Standalone CLI. NOT wired into hindsight_retain, memory(), or
memory-layer-gate. Script itself says so. Checks MEMORY.md / USER.md lexical
overlap, not the Hindsight vector store.

    if TF_cosine(new_fact, existing_chunk) >= 0.88: verdict=SUPPRESS else WRITE
    # lexical TF cosine, NOT embeddings, NOT Shannon R = 1 - H/H_max

    python3 ~/.hermes/scripts/memory-redundancy-gate.py 'User prefers concise responses'
    # positional fact; --threshold (default 0.88); --facts-json JSON array
    # NO --fact, --memory-dir, or --top-k. Default is 0.88, not 0.92.

Verified output:

    verdict=WRITE, redundancy=0.25, info_gain=0.75, residual=0.9963
    nearest starts: "TraceGrant: ~/.hermes/scripts/l1-tracegrant.py; ..."
    reason: TF cosine 0.250 < threshold 0.880

JSON keys: verdict, redundancy, info_gain, nearest, residual, reason.
There is no `should_write` field. Exit 0 always on a successful evaluation;
SUPPRESS is not a process failure (exit 2 = usage/IO).

Threshold: 0.88 default. At 0.85 you suppress useful updates; at 0.97 you miss
near-verbatim duplicates. TF cosine does NOT catch paraphrases.

## Wiring status (verified)

| Alg | Runtime | Wired? |
|-----|---------|--------|
| 1 gzip density in `_rr_score` | context_compressor.py | YES |
| 2 kl-skill-prior.py | CLI only | NO — no ranker to patch; skill-state dummy |
| 3 rd-compaction-advisor.py | CLI only | NO — hooks exist, unused |
| 4 occam-skill-ranker.py | CLI only | NO |
| 5 memory-redundancy-gate.py | CLI only | NO |

## Verification

Do not cite the old "24 ad-hoc checks" as current evidence unless you re-run them.
After any change, re-run the CLIs (`--help` first) and check:
- Alg 1: weights 0.40+0.10+0.30+0.20=1.0; `import gzip` at top; compress in `_rr_score`; fallback=`density`
- Alg 2: missing dir -> empty list; empty observations omitted; epsilon=1e-8 on Q; live dir currently 2 dummy files
- Alg 3: remaining=1 -> ~0.0498; remaining=0 -> 1.0; 85k/120k -> aggressiveness~0.417 level=light; monotonic in remaining
- Alg 4: default coverage Occam; `--legacy-score` for length penalty; `--lambda` default 0.25 on legacy path
- Alg 5: high TF cosine -> SUPPRESS; low -> WRITE; keys are verdict/redundancy not should_write

## Common Pitfalls

- **Do not invert the R(D) curve**: live advisor is `exp(-k * remaining)`, not
  `1 - exp(-3 * fill)`. The inverted form falsely labels 71% fill as aggressive.
- **Strict threshold asserts against exp()**: compute the exact value first
  (`python3 -c "import math; print(math.exp(-3.0))"`), use `>= value - 1e-4`.
- **KL smoothing is mandatory**: epsilon=1e-8 on Q. Removing it crashes on sparse histories.
- **Gzip bypass on structured/short content**: blocks <80 chars or starting with
  JSON/code/HTML/table markers bypass gzip (uses density fallback). This prevents
  LZ77 from unfairly demoting high-value structured tool results.
- **Floor 0.10**: clamp is max(0.10, min(ratio, 1.0)), not just min(ratio, 1.0).
  Floor prevents header-inflation near-zero scores on tiny repeated blocks.
- **Verify args with --help before documenting**: positional `queries`/`query`/`fact`;
  `--top` not `--top-k`; `--threshold` not `--threshold-tokens`.
- **Do not treat skill-state as dispatch history**: it is a long-horizon execution
  state CLI. Runtime skill loads do not write it. KL prior is empty until they do.
