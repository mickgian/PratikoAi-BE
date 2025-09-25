# RAG STEP 97 — Provenance.log Ledger entry (RAG.docs.provenance.log.ledger.entry)

**Type:** process  
**Category:** docs  
**Node ID:** `Provenance`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Provenance` (Provenance.log Ledger entry).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/docs.py:step_97__provenance`
- **Status:** ✅ Implemented
- **Behavior notes:** Thin orchestrator logs provenance ledger entries with immutable metadata for document processing audit trail. Creates ledger entries with timestamp, blob_id, encryption status, TTL. Routes to Step 98 (ToToolResults).

## Differences (Blueprint vs Current)
- _TBD_

## Risks / Impact
- _TBD_

## TDD Task List
- [x] Unit tests (provenance logging, ledger metadata, immutable characteristics, routing)
- [x] Integration tests (Step 96→97→98 flow, multiple documents)
- [x] Implementation changes (thin orchestrator in app/orchestrators/docs.py)
- [x] Observability: add structured log line
  `RAG STEP 97 (RAG.docs.provenance.log.ledger.entry): Provenance.log Ledger entry | attrs={...}`
- [x] Feature flag / config if needed (none required - core functionality)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.40

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

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->