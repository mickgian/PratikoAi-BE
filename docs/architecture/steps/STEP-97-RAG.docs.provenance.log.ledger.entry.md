# RAG STEP 97 — Provenance.log Ledger entry (RAG.docs.provenance.log.ledger.entry)

**Type:** process  
**Category:** docs  
**Node ID:** `Provenance`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Provenance` (Provenance.log Ledger entry).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/docs.py:step_97__provenance`
- **Status:** 🔌
- **Behavior notes:** Thin orchestrator logs provenance ledger entries with immutable metadata for document processing audit trail. Creates ledger entries with timestamp, blob_id, encryption status, TTL. Routes to Step 98 (ToToolResults).

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing document processing infrastructure

## TDD Task List
- [x] Unit tests (provenance logging, ledger metadata, immutable characteristics, routing)
- [x] Integration tests (Step 96→97→98 flow, multiple documents)
- [x] Implementation changes (thin orchestrator in app/orchestrators/docs.py)
- [x] Observability: add structured log line
  `RAG STEP 97 (RAG.docs.provenance.log.ledger.entry): Provenance.log Ledger entry | attrs={...}`
- [x] Feature flag / config if needed (none required - core functionality)
- [x] Rollout plan (implemented with comprehensive tests)

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