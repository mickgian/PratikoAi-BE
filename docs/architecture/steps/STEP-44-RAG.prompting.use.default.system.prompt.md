# RAG STEP 44 — Use default SYSTEM_PROMPT (RAG.prompting.use.default.system.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `DefaultSysPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DefaultSysPrompt` (Use default SYSTEM_PROMPT).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/prompting.py:470` - `step_44__default_sys_prompt()`
- **Status:** ✅ Implemented
- **Behavior notes:** Orchestrator using default system prompt when domain-specific prompts are not available. Provides fallback prompt template for general conversation handling across all domains.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing prompting infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (platform flow and API integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 44 (...): ... | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (platform configuration and API settings)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.32

Top candidates:
1) app/orchestrators/prompting.py:203 — app.orchestrators.prompting._get_default_system_prompt (score 0.32)
   Evidence: Score 0.32, Get appropriate default system prompt based on query analysis.
2) app/orchestrators/prompting.py:470 — app.orchestrators.prompting.step_44__default_sys_prompt (score 0.32)
   Evidence: Score 0.32, RAG STEP 44 — Use default SYSTEM_PROMPT
ID: RAG.prompting.use.default.system.pro...
3) app/orchestrators/prompting.py:14 — app.orchestrators.prompting.step_15__default_prompt (score 0.29)
   Evidence: Score 0.29, RAG STEP 15 — Continue without classification
ID: RAG.prompting.continue.without...
4) app/core/prompts/__init__.py:9 — app.core.prompts.__init__.load_system_prompt (score 0.28)
   Evidence: Score 0.28, Load the system prompt from the file.
5) app/services/italian_document_analyzer.py:189 — app.services.italian_document_analyzer.ItalianDocumentAnalyzer._build_system_prompt (score 0.28)
   Evidence: Score 0.28, Build system prompt based on analysis type

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Internal step is correctly implemented (no wiring required)

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->