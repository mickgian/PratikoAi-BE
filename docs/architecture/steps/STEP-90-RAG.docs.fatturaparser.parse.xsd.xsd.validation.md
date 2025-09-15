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
Status: ❌  |  Confidence: 0.23

Top candidates:
1) app/services/validators/financial_validation_engine.py:518 — app.services.validators.financial_validation_engine.FinancialValidationEngine._execute_document_parsing (score 0.23)
   Evidence: Score 0.23, Execute document parsing task.
2) app/models/document_simple.py:132 — app.models.document_simple.Document.is_expired (score 0.22)
   Evidence: Score 0.22, Check if document has expired
3) app/models/document_simple.py:136 — app.models.document_simple.Document.to_dict (score 0.22)
   Evidence: Score 0.22, Convert document to dictionary for API responses
4) app/services/document_uploader.py:189 — app.services.document_uploader.DocumentUploader._validate_file_signature (score 0.22)
   Evidence: Score 0.22, Validate file content matches expected file type signatures.

Args:
  content: F...
5) app/services/legal_document_analyzer.py:919 — app.services.legal_document_analyzer.ItalianLegalDocumentAnalyzer._extract_contract_price (score 0.22)
   Evidence: Score 0.22, Extract contract price

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for FatturaParser
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->