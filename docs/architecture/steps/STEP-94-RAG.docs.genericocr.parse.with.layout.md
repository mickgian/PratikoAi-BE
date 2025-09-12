# RAG STEP 94 — GenericOCR.parse_with_layout (RAG.docs.genericocr.parse.with.layout)

**Type:** process  
**Category:** docs  
**Node ID:** `GenericOCR`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `GenericOCR` (GenericOCR.parse_with_layout).

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
  `RAG STEP 94 (RAG.docs.genericocr.parse.with.layout): GenericOCR.parse_with_layout | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.23

Top candidates:
1) app/services/legal_document_analyzer.py:450 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._parse_italian_amount (score 0.23)
   Evidence: Score 0.23, Parse Italian currency format to float
2) app/models/subscription.py:127 — app.models.subscription.SubscriptionPlan.price_with_iva (score 0.23)
   Evidence: Score 0.23, Total price including 22% IVA
3) app/services/legal_document_analyzer.py:435 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._parse_italian_date (score 0.22)
   Evidence: Score 0.22, Parse Italian date formats to ISO format
4) app/services/scrapers/cassazione_scraper.py:607 — app.services.scrapers.cassazione_scraper.CassazioneScraper._parse_italian_date (score 0.22)
   Evidence: Score 0.22, Parse Italian date string.
5) app/services/ccnl_update_processor.py:207 — app.services.ccnl_update_processor.CCNLUpdateProcessor._parse_html_document (score 0.22)
   Evidence: Score 0.22, Parse HTML document content.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for GenericOCR
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->