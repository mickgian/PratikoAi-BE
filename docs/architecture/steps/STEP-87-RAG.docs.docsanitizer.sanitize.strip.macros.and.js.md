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
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/services/document_uploader.py:351 — app.services.document_uploader.DocumentUploader._document_security_scan (score 0.28)
   Evidence: Score 0.28, Document-specific security scanning
2) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.28)
   Evidence: Score 0.28, Convert APIContract to OpenAPI specification.
3) app/models/document.py:118 — app.models.document.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired
4) app/models/document.py:134 — app.models.document.Document.to_dict (score 0.27)
   Evidence: Score 0.27, Convert document to dictionary
5) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocSecurity
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->