# RAG STEP 22 — Doc-dependent or refers to doc? (RAG.docs.doc.dependent.or.refers.to.doc)

**Type:** process  
**Category:** docs  
**Node ID:** `DocDependent`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DocDependent` (Doc-dependent or refers to doc?).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/docs.py:16` - `step_22__doc_dependent_check()`
- **Status:** 🔌
- **Behavior notes:** Node orchestrator checking if query is document-dependent or refers to documents. Decision point for document processing requirements.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing document processing infrastructure

## TDD Task List
- [x] Unit tests (document processing, parsing, format handling)
- [x] Integration tests (document processing flow and format validation)
- [x] Implementation changes (async orchestrator with document processing, parsing, format handling)
- [x] Observability: add structured log line
  `RAG STEP 22 (...): ... | attrs={document_type, file_size, processing_time}`
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