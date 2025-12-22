"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.

DEV-158: Added ProactivityEngine integration for suggested actions and
interactive questions support.

DEV-162: Added analytics tracking for action clicks and question answers.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.database import get_db, get_sync_session
from app.models.session import Session
from app.observability.rag_logging import rag_step_log
from app.observability.rag_trace import rag_trace_context
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.schemas.proactivity import (
    Action,
    ActionExecuteRequest,
    ProactivityContext,
    ProactivityResult,
    QuestionAnswerRequest,
    QuestionAnswerResponse,
)
from app.services.action_template_service import ActionTemplateService
from app.services.atomic_facts_extractor import AtomicFactsExtractor
from app.services.attachment_resolver import (
    AttachmentNotFoundError,
    AttachmentOwnershipError,
    attachment_resolver,
)
from app.services.chat_history_service import chat_history_service
from app.services.proactivity_analytics_service import ProactivityAnalyticsService
from app.services.proactivity_engine import ProactivityEngine

router = APIRouter()
agent = LangGraphAgent()

# DEV-158: Singleton ProactivityEngine instance
_proactivity_engine: ProactivityEngine | None = None


def get_proactivity_engine() -> ProactivityEngine:
    """Get or create the ProactivityEngine singleton.

    Returns:
        ProactivityEngine: The singleton engine instance
    """
    global _proactivity_engine
    if _proactivity_engine is None:
        template_service = ActionTemplateService()
        template_service.load_templates()
        facts_extractor = AtomicFactsExtractor()
        _proactivity_engine = ProactivityEngine(
            template_service=template_service,
            facts_extractor=facts_extractor,
        )
    return _proactivity_engine


# DEV-160: Singleton ActionTemplateService instance
_template_service: ActionTemplateService | None = None


def get_template_service() -> ActionTemplateService:
    """Get or create the ActionTemplateService singleton.

    Returns:
        ActionTemplateService: The singleton service instance
    """
    global _template_service
    if _template_service is None:
        _template_service = ActionTemplateService()
        _template_service.load_templates()
    return _template_service


# =============================================================================
# DEV-162: Analytics Tracking Helpers
# =============================================================================

# Thread pool executor for fire-and-forget sync analytics writes
_analytics_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analytics")


def _track_action_click_sync(
    session_id: str,
    user_id: int | None,
    action: Action,
    domain: str,
    context_hash: str | None = None,
) -> None:
    """Run action click tracking synchronously in thread pool.

    Args:
        session_id: Session identifier
        user_id: User ID (None for anonymous users)
        action: The clicked Action object
        domain: Domain context (tax, labor, legal, etc.)
        context_hash: Optional hash for grouping similar contexts
    """
    try:
        with get_sync_session() as db_session:
            analytics_service = ProactivityAnalyticsService(db_session)
            analytics_service.track_action_click(
                session_id=session_id,
                user_id=user_id,
                action=action,
                domain=domain,
                context_hash=context_hash,
            )
    except Exception as e:
        logger.warning(
            "analytics_action_click_background_failed",
            session_id=session_id,
            error=str(e),
        )


def _track_question_answer_sync(
    session_id: str,
    user_id: int | None,
    question_id: str,
    option_id: str,
    custom_input: str | None = None,
) -> None:
    """Run question answer tracking synchronously in thread pool.

    Args:
        session_id: Session identifier
        user_id: User ID (None for anonymous users)
        question_id: ID of the answered question
        option_id: ID of the selected option
        custom_input: Custom text if "altro" was selected
    """
    try:
        with get_sync_session() as db_session:
            analytics_service = ProactivityAnalyticsService(db_session)
            analytics_service.track_question_answer(
                session_id=session_id,
                user_id=user_id,
                question_id=question_id,
                option_id=option_id,
                custom_input=custom_input,
            )
    except Exception as e:
        logger.warning(
            "analytics_question_answer_background_failed",
            session_id=session_id,
            error=str(e),
        )


async def track_action_click_async(
    session_id: str,
    user_id: int | None,
    action: Action,
    domain: str,
    context_hash: str | None = None,
) -> None:
    """Fire-and-forget async wrapper for action click tracking.

    Runs the sync analytics write in a thread pool to avoid blocking
    the endpoint response.

    Args:
        session_id: Session identifier
        user_id: User ID (None for anonymous users)
        action: The clicked Action object
        domain: Domain context (tax, labor, legal, etc.)
        context_hash: Optional hash for grouping similar contexts
    """
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _analytics_executor,
        _track_action_click_sync,
        session_id,
        user_id,
        action,
        domain,
        context_hash,
    )


async def track_question_answer_async(
    session_id: str,
    user_id: int | None,
    question_id: str,
    option_id: str,
    custom_input: str | None = None,
) -> None:
    """Fire-and-forget async wrapper for question answer tracking.

    Runs the sync analytics write in a thread pool to avoid blocking
    the endpoint response.

    Args:
        session_id: Session identifier
        user_id: User ID (None for anonymous users)
        question_id: ID of the answered question
        option_id: ID of the selected option
        custom_input: Custom text if "altro" was selected
    """
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _analytics_executor,
        _track_question_answer_sync,
        session_id,
        user_id,
        question_id,
        option_id,
        custom_input,
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """Process a chat request using LangGraph.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.
        db: Database session for attachment resolution.

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

            # Resolve file attachments if provided (DEV-007)
            resolved_attachments = None
            if chat_request.attachment_ids:
                try:
                    resolved_attachments = await attachment_resolver.resolve_attachments(
                        db=db,
                        attachment_ids=chat_request.attachment_ids,
                        user_id=session.user_id,  # DEV-007 Issue 7: Pass int directly
                    )
                    logger.info(
                        "attachments_resolved",
                        session_id=session.id,
                        attachment_count=len(resolved_attachments),
                        attachment_ids=[str(aid) for aid in chat_request.attachment_ids],
                    )
                except AttachmentNotFoundError as e:
                    logger.warning(
                        "attachment_not_found",
                        session_id=session.id,
                        error=str(e),
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"Documento allegato non trovato: {e.attachment_id}",
                    )
                except AttachmentOwnershipError as e:
                    logger.warning(
                        "attachment_ownership_denied",
                        session_id=session.id,
                        error=str(e),
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Non sei autorizzato ad accedere a questo documento allegato.",
                    )

            # Pass attachments to agent (will be injected into RAG state)
            result = await agent.get_response(
                processed_messages,
                session.id,
                user_id=session.user_id,
                attachments=resolved_attachments,
            )

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

            # DEV-158: Process proactivity for suggested actions and questions
            proactivity_result: ProactivityResult | None = None
            try:
                proactivity_engine = get_proactivity_engine()
                proactivity_context = ProactivityContext(
                    session_id=str(session.id),
                    domain="default",  # TODO: Get from classification when available
                    action_type=None,
                    document_type=None,
                )
                proactivity_result = proactivity_engine.process(
                    query=user_query if user_query else "",
                    context=proactivity_context,
                )
                logger.debug(
                    "proactivity_processed",
                    session_id=session.id,
                    action_count=len(proactivity_result.actions),
                    has_question=proactivity_result.question is not None,
                    processing_time_ms=proactivity_result.processing_time_ms,
                )
            except Exception as proactivity_error:
                # Graceful degradation: log warning but continue without actions
                logger.warning(
                    "proactivity_processing_failed_non_critical",
                    session_id=session.id,
                    error=str(proactivity_error),
                )
                proactivity_result = None

            # Build response with proactivity fields
            extracted_params = None
            if proactivity_result and proactivity_result.extraction_result:
                extracted_params = {p.name: p.value for p in proactivity_result.extraction_result.extracted}

            return ChatResponse(
                messages=result,
                suggested_actions=proactivity_result.actions if proactivity_result else None,
                interactive_question=proactivity_result.question if proactivity_result else None,
                extracted_params=extracted_params if extracted_params else None,
            )
    except Exception as e:
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    """Process a chat request using LangGraph with streaming response.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        session: The current session from the auth token.
        db: Database session for attachment resolution.

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

        # Resolve file attachments if provided (DEV-007)
        resolved_attachments = None
        if chat_request.attachment_ids:
            try:
                resolved_attachments = await attachment_resolver.resolve_attachments(
                    db=db,
                    attachment_ids=chat_request.attachment_ids,
                    user_id=session.user_id,  # DEV-007 Issue 7: Pass int directly
                )
                logger.info(
                    "stream_attachments_resolved",
                    session_id=session.id,
                    attachment_count=len(resolved_attachments),
                    attachment_ids=[str(aid) for aid in chat_request.attachment_ids],
                )
            except AttachmentNotFoundError as e:
                logger.warning(
                    "stream_attachment_not_found",
                    session_id=session.id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Documento allegato non trovato: {e.attachment_id}",
                )
            except AttachmentOwnershipError as e:
                logger.warning(
                    "stream_attachment_ownership_denied",
                    session_id=session.id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=403,
                    detail="Non sei autorizzato ad accedere a questo documento allegato.",
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

                    # Send progress event for attachment analysis (DEV-007)
                    if resolved_attachments:
                        # Send SSE keepalive/progress event for document analysis
                        yield ": Analisi documento in corso...\n\n"

                    with llm_stream_duration_seconds.labels(model="llm").time():
                        # Wrap the original stream to prevent double iteration
                        original_stream = SinglePassStream(
                            agent.get_stream_response(
                                processed_messages,
                                session.id,
                                user_id=session.user_id,
                                attachments=resolved_attachments,
                            )
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
                                    stream_response = StreamResponse(content=chunk, done=False, event_type="content")
                                    sse_event = format_sse_event(stream_response)
                                    yield write_sse(None, sse_event, request_id=request_id)

                    # DEV-159: Process proactivity after streaming, before done frame
                    proactivity_result: ProactivityResult | None = None
                    try:
                        proactivity_engine = get_proactivity_engine()
                        proactivity_context = ProactivityContext(
                            session_id=str(session.id),
                            domain="default",  # TODO: Get from classification when available
                            action_type=None,
                            document_type=None,
                        )
                        proactivity_result = proactivity_engine.process(
                            query=user_query if user_query else "",
                            context=proactivity_context,
                        )
                        logger.debug(
                            "streaming_proactivity_processed",
                            session_id=session.id,
                            action_count=len(proactivity_result.actions),
                            has_question=proactivity_result.question is not None,
                            processing_time_ms=proactivity_result.processing_time_ms,
                        )
                    except Exception as proactivity_error:
                        # Graceful degradation: log warning but continue
                        logger.warning(
                            "streaming_proactivity_processing_failed_non_critical",
                            session_id=session.id,
                            error=str(proactivity_error),
                        )
                        proactivity_result = None

                    # DEV-159: Yield proactivity events if available
                    if proactivity_result:
                        # Yield suggested_actions event if actions present
                        if proactivity_result.actions:
                            actions_data = [a.model_dump() for a in proactivity_result.actions]
                            extracted_params = None
                            if proactivity_result.extraction_result:
                                extracted_params = {
                                    p.name: p.value for p in proactivity_result.extraction_result.extracted
                                }
                            actions_event = StreamResponse(
                                content="",
                                event_type="suggested_actions",
                                suggested_actions=actions_data,
                                extracted_params=extracted_params,
                            )
                            yield write_sse(None, format_sse_event(actions_event), request_id=request_id)

                        # Yield interactive_question event if question present
                        if proactivity_result.question:
                            question_data = proactivity_result.question.model_dump()
                            question_event = StreamResponse(
                                content="",
                                event_type="interactive_question",
                                interactive_question=question_data,
                            )
                            yield write_sse(None, format_sse_event(question_event), request_id=request_id)

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
        # DEV-007 FIX: Add required user_id parameter
        messages = await chat_history_service.get_session_history(
            user_id=session.user_id,
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


# =============================================================================
# DEV-160: Action Execution Endpoint
# =============================================================================


@router.post("/actions/execute")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def execute_action(
    request: Request,
    action_request: ActionExecuteRequest,
    session: Session = Depends(get_current_session),
) -> ChatResponse:
    """Execute a suggested action - DEV-160.

    Takes an action_id from a suggested action, substitutes parameters
    in the prompt_template, and executes it as a chat query.

    Args:
        request: The FastAPI request object for rate limiting.
        action_request: The action execution request containing action_id,
                       optional parameters, and session_id.
        session: The current authenticated session.

    Returns:
        ChatResponse: The response from executing the action, with new
                     suggested actions for follow-up.

    Raises:
        HTTPException:
            - 400: If action_id is unknown or parameters are invalid
            - 500: If there's an internal error during execution
    """
    try:
        # Get template service and lookup action
        template_service = get_template_service()
        action = template_service.get_action_by_id(action_request.action_id)

        if action is None:
            logger.warning(
                "action_not_found",
                action_id=action_request.action_id,
                session_id=action_request.session_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Azione non valida",
            )

        # Generate prompt from template
        parameters = action_request.parameters or {}
        try:
            prompt = action.prompt_template.format(**parameters)
        except KeyError as e:
            missing_param = str(e).strip("'")
            logger.warning(
                "action_missing_parameter",
                action_id=action_request.action_id,
                missing_param=missing_param,
                session_id=action_request.session_id,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Parametro richiesto mancante: {missing_param}",
            )

        logger.info(
            "action_execution_started",
            action_id=action_request.action_id,
            action_label=action.label,
            session_id=action_request.session_id,
            user_id=session.user_id,
        )

        # Execute action as regular chat query
        response = await agent.get_response(
            session_id=action_request.session_id,
            user_id=session.user_id,
            query=prompt,
        )

        # Convert response to messages
        messages = [Message(role="assistant", content=str(response))]

        # Process proactivity for follow-up actions
        proactivity_result: ProactivityResult | None = None
        try:
            proactivity_engine = get_proactivity_engine()
            proactivity_context = ProactivityContext(
                session_id=action_request.session_id,
                domain="default",
                action_type=None,
                document_type=None,
            )
            proactivity_result = proactivity_engine.process(
                query=prompt,
                context=proactivity_context,
            )
        except Exception as proactivity_error:
            logger.warning(
                "action_proactivity_processing_failed",
                action_id=action_request.action_id,
                session_id=action_request.session_id,
                error=str(proactivity_error),
            )

        # Build response
        suggested_actions = None
        interactive_question = None
        extracted_params = None

        if proactivity_result:
            if proactivity_result.actions:
                suggested_actions = proactivity_result.actions
            if proactivity_result.question:
                interactive_question = proactivity_result.question
            if proactivity_result.extraction_result:
                extracted_params = {p.name: p.value for p in proactivity_result.extraction_result.extracted}

        logger.info(
            "action_execution_completed",
            action_id=action_request.action_id,
            session_id=action_request.session_id,
            new_actions_count=len(suggested_actions) if suggested_actions else 0,
        )

        # DEV-162: Fire-and-forget analytics tracking
        await track_action_click_async(
            session_id=action_request.session_id,
            user_id=session.user_id,
            action=action,
            domain="default",  # TODO: Get from proactivity context when available
            context_hash=None,
        )

        return ChatResponse(
            messages=messages,
            suggested_actions=suggested_actions,
            interactive_question=interactive_question,
            extracted_params=extracted_params,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "action_execution_failed",
            action_id=action_request.action_id,
            session_id=action_request.session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DEV-161: Question Answer Endpoint
# =============================================================================


@router.post("/questions/answer")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def answer_question(
    request: Request,
    answer_request: QuestionAnswerRequest,
    session: Session = Depends(get_current_session),
) -> QuestionAnswerResponse:
    """Process an answer to an interactive question - DEV-161.

    Handles both single-step and multi-step question flows.
    For multi-step flows, returns the next question.
    For terminal questions, processes the answer and returns a response.

    Args:
        request: The FastAPI request object for rate limiting.
        answer_request: The question answer request containing question_id,
                       selected_option, optional custom_input, and session_id.
        session: The current authenticated session.

    Returns:
        QuestionAnswerResponse: Either next question or answer with actions.

    Raises:
        HTTPException:
            - 400: If question_id, option_id is invalid, or custom input required but missing
            - 500: If there's an internal error during processing
    """
    try:
        # Get template service and lookup question
        template_service = get_template_service()
        question = template_service.get_question(answer_request.question_id)

        if question is None:
            logger.warning(
                "question_not_found",
                question_id=answer_request.question_id,
                session_id=answer_request.session_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Domanda non valida",
            )

        # Validate selected option
        selected_option = None
        for option in question.options:
            if option.id == answer_request.selected_option:
                selected_option = option
                break

        if selected_option is None:
            logger.warning(
                "option_not_found",
                question_id=answer_request.question_id,
                option_id=answer_request.selected_option,
                session_id=answer_request.session_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Opzione non valida",
            )

        # Check if custom input is required but missing
        if selected_option.requires_input and not answer_request.custom_input:
            logger.warning(
                "custom_input_required",
                question_id=answer_request.question_id,
                option_id=answer_request.selected_option,
                session_id=answer_request.session_id,
            )
            raise HTTPException(
                status_code=400,
                detail="Input personalizzato richiesto",
            )

        logger.info(
            "question_answer_processing",
            question_id=answer_request.question_id,
            option_id=answer_request.selected_option,
            has_custom_input=answer_request.custom_input is not None,
            session_id=answer_request.session_id,
            user_id=session.user_id,
        )

        # Check if this is a multi-step flow (option leads to next question)
        if selected_option.leads_to:
            next_question = template_service.get_question(selected_option.leads_to)
            if next_question:
                logger.info(
                    "question_flow_continuing",
                    from_question=answer_request.question_id,
                    to_question=selected_option.leads_to,
                    session_id=answer_request.session_id,
                )

                # DEV-162: Fire-and-forget analytics tracking for multi-step flow
                await track_question_answer_async(
                    session_id=answer_request.session_id,
                    user_id=session.user_id,
                    question_id=answer_request.question_id,
                    option_id=answer_request.selected_option,
                    custom_input=answer_request.custom_input,
                )

                return QuestionAnswerResponse(next_question=next_question)

        # Terminal question - generate prompt and get answer
        # Build prompt from question context and selected option
        prompt_parts = [question.text, f"Risposta selezionata: {selected_option.label}"]
        if answer_request.custom_input:
            prompt_parts.append(f"Input personalizzato: {answer_request.custom_input}")

        prompt = " ".join(prompt_parts)

        # Execute as chat query
        response = await agent.get_response(
            session_id=answer_request.session_id,
            user_id=session.user_id,
            query=prompt,
        )

        # Process proactivity for follow-up actions
        suggested_actions = None
        try:
            proactivity_engine = get_proactivity_engine()
            proactivity_context = ProactivityContext(
                session_id=answer_request.session_id,
                domain="default",
                action_type=None,
                document_type=None,
            )
            proactivity_result = proactivity_engine.process(
                query=prompt,
                context=proactivity_context,
            )
            if proactivity_result and proactivity_result.actions:
                suggested_actions = proactivity_result.actions
        except Exception as proactivity_error:
            logger.warning(
                "question_proactivity_processing_failed",
                question_id=answer_request.question_id,
                session_id=answer_request.session_id,
                error=str(proactivity_error),
            )

        logger.info(
            "question_answer_completed",
            question_id=answer_request.question_id,
            session_id=answer_request.session_id,
            has_actions=suggested_actions is not None,
        )

        # DEV-162: Fire-and-forget analytics tracking for terminal question
        await track_question_answer_async(
            session_id=answer_request.session_id,
            user_id=session.user_id,
            question_id=answer_request.question_id,
            option_id=answer_request.selected_option,
            custom_input=answer_request.custom_input,
        )

        return QuestionAnswerResponse(
            answer=str(response),
            suggested_actions=suggested_actions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_answer_failed",
            question_id=answer_request.question_id,
            session_id=answer_request.session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
