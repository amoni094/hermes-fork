---
name: cmtf-tool-filtering
description: "Use when checking tools. CMTF causal minimal filter."
tags: [tools, efficiency, wave16]
---

# CMTF Causal Minimal Tool Filtering

Based on arXiv:2606.06284. Training-free causal contracts reduce tool exposure 60-90%.

## Contracts (last-tool -> allowed next)
- read_file -> write/patch/navigate
- terminal -> read/patch/write
- write_file, patch -> terminal/read (verify)
- web_search -> web_extract/navigate
- browser -> interact tools
- skill_view -> skill_manage
- memory -> any

## Script
```bash
python3 ~/.hermes/hermes-scripts/cmtf-tool-frontier.py --goal "read and patch a file"
python3 ~/.hermes/hermes-scripts/cmtf-tool-frontier.py --state-file session.jsonl
python3 ~/.hermes/hermes-scripts/cmtf-tool-frontier.py --audit
```

## Cron: daily 7am (wave16-cmtf-tool-frontier-audit)

## Lessons
- 25-tool Hermes menu = ~60% reduction (vs 90% at 100 tools)
- If needed tool missing from frontier, add to matching contract effects
- Exposure log: cache/cmtf-exposure-log.jsonl
