# Golden Set Performance Optimization - Usage Examples

This document provides practical examples of using the optimized Expert FAQ Retrieval Service.

## Basic Usage

### Simple Query

```python
from app.services.expert_faq_retrieval_service_optimized import ExpertFAQRetrievalServiceOptimized

async def find_faqs_for_query(query: str):
    """Find matching FAQs for a user query."""
    async with get_db_session() as db:
        service = ExpertFAQRetrievalServiceOptimized(db)

        faqs = await service.find_matching_faqs(
            query=query,
            min_similarity=0.85,
            max_results=10
        )

        return faqs
```

See full documentation in `/PHASE_2_3_PERFORMANCE_OPTIMIZATION_SUMMARY.md`
