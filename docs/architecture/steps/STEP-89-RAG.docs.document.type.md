# RAG STEP 89 — Document type? (RAG.docs.document.type)

**Type:** decision  
**Category:** docs  
**Node ID:** `DocType`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocType` (Document type?).

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
  `RAG STEP 89 (RAG.docs.document.type): Document type? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

Top candidates:
1) app/services/document_processor.py:501 — app.services.document_processor.DocumentProcessor._determine_document_type (score 0.32)
   Evidence: Score 0.32, Determine document type from URL.

Args:
    document_url: Document URL
    
Ret...
2) app/services/legal_document_analyzer.py:883 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_parties (score 0.31)
   Evidence: Score 0.31, Extract parties from contract
3) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.31)
   Evidence: Score 0.31, Extract contract object/purpose
4) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.31)
   Evidence: Score 0.31, Extract contract price
5) app/services/legal_document_analyzer.py:933 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_duration (score 0.31)
   Evidence: Score 0.31, Extract contract duration

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->