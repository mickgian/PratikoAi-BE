# RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR (RAG.docs.f24parser.parse.ocr.layout.aware.ocr)

**Type:** process  
**Category:** docs  
**Node ID:** `F24Parser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `F24Parser` (F24Parser.parse_ocr Layout aware OCR).

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
  `RAG STEP 91 (RAG.docs.f24parser.parse.ocr.layout.aware.ocr): F24Parser.parse_ocr Layout aware OCR | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.24

Top candidates:
1) app/core/langgraph/tools/ccnl_tool.py:535 — app.core.langgraph.tools.ccnl_tool.CCNLTool._parse_sector (score 0.24)
   Evidence: Score 0.24, Parse sector string to enum.
2) app/services/ccnl_search_service.py:206 — app.services.ccnl_search_service.NaturalLanguageProcessor.parse_query (score 0.23)
   Evidence: Score 0.23, Parse natural language query into search filters.
3) app/services/scrapers/cassazione_scheduler.py:24 — app.services.scrapers.cassazione_scheduler.MockSchedulerService.pause_job (score 0.23)
   Evidence: Score 0.23, method: pause_job
4) app/services/scrapers/cassazione_scheduler.py:295 — app.services.scrapers.cassazione_scheduler.CassazioneScheduler.pause_job (score 0.23)
   Evidence: Score 0.23, Pause a scheduled job.

Args:
    job_id: ID of job to pause
    
Returns:
    T...
5) version-management/core/version_schema.py:334 — version-management.core.version_schema.VersioningScheme.parse_version (score 0.23)
   Evidence: Score 0.23, Parse a version string and extract components.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for F24Parser
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->