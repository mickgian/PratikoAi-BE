# RAG STEP 95 — Extractor.extract Structured fields (RAG.facts.extractor.extract.structured.fields)

**Type:** process  
**Category:** facts  
**Node ID:** `ExtractDocFacts`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ExtractDocFacts` (Extractor.extract Structured fields).

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
  `RAG STEP 95 (RAG.facts.extractor.extract.structured.fields): Extractor.extract Structured fields | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.19

Top candidates:
1) deployment-orchestration/adaptive_deployment_engine.py:502 — deployment-orchestration.adaptive_deployment_engine.DeploymentMLOptimizer.extract_features (score 0.19)
   Evidence: Score 0.19, Extract feature vector from deployment context for ML prediction.

Features incl...
2) app/models/cassazione_data.py:180 — app.models.cassazione_data.LegalPrinciple._extract_keywords (score 0.19)
   Evidence: Score 0.19, Extract keywords from principle text.
3) app/services/italian_document_collector.py:451 — app.services.italian_document_collector.ItalianDocumentCollector._extract_keywords (score 0.19)
   Evidence: Score 0.19, Extract relevant keywords from document content.
4) app/services/legal_document_analyzer.py:826 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_debitore (score 0.19)
   Evidence: Score 0.19, Extract debtor from decreto ingiuntivo
5) app/services/scrapers/cassazione_scraper.py:550 — app.services.scrapers.cassazione_scraper.CassazioneScraper._extract_keywords (score 0.19)
   Evidence: Score 0.19, Extract keywords from decision content.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ExtractDocFacts
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->