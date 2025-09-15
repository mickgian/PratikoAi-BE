# RAG STEP 86 — Return tool error Invalid file (RAG.platform.return.tool.error.invalid.file)

**Type:** error  
**Category:** platform  
**Node ID:** `ToolErr`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToolErr` (Return tool error Invalid file).

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
  `RAG STEP 86 (RAG.platform.return.tool.error.invalid.file): Return tool error Invalid file | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.14

Top candidates:
1) app/core/langgraph/tools/__init__.py:1 — app.core.langgraph.tools.__init__ (score 0.14)
   Evidence: Score 0.14, LangGraph tools for enhanced language model capabilities.

This package contains...
2) app/core/langgraph/tools/duckduckgo_search.py:1 — app.core.langgraph.tools.duckduckgo_search (score 0.14)
   Evidence: Score 0.14, DuckDuckGo search tool for LangGraph.

This module provides a DuckDuckGo search ...
3) app/services/location_service.py:17 — app.services.location_service.InvalidCAP (score 0.13)
   Evidence: Score 0.13, Raised when CAP format is invalid
4) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.13)
   Evidence: Score 0.13, Validate the citation.
5) app/models/cassazione_data.py:279 — app.models.cassazione_data.ScrapingResult.is_valid (score 0.13)
   Evidence: Score 0.13, Validate the result.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create error implementation for ToolErr
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->