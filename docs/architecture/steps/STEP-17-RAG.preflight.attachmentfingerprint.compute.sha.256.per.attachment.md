# RAG STEP 17 — AttachmentFingerprint.compute SHA-256 per attachment (RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment)

**Type:** process  
**Category:** preflight  
**Node ID:** `AttachmentFingerprint`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `AttachmentFingerprint` (AttachmentFingerprint.compute SHA-256 per attachment).

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
  `RAG STEP 17 (RAG.preflight.attachmentfingerprint.compute.sha.256.per.attachment): AttachmentFingerprint.compute SHA-256 per attachment | attrs={...}`
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