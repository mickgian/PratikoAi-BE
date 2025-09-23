# RAG STEP 134 — Extract text and metadata (RAG.docs.extract.text.and.metadata)

**Type:** process  
**Category:** docs  
**Node ID:** `ParseDocs`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ParseDocs` (Extract text and metadata).

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
  `RAG STEP 134 (RAG.docs.extract.text.and.metadata): Extract text and metadata | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) app/orchestrators/docs.py:1111 — app.orchestrators.docs.step_134__parse_docs (score 0.31)
   Evidence: Score 0.31, RAG STEP 134 — Extract text and metadata
ID: RAG.docs.extract.text.and.metadata
...
2) app/services/document_processor.py:541 — app.services.document_processor.DocumentProcessor._extract_content_metadata (score 0.31)
   Evidence: Score 0.31, Extract metadata from document content.

Args:
    content: Extracted text conte...
3) app/services/legal_document_analyzer.py:883 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_parties (score 0.31)
   Evidence: Score 0.31, Extract parties from contract
4) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.31)
   Evidence: Score 0.31, Extract contract object/purpose
5) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.31)
   Evidence: Score 0.31, Extract contract price

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->