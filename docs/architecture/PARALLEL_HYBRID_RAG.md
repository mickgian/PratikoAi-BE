# Parallel Hybrid RAG Architecture

**Status:** ✅ IMPLEMENTED
**Date:** January 17, 2026
**Ticket:** DEV-245

---

## Overview

PratikoAI uses a **Parallel Hybrid RAG** architecture that combines Knowledge Base (KB) retrieval with real-time web search in a single retrieval phase, enabling single-LLM synthesis with ~50% faster response times.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                       │
│                    "rottamazione quinquies imu"                          │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 39c: PARALLEL RETRIEVAL                          │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   BM25      │  │   Vector    │  │    HyDE     │  │  Authority  │     │
│  │  (0.30)     │  │   (0.35)    │  │   (0.25)    │  │   (0.10)    │     │
│  │             │  │             │  │             │  │             │     │
│  │ Full-text   │  │  Semantic   │  │ Hypothetical│  │  Official   │     │
│  │  search     │  │ similarity  │  │  doc embed  │  │  sources    │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │                │             │
│         │  ┌─────────────────────────────────────────────┐ │             │
│         │  │              BRAVE WEB SEARCH               │ │             │
│         │  │                  (0.15)                     │ │             │
│         │  │                                             │ │             │
│         │  │  • Real-time web results                    │ │             │
│         │  │  • AI summary (if available)                │ │             │
│         │  │  • Configurable via BRAVE_SEARCH_WEIGHT     │ │             │
│         │  └──────────────────────┬──────────────────────┘ │             │
│         │                         │                        │             │
│         └─────────┬───────────────┼────────────────────────┘             │
│                   │               │                                       │
│                   ▼               ▼                                       │
│         ┌─────────────────────────────────────────────┐                  │
│         │        RECIPROCAL RANK FUSION (RRF)         │                  │
│         │                                             │                  │
│         │  score = Σ(weight / (k + rank))             │                  │
│         │  k = 60 (RRF constant)                      │                  │
│         │                                             │                  │
│         │  Combines all 5 search types with weights   │                  │
│         └─────────────────────┬───────────────────────┘                  │
│                               │                                           │
└───────────────────────────────┼───────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 40: CONTEXT BUILDING                             │
│                                                                          │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │       KB DOCUMENTS          │  │        WEB DOCUMENTS            │   │
│  │                             │  │                                 │   │
│  │  • Gazzetta Ufficiale       │  │  • is_web_result: true          │   │
│  │  • Agenzia Entrate          │  │  • source: brave_web_search     │   │
│  │  • INPS, Cassazione         │  │  • AI synthesis (if available)  │   │
│  │                             │  │                                 │   │
│  │  Stored in: state.documents │  │  Stored in: state.web_documents │   │
│  └─────────────────────────────┘  └─────────────────────────────────┘   │
│                                                                          │
│  state.web_sources_metadata = [                                          │
│    {"title": "...", "url": "...", "snippet": "..."}                      │
│  ]                                                                       │
│                                                                          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 41/44: PROMPT INJECTION                          │
│                                                                          │
│  System Prompt + KB Context + Web Sources Section:                       │
│                                                                          │
│  ## Fonti Web Recenti (DEV-245: Parallel Hybrid RAG)                     │
│  Le seguenti fonti web sono state recuperate tramite Brave Search...     │
│  [{"title": "...", "url": "...", "snippet": "..."}]                      │
│                                                                          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 64: SINGLE LLM SYNTHESIS                         │
│                                                                          │
│  One LLM call synthesizes KB + Web context together                      │
│  • Uses [Fonte web] citation for web sources                             │
│  • Maintains KB authority for official legal citations                   │
│                                                                          │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FINAL RESPONSE                                   │
│                                                                          │
│  La rottamazione quinquies permette di definire i debiti IMU...          │
│  (Art. 1, comma 231, Legge 199/2025)                                     │
│                                                                          │
│  Nota: Alcuni comuni potrebbero richiedere accordi specifici.            │
│  [Fonte web: italia-informa.com]                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Search Weights

| Search Type | Weight | Description |
|-------------|--------|-------------|
| **bm25** | 0.30 | Full-text keyword search (BM25 algorithm) |
| **vector** | 0.35 | Semantic similarity (text-embedding-3-small) |
| **hyde** | 0.25 | Hypothetical Document Embedding |
| **authority** | 0.10 | Official source boost (Gazzetta, AE, INPS) |
| **brave** | 0.30* | Web search for recent/practical info |

*\* Configurable via `BRAVE_SEARCH_WEIGHT` environment variable*

---

## Configuration

### Environment Variables

```bash
# Brave Search API key (required for web search)
BRAVE_SEARCH_API_KEY=your_api_key_here

# Brave search weight (default: 0.30)
# Range: 0.0 (disabled) to 0.4 (max recommended)
BRAVE_SEARCH_WEIGHT=0.30

# Enable/disable web verification (default: true)
WEB_VERIFICATION_ENABLED=true
```

### Tuning Guidelines

| Scenario | Recommended Weight |
|----------|-------------------|
| **High KB authority** (legal/official queries) | 0.10 - 0.15 |
| **Current events** (news, recent changes) | 0.20 - 0.25 |
| **Disable web search** | 0.0 |

---

## Monitoring

### Log Events

The following structured log events are emitted for monitoring:

| Event | Description | Key Fields |
|-------|-------------|------------|
| `brave_parallel_search_starting` | Web search initiated | `query` |
| `brave_parallel_search_complete` | Web search finished | `results_count`, `latency_ms`, `has_ai_summary` |
| `brave_api_latency` | API response time | `latency_ms` |
| `parallel_searches_complete` | All searches done | `source_counts`, `brave_results`, `kb_results` |
| `DEV245_retrieval_docs_summary` | Final ranked results | `web_results_in_final`, `web_contribution_pct` |

### Docker Log Examples

```bash
# View all Brave-related logs
docker logs pratikoai-backend 2>&1 | grep -E "brave_|DEV245"

# Monitor API latency
docker logs pratikoai-backend 2>&1 | grep "brave_api_latency"

# Check web contribution to final results
docker logs pratikoai-backend 2>&1 | grep "web_contribution_pct"
```

### Key Metrics to Track

1. **Brave API Latency**: Target p95 < 500ms
2. **Web Result Contribution**: Typically 10-30% of final results
3. **AI Summary Rate**: Percentage of queries with Brave AI summary

---

## Files Modified

| File | Purpose |
|------|---------|
| `app/services/parallel_retrieval.py` | Core parallel retrieval with Brave search |
| `app/core/config.py` | `BRAVE_SEARCH_WEIGHT` configuration |
| `app/core/langgraph/types.py` | RAGState with `web_documents`, `web_sources_metadata` |
| `app/core/langgraph/nodes/step_040__build_context.py` | KB/web separation |
| `app/orchestrators/prompting.py` | Web sources injection |
| `app/services/web_verification.py` | Reuses existing web sources |

---

## Benefits

| Metric | Before (2 LLM calls) | After (1 LLM call) |
|--------|---------------------|-------------------|
| **LLM Calls** | 2 | 1 |
| **Response Time** | ~6-10s | ~3-5s |
| **API Cost** | Higher | ~50% lower |
| **Architecture** | Sequential | Parallel |

---

## Sources

- [RAG 2025 Definitive Guide](https://www.chitika.com/retrieval-augmented-generation-rag-the-definitive-guide-2025/)
- [Azure AI Search RAG](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- [Hybrid RAG Architecture](https://www.ai21.com/glossary/foundational-llm/hybrid-rag/)

---

**Last Updated:** January 17, 2026
**Maintained By:** PratikoAI Development Team
