# Hugging Face Models for PratikoAI - Analysis Report

> **Date:** January 2026
> **Purpose:** Evaluate small, CPU-efficient Hugging Face models for PratikoAI's Italian legal/labor domain

## Executive Summary

This report analyzes small, CPU-efficient Hugging Face models suitable for PratikoAI's Italian legal/labor domain. Focus areas: embeddings, reranking, NER, and classification.

**Key Recommendation:** Start with embedding models (immediate cost savings) + Italian NER (domain value), then add reranking for search quality.

---

## 1. Embedding Models (Replace OpenAI Embeddings)

### 1.1 all-MiniLM-L6-v2 (Recommended for Start)

| Attribute | Value |
|-----------|-------|
| **Size** | 90MB |
| **Dimensions** | 384 |
| **Max Tokens** | 256 |
| **Inference** | 5-15ms CPU |
| **License** | Apache 2.0 |

**Pros:**
- Already in your codebase (`local_provider.py`)
- Extremely fast on CPU
- Well-tested, stable, huge community
- Zero cost at scale

**Cons:**
- English-optimized (works for Italian but not ideal)
- 384 dimensions vs OpenAI's 1536 (less expressive)
- 256 token limit (need chunking strategy)

**Source:** [HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

---

### 1.2 BAAI/bge-small-en-v1.5

| Attribute | Value |
|-----------|-------|
| **Size** | 130MB |
| **Dimensions** | 384 |
| **Max Tokens** | 512 |
| **Inference** | 10-20ms CPU |
| **License** | MIT |

**Pros:**
- Better quality than MiniLM on MTEB benchmarks
- 512 token context (2x MiniLM)
- Excellent for retrieval tasks

**Cons:**
- English-focused
- Slightly larger/slower than MiniLM

**Source:** [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

---

### 1.3 intfloat/multilingual-e5-small

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
- 5x larger than MiniLM
- Slower inference
- Requires prefix: "query: " or "passage: "

**Best for PratikoAI:** Yes - native Italian support critical for legal/CCNL documents.

---

### 1.4 Model2Vec Static Embeddings (Fastest Option)

| Attribute | Value |
|-----------|-------|
| **Size** | ~30MB |
| **Inference** | <1ms CPU |
| **License** | Apache 2.0 |

**Pros:**
- **400x faster** than transformer models
- Dictionary lookup, no neural network
- Perfect for high-throughput scenarios

**Cons:**
- Lower quality than transformer embeddings
- No contextual understanding
- Best as pre-filter, not primary embedder

**Source:** [HuggingFace Blog](https://huggingface.co/blog/static-embeddings)

---

### Embedding Models Comparison

| Model | Size | Italian | Speed | Quality | Recommendation |
|-------|------|---------|-------|---------|----------------|
| all-MiniLM-L6-v2 | 90MB | Fair | Fast | Good | Dev/Testing |
| bge-small-en-v1.5 | 130MB | Fair | Fast | Very Good | English content |
| **multilingual-e5-small** | 470MB | **Native** | Medium | Very Good | **Production** |
| Model2Vec | 30MB | Varies | Fastest | Fair | Pre-filtering |

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
1. **Add multilingual-e5-small** as embedding option
   - Immediate cost reduction
   - Better Italian support
   - File: `app/services/vector_providers/local_provider.py`

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
| Local embeddings | Dev time (2-3 days) | $0 | Save ~$50-200/month on OpenAI |
| NER integration | Dev time (3-5 days) | $0 | Better KB quality, entity search |
| Reranker | Dev time (2-3 days) | $0 | 20-35% better search relevance |
| Intent classifier | Dev time (5-7 days) + training | $0 | Save GPT calls, faster routing |

**Break-even:** Most integrations pay for themselves within 1-2 months of reduced API costs.

---

## 8. Sources

### Embedding Models
- [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Static Embeddings Blog](https://huggingface.co/blog/static-embeddings)

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
| **Embeddings** | intfloat/multilingual-e5-small | Native Italian, good quality/size ratio |
| **Reranking** | BAAI/bge-reranker-v2-m3 | Multilingual, 8K context, state-of-art |
| **NER** | DeepMount00/Italian_NER_XXL_v2 | 52 entities, legal/financial focus |
| **Legal NER** | fabiod20/italian-legal-ner | Trained on Italian court judgments |
| **Classification** | dbmdz/bert-base-italian-cased | Best Italian BERT for fine-tuning |
