# RAG STEP 129 — GoldenSet.publish_or_update versioned entry (RAG.golden.goldenset.publish.or.update.versioned.entry)

**Type:** process
**Category:** golden
**Node ID:** `PublishGolden`

## Intent (Blueprint)
Publishes or updates an approved FAQ entry in the Golden Set database with versioning. When a candidate is approved (from Step 128), this step persists it to the database, either creating a new FAQ entry or updating an existing one with version history. Routes to InvalidateFAQCache (Step 130) and VectorReindex (Step 131) for downstream cache invalidation and vector embedding updates. This step is derived from the Mermaid node: `PublishGolden` (GoldenSet.publish_or_update versioned entry).

## Current Implementation (Repo)
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
Status: ✅  |  Confidence: 1.00

Implementation:
- app/orchestrators/golden.py:852 — step_129__publish_golden (async orchestrator)
- tests/test_rag_step_129_publish_golden.py — 11 comprehensive tests (all passing)

Key Features:
- Async orchestrator publishing/updating FAQ entries with versioning
- Create new FAQ entry via intelligent_faq_service.create_faq_entry
- Update existing FAQ entry via intelligent_faq_service.update_faq_entry
- Automatic version history creation for updates
- Structured logging with rag_step_log (step 129, processing stages)
- Context preservation (expert_id, trust_score, user/session data)
- Publication metadata tracking (published_at, faq_id, operation, version)
- Regulatory references preservation
- Error handling with graceful degradation
- Routes to 'invalidate_faq_cache' (Step 130) per Mermaid flow

Test Coverage:
- Unit: create new entry, update existing, preserve regulatory refs, context preservation, publication metadata, cache invalidation routing, error handling, logging
- Parity: FAQ creation/update behavior verification
- Integration: GoldenApproval→PublishGolden→InvalidateFAQCache flow

Operations:
- New FAQ: calls create_faq_entry → operation='created'
- Update FAQ: calls update_faq_entry with version history → operation='updated'
- Error: sets error in published_faq → operation='error'

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (no business logic)
- All TDD tasks completed
<!-- AUTO-AUDIT:END -->