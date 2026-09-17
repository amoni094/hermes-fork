# Subagent Loop Cap and Retry Patterns
# From Aug 2026 multilingual trading strategy research session

## Loop cap vs context exhaustion — diagnosis

Two distinct failure modes produce thin/empty subagent output files:

| Signal | Loop cap | Context exhaustion |
|--------|----------|--------------------|
| api_calls | <15 | >15 |
| todos status | incomplete | complete |
| log endpoint | mid-research, no write_file | after todos done, no write_file |
| cause | repeated same query hits guardrail | ran out of tokens before final write |
| fix | add "at most 2 attempts per topic, vary queries" | add "CRITICAL: write file before stopping" |

## Retry prompt — mandatory additions for loop-cap retries

Add ALL THREE to the retry prompt:
1. "For each topic, make at most 2 web_search attempts with different queries, then move
   on. If results are off-topic (weather/medical/unrelated), change query immediately or
   skip and note [SEARCH FAILED]. Do NOT retry the same query twice in a row."
2. "Total tool calls budget: 30 max."
3. "CRITICAL OUTPUT STEP: After all research, write the output file using write_file.
   Then confirm: terminal('ls -la /tmp/<output-file>.md'). Do not stop before this step."

## Check-before-retry discipline

Before dispatching a retry, run: terminal("wc -l /tmp/<output-file>.md")
A batch result may be delivered before a subagent's late write_file completes.
The output file may already exist and be complete by the time you check.
Retrying without checking produces a redundant shorter version that can overwrite
the richer original.

## Multilingual sweep — garbage returns for non-English queries

Arabic, Korean, Polish, and some Eastern European queries against general search
providers frequently return weather data, medical results, Grammy rankings, or
completely unrelated content instead of finance/academic papers.

When this happens:
- Do NOT retry the native-language query; it produces the same garbage
- Immediately switch to an English-language query covering the same topic
- Most non-English academic finance papers are indexed in English anyway
- Note [SEARCH FAILED - off-topic results] and move on
- Allocate at most 2 total attempts (1 native-language, 1 English fallback)

Observed Aug 2026: Arabic "momentum Saudi stock market" → weather/IMDB results.
Korean stock exchange query → Grammy results. Fix: English query + [SEARCH FAILED] note.

## Opus-4-8 orchestration pattern (Aug 2026)

For large multilingual research sweeps (9+ languages, 3+ strategy clusters):
1. Use `hermes chat -q "design N parallel research clusters for [domain]..." -m claude-opus-4-8`
   to get cluster decomposition. This produces topic-isolated, non-overlapping clusters
   with specific scope, anti-fabrication rules, access tips, and output format.
2. Dispatch each cluster as a separate leaf subagent (sonnet-4-6) with the Opus-designed
   prompt verbatim. Do not simplify the Opus prompt — the specificity is what prevents
   loop caps and fabrication.
3. When a cluster subagent hits loop cap: retry with the same Opus prompt PLUS the three
   mandatory anti-loop additions above.
4. Synthesis: read all cluster files, integrate into main report as new numbered Parts.
   Run adversarial-review pass after integration (new content bypasses prior review passes).
