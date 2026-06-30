# Tuning Boundary Map

Use this quick map before loading the full performance-tuning playbook.

- overall workflow/token efficiency -> `hermes-workflow-optimization`
- session bloat / missed compression checkpoints -> `hermes-context-hygiene`
- memory surface / continuity / retrieval choice -> `hermes-memory-surface-selection`
- runtime heat / local CPU / RAM / auxiliary-model pressure -> `hermes-performance-tuning`
- exact context cap and compression-setting decisions -> `hermes-context-budgeting`

If the user complaint is about local heat or slowness and you suspect Ollama/Hindsight/auxiliary calls, `hermes-performance-tuning` is the right specialist.
