# RAG STEP 87 — DocSanitizer.sanitize Strip macros and JS (RAG.docs.docsanitizer.sanitize.strip.macros.and.js)

**Type:** process  
**Category:** docs  
**Node ID:** `DocSecurity`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocSecurity` (DocSanitizer.sanitize Strip macros and JS).

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
  `RAG STEP 87 (RAG.docs.docsanitizer.sanitize.strip.macros.and.js): DocSanitizer.sanitize Strip macros and JS | attrs={...}`
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
1) app/services/document_uploader.py:351 — app.services.document_uploader.DocumentUploader._document_security_scan (score 0.23)
   Evidence: Score 0.23, Document-specific security scanning
2) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.22)
   Evidence: Score 0.22, Check if document has expired
3) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.22)
   Evidence: Score 0.22, Convert document to dictionary for API responses
4) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.22)
   Evidence: Score 0.22, Extract contract price
5) app/models/regulatory_documents.py:310 — app.models.regulatory_documents.create_document_id (score 0.22)
   Evidence: Score 0.22, Create standardized document ID.

Args:
    source: Source authority
    documen...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocSecurity
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->