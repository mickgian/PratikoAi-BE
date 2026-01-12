# ADR-022: LLM-Based Document Identification for Colloquial Query Resolution

## Status
Accepted

## Date
2026-01-09

## Context

Italian legal queries often use colloquial terms (e.g., "rottamazione quinquies") that refer to specific
normative documents (e.g., "Legge 199/2025"). Users expect PratikoAI to understand these mappings
just as a human tax professional would.

The previous approach used static mappings in `_build_colloquial_mappings()` that:
- Required manual maintenance for each new term
- Could not handle variations or unknown terms
- Mapped to search keywords, not actual document references
- Did not enable filtering to specific documents

Example of the problem:
- User asks: "Parlami della rottamazione quinquies"
- System found generic content but couldn't identify it refers to Legge 199/2025
- LLM hallucinated dates and references instead of citing actual law content

## Decision

Use LLM-based document identification within the existing Multi-Query Generator (Step 36) to:

1. **Extract `document_references`** from user queries alongside existing query variants
2. **Filter BM25 search results** by document title when references are identified
3. **Fall back to regular search** if filtered search returns no results

This approach leverages the existing LLM call, adding no extra latency or cost.

### Technical Implementation

```
User: "Parlami della rottamazione quinquies"
           ↓
Step 36: Multi-Query Generator (ENHANCED)
           ↓
LLM outputs:
{
    "bm25_query": "rottamazione quinquies definizione agevolata legge",
    "vector_query": "Quali sono le disposizioni sulla rottamazione...",
    "entity_query": "Legge 199/2025 Art. 1 definizione agevolata",
    "document_references": [                    ← NEW!
        "Legge 199/2025",
        "LEGGE 30 dicembre 2025, n. 199",
        "Legge di Bilancio 2026"
    ]
}
           ↓
Step 39c: Parallel Retrieval (ENHANCED)
           ↓
If document_references exist:
    → Search with title filter (priority)
    → Fallback to regular search if no results
```

### Changes Required

| Component | Change |
|-----------|--------|
| `QueryVariants` dataclass | Add `document_references: list[str] \| None` field |
| Multi-Query Generator prompt | Add instructions for extracting document references |
| `SearchService` | Add `search_with_title_filter()` method |
| `ParallelRetrievalService` | Use document filtering with fallback |

## Consequences

### Positive

- **Handles ANY colloquial term**, including future ones
- **No manual mapping maintenance** required
- **Accurate document filtering** improves response quality
- **LLM understands Italian legal terminology** in context
- **No extra LLM call** - reuses existing multi-query generation
- **Graceful fallback** - regular search if filter finds nothing

### Negative

- LLM quality affects document identification accuracy
- May occasionally identify wrong documents (mitigated by fallback)
- Slightly larger prompt in multi-query generator

## Supersedes

This ADR supersedes the static colloquial mapping approach implemented in:
- `_build_colloquial_mappings()` in `query_expansion_service.py`
- `expand_colloquial_sync()` in `query_expansion_service.py`
- Colloquial expansion in `search_service.py:normalize_italian_query()`

These code sections are removed as part of this implementation.

## Related

- **ADR-018**: Normative Matching Engine (complements this approach)
- **ADR-002**: Hybrid Search Architecture (this enhances the search pipeline)
- **GitHub Issue**: #975 - Response Quality & Suggested Actions Fixes
- **JIRA**: DEV-242

## References

- [Retrieval-Augmented Generation Best Practices](https://arxiv.org/abs/2312.10997)
- [Query Understanding for Search](https://research.google/pubs/pub48175/)
