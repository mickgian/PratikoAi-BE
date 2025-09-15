# RAG STEP 1 — ChatbotController.chat Validate request and authenticate (RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate)

**Type:** process  
**Category:** platform  
**Node ID:** `ValidateRequest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateRequest` (ChatbotController.chat Validate request and authenticate).

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
  `RAG STEP 1 (RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate): ChatbotController.chat Validate request and authenticate | attrs={...}`
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
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.28)
   Evidence: Score 0.28, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) feature-flags/feature_flag_service.py:179 — feature-flags.feature_flag_service.FlagRequest.validate_flag_id (score 0.28)
   Evidence: Score 0.28, method: validate_flag_id
3) app/api/v1/italian.py:38 — app.api.v1.italian.TaxCalculationRequest.validate_tax_year (score 0.27)
   Evidence: Score 0.27, method: validate_tax_year
4) app/api/v1/data_export.py:69 — app.api.v1.data_export.CreateExportRequest.validate_future_dates (score 0.27)
   Evidence: Score 0.27, method: validate_future_dates
5) app/api/v1/data_export.py:75 — app.api.v1.data_export.CreateExportRequest.validate_date_range (score 0.27)
   Evidence: Score 0.27, method: validate_date_range

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ValidateRequest
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->