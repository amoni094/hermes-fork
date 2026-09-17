# Zero-Mem Quick Note (arXiv:2607.29377)

57.6% faster memory ops. No LLM calls in consolidation — deterministic retrieval from raw traces.
Two indexes: entity-context graph + temporal hierarchy. LLM only for final-QA reader.

Key for Hermes consolidation: run a deterministic conflict-detection pre-pass BEFORE LLM synthesis
to surface contradictions rather than letting the LLM paper over them.

Code (post peer review): https://github.com/TheMoon0815/Zero-mem

Full findings: references/community-sweep-aug12-2026b.md
