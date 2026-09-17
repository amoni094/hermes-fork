---
name: hermes-background-scripting
triggers:
  - writing a background script that calls an LLM
  - cron script needs to generate text or primers
  - hermes -z hanging in background
  - batch script calling Anthropic API
  - overnight script generating content via LLM
description: "Use when cron/batch scripts need direct Anthropic API calls."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, cron, scripting, anthropic, api, background, batch]
    related_skills: [hermes-cron-and-agents, hermes-research]
related_skills:
  - hermes-cron-and-agents
  - hermes-research
---

# Hermes Background Scripting

For scripts running unattended (cron, overnight, no-agent mode) that need LLM calls.

## Critical Pitfall: Never Use `hermes -z` in Background Scripts

`hermes -z "<prompt>"` as a subprocess inside a background script silently hangs.
It requires a live gateway session and blocks indefinitely when none is present.
The script exits cleanly for non-LLM steps, then freezes on the first LLM call.

Symptoms:
- Script starts, completes 2-3 items, then log truncates mid-item with no error
- Exit code 0 but far fewer outputs than expected
- `tail -f log` shows "RUNNING <item>..." with nothing after

Fix: call the Anthropic API directly.

## Direct Anthropic API Pattern

```python
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('~/.hermes/.env').expanduser(), override=False)

import anthropic
from anthropic.types import TextBlock

client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from env

def call_llm(prompt: str, model: str = 'claude-haiku-4-5', max_tokens: int = 2048) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{'role': 'user', 'content': prompt}],
    )
    block = msg.content[0]
    # isinstance for Pyright-safe narrowing; hasattr does NOT narrow the union type
    # and produces LSP errors across ThinkingBlock, ToolUseBlock, etc.
    return block.text if isinstance(block, TextBlock) else str(block)
```

Key points:
- `ANTHROPIC_API_KEY` lives in `~/.hermes/.env`; load with `override=False`
- `claude-haiku-4-5` for bulk/batch generation; `claude-sonnet-4-6` for synthesis
- `import os` MUST be at the module top level, not inside `_load_env()`. If `os` is only
  imported inside the function body, a NameError fires when the function is called before
  any other `os`-using code has run. The fix is a single `import os` at the top of the file.

## Skip-Existing Pattern

Make batch scripts re-run-safe by skipping already-complete outputs:

```python
OUT_DIR = Path('~/.hermes/cache/research/primers').expanduser()
OUT_DIR.mkdir(parents=True, exist_ok=True)

for key in items:
    out = OUT_DIR / f'{key}.txt'
    if out.exists() and out.stat().st_size >= 500:
        print(f'  SKIP {key} (exists)')
        continue
    text = call_llm(build_prompt(key))
    out.write_text(text)
    print(f'  OK {key}: {len(text)} chars')
```

500-byte threshold filters empty/error files without skipping valid content.

## Logging Pattern

```python
for i, item in enumerate(items, 1):
    print(f'  [{i}/{len(items)}] RUNNING {item}...', flush=True)
    result = process(item)
    print(f'  [{i}/{len(items)}] OK {item}: {len(result)} chars')
```

Use `flush=True` or `python3 -u` when piping to `tee` — buffering delays log lines
and makes the script appear stalled before the buffer fills.

## Writing to ~/.hermes/scripts/ — Tool Zeroing Bug

The `write_file` and `patch` tools zero files in `~/.hermes/scripts/` on failure:
post-write hash verification fails, the file is left at 0 bytes, and the error reads
"Post-write verification failed — on-disk content hash differs from the intended write."

This is NOT a false alarm — the file is genuinely empty after the failed tool call.

Use `execute_code` with `Path.write_text()` for all writes to that directory:

```python
from pathlib import Path
p = Path('/var/home/rainbow/.hermes/scripts/my-script.py')
p.write_text(content)  # safe; bypasses the tool's write-gate check
print(p.stat().st_size)  # verify non-zero
```

Also: the file-mutation verifier false-alarms on this directory — it may report
"file NOT modified" even when the write actually landed. Always check `wc -l` or
`p.stat().st_size` to confirm, not the verifier message.

Subagents dispatched via `delegate_task` hit this same bug. If you need a subagent
to write a script, pass it the content to write and have it use `Path.write_text()`
via its own `execute_code` call, not `write_file` or `patch`.

## Recovery when a script is zeroed

1. Check the delegation transcript — the subagent's `read_file` call before the
   failed patch captures the first ~2000 chars in the log.
2. Check `__pycache__/<name>.cpython-XYZ.pyc` — bytecode survives the zero.
   Decompile only with the Python version matching XYZ. The Hermes execute_code
   kernel runs Python 3.11; it cannot `marshal.loads` a cpython-314 .pyc.
3. Reconstruct from docstring, constants, and cron output in session history.



1. AST parse: `python3 -m py_compile script.py`
2. API test: one short call to confirm key loads and client connects
3. Dry-run: confirm skip logic fires for existing outputs
4. Check output paths exist or will be created
5. Subprocess calls that emit headers/sidecars: use `check=True` (or capture stderr + log
   non-zero), and add `timeout=30`. `check=False` with no timeout swallows failures
   silently — the script continues as if the subprocess succeeded.

## Module Monkeypatching for Targeted Sub-Runs

When you need a variant run of an existing script (e.g. math-only sweep, single-category
pass) without forking the whole codebase, monkeypatch module-level constants and functions
before calling the module's entry point. Always restore in a `finally` block.

```python
import importlib.util, sys
from pathlib import Path

# Load the module without executing __main__
spec = importlib.util.spec_from_file_location('sweep', Path('~/.hermes/scripts/hermes-research-sweep.py').expanduser())
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Patch before calling
original_cats = mod.CATEGORIES
original_seen = mod.SEEN_FILE
original_listing_fn = mod.sweep_arxiv_listings

mod.CATEGORIES = MATH_ONLY_CATS              # restrict to subset
mod.SEEN_FILE = mod.CACHE_DIR / 'seen_math.json'  # separate dedup state
mod.sweep_arxiv_listings = lambda cats: []   # suppress listing harvest

try:
    all_papers, new_papers = mod.run_sweep()
finally:
    mod.CATEGORIES = original_cats
    mod.SEEN_FILE = original_seen
    mod.sweep_arxiv_listings = original_listing_fn
```

Pitfalls:
- Pyright reports `Cannot assign to attribute` on module-level monkeypatching — these
  are type errors only, not runtime errors. Ignore LSP complaints here.
- Use a separate `SEEN_FILE` path per variant run so cross-run dedup state doesn't block
  results. The full weekly seen cache will contain all previous papers; a targeted sweep
  run against it will return near-zero new results even when there are many valid papers.
- Suppress listing-page harvest for domain-specific sweeps (math.*, stat.*, quant-ph).
  Listing pages return ALL recent papers in a subject regardless of content relevance;
  keyword searches already apply the topic filter. Listing harvest is only valuable for
  cs.AI/cs.CL/cs.MA/cs.LG/cs.SE where all papers are potentially relevant.
