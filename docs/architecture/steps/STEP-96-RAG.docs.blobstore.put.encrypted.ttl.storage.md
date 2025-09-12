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
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/core/encryption/encrypted_types.py:40 — app.core.encryption.encrypted_types.EncryptedType.__init__ (score 0.25)
   Evidence: Score 0.25, Initialize encrypted type.

Args:
    impl_type: Underlying SQLAlchemy type (Str...
2) app/core/encryption/encrypted_types.py:63 — app.core.encryption.encrypted_types.EncryptedType.load_dialect_impl (score 0.25)
   Evidence: Score 0.25, Load dialect-specific implementation.
3) app/core/encryption/encrypted_types.py:67 — app.core.encryption.encrypted_types.EncryptedType.process_bind_param (score 0.25)
   Evidence: Score 0.25, Encrypt value when binding to database parameter.

Called when saving data to da...
4) app/core/encryption/encrypted_types.py:96 — app.core.encryption.encrypted_types.EncryptedType.process_result_value (score 0.25)
   Evidence: Score 0.25, Decrypt value when loading from database result.

Called when loading data from ...
5) app/core/encryption/encrypted_types.py:124 — app.core.encryption.encrypted_types.EncryptedType._get_encryption_service (score 0.25)
   Evidence: Score 0.25, Get or create encryption service instance.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for StoreBlob
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->