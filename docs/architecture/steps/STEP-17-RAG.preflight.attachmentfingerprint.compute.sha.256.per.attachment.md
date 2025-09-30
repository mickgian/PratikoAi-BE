# RAG STEP 17 — AttachmentFingerprint.compute SHA-256 per attachment (RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment)

**Type:** process  
**Category:** preflight  
**Node ID:** `AttachmentFingerprint`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AttachmentFingerprint` (AttachmentFingerprint.compute SHA-256 per attachment).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/preflight.py:15` - `step_17__attachment_fingerprint()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator computing SHA-256 fingerprints for each attachment to enable secure caching and deduplication. Routes to Step 18 (QuerySig) for query signature computation.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing preflight validation infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 17 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/orchestrators/preflight.py:15 — app.orchestrators.preflight.step_17__attachment_fingerprint (score 0.28)
   Evidence: Score 0.28, RAG STEP 17 — AttachmentFingerprint.compute SHA-256 per attachment
ID: RAG.prefl...
2) app/models/query.py:193 — app.models.query.QueryMetrics.average_cost_per_query (score 0.25)
   Evidence: Score 0.25, Calculate average cost per query.
3) app/core/langgraph/tools/document_ingest_tool.py:91 — app.core.langgraph.tools.document_ingest_tool.DocumentIngestTool._validate_attachment (score 0.25)
   Evidence: Score 0.25, Validate a single attachment.

Args:
    attachment: Attachment data dictionary
...
4) app/services/database_encryption_service.py:425 — app.services.database_encryption_service.DatabaseEncryptionService._encrypt_aes_256_cbc (score 0.25)
   Evidence: Score 0.25, Encrypt using AES-256-CBC.
5) app/services/database_encryption_service.py:447 — app.services.database_encryption_service.DatabaseEncryptionService._decrypt_aes_256_cbc (score 0.25)
   Evidence: Score 0.25, Decrypt using AES-256-CBC.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AttachmentFingerprint
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->