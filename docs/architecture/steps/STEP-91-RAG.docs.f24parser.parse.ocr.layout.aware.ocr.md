# RAG STEP 91 — F24Parser.parse_ocr Layout aware OCR (RAG.docs.f24parser.parse.ocr.layout.aware.ocr)

**Type:** process  
**Category:** docs  
**Node ID:** `F24Parser`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `F24Parser` (F24Parser.parse_ocr Layout aware OCR).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/docs.py:500` - `step_91__f24_parser()`
- **Status:** 🔌
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
Role: Internal  |  Status: 🔌 (Implemented (internal))  |  Registry: ❌ Not in registry

Notes:
- ✅ Internal step (no wiring required)
<!-- AUTO-AUDIT:END -->