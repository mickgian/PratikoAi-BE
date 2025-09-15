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
Status: ❌  |  Confidence: 0.25

Top candidates:
1) app/models/query.py:193 — app.models.query.QueryMetrics.average_cost_per_query (score 0.25)
   Evidence: Score 0.25, Calculate average cost per query.
2) app/services/database_encryption_service.py:425 — app.services.database_encryption_service.DatabaseEncryptionService._encrypt_aes_256_cbc (score 0.25)
   Evidence: Score 0.25, Encrypt using AES-256-CBC.
3) app/services/database_encryption_service.py:447 — app.services.database_encryption_service.DatabaseEncryptionService._decrypt_aes_256_cbc (score 0.25)
   Evidence: Score 0.25, Decrypt using AES-256-CBC.
4) app/api/v1/regional_taxes.py:87 — app.api.v1.regional_taxes.CompleteTaxCalculationRequest.validate_business_type (score 0.20)
   Evidence: Score 0.20, method: validate_business_type
5) app/services/validators/italian_tax_calculator.py:334 — app.services.validators.italian_tax_calculator.ItalianTaxCalculator.calculate_complete_individual_taxes (score 0.20)
   Evidence: Score 0.20, Calculate complete individual tax burden.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AttachmentFingerprint
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->