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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.30)
   Evidence: Score 0.30, Check if document has expired
2) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.30)
   Evidence: Score 0.30, Convert document to dictionary for API responses
3) app/models/document_simple.py:126 — app.models.document_simple.Document.__init__ (score 0.27)
   Evidence: Score 0.27, method: __init__
4) app/models/document_simple.py:77 — app.models.document_simple.Document (score 0.25)
   Evidence: Score 0.25, Document model with GDPR compliance fields
5) app/services/document_uploader.py:189 — app.services.document_uploader.DocumentUploader._validate_file_signature (score 0.24)
   Evidence: Score 0.24, Validate file content matches expected file type signatures.

Args:
  content: F...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for DocType
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->