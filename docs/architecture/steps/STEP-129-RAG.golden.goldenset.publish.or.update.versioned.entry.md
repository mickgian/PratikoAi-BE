# RAG STEP 129 — GoldenSet.publish_or_update versioned entry (RAG.golden.goldenset.publish.or.update.versioned.entry)

**Type:** process
**Category:** golden
**Node ID:** `PublishGolden`

## Intent (Blueprint)
Publishes or updates an approved FAQ entry in the Golden Set database with versioning. When a candidate is approved (from Step 128), this step persists it to the database, either creating a new FAQ entry or updating an existing one with version history. Routes to InvalidateFAQCache (Step 130) and VectorReindex (Step 131) for downstream cache invalidation and vector embedding updates. This step is derived from the Mermaid node: `PublishGolden` (GoldenSet.publish_or_update versioned entry).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_129__publish_golden`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that publishes/updates FAQ entries with versioning. Uses intelligent_faq_service.create_faq_entry for new entries or update_faq_entry for updates. Creates version history for updates. Routes to 'invalidate_faq_cache' (Step 130) for cache invalidation. Preserves regulatory references and all metadata.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing service behavior

## TDD Task List
- [x] Unit tests (create new entry, update existing, preserve regulatory refs, context preservation, publication metadata, cache invalidation routing, error handling, logging)
- [x] Parity tests (FAQ creation/update behavior verification)
- [x] Integration tests (GoldenApproval→PublishGolden→InvalidateFAQCache flow, data preparation for cache invalidation)
- [x] Implementation changes (async orchestrator wrapping intelligent_faq_service)
- [x] Observability: add structured log line
  `RAG STEP 129 (RAG.golden.goldenset.publish.or.update.versioned.entry): GoldenSet.publish_or_update versioned entry | attrs={faq_id, operation, version, category, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing service)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🟡  |  Confidence: 0.57

Top candidates:
1) app/api/v1/faq_automation.py:460 — app.api.v1.faq_automation.publish_faq (score 0.57)
   Evidence: Score 0.57, Publish an approved FAQ to make it available to users
2) app/api/v1/faq_automation.py:418 — app.api.v1.faq_automation.approve_faq (score 0.54)
   Evidence: Score 0.54, Approve, reject, or request revision for a generated FAQ
3) app/api/v1/faq.py:431 — app.api.v1.faq.update_faq (score 0.53)
   Evidence: Score 0.53, Update an existing FAQ entry with versioning.

Requires admin privileges.
4) app/orchestrators/golden.py:690 — app.orchestrators.golden.step_117__faqfeedback (score 0.51)
   Evidence: Score 0.51, RAG STEP 117 — POST /api/v1/faq/feedback.

ID: RAG.golden.post.api.v1.faq.feedba...
5) app/api/v1/faq.py:130 — app.api.v1.faq.query_faq (score 0.49)
   Evidence: Score 0.49, Query the FAQ system with semantic search and response variation.

This endpoint...

Notes:
- Partial implementation identified

Suggested next TDD actions:
- Complete partial implementation
- Add missing error handling
- Expand test coverage
- Add performance benchmarks if needed
<!-- AUTO-AUDIT:END -->