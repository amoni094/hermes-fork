---
name: anchored-context-distillation
description: "Use when context fills with tool output. Compress floatsam."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
triggers: []
---

# Anchored Context Distillation

Source: arXiv:2609.31430 - Compress What You See, Not What You Say.

## Problem

Tool observations dominate agent context. Naive truncation discards information needed by later actions.

## Key insight

Anchors = tool outputs cited by subsequent reasoning steps. Floatsam = outputs never referenced again.
Only floatsam is eligible for aggressive compression.

## Procedure

1. Mark anchors: annotate which prior tool outputs each reasoning step cites. NEVER compress anchors.
2. Compress floatsam: outputs not cited after 2+ steps -> keep first sentence + numeric results + errors.
3. Threshold: compress when context > 60% of limit. Target: bring below 40%.
4. Never compress: the MOST RECENT tool result, any exit_code != 0, any secret/credential pattern.

## Integration with cliff-compaction

Run anchored distillation BEFORE cliff-compaction so it operates on a smaller anchor-preserved context.

## Anchor detection

- Explicit quote: reasoning contains a substring from the tool output
- Structural cite: reasoning references file path / function name / line number from output
- Decision cite: "since X returned Y, I will..." pattern

## Metrics

- Target: compression >= 40%, anchor recall = 100%
