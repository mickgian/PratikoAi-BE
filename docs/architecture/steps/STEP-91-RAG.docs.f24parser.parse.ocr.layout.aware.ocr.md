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
Status: ❌  |  Confidence: 0.28

Top candidates:
1) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.28)
   Evidence: Score 0.28, Convert APIContract to OpenAPI specification.
2) app/models/document.py:118 — app.models.document.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired
3) app/models/document.py:134 — app.models.document.Document.to_dict (score 0.27)
   Evidence: Score 0.27, Convert document to dictionary
4) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired
5) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.27)
   Evidence: Score 0.27, Convert document to dictionary for API responses

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for F24Parser
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->