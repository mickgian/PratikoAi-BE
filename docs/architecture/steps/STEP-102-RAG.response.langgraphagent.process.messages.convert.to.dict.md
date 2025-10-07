# RAG STEP 102 — LangGraphAgent.__process_messages Convert to dict (RAG.response.langgraphagent.process.messages.convert.to.dict)

**Type:** process  
**Category:** response  
**Node ID:** `ProcessMsg`

## Intent (Blueprint)
Converts LangChain BaseMessage objects to dictionary format for final response processing. Applies filtering logic to keep only assistant and user messages with content, removing system messages, tool messages, and empty content. Routes processed messages to LogComplete (Step 103) for final completion logging. This step is derived from the Mermaid node: `ProcessMsg` (LangGraphAgent.__process_messages Convert to dict).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:** `app/orchestrators/response.py:697` - `step_102__process_msg()`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that converts LangChain BaseMessage objects to dictionary format using convert_to_openai_messages. Filters to user/assistant messages with non-empty content. Preserves all context data and adds message processing metadata. Routes to LogComplete (Step 103).

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing message processing logic

## TDD Task List
- [x] Unit tests (message conversion, filtering, content preservation, empty handling, complex types, context preservation, metadata addition)
- [x] Parity tests (message conversion behavior verification)
- [x] Integration tests (FinalResponse→ProcessMsg→LogComplete flow, ReturnCached integration)
- [x] Implementation changes (async message processing orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 102 (RAG.response.langgraphagent.process.messages.convert.to.dict): LangGraphAgent.__process_messages Convert to dict | attrs={step, request_id, original_message_count, processed_message_count, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing conversion logic)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: 🔌 (Implemented - internal)  |  Confidence: 0.36

Top candidates:
1) app/core/langgraph/graph.py:1848 — app.core.langgraph.graph.LangGraphAgent.__process_messages (score 0.36)
   Evidence: Score 0.36, method: __process_messages
2) app/orchestrators/response.py:656 — app.orchestrators.response._process_messages_to_dict (score 0.31)
   Evidence: Score 0.31, Convert LangChain BaseMessage objects to dictionary format.
Mirrors the logic fr...
3) app/core/langgraph/graph.py:185 — app.core.langgraph.graph.LangGraphAgent.__init__ (score 0.30)
   Evidence: Score 0.30, Initialize the LangGraph Agent with necessary components.
4) app/core/langgraph/graph.py:929 — app.core.langgraph.graph.LangGraphAgent._should_continue (score 0.29)
   Evidence: Score 0.29, Determine if the agent should continue or end based on the last message.

Args:
...
5) app/core/langgraph/graph.py:447 — app.core.langgraph.graph.LangGraphAgent._get_routing_strategy (score 0.29)
   Evidence: Score 0.29, Get the LLM routing strategy from configuration.

Returns:
    RoutingStrategy: ...

Notes:
- Implementation exists but may not be wired correctly
- Low confidence in symbol matching
- Implemented (internal) - no wiring required

Suggested next TDD actions:
- Connect existing implementation to RAG workflow
- Add integration tests for end-to-end flow
- Verify error handling and edge cases
<!-- AUTO-AUDIT:END -->