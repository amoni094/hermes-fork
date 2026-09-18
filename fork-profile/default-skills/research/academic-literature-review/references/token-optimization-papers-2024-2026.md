# Token Optimization & Efficient LLM Inference — Verified Paper Index 2024–2026

> Compiled July 2025. Institution attribution verified against author homepages and paper PDFs.
> Full narrative survey: ~/token-optimization-research-2024-2026.md

---

## KV-Cache Optimization

| arXiv | Title | Institution | Venue | Key Metric |
|-------|-------|-------------|-------|-----------|
| 2404.14469 | **SnapKV** | UIUC + WestLake University | NeurIPS 2024 | 3.6× memory reduction; fine-tuning-free; attention-pattern-based |
| 2406.19707 | **InfiniGen** | **Seoul National University (SNU)** 🇰🇷 | OSDI 2024 | 1.4–2× throughput on 32K+ tokens; 4× GPU memory savings; CPU offload |
| 2503.16163 | **SpeCache** | Peking University | ICML 2025 | 50% VRAM reduction; low-bit shadow KV for speculative prefetch |
| 2504.09936 | **KeepKV** | Chinese Academy of Sciences | AAAI 2025 | 2–4× lossless KV compression; Electoral Votes + ZIPM mechanism |
| 2510.00636 | **Expected Attention + KVPress** | NVIDIA (Devoto/Jégou — Sapienza/NVIDIA Paris) 🇫🇷 | Preprint Oct 2025 | Training-free; closed-form expected attention; releases KVPress (20+ methods, pip-installable) |

### Tooling
- **KVPress**: `pip install kvpress` — HuggingFace transformers compatible, `github.com/NVIDIA/kvpress`
- **InfiniGen**: `github.com/snu-comparch/InfiniGen`

---

## Prompt & Context Compression

| arXiv | Title | Institution | Venue | Key Metric |
|-------|-------|-------------|-------|-----------|
| 2403.12968 | **LLMLingua-2** | Microsoft Research | ACL 2024 Findings | 3–6× faster; 1.6–2.9× E2E latency at 2–5× compression ratio |
| 2507.22931 | **ACC-RAG** | Leiden University | EMNLP 2025 Findings | Adaptive compression rate beats any fixed rate on RAG QA benchmarks |
| 2404.04997 | **Soft Prompt Compression** | Multi-institution | ACM 2024 | 10–20× reduction; white-box model fine-tuning required |

### LLMLingua-2 Quick Use
```bash
pip install llmlingua
```
```python
from llmlingua import PromptCompressor
compressor = PromptCompressor(model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank")
result = compressor.compress_prompt(context, rate=0.5, force_tokens=["\n", "?"])
compressed = result["compressed_prompt"]
```
- Task-agnostic: no task-specific tuning needed
- Works entirely independently of target LLM — usable with Anthropic API
- BERT-level encoder: runs on CPU, fast

---

## Speculative Decoding

| arXiv | Title | Institution | Venue | Key Metric |
|-------|-------|-------------|-------|-----------|
| 2503.01840 | **EAGLE-3** | SafeAI Lab / Beihang University | NeurIPS 2025 | 3.0–6.5× speedup; 1.38× throughput at batch=64 in SGLang |
| 2502.05202 | **Heterogeneous-Vocab SD** | **Weizmann Institute + Intel Labs** 🇮🇱 | ICML 2025 **Oral (top 1%)** | 2.8× speedup; removes shared-vocab constraint; training-free; off-the-shelf |
| 2507.02659 | **OmniDraft** | Qualcomm AI Research | NeurIPS 2025 | 1.5–2× speedup; single draft model for multiple target families |
| 2602.13836 | **SpecVocab** | Multi-affiliation | Preprint Feb 2026 | 8.1% throughput gain over EAGLE-3 via per-step vocab subset |

### EAGLE lineage
- EAGLE-1 (ICML 2024): 2–3× — `github.com/SafeAILab/EAGLE`
- EAGLE-2 (2024): 3–4.3× (dynamic draft trees)
- EAGLE-3 (NeurIPS 2025): 3–6.5× (training-time test scaling + multi-layer fusion)

### Weizmann/Intel paper notes
- Authors: Nadav Timor, Jonathan Mamou, Daniel Korat, Moshe Berchansky, Gaurav Jain, Oren Pereg, Moshe Wasserblat, David Harel
- Three distinct SD algorithms, all lossless, all training-free, all off-the-shelf
- Key insight: enables mixing models from different vendor families (e.g., Mistral draft → Llama target)

---

## Chain-of-Thought Length Reduction

| arXiv | Title | Institution | Venue | Key Metric |
|-------|-------|-------------|-------|-----------|
| 2412.18547 | **TALE** (Token-Budget-Aware LLM Reasoning) | Shanghai Jiao Tong University | ACL 2025 Findings | ~40% CoT reduction, ~2% accuracy drop; pure prompt engineering, API-compatible |
| 2504.01296 | **ThinkPrune** | UCSB NLP (Chang group) | Preprint Apr 2025 | 50% length reduction, 2% drop on AIME24; RL fine-tuning required |

### TALE budget hint pattern (API-compatible)
Prepend before reasoning task:
```
[Budget: Use approximately {N} tokens for your reasoning steps.]
```
Calibrated budget targets by task type (set at P80, not median — median causes wrong answers):
- Math/formal reasoning: ~800 tokens
- Code generation: ~600 tokens
- Factual retrieval: ~200 tokens
- Creative writing: ~400 tokens

**Warning**: ThinkPrune confirms that hard budget-forcing (naive truncation) without RL causes wrong answers when budget < actual task need. Be conservative; use P80.

---

## RAG Efficiency

| arXiv/ID | Title | Institution | Venue | Key Metric |
|----------|-------|-------------|-------|-----------|
| COLM 2025 | **E²-RAG** | Multi-institution | COLM 2025 | 40× faster KV editing; 3× faster generation vs. standard RAG |
| 2507.22931 | **ACC-RAG** | Leiden University | EMNLP 2025 | Adaptive rate beats fixed rate; hierarchical compressor + adaptive selector |
| 2409.13385 | **Contextual Compression in RAG Survey** | Multi-institution | Preprint 2024 | Best: extractive (LLMLingua-2) → selective abstractive merge |

### Recommended hybrid RAG compression pipeline
1. LLMLingua-2 extractive pass at 3–5× compression on retrieved chunks
2. Complexity gate: if query_complexity > threshold → keep extractive output; else → Haiku abstractive merge
3. Complexity signals: query perplexity, entity count, multi-hop indicator keywords

---

## Regional Highlights

### 🇮🇱 Israel — Weizmann Institute + Intel Labs
- **Flagship**: arXiv 2502.05202, ICML 2025 Oral — heterogeneous-vocabulary speculative decoding
- Landmark result: removes shared-vocab constraint that blocked cross-vendor draft/target mixing

### 🇰🇷 Korea
- **SNU**: InfiniGen (arXiv 2406.19707, OSDI 2024) — `github.com/snu-comparch/InfiniGen`
- **KAIST + DeepAuto.AI**: InfiniteHiP (arXiv 2502.08910) — 18.95× attention speedup; 3M tokens on single L40s 48GB
- **KAIST**: REFORM (arXiv 2506.01215, NeurIPS 2025) — 52% improvement on RULER; 30% inference time reduction
- **KAIST-adjacent**: Multilingual SD (arXiv 2406.16758, EMNLP 2024) — language-specific draft models

### 🇩🇪 Germany — MPI-IS Tübingen (SEAL Group, Jonas Geiping)
- **Binary Block Masking** (arXiv 2409.15097; NeurIPS Workshop 2024 → ICML 2025)
- Up to **9× runtime reduction** on sparse FlashAttention masks
- Drop-in for: packed fine-tuning, Medusa tree attention, sparse long-doc attention

### 🇬🇧 UK
- **Oxford OATML (Yarin Gal)**: Semantic Entropy — Nature 2024 — AUROC 0.79 for hallucination detection
- **Cambridge**: EfficientLLM benchmark (arXiv 2505.13840) — spec-decoding + INT8 = highest-leverage combo for throughput

### 🇫🇷 France / NVIDIA Paris
- **Expected Attention + KVPress** (arXiv 2510.00636) — theoretical: closed-form expected attention via Gaussianity of LLM activations

### 🇯🇵 Japan
- **NII**: LLM-jp-4 32B-A3B (2026) — MoE, only 3B active params at inference (~70% compute reduction); Apache 2.0
- **RIKEN + Tokyo Tech**: Fugaku-LLM (2024) — data mixing optimization reduces pretraining token budget ~30%

---

## Hermes CLI Priority Actions (from survey)

## 2026 update (SerpApi sweep, July 2026)

New LLM-routing research (distinct from token/KV-cache optimization above, but adjacent):
R2-Router (arXiv:2602.02823, ICML 2026) shows routers should jointly pick (model, output-length
budget), not just model — a length-constrained pass on the current-tier model can match a
higher-tier model's quality at much lower cost. This pairs directly with the TALE P80 budget-hint
pattern below (P1 priority): before escalating model tier, first retry with a tighter length
budget on the current model. Full detail filed in the `claude-routing-hierarchy` skill.

| Priority | Action | Paper | Effort |
|----------|--------|-------|--------|
| P1 | TALE budget hints at P80 per task type | 2412.18547 | Low — prompt templates |
| P1b | Compact constraint headers (71% token reduction, no CSR loss) | 2604.07192 | Zero — already in nesy.py FSMAgent.compact_schema_prompt |
| P2 | Replace Haiku compressor with LLMLingua-2 for extractive compression | 2403.12968 | Medium — pip + wrapper |
| P3 | Adaptive compression threshold (complexity-based, not fixed 0.4) | 2507.22931 | Medium — scorer build |
| P4 | Hybrid RAG: extractive → selective abstractive pipeline | 2409.13385 | Medium — pipeline change |
| P5 | KVPress for local model serving | 2510.00636 | Medium — HF integration |
| P6 | EAGLE-3 on local fallback endpoints | 2503.01840 | High — SGLang/vLLM |
| P7 | InfiniteHiP for 200K+ context | 2502.08910 | Medium-High |

---

## RAG Robustness & Retrieval Quality (July 2026 Addendum)

These papers are adjacent to token optimization — they reduce wasteful tokens by filtering irrelevant context BEFORE generation, complementing compression approaches above.

| arXiv | Title | Venue | Token Efficiency Mechanism |
|-------|-------|-------|--------------------------|
| 2310.01558 | **RetRobust** (ret-robust) | arXiv 2023/2024 | NLI pre-filter removes irrelevant retrieved passages before generation — prevents wasted tokens on bad context |
| 2606.13438 | **CQC-RAG** | arXiv Jun 2026 | Cross-query consistency voting — only passes confident answers; reduces hallucination-correction retry tokens |
| 2601.06048 | **Noise Filtering Inherently Difficult** | arXiv Jan 2026 | LLM robustness training approach — reduces token waste from incorrect answers that require retry |
| 2603.04238 | **Retrieval or Representation?** | ICLR 2026 Workshop | Preprocessing improvement > retrieval algorithm change — fewer irrelevant documents retrieved → lower context token count |

### Hermes RAG Token Budget Workflow (updated)

1. Preprocessing: normalize/clean retrieved text (Representation > Retrieval finding, 2603.04238)
2. NLI filter: run DeBERTa entailment on query+passage pairs (RetRobust Method 1, 2310.01558)
   - Only pass passages where entailment score > threshold
   - Use transformers: `pipeline("text-classification", model="cross-encoder/nli-deberta-v3-large")`
3. CQC gate: for multi-hop queries, rewrite × 3 → retrieve → vote on consistency (2606.13438)
4. LLMLingua-2 extractive pass on surviving passages (P2 action above)
5. TALE budget hint at P80 per task type (P1 action above)

This ordering ensures bad context never reaches the compressor or the LLM — the token savings multiply.
