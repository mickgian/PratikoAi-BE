# RAG STEP 104 — Streaming requested? (RAG.streaming.streaming.requested)

**Type:** decision  
**Category:** streaming  
**Node ID:** `StreamCheck`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `StreamCheck` (Streaming requested?).

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
  `RAG STEP 104 (RAG.streaming.streaming.requested): Streaming requested? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.19

Top candidates:
1) app/core/security/request_signing.py:16 — app.core.security.request_signing.RequestSigner.__init__ (score 0.19)
   Evidence: Score 0.19, Initialize request signer.
2) app/core/security/request_signing.py:23 — app.core.security.request_signing.RequestSigner.generate_signature (score 0.19)
   Evidence: Score 0.19, Generate HMAC signature for request.

Args:
    method: HTTP method (GET, POST, ...
3) app/core/security/request_signing.py:79 — app.core.security.request_signing.RequestSigner.verify_signature (score 0.19)
   Evidence: Score 0.19, Verify request signature.

Args:
    method: HTTP method
    path: Request path
...
4) app/core/security/request_signing.py:148 — app.core.security.request_signing.RequestSigner._is_timestamp_valid (score 0.19)
   Evidence: Score 0.19, Check if timestamp is within acceptable range.

Args:
    timestamp_str: Unix ti...
5) app/core/security/request_signing.py:229 — app.core.security.request_signing.RequestSigner.create_webhook_signature (score 0.19)
   Evidence: Score 0.19, Create signature for webhook payloads (like Stripe).

Args:
    payload: Webhook...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create decision implementation for StreamCheck
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->