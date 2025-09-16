# RAG STEP 102 — LangGraphAgent.__process_messages Convert to dict (RAG.response.langgraphagent.process.messages.convert.to.dict)

**Type:** process  
**Category:** response  
**Node ID:** `ProcessMsg`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ProcessMsg` (LangGraphAgent.__process_messages Convert to dict).

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
  `RAG STEP 102 (RAG.response.langgraphagent.process.messages.convert.to.dict): LangGraphAgent.__process_messages Convert to dict | attrs={...}`
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
3) app/services/context_builder_merge.py:557 — app.services.context_builder_merge.ContextBuilderMerge._convert_to_dict (score 0.27)
   Evidence: Score 0.27, Convert MergedContext to dictionary.
4) app/core/llm/providers/anthropic_provider.py:86 — app.core.llm.providers.anthropic_provider.AnthropicProvider._convert_messages_to_anthropic (score 0.27)
   Evidence: Score 0.27, Convert messages to Anthropic format.

Args:
    messages: List of Message objec...
5) app/core/llm/providers/openai_provider.py:103 — app.core.llm.providers.openai_provider.OpenAIProvider._convert_messages_to_openai (score 0.26)
   Evidence: Score 0.26, Convert messages to OpenAI format.

Args:
    messages: List of Message objects
...

Notes:
- Weak or missing implementation
- Low confidence in symbol matching

Suggested next TDD actions:
- Create process implementation for ProcessMsg
- Add unit tests covering happy path and edge cases
- Wire into the RAG pipeline flow
<!-- AUTO-AUDIT:END -->