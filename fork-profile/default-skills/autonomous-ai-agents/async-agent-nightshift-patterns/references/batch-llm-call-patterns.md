# Batch LLM Call Patterns for Overnight Scripts

For overnight/background scripts that need to call an LLM for N items (e.g. generating
primers, classifying papers, summarizing sessions), use the provider SDK directly.
Do NOT use `hermes -z` subprocesses.

## Why not hermes -z

- Depends on gateway state; hangs silently when gateway is busy
- Slow: full session initialization per call (~10-30s overhead)
- No error surfaced on hang: log cuts off mid-entry, script exits
- Not recoverable: no partial-completion checkpoint

## Anthropic SDK Pattern (canonical)

```python
from dotenv import load_dotenv
from pathlib import Path
from anthropic.types import TextBlock
import anthropic

load_dotenv(Path('~/.hermes/.env').expanduser(), override=False)
client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY

def call_llm(prompt: str, model: str = 'claude-haiku-4-5', max_tokens: int = 2048) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{'role': 'user', 'content': prompt}]
    )
    block = msg.content[0]
    return block.text if isinstance(block, TextBlock) else str(block)
```

Key: ANTHROPIC_API_KEY is in ~/.hermes/.env. Use dotenv load, not os.environ directly.
TextBlock isinstance check required — other block types (ToolUseBlock etc) have no .text.

## Skip / Idempotency Pattern

For N-item batch jobs, always skip items with existing valid output:

```python
OUT_DIR = Path('~/.hermes/cache/research/primers').expanduser()

def should_skip(cat_key: str) -> bool:
    out = OUT_DIR / f'{cat_key}.txt'
    return out.exists() and out.stat().st_size >= 500

for cat_key in ALL_CATS:
    if should_skip(cat_key):
        print(f'  SKIP {cat_key} (already done)')
        continue
    text = call_llm(build_prompt(cat_key))
    (OUT_DIR / f'{cat_key}.txt').write_text(text)
```

This makes the script safe to re-run after partial completion.

## Model Selection for Batch Jobs

- claude-haiku-4-5: default for classification, summarization, primer generation (~$0.001/call)
- claude-sonnet-4-6: for tasks requiring stronger reasoning (use sparingly, ~20x cost)
- Never use reasoning models (claude-opus, o3) for batch overnight jobs — cost explodes

## Verification Before Running Overnight

```python
# Quick API sanity check before the batch loop:
msg = client.messages.create(model='claude-haiku-4-5', max_tokens=10,
    messages=[{'role': 'user', 'content': 'say ok'}])
assert isinstance(msg.content[0], TextBlock) and 'ok' in msg.content[0].text.lower()
print('API OK')
```

Fail fast if the API key is wrong or the model is unavailable, before wasting time on the loop.
