# RAG STEP 98 — Convert to ToolMessage facts and spans (RAG.facts.convert.to.toolmessage.facts.and.spans)

**Type:** process  
**Category:** facts  
**Node ID:** `ToToolResults`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ToToolResults` (Convert to ToolMessage facts and spans).

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
  `RAG STEP 98 (RAG.facts.convert.to.toolmessage.facts.and.spans): Convert to ToolMessage facts and spans | attrs={...}`
- [ ] Feature flag / config if needed
- [ ] Rollout plan

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ❌  |  Confidence: 0.24

Top candidates:
1) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.24)
   Evidence: Score 0.24, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
2) app/core/llm/factory.py:27 — app.core.llm.factory.LLMFactory.__init__ (score 0.23)
   Evidence: Score 0.23, Initialize the LLM factory.
3) app/core/llm/factory.py:33 — app.core.llm.factory.LLMFactory._get_provider_configs (score 0.23)
   Evidence: Score 0.23, Get provider configurations from settings.

Returns:
    Dictionary of provider ...
4) app/core/llm/factory.py:59 — app.core.llm.factory.LLMFactory.create_provider (score 0.23)
   Evidence: Score 0.23, Create an LLM provider instance.

Args:
    provider_type: Type of provider to c...
5) app/core/llm/factory.py:105 — app.core.llm.factory.LLMFactory.get_available_providers (score 0.23)
   Evidence: Score 0.23, Get all available configured providers.

Returns:
    List of available provider...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ToToolResults
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->