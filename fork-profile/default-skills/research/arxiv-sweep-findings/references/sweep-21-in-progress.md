# Sweep 21 — COMPLETE (Aug 22 2026)

Cutoff: arXiv > 2608.20320
Delegations: deleg_dee63124 (5 subagents, original) + deleg_40b90cda (2 subagents, redo)
Status: All tasks complete. Findings absorbed. Sweep log updated.

## Task Status (final)

| Task | Source | Status | Notes |
|------|--------|--------|-------|
| task-0 | arXiv > 2608.20320 | Completed (127s) | MemTrapBench/AdaptiveMem HIGH; Pandora's Router HIGH |
| task-1 | Google Scholar / OpenAlex (original) | Failed — 0 results | OpenAlex query issue; re-run as redo-1 |
| task-2 | Semantic Scholar + GitHub + HN | Completed (121s) | OpenViking HIGH, semantica HIGH, plano HIGH |
| task-3 | Multilingual (Zenn/Qiita/CyberLeninka/CN/KR) | Failed — Brave API not inherited | Re-run as redo-0 with SearXNG fallback |
| task-4 | Brave Search general web | Completed (360s) | SearXNG braveapi fallback; 70 items |
| redo-0 | Multilingual redo (deleg_40b90cda) | Completed (375s) | 10 findings: Z21-1 Trace2Skill (HIGH), Z21-3 CoEvoSkills (HIGH), Z21-4 SkillRouter (HIGH), AR21-2–4 |
| redo-1 | Google Scholar/OpenAlex redo (deleg_40b90cda) | Completed (415s) | 14 findings: SUPO (HIGH), AMA (HIGH), GS003 experience-following (HIGH), AgentRouter (HIGH), ACE (HIGH) |

## Findings Applied

### arXiv (task-0)
| ID | Title | Target skill | Rating |
|----|-------|-------------|--------|
| arXiv 2026 | MemTrapBench / AdaptiveMem — Memory cognitive trap gate | hermes-memory-surface-selection | HIGH |
| arXiv 2026 | Pandora's Router — Value-of-information routing gate | claude-routing-hierarchy | HIGH |

### GitHub/HN (task-2)
| ID | Title | Notes |
|----|-------|-------|
| volcengine/OpenViking | Self-evolving context DB (ByteDance) | Logged; no skill patch needed yet — monitor |
| semantica-agi/semantica | Graph-native context+governance 10.2k stars | Logged; KG relevance — see Graphiti skill |
| katanemo/plano | Envoy-based agent guardrail proxy | Logged; architecture reference |
| forcedotcom/sf-skills | Salesforce skill-as-library pattern | MED; logged |

### Multilingual redo (redo-0)
| ID | Title | Target skill | Rating |
|----|-------|-------------|--------|
| Z21-1 | Trace2Skill — Trajectory→skill distillation pipeline | hermes-skill-library-consolidation-audit | HIGH |
| Z21-2 | Agent Skills quality standard (name+desc routing risk) | hermes-skill-library-consolidation-audit | HIGH |
| Z21-3 | CoEvoSkills — Co-evolutionary verifier pattern | evaluation-driven-development | HIGH |
| Z21-4 | SkillRouter — Scale routing degradation at 80k skills | hermes-skill-library-consolidation-audit, hermes-semantic-skill-routing | HIGH |
| AR21-2 | Trace2Skill arXiv — repeated-edit merge quality gate | agent-memory-consolidation (promotion section) | HIGH |
| AR21-3 | CoEvoSkills arXiv — oracle-isolation eval design | evaluation-driven-development | HIGH |
| AR21-4 | SkillRouter arXiv — 31-44pp accuracy drop at scale | hermes-semantic-skill-routing | HIGH |

### Google Scholar redo (redo-1)
| ID | Title | Target skill | Rating |
|----|-------|-------------|--------|
| GS001 | SUPO — End-to-end RL context compression (ACL 2026) | hermes-context-budgeting | HIGH |
| GS002 | AMA — Adaptive Memory multi-agent roles (ACL Findings 2026) | agent-memory-consolidation | HIGH |
| GS003 | Experience-following + history-aware deletion (ACL 2026) | agent-memory-consolidation | HIGH |
| GS004 | AgentRouter — KG-guided routing for MAS (ACL 2026) | claude-routing-hierarchy (logged, no patch yet) | HIGH |
| GS005 | ACE — Agentic Context Engineering (ICLR 2026) | hermes-context-budgeting | HIGH |
| GS006 | Textual backpropagation for MAS self-improvement (ACL Findings) | self-improve-agent | MED |
| GS007 | GhostWriter/AM-Sentry — Memory poisoning + defense | agent-memory-consolidation | HIGH |
| GS008 | MAIS-Bench — Multi-agent safety benchmarks | trajectory-risk-guardrail | MED |
| GS009 | Memory-to-skills co-evolution governance (arXiv:2607.16621) | agent-memory-consolidation | HIGH |
| GS011 | MAIA — Multi-agent influence attacks | trajectory-risk-guardrail | MED |
| GS013 | Capability degradation on skill updates (arXiv:2605.09315) | self-improve-agent, hermes-skill-library-consolidation-audit | HIGH |

## Skills Patched in This Sweep
- hermes-memory-surface-selection — Cognitive trap gate (MemTrapBench/AdaptiveMem)
- agent-memory-consolidation — AMA roles, GhostWriter defense, Memory→Skill governance, experience-following risk
- claude-routing-hierarchy — Pandora's Router VoI gate
- hermes-skill-library-consolidation-audit — Freshness test, scale routing risk, capability degradation
- hermes-context-budgeting — SUPO + ACE context compression findings
- self-improve-agent — Capability degradation (GS013), textual backpropagation (GS006)
- trajectory-risk-guardrail — MAIS-Bench, MAIA multi-agent safety

## Pending (not patched — logged for future work)
- AgentRouter (GS004): KG-guided task routing architecture — relevant to future multi-agent routing redesign
- OpenViking / semantica / plano: monitor for production maturity before integrating
- Korean/Chinese multilingual sources: no extractable content found this sweep; SearXNG CJK coverage still weak

## Infrastructure Fix Applied This Sweep
- Root cause: subagents do not inherit Hermes web_search 'brave' provider config
- Fix: always include SearXNG fallback in all research subagent context blocks:
  `curl -s 'http://localhost:8888/search?q=QUERY&format=json&engines=braveapi,bing'`
- Documented in: dispatching-parallel-agents/references/subagent-web-search-pitfalls.md (to add next)

## Net counts
- HIGH: 15 applied
- MED: 6 applied (MAIS-Bench, MAIA, GS006, sf-skills, AR21-2/5 non-skill items)
- Total unique findings: 24
- Tasks failed and re-run: 2 (task-1, task-3)
- Skills patched: 7
