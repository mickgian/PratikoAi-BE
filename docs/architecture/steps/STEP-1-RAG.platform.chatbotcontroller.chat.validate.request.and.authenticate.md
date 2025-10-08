# RAG STEP 1 — ChatbotController.chat Validate request and authenticate (RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate)

**Type:** process  
**Category:** platform  
**Node ID:** `ValidateRequest`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `ValidateRequest` (ChatbotController.chat Validate request and authenticate).

## Current Implementation (Repo)
- **Role:** Node
- **Status:** ✅
- **Paths / classes:**
  - app/core/langgraph/nodes/step_001__validate_request.py:13 — node_step_1 (wrapper)
  - app/orchestrators/platform.py:16 (orchestrator)
- **Behavior notes:**
  - Runtime boundary; validates and authenticates; routes to ValidCheck.
  - Baseline neighbors: incoming=[], outgoing=['ValidCheck']; runtime_hits=0.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, error cases, routing logic)
- [x] Integration tests (Step 1→3→5 flows, authentication integration, validation error handling)
- [x] Implementation changes (async orchestrator with request validation and authentication)
- [x] Observability: add structured log line
  `RAG STEP 1 (RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate): ChatbotController.chat Validate request and authenticate | attrs={validation_successful, authentication_successful, request_valid, processing_stage}`
- [x] Feature flag / config if needed (uses existing authentication configuration)
- [x] Rollout plan (implemented with comprehensive validation and error handling)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Node  |  Status: ✅ (Implemented & Wired)  |  Registry: ✅ Wired

Wiring information:
- Node name: node_step_1
- Incoming edges: none
- Outgoing edges: [3]

Notes:
- ✅ Node is wired in LangGraph runtime
<!-- AUTO-AUDIT:END -->