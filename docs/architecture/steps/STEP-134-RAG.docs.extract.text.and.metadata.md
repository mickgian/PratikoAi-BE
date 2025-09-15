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
Status: 🔌  |  Confidence: 0.30

Top candidates:
1) app/services/atomic_facts_extractor.py:421 — app.services.atomic_facts_extractor.AtomicFactsExtractor.extract (score 0.30)
   Evidence: Score 0.30, Extract atomic facts from an Italian professional query.

Args:
    query: The u...
2) version-management/validation/contract_validator.py:146 — version-management.validation.contract_validator.APIContractValidator._contract_to_openapi (score 0.28)
   Evidence: Score 0.28, Convert APIContract to OpenAPI specification.
3) app/services/italian_document_collector.py:451 — app.services.italian_document_collector.ItalianDocumentCollector._extract_keywords (score 0.27)
   Evidence: Score 0.27, Extract relevant keywords from document content.
4) app/services/italian_document_collector.py:440 — app.services.italian_document_collector.ItalianDocumentCollector._extract_tax_types (score 0.27)
   Evidence: Score 0.27, Extract relevant tax types from document content.
5) app/models/document.py:118 — app.models.document.Document.is_expired (score 0.27)
   Evidence: Score 0.27, Check if document has expired

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
- Test document parsing and validation
<!-- AUTO-AUDIT:END -->