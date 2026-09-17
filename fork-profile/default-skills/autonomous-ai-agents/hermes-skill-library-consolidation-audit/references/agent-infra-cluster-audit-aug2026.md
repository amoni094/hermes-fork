# Agent Infrastructure & Routing Cluster Audit — August 2026

Conducted as a subagent pass over 33 skills in the `autonomous-ai-agents/` + `superpowers/` + `software-development/hermes-semantic-skill-routing` cluster.

## Confirmed findings

### HIGH severity

| Skill | Issue | Fix |
|-------|-------|-----|
| `computer-use` | Cluster manifest listed path `skills/computer-use/SKILL.md` — **does not exist**. Real path: `/var/home/rainbow/.hermes/skills/computer-use/SKILL.md` (top-level, not under `skills/`). | Update any catalogs/cross-references to use the correct top-level path. |
| `harness-first-agent-design` | Body section "## llama.cpp --tools-runtime Rootless Container Sandboxing" describes a local LLM (llama-server) feature. Ollama/local LLMs removed Jul 2026; section is not applicable to this Anthropic-API-only environment. | Scope section with a "local-model-only" callout or remove it. |
| `hermes-semantic-skill-routing` | Description (57-char window) contains inline parenthetical: "Ollama was uninstalled 2026-07-12" — pollutes the routing signal. Body also references an Ollama embedding section as "deprecated" but it may still be present. | Remove parenthetical from description. Confirm/delete Ollama body section. |

### MED severity

| Skill | Issue | Fix |
|-------|-------|-----|
| `messaging-consent-boundaries` | Duplicate `related_skills` field: one under `metadata.hermes.related_skills` `[email-compose-and-send, computer-use]` and another as top-level `related_skills: [autonomous-agent-loop-design, verification-before-completion]`. Two lists diverge. | Consolidate into single top-level `related_skills` covering all four. Remove `metadata.hermes.related_skills`. |
| `hermes-self-evolution` vs `self-improve-agent` | Boundary between the two skills is poorly marked. Both cover skill self-improvement with human gating. `hermes-self-evolution` = offline DSPy/GEPA repo only. `self-improve-agent` = post-task lesson extraction in live session. | Add explicit mutual boundary statement to each skill. (Both not curator-managed — requires `hermes curator adopt`.) |
| `autonomous-ai-agents` (router) | Missing routing entries for `agent-browser-troubleshooting`, `agent-runtime-stack-debugging`, `agent-task-signoff`. | Add routing entries under these child skills. (Not curator-managed — requires `hermes curator adopt`.) |
| `agent-task-signoff` | All triggers are exact quoted phrases — too specific for automatic matching when no user explicitly says those words. | Add situational triggers for post-parallel-agent synthesis, multi-phase task wrap-up, etc. (Not curator-managed.) |
| `anthropic-agent-api-patterns` | Triggers are nearly all exact quoted strings. A user building an agentic loop would not phrase their question using these keywords. | Add broader situational triggers. (Not curator-managed.) |
| `hermes-skill-library-consolidation-audit` | Missing trigger for "cluster audit report reveals stale content across many skills". | Add trigger. |

## Not-curator-managed skills (cannot be patched autonomously)

The following skills in this cluster are `created_by=None` (user-owned) and require
`hermes curator adopt <name>` in a foreground session before autonomous patching is possible:

- `hermes-semantic-skill-routing`
- `harness-first-agent-design`
- `autonomous-ai-agents`
- `self-improve-agent`
- `hermes-skillspector-guard-maintenance`
- `agent-task-signoff`
- `anthropic-agent-api-patterns`

## Clean skills (no issues found)

`hermes-agent`, `hermes-acp-routing`, `skill-family-router-maintenance`, `ouroboros-setup-and-health-check`, `ouroboros-plugin-development`, `agent-browser-troubleshooting`, `agent-runtime-stack-debugging`, `hermes-dashboard-troubleshooting`, `hermes-web-provider-configuration`, `hermes-cowork-port-sync`, `hermes-config-repo-audit`, `claude-code`, `fable-orchestrate`, `graphiti-mcp-setup`, `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `using-git-worktrees`, `using-superpowers`, `writing-skills`, `computer-use` (content clean, path reference is the issue).

## Consolidation candidates

| Pair | Verdict |
|------|---------|
| `hermes-self-evolution` + `self-improve-agent` | Keep separate — distinct scopes (offline repo vs. live session). Add cross-references. |
| `hermes-skill-library-consolidation-audit` + `hermes-skillspector-guard-maintenance` | Keep as umbrella→child. Skillspector is already documented as child under consolidation-audit's Section 1. |
| `agent-browser-troubleshooting` + `hermes-dashboard-troubleshooting` | Keep separate — different systems (npx agent-browser headless Chrome vs. Hermes web dashboard). |

## Adopt candidates (for next foreground session)

Run in a foreground Hermes session to enable autonomous maintenance:

```bash
hermes curator adopt harness-first-agent-design
hermes curator adopt hermes-semantic-skill-routing
hermes curator adopt autonomous-ai-agents
hermes curator adopt self-improve-agent
hermes curator adopt hermes-skillspector-guard-maintenance
hermes curator adopt agent-task-signoff
hermes curator adopt anthropic-agent-api-patterns
```
