"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.
"""

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
)
from app.core.privacy.anonymizer import anonymizer
from app.core.privacy.gdpr import gdpr_compliance, ProcessingPurpose, DataCategory
from app.core.streaming_processor import EnhancedStreamingProcessor
from app.core.streaming_guard import SinglePassStream
from app.core.sse_write import write_sse

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
        # Record data processing for GDPR compliance
        gdpr_compliance.data_processor.record_processing(
            user_id=session.user_id,
            data_category=DataCategory.CONTENT,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="chat_api",
            legal_basis="Service provision under contract",
            anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS
        )
        
        # Anonymize request if privacy settings require it
        processed_messages = chat_request.messages
        if settings.PRIVACY_ANONYMIZE_REQUESTS:
            processed_messages = []
            for message in chat_request.messages:
                anonymization_result = anonymizer.anonymize_text(message.content)
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
        # Record data processing for GDPR compliance
        gdpr_compliance.data_processor.record_processing(
            user_id=session.user_id,
            data_category=DataCategory.CONTENT,
            processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
            data_source="chat_stream_api",
            legal_basis="Service provision under contract",
            anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS
        )
        
        # Anonymize request if privacy settings require it
        processed_messages = chat_request.messages
        if settings.PRIVACY_ANONYMIZE_REQUESTS:
            processed_messages = []
            for message in chat_request.messages:
                anonymization_result = anonymizer.anonymize_text(message.content)
                processed_messages.append(Message(
                    role=message.role,
                    content=anonymization_result.anonymized_text
                ))
                
                if anonymization_result.pii_matches:
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

        async def event_generator():
            """Generate streaming events with pure HTML output and deduplication.

            Yields:
                str: Server-sent events with HTML-only content.

            Raises:
                Exception: If there's an error during streaming.
            """
            # Create processor with session ID for tracking
            processor = EnhancedStreamingProcessor(stream_id=session.id)
            
            try:
                with llm_stream_duration_seconds.labels(model="llm").time():
                    # Wrap the original stream to prevent double iteration
                    original_stream = SinglePassStream(agent.get_stream_response(
                        processed_messages, session.id, user_id=session.user_id
                    ))
                    
                    async for chunk in original_stream:
                        # Process chunk through enhanced processor
                        html_delta = await processor.process_chunk(chunk)
                        if html_delta:
                            # Only emit if there's new content
                            frame = processor.format_sse_frame(content=html_delta, done=False)
                            # Log and yield what we're sending
                            yield write_sse(None, frame)

                # Send final frame with done=true and no content
                final_frame = processor.format_sse_frame(done=True)
                yield write_sse(None, final_frame)
                
                # Log final stats
                processor.finalize()

            except RuntimeError as re:
                if "iterated twice" in str(re):
                    logger.error(
                        f"CRITICAL: Stream iterated twice - session: {session.id}",
                        exc_info=True
                    )
                raise
            except Exception as e:
                stats = processor.get_stats()
                logger.error(
                    f"stream_chat_request_failed - session: {session.id}, error: {str(e)}, "
                    f"stats: frames={stats['total_frames']}, bytes={stats['total_bytes_emitted']}",
                    exc_info=True
                )
                # Send error done frame
                error_frame = processor.format_sse_frame(done=True)
                yield write_sse(None, error_frame)

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
