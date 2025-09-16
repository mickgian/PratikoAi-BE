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
Status: 🔌  |  Confidence: 0.34

Top candidates:
1) app/ragsteps/prompting/step_44_rag_prompting_use_default_system_prompt.py:44 — app.ragsteps.prompting.step_44_rag_prompting_use_default_system_prompt.step_44_rag_prompting_use_default_system_prompt (score 0.34)
   Evidence: Score 0.34, function: step_44_rag_prompting_use_default_system_prompt
2) app/ragsteps/prompting/step_44_rag_prompting_use_default_system_prompt.py:26 — app.ragsteps.prompting.step_44_rag_prompting_use_default_system_prompt.run (score 0.33)
   Evidence: Score 0.33, function: run
3) app/core/prompts/__init__.py:9 — app.core.prompts.__init__.load_system_prompt (score 0.28)
   Evidence: Score 0.28, Load the system prompt from the file.
4) app/services/italian_document_analyzer.py:189 — app.services.italian_document_analyzer.ItalianDocumentAnalyzer._build_system_prompt (score 0.28)
   Evidence: Score 0.28, Build system prompt based on analysis type
5) deployment-orchestration/notification_system.py:674 — deployment-orchestration.notification_system.NotificationManager.setup_default_rules (score 0.28)
   Evidence: Score 0.28, Setup default notification rules.

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->