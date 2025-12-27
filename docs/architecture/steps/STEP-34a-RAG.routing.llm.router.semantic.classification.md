# RAG STEP 34a — LLMRouterService.route Semantic query classification (RAG.routing.llm.router.semantic.classification)

**Type:** process
**Category:** routing
**Node ID:** `step_034a_llm_router`

## Intent (Blueprint)
Semantic query classification using LLM-powered routing. This step integrates the LLMRouterService to classify user queries into routing categories for intelligent pipeline navigation:

- **CHITCHAT**: Casual conversation, handled directly without retrieval
- **CALCULATOR**: Calculation requests, routed to calculator tools
- **THEORETICAL_DEFINITION**: Definition requests, triggers RAG retrieval
- **TECHNICAL_RESEARCH**: Complex queries, triggers full RAG retrieval
- **GOLDEN_SET**: Known high-value patterns, golden set lookup

This replaces regex-based routing with semantic understanding for more accurate query classification.

## Current Implementation (Repo)
- **Paths / classes:** `app/core/langgraph/nodes/step_034a__llm_router.py:85` - `node_step_34a()`
- **Service:** `app/services/llm_router_service.py` - `LLMRouterService`
- **Role:** External (LangGraph node)
- **Status:** 🔌
- **Behavior notes:**
  - Extracts user query from state or last user message
  - Calls LLMRouterService.route() for semantic classification
  - Stores RouterDecision as serializable dict in state["routing_decision"]
  - Falls back to TECHNICAL_RESEARCH on any error (confidence 0.3)

## State Changes
**Input:**
- `user_query` (str): The user's query text
- `messages` (list): Conversation history for context

**Output:**
- `routing_decision` (dict): Serialized RouterDecision containing:
  - `route` (str): The routing category value
  - `confidence` (float): Classification confidence (0.0-1.0)
  - `reasoning` (str): Explanation for the classification
  - `entities` (list[dict]): Extracted entities with text, type, confidence
  - `requires_freshness` (bool): Whether fresh data is needed
  - `suggested_sources` (list[str]): Recommended sources for retrieval
  - `needs_retrieval` (bool): Whether RAG retrieval is required

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- LLM service unavailability: Mitigated with fallback to TECHNICAL_RESEARCH
- Classification latency: ~200-500ms per query (cached after first call)
- Token costs: Uses GPT-4o-mini for cost efficiency (~$0.00015/query)

## TDD Task List
- [x] Unit tests (routing categories, fallback behavior, state preservation)
- [x] Integration tests (service integration, conversation history)
- [x] Implementation changes (async node with lazy imports)
- [x] Observability: add structured log line
  `RAG STEP 34 (RAG.routing.llm_router) step_034a_llm_router.enter | attrs={query_length}`
  `RAG STEP 34 (RAG.routing.llm_router) step_034a_llm_router.exit | attrs={route, confidence, needs_retrieval}`
- [x] Feature flag / config if needed (router service has model configuration)
- [x] Rollout plan (implemented with fallback safety)

## Done When
- Tests pass; latency acceptable (<500ms p99); fallback verified.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag_hybrid.mmd`
- Step registry: `docs/architecture/rag_steps.yml`
- Task: DEV-194 in `docs/tasks/PRATIKO_1.5.md`
- Related ADR: `docs/adr/ADR-024-proactivity-pre-post-response.md`


<!-- AUTO-AUDIT:BEGIN -->
Role: External  |  Status: 🔌 (Implemented)  |  Registry: ✅ In diagram

Notes:
- ✅ LangGraph node wrapper
- ✅ TDD tests: 14 tests in tests/langgraph/agentic_rag/test_step_034a__llm_router.py
- ✅ Fallback to TECHNICAL_RESEARCH on service errors
<!-- AUTO-AUDIT:END -->
