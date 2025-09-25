# RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields (RAG.preflight.docpreingest.quick.extract.type.sniff.and.key.fields)

**Type:** process  
**Category:** preflight  
**Node ID:** `QuickPreIngest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `QuickPreIngest` (DocPreIngest.quick_extract type sniff and key fields).

## Current Implementation (Repo)
- **Paths / classes:** _TBD during audit_
- **Status:** ✅ Implemented
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
Status: ❌  |  Confidence: 0.29

Top candidates:
1) app/orchestrators/preflight.py:147 — app.orchestrators.preflight.step_21__doc_pre_ingest (score 0.29)
   Evidence: Score 0.29, RAG STEP 21 — DocPreIngest.quick_extract type sniff and key fields
ID: RAG.prefl...
2) app/orchestrators/docs.py:315 — app.orchestrators.docs.step_89__doc_type (score 0.27)
   Evidence: Score 0.27, RAG STEP 89 — Document type?
ID: RAG.docs.document.type
Type: decision | Categor...
3) app/orchestrators/facts.py:588 — app.orchestrators.facts.step_95__extract_doc_facts (score 0.27)
   Evidence: Score 0.27, RAG STEP 95 — Extractor.extract Structured fields
ID: RAG.facts.extractor.extrac...
4) app/orchestrators/preflight.py:505 — app.orchestrators.preflight.step_82__doc_ingest (score 0.27)
   Evidence: Score 0.27, RAG STEP 82 — DocumentIngestTool.process Process attachments
ID: RAG.preflight.d...
5) app/orchestrators/docs.py:1210 — app.orchestrators.docs._extract_text_and_metadata (score 0.27)
   Evidence: Score 0.27, Helper function to extract text and metadata from parsed RSS feeds.

Args:
    p...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for QuickPreIngest
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->