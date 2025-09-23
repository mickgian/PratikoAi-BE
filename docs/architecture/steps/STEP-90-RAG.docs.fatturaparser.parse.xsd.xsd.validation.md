# RAG STEP 90 — FatturaParser.parse_xsd XSD validation (RAG.docs.fatturaparser.parse.xsd.xsd.validation)

**Type:** process  
**Category:** docs  
**Node ID:** `FatturaParser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FatturaParser` (FatturaParser.parse_xsd XSD validation).

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
  `RAG STEP 90 (RAG.docs.fatturaparser.parse.xsd.xsd.validation): FatturaParser.parse_xsd XSD validation | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.31

Top candidates:
1) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.31)
   Evidence: Score 0.31, Convert APIContract to OpenAPI specification.
2) app/orchestrators/docs.py:1111 — app.orchestrators.docs.step_134__parse_docs (score 0.30)
   Evidence: Score 0.30, RAG STEP 134 — Extract text and metadata
ID: RAG.docs.extract.text.and.metadata
...
3) app/services/legal_document_analyzer.py:883 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_parties (score 0.29)
   Evidence: Score 0.29, Extract parties from contract
4) app/services/legal_document_analyzer.py:905 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_object (score 0.29)
   Evidence: Score 0.29, Extract contract object/purpose
5) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.29)
   Evidence: Score 0.29, Extract contract price

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->