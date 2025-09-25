# RAG STEP 60 — EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version (RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version)

**Type:** process  
**Category:** golden  
**Node ID:** `ResolveEpochs`

## Intent (Blueprint)
Resolves version epochs from various data sources (KB, Golden Set, CCNL, parsers) to enable cache invalidation based on data freshness. These epochs are used by Step 61 (GenHash) for cache key generation, ensuring cached responses are invalidated when underlying data changes.

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/golden.py:step_60__resolve_epochs`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that extracts epoch timestamps from context (kb_last_updated, golden_last_updated, ccnl_last_updated, parser_version). Creates epoch resolution metadata tracking which epochs were resolved. Routes to Step 61 (GenHash) with resolved epochs for cache key generation.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - simple epoch extraction with graceful handling of missing values

## TDD Task List
- [x] Unit tests (resolve all epochs, missing epochs, defaults, context preservation, logging, metadata, timestamp conversion)
- [x] Parity tests (epoch resolution behavior verification)
- [x] Integration tests (Step 59→60→61 flow, prepare for GenHash)
- [x] Implementation changes (async orchestrator with epoch extraction)
- [x] Observability: add structured log line
  `RAG STEP 60 (RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version): EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version | attrs={epochs_resolved, kb_epoch, golden_epoch, ccnl_epoch, parser_version, next_step}`
- [x] Feature flag / config if needed (none required - extracts from context)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.53

Top candidates:
1) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.53)
   Evidence: Score 0.53, Approve, reject, or request revision for a generated FAQ
2) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.53)
   Evidence: Score 0.53, Publish an approved FAQ to make it available to users
3) app/orchestrators/golden.py:534 — app.orchestrators.golden.step_117__faqfeedback (score 0.50)
   Evidence: Score 0.50, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
4) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.48)
   Evidence: Score 0.48, Query the FAQ system with semantic search and response variation.

This endpoint...
5) app/api/v1/faq.py:385 — app.api.v1.faq.create_faq (score 0.48)
   Evidence: Score 0.48, Create a new FAQ entry.

Requires admin privileges.

Notes:
- Implementation exists but may not be wired correctly

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->