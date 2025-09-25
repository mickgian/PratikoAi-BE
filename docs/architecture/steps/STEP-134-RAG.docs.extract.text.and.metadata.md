# RAG STEP 134 — Extract text and metadata (RAG.docs.extract.text.and.metadata)

**Type:** process  
**Category:** docs  
**Node ID:** `ParseDocs`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ParseDocs` (Extract text and metadata).

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
  `RAG STEP 134 (RAG.docs.extract.text.and.metadata): Extract text and metadata | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.41

Top candidates:
1) app/orchestrators/docs.py:500 — app.orchestrators.docs.step_91__f24_parser (score 0.41)
   Evidence: Score 0.41, RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR
ID: RAG.docs.f24parser.parse....
2) app/orchestrators/docs.py:387 — app.orchestrators.docs.step_90__fattura_parser (score 0.38)
   Evidence: Score 0.38, RAG STEP 90 — FatturaParser.parse_xsd XSD validation
ID: RAG.docs.fatturaparser....
3) app/orchestrators/docs.py:610 — app.orchestrators.docs.step_92__contract_parser (score 0.38)
   Evidence: Score 0.38, RAG STEP 92 — ContractParser.parse
ID: RAG.docs.contractparser.parse
Type: proce...
4) app/orchestrators/docs.py:735 — app.orchestrators.docs.step_93__payslip_parser (score 0.38)
   Evidence: Score 0.38, RAG STEP 93 — PayslipParser.parse
ID: RAG.docs.payslipparser.parse
Type: process...
5) app/orchestrators/docs.py:315 — app.orchestrators.docs.step_89__doc_type (score 0.37)
   Evidence: Score 0.37, RAG STEP 89 — Document type?
ID: RAG.docs.document.type
Type: decision | Categor...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->