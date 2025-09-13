# RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields)

**Type:** process  
**Category:** preflight  
**Node ID:** `QuickPreIngest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuickPreIngest` (DocPreIngest.quick_extract type sniff and key fields).

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
  `RAG STEP 21 (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields): DocPreIngest.quick_extract type sniff and key fields | attrs={...}`
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
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.24)
   Evidence: Score 0.24, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) app/models/cassazione_data.py:261 — app.models.cassazione_data.ScrapingResult.success_rate (score 0.23)
   Evidence: Score 0.23, Calculate success rate.
3) app/models/cassazione_data.py:268 — app.models.cassazione_data.ScrapingResult.processing_rate (score 0.23)
   Evidence: Score 0.23, Calculate processing rate.
4) app/models/cassazione_data.py:275 — app.models.cassazione_data.ScrapingResult.duration_minutes (score 0.23)
   Evidence: Score 0.23, Get duration in minutes.
5) app/models/cassazione_data.py:279 — app.models.cassazione_data.ScrapingResult.is_valid (score 0.23)
   Evidence: Score 0.23, Validate the result.

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuickPreIngest
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->