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
Status: ❌  |  Confidence: 0.30

Top candidates:
1) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.30)
   Evidence: Score 0.30, Convert APIContract to OpenAPI specification.
2) app/services/legal_document_analyzer.py:883 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_parties (score 0.29)
   Evidence: Score 0.29, Extract parties from contract
3) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.29)
   Evidence: Score 0.29, Extract contract object/purpose
4) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.29)
   Evidence: Score 0.29, Extract contract price
5) app/services/legal_document_analyzer.py:933 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_duration (score 0.29)
   Evidence: Score 0.29, Extract contract duration

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DocDependent
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->