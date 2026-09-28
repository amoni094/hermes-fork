---
name: cross-lingual-compression-audit
description: "Use for multilingual text. English compressors widen gap."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers: []
---

# Cross-Lingual Compression Audit

Source: arXiv:2608.26175 - Lost in Compression: A Controlled Cross-Lingual Audit.

## Core finding

English-trained extractive compressors (e.g. LLMLingua-2) perform WORSE on non-English text.
They over-compress tokens dense in other languages. The token premium for non-English (1.3-1.8x) is widened.

## Rules

1. Never apply English-trained extractive compression to non-English spans.
2. Language-aware budget: scale token budget proportionally to token premium per language.
3. Fallback: use positional (keep first + last N sentences per span) when no language-aware compressor available.
4. Preserve multilingual anchors: proper nouns, numbers, quoted phrases in any language.
5. Audit trigger: non-English compressed shorter than English by >2x -> flag as potential misfire.

## Integration with hermes-research-sweep

Multilingual sweep returns zh/ru/ja/de/fr results. When summarizing:
- Keep title + arXiv ID verbatim
- Preserve abstract first sentence verbatim
- Compress only middle body sentences
- Never score non-English summaries with English-trained relevance models
