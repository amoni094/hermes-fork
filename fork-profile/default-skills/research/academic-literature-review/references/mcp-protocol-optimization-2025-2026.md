# MCP (Model Context Protocol) Optimization — Schema Bloat, Response Bloat, Efficiency
Compiled July 2026. General web/industry sources + English arXiv. Non-English academic search
returned only derivative commentary (see academic-literature-review SKILL.md pitfall on this).

## The problem, quantified
- Anthropic (internal): tool defs consumed 134K tokens before optimization in one case; a 5-server
  setup (GitHub 35 tools, Slack 11, Sentry 5, Grafana 5, Splunk 2 = 58 tools) = ~55K tokens before
  the conversation starts.
- Atlassian: GitHub's official MCP server alone = 94 tools / ~17.6K tokens.
- agentmarketcap.ai: enterprise MCP deployments burn 60-80% of context budget on tool definitions;
  ~10,000 public servers, 72% average context waste (Apr 2026 figure, industry-reported not peer-reviewed).
- arXiv 2509.25292 (Shandong University + NTU Singapore, Nov 2025) — first large-scale empirical
  measurement of the public MCP ecosystem: 17,630 listings crawled across 6 marketplaces, only
  49.1% valid/maintained. 21.9% of servers inactive >1 year. Dependency monocultures (Java servers
  universally on Spring) create cascading-vuln risk (e.g. SpringShell).

## Schema bloat — solutions
- **Anthropic Tool Search Tool / `defer_loading`** (Nov 2025, official beta `advanced-tool-use-2025-11-20`):
  mark tools `defer_loading: true`; lightweight search tool (~500 tokens) loaded upfront, matching
  tools expanded on demand. Measured 85% token reduction (191,300 vs 122,800 tokens preserved);
  Opus 4 MCP-eval accuracy 49%→74%, Opus 4.5 79.5%→88.1%. Compatible with prompt caching (deferred
  tools excluded from cached prefix).
- **Atlassian mcp-compressor** (OSS, github.com/atlassian-labs/mcp-compressor, Mar 2026): drop-in
  proxy wrapping any MCP server with a 2-3 tool generic interface (`get_tool_schema`, `invoke_tool`,
  optional `list_tools`). Tunable tiers on a 94-tool GitHub-style server: 17,600 → 3,900 → 3,300 →
  2,200 → 500 tokens (up to 97% reduction). No changes needed to server or client.
- **Speakeasy/Gram Dynamic Toolsets**: `search_tools` / `describe_tools` / `execute_tool` split.
  96.7% input token reduction (simple tasks), 91.2% (complex), 100% success maintained across
  40-400 tool toolsets. Tradeoff: 2-3x more tool calls, ~50% more wall-clock time.
- **RAG-MCP** (arXiv 2505.03275, May 2025) — academic formalization of retrieval-based tool
  selection: semantic retrieval picks relevant MCP(s) before the LLM sees any tool list. >50%
  prompt token reduction, 3x tool-selection accuracy (43.13% vs 13.62% baseline). Confirms bloat
  degrades accuracy, not just cost.
- **Code execution with MCP** (Anthropic engineering blog) / Cloudflare **Code Mode**: present
  tools as a code API in a sandbox instead of per-call JSON turns; model writes code to
  orchestrate/filter, avoiding both schema and response bloat. Complementary to defer_loading,
  not a replacement.

## Response bloat — solutions
- MCP spec native: cursor-based pagination (`NextCursor`), not offset-based.
- **Programmatic Tool Calling** (Anthropic, same Nov 2025 release): multi-tool workflows run in a
  code sandbox so intermediate results (e.g. 2,000+ line items from 20 API calls) never enter
  context directly — only the final computed answer does.
- ResourceLink / reference-handle pattern: return a pointer to a large resource, let the agent
  fetch only the needed slice (same principle as this session's own web_extract head+tail
  truncation with disk-cached full text).
- Document tool return shapes explicitly in schema descriptions — improves model's ability to
  write correct parsing code against responses (Programmatic Tool Calling docs).

## Other efficiency levers
- Prune dead/abandoned MCP servers from your own config — arXiv 2509.25292 found >50% of public
  listings are placeholders/forks; this is a legitimate "reduce bloat" action, not just schema design.
- Tool Use Examples (1-5 concrete input examples per tool) improve parameter accuracy without
  growing the schema — cheaper than verbose prose descriptions.
- Verbose/ambiguous tool descriptions are also an attack surface (tool-poisoning / prompt
  injection via tool description) per MCPTox (arXiv 2508.14925) and STRIDE threat-modeling
  (arXiv 2603.22489) — tight minimal schemas are a security control, not just a token control.
- Local tool relevant to this: `lintlang` (~/.hermes/integrations.disabled/lintlang, currently
  disabled) — zero-LLM static linter for tool-description ambiguity/schema-intent mismatch,
  deterministic PASS/REVIEW/FAIL output, H1-H7 pattern detectors. Re-enable + run before adding
  new MCP servers to a Hermes config.

## Key arXiv IDs (quick index)
| arXiv | Title | Contribution |
|-------|-------|--------------|
| 2505.03275 | RAG-MCP | retrieval-based tool selection, >50% token cut, 3x accuracy |
| 2509.25292 | Measurement Study of MCP Ecosystem | first large-scale empirical study, 8,401 servers/clients |
| 2503.23278 | MCP: Landscape, Security Threats, Future Directions | lifecycle + threat taxonomy survey |
| 2508.14925 | MCPTox | tool-poisoning attack benchmark |
| 2504.08623 | Enterprise-Grade Security for MCP | security hardening framework |
| 2603.22489 | MCP Threat Modeling (STRIDE) | client-side threat modeling |
| OpenReview ty6y1WiVzk | ProMCP | token-flow/latency profiling across Host-Client-Server (bot-walled at review time — revisit) |
