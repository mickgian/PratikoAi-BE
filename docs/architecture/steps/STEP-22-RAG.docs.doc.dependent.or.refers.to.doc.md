# RAG STEP 22 — Doc-dependent or refers to doc? (RAG.docs.doc.dependent.or.refers.to.doc)

**Type:** process  
**Category:** docs  
**Node ID:** `DocDependent`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocDependent` (Doc-dependent or refers to doc?).

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
  `RAG STEP 22 (RAG.docs.doc.dependent.or.refers.to.doc): Doc-dependent or refers to doc? | attrs={...}`
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
1) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.23)
   Evidence: Score 0.23, Check if document has expired
2) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.23)
   Evidence: Score 0.23, Convert document to dictionary for API responses
3) app/services/secure_document_storage.py:300 — app.services.secure_document_storage.SecureDocumentStorage._decrypt_content (score 0.22)
   Evidence: Score 0.22, Decrypt document content
4) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.22)
   Evidence: Score 0.22, Extract contract price
5) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.22)
   Evidence: Score 0.22, Extract contract object/purpose

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocDependent
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->