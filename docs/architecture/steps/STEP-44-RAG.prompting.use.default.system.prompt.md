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
Status: ❌  |  Confidence: 0.28

Top candidates:
1) app/core/prompts/__init__.py:9 — app.core.prompts.__init__.load_system_prompt (score 0.28)
   Evidence: Score 0.28, Load the system prompt from the file.
2) app/services/italian_document_analyzer.py:189 — app.services.italian_document_analyzer.ItalianDocumentAnalyzer._build_system_prompt (score 0.28)
   Evidence: Score 0.28, Build system prompt based on analysis type
3) deployment-orchestration/notification_system.py:674 — deployment-orchestration.notification_system.NotificationManager.setup_default_rules (score 0.28)
   Evidence: Score 0.28, Setup default notification rules.
4) app/core/langgraph/graph.py:529 — app.core.langgraph.graph.LangGraphAgent._get_system_prompt (score 0.27)
   Evidence: Score 0.27, Get the appropriate system prompt based on classification.

RAG STEP 41 — LangGr...
5) app/services/italian_document_analyzer.py:239 — app.services.italian_document_analyzer.ItalianDocumentAnalyzer._build_comparison_system_prompt (score 0.27)
   Evidence: Score 0.27, Build system prompt for document comparison

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for DefaultSysPrompt
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->