# RAG STEP 108 — write_sse Format chunks (RAG.streaming.write.sse.format.chunks)

**Type:** process
**Category:** streaming
**Node ID:** `WriteSSE`

## Intent (Blueprint)
Formats streaming chunks into Server-Sent Events (SSE) format using the write_sse function. Transforms protected async generator streams into proper SSE format for browser consumption. Essential step that bridges stream protection to streaming response delivery, enabling proper SSE formatting with logging and error handling. Routes from SinglePass (Step 107) to StreamingResponse (Step 109). This step is derived from the Mermaid node: `WriteSSE` (write_sse Format chunks).

## Current Implementation (Repo)
- **Paths / classes:** `app/orchestrators/streaming.py:step_108__write_sse`
- **Status:** ✅ Implemented
- **Behavior notes:** Async orchestrator that formats streaming chunks into SSE format using the existing write_sse function. Creates SSE-formatted generator, configures formatting options, and validates requirements. Routes to StreamingResponse (Step 109) with properly formatted SSE stream ready for delivery.

## Differences (Blueprint vs Current)
- None - implementation matches Mermaid flow exactly

## Risks / Impact
- None - thin orchestrator preserving existing write_sse formatting logic

## TDD Task List
- [x] Unit tests (SSE formatting, configuration settings, complex chunks, context preservation, metadata addition, validation requirements, SSE options, stream errors, formatting parameters, logging)
- [x] Parity tests (SSE formatting behavior verification)
- [x] Integration tests (SinglePass→WriteSSE→StreamingResponse flow, error handling)
- [x] Implementation changes (async SSE formatting orchestrator)
- [x] Observability: add structured log line
  `RAG STEP 108 (RAG.streaming.write.sse.format.chunks): write_sse Format chunks | attrs={step, request_id, chunks_formatted, format_configured, next_step, processing_stage}`
- [x] Feature flag / config if needed (none required - uses existing write_sse infrastructure)
- [x] Rollout plan (implemented with comprehensive tests)

## Done When
- Tests pass; metrics/latency acceptable; feature behind flag if risky.

## Links
- RAG Diagram: `docs/architecture/diagrams/pratikoai_rag.mmd`
- Step registry: `docs/architecture/rag_steps.yml`


<!-- AUTO-AUDIT:BEGIN -->
Status: ✅  |  Confidence: 1.00

Implementation:
- app/orchestrators/streaming.py:290 — step_108__write_sse (async orchestrator)
- app/orchestrators/streaming.py:350 — _create_sse_formatted_generator (helper function)
- app/orchestrators/streaming.py:391 — _prepare_sse_format_configuration (helper function)
- app/orchestrators/streaming.py:450 — _validate_sse_format_requirements (helper function)
- app/core/sse_write.py:15 — write_sse (core SSE formatting function)
- tests/test_rag_step_108_write_sse.py — 15 comprehensive tests (all passing)

Key Features:
- Async SSE formatting orchestrator with write_sse integration
- Formats streaming chunks into proper Server-Sent Events format
- Creates SSE-formatted generator with browser-compatible output
- Formatting configuration with session data and provider settings
- Complex chunk handling (dictionaries, strings, structured data)
- Stream requirements validation with comprehensive warning system
- Structured logging with rag_step_log (step 108, formatting tracking)
- Context preservation (user/session data, protection config, processing history)
- Formatting metadata addition (config, timestamps, validation results)
- Error recovery and graceful handling of stream errors

Test Coverage:
- Unit: SSE formatting, configuration settings, complex chunks, context preservation, metadata addition, validation requirements, SSE options, stream errors, formatting parameters, logging
- Parity: SSE formatting behavior verification
- Integration: SinglePass→WriteSSE→StreamingResponse flow, error handling

SSE Format Configuration:
- Uses existing write_sse function from app/core/sse_write.py
- Formats chunks as "data: {content}\n\n" for browser consumption
- Handles structured data, strings, and [DONE] termination signals
- Session and user context with provider/model settings
- Event type, retry interval, and connection management settings
- Formatting options (JSON, timestamps, escaping, chunk limits)

write_sse Integration:
- Leverages existing app/core/sse_write.py:write_sse function
- Maintains SSE logging and debugging capabilities
- Compatible with existing chatbot streaming implementation
- Preserves SSE frame formatting and error handling

Notes:
- Full implementation complete following MASTER_GUARDRAILS
- Thin orchestrator pattern (coordination only)
- All TDD tasks completed
- Critical bridge from stream protection to streaming response delivery
<!-- AUTO-AUDIT:END -->