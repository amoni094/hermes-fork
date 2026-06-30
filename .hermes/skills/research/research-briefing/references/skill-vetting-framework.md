# Third-Party Skill Evaluation Framework

Use this checklist when vetting external skill repos for integration into your Hermes library.

## Step 1: Verify repo basics
- [ ] Repository exists and is not archived/removed.
- [ ] Latest commit is recent (within 6 months for active, within 12 months for stable).
- [ ] Star count > 50 or author is known-trusted (Trail of Bits, Anthropic, OWASP).
- [ ] Clone test: `git clone <URL> && ls -la` succeeds without errors.

## Step 2: Locate skill files
- [ ] Repo has a documented structure (README or file listing shows skill directory).
- [ ] Expected skill path exists: check `skills/`, `.claude/skills/`, or `plugins/` based on repo type.
- [ ] SKILL.md file(s) exist in the expected location.
- [ ] Path claim in README matches actual directory structure (verify with `git ls-tree main | grep SKILL`).

## Step 3: Evaluate skill quality (per skill)
For each candidate skill, assess:

### Frontmatter quality
- [ ] `name` field is class-level (e.g., `codeql`, not `run-codeql-on-djangoproject`).
- [ ] `description` includes trigger phrases that match the user's intent.
- [ ] `tags` include domain and use-case keywords.
- [ ] `version` is present and semantic.
- [ ] Required/optional fields documented (e.g., `allowed-tools`, `required-environment-variables`).

### Body quality
- [ ] "When to use" section is concrete, not generic.
- [ ] "When NOT to use" section exists and explains anti-patterns.
- [ ] "Workflow" section has step-by-step instructions with specific commands/tools.
- [ ] "Verification" section describes how to confirm success.
- [ ] No placeholder text, boilerplate, or TBD sections.
- [ ] Practitioner detail present (real tool options, known failures, workarounds, edge cases).

### Coverage signals
- [ ] Skill is specialized to a clear problem class (not "run security analysis").
- [ ] Content shows evidence of real-world use (specific error messages, framework quirks, version pins).
- [ ] References or links point to authoritative upstream docs (MITRE, OWASP, vendor docs).
- [ ] No circular references or self-referential definitions.

### Conflict check
- [ ] Skill name does NOT duplicate an existing skill in your library.
- [ ] Trigger phrases do NOT heavily overlap with existing skills.
- [ ] Skill domain does NOT directly conflict with your established umbrellas.

## Step 4: Assess installation risk
- [ ] Skill has no external binary dependencies (or dependencies are documented).
- [ ] No hardcoded paths that will fail on your OS (check for `/usr/bin/`, `/opt/`, Windows paths).
- [ ] No hidden side effects (the skill does not modify `.gitignore`, install packages, or write to home dir).
- [ ] No telemetry or external API calls without explicit user consent or `--metrics=off` switches.

## Step 5: Assign tier

### Tier 1 — Install immediately
- ✓ Repo is active and trusted (Trail of Bits, Anthropic, 1000+ stars).
- ✓ Skill quality is high (practitioner content, clear workflow, verified steps).
- ✓ Direct fit to your workflow (you have matching use cases now).
- ✓ Low installation risk.
- ✓ Zero conflicts with existing skills.

**Examples:** Trail of Bits codeql, semgrep, fp-check. OWASP Top 10:2025.

### Tier 2 — Solid value, lower priority
- ✓ Quality is high but niche use case.
- ✓ OR high value but requires external tool setup.
- ✓ OR fills a gap but lower immediate urgency.
- ✓ No conflicts; installation risk is moderate.
- ✓ Should be installed when the use case becomes active.

**Examples:** Varlock (requires external CLI), Firecrawl advanced plugins (requires local service), AI Security domain skills (specialized but high-value).

### Tier 3 — Review before deciding
- ✓ Quality is moderate (lacks some practitioner detail).
- ✓ OR use case is unclear or overlaps existing skills.
- ✓ OR installation requires significant setup (auth, credentials, config).
- ✓ OR author trust is lower (single contributor, <50 stars).
- ✓ Should be reviewed case-by-case before installation.

**Examples:** Single-author niche skills, repos with stale READMEs, experimental tools.

### Rejected — Do not install
- ✗ Repo path is 404 or link is broken.
- ✗ Skill content is generated/template boilerplate.
- ✗ Trigger phrases are too broad (loads on every task).
- ✗ No verification section or success criteria.
- ✗ Installation breaks or requires manual workarounds.

**Examples:** ironclaw-agent-guard (404), varlock without varlock.dev CLI (unusable), sanitize (path mismatch).

## Known-good sources (2026-06-30)

### Trail of Bits (`trailofbits/skills`)
- **Plugins:** 38 total; skills in `plugins/<name>/skills/`
- **Tier 1:** `codeql`, `semgrep`, `agentic-actions-auditor`, `fp-check`
- **Installation:** Clone repo, copy `plugins/<name>/skills/<skillname>` to `~/.hermes/skills/<skillname>`
- **Trust:** 5.9k stars, 123 commits, maintained by security research org. Peer-reviewed content.
- **Notes:** These are production-ready security-analysis skills with deep practitioner workflow. The `fp-check` skill is unique for systematic false-positive verification.

### Anthropic-Cybersecurity-Skills (`mukul975/Anthropic-Cybersecurity-Skills`)
- **Scale:** 817 skills across 29 domains
- **Mapping:** MITRE ATT&CK v19.1, NIST CSF 2.0, ATLAS, D3FEND, AI RMF, F3
- **Tier 1 domain subset:**
  - AI Security (14 skills): LLM red-teaming, prompt injection, MCP/agentic security, guardrails
  - DevSecOps (18 skills): CI/CD security, Trivy IaC, code signing
  - Supply Chain Security (8 skills): SBOMs, dependency confusion, SLSA/Sigstore
- **Tier 2 domain subset:** Container Security, Threat Hunting, Cloud Security (all strong but specialized)
- **Installation:** `npx skills add mukul975/Anthropic-Cybersecurity-Skills` or clone and pick specific domains
- **Trust:** 23.2k stars, 2026 framework alignment, active curation
- **Pitfall:** Do NOT install wholesale (817 skills will flood your library). Pick by domain: `skills/ai-security/`, `skills/devsecops/`, `skills/supply-chain-security/`.

### OWASP Security (`agamm/claude-code-owasp`)
- **Path:** `.claude/skills/owasp-security/`
- **Content:** OWASP Top 10:2025, ASVS 5.0, Agentic AI Security 2026 (ASI01–ASI06)
- **Unique:** Agentic AI Security section covers tool-calling hijacking, agent goal confusion, memory poisoning. Not covered in other security skills.
- **Installation:** `npx degit agamm/claude-code-owasp/.claude/skills/owasp-security ~/.hermes/skills/owasp-security`
- **Trust:** Updated Jun 2026, includes reference files and language-specific quirks
- **Notes:** Install the whole directory (includes references/). Progressive disclosure means only core patterns load by default; detailed language quirks are on-demand.

## Pitfalls that block vetting

| Pitfall | Detection | Action |
|---------|-----------|--------|
| **Index path mismatch** | Claimed `/skills/ai-security`, actual path is `/domains/ai/` or `/` only | Clone and inspect directory with `find . -name "SKILL.md"` |
| **Deleted or renamed dir** | README says skill exists but path returns 404 | Check git log for removal commit; do not force-install |
| **Stale frontmatter** | SKILL.md references tools that do not exist or are deprecated | Read tool version history; test install in isolated venv first |
| **Generated content** | SKILL.md is verbose boilerplate with no practitioner detail | Compare against Trail of Bits or OWASP examples; generated content is obvious |
| **Too-broad trigger** | Skill triggers on "security", "analysis", "code review" | Would load on every session; too noisy for umbrella skills |
| **No verification section** | Skill describes steps but does not say how to confirm success | Risky; cannot tell if workflow completed correctly |
| **Telemetry leaks** | Skill uses `semgrep --config auto` or similar without `--metrics=off` | Audit all external API calls; add redaction where needed |
| **OS-specific failures** | Skill path assumes `/usr/bin/tool` or Windows `%PATH%` | Test on your actual OS first; do not assume portability |

## Quick verification commands

```bash
# Test clone + path
git clone https://github.com/trail-of-bits/skills /tmp/tob-skills
ls -la /tmp/tob-skills/plugins/codeql/skills/codeql/SKILL.md

# Count SKILL files in repo
find . -name "SKILL.md" | wc -l

# Check recent commits in skill directory
git log -1 --format="%ai %s" -- plugins/codeql/

# Verify degit works (for Claude Code installed skills)
npx degit agamm/claude-code-owasp/.claude/skills/owasp-security /tmp/test-owasp
ls -la /tmp/test-owasp/SKILL.md

# Check skill frontmatter validity
grep -A 5 "^---" skills/codeql/SKILL.md | head -20
```

## Consolidation and conflicts

If you install multiple skill sources covering the same domain (e.g., multiple static-analysis skills), note potential overlaps:

- **Duplicate problem class:** Two skills both solve "find bugs in code" with similar trigger phrases.
- **Different tools, same domain:** codeql vs. semgrep (both static analysis, different engines).
- **Specialization hierarchy:** Broad "code-review" skill vs. narrow "codeql-database-quality-gate" skill.

When conflicts arise, prefer:
1. Most recently maintained version.
2. Highest signal-to-noise (practitioner content > boilerplate).
3. Least number of dependencies.

The curator (`hermes curator consolidate`) can merge skills when overlaps are confirmed — do not manually delete; just document the overlap in a session note and let the curator decide.

## Recording your installation

After installing a new skill from an external repo, create a session note or memory entry:

```markdown
Installed: codeql (Trail of Bits)
Source: https://github.com/trailofbits/skills
Commit: ff4162dcb9cec5b7abe5ab039c868544b325275d (Jun 2026)
Reason: Deep practitioner workflow for CodeQL database quality gates + data extensions
Trigger: User asks about codeql analysis, building databases, security scanning
Location: ~/.hermes/skills/codeql/
```

This makes updates and rollback traceable.
