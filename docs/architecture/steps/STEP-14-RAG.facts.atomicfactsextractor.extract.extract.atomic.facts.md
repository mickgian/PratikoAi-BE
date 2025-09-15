# RAG STEP 14 — AtomicFactsExtractor.extract Extract atomic facts (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractFacts` (AtomicFactsExtractor.extract Extract atomic facts).

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
  `RAG STEP 14 (RAG.facts.atomicfactsextractor.extract.extract.atomic.facts): AtomicFactsExtractor.extract Extract atomic facts | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.20

Top candidates:
1) deployment-orchestration/adaptive_deployment_engine.py:502 — deployment-orchestration.adaptive_deployment_engine.DeploymentMLOptimizer.extract_features (score 0.20)
   Evidence: Score 0.20, Extract feature vector from deployment context for ML prediction.

Features incl...
2) app/services/legal_document_analyzer.py:459 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_parties (score 0.19)
   Evidence: Score 0.19, Extract plaintiff and defendant from legal text
3) app/services/italian_document_collector.py:440 — app.services.italian_document_collector.ItalianDocumentCollector._extract_tax_types (score 0.18)
   Evidence: Score 0.18, Extract relevant tax types from document content.
4) app/services/scrapers/cassazione_scraper.py:532 — app.services.scrapers.cassazione_scraper.CassazioneScraper._extract_law_citations (score 0.18)
   Evidence: Score 0.18, Extract citations to laws from HTML.
5) app/services/legal_document_analyzer.py:583 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_exceptions (score 0.18)
   Evidence: Score 0.18, Extract legal exceptions raised

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ExtractFacts
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->