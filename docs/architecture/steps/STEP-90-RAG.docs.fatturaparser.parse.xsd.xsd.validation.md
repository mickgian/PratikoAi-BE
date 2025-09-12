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
Status: 🔌  |  Confidence: 0.30

Top candidates:
1) version-management/validation/contract_validator.py:75 — version-management.validation.contract_validator.APIContractValidator.__init__ (score 0.30)
   Evidence: Score 0.30, method: __init__
2) version-management/validation/contract_validator.py:78 — version-management.validation.contract_validator.APIContractValidator._load_breaking_change_rules (score 0.30)
   Evidence: Score 0.30, Load rules for detecting breaking changes.
3) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.30)
   Evidence: Score 0.30, Convert APIContract to OpenAPI specification.
4) version-management/validation/contract_validator.py:633 — version-management.validation.contract_validator.APIContractValidator._generate_summary (score 0.30)
   Evidence: Score 0.30, Generate summary statistics.
5) version-management/validation/contract_validator.py:728 — version-management.validation.contract_validator.APIContractValidator._generate_test_data (score 0.30)
   Evidence: Score 0.30, Generate test data based on JSON schema.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->