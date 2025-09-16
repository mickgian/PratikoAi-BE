# RAG STEP 11 — LangGraphAgent._chat Convert to Message objects (RAG.platform.langgraphagent.chat.convert.to.message.objects)

**Type:** process  
**Category:** platform  
**Node ID:** `ConvertMessages`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ConvertMessages` (LangGraphAgent._chat Convert to Message objects).

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
  `RAG STEP 11 (RAG.platform.langgraphagent.chat.convert.to.message.objects): LangGraphAgent._chat Convert to Message objects | attrs={...}`
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
1) app/utils/graph.py:10 — app.utils.graph.dump_messages (score 0.28)
   Evidence: Score 0.28, Dump the messages to a list of dictionaries.

Args:
    messages (list[Message])...
2) app/utils/graph.py:22 — app.utils.graph.prepare_messages (score 0.28)
   Evidence: Score 0.28, Prepare the messages for the LLM.

Args:
    messages (list[Message]): The messa...
3) app/schemas/chat.py:34 — app.schemas.chat.Message.validate_content (score 0.27)
   Evidence: Score 0.27, Validate the message content.

Args:
    v: The content to validate

Returns:
  ...
4) app/core/llm/providers/anthropic_provider.py:86 — app.core.llm.providers.anthropic_provider.AnthropicProvider._convert_messages_to_anthropic (score 0.27)
   Evidence: Score 0.27, Convert messages to Anthropic format.

Args:
    messages: List of Message objec...
5) app/core/langgraph/graph.py:31 — app.core.langgraph.graph.step_45_rag_prompting_system_message_exists (score 0.26)
   Evidence: Score 0.26, function: step_45_rag_prompting_system_message_exists

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ConvertMessages
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->