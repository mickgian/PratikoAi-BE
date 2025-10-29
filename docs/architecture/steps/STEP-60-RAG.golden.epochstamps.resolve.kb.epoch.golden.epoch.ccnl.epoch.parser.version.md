# RAG STEP 60 — EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version (RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version)

**Type:** process  
**Category:** golden  
**Node ID:** `ResolveEpochs`

## Intent (Blueprint)
Resolves version epochs from various data sources (KB, Golden Set, CCNL, parsers) to enable cache invalidation based on data freshness. These epochs are used by Step 61 (GenHash) for cache key generation, ensuring cached responses are invalidated when underlying data changes.

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/golden.py:step_60__resolve_epochs`
- **Status:** 🔌
- **Behavior notes:** Async orchestrator that extracts epoch timestamps from context (kb_last_updated, golden_last_updated, ccnl_last_updated, parser_version). Creates epoch resolution metadata tracking which epochs were resolved. Routes to Step 61 (GenHash) with resolved epochs for cache key generation.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - simple epoch extraction with graceful handling of missing values

## TDD Task List
- [x] Unit tests (resolve all epochs, missing epochs, defaults, context preservation, logging, metadata, timestamp conversion)
- [x] Parity tests (epoch resolution behavior verification)
- [x] Integration tests (Step 59→60→61 flow, prepare for GenHash)
- [x] Implementation changes (async orchestrator with epoch extraction)
- [x] Observability: add structured log line
  `RAG STEP 60 (RAG.golden.epochstamps.resolve.kb.epoch.golden.epoch.ccnl.epoch.parser.version): EpochStamps.resolve kb_epoch golden_epoch ccnl_epoch parser_version | attrs={epochs_resolved, kb_epoch, golden_epoch, ccnl_epoch, parser_version, next_step}`
- [x] Feature flag / config if needed (none required - extracts from context)
- [x] Rollout plan (implemented with comprehensive tests)

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