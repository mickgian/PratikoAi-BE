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
Status: ❌  |  Confidence: 0.24

Top candidates:
1) app/models/regional_taxes.py:134 — app.models.regional_taxes.Comune.__repr__ (score 0.24)
   Evidence: Score 0.24, method: __repr__
2) app/models/regional_taxes.py:137 — app.models.regional_taxes.Comune.get_primary_cap (score 0.24)
   Evidence: Score 0.24, Get the primary postal code for this comune
3) app/models/regional_taxes.py:141 — app.models.regional_taxes.Comune.has_cap (score 0.24)
   Evidence: Score 0.24, Check if this comune includes the given CAP
4) app/models/regional_taxes.py:145 — app.models.regional_taxes.Comune.to_dict (score 0.24)
   Evidence: Score 0.24, method: to_dict
5) app/services/vector_provider_factory.py:20 — app.services.vector_provider_factory.VectorSearchProvider.upsert (score 0.23)
   Evidence: Score 0.23, Upsert vectors into the provider.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for AttachmentFingerprint
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->