# hermes-fork profile

This is the **amoni094/hermes-fork** build — a private fork of NousResearch/hermes-agent on branch `feature/adaptive-compression-plugin-api`.

Install: `~/.hermes/hermes-fork/` (venv at `.../venv`)
Profile: `~/.hermes/profiles/fork/`
Wrapper: `~/.local/bin/hermes-fork`

Key fork additions:
- Adaptive compression plugin API (4 hooks: on_session_start, pre_llm_call, pre_compress, on_session_finalize)
- lambda-tuner plugin (session classification, rr_scorer_lambda hints)
- TaskComplexityScorer, ChronoMem, domain-matched compaction eval (v4 complete)
- 22 commits on top of main; 182 tests passing

This is NOT the default Hermes home. It is a development fork for testing compression and plugin API changes.
