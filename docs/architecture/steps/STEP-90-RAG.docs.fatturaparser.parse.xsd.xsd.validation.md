# RAG STEP 90 — FatturaParser.parse_xsd XSD validation (RAG.docs.fatturaparser.parse.xsd.xsd.validation)

**Type:** process  
**Category:** docs  
**Node ID:** `FatturaParser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `FatturaParser` (FatturaParser.parse_xsd XSD validation).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/docs.py:387` - `step_90__fattura_parser()`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator parsing Italian electronic invoices (Fattura Elettronica) using XSD validation. Processes XML invoices according to Italian tax authority specifications, extracts structured data, and validates against schema requirements.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing document processing infrastructure

## TDD Task List
- [x] Unit tests (document processing, parsing, format handling)
- [x] Integration tests (document processing flow and format validation)
- [x] Implementation changes (async orchestrator with document processing, parsing, format handling)
- [x] Observability: add structured log line
  `RAG STEP 90 (...): ... | attrs={document_type, file_size, processing_time}`
- [x] Feature flag / config if needed (document processing limits and format support)
- [x] Rollout plan (implemented with document processing reliability and security safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->