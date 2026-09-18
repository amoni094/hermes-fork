---
name: hermes-llm-middleware-stack
description: Use when adding loop detection or cost guard to LLM calls.
tags: [middleware, llm, loop-detection, grounding, cost-guard]
related_skills: [agent-runtime-loop-patterns, adaptive-agent-reasoning]
---

# Hermes LLM Middleware Stack

Composable middleware chain for LLM calls. Ported from Denuto (src/harness/middleware.py). Each middleware wraps a call and runs logic before (pre-call) or after (post-call).

## Pattern

Each middleware: `async def __call__(ctx, next) -> ctx`
Stack: middleware_1 -> ... -> actual_llm_call
Use Python `contextvars.ContextVar` to share the active stack without threading it through every function.

## Available Middlewares

### LoopDetectionMiddleware (post-call)
MD5-hashes each LLM response per (session_id, agent_stage) key.
If same hash recurs: short-circuit, annotate context, do not call LLM again.
Catches stuck agents returning coherent but wrong identical output on every retry.
LIMITATION: syntactically identical responses only. Rephrased-but-same responses evade it. Full detection needs embedding cosine similarity.

### GroundingMiddleware (post-call)
Extracts quoted strings from response (double-quotes or backticks, >=6 chars).
Verifies each against source text via CPU fuzzy match.
Annotates ctx.metadata grounding counts. NEVER retries - annotates only.

### CostGuardMiddleware (pre-call)
Reads cumulative cost from contextvar. If cost > threshold: sets model_id_override to cheaper model.
Does NOT cancel the call - only redirects to cheaper model.
Fork plugin mapping: maps to pre_llm_call hook in ~/.hermes/hermes-fork/agent/plugin_llm.py

### FewShotInjectionMiddleware (pre-call)
Queries a FewShotProvider by ctx.agent_stage.
If examples returned: prepends (user, assistant) pairs to prompt.
NoopFewShotProvider always returns [] (safe default).

## Core Implementation

```python
import contextvars, hashlib
from dataclasses import dataclass, field

_stack_var = contextvars.ContextVar('middleware_stack', default=None)

@dataclass
class MiddlewareContext:
    prompt: str
    response: str = ''
    model_id: str = ''
    model_id_override: str | None = None
    session_id: str = ''
    agent_stage: str = ''
    contract_text: str = ''
    metadata: dict = field(default_factory=dict)

# Loop detection (sync version for Hermes scripts)
_response_hashes: dict[str, set] = {}

def check_loop(session_id: str, stage: str, response: str) -> bool:
    key = f"{session_id}:{stage}"
    h = hashlib.md5(response.encode(), usedforsecurity=False).hexdigest()
    if key not in _response_hashes:
        _response_hashes[key] = set()
    if h in _response_hashes[key]:
        return True
    _response_hashes[key].add(h)
    return False
```

## Fork Plugin Hook Mapping

Fork plugin API (hermes-fork/agent/plugin_llm.py):
- pre_llm_call -> CostGuardMiddleware + LoopDetectionMiddleware
- post_api_request -> GroundingMiddleware
- pre_compress -> context hygiene passes

CostGuard as fork plugin:
```python
def pre_llm_call(ctx, **kwargs):
    cost_so_far = ctx.get('cumulative_cost_usd', 0.0)
    if cost_so_far > COST_THRESHOLD:
        ctx['model_override'] = 'claude-haiku-4-5'
```

## Rules

- Pre-call: mutate ctx.prompt or ctx.model_id_override only
- Post-call: annotate ctx.metadata only, never mutate ctx.response
- Shadow/annotation paths NEVER raise - swallow and annotate
- Stack order: [LoopDetection, CostGuard, FewShot, Grounding]

GATE GAP (Tier-2): No CI gate yet. Proposed: test_middleware_stack.py in ~/.hermes/scripts/
