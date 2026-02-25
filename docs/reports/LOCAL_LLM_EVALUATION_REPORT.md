# Local LLM Evaluation Report for PratikoAI

**Date:** 2026-02-25
**Author:** Claude Code
**Status:** Research Report
**Scope:** Evaluate opportunities for local LLM adoption across the PratikoAI platform, covering current state, PRATIKO 2.0 features, and cost-benefit analysis.

---

## Executive Summary

PratikoAI already runs one local model (mDeBERTa for intent classification) with proven results: 70% reduction in GPT-4o-mini routing calls, <100ms latency, zero API cost. This report identifies **7 additional opportunities** where local models could reduce costs, improve latency, or enhance GDPR compliance — particularly important as PRATIKO 2.0 introduces client-facing features with higher query volumes and stricter data residency requirements.

**Key findings:**

| Priority | Opportunity | Estimated Savings | Infrastructure Impact |
|----------|------------|-------------------|----------------------|
| HIGH | Local embeddings (replace OpenAI) | €50-200/month | +1GB RAM |
| HIGH | Local reranking | €0 (quality gain) | +1-2GB RAM |
| HIGH | NER for document ingestion | €0 (new capability) | +1GB RAM |
| MEDIUM | Query normalization/expansion | €30-80/month | +1GB RAM |
| MEDIUM | Fine-tuned intent classifier | Accuracy gain 70%→93% | Same footprint |
| LOW | Local HyDE generation | €20-50/month | +4-8GB RAM |
| NOT REC. | Local response synthesis | N/A | Requires GPU |

**Bottom line:** The top 3 opportunities (embeddings, reranking, NER) are achievable on the current Hetzner CPX41 (16GB RAM) with 2-4GB additional RAM usage and zero ongoing API cost. They are strongly recommended. A generative local LLM for response synthesis is NOT recommended given the current hardware constraints and Italian legal domain quality requirements.

---

## 1. Current State

### 1.1 Infrastructure

| Environment | Server | vCPU | RAM | Storage | GPU |
|-------------|--------|------|-----|---------|-----|
| QA | Hetzner CPX21 | 3 | 4GB | 80GB SSD | None |
| Production | Hetzner CPX41 | 8 | 16GB | 240GB SSD | None |

**Critical constraint:** No GPU. All local models must run on CPU. This rules out generative LLMs (7B+ parameters) for latency-sensitive tasks but is adequate for encoder models (BERT-class, <500M parameters).

### 1.2 Current LLM Usage by Pipeline Step

Based on the LangGraph RAG pipeline (134 steps), LLM calls occur at these stages:

| Pipeline Step | Task | Current Model | Tier | Latency | Cost/Call |
|---------------|------|---------------|------|---------|-----------|
| step_034a | Intent classification | mDeBERTa (local) → GPT-4o-mini fallback | LOCAL→BASIC | <100ms local, ~200ms GPT | $0.00 / ~$0.001 |
| step_034a | Complexity routing | GPT-4o-mini | BASIC | ~1.4s | ~$0.001 |
| step_036 | Query normalization | GPT-4o-mini | BASIC | ~500ms | ~$0.001 |
| step_038 | Multi-query expansion | GPT-4o-mini | BASIC | ~7.3s | ~$0.003 |
| step_039 | HyDE generation | Claude 3 Haiku | BASIC | ~7.2s | ~$0.002 |
| step_055 | Cost estimation | Deterministic | — | <1ms | $0.00 |
| step_064 | Response synthesis (ToT/CoT) | GPT-4o / Mistral Large | PREMIUM | ~18.8s | ~$0.09 |
| Embeddings | Vector generation | text-embedding-3-small (OpenAI) | API | ~50ms | ~$0.0001/chunk |

**Total LLM time per query:** ~37.7s (92% of total latency)
**Total LLM cost per query:** ~€0.10 median

### 1.3 Current Local Model: Intent Classification (DEV-251)

| Attribute | Value |
|-----------|-------|
| Model | `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` |
| Size | 280MB |
| RAM Usage | ~280MB |
| Latency | <100ms (after 5s warmup on first call) |
| Accuracy | ~70-80% (zero-shot) |
| Fallback | GPT-4o-mini when confidence < 0.7 |
| Savings | ~70% reduction in routing API calls |

This implementation validates the pattern: lazy-loaded singleton, confidence-based fallback, zero API cost for high-confidence predictions.

### 1.4 Cost Budget Context

| Metric | Value |
|--------|-------|
| Monthly LLM budget | €2,000 |
| Target active users | 500 |
| Per-user monthly budget | €4 |
| Per-query target | <€0.004 (at 1,000 queries/user/month) |
| Current per-query median | €0.10 |

The gap between the per-query target (€0.004) and actual cost (€0.10) is significant. At scale (500 users × 1,000 queries), costs would be €50,000/month — well above the €2,000 budget. This makes cost reduction through local models strategically critical.

---

## 2. Opportunity Analysis

### 2.1 LOCAL EMBEDDINGS — Priority: HIGH

**Current state:** OpenAI `text-embedding-3-small` (1536 dimensions, API call per chunk).

**Proposal:** Replace with `intfloat/multilingual-e5-small` for local embedding generation.

| Attribute | OpenAI (current) | multilingual-e5-small (proposed) |
|-----------|------------------|----------------------------------|
| Dimensions | 1536 | 384 |
| Latency | ~50ms + network | 30-60ms (CPU, no network) |
| Cost | $0.02/1M tokens | $0.00 |
| Italian support | Good | Native (100+ languages) |
| Size | API | 470MB |
| RAM | 0 | ~1GB |
| Max tokens | 8191 | 512 |

**Why this matters for PRATIKO 2.0:**
- **FR-002 (Client Database):** Every client profile generates a vector for normative matching (DEV-322). At 100 clients × 500 studios = 50,000 embeddings.
- **FR-003 (Normative Matching):** Continuous re-embedding as regulations update.
- **FR-008 (Document Enhancement):** New document types (Bilanci, CU) need chunking and embedding.
- **GDPR (Phase 9):** Client PII data never leaves the server. Local embeddings mean no client text is sent to OpenAI.

**Trade-offs:**
- Dimension reduction (1536→384) means less expressive vectors. Mitigation: multilingual-e5 performs comparably on retrieval benchmarks and better on Italian text.
- Token limit (512 vs 8191) requires proper chunking strategy. Already in place (section-aware chunking from DEV-259).
- Requires re-indexing existing pgvector data (one-time migration).

**Cost savings:** ~$50-200/month depending on ingestion volume. Primary value is GDPR compliance and latency reduction.

**Infrastructure:** +1GB RAM on CPX41 (16GB available, ~8-10GB currently used → feasible).

**Recommendation: PROCEED.** This is already partially implemented (`local_provider.py` uses `all-MiniLM-L6-v2`). Upgrade to `multilingual-e5-small` for production Italian support.

---

### 2.2 LOCAL RERANKING — Priority: HIGH

**Current state:** Hybrid search uses a weighted formula (45% FTS + 30% Vector + 10% Recency + 10% Quality + 5% Source) with no neural reranking.

**Proposal:** Add `BAAI/bge-reranker-v2-m3` as a reranking stage after initial retrieval.

| Attribute | Value |
|-----------|-------|
| Model | BAAI/bge-reranker-v2-m3 |
| Size | ~600MB |
| RAM | ~1-2GB |
| Context window | 8192 tokens |
| Latency | 50-100ms per query-document pair |
| Italian support | Native (multilingual) |
| Cost | $0.00 |

**Pipeline integration:**
```
Current:  Hybrid search → top_k results → LLM synthesis
Proposed: Hybrid search → top 30 candidates → Reranker → top 10 → LLM synthesis
```

**Why this matters for PRATIKO 2.0:**
- **FR-003 (Normative Matching):** Matching clients to regulations requires high-precision retrieval. Reranking improves relevance by 20-35%.
- **FR-006 (Deadline System):** Extracting deadlines from KB requires finding the right chunks. Better retrieval = fewer hallucinated deadlines.
- **FR-007 (Fiscal Calculations):** Tax calculation queries need precise article references. Cross-encoder reranking excels at this.

**Trade-offs:**
- Adds 200-500ms latency for reranking 30 candidates. Acceptable given current 37.7s total.
- Actually reduces downstream cost: better retrieved chunks → shorter/better LLM responses → fewer tokens.

**Cost savings:** No direct cost savings, but quality improvement reduces need for premium models on some queries.

**Infrastructure:** +1-2GB RAM. Feasible on CPX41.

**Recommendation: PROCEED.** Strongest quality improvement available without changing the LLM tier.

---

### 2.3 ITALIAN NER FOR DOCUMENT INGESTION — Priority: HIGH

**Current state:** Entity extraction during document ingestion is minimal. Metadata relies on manual tagging or LLM-based extraction.

**Proposal:** Integrate `DeepMount00/Italian_NER_XXL_v2` for automatic entity extraction during document ingestion.

| Attribute | Value |
|-----------|-------|
| Model | DeepMount00/Italian_NER_XXL_v2 |
| Base | BERT |
| Entities | 52 categories |
| Accuracy | 87.5% |
| F1 Score | 89.2% |
| RAM | ~1GB |
| Latency | 20-50ms per document chunk |

**Relevant entity types for PratikoAI:**

| Entity | Type | Use Case |
|--------|------|----------|
| `LEGGE` | Law references | Index regulations by citation |
| `DATA` | Dates | Extract deadlines (FR-006) |
| `IMPORTO` | Monetary amounts | Extract thresholds for calculations (FR-007) |
| `CODICE_FISCALE` | Tax codes | Client matching (FR-002/FR-003) |
| `RAGIONE_SOCIALE` | Company names | Client identification |
| `AVV_NOTAIO` | Professional names | Reference linking |

**Why this matters for PRATIKO 2.0:**
- **FR-002 (Client Database):** Auto-extract client entities from imported documents.
- **FR-003 (Normative Matching):** Extract law references and dates from regulations for structured matching rules.
- **FR-006 (Deadline System):** Automatically extract dates and deadlines from KB documents (DEV-382).
- **FR-007 (Fiscal Calculations):** Extract amounts, thresholds, and percentages from tax regulations.
- **FR-008 (Document Enhancement):** Structured metadata from Bilanci and CU documents.

**Trade-offs:**
- Focused on civil judgments; may need fine-tuning for CCNL/labor law specifics.
- Runs during ingestion (offline), so latency is not critical.

**Cost savings:** Replaces LLM-based entity extraction during ingestion. Primary value is enabling new structured features.

**Infrastructure:** +1GB RAM. Runs only during ingestion (not per-query), so load is intermittent.

**Recommendation: PROCEED.** Critical enabler for PRATIKO 2.0 features FR-003, FR-006, FR-007.

---

### 2.4 LOCAL QUERY NORMALIZATION/EXPANSION — Priority: MEDIUM

**Current state:**
- Query normalization (step_036): GPT-4o-mini corrects typos, expands abbreviations, resolves context.
- Multi-query expansion (step_038): GPT-4o-mini generates 3-5 alternative query formulations.

**Proposal:** Replace query normalization with a local approach; keep multi-query expansion on API.

**Option A: Rule-based + local model hybrid**
- Dictionary-based abbreviation expansion (IVA, IRPEF, IRAP, IMU, etc.)
- Local spell-correction using `symspellpy` or similar (no LLM needed)
- Context-aware correction using conversation history (already partially implemented in DEV-251 Part 2)

**Option B: Small local generative model via Ollama**
- `mistral:7b-instruct` or `phi-3-mini` for query normalization
- Requires Ollama container in docker-compose
- ~4-8GB RAM for 7B model with 4-bit quantization

| Approach | Latency | RAM | Quality | Feasibility |
|----------|---------|-----|---------|-------------|
| Rule-based + dictionary | <10ms | ~50MB | Good for known terms | HIGH |
| Local 7B model (GGUF Q4) | 2-5s on CPU | 4-8GB | Good | MEDIUM (RAM constraint) |

**Why this matters for PRATIKO 2.0:**
- **FR-007 (Fiscal Calculations):** Tax-specific abbreviations need reliable expansion.
- **Cost at scale:** Normalization runs on every query. At 500K queries/month, ~$500/month in API costs.

**Trade-offs:**
- Rule-based approach loses generalization ability but covers 90%+ of Italian tax/legal abbreviations.
- 7B model on CPU is slow (2-5s) but normalization is not on the critical latency path if done in parallel.
- RAM impact of 7B model is significant on CPX41 (4-8GB of 16GB).

**Recommendation: PROCEED WITH OPTION A (rule-based).** A dictionary-based approach handles the majority of Italian fiscal abbreviations deterministically and at zero cost. Defer Option B until a GPU-equipped server or Hetzner GPU instance is available.

---

### 2.5 FINE-TUNED INTENT CLASSIFIER — Priority: MEDIUM

**Current state:** Zero-shot mDeBERTa achieves ~70-80% accuracy with 0.7 confidence threshold.

**Proposal:** Fine-tune `dbmdz/bert-base-italian-cased` on labeled data from expert feedback.

| Attribute | Zero-shot (current) | Fine-tuned (target) |
|-----------|---------------------|---------------------|
| Accuracy | 70-80% | 90-95% |
| Confidence > 0.7 rate | ~75% | ~95% |
| GPT fallback rate | ~25% | ~5% |
| Model size | 280MB | 420MB |
| Latency | <100ms | <30ms |
| Training data needed | None | ~200+ labeled examples per category |

**Why this matters for PRATIKO 2.0:**
- **FR-001 (Procedural Guides):** New intent category "guide_request" needs classification.
- **FR-007 (Fiscal Calculations):** Calculator intent must be reliably detected to route to deterministic calculation engine.
- **Volume increase:** More users = more queries = more fallback costs.

**Current progress:**
- DEV-253 (Expert Labeling UI) is defined with GitHub Issue #1009.
- ADR-030 documents the model versioning workflow via HF Hub.
- `scripts/train_intent_classifier.py` and training guide already exist.
- The infrastructure (HF Hub private repos, Docker build integration, rollback workflow) is ready.

**Trade-offs:**
- Requires labeled data collection (needs expert time from commercialisti).
- Fixed categories (adding a new intent requires retraining).
- Already planned — this is a matter of execution, not evaluation.

**Recommendation: PROCEED when sufficient labeled data is available (target: 200+ examples per category).** The infrastructure is already in place. This is the natural next step after DEV-253 labeling UI.

---

### 2.6 LOCAL HyDE GENERATION — Priority: LOW

**Current state:** Claude 3 Haiku generates hypothetical documents for HyDE (Hypothetical Document Embeddings), ~7.2s per query.

**Proposal:** Replace with a local generative model (Mistral 7B via Ollama).

| Attribute | Claude 3 Haiku (current) | Mistral 7B Q4 (proposed) |
|-----------|--------------------------|--------------------------|
| Latency | ~7.2s (network included) | 5-15s (CPU, no network) |
| Cost | ~$0.002/call | $0.00 |
| Quality | High | Moderate (7B vs 20B+) |
| RAM | 0 | 4-8GB |
| Italian quality | Good | Moderate |

**Why this is LOW priority:**
- HyDE quality directly impacts retrieval quality. A weaker hypothetical document generates worse embeddings.
- Latency on CPU may be worse than API (5-15s vs 7.2s).
- Cost is only ~$0.002/call (~$1,000/month at 500K queries) — relatively low.
- RAM impact is significant (4-8GB of 16GB available).
- Italian legal domain requires specialized vocabulary that 7B models handle poorly.

**Trade-offs:**
- Risk of retrieval quality degradation if hypothetical documents are lower quality.
- RAM consumption competes with other local models (embeddings, reranker, NER).
- CPU inference is not faster than API for generative tasks.

**Recommendation: DEFER.** The cost-quality trade-off does not favor local HyDE on current hardware. Reconsider when:
1. A Hetzner GPU instance becomes available (GEX44 with RTX 3060 — €50/month), or
2. A smaller, Italian-specialized generative model becomes available (<3B parameters with Italian legal training).

---

### 2.7 LOCAL RESPONSE SYNTHESIS — Priority: NOT RECOMMENDED

**Current state:** GPT-4o / Mistral Large generates the final user-facing response via Tree of Thoughts (18.8s, ~$0.09/query).

**Why NOT recommended:**

| Factor | Requirement | Local Model Reality |
|--------|-------------|---------------------|
| Italian legal accuracy | Must cite exact articles, commas, lettere | 7B models hallucinate citations |
| Token budget | 4,000+ output tokens | 7B on CPU: minutes per response |
| Structured reasoning | Tree of Thoughts with 3 branches | Requires instruction-following at GPT-4 level |
| Liability | Professionals rely on answers for compliance | Cannot risk degraded accuracy |
| RAM | — | 8-16GB for a usable model |

**The core issue:** PratikoAI serves Italian accountants who make compliance decisions based on the responses. Legal citation accuracy is non-negotiable. Current frontier models (GPT-4o, Claude 3.5 Sonnet, Mistral Large) achieve this; open 7B-13B models do not, especially for Italian legal text.

**When to reconsider:**
- When open Italian legal models reach GPT-4-level quality on Italian tax/legal benchmarks.
- When Hetzner offers affordable GPU instances with 24GB+ VRAM.
- When quantized 70B models can run with acceptable latency on available hardware.

**Recommendation: DO NOT PROCEED.** Continue using PREMIUM-tier API models for response synthesis. The risk to professional users from lower-quality legal responses far outweighs cost savings.

---

## 3. PRATIKO 2.0 Feature-Specific Analysis

### 3.1 FR-002: Studio Client Database — Local Model Opportunities

| Task | Current Approach | Local Model Opportunity |
|------|-----------------|------------------------|
| Client profile vectorization | OpenAI embeddings | Local multilingual-e5 embeddings |
| Client data extraction from docs | Manual entry | NER model (codice_fiscale, ragione_sociale) |
| PII detection for GDPR | — | NER model for automatic PII flagging |

**GDPR impact:** With client PII (codice fiscale, P.IVA, contact info), local embeddings ensure client data never leaves the server for vectorization. This is a compliance advantage.

### 3.2 FR-003: Normative Matching — Local Model Opportunities

| Task | Current Approach | Local Model Opportunity |
|------|-----------------|------------------------|
| Regulation embedding | OpenAI API | Local multilingual-e5 |
| Entity extraction from regulations | LLM-based | NER model (LEGGE, DATA, IMPORTO) |
| Client-regulation matching | Vector similarity | Local embeddings + reranker |
| Match confidence scoring | LLM evaluation | Local cross-encoder score |

**Key insight:** The matching engine (DEV-320 to DEV-329) runs as a background service, not real-time. This means CPU latency for local models is acceptable — background jobs can tolerate 50-100ms per reranking pair.

### 3.3 FR-006: Proactive Deadline System — Local Model Opportunities

| Task | Current Approach | Local Model Opportunity |
|------|-----------------|------------------------|
| Deadline extraction from KB | Not yet implemented | NER model (DATA entities) |
| Deadline-client matching | Not yet implemented | Local embeddings + reranker |
| Notification text generation | LLM synthesis | API model (quality-critical, user-facing) |

**Key insight:** Deadline extraction (DEV-382) is a perfect NER use case. The `DATA` entity type from Italian_NER_XXL_v2 can extract dates from regulatory documents during ingestion, building a structured deadline database without LLM calls.

### 3.4 FR-007: Fiscal Calculations — Local Model Opportunities

| Task | Current Approach | Local Model Opportunity |
|------|-----------------|------------------------|
| Intent detection ("calculator") | mDeBERTa zero-shot | Fine-tuned classifier (higher accuracy) |
| Parameter extraction from query | LLM-based | NER model (IMPORTO, percentages) |
| Calculation execution | Deterministic code | Deterministic code (no change) |
| Result presentation | LLM synthesis | API model (user-facing) |

**Key insight:** Fiscal calculations must be deterministic (not LLM-generated). Local models help with intent detection and parameter extraction, routing to calculation engines rather than LLMs.

### 3.5 FR-008: Document Enhancement — Local Model Opportunities

| Task | Current Approach | Local Model Opportunity |
|------|-----------------|------------------------|
| Document type detection | LLM-based (ADR-022) | Fine-tuned classifier |
| Entity extraction from Bilanci | Not implemented | NER model (IMPORTO, RAGIONE_SOCIALE) |
| CU data parsing | Not implemented | NER + rule-based extraction |
| Chunk embedding | OpenAI API | Local multilingual-e5 |

---

## 4. Infrastructure Feasibility

### 4.1 RAM Budget on Hetzner CPX41 (16GB)

| Component | Current RAM | With Local Models |
|-----------|-------------|-------------------|
| PostgreSQL + pgvector | ~2GB | ~2GB |
| Redis | ~1GB (allocated) | ~1GB |
| FastAPI application | ~1GB | ~1GB |
| mDeBERTa (intent classifier) | ~280MB | ~280MB |
| **New: multilingual-e5-small** | — | **+1GB** |
| **New: bge-reranker-v2-m3** | — | **+1.5GB** |
| **New: Italian_NER_XXL_v2** | — | **+1GB** |
| **New: fine-tuned intent classifier** | — | **+420MB** (replaces mDeBERTa) |
| OS + buffers | ~2GB | ~2GB |
| **TOTAL** | ~6.3GB | **~10.2GB** |
| **Headroom** | ~9.7GB free | **~5.8GB free** |

**Verdict:** The top 3 recommendations (embeddings, reranker, NER) fit within the CPX41's 16GB with comfortable headroom. Adding a generative model (7B = 4-8GB) would push RAM to the limit.

### 4.2 CPU Budget

| Model Type | CPU Usage | Concurrency Impact |
|------------|-----------|-------------------|
| Embedding (inference) | 2-4 cores for 30-60ms | Minimal per-request |
| Reranker (30 candidates) | 2-4 cores for 200-500ms | Moderate per-request |
| NER (ingestion-time) | 2-4 cores for 20-50ms | Background only |
| Classifier (inference) | 1-2 cores for <100ms | Minimal per-request |

On CPX41 (8 vCPU), these models can run concurrently with the main application. The reranker is the heaviest per-request load but adds only 200-500ms to a pipeline that already takes 37+ seconds.

### 4.3 Scaling Considerations

| Scenario | Users | Queries/month | Can CPX41 Handle? |
|----------|-------|--------------|-------------------|
| Current | ~50 | ~50K | Yes, easily |
| Growth target | 500 | 500K | Yes, with batching |
| Scale-out signal | 1000+ | 1M+ | Consider dedicated ML server |

**When to add a dedicated ML server:** If query volume exceeds ~1M/month, consider a separate Hetzner server (CPX41 or GEX44 with GPU) running only the local models as a microservice, accessed via internal API. This decouples ML scaling from application scaling.

---

## 5. Cost-Benefit Summary

### 5.1 Monthly Cost Projections at Scale (500 users, 500K queries)

| Component | Current (API) | With Local Models | Savings |
|-----------|--------------|-------------------|---------|
| Embeddings | ~$100-200 | $0 | $100-200/month |
| Intent classification | ~$150 (30% fallback) | ~$40 (5% fallback) | ~$110/month |
| Query normalization | ~$500 | ~$50 (rule-based + reduced fallback) | ~$450/month |
| Reranking | $0 (not available) | $0 (local) | $0 (quality gain) |
| NER extraction | ~$200 (LLM-based) | $0 (local) | ~$200/month |
| HyDE generation | ~$1,000 | ~$1,000 (keep on API) | $0 |
| Response synthesis | ~$45,000 | ~$45,000 (keep on API) | $0 |
| **TOTAL** | **~$47,150** | **~$46,090** | **~$1,060/month** |

**Note:** The savings from local models ($1,060/month) are modest compared to total LLM spend because response synthesis (the most expensive step) remains on API models. However, the non-cost benefits (GDPR compliance, quality improvement from reranking, new NER capabilities) are substantial.

### 5.2 One-Time Implementation Costs

| Task | Estimated Effort | Priority |
|------|-----------------|----------|
| Local embeddings integration + re-indexing | 3-5 days | HIGH |
| Reranker integration in hybrid search | 2-3 days | HIGH |
| NER integration in document ingestion | 3-5 days | HIGH |
| Rule-based query normalization | 2-3 days | MEDIUM |
| Fine-tuned intent classifier (needs labels) | 5-7 days + data collection | MEDIUM |
| Ollama setup for HyDE | 3-5 days | LOW (deferred) |

### 5.3 Non-Cost Benefits

| Benefit | Impact | Relevant Features |
|---------|--------|-------------------|
| **GDPR data residency** | Client PII never leaves server | FR-002, Phase 9 (GDPR) |
| **Retrieval quality** | 20-35% improvement from reranking | FR-003, FR-006, FR-007 |
| **Structured metadata** | Automatic entity extraction | FR-003, FR-006, FR-008 |
| **Resilience** | Reduced API dependency | All features |
| **Latency** | Faster embeddings (no network) | All RAG queries |

---

## 6. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Quality degradation from local embeddings | Medium | High | A/B test against OpenAI embeddings before cutover; keep OpenAI as fallback |
| RAM exhaustion on CPX41 | Low | High | Monitor memory usage; lazy-load models; load NER only during ingestion |
| Italian legal NER accuracy gap | Medium | Medium | Validate on CCNL/tax document corpus before deploying; fine-tune if needed |
| Model loading cold start | Low | Low | Pre-warm models on container startup; already solved for mDeBERTa |
| Reranker latency spike under load | Low | Medium | Limit reranker to top-30 candidates; add timeout fallback |
| Embedding dimension mismatch during migration | Medium | High | Run dual-index period; migrate vectors in batches; verify retrieval quality |

---

## 7. Recommended Implementation Roadmap

### Phase 1: Foundation (Immediate)

**Goal:** Add local embeddings and reranker for GDPR compliance and quality.

1. **Upgrade local embeddings** from `all-MiniLM-L6-v2` to `intfloat/multilingual-e5-small`
   - Update `local_provider.py` with new model
   - Run quality comparison benchmarks against OpenAI embeddings
   - Plan pgvector re-indexing migration

2. **Integrate reranker** into hybrid search pipeline
   - Add `BAAI/bge-reranker-v2-m3` as post-retrieval reranking step
   - Configure: retrieve top 30 → rerank → return top 10
   - Benchmark retrieval quality improvement

### Phase 2: Entity Extraction (With PRATIKO 2.0 Phase 0-1)

**Goal:** Enable structured data extraction for client database and matching engine.

3. **Integrate Italian NER** into document ingestion
   - Add `DeepMount00/Italian_NER_XXL_v2` to ingestion pipeline
   - Extract and store entities as document metadata
   - Build entity index for structured queries

4. **Rule-based query normalization**
   - Build Italian fiscal abbreviation dictionary
   - Integrate `symspellpy` for spell correction
   - Reduce GPT-4o-mini normalization calls by ~80%

### Phase 3: Classification Improvement (With PRATIKO 2.0 Phase 4-5)

**Goal:** Improve intent classification accuracy for new feature routing.

5. **Deploy expert labeling UI** (DEV-253)
   - Collect 200+ labeled examples per intent category
   - Add new categories for PRATIKO 2.0 features (e.g., `guide_request`, `deadline_query`)

6. **Train and deploy fine-tuned classifier**
   - Fine-tune `dbmdz/bert-base-italian-cased`
   - Validate: target 90%+ accuracy on test set
   - Deploy via HF Hub (ADR-030 workflow)

### Phase 4: Evaluate Generative (Future — When GPU Available)

**Goal:** Assess local generative models for pipeline tasks.

7. **Evaluate Hetzner GPU instances** (GEX44 with RTX 3060, ~€50/month)
8. **Benchmark Mistral 7B / Llama 3 8B** on Italian legal tasks
9. **If quality sufficient:** Replace HyDE generation and query expansion
10. **If quality insufficient:** Continue with API models

---

## 8. Comparison: Local vs API for Each Task

| Task | Recommend Local? | Reason |
|------|-----------------|--------|
| Intent classification | **YES** (already done) | High volume, low complexity, proven pattern |
| Embeddings | **YES** | GDPR compliance, zero cost, comparable quality |
| Reranking | **YES** | Quality improvement, zero cost, no API equivalent |
| NER/Entity extraction | **YES** | New capability, offline task, zero cost |
| Query normalization | **PARTIAL** | Rule-based for 80%, API fallback for complex cases |
| Fine-tuned classification | **YES** (when data ready) | Higher accuracy, lower fallback rate |
| HyDE generation | **NO** (defer) | Quality risk, RAM heavy, modest savings |
| Multi-query expansion | **NO** | Requires creative generation ability |
| Response synthesis | **NO** | Quality-critical, requires frontier model capability |

---

## 9. Conclusion

PratikoAI is well-positioned to expand its local model usage from the current single intent classifier to a suite of 4-5 local models covering embeddings, reranking, NER, and classification. These models:

1. **Fit within current infrastructure** (CPX41, 16GB RAM, no GPU)
2. **Align with PRATIKO 2.0 requirements** (client data privacy, normative matching, deadline extraction)
3. **Follow the proven pattern** established by DEV-251 (lazy loading, singleton, confidence-based fallback)
4. **Provide the highest value** where the task is high-volume, classification/retrieval-oriented, and does not require generative capability

The generative tasks (HyDE, multi-query expansion, response synthesis) should remain on API models until GPU hardware becomes available or open Italian legal models reach sufficient quality.

**Strategic principle:** Use local models for the "plumbing" (classification, embedding, extraction, reranking) and API models for the "intelligence" (reasoning, synthesis, generation). This maximizes cost savings and data privacy while preserving answer quality where it matters most — in the user-facing response.

---

## References

| Document | Location |
|----------|----------|
| ADR-025: Model Tiering | `docs/architecture/decisions/ADR-025-llm-model-inventory-and-tiering.md` |
| ADR-027: Usage-Based Billing | `docs/architecture/decisions/ADR-027-usage-based-billing.md` |
| ADR-030: ML Model Versioning | `docs/architecture/decisions/ADR-030-ml-model-versioning.md` |
| DEV-251: HuggingFace Classifier | `docs/DEV-251-huggingface-intent-classifier.md` |
| HuggingFace Models Analysis | `docs/HUGGINGFACE_MODELS_ANALYSIS.md` |
| AI Architect Knowledge Base | `docs/architecture/AI_ARCHITECT_KNOWLEDGE_BASE.md` |
| PRATIKO 2.0 Roadmap | `docs/tasks/PRATIKO_2.0.md` |
| Deployment Platform Analysis | `docs/deployment/DEPLOYMENT_PLATFORM_ANALYSIS.md` |
| Intent Classifier Training Guide | `docs/intent-classifier-training-guide.md` |
| LLM Model Registry | `config/llm_models.yaml` |
| Billing Plans | `config/billing_plans.yaml` |
