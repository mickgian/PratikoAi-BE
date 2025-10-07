# RAG STEP 2 — User submits query via POST /api/v1/chat (RAG.platform.user.submits.query.via.post.api.v1.chat)

**Type:** startEnd  
**Category:** platform  
**Node ID:** `Start`

## Intent (Blueprint)
Describe the purpose of this step in the approved RAG. This step is derived from the Mermaid node: `Start` (User submits query via POST /api/v1/chat).

## Current Implementation (Repo)
- **Role:** Internal
- **Paths / classes:**
  - `app/api/v1/chatbot.py:40` - `@router.post("/chat")` (HTTP entry point)
  - `app/orchestrators/platform.py:179` - `step_2__start()` (orchestrator)
  - `app/core/langgraph/nodes/step_002__start.py:9` - `node_step_2()` (wrapper exists but not wired)
- **Status:** ✅ Implemented (Internal - NOT wired by design)
- **Behavior notes:**
  - **Why Internal?** This is the HTTP API entry point, not a graph node. The workflow starts at Step 1 (ValidateRequest), which is called by the FastAPI endpoint.
  - **Why NOT wired?** Step 2 represents the external API boundary (`POST /api/v1/chat`). It's the trigger that initiates the graph execution, not a node within the graph itself.
  - **Canonical Node Set:** Per `docs/architecture/RAG-architecture-mode.md`, the Request/Privacy lane promotes only steps 1, 3, 6, and 9 as runtime nodes. Step 2 remains Internal because it's pure infrastructure (HTTP → graph initialization).
  - The FastAPI endpoint receives the POST request, validates at the HTTP layer, then invokes the LangGraph workflow starting at node_step_1.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - uses existing platform infrastructure

## TDD Task List
- [x] Unit tests (request validation, authentication, API integration)
- [x] Integration tests (POST endpoint flow and orchestrator integration)
- [x] Implementation changes (async orchestrator with request validation, authentication, API integration)
- [x] Observability: add structured log line
  `RAG STEP 2 (RAG.platform.user.submits.query.via.post.api.v1.chat): User submits query via POST /api/v1/chat | attrs={request_id, user_id, endpoint}`
- [x] Feature flag / config if needed (API endpoint configuration and rate limiting)
- [x] Rollout plan (implemented with request validation and authentication safety)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Role: Internal  |  Status: ✅ Implemented (NOT wired by design)  |  Confidence: 1.00

Top candidates:
1. app/api/v1/chatbot.py:40 — @router.post("/chat") (score 1.00)
   Evidence: FastAPI endpoint - HTTP entry point for chat requests

2. app/orchestrators/platform.py:179 — step_2__start() (score 1.00)
   Evidence: Orchestrator implementation for request initialization

3. app/core/langgraph/nodes/step_002__start.py:9 — node_step_2() (score 1.00)
   Evidence: Node wrapper exists but intentionally not wired in graph registry

Notes:
- **Intentionally NOT wired:** Step 2 is the API entry point, not a graph node
- **Architecture decision:** External API boundaries remain Internal per canonical node set
- **Flow:** HTTP POST → FastAPI endpoint → LangGraph workflow starts at Step 1 (ValidateRequest)
- **Phase 6 scope:** Only steps 1, 3, 4, 6, 7, 8, 9, 10 are wired graph nodes
- Step 2 represents infrastructure (HTTP → graph trigger), not workflow logic

Why NOT wired:
- Graph nodes represent runtime boundaries with state isolation, retries, and observability
- API endpoints are external triggers that initiate graphs, not nodes within graphs
- Wiring Step 2 would create circular dependency (graph can't start itself)
- Per RAG-architecture-mode.md: "Request/Privacy lane promotes steps 1, 3, 6, 9 as nodes"

Suggested next TDD actions:
- Verify HTTP endpoint integration tests exist
- Confirm orchestrator unit tests cover request parsing
- Validate that Step 1 (ValidateRequest) is properly invoked by endpoint
<!-- AUTO-AUDIT:END -->