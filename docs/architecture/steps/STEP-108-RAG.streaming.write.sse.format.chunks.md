# RAG STEP 108 — write_sse Format chunks (RAG.streaming.write.sse.format.chunks)

**Type:** process  
**Category:** streaming  
**Node ID:** `WriteSSE`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `WriteSSE` (write_sse Format chunks).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ❓ Pending review (✅ Implemented / 🟡 Partial / ❌ Missing / 🔌 Not wired)
- **Behavior notes:** _TBD_

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [ ] Unit tests (list specific cases)
- [ ] Integration tests (list cases)
- [ ] Implementation changes (bullets)
- [ ] Observability: add structured log line  
  `RAG STEP 108 (RAG.streaming.write.sse.format.chunks): write_sse Format chunks | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.33

Top candidates:
1) app/core/sse_write.py:15 — app.core.sse_write.write_sse (score 0.33)
   Evidence: Score 0.33, Log an SSE frame that will be written to the response.

Args:
    response: The ...
2) app/services/i18n_service.py:322 — app.services.i18n_service.I18nService.format_date (score 0.25)
   Evidence: Score 0.25, Format date according to language preferences.
3) app/models/cassazione_data.py:345 — app.models.cassazione_data.ScrapingStatistics.reset (score 0.23)
   Evidence: Score 0.23, Reset all statistics.
4) load_testing/locust_tests.py:64 — load_testing.locust_tests.PratikoAIUser._register_user (score 0.23)
   Evidence: Score 0.23, Register a new test user
5) app/core/performance/cdn_integration.py:69 — app.core.performance.cdn_integration.CDNManager.__init__ (score 0.23)
   Evidence: Score 0.23, Initialize CDN manager.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->