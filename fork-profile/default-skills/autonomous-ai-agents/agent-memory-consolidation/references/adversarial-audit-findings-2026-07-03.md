# Adversarial Memory Audit — Session Log 2026-07-03

Two consecutive adversarial passes on the same memory topology.
Pass 1 resolved 17 findings; Pass 2 resolved 13 findings.
Combined reduction: ~9280 → ~8352 bytes across all surfaces.
MEMORY.md alone: 1818 → 1283 bytes (29% reduction, 535 chars freed).

## Pass 1 Findings (2026-07-03 morning)

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| DUP-A | HIGH | CTX-systems | LLM routing duplicated MEMORY.md routing block verbatim | Replaced with one-liner pointer to MEMORY.md |
| DUP-B | HIGH | MEMORY.md | Firecrawl info in both MEMORY.md and CTX-systems | Removed from MEMORY.md; CTX-systems authoritative |
| DUP-C | HIGH | CTX-systems | GitHub PAT constraint in both MEMORY.md and CTX-systems Known Bugs | Removed from CTX-systems (not a bug); kept in MEMORY.md |
| STRUCT-1 | HIGH | CTX-systems | "Known Bugs" conflated bugs, policy, and auth constraints | Renamed "Maintenance Notes"; WhatsApp + GitHub PAT lines removed |
| STRUCT-2 | HIGH | MEMORY.md | DecodingAI entry dense/vague | Compressed to one line |
| STRUCT-3 | HIGH | MEMORY.md | Delegation entry had non-sequitur "A/B: parallel subagents" tack-on | Cleaned |
| MISS-1 | HIGH | MEMORY.md | Graphiti temperature=None patch missing | Added |
| STALE-1 | MEDIUM | CTX-now | Phase block described 2026-07-02 session | Updated to reflect memory audit work |
| STALE-2 | MEDIUM | CTX-projects | Graphiti MCP Integration still "Active" | Moved to Completed |
| STALE-3 | MEDIUM | CTX-now | Open Loops had stale items | Cleared resolved ones |
| STALE-4 | LOW | CTX-systems | Config version number drift | Replaced with `hermes config check` pointer |
| DUP-5 | LOW | MEMORY.md + CTX-systems | Memory stack stub vs full spec | Acceptable two-level pattern, kept |
| STRUCT-4 | LOW | CTX-now | Vault MEMORY.md workflow pref duplicates USER.md | Different consumers, harmless |
| STRUCT-5 | LOW | CTX-systems | Cron list accurate | No fix needed |
| MISS-2 | LOW | MEMORY.md | Fallback chain inline vs skill ref | Resolved by DUP-A fix |

## Pass 2 Findings (2026-07-03 afternoon)

| ID | Sev | Surface | Issue | Fix |
|---|---|---|---|---|
| DUP-A | HIGH | MEMORY.md | Memory Stack line repeated port/service detail from CTX-systems | Stripped to routing hint + dormant flag only |
| DUP-B | HIGH | MEMORY.md + CTX-systems | Graphiti temp=None in both (rare maintenance event, not per-turn) | Removed from MEMORY.md; CTX-systems Maintenance Notes only |
| MISS-A | HIGH | MEMORY.md | Memory bridge line named 3 crons that are already in CTX-systems cron table | Compressed to "3 crons (see CTX-systems cron table)" |
| STRUCT-A | MEDIUM | CTX-now | Current Phase was a session log, not stable state | Reframed as stable state snapshot |
| STRUCT-B | MEDIUM | CTX-now | Reasoning convention (stable tooling) sitting in Current Focus file | Moved to CTX-systems |
| DUP-C | MEDIUM | CTX-now | "CTX files due for review" in Open Loops AND in Staleness Signal rule | Removed from Open Loops (self-referential) |
| DUP-D | MEDIUM | CTX-now | Recent Decisions block had decisions >7 days old (Graphiti policy, CTX pattern) | Moved stable facts to CTX-systems; cleared completed-action entries |
| STRUCT-C | MEDIUM | CTX-systems | Active MCP Servers section duplicated Memory Stack URLs/dormancy | Merged into Memory Stack with systemd unit names; removed standalone section |
| STALE-A | MEDIUM | CTX-projects | Fable-5 and Ouroboros listed Active despite milestones being finalized | Moved both to Completed |
| STRUCT-D | LOW | CTX-systems | Ollama model list in CTX-systems overlaps MEMORY.md Ollama note | Acceptable — CTX-systems has fuller detail; no change |
| STALE-B | LOW | CTX-projects | Completed entries had no archive policy | Added "keep 30 days, then archive to vault note" |
| STRUCT-E | LOW | MEMORY.md | Agent design principle (fresh context > multi-agent) occupies prompt-resident budget | Removed; skills are canonical for design principles |
| STRUCT-F | LOW | MEMORY.md | Guardian API key config in prompt-resident memory every turn | Moved to CTX-systems Local Services |

## Key Heuristics Validated

1. **MEMORY.md token cost heuristic**: rare-event maintenance notes, design principles,
   named cron lists = low per-turn value. Removing 4 such entries freed 535 chars (29%).

2. **CTX-now is state, not log**: Current Phase must describe stable NOW state, not
   what the previous session resolved. Previous session outcomes live in session history.

3. **Intra-file section dedup**: when moving a fact between sections of the same file
   (e.g. Local Services → Maintenance Notes) verify the destination didn't already have
   it in another form. Active MCP Servers was a full duplicate of Memory Stack details
   within CTX-systems — one should have been detected by the prior audit.

4. **Self-referential open loops**: if a loop item is a policy trigger already encoded
   in the same file (Staleness Signal), removing the loop item loses nothing.

5. **Stable tooling config drift to Current Focus**: Reasoning conventions (Graphiti
   group format, API calls) accumulated in CTX-now across multiple sessions despite
   being unchanged. CTX-systems is the correct home for stable tooling configuration.
