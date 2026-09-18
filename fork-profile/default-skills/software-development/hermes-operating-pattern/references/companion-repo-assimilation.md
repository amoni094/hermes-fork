# Companion-Repo Assimilation

Use this note when a task asks whether ideas from a companion repo, wrapper app, or fork should be ported into Hermes itself.

## Selection heuristic

Prefer ideas that are:

- small enough to land in core without importing a whole new subsystem
- useful in CLI / setup / runtime behavior, not only in a specific GUI
- zero-fork compatible
- verifiable with targeted tests
- local-first and friction-reducing

Reject or defer ideas that are:

- mostly UI chrome
- tightly coupled to a separate control plane
- specific to one app's state model
- expensive to maintain in core Hermes for marginal gain

## High-value pattern from this session

### Local OpenAI-compatible endpoint auto-discovery

If custom-endpoint setup starts with a blank base URL, probe common local servers and offer the user a picker instead of cancelling immediately.

Concrete endpoints used in this session:

- ~~Ollama — `http://127.0.0.1:11434/v1`~~ (REMOVED Jul 2026 — uninstalled)
- LM Studio — `http://127.0.0.1:1234/v1`
- Atomic Chat — `http://127.0.0.1:1337/v1`
- vLLM / generic OpenAI server — `http://127.0.0.1:8000/v1`
- llama.cpp — `http://127.0.0.1:8080/v1`

Implementation shape:

1. Reuse existing `/models` probing logic instead of adding a separate network stack.
2. Keep per-endpoint probe timeout short (~0.8s) because these are localhost checks.
3. Deduplicate by resolved base URL, not only by label.
4. Show a short model preview when available.
5. Fall back to existing behavior if nothing is detected.
6. Add targeted tests for both the probe helper and the interactive blank-URL flow.

## Why this was worth porting

The idea came from companion projects that optimize local-first UX, but the useful behavior is independent of their UI shells. It reduces setup friction in core Hermes without coupling Hermes to a desktop or dashboard architecture.
