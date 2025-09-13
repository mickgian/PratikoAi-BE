# RAG STEP 96 — BlobStore.put Encrypted TTL storage (RAG.docs.blobstore.put.encrypted.ttl.storage)

**Type:** process  
**Category:** docs  
**Node ID:** `StoreBlob`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StoreBlob` (BlobStore.put Encrypted TTL storage).

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
  `RAG STEP 96 (RAG.docs.blobstore.put.encrypted.ttl.storage): BlobStore.put Encrypted TTL storage | attrs={...}`
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
1) app/services/secure_document_storage.py:292 — app.services.secure_document_storage.SecureDocumentStorage._encrypt_content (score 0.28)
   Evidence: Score 0.28, Encrypt document content
2) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.28)
   Evidence: Score 0.28, Convert APIContract to OpenAPI specification.
3) app/services/secure_document_storage.py:300 — app.services.secure_document_storage.SecureDocumentStorage._decrypt_content (score 0.27)
   Evidence: Score 0.27, Decrypt document content
4) app/models/document.py:118 — app.models.document.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired
5) app/models/document.py:134 — app.models.document.Document.to_dict (score 0.27)
   Evidence: Score 0.27, Convert document to dictionary

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for StoreBlob
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->