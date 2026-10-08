---
name: cross-lingual-context-compression
description: >
  Use when compressing context that contains multilingual content. Applies token-arbitrage
  compression: identify spans in non-English languages where a translation is shorter in
  the target token space, and substitute. Works within the existing lambda-tuner pipeline.
triggers:
  - context window contains non-English text
  - compression ratio below target on multilingual sessions
  - tuning lambda-tuner for multilingual users
  - implementing cross-lingual token efficiency
category: research
---

# Cross-Lingual Context Compression

## Theory

From MSCLAR et al., NeurIPS 2025 (extended 2026): Cross-lingual prompt compression exploits
the fact that LLM tokenizers are not language-neutral. A concept expressed in German may
tokenize to 30% fewer tokens than the same concept in English, depending on the LLM vocab.

Key insight: for compressible spans (definitions, summaries, background context), find the
language-token combination that minimizes token count while preserving semantic fidelity.

**Token-arbitrage score**: `TA(span, lang) = semantic_sim(span, translate(span, lang)) / tokens(translate(span, lang))`

Pick the `(span, lang)` pair maximizing TA above a fidelity floor (default 0.85).

## Hermes Application

Target: `plugins/context_engine/` (lambda-tuner plugin) and the `pre_compress` hook.

### Implementation sketch

```python
COMPRESS_LANGS = ['de', 'zh', 'fi']  # dense-tokenizing languages for GPT/Claude vocabs
FIDELITY_FLOOR = 0.85  # minimum semantic similarity to accept translation

def cross_lingual_compress(span: str, tokenizer_count_fn) -> str:
    base_tokens = tokenizer_count_fn(span)
    best = span
    best_tokens = base_tokens
    for lang in COMPRESS_LANGS:
        translated = translate(span, lang)
        t = tokenizer_count_fn(translated)
        sim = semantic_sim(span, translated)  # cosine of embeddings
        if sim >= FIDELITY_FLOOR and t < best_tokens:
            best = translated
            best_tokens = t
    return best  # returns original if no improvement
```

### Integration point

In `pre_compress` hook in `plugins/context_engine/lambda_tuner_plugin.py`:
1. Identify background / summary spans (marked by compaction layer)
2. Apply `cross_lingual_compress` to each span
3. Report token delta to lambda-tuner for calibration

### Configuration

```yaml
# In config.yaml under plugins.lambda_tuner:
cross_lingual_compress:
  enabled: true
  langs: ['de', 'zh']  # start conservative: 2 languages
  fidelity_floor: 0.85
  max_span_tokens: 200  # only compress spans <= 200 tokens
```

## Pitfalls

- NEVER compress code spans, commands, names, or structured data (JSON, YAML)
- NEVER apply to the system prompt core (cached prefix) — only to compressible context segments
- Fidelity floor below 0.80 risks semantic drift; use 0.85 minimum
- Translation adds latency: only invoke for sessions where compression is already triggered

## Measurement

Track: `tokens_before`, `tokens_after`, `fidelity_score`, `lang_chosen` per span.
Log to `~/.hermes/cache/cross-lingual-compress-log.jsonl` for lambda-tuner calibration.

## References

- MSCLAR et al. (2026): Cross-Lingual Prompt Compression (NeurIPS extended)
- hermes-lambda-tuner skill: lambda-tuner plugin overview
- rate-distortion-context-budget skill: token budget framework
