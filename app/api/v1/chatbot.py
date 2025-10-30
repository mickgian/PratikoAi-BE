"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

import json
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse
from app.core.metrics import llm_stream_duration_seconds
from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.core.privacy.anonymizer import anonymizer
from app.core.privacy.gdpr import gdpr_compliance, ProcessingPurpose, DataCategory
from app.core.streaming_guard import SinglePassStream
from app.core.sse_write import write_sse, log_sse_summary
from app.observability.rag_trace import rag_trace_context
from app.observability.rag_logging import rag_step_log

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
                step_id='RAG.platform.chatbotcontroller.chat.user.submits.query',
                node_label='Start',
                processing_stage='received',
                session_id=session.id,
                user_id=session.user_id,
                message_count=len(chat_request.messages),
                query_preview=user_query[:100] if user_query else "N/A"
            )

            # Step 2: Validate request and authenticate
            rag_step_log(
                step=2,
                step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                node_label='ValidateRequest',
                processing_stage='completed',
                session_id=session.id,
                user_id=session.user_id
            )

            # Step 3: Request valid? (decision point)
            request_valid = True  # At this point, request passed validation
            logger.info("EXECUTING STEP 3 - Request Valid Check", session_id=session.id)
            rag_step_log(
                step=3,
                step_id='RAG.platform.request.valid.check',
                node_label='ValidCheck',
                processing_stage='decision',
                session_id=session.id,
                user_id=session.user_id,
                decision_result='Yes'  # Request is valid if we reached this point
            )
            logger.info("COMPLETED STEP 3 - Request Valid Check", session_id=session.id)

            # Record data processing for GDPR compliance
            gdpr_compliance.data_processor.record_processing(
                user_id=session.user_id,
                data_category=DataCategory.CONTENT,
                processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
                data_source="chat_api",
                legal_basis="Service provision under contract",
                anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS
            )

            # Step 4: GDPR log
            rag_step_log(
                step=4,
                step_id='RAG.privacy.gdprcompliance.record.processing.log.data.processing',
                node_label='GDPRLog',
                processing_stage='completed',
                session_id=session.id,
                user_id=session.user_id
            )

            # Step 6: PRIVACY_ANONYMIZE_REQUESTS enabled? (decision point)
            rag_step_log(
                step=6,
                step_id='RAG.privacy.privacy.anonymize.requests.enabled',
                node_label='PrivacyCheck',
                processing_stage='decision',
                session_id=session.id,
                user_id=session.user_id,
                decision_result='Yes' if settings.PRIVACY_ANONYMIZE_REQUESTS else 'No'
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
                        step_id='RAG.privacy.anonymizer.anonymize.text.anonymize.pii',
                        node_label='AnonymizeText',
                        processing_stage='completed',
                        session_id=session.id,
                        pii_detected=len(anonymization_result.pii_matches) > 0
                    )

                    # Step 9: PII detected? (decision point)
                    pii_detected = len(anonymization_result.pii_matches) > 0
                    rag_step_log(
                        step=9,
                        step_id='RAG.privacy.pii.detected.check',
                        node_label='PIICheck',
                        processing_stage='decision',
                        session_id=session.id,
                        decision_result='Yes' if pii_detected else 'No',
                        pii_count=len(anonymization_result.pii_matches)
                    )

                    processed_messages.append(Message(
                        role=message.role,
                        content=anonymization_result.anonymized_text
                    ))

                    if anonymization_result.pii_matches:
                        logger.info(
                            "chat_request_pii_anonymized",
                            session_id=session.id,
                            pii_types=[match.pii_type.value for match in anonymization_result.pii_matches],
                            pii_count=len(anonymization_result.pii_matches)
                        )

                        # Step 10: Log PII anonymization
                        rag_step_log(
                            step=10,
                            step_id='RAG.platform.logger.info.log.pii.anonymization',
                            node_label='LogPII',
                            processing_stage='completed',
                            session_id=session.id,
                            pii_count=len(anonymization_result.pii_matches)
                        )

            logger.info(
                "chat_request_received",
                session_id=session.id,
                message_count=len(processed_messages),
                anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
            )

            result = await agent.get_response(
                processed_messages, session.id, user_id=session.user_id
            )

            logger.info("chat_request_processed", session_id=session.id)

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
            anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS
        )

        # Anonymize request if privacy settings require it (outer function)
        processed_messages = chat_request.messages
        pii_detected_count = 0
        if settings.PRIVACY_ANONYMIZE_REQUESTS:
            processed_messages = []
            for message in chat_request.messages:
                anonymization_result = anonymizer.anonymize_text(message.content)

                processed_messages.append(Message(
                    role=message.role,
                    content=anonymization_result.anonymized_text
                ))

                if anonymization_result.pii_matches:
                    pii_detected_count = len(anonymization_result.pii_matches)
                    logger.info(
                        "stream_chat_request_pii_anonymized",
                        session_id=session.id,
                        pii_types=[match.pii_type.value for match in anonymization_result.pii_matches],
                        pii_count=len(anonymization_result.pii_matches)
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
                        step_id='RAG.platform.chatbotcontroller.chat.user.submits.query',
                        node_label='Start',
                        processing_stage='received',
                        session_id=session.id,
                        user_id=session.user_id,
                        message_count=len(processed_messages),
                        query_preview=user_query[:100] if user_query else "N/A"
                    )

                    # Step 2: Validate request and authenticate
                    rag_step_log(
                        step=2,
                        step_id='RAG.platform.chatbotcontroller.chat.validate.request.and.authenticate',
                        node_label='ValidateRequest',
                        processing_stage='completed',
                        session_id=session.id,
                        user_id=session.user_id
                    )

                    # Step 3: Request valid? (decision point)
                    rag_step_log(
                        step=3,
                        step_id='RAG.platform.request.valid.check',
                        node_label='ValidCheck',
                        processing_stage='decision',
                        session_id=session.id,
                        user_id=session.user_id,
                        decision_result='Yes'  # Request is valid if we reached this point
                    )

                    # Step 4: GDPR log
                    rag_step_log(
                        step=4,
                        step_id='RAG.privacy.gdprcompliance.record.processing.log.data.processing',
                        node_label='GDPRLog',
                        processing_stage='completed',
                        session_id=session.id,
                        user_id=session.user_id
                    )

                    # Step 6: PRIVACY_ANONYMIZE_REQUESTS enabled? (decision point)
                    rag_step_log(
                        step=6,
                        step_id='RAG.privacy.privacy.anonymize.requests.enabled',
                        node_label='PrivacyCheck',
                        processing_stage='decision',
                        session_id=session.id,
                        user_id=session.user_id,
                        decision_result='Yes' if settings.PRIVACY_ANONYMIZE_REQUESTS else 'No'
                    )

                    # Step 7: Anonymize PII (log for each processed message)
                    if settings.PRIVACY_ANONYMIZE_REQUESTS:
                        rag_step_log(
                            step=7,
                            step_id='RAG.privacy.anonymizer.anonymize.text.anonymize.pii',
                            node_label='AnonymizeText',
                            processing_stage='completed',
                            session_id=session.id,
                            pii_detected=pii_detected_count > 0
                        )

                        # Step 9: PII detected? (decision point)
                        rag_step_log(
                            step=9,
                            step_id='RAG.privacy.pii.detected.check',
                            node_label='PIICheck',
                            processing_stage='decision',
                            session_id=session.id,
                            decision_result='Yes' if pii_detected_count > 0 else 'No',
                            pii_count=pii_detected_count
                        )

                    # Step 10: Log PII anonymization (if PII was detected)
                    if pii_detected_count > 0:
                        rag_step_log(
                            step=10,
                            step_id='RAG.platform.logger.info.log.pii.anonymization',
                            node_label='LogPII',
                            processing_stage='completed',
                            session_id=session.id,
                            pii_count=pii_detected_count
                        )

                    # Step 8: InitAgent - Transition to LangGraph workflow
                    rag_step_log(
                        step=8,
                        step_id='RAG.langgraphagent.get.response.initialize.workflow',
                        node_label='InitAgent',
                        processing_stage='started',
                        session_id=session.id,
                        user_id=session.user_id,
                        previous_step=10 if pii_detected_count > 0 else 7,
                        transition=f"Step {10 if pii_detected_count > 0 else 7} → Step 8",
                        message_count=len(processed_messages),
                        streaming_requested=True
                    )

                    with llm_stream_duration_seconds.labels(model="llm").time():
                        # Wrap the original stream to prevent double iteration
                        original_stream = SinglePassStream(agent.get_stream_response(
                            processed_messages, session.id, user_id=session.user_id
                        ))

                        async for chunk in original_stream:
                            if chunk and chunk.strip():
                                # Format as proper SSE event
                                stream_response = StreamResponse(content=chunk, done=False)
                                sse_event = f"data: {stream_response.model_dump_json()}\n\n"
                                yield write_sse(None, sse_event, request_id=request_id)

                    # Send final done frame
                    done_response = StreamResponse(content="", done=True)
                    sse_done = f"data: {done_response.model_dump_json()}\n\n"
                    yield write_sse(None, sse_done, request_id=request_id)

                    # Log aggregated statistics for this streaming session
                    log_sse_summary(request_id=request_id)

            except RuntimeError as re:
                if "iterated twice" in str(re):
                    logger.error(
                        f"CRITICAL: Stream iterated twice - session: {session.id}",
                        exc_info=True
                    )
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
