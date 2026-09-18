# RUMBA: Russian User Memory Benchmark — Evaluation Taxonomy

**Source:** Sber AI — Lisa Tikhonova (spreadingmind), AI Researcher  
**Language:** Russian  
**URL:** https://habr.com/ru/companies/sberbank/articles/1060432/  
**Date:** July 24, 2026  
**arXiv:** Not cross-posted (blog-only as of Aug 2026)

---

## Why it matters for Hermes memory evaluation

RUMBA is the first benchmark with:
1. Compositional 3-axis question taxonomy (richer than English benchmarks like LoCoMo, LongMemEval)
2. **DeleteInfo** questions — does the system actually forget on user request?
3. **AsstQuery** questions — does the system remember what *the agent itself said*?
4. Time-stamped questions — the correct answer depends on *when the question is asked*, not just what facts exist

No existing English benchmark covers all four together. RUMBA's taxonomy is a superior
design framework for memory system evaluation even if you don't use the Russian dataset itself.

---

## Dataset statistics

| Metric | Value |
|--------|-------|
| Dialogues | 85 |
| Questions | 1,543 |
| Avg dialogue length | ~340,000 chars |
| Avg dialogue span | 191 days |
| Sessions per dialogue | 12–85 |
| Turns per dialogue | 180–998 |
| Questions per dialogue | 14–22 |
| Languages | Russian (primary) + English (auto-translated) |

---

## The 3-axis compositional taxonomy

Every question gets all three axes tagged simultaneously, enabling fine-grained failure analysis:

### Axis 1: Semantic type (17 types across 3 super-groups)

**Extraction super-group** (find and return information):
- `StaticUser` — stable fact: "What is my dog's name?"
- `UpdatingInfo` — fact has been updated: only latest value is correct
- `DeleteInfo` — user asked to delete the fact: correct answer is "I have no such information"
- `AsstQuery` — fact is in assistant's own prior output, not user's statement
- `OpenDomainType` — requires world knowledge beyond the dialogue

**Reasoning super-group** (derive from multiple facts):
- `DateExtraction`, `SocialRelationship`, `Ordering`, `Arithmetic`, `Comparison`
- `UserQA`, `CalendarUnderstanding`, `TemporalCommonsense`
- `TemporallyModifiedGeneralReasoning`, `ComplexRelations`, `OtherReasoning`

**Abstention super-group** (no answer exists in the dialogue):
- `Abstention` — tests that system does NOT hallucinate when context is absent

### Axis 2: Session scope

- `Single session` — all evidence in one session
- `Multi-session` — evidence spread across multiple sessions

### Axis 3: Temporality

- `Atemporal` — time doesn't affect the answer
- `Temporal` — correct answer depends on when the question is asked

**4th tag for temporal questions — temporal expression type:**
- `Explicit` — time stated directly ("on March 3rd")
- `Implicit` — time inferred from event ("after I started my new job")
- `None` — no time marker in user speech; must infer from session structure

---

## Question type examples (translated from Russian)

**StaticUser:**
> User: "Our dog is named Losyash."  
> Q: "What is my dog's name?"  
> A: "Losyash."

**UpdatingInfo:**
> User: "I love roses." → … → "Now I like cacti more." → … → "Cacti are boring, lilies are my favorite now."  
> Q: "What flowers do I like?"  
> A: "Lilies." (not roses, not cacti)

**DeleteInfo:**
> User: "I want to become an actress." → … → "Delete what I said about what I want to be."  
> Q: "What do you want to be?"  
> A: "I have no such information." (not "an actress")

**AsstQuery:**
> User: "Which 20th-century Russian writers should I read?"  
> Assistant: "You could start with Bulgakov, Pasternak, Dovlatov, Orwell, and Joyce."  
> Q: "Which Russian 20th-century writers did you recommend?"  
> A: "Bulgakov, Pasternak, and Dovlatov." (filtering to Russian, from assistant's own output)

---

## Gaps this reveals in Hermes memory systems

| Test type | Current Hermes coverage | Gap |
|-----------|------------------------|-----|
| DeleteInfo | ❌ Not tested | Does MEMORY.md/Graphiti actually suppress facts on user request? |
| AsstQuery | ❌ Not tested | Does l1-extract.py tag assistant outputs as memories? |
| UpdatingInfo | Partial (temporal validity fields via `valid_to`) | Does retrieval return the latest valid version? |
| Temporal anchoring | ❌ Not tested | Can the system answer "what did you say before X event"? |
| Abstention | Partial | Does the system say "I don't know" rather than hallucinate when fact is absent? |
| Multi-session scope | ✅ Covered via Hindsight + session_search | Needs test cases |

**Recommended action:** When building memory eval harnesses, include at least one test case per
RUMBA semantic-type row. The DeleteInfo and AsstQuery types are the highest-priority gaps.

---

## Comparison to English benchmarks

| Benchmark | DeleteInfo | AsstQuery | Temporal anchor | Multi-session |
|-----------|-----------|-----------|----------------|---------------|
| LoCoMo | ❌ | ❌ | Partial | ✅ |
| LongMemEval | ❌ | ❌ | Partial | ✅ |
| Mem-Gallery (arXiv:2601.03515) | ❌ | ❌ | ❌ | ✅ |
| **RUMBA** | ✅ | ✅ | ✅ | ✅ |

RUMBA's taxonomy is strictly richer. Even if using an English-language memory evaluation,
adopt the RUMBA question-type taxonomy as the design framework.
