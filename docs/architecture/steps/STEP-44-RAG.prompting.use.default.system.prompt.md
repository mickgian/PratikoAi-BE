# RAG STEP 44 — Use default SYSTEM_PROMPT (RAG.prompting.use.default.system.prompt)

**Type:** process  
**Category:** prompting  
**Node ID:** `DefaultSysPrompt`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `DefaultSysPrompt` (Use default SYSTEM_PROMPT).

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
  `RAG STEP 44 (RAG.prompting.use.default.system.prompt): Use default SYSTEM_PROMPT | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: 🔌  |  Confidence: 0.32

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

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->