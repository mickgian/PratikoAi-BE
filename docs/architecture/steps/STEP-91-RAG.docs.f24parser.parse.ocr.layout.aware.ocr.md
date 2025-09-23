# RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR (RAG.docs.f24parser.parse.ocr.layout.aware.ocr)

**Type:** process  
**Category:** docs  
**Node ID:** `F24Parser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `F24Parser` (F24Parser.parse_ocr Layout aware OCR).

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
  `RAG STEP 91 (RAG.docs.f24parser.parse.ocr.layout.aware.ocr): F24Parser.parse_ocr Layout aware OCR | attrs={...}`
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
1) app/orchestrators/docs.py:1111 — app.orchestrators.docs.step_134__parse_docs (score 0.30)
   Evidence: Score 0.30, RAG STEP 134 — Extract text and metadata
ID: RAG.docs.extract.text.and.metadata
...
2) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.29)
   Evidence: Score 0.29, Convert APIContract to OpenAPI specification.
3) app/services/legal_document_analyzer.py:883 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_parties (score 0.29)
   Evidence: Score 0.29, Extract parties from contract
4) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.29)
   Evidence: Score 0.29, Extract contract object/purpose
5) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.29)
   Evidence: Score 0.29, Extract contract price

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for F24Parser
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->