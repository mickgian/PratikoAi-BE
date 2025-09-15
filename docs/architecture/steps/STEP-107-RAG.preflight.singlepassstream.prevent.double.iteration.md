# RAG STEP 107 — SinglePassStream Prevent double iteration (RAG.preflight.singlepassstream.prevent.double.iteration)

**Type:** process  
**Category:** preflight  
**Node ID:** `SinglePass`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `SinglePass` (SinglePassStream Prevent double iteration).

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
  `RAG STEP 107 (RAG.preflight.singlepassstream.prevent.double.iteration): SinglePassStream Prevent double iteration | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.20

Top candidates:
1) app/models/cassazione_data.py:209 — app.models.cassazione_data.Citation.is_law_citation (score 0.20)
   Evidence: Score 0.20, Check if this is a citation to law.
2) app/models/cassazione_data.py:213 — app.models.cassazione_data.Citation.is_decision_citation (score 0.20)
   Evidence: Score 0.20, Check if this is a citation to another decision.
3) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.20)
   Evidence: Score 0.20, Validate the citation.
4) app/models/cassazione_data.py:222 — app.models.cassazione_data.Citation.extract_from_text (score 0.20)
   Evidence: Score 0.20, Extract citations from decision text.
5) app/core/performance/cdn_integration.py:69 — app.core.performance.cdn_integration.CDNManager.__init__ (score 0.19)
   Evidence: Score 0.19, Initialize CDN manager.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for SinglePass
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->