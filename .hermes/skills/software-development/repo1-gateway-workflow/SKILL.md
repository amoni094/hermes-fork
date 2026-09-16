---
name: repo1-gateway-workflow
description: >
  Use when: Work effectively in /var/home/rainbow/repo1: API, policy, optimizer, router, providers, cache, telemetry, and control UI.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [gateway, fastapi, routing, llm, policy, cache, telemetry]
    related_skills: [verification-before-completion, requesting-code-review, subagent-driven-development]
triggers:
  - Task involves working in or modifying the repo1 gateway project at /var/home/rainbow/repo1
  - User asks to change routing, policy, optimizer, cache, or telemetry in the local LLM gateway
  - Work touches the FastAPI gateway, provider config, or control UI in repo1
related_skills:
  - verification-before-completion
  - plan
  - requesting-code-review
  - subagent-driven-development
---

# Repo1 Gateway Workflow

Use this skill when working in `/var/home/rainbow/repo1`.

Before running commands or inspecting logs, read `/var/home/rainbow/repo1/docs/onboarding-agent-checklist.md` — it has environment setup, key contracts, pitfalls, and definition of done.

## What this repo is

An enterprise LLM gateway with:
- OpenAI-compatible API surface
- policy enforcement and redaction
- prompt optimization
- model routing
- provider adapters
- exact caching
- telemetry and readiness metrics
- a control UI with persisted runtime state

## Default collaboration patterns

Choose the pattern first.

- **Pipeline**: use for end-to-end request path changes across API -> policy -> optimizer -> router -> provider -> cache/telemetry -> tests/docs.
- **Producer-Reviewer**: use for focused fixes within one package.
- **Expert Pool**: use for cross-cutting work where security, latency, cost, and provider semantics interact.
- **Fan-out/Fan-in**: use for multi-package audits before one parent reconciles contracts.

In this Hermes runtime, avoid nested delegation trees; coordinate flat worker waves from the parent.

## Repo map

- `apps/api/src/llm_efficiency_gateway/` — API, control, UI, config, models
- `packages/optimizer/src/llm_gateway_optimizer/` — prompt transforms
- `packages/router/src/llm_gateway_router/` — model selection
- `packages/providers/src/llm_gateway_providers/` — upstream adapters
- `packages/policy/src/llm_gateway_policy/` — governance and redaction
- `packages/cache/src/llm_gateway_cache/` — exact cache
- `packages/telemetry/src/llm_gateway_telemetry/` — metrics and accounting
- `tests/` — API and core regression tests
- `docs/` — architecture, threat model, API notes

## High-value task splits

### Request-path feature
- Worker A: request/response contract, auth, control-surface impact
- Worker B: optimizer/router/provider behavior
- Worker C: cache/telemetry/tests/docs impact
- Parent: verify end-to-end behavior and failure handling

### Provider or routing change
- Worker A: adapter retry/health semantics
- Worker B: model tiers, routing heuristics, local-vs-frontier policy
- Worker C: readiness/metrics/UI exposure and tests
- Parent: confirm cache and policy invariants still hold

### Security/governance change
- Worker A: gateway key / tenant enforcement
- Worker B: sensitive-data redaction and provider restriction logic
- Worker C: observability and error-leakage behavior
- Parent: ensure no fallback bypasses policy

## Working rules

- Preserve OpenAI-compatible behavior unless the change explicitly updates the contract.
- When touching request handling, verify both non-stream and stream paths.
- Routing/provider changes must be checked with cache-hit semantics and telemetry together.
- Control UI/runtime-state changes must preserve persisted state across restarts.
- If docs claim a behavior, align tests or code proof in the same pass.

## Verification

Use targeted proof matching the touched path:

```bash
pip install -e .[dev]
pytest -q
pytest tests/test_gateway_core.py -q
pytest tests/test_gateway_api.py -q
ruff check .
uvicorn llm_efficiency_gateway.main:app --reload --host 0.0.0.0 --port 8080
```

## Pitfalls

- Verifying only core helpers after changing the API contract.
- Forgetting streaming behavior when non-stream tests pass.
- Changing routing/provider behavior without checking metrics and cache invariants.
- Updating runtime control state without confirming persistence semantics.
