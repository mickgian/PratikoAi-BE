# Hugging Face Models for PratikoAI - Analysis Report

> **Date:** January 2026 (Updated: March 2026)
> **Purpose:** Evaluate small, CPU-efficient Hugging Face models for PratikoAI's Italian legal/labor domain

## Executive Summary

This report analyzes small, CPU-efficient Hugging Face models suitable for PratikoAI's Italian legal/labor domain. Focus areas: embeddings, reranking, NER, and classification.

**Key Recommendation:** Start with embedding models (immediate cost savings) + Italian NER (domain value), then add reranking for search quality.

**March 2026 Update — Embedding Deep Dive:** Added comprehensive analysis of current OpenAI embedding costs, API alternatives (Cohere, Voyage AI, Google, Mistral), industry-leading local models (BGE-M3, Nomic Embed v2), and a migration plan. **Primary recommendation upgraded from multilingual-e5-small to BAAI/bge-m3** based on hybrid retrieval support, Italian quality, and alignment with PratikoAI's hybrid search architecture.

---

## 1. Embedding Models (Replace OpenAI Embeddings)

### 1.0 Current State: OpenAI text-embedding-3-small

PratikoAI currently uses OpenAI's `text-embedding-3-small` via API calls in `app/core/embed.py`.

**Current configuration:**

| Setting | Value | Source |
|---------|-------|--------|
| Model | `text-embedding-3-small` | `EMBED_MODEL` env var / `app/core/config.py:499` |
| Dimensions | 1536 | `EMBED_DIM` env var / `app/core/config.py:500` |
| Max tokens | 8,191 | `app/core/embed.py:29` |
| Batch size | 20 texts/API call | `app/core/embed.py:92` |
| Retry | 3 attempts, exponential backoff 1-10s | `app/core/embed.py:50-55` |
| Backfill | Daily at 03:00 Rome time | `app/services/scheduler_service.py` |

**Where embeddings are stored (all Vector(1536)):**
- `knowledge_chunks.embedding` — document chunks (primary search path)
- `faq_entries.question_embedding` — FAQ semantic search
- `client_profiles.profile_vector` — client matching
- `expert_faq_candidates.embedding` — expert FAQ matching

**Cost analysis (yes, we pay per API call):**

| Metric | Value |
|--------|-------|
| OpenAI price | ~$0.02 per 1M tokens |
| Per embedding (avg 500 tokens) | ~$0.00001 |
| 5,000 embeddings/day | ~$0.05/day |
| Monthly estimate | ~$1.50/month |
| Annual estimate | ~$18/year |

The dollar cost is low, but the real concerns are:
1. **Latency** — 200-500ms per batch API call during ingestion
2. **Reliability** — OpenAI outage = no embeddings (backfill mitigates but delays)
3. **GDPR** — document text sent to OpenAI's US servers for embedding
4. **Vendor lock-in** — dimension change requires full re-embedding + migration

---

### 1.1 API Alternatives to OpenAI

Before looking at local models, here are the commercial API alternatives:

| Provider | Model | MTEB Score | Dims | Price/1M tokens | Italian Support | Notes |
|----------|-------|-----------|------|-----------------|-----------------|-------|
| **OpenAI** | text-embedding-3-small | ~62 | 1536 | $0.02 | Fair | Current setup |
| **OpenAI** | text-embedding-3-large | ~64.6 | 3072 | $0.13 | Fair | Better quality, 6.5x cost |
| **Cohere** | embed-v4 | ~65.2 | 1024 | $0.10 | Good | Best overall API quality, handles noisy data |
| **Voyage AI** | voyage-3.5 | ~65+ | 2048 | $0.06 | Good | Excellent for code/legal, Matryoshka dims |
| **Google** | gemini-embedding-001 | ~63 | 3072 | **Free** (rate limits) | Good | Free tier generous, good multilingual |
| **Mistral** | mistral-embed | ~60 | 1024 | $0.10 | Good | EU company (GDPR advantage) |

**Note:** Anthropic does **NOT** offer an embedding model.

**Verdict:** If staying on API, **Voyage AI** offers the best price/quality ratio for legal domains. **Google** is worth testing for the free tier. However, local models are the better long-term path for PratikoAI given GDPR, latency, and cost concerns.

---

### 1.2 BAAI/bge-m3 (NEW — Recommended for Production)

| Attribute | Value |
|-----------|-------|
| **Size** | ~2.2GB |
| **Parameters** | 568M |
| **Dimensions** | 1024 |
| **Max Tokens** | 8,192 |
| **Inference** | ~50ms CPU |
| **License** | MIT |

**Pros:**
- **Native Italian support** (100+ languages, trained on multilingual data)
- **Hybrid retrieval** — supports dense, sparse, AND multi-vector (matches PratikoAI's hybrid search architecture perfectly)
- **8,192 token context** — same as OpenAI, no chunking compromises
- **MTEB ~63** — competitive with OpenAI text-embedding-3-small
- Fits on Hetzner CX33 (2GB RAM for model, server has 8GB)
- **GDPR compliant** — data never leaves your server
- **Zero marginal cost** at any scale
- Active community, well-maintained, battle-tested in production systems

**Cons:**
- 2.2GB download (one-time)
- Slower than smaller models on CPU (~50ms vs ~5ms for MiniLM)
- Requires `sentence-transformers` library (already in dependencies)

**Why BGE-M3 over multilingual-e5-small (previous recommendation):**
- 8K context vs 512 tokens — critical for legal documents
- Hybrid retrieval support aligns with ADR-002 hybrid search
- Higher MTEB scores across retrieval benchmarks
- Actively maintained with regular updates

**Source:** [HuggingFace](https://huggingface.co/BAAI/bge-m3)

---

### 1.3 nomic-ai/nomic-embed-text-v2-moe (NEW — Runner-Up)

| Attribute | Value |
|-----------|-------|
| **Size** | ~1.5GB |
| **Active Parameters** | 305M (MoE architecture) |
| **Dimensions** | 768 |
| **Max Tokens** | 8,192 |
| **Inference** | ~30ms CPU |
| **License** | Apache 2.0 |

**Pros:**
- Mixture-of-Experts (MoE) — only activates 305M of total parameters per inference
- 8,192 token context window
- Matryoshka representations (can use smaller dims: 256, 512, 768)
- Smaller and faster than BGE-M3
- Apache 2.0 license — maximally permissive

**Cons:**
- Less proven on Italian legal text than BGE-M3
- Newer model, less production track record
- 768 dims (lower expressiveness than BGE-M3's 1024)

**Source:** [HuggingFace](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)

---

### 1.4 intfloat/e5-large-v2

| Attribute | Value |
|-----------|-------|
| **Size** | ~1.3GB |
| **Parameters** | 335M |
| **Dimensions** | 1024 |
| **Max Tokens** | 512 |
| **Inference** | ~40ms CPU |
| **License** | MIT |

**Pros:**
- Strong MTEB scores (~62) for its size
- 1024 dimensions — same as BGE-M3
- Well-established, battle-tested

**Cons:**
- 512 token limit (vs 8K for BGE-M3 and Nomic)
- English-centric (fair Italian, not native)
- No hybrid retrieval support

---

### 1.5 intfloat/multilingual-e5-small (Previous Recommendation)

| Attribute | Value |
|-----------|-------|
| **Size** | 470MB |
| **Dimensions** | 384 |
| **Max Tokens** | 512 |
| **Inference** | 20-40ms CPU |
| **License** | MIT |

**Pros:**
- **Native Italian support** (100+ languages)
- Better for Italian legal text than English models
- Good balance of size/quality

**Cons:**
- 384 dimensions — less expressive than BGE-M3's 1024
- 512 token limit — insufficient for legal documents
- Requires prefix: "query: " or "passage: "
- **Superseded by BGE-M3** for PratikoAI's use case

**Source:** [HuggingFace](https://huggingface.co/intfloat/multilingual-e5-small)

---

### 1.6 all-MiniLM-L6-v2 (Dev/Testing)

| Attribute | Value |
|-----------|-------|
| **Size** | 90MB |
| **Dimensions** | 384 |
| **Max Tokens** | 256 |
| **Inference** | 5-15ms CPU |
| **License** | Apache 2.0 |

**Pros:**
- Already in codebase (`local_provider.py`)
- Extremely fast on CPU
- Well-tested, stable, huge community

**Cons:**
- English-optimized (not ideal for Italian)
- 384 dimensions vs 1024/1536 (less expressive)
- 256 token limit (too small for legal docs)

**Source:** [HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

---

### 1.7 Model2Vec Static Embeddings (Pre-filtering Only)

| Attribute | Value |
|-----------|-------|
| **Size** | ~30MB |
| **Inference** | <1ms CPU |
| **License** | Apache 2.0 |

**Pros:**
- **400x faster** than transformer models
- Dictionary lookup, no neural network
- Perfect for high-throughput pre-filtering

**Cons:**
- Lower quality than transformer embeddings
- No contextual understanding
- Best as pre-filter, not primary embedder

**Source:** [HuggingFace Blog](https://huggingface.co/blog/static-embeddings)

---

### Embedding Models Comparison (Updated March 2026)

| Model | Size | Dims | Context | Italian | MTEB | Speed (CPU) | License | Recommendation |
|-------|------|------|---------|---------|------|-------------|---------|----------------|
| OpenAI text-embedding-3-small | API | 1536 | 8,191 | Fair | ~62 | 200-500ms (network) | Proprietary | Current (migrate away) |
| **BAAI/bge-m3** | **2.2GB** | **1024** | **8,192** | **Native** | **~63** | **~50ms** | **MIT** | **Production (NEW)** |
| nomic-embed-text-v2-moe | 1.5GB | 768 | 8,192 | Good | ~62 | ~30ms | Apache 2.0 | Alternative |
| intfloat/e5-large-v2 | 1.3GB | 1024 | 512 | Fair | ~62 | ~40ms | MIT | English-heavy content |
| multilingual-e5-small | 470MB | 384 | 512 | Native | ~59 | 20-40ms | MIT | Lightweight option |
| all-MiniLM-L6-v2 | 90MB | 384 | 256 | Fair | ~56 | 5-15ms | Apache 2.0 | Dev/Testing only |
| Model2Vec | 30MB | varies | — | Varies | ~45 | <1ms | Apache 2.0 | Pre-filtering only |

---

### Industry Best Practices for Embedding Selection

**What production RAG systems typically do:**

1. **Start with API** (OpenAI/Cohere) to validate search quality quickly ← PratikoAI is here
2. **Evaluate local models** on domain-specific benchmarks (Italian legal retrieval)
3. **Fine-tune** a local model on domain data → typically +10-30% retrieval accuracy
4. **Self-host** once volume justifies it and quality is validated

**For Italian regulatory/legal documents specifically:**

- Generic English-trained models handle Italian legal terminology poorly
- A fine-tuned BGE-M3 on Italian legal/CCNL corpus would likely **outperform** OpenAI
- Fine-tuning cost: one-time ~$50-100 on a GPU cloud instance (e.g., RunPod, Lambda)
- The hybrid retrieval capability of BGE-M3 (dense + sparse + multi-vector) directly maps to PratikoAI's ADR-002 hybrid search architecture

**Key industry principles:**

- **Embedding dimension ≠ quality** — 1024-dim BGE-M3 matches 1536-dim OpenAI on retrieval benchmarks
- **Context length matters** — legal documents often exceed 512 tokens; 8K context avoids information loss
- **Domain fine-tuning > model size** — a fine-tuned 568M model outperforms a generic 175B model on domain tasks
- **Matryoshka embeddings** — models like Nomic v2 allow trading dimension for speed at query time without retraining

---

### Migration Plan: OpenAI → BGE-M3

**This is a breaking change** — all existing embeddings become dimension-incompatible.

**Steps:**
1. Add `sentence-transformers` + BGE-M3 to `app/core/embed.py` (behind feature flag)
2. Update `EMBED_DIM` from `1536` → `1024`
3. Alembic migration: alter `Vector(1536)` → `Vector(1024)` on all embedding columns:
   - `knowledge_chunks.embedding`
   - `faq_entries.question_embedding`
   - `client_profiles.profile_vector`
   - `expert_faq_candidates.embedding`
4. One-time batch re-embedding of all existing documents
5. Rebuild IVFFlat indexes with new dimensions
6. Update `app/services/profile_embedding_service.py` for new model
7. Validate search quality on golden set (`tests/orchestrators/test_step_127_embedding_integration.py`)

**Estimated effort:** 3-5 days including migration, testing, and quality validation.
**Downtime:** Requires a maintenance window for the re-embedding batch job.

---

## 2. Reranking Models (Improve Hybrid Search)

### 2.1 cross-encoder/ms-marco-MiniLM-L-6-v2 (Recommended)

| Attribute | Value |
|-----------|-------|
| **Size** | 90MB |
| **Max Tokens** | 512 |
| **Inference** | 20-50ms per pair |
| **License** | Apache 2.0 |

**Pros:**
- Fast, small, well-tested
- Great baseline performance
- Easy integration with sentence-transformers

**Cons:**
- English-only trained
- May underperform on Italian legal jargon

**Source:** [OpenAI Cookbook](https://cookbook.openai.com/examples/search_reranking_with_cross-encoders)

---

### 2.2 BAAI/bge-reranker-v2-m3 (Best Multilingual)

| Attribute | Value |
|-----------|-------|
| **Size** | ~600MB |
| **Max Tokens** | 8192 |
| **Languages** | 100+ |
| **Inference** | 50-100ms per pair |
| **License** | Apache 2.0 |

**Pros:**
- **Native Italian support**
- 8K context window (full documents)
- State-of-the-art multilingual quality
- M3 = Multi-lingual, Multi-granularity, Multi-functionality

**Cons:**
- Larger model, slower inference
- May need batching for many candidates

**Source:** [HuggingFace](https://huggingface.co/BAAI/bge-reranker-base)

---

### 2.3 Jina-reranker-v2-base-multilingual

| Attribute | Value |
|-----------|-------|
| **Size** | ~550MB |
| **Max Tokens** | 1024 |
| **Inference** | 40-80ms per pair |
| **License** | Apache 2.0 |

**Pros:**
- Flash attention (faster inference)
- Good multilingual performance
- Well-documented API

**Cons:**
- Smaller context than BGE-M3
- Newer, less battle-tested

**Source:** [ZeroEntropy Guide](https://www.zeroentropy.dev/articles/ultimate-guide-to-choosing-the-best-reranking-model-in-2025)

---

### Reranking Impact on PratikoAI

Current hybrid search: `45% FTS + 30% Vector + 10% Recency + 10% Quality + 5% Source`

**With reranker added:**
```
1. Hybrid search returns top 30 candidates
2. Cross-encoder reranks to top 10
3. Expected improvement: 20-35% better relevance
4. Added latency: 200-500ms (acceptable for quality gain)
```

---

## 3. Italian NER Models (Extract Entities from Legal Docs)

### 3.1 fabiod20/italian-legal-ner (Best for Legal)

| Attribute | Value |
|-----------|-------|
| **Base** | ELECTRA |
| **Domain** | Italian civil judgments |
| **Training** | 9,000 Cassazione judgments (2016-2021) |
| **License** | Check repository |

**Pros:**
- **Trained on Italian legal documents** (Corte di Cassazione)
- Domain-specific entity types
- Production-tested on real judgments

**Cons:**
- Focused on civil judgments (may not cover labor law fully)
- Smaller training set than general models

**Source:** [HuggingFace](https://huggingface.co/fabiod20/italian-legal-ner)

---

### 3.2 DeepMount00/Italian_NER_XXL_v2 (Most Comprehensive)

| Attribute | Value |
|-----------|-------|
| **Base** | BERT |
| **Entities** | 52 categories |
| **Accuracy** | 87.5% |
| **F1 Score** | 89.2% |
| **License** | Check repository |

**Entity types relevant to PratikoAI:**
- `RAGIONE_SOCIALE` - Company legal names
- `CODICE_FISCALE` - Tax codes (personal/business)
- `AVV_NOTAIO` - Lawyers, notaries
- `LEGGE` - Law references
- `DATA` - Dates
- `IMPORTO` - Monetary amounts

**Pros:**
- **52 entity categories** (most comprehensive for Italian)
- Covers legal, financial, privacy domains
- High accuracy (87.5%)
- Active development

**Cons:**
- Larger model
- May need fine-tuning for CCNL-specific terms

**Source:** [HuggingFace](https://huggingface.co/DeepMount00/Italian_NER_XXL_v2)

---

### 3.3 dlicari/Italian-Legal-BERT (Base for Fine-tuning)

| Attribute | Value |
|-----------|-------|
| **Base** | Italian XXL BERT |
| **Training** | 3.7GB National Jurisprudential Archive |
| **Tasks** | NER, Classification, Similarity |

**Pros:**
- Pre-trained on Italian legal corpus
- Good base for fine-tuning on CCNL/labor law
- Supports multiple downstream tasks

**Cons:**
- Requires fine-tuning for NER
- Less "out of box" than XXL_v2

**Source:** [HuggingFace](https://huggingface.co/dlicari/Italian-Legal-BERT)

---

### NER Integration Benefits for PratikoAI

| Use Case | Benefit |
|----------|---------|
| Document ingestion | Auto-extract companies, laws, dates |
| Search enhancement | Filter by entity type |
| Knowledge base | Structured metadata extraction |
| Compliance | Identify PII for GDPR |
| CCNL matching | Extract contract references |

---

## 4. Classification Models (Intent Detection, Routing)

### 4.1 dbmdz/bert-base-italian-cased (Base Model)

| Attribute | Value |
|-----------|-------|
| **Size** | 420MB |
| **License** | MIT |

**Pros:**
- Standard Italian BERT, well-tested
- Good base for fine-tuning classifiers
- Large community support

**Use in PratikoAI:** Fine-tune for intent classification to replace GPT calls in router.

**Source:** [HuggingFace](https://huggingface.co/dbmdz/bert-base-italian-cased)

---

### 4.2 neuraly/bert-base-italian-cased-sentiment

| Attribute | Value |
|-----------|-------|
| **Accuracy** | 82% |
| **Classes** | Positive/Negative/Neutral |

**Pros:**
- Ready to use for sentiment
- Could inform response tone

**Source:** [HuggingFace](https://huggingface.co/neuraly/bert-base-italian-cased-sentiment)

---

## 5. Resource Requirements on Hetzner

Assuming Hetzner server without GPU:

| Model Type | RAM | CPU Cores | Inference Time |
|------------|-----|-----------|----------------|
| Embedding (small) | 500MB | 1-2 | 10-30ms |
| Embedding (multilingual) | 1GB | 2-4 | 30-60ms |
| Reranker | 1-2GB | 2-4 | 50-100ms/pair |
| NER | 1GB | 2-4 | 20-50ms |
| Classifier | 1GB | 2-4 | 10-30ms |

**Total additional RAM needed:** ~2-4GB for running multiple models

---

## 6. Recommended Implementation Roadmap

### Phase 1: Quick Wins
1. **Replace OpenAI with BAAI/bge-m3** as primary embedding model
   - Eliminate API dependency and latency (200-500ms → ~50ms)
   - Native Italian support, 8K context, hybrid retrieval
   - GDPR compliant (data stays on Hetzner)
   - Files: `app/core/embed.py`, `app/core/config.py`, Alembic migration for Vector(1024)
   - **Breaking change:** requires full re-embedding + dimension migration (1536 → 1024)

2. **Integrate Italian_NER_XXL_v2** for document ingestion
   - Extract entities during KB ingestion
   - Improve search metadata
   - File: `app/core/document_ingestion.py`

### Phase 2: Search Quality
3. **Add BGE-reranker-v2-m3** to hybrid search
   - Rerank top candidates before returning
   - 20-35% relevance improvement
   - File: `app/services/hybrid_search.py` (or similar)

### Phase 3: Cost Optimization
4. **Train intent classifier** on Italian BERT
   - Replace GPT routing calls
   - <10ms vs 500ms latency
   - File: `app/core/langgraph/nodes/step_034a__llm_router.py`

### Phase 4: Domain Specialization (Future)
5. **Fine-tune embeddings** on CCNL/labor law corpus
   - Improved domain retrieval
   - Competitive advantage

---

## 7. Cost-Benefit Analysis

| Model | One-time Cost | Ongoing Cost | Benefit |
|-------|---------------|--------------|---------|
| BGE-M3 embeddings | Dev time (3-5 days) + re-embedding window | $0 | Eliminate ~$18/year API cost, remove latency (200ms→50ms), GDPR compliance, reliability (no OpenAI dependency) |
| NER integration | Dev time (3-5 days) | $0 | Better KB quality, entity search |
| Reranker | Dev time (2-3 days) | $0 | 20-35% better search relevance |
| Intent classifier | Dev time (5-7 days) + training | $0 | Save GPT calls, faster routing |
| Fine-tuning BGE-M3 | $50-100 GPU rental (one-time) | $0 | +10-30% retrieval accuracy on Italian legal text |

**Break-even:** The dollar savings from OpenAI embeddings are minimal (~$18/year), but the real value is in **latency reduction**, **GDPR compliance**, **reliability**, and **domain-specific fine-tuning potential**.

---

## 8. Sources

### Embedding Models
- [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)
- [nomic-ai/nomic-embed-text-v2-moe](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe)
- [intfloat/e5-large-v2](https://huggingface.co/intfloat/e5-large-v2)
- [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Static Embeddings Blog](https://huggingface.co/blog/static-embeddings)

### API Embedding Providers
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Embed v4](https://cohere.com/embed)
- [Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings)
- [Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Mistral Embeddings](https://docs.mistral.ai/capabilities/embeddings/)

### Reranking Models
- [BAAI/bge-reranker-base](https://huggingface.co/BAAI/bge-reranker-base)
- [Ultimate Guide to Reranking 2025](https://www.zeroentropy.dev/articles/ultimate-guide-to-choosing-the-best-reranking-model-in-2025)
- [OpenAI Cookbook - Reranking](https://cookbook.openai.com/examples/search_reranking_with_cross-encoders)

### Italian NER Models
- [fabiod20/italian-legal-ner](https://huggingface.co/fabiod20/italian-legal-ner)
- [DeepMount00/Italian_NER_XXL_v2](https://huggingface.co/DeepMount00/Italian_NER_XXL_v2)
- [dlicari/Italian-Legal-BERT](https://huggingface.co/dlicari/Italian-Legal-BERT)

### Italian Base Models
- [dbmdz/bert-base-italian-cased](https://huggingface.co/dbmdz/bert-base-italian-cased)
- [neuraly/bert-base-italian-cased-sentiment](https://huggingface.co/neuraly/bert-base-italian-cased-sentiment)

---

## Summary Table: Top Picks for PratikoAI

| Category | Model | Why |
|----------|-------|-----|
| **Embeddings** | **BAAI/bge-m3** (updated March 2026) | Native Italian, 8K context, hybrid retrieval (dense+sparse+multi-vector), MIT license, aligns with ADR-002 |
| **Embeddings (alt)** | nomic-ai/nomic-embed-text-v2-moe | Smaller/faster than BGE-M3, Matryoshka dims, Apache 2.0 |
| **Reranking** | BAAI/bge-reranker-v2-m3 | Multilingual, 8K context, state-of-art |
| **NER** | DeepMount00/Italian_NER_XXL_v2 | 52 entities, legal/financial focus |
| **Legal NER** | fabiod20/italian-legal-ner | Trained on Italian court judgments |
| **Classification** | dbmdz/bert-base-italian-cased | Best Italian BERT for fine-tuning |
