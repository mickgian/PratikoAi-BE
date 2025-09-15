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
Status: ❌  |  Confidence: 0.23

Top candidates:
1) app/services/secure_document_storage.py:292 — app.services.secure_document_storage.SecureDocumentStorage._encrypt_content (score 0.23)
   Evidence: Score 0.23, Encrypt document content
2) app/services/secure_document_storage.py:300 — app.services.secure_document_storage.SecureDocumentStorage._decrypt_content (score 0.22)
   Evidence: Score 0.22, Decrypt document content
3) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.22)
   Evidence: Score 0.22, Check if document has expired
4) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.22)
   Evidence: Score 0.22, Convert document to dictionary for API responses
5) app/services/document_uploader.py:639 — app.services.document_uploader.DocumentUploader.get_storage_filename (score 0.22)
   Evidence: Score 0.22, Generate secure storage filename using document ID.

Args:
  document_id: Unique...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for StoreBlob
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->