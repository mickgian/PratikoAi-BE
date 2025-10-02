# RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR (RAG.docs.f24parser.parse.ocr.layout.aware.ocr)

**Type:** process  
**Category:** docs  
**Node ID:** `F24Parser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `F24Parser` (F24Parser.parse_ocr Layout aware OCR).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/docs.py:500` - `step_91__f24_parser()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator processing F24 tax forms using layout-aware OCR. Extracts structured data from Italian F24 payment forms with field recognition and validation. Routes to Step 95 (ExtractDocFacts) for fact extraction.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing document processing infrastructure

## TDD Task List
- [x] Unit tests (document processing, parsing, format handling)
- [x] Integration tests (document processing flow and format validation)
- [x] Implementation changes (async orchestrator with document processing, parsing, format handling)
- [x] Observability: add structured log line
  `RAG STEP 91 (...): ... | attrs={document_type, file_size, processing_time}`
- [x] Feature flag / config if needed (document processing limits and format support)
- [x] Rollout plan (implemented with document processing reliability and security safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.40

Top candidates:
1) app/orchestrators/docs.py:500 — app.orchestrators.docs.step_91__f24_parser (score 0.40)
   Evidence: Score 0.40, RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR
ID: RAG.docs.f24parser.parse....
2) app/orchestrators/docs.py:387 — app.orchestrators.docs.step_90__fattura_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 90 — FatturaParser.parse_xsd XSD validation
ID: RAG.docs.fatturaparser....
3) app/orchestrators/docs.py:610 — app.orchestrators.docs.step_92__contract_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 92 — ContractParser.parse
ID: RAG.docs.contractparser.parse
Type: proce...
4) app/orchestrators/docs.py:735 — app.orchestrators.docs.step_93__payslip_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 93 — PayslipParser.parse
ID: RAG.docs.payslipparser.parse
Type: process...
5) app/orchestrators/docs.py:315 — app.orchestrators.docs.step_89__doc_type (score 0.35)
   Evidence: Score 0.35, RAG STEP 89 — Document type?
ID: RAG.docs.document.type
Type: decision | Categor...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->