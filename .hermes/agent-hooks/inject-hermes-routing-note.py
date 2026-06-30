#!/usr/bin/env python3
"""
pre_llm_call hook — complexity classifier + auto-delegation injector
~/.hermes/agent-hooks/inject-hermes-routing-note.py

Fires before every LLM call.  Classifies the user query on four axes
and injects the appropriate level of routing guidance:

  SIMPLE   (score 0–3)  → no injection (let model respond directly)
  MEDIUM   (score 4–6)  → delegation routing hints only
  COMPLEX  (score 7–9)  → delegation routing + full findings contract
  RESEARCH (score 10+)  → all of the above + parallel fan-out instruction

Complexity axes (each 0–3):
  1. Parallelism potential — multiple independent sub-tasks detectable
  2. Research depth      — requires web search / external sources
  3. Implementation breadth — touches >= 2 files/components/systems
  4. Ambiguity / open-ended — requires synthesis or design decisions

The findings contract (hermes-finding/v2) is injected only when score>=7
so routine queries are never slowed by boilerplate.
"""

import json
import re
import sys

payload = json.load(sys.stdin)
extra = payload.get("extra") or {}
message = (extra.get("user_message") or "").strip().lower()

# ── Axis scoring ─────────────────────────────────────────────────────────────

def score_parallelism(msg: str) -> int:
    """Multiple independent tasks that could run concurrently."""
    patterns = [
        r"\band\b.{0,60}\band\b",          # "X and Y and Z"
        r"\b(also|additionally|furthermore|plus)\b",
        r"\b(multiple|several|each|all)\b.{0,30}\b(file|component|module|pattern|check)\b",
        r"\b(parallel|concurrent|simultaneously|at the same time)\b",
        r"\b(batch|fan.?out|dispatch)\b",
    ]
    hits = sum(1 for p in patterns if re.search(p, msg))
    return min(hits, 3)


def score_research(msg: str) -> int:
    """Needs external knowledge, web search, or synthesis across sources."""
    patterns = [
        r"\b(research|investigate|find out|look up|search for)\b",
        r"\b(latest|recent|current|2025|2026|new|state.of.the.art)\b",
        r"\b(best practice|benchmark|compare|survey|review)\b",
        r"\b(cve|vulnerability|exploit|attack|threat|security)\b.{0,30}\b(new|recent|known)\b",
        r"\b(paper|arxiv|study|literature)\b",
    ]
    hits = sum(1 for p in patterns if re.search(p, msg))
    return min(hits, 3)


def score_implementation(msg: str) -> int:
    """Touches multiple files, components, or systems."""
    patterns = [
        r"\b(implement|build|create|write|add|update|patch|fix)\b.{0,40}\b(and|plus|also)\b",
        r"\b(refactor|migrate|overhaul|rework)\b",
        r"\b(across|throughout|all|every)\b.{0,30}\b(file|module|class|component|service)\b",
        r"\b(commit|push|pr|pull request|deploy)\b",
        r"\b(test|verify|validate)\b.{0,30}\b(and|then|after)\b.{0,30}\b(impl|build|write)\b",
    ]
    hits = sum(1 for p in patterns if re.search(p, msg))
    return min(hits, 3)


def score_ambiguity(msg: str) -> int:
    """Requires design decisions, synthesis, or is open-ended."""
    patterns = [
        r"\b(best way|how should|what.*approach|design|architect)\b",
        r"\b(sync|coordinate|orchestrate|automate)\b",
        r"\b(based on context|appropriately|intelligently|automatically)\b",
        r"\?.*\?",                          # multiple questions
        r"\b(or is there a better way|alternatives|options)\b",
    ]
    hits = sum(1 for p in patterns if re.search(p, msg))
    return min(hits, 3)


p = score_parallelism(message)
r = score_research(message)
i = score_implementation(message)
a = score_ambiguity(message)
score = p + r + i + a

# ── Existing routing signals ─────────────────────────────────────────────────

delegate_pattern = re.compile(
    r"\b(delegate|delegation|subagent|worker|spawn|background|cron|schedule|agent)\b", re.I
)
escalate_pattern = re.compile(
    r"\b(hard|complex|difficult|deep|exhaustive|thorough|adversarial|security|audit|architecture|design|research)\b",
    re.I,
)

# ── Build context parts ──────────────────────────────────────────────────────

context_parts = []

# Always include ledger note when delegation keywords present
if delegate_pattern.search(message):
    context_parts.append(
        "Routing: before durable background work or delegation, check local workspace/vault context first; "
        "pass a compact context packet; long-lived work should be visible in ~/.hermes/logs/hermes-task-ledger.jsonl."
    )

if escalate_pattern.search(message):
    context_parts.append(
        "Escalation guidance: for security audits, architecture decisions, and exhaustive research prefer "
        "delegation.model=claude-opus-4-8. For maximum reasoning depth (formal verification, adversarial "
        "red-teaming, large document synthesis) prefer claude-fable-5."
    )

# Complexity-gated injection
if score >= 4:
    context_parts.append(
        f"[complexity score={score}/12 p={p} r={r} i={i} a={a}] "
        "Consider parallel delegation for independent sub-tasks rather than sequential execution."
    )

if score >= 7:
    context_parts.append(
        "STRUCTURED OUTPUT CONTRACT (hermes-finding/v2): "
        "When delegating agents, include this in each agent's context: "
        "\"Write your findings to /var/home/rainbow/.hermes/agent-workspace/<agent_id>-<task_label>.finding.json "
        "using schema hermes-finding/v2 (see SCHEMA.md in that dir). "
        "Each finding needs: type (patch|file_append|file_write|config_set|git_commit|observation), "
        "idempotency_key, rationale, status='ready', confidence 0-1, evidence[]. "
        "Use depends_on[] for ordering. Return only: 'Findings written to <file>, N findings.'\" "
        "The subagent_stop hook will auto-apply findings as each agent completes — no manual apply step needed."
    )

if score >= 10:
    context_parts.append(
        "HIGH complexity: fan out to parallel agents immediately; do not attempt this in a single turn. "
        "Decompose into: (1) research agents, (2) implementation agents, (3) verification agent. "
        "Research agents write observations; implementation agents write patch/file_write/config_set findings; "
        "verification agent writes a final observation confirming correctness."
    )

if context_parts:
    json.dump({"context": " | ".join(context_parts)}, sys.stdout)
else:
    sys.stdout.write("{}\n")
