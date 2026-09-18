## Adversarial topology audit

Run this as a higher-order pass when memory drift is suspected or the system has been
running for weeks without a structural review. Distinct from the standard consolidation
loop — this looks for cross-surface inconsistencies, not just individual fact quality.

### Step A: Gather all surfaces
Collect current content of ALL surfaces in one pass (batch the terminal reads):
- `~/.hermes/memories/MEMORY.md` and `USER.md` (cat, not read_file — dedup cache may suppress)
- Active CTX files: `SecondBrain/CTX-*.md`
- Obsidian MEMORY.md: `SecondBrain/MEMORY.md`
- Cron list: `hermes cron list` (verify the live count before trusting what CTX-systems says)
- Char counts: `wc -c` all files — budget pressure is a finding in itself

Run ALL these reads in a single parallel batch before analysis. Do not read one,
analyse, then read the next — you need the full cross-surface picture before scoring.

**Always run `wc -c` on MEMORY.md and USER.md as the very first step.** USER.md has a
lower char limit (1375 vs 2200). If it is at or over budget, any subsequent memory write
will fail silently or be rejected. Budget pressure itself is a CRITICAL finding.

### Step B: Cross-check for these failure modes (in priority order)

| Severity | Pattern | Example |
|---|---|---|
| CRITICAL | Contradiction across surfaces | MEMORY says "Opus=escalation only"; USER says "Opus=orchestrator"; CTX says both |
| CRITICAL | Status conflict (active vs dormant) | CTX lists MemPalace as active layer; MEMORY says dormant |
| HIGH | Shadow copy / verbatim duplicate | CTX-now.md copies USER.md preferences line-for-line |
| HIGH | Stale enumeration | CTX-systems lists 6 cron jobs; actual live crons = 9 |
| HIGH | Credential in always-injected memory | API key literal in MEMORY.md = sent to provider every turn |
| HIGH | Intra-file duplicate (intra-file) | Memory Stack and Active MCP Servers both list URLs/status for same services — merge into one section with systemd unit names inline; remove standalone section |
| HIGH | Permanent constraint tracked as open loop | "Hindsight has no per-ID delete endpoint" parked in Open Loops — it will never be "done"; belongs in Maintenance Notes |
| HIGH | Rare-event note in prompt-resident memory | Maintenance gotcha (e.g. temp=None patch after uv sync), agent design principle, or named cron list belongs in CTX-systems, not MEMORY.md — every token in MEMORY.md is paid on every turn |
| HIGH | Task-log block in prompt-resident memory | Pending skill patches, "next session" TODOs, or deferred work items in MEMORY.md are task-logs masquerading as durable facts — they bloat prompt cost and become stale immediately. Remove them; the work belongs in a skill or CTX-now Open Loops. Validated: "PENDING SKILL PATCHES" block cost 635-767 chars (30%+ of budget) across two sessions. |
| HIGH | Session log masquerading as current state | CTX-now "Current Phase" decays into "what the last session resolved" — rephrase as stable state snapshot: Memory topology: stable as of <date>; last audit resolved N findings |
| MEDIUM | Self-referential open loop | "CTX files due for next review" added to Open Loops when Staleness Signal section already encodes the same rule — remove; a loop item must be completable, not a rule restatement |
| MEDIUM | Stable architecture in "Recent Decisions" | Decisions >7 days old (Graphiti bulk-ingest policy, CTX pattern origin) are stable architecture, not recent — move to CTX-systems or drop; keep only decisions from last 7 days |
| MEDIUM | Stable tooling config in "Current Focus" | Reasoning conventions (Graphiti group format, API call, skip rules) sitting in CTX-now unchanged for multiple sessions — move to CTX-systems; CTX-now is for active/current state only |
| MEDIUM | Ordering conflict | Skill says query order A→B→C; CTX says C→A→B |
| MEDIUM | Convention only in skill, not injection-resident | Graphiti group_id only in skill body; agents without skill load will use wrong ID |
| MEDIUM | Project lifecycle drift | Graphiti MCP Integration still in Active section after 7+ days as operational infra; should move to Completed |
| LOW | Completed entries accumulating without archive policy | CTX-projects On Hold/Completed grows indefinitely — add one-line policy: keep for 30 days then archive to vault note |
| HIGH | Retention policy entry past stated window | A Completed entry that already exceeds the retention period is HIGH — if the first entry immediately violates the policy just added, the policy is worthless; remove and vault-archive immediately |
| HIGH | Inactive project sitting in Active section | Entry marked "inactive" in Active / Recent will mislead any agent reading section as current workload — move to Completed; if inactive >30 days, remove to vault |
| MEDIUM | Empty section shell with placeholder | "Nothing to record — update when…" header is noisier than no section; delete the header; append "Add ## [Section] only when content exists" to Staleness Signal |
| LOW | MCP tool parameter name asserted without live verification | Writing search/call examples in CTX-systems without confirming exact param names — add "verify param name on first use" inline to avoid silent wrong-group queries |
| HIGH | No compression/auxiliary/fallback_model in config.yaml | These keys are absent by default on minimal configs; sessions accumulate unbounded context, compression falls to main model (premium cost), and no failover fires. Run `grep -E 'compression|auxiliary|fallback_model' ~/.hermes/config.yaml` as first audit step. |
| HIGH | Cron deliver=origin on CLI profile | CLI Hermes has no gateway — deliver=origin silently drops output. Affects watchdogs added in messaging-platform sessions then used on CLI. Always verify deliver field when auditing cron jobs on a CLI-only profile. |
| HIGH | Never-used skills inflating available_skills prompt block | 60+ never-used skills = ~60 extra header lines injected every turn. Platform-incompatible skills (macOS/HomeKit/cloud SaaS) are safe disable candidates on Linux. Run .usage.json analysis each audit pass. |
| MEDIUM | .usage.json ghost references inflate never-used count | Skills in `.archive/` keep entries in `.usage.json` and appear as "never used". Exclude `.archive/` when computing true active count: `find ~/.hermes/skills -name 'SKILL.md' \| grep -v '/.archive/' \| wc -l`. Do not delete based on .usage.json alone — verify the skill dir still exists under an active path. |
| MEDIUM | CTX-systems.md stale cron reference | CTX-systems lists cron jobs in prose and drifts on any add/delete. Always cross-reference its Background Automation section against live `hermes cron list` output. Specific vector: deleted job entries that reference complementary jobs that now no longer have a partner. |

### Step C: Propose before applying
Always present the full finding list to the user (severity + surface + specific text diff)
before making any changes. Apply only after explicit approval.

Use this finding taxonomy for labelling (makes proposals scannable):
- `DUP-*` — duplicate or shadow copy across surfaces
- `STRUCT-*` — structural misclassification (e.g. constraint in wrong section)
- `STALE-*` — outdated fact (date, version, status, completed task still listed as active)
- `GAP-*` — missing fact that should exist on this surface
- `MISS-*` — fact present on wrong surface, absent from canonical one

### Step D: Fix order
1. MEMORY.md / USER.md (prompt-resident — highest urgency)
2. CTX files (bootstrap orientation — high urgency)
3. Skills (procedural — medium urgency)

### Step E: Verify after applying
After all patches, check:
- File sizes (`wc -c`) — confirm reductions landed
- Spot-check each changed section with `grep -A<n>` — confirm the right text landed
- Cross-check for any new duplicates introduced by the fix (moving a fact to surface B may
  duplicate it if B already had it in a different section — always check all sections of the
  destination, not just whether the destination file exists)
