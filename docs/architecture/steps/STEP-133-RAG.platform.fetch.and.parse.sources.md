# RAG STEP 133 — Fetch and parse sources (RAG.platform.fetch.and.parse.sources)

**Type:** process  
**Category:** platform  
**Node ID:** `FetchFeeds`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FetchFeeds` (Fetch and parse sources).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/platform.py:3326` - `step_133__fetch_feeds()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator fetching and parsing RSS feeds and external content sources. Retrieves latest updates from configured sources for knowledge base ingestion. Routes to Step 134 (ParseDocs) for document processing.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 133 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.37

Top candidates:
1) app/orchestrators/platform.py:3421 — app.orchestrators.platform._fetch_and_parse_feeds (score 0.37)
   Evidence: Score 0.37, Helper function to fetch and parse RSS feeds.

Args:
    rss_feeds: List of RSS ...
2) app/orchestrators/platform.py:3326 — app.orchestrators.platform.step_133__fetch_feeds (score 0.28)
   Evidence: Score 0.28, RAG STEP 133 — Fetch and parse sources
ID: RAG.platform.fetch.and.parse.sources
...
3) evals/evaluator.py:182 — evals.evaluator.Evaluator.__fetch_traces (score 0.26)
   Evidence: Score 0.26, Fetch traces from the past 24 hours without scores.

Returns:
    List of traces...
4) test_rss_feeds.py:101 — test_rss_feeds.main (score 0.26)
   Evidence: Score 0.26, Main testing function.
5) app/api/v1/regulatory.py:544 — app.api.v1.regulatory.get_regulatory_sources (score 0.26)
   Evidence: Score 0.26, Get list of available regulatory sources and statistics.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->