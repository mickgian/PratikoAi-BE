# RAG STEP 126 — Determine action (RAG.platform.determine.action)

**Type:** process  
**Category:** platform  
**Node ID:** `DetermineAction`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DetermineAction` (Determine action).

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
  `RAG STEP 126 (RAG.platform.determine.action): Determine action | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/services/domain_action_classifier.py:35 — app.services.domain_action_classifier.Action (score 0.27)
   Evidence: Score 0.27, Professional actions/intents
2) app/models/cassazione_data.py:209 — app.models.cassazione_data.Citation.is_law_citation (score 0.24)
   Evidence: Score 0.24, Check if this is a citation to law.
3) app/models/cassazione_data.py:213 — app.models.cassazione_data.Citation.is_decision_citation (score 0.24)
   Evidence: Score 0.24, Check if this is a citation to another decision.
4) app/models/cassazione_data.py:217 — app.models.cassazione_data.Citation.is_valid (score 0.24)
   Evidence: Score 0.24, Validate the citation.
5) app/models/cassazione_data.py:222 — app.models.cassazione_data.Citation.extract_from_text (score 0.24)
   Evidence: Score 0.24, Extract citations from decision text.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DetermineAction
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->