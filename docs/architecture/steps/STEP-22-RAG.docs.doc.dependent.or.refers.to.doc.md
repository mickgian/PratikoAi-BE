# RAG STEP 22 — Doc-dependent or refers to doc? (RAG.docs.doc.dependent.or.refers.to.doc)

**Type:** process  
**Category:** docs  
**Node ID:** `DocDependent`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocDependent` (Doc-dependent or refers to doc?).

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
  `RAG STEP 22 (RAG.docs.doc.dependent.or.refers.to.doc): Doc-dependent or refers to doc? | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.40

Top candidates:
1) app/orchestrators/docs.py:144 — app.orchestrators.docs.step_91__f24_parser (score 0.40)
   Evidence: Score 0.40, RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR
ID: RAG.docs.f24parser.parse....
2) app/orchestrators/docs.py:126 — app.orchestrators.docs.step_90__fattura_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 90 — FatturaParser.parse_xsd XSD validation
ID: RAG.docs.fatturaparser....
3) app/orchestrators/docs.py:162 — app.orchestrators.docs.step_92__contract_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 92 — ContractParser.parse
ID: RAG.docs.contractparser.parse
Type: proce...
4) app/orchestrators/docs.py:180 — app.orchestrators.docs.step_93__payslip_parser (score 0.37)
   Evidence: Score 0.37, RAG STEP 93 — PayslipParser.parse
ID: RAG.docs.payslipparser.parse
Type: process...
5) app/orchestrators/docs.py:234 — app.orchestrators.docs.step_97__provenance (score 0.33)
   Evidence: Score 0.33, RAG STEP 97 — Provenance.log Ledger entry
ID: RAG.docs.provenance.log.ledger.ent...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->