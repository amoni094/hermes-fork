---
name: lm-polygraph-ue
description: "Use when estimating LLM output uncertainty."
version: 1.0
author: Hermes Agent
license: MIT
tags: [uncertainty, hallucination, calibration, memory-gate, blackbox]
---

# lm-polygraph blackbox uncertainty estimation

Use when estimating LLM output uncertainty, detecting potential hallucinations, gating memory commits, or calibrating confidence scores. All methods here are **blackbox / API-only** (no hidden states, no white-box logits beyond optional logprobs).

Run with:

```bash
HERMES_HOME=/var/home/rainbow/.hermes HERMES_PROFILE=fork python3 <script>
```

Canonical scripts: `~/.hermes/hermes-scripts/ue-*.py`  
Fork wrappers: `~/.hermes/profiles/fork/scripts/ue-*.py` (runpy delegates)

JSONL / state lands in the profile cache: `~/.hermes/profiles/fork/cache/`.

## When to use which method

| Signal | Script | Needs | Use when |
|---|---|---|---|
| LexicalSimilarity | `ue-blackbox-scorer.py` | ≥2 samples | Multiple generations exist; no logprobs |
| SemanticClusterCount | `ue-blackbox-scorer.py` | samples | Diversity / disagreement of samples |
| VerbalizationConfidence | `ue-blackbox-scorer.py` | response text | Model uttered a % or hedge phrase |
| LengthAnomalyScore | `ue-blackbox-scorer.py` | running cache | Abruptly short/long answers |
| RepetitionScore | `ue-blackbox-scorer.py` | response | Degenerate / looping text |
| HedgePhraseScore | `ue-blackbox-scorer.py` | response | Explicit epistemic hedges |
| ConsistencyScore | `ue-blackbox-scorer.py` | cache or `--consistency` | Condorcet N=3 already ran |
| EigValLaplacian / DegMat / Eccentricity / NumSemSets | `ue-semantic-graph.py` | samples | Graph UE (lm-polygraph) |
| Memory gate | `ue-memory-gate.py` | query+response | Before committing a fact |
| Calibration bridge | `ue-calibration-bridge.py` | jsonl | Feed `calibration-threshold-updater.py` |

White-box methods **not** implemented (API-only constraint): token entropy, mean token entropy, perplexity from full distributions, Mahalanobis on hidden states, true semantic entropy with NLI clustering. Approximate semantic entropy via sample clusters + graph metrics instead.

## Invoke

```bash
python3 ~/.hermes/hermes-scripts/ue-blackbox-scorer.py score \
  --query '...' --response '...' [--samples 'a|b|c'] [--logprob-confidence 0.7]
python3 ~/.hermes/hermes-scripts/ue-blackbox-scorer.py stats
python3 ~/.hermes/hermes-scripts/ue-blackbox-scorer.py --self-test

python3 ~/.hermes/hermes-scripts/ue-semantic-graph.py --samples 't1|t2|t3'
python3 ~/.hermes/hermes-scripts/ue-semantic-graph.py --self-test

python3 ~/.hermes/hermes-scripts/ue-memory-gate.py check \
  --query '...' --response '...' [--content 'fact to commit']
python3 ~/.hermes/hermes-scripts/ue-memory-gate.py stats

python3 ~/.hermes/hermes-scripts/ue-calibration-bridge.py sync [--since-hours 24]
python3 ~/.hermes/hermes-scripts/ue-calibration-bridge.py status
```

`composite_ue > 0.5` ⇒ `high_ue=true`. Gate: `>0.6` or `hedge_phrase>0.4` ⇒ `GATE_WARN`; `>0.75` or empty query/response ⇒ `GATE_DENY`; else `GATE_PASS`.

## Integration

- **memory-ransac-commit / memory-ransac-gate:** run `ue-memory-gate.py check` *before* RANSAC commit. DENY blocks the write; WARN annotates `ue_uncertain=true` and still allows RANSAC to reject outliers.
- **calibration-threshold-updater:** consumes `cache/calibration-log.jsonl`. Bridge writes `{ts, query_hash, predicted_confidence, scope: ue_blackbox}`.
- **metacognitive-harness:** verbalized FOK/JOL and hedge-score are complementary; UE composite is the blackbox ensemble. Do not average FOK with `1-composite_ue` unless both are DPI-clamped.
- **consistency_scorer:** Condorcet `{0.05,0.2,0.5,1.0}` is incorporated when present (`--consistency` or cache). High consistency lowers UE.

## Hard-core invariants

1. **DPI (data-processing inequality):** `predicted_confidence = 1 - composite_ue`, then `min` with any available `logprob_confidence`. Never claim higher confidence than raw logprobs. Empty / missing evidence ⇒ confidence 0, not 1.
2. **Normalization:** every per-signal UE contribution and `composite_ue` are clipped to `[0,1]`. Composite is the equal-weight mean of *available* UE-direction scores (skip missing samples/consistency; do not treat missing as 0 — that would deflate UE).
3. **Fail-closed gate:** empty/whitespace query or response ⇒ `GATE_DENY`. Missing scorer ⇒ `GATE_DENY`. No silent PASS.
4. **H-I7:** missing or malformed cache files never raise; annotation / empty stats only.
5. **H-I6:** stdlib only. No numpy/scipy/torch/transformers.
6. **Atomic JSON:** dict state files use write-tmp + `os.replace`. JSONL is append + flush.

## Score direction

JSON `scores.lexical_sim` / `verbalization` / `consistency` are *similarity or confidence* (high = certain). `cluster_count` is a raw count. `length_anomaly`, `repetition`, `hedge_phrase`, and `composite_ue` are *uncertainty* (high = uncertain). Composite converts sim/confidence via `1 - x` and cluster via `(k-1)/(n-1)`.

Graph: `eigval_laplacian` is `trace(L)=sum(degrees)` of the trigram-Jaccard similarity Laplacian (exact eigenvalue sum; power iteration reports `λ_max` as belt). Identical samples ⇒ one semantic set, low diversity. Unrelated samples ⇒ many components, `high_diversity=true`.

## Limitations (blackbox vs white-box)

- Trigram Jaccard is a lexical/semantic *proxy*, not NLI entailment clustering (true semantic entropy).
- Power iteration is belt; the hard-core Laplacian sum is the trace identity.
- Verbalized % is cheap and overconfident (GPT-4 assigned max confidence to 87% of answers including wrong ones). Always combine with samples when possible.
- Length prior is weakly informative (n=8, mean=200, std=100), not a fitted language-specific length model.
- `|` is the sample delimiter and cannot appear unescaped inside a sample on the CLI.
- No Mahalanobis / hidden-state density. No token-level entropy without logprobs.

## Falsifier

If `ue-calibration-bridge.py` emits `predicted_confidence` strictly greater than a provided `logprob_confidence` on the same row, the DPI hard core is broken — do not ship.
