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
Status: ❌  |  Confidence: 0.27

Top candidates:
1) app/orchestrators/docs.py:108 — app.orchestrators.docs.step_89__doc_type (score 0.27)
   Evidence: Score 0.27, RAG STEP 89 — Document type?
ID: RAG.docs.document.type
Type: decision | Categor...
2) app/orchestrators/facts.py:403 — app.orchestrators.facts.step_95__extract_doc_facts (score 0.27)
   Evidence: Score 0.27, RAG STEP 95 — Extractor.extract Structured fields
ID: RAG.facts.extractor.extrac...
3) app/orchestrators/preflight.py:400 — app.orchestrators.preflight.step_82__doc_ingest (score 0.27)
   Evidence: Score 0.27, RAG STEP 82 — DocumentIngestTool.process Process attachments
ID: RAG.preflight.d...
4) app/orchestrators/golden.py:32 — app.orchestrators.golden.step_23__require_doc_ingest (score 0.27)
   Evidence: Score 0.27, RAG STEP 23 — PlannerHint.require_doc_ingest_first ingest then Golden and KB
ID:...
5) app/services/domain_action_classifier.py:530 — app.services.domain_action_classifier.DomainActionClassifier._extract_document_type (score 0.26)
   Evidence: Score 0.26, Extract document type for document generation actions

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuickPreIngest
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->