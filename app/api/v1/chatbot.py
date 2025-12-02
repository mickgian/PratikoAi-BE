"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import llm_stream_duration_seconds
from app.core.privacy.anonymizer import anonymizer
from app.core.privacy.gdpr import (
    DataCategory,
    ProcessingPurpose,
    gdpr_compliance,
)
from app.core.sse_formatter import (
    format_sse_done,
    format_sse_event,
)
from app.core.sse_write import (
    log_sse_summary,
    write_sse,
)
from app.core.streaming_guard import SinglePassStream
from app.models.session import Session
from app.observability.rag_logging import rag_step_log
from app.observability.rag_trace import rag_trace_context
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.services.chat_history_service import chat_history_service

router = APIRouter()
agent = LangGraphAgent()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Extract user query for trace metadata (before anonymization)
        user_query = chat_request.messages[-1].content if chat_request.messages else "N/A"

        # Wrap entire request processing with RAG trace context (dev/staging only)
        with rag_trace_context(request_id=str(session.id), user_query=user_query):
            # Step 1: User submits query (entry point)
            rag_step_log(
                step=1,
                step_id="RAG.platform.chatbotcontroller.chat.user.submits.query",
                node_label="Start",
                processing_stage="received",
                session_id=session.id,
                user_id=session.user_id,
                message_count=len(chat_request.messages),
                query_preview=user_query[:100] if user_query else "N/A",
            )

            # Step 2: Validate request and authenticate
            rag_step_log(
                step=2,
                step_id="RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
                node_label="ValidateRequest",
                processing_stage="completed",
                session_id=session.id,
                user_id=session.user_id,
            )

            # Step 3: Request valid? (decision point)
            # At this point, request passed validation
            logger.info("EXECUTING STEP 3 - Request Valid Check", session_id=session.id)
            rag_step_log(
                step=3,
                step_id="RAG.platform.request.valid.check",
                node_label="ValidCheck",
                processing_stage="decision",
                session_id=session.id,
                user_id=session.user_id,
                decision_result="Yes",  # Request is valid if we reached this point
            )
            logger.info("COMPLETED STEP 3 - Request Valid Check", session_id=session.id)

            # Record data processing for GDPR compliance
            gdpr_compliance.data_processor.record_processing(
                user_id=session.user_id,
                data_category=DataCategory.CONTENT,
                processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
                data_source="chat_api",
                legal_basis="Service provision under contract",
                anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
            )

            # Step 4: GDPR log
            rag_step_log(
                step=4,
                step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                node_label="GDPRLog",
                processing_stage="completed",
                session_id=session.id,
                user_id=session.user_id,
            )

            # Step 6: PRIVACY_ANONYMIZE_REQUESTS enabled? (decision point)
            rag_step_log(
                step=6,
                step_id="RAG.privacy.privacy.anonymize.requests.enabled",
                node_label="PrivacyCheck",
                processing_stage="decision",
                session_id=session.id,
                user_id=session.user_id,
                decision_result="Yes" if settings.PRIVACY_ANONYMIZE_REQUESTS else "No",
            )

            # Anonymize request if privacy settings require it
            processed_messages = chat_request.messages
            if settings.PRIVACY_ANONYMIZE_REQUESTS:
                processed_messages = []
                for message in chat_request.messages:
                    anonymization_result = anonymizer.anonymize_text(message.content)

                    # Step 7: Anonymize PII
                    rag_step_log(
                        step=7,
                        step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
                        node_label="AnonymizeText",
                        processing_stage="completed",
                        session_id=session.id,
                        pii_detected=len(anonymization_result.pii_matches) > 0,
                    )

                    # Step 9: PII detected? (decision point)
                    pii_detected = len(anonymization_result.pii_matches) > 0
                    rag_step_log(
                        step=9,
                        step_id="RAG.privacy.pii.detected.check",
                        node_label="PIICheck",
                        processing_stage="decision",
                        session_id=session.id,
                        decision_result="Yes" if pii_detected else "No",
                        pii_count=len(anonymization_result.pii_matches),
                    )

                    processed_messages.append(Message(role=message.role, content=anonymization_result.anonymized_text))

                    if anonymization_result.pii_matches:
                        logger.info(
                            "chat_request_pii_anonymized",
                            session_id=session.id,
                            pii_types=[match.pii_type.value for match in anonymization_result.pii_matches],
                            pii_count=len(anonymization_result.pii_matches),
                        )

                        # Step 10: Log PII anonymization
                        rag_step_log(
                            step=10,
                            step_id="RAG.platform.logger.info.log.pii.anonymization",
                            node_label="LogPII",
                            processing_stage="completed",
                            session_id=session.id,
                            pii_count=len(anonymization_result.pii_matches),
                        )

            logger.info(
                "chat_request_received",
                session_id=session.id,
                message_count=len(processed_messages),
                anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
            )

            result = await agent.get_response(processed_messages, session.id, user_id=session.user_id)

            logger.info("chat_request_processed", session_id=session.id)

            # Save chat interaction to database for multi-device sync and GDPR compliance
            try:
                # Extract user query (last user message)
                user_query = next((msg.content for msg in reversed(processed_messages) if msg.type == "user"), None)

                # Extract AI response (last AI message)
                ai_response = next((msg.content for msg in reversed(result) if msg.type == "ai"), None)

                # Validate both query and response are non-empty before saving
                if user_query and user_query.strip() and ai_response and ai_response.strip():
                    await chat_history_service.save_chat_interaction(
                        user_id=session.user_id,
                        session_id=session.id,
                        user_query=user_query.strip(),
                        ai_response=ai_response.strip(),
                        model_used="gpt-4-turbo",  # TODO: Get from agent/LLM provider
                        italian_content=True,  # TODO: Detect from query content
                    )
            except Exception as save_error:
                # Log error but don't fail the request (degraded functionality)
                logger.error(
                    "chat_history_save_failed_non_critical",
                    session_id=session.id,
                    error=str(save_error),
                    exc_info=True,
                )

            return ChatResponse(messages=result)
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Record data processing for GDPR compliance (outer function)
        gdpr_compliance.data_processor.record_processing(
            user_id=session.user_id,
            data_category=DataCategory.CONTENT,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="chat_stream_api",
            legal_basis="Service provision under contract",
            anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
        )

        # Anonymize request if privacy settings require it (outer function)
        processed_messages = chat_request.messages
        pii_detected_count = 0
        if settings.PRIVACY_ANONYMIZE_REQUESTS:
            processed_messages = []
            for message in chat_request.messages:
                anonymization_result = anonymizer.anonymize_text(message.content)

                processed_messages.append(Message(role=message.role, content=anonymization_result.anonymized_text))

                if anonymization_result.pii_matches:
                    pii_detected_count = len(anonymization_result.pii_matches)
                    logger.info(
                        "stream_chat_request_pii_anonymized",
                        session_id=session.id,
                        pii_types=[match.pii_type.value for match in anonymization_result.pii_matches],
                        pii_count=len(anonymization_result.pii_matches),
                    )

        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(processed_messages),
            anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
        )

        # Use session.id as request_id for tracking SSE writes
        request_id = str(session.id)

        # Extract user query for trace metadata (before anonymization for readability)
        user_query = chat_request.messages[-1].content if chat_request.messages else "N/A"

        async def event_generator():
            """Generate streaming events with pure markdown output and deduplication.

            Yields:
                str: Server-sent events with markdown content.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                # Wrap streaming with RAG trace context (dev/staging only)
                with rag_trace_context(request_id=request_id, user_query=user_query):
                    # Log Steps 1, 2, 4, 7, 10 inside trace context (completed in outer function)
                    # Step 1: User submits query (entry point)
                    rag_step_log(
                        step=1,
                        step_id="RAG.platform.chatbotcontroller.chat.user.submits.query",
                        node_label="Start",
                        processing_stage="received",
                        session_id=session.id,
                        user_id=session.user_id,
                        message_count=len(processed_messages),
                        query_preview=user_query[:100] if user_query else "N/A",
                    )

                    # Step 2: Validate request and authenticate
                    rag_step_log(
                        step=2,
                        step_id="RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate",
                        node_label="ValidateRequest",
                        processing_stage="completed",
                        session_id=session.id,
                        user_id=session.user_id,
                    )

                    # Step 3: Request valid? (decision point)
                    rag_step_log(
                        step=3,
                        step_id="RAG.platform.request.valid.check",
                        node_label="ValidCheck",
                        processing_stage="decision",
                        session_id=session.id,
                        user_id=session.user_id,
                        decision_result="Yes",  # Request is valid if we reached this point
                    )

                    # Step 4: GDPR log
                    rag_step_log(
                        step=4,
                        step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                        node_label="GDPRLog",
                        processing_stage="completed",
                        session_id=session.id,
                        user_id=session.user_id,
                    )

                    # Step 6: PRIVACY_ANONYMIZE_REQUESTS enabled? (decision point)
                    rag_step_log(
                        step=6,
                        step_id="RAG.privacy.privacy.anonymize.requests.enabled",
                        node_label="PrivacyCheck",
                        processing_stage="decision",
                        session_id=session.id,
                        user_id=session.user_id,
                        decision_result="Yes" if settings.PRIVACY_ANONYMIZE_REQUESTS else "No",
                    )

                    # Step 7: Anonymize PII (log for each processed message)
                    if settings.PRIVACY_ANONYMIZE_REQUESTS:
                        rag_step_log(
                            step=7,
                            step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
                            node_label="AnonymizeText",
                            processing_stage="completed",
                            session_id=session.id,
                            pii_detected=pii_detected_count > 0,
                        )

                        # Step 9: PII detected? (decision point)
                        rag_step_log(
                            step=9,
                            step_id="RAG.privacy.pii.detected.check",
                            node_label="PIICheck",
                            processing_stage="decision",
                            session_id=session.id,
                            decision_result="Yes" if pii_detected_count > 0 else "No",
                            pii_count=pii_detected_count,
                        )

                    # Step 10: Log PII anonymization (if PII was detected)
                    if pii_detected_count > 0:
                        rag_step_log(
                            step=10,
                            step_id="RAG.platform.logger.info.log.pii.anonymization",
                            node_label="LogPII",
                            processing_stage="completed",
                            session_id=session.id,
                            pii_count=pii_detected_count,
                        )

                    # Step 8: InitAgent - Transition to LangGraph workflow
                    rag_step_log(
                        step=8,
                        step_id="RAG.langgraphagent.get.response.initialize.workflow",
                        node_label="InitAgent",
                        processing_stage="started",
                        session_id=session.id,
                        user_id=session.user_id,
                        previous_step=10 if pii_detected_count > 0 else 7,
                        transition=f"Step {10 if pii_detected_count > 0 else 7} → Step 8",
                        message_count=len(processed_messages),
                        streaming_requested=True,
                    )

                    # Collect response chunks for chat history (non-blocking save after streaming)
                    collected_response_chunks = []
                    # Track if response came from golden set (for model_used in chat history)
                    golden_hit = False

                    with llm_stream_duration_seconds.labels(model="llm").time():
                        # Wrap the original stream to prevent double iteration
                        original_stream = SinglePassStream(
                            agent.get_stream_response(processed_messages, session.id, user_id=session.user_id)
                        )

                        async for chunk in original_stream:
                            if chunk:
                                # ============================================================================
                                # SSE Comment vs Content Distinction
                                # ============================================================================
                                # The graph yields two types of chunks:
                                #
                                # 1. SSE COMMENTS (Keepalives):
                                #    Format: ": <text>\n\n"
                                #    Example: ": starting\n\n"
                                #    Purpose: Establish connection immediately during blocking operations
                                #    Must be: colon + SPACE + text + double newline
                                #    Frontend: Skips these (api.ts:788)
                                #
                                # 2. CONTENT CHUNKS:
                                #    Format: Plain text strings (no SSE formatting)
                                #    Example: "Ecco le informazioni richieste..."
                                #    Purpose: Actual response content from LLM
                                #    Must be: Wrapped as SSE data events for frontend
                                #    Frontend: Parses as data: {...}\n\n format
                                #
                                # CRITICAL: Content that happens to start with ":" (e.g., ": Ecco...")
                                # is NOT an SSE comment. It must be wrapped as normal content.
                                # SSE comments MUST have ": " (colon-space) AND "\n\n" (double newline).
                                #
                                # If we incorrectly treat content as SSE comment:
                                # - Content gets yielded without data: {...}\n\n wrapper
                                # - Frontend receives malformed SSE format
                                # - Frontend strict parser (api.ts:794-797) errors and stops all processing
                                # - User sees "Sto pensando..." forever (STUCK)
                                # ============================================================================

                                # Check if this is an SSE comment (keepalive) using strict format check
                                is_sse_comment = chunk.startswith(": ") and chunk.endswith("\n\n")

                                if is_sse_comment:
                                    # This is an SSE keepalive comment (e.g., ": starting\n\n")
                                    # Pass through unchanged - frontend will skip it (api.ts:788)
                                    yield chunk
                                elif chunk.startswith("__RESPONSE_METADATA__:"):
                                    # This is a metadata marker from graph.py (not content)
                                    # Extract golden_hit flag for chat history save
                                    # Format: __RESPONSE_METADATA__:golden_hit=True/False
                                    if "golden_hit=True" in chunk:
                                        golden_hit = True
                                    # Don't yield or collect - this is internal metadata
                                else:
                                    # This is regular content (plain text string from graph)
                                    # Collect chunk for chat history
                                    collected_response_chunks.append(chunk)
                                    # Wrap as proper SSE data event: data: {"content":"...","done":false}\n\n
                                    # Frontend expects this format (api.ts:756-784)
                                    stream_response = StreamResponse(content=chunk, done=False)
                                    sse_event = format_sse_event(stream_response)
                                    yield write_sse(None, sse_event, request_id=request_id)

                    # Send final done frame using validated formatter
                    sse_done = format_sse_done()
                    yield write_sse(None, sse_done, request_id=request_id)

                    # Log aggregated statistics for this streaming session
                    log_sse_summary(request_id=request_id)

                    # Save chat history (non-blocking, after streaming completes)
                    if collected_response_chunks:
                        try:
                            ai_response = "".join(collected_response_chunks)
                            # Validate both query and response are non-empty before saving
                            if user_query and user_query.strip() and ai_response and ai_response.strip():
                                # Use "golden_set" if response came from Golden Set FAQ,
                                # otherwise use the LLM model identifier
                                model_used = "golden_set" if golden_hit else "gpt-4-turbo"
                                await chat_history_service.save_chat_interaction(
                                    user_id=session.user_id,
                                    session_id=session.id,
                                    user_query=user_query.strip(),
                                    ai_response=ai_response.strip(),
                                    model_used=model_used,
                                    italian_content=True,  # TODO: Detect from query content
                                )
                        except Exception as save_error:
                            # Log error but don't fail the stream (degraded functionality)
                            logger.error(
                                "chat_history_save_failed_streaming_non_critical",
                                session_id=session.id,
                                error=str(save_error),
                                exc_info=True,
                            )

            except RuntimeError as re:
                if "iterated twice" in str(re):
                    logger.error(f"CRITICAL: Stream iterated twice - session: {session.id}", exc_info=True)
                # Still log summary even on error
                log_sse_summary(request_id=request_id)
                raise
            except Exception as e:
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"
                # Log summary even on error
                log_sse_summary(request_id=request_id)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Get all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """Clear all messages for a session.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_history(
    request: Request,
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_current_session),
):
    """Retrieve chat history for a specific session (PostgreSQL-backed).

    Args:
        request: The FastAPI request object for rate limiting.
        session_id: ID of the session to retrieve history for.
        limit: Maximum number of messages to return (default: 100).
        offset: Number of messages to skip for pagination (default: 0).
        session: The current authenticated session.

    Returns:
        list[dict]: List of chat messages with metadata.

    Raises:
        HTTPException: If user is not authorized or if there's an error.
    """
    try:
        # Authorization: User can only access their own sessions
        if session.id != session_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this session",
            )

        # Retrieve history from PostgreSQL
        messages = await chat_history_service.get_session_history(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_session_history_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-history")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def import_chat_history(
    request: Request,
    import_data: dict,
    session: Session = Depends(get_current_session),
):
    """Import chat history from IndexedDB (client-side migration).

    Args:
        request: The FastAPI request object for rate limiting.
        import_data: Dict containing 'messages' array with chat history.
        session: The current authenticated session.

    Returns:
        dict: Import results with imported_count and skipped_count.

    Raises:
        HTTPException: If there's a validation or processing error.
    """
    try:
        messages = import_data.get("messages", [])

        if not isinstance(messages, list):
            raise HTTPException(
                status_code=422,
                detail="import_data must contain 'messages' array",
            )

        imported_count = 0
        skipped_count = 0

        # Process messages in batch
        for msg in messages:
            try:
                # Validate required fields
                if not all(k in msg for k in ["session_id", "query", "response", "timestamp"]):
                    skipped_count += 1
                    continue

                # Save to database
                await chat_history_service.save_chat_interaction(
                    user_id=session.user_id,
                    session_id=msg["session_id"],
                    user_query=msg["query"],
                    ai_response=msg["response"],
                    model_used=msg.get("model_used"),
                    tokens_used=msg.get("tokens_used"),
                    cost_cents=msg.get("cost_cents"),
                    response_time_ms=msg.get("response_time_ms"),
                    response_cached=msg.get("response_cached", False),
                    italian_content=msg.get("italian_content", True),
                )
                imported_count += 1

            except Exception as save_error:
                logger.warning(
                    "import_message_skipped",
                    error=str(save_error),
                    message_preview=msg.get("query", "")[:100],
                )
                skipped_count += 1

        status = "success"
        if imported_count == 0 and skipped_count > 0:
            status = "failed"
        elif skipped_count > 0:
            status = "partial_success"

        logger.info(
            "chat_history_import_completed",
            user_id=session.user_id,
            imported_count=imported_count,
            skipped_count=skipped_count,
            status=status,
        )

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "status": status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "import_chat_history_failed",
            user_id=session.user_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
