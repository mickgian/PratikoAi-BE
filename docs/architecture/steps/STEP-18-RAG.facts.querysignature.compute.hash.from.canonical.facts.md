# RAG STEP 18 — QuerySignature.compute Hash from canonical facts (RAG.facts.querysignature.compute.hash.from.canonical.facts)

**Type:** process  
**Category:** facts  
**Node ID:** `QuerySig`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuerySig` (QuerySignature.compute Hash from canonical facts).

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
  `RAG STEP 18 (RAG.facts.querysignature.compute.hash.from.canonical.facts): QuerySignature.compute Hash from canonical facts | attrs={...}`
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
1) app/core/security/request_signing.py:79 — app.core.security.request_signing.RequestSigner.verify_signature (score 0.25)
   Evidence: Score 0.25, Verify request signature.

Args:
    method: HTTP method
    path: Request path
...
2) app/models/query.py:50 — app.models.query.LLMResponse.__post_init__ (score 0.24)
   Evidence: Score 0.24, Add timestamp if not present.
3) app/models/query.py:74 — app.models.query.QueryResponse.__post_init__ (score 0.24)
   Evidence: Score 0.24, method: __post_init__
4) app/models/query.py:181 — app.models.query.QueryMetrics.success_rate (score 0.24)
   Evidence: Score 0.24, Calculate success rate percentage.
5) app/models/query.py:188 — app.models.query.QueryMetrics.failure_rate (score 0.24)
   Evidence: Score 0.24, Calculate failure rate percentage.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuerySig
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->