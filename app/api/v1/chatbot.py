"""Chatbot API endpoints for handling chat interactions.

This module provides endpoints for chat interactions, including regular chat,
streaming chat, message history management, and chat history clearing.

DEV-158: Added ProactivityEngine integration for suggested actions and
interactive questions support.

DEV-162: Added analytics tracking for action clicks and question answers.
"""

import asyncio
import json
import re
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

# DEV-245 Phase 5.15: SUGGESTED_ACTIONS_PROMPT import removed per user feedback
from app.core.sse_formatter import (
    format_sse_done,
    format_sse_event,
)
from app.core.sse_write import (
    log_sse_summary,
    write_sse,
)
from app.core.streaming_guard import SinglePassStream
from app.core.utils.xml_stripper import clean_proactivity_content
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
    QuestionAnswerRequest,
    QuestionAnswerResponse,
)
from app.services.attachment_resolver import (
    AttachmentNotFoundError,
    AttachmentOwnershipError,
    attachment_resolver,
)
from app.services.chat_history_service import chat_history_service
from app.services.domain_action_classifier import DomainActionClassifier
from app.services.llm_response_parser import parse_llm_response
from app.services.proactivity_analytics_service import ProactivityAnalyticsService

# DEV-179: Import simplified proactivity engine (replaces deprecated ProactivityEngine)
from app.services.proactivity_engine_simplified import (
    ProactivityEngine as SimplifiedProactivityEngine,
)
from app.services.proactivity_engine_simplified import (
    ProactivityResult as SimplifiedProactivityResult,
)

router = APIRouter()
agent = LangGraphAgent()


def get_template_service():
    """DEPRECATED: Get template service (archived in DEV-178).

    This function is no longer available. The ActionTemplateService has been
    archived and replaced by the simplified LLM-First proactivity engine.

    Action templates are now defined in app.core.proactivity_constants.

    Raises:
        RuntimeError: Always, since this functionality is deprecated.
    """
    raise RuntimeError(
        "DEV-179: ActionTemplateService has been deprecated. "
        "Action and question templates are now defined in proactivity_constants. "
        "Use get_simplified_proactivity_engine() for proactivity processing."
    )


# =============================================================================
# Proactivity Engine (DEV-179: Using simplified LLM-First engine)
# =============================================================================

# Singleton simplified proactivity engine
_simplified_proactivity_engine: SimplifiedProactivityEngine | None = None


def get_simplified_proactivity_engine() -> SimplifiedProactivityEngine:
    """Get or create the simplified ProactivityEngine singleton.

    DEV-179: Returns the new LLM-First ProactivityEngine from DEV-177.
    Uses three-step decision logic:
    1. Calculable intent with missing params -> InteractiveQuestion
    2. Recognized document type -> template actions
    3. Otherwise -> LLM generates actions

    Returns:
        SimplifiedProactivityEngine: The singleton engine instance
    """
    global _simplified_proactivity_engine
    if _simplified_proactivity_engine is None:
        _simplified_proactivity_engine = SimplifiedProactivityEngine()
        logger.info(
            "simplified_proactivity_engine_initialized",
            extra={"message": "LLM-First ProactivityEngine ready"},
        )
    return _simplified_proactivity_engine


# DEV-245 Phase 5.15: inject_proactivity_prompt and apply_action_override removed
# Suggested actions feature has been completely removed per user feedback


# =============================================================================
# DEV-180: Streaming Tag Stripping and Buffering Helpers
# DEV-245 Phase 5.15: inject_proactivity_prompt and apply_action_override removed
# =============================================================================

# Compiled regex patterns for XML tag stripping (uses 're' imported at top)
_ANSWER_TAG_PATTERN = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
_ACTIONS_TAG_PATTERN = re.compile(r"<suggested_actions>.*?</suggested_actions>", re.DOTALL)
_OPENING_ANSWER_TAG = re.compile(r"<answer>")
_CLOSING_ANSWER_TAG = re.compile(r"</answer>")


def strip_xml_tags(content: str) -> str:
    """Strip <answer> and <suggested_actions> XML tags from content.

    DEV-180: Removes XML tags used for LLM-First proactivity while
    preserving the actual content. Used for streaming output.

    Args:
        content: Raw content with potential XML tags

    Returns:
        str: Content with XML tags stripped
    """
    if not content:
        return ""

    result = content

    # First, try to extract just the answer content
    answer_match = _ANSWER_TAG_PATTERN.search(result)
    if answer_match:
        result = answer_match.group(1)
    else:
        # If no complete answer tag, strip opening tag if present
        result = _OPENING_ANSWER_TAG.sub("", result)
        result = _CLOSING_ANSWER_TAG.sub("", result)

    # Remove suggested_actions block entirely
    result = _ACTIONS_TAG_PATTERN.sub("", result)

    return result.strip()


class StreamBuffer:
    """Buffer for accumulating streamed response chunks.

    DEV-180: Collects chunks during streaming for final parsing
    while allowing real-time content delivery.
    """

    def __init__(self, max_size: int = 1024 * 1024) -> None:
        """Initialize buffer with optional max size.

        Args:
            max_size: Maximum buffer size in bytes (default 1MB)
        """
        self._chunks: list[str] = []
        self._size = 0
        self._max_size = max_size

    def append(self, chunk: str) -> None:
        """Append a chunk to the buffer.

        Args:
            chunk: String chunk to append
        """
        if chunk:
            self._chunks.append(chunk)
            self._size += len(chunk)

    def get_content(self) -> str:
        """Get the complete buffered content.

        Returns:
            str: All chunks joined together
        """
        return "".join(self._chunks)

    def size(self) -> int:
        """Get current buffer size in characters.

        Returns:
            int: Total size of buffered content
        """
        return self._size

    def clear(self) -> None:
        """Clear the buffer."""
        self._chunks = []
        self._size = 0


class StreamTagState:
    """State for tracking XML tags across stream chunks.

    DEV-180: Maintains state for handling partial tags that
    span multiple chunks during streaming.
    """

    def __init__(self) -> None:
        """Initialize tag state."""
        self.pending_tag: str = ""
        self.inside_answer: bool = False
        self.inside_actions: bool = False


def process_stream_chunk(chunk: str, state: StreamTagState) -> tuple[str, StreamTagState]:
    """Process a single stream chunk, stripping tags.

    DEV-180: Handles partial tags across chunk boundaries.

    Args:
        chunk: Single chunk from stream
        state: Current tag state

    Returns:
        Tuple of (processed content, updated state)
    """
    if not chunk:
        return "", state

    # Combine with any pending content from previous chunk
    content = state.pending_tag + chunk
    state.pending_tag = ""

    # Check for partial tags at end of chunk
    # Look for incomplete opening or closing tags
    for i in range(len(content) - 1, max(len(content) - 20, -1), -1):
        if i < 0:
            break
        if content[i] == "<":
            potential_tag = content[i:]
            # Check if this could be start of our tags
            if (
                potential_tag.startswith("<a")
                or potential_tag.startswith("</a")
                or potential_tag.startswith("<s")
                or potential_tag.startswith("</s")
            ):
                # Check if tag is incomplete
                if ">" not in potential_tag:
                    state.pending_tag = potential_tag
                    content = content[:i]
                    break

    # Now strip complete tags from content
    result = strip_xml_tags(content)

    return result, state


def format_actions_sse_event(actions: list[dict]) -> str:
    """Format suggested_actions as SSE event.

    DEV-180: Creates SSE event for suggested actions.

    Args:
        actions: List of action dictionaries

    Returns:
        str: Formatted SSE event string
    """
    event_data = {
        "content": "",
        "event_type": "suggested_actions",
        "suggested_actions": actions,
    }
    return f"data: {json.dumps(event_data)}\n\n"


def format_question_sse_event(question: dict) -> str:
    """Format interactive_question as SSE event.

    DEV-180: Creates SSE event for interactive questions.

    Args:
        question: Question dictionary

    Returns:
        str: Formatted SSE event string
    """
    event_data = {
        "content": "",
        "event_type": "interactive_question",
        "interactive_question": question,
    }
    return f"data: {json.dumps(event_data)}\n\n"


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

            # DEV-179: Process proactivity using simplified engine (interactive questions only)
            # DEV-245 Phase 5.15: suggested_actions/template_actions feature removed
            simplified_proactivity_result: SimplifiedProactivityResult | None = None
            interactive_question = None
            try:
                simplified_engine = get_simplified_proactivity_engine()
                query_text = user_query if user_query else ""
                simplified_proactivity_result = simplified_engine.process_query(
                    query=query_text,
                    document=None,
                )

                logger.debug(
                    "proactivity_processed",
                    session_id=session.id,
                    has_question=simplified_proactivity_result.interactive_question is not None,
                )

                # Convert to schema types if present (interactive questions only)
                if simplified_proactivity_result.interactive_question:
                    from app.schemas.proactivity import InputField, InteractiveQuestion

                    question_dict = simplified_proactivity_result.interactive_question
                    fields = [InputField(**f) if isinstance(f, dict) else f for f in question_dict.get("fields", [])]
                    interactive_question = InteractiveQuestion(
                        id=question_dict.get("id", "unknown"),
                        text=question_dict.get("text", "Ho bisogno di alcune informazioni:"),
                        question_type=question_dict.get("question_type", "multi_field"),
                        fields=fields,
                        prefilled_params=question_dict.get("prefilled"),
                    )

            except Exception as proactivity_error:
                # Graceful degradation: log warning but continue without proactivity
                logger.warning(
                    "proactivity_processing_failed_non_critical",
                    session_id=session.id,
                    error=str(proactivity_error),
                )

            # DEV-245 Phase 5.15: suggested_actions removed from response
            return ChatResponse(
                messages=result,
                interactive_question=interactive_question,
                extracted_params=None,  # Not available in simplified engine
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

        # BUGFIX: Classify query for proactivity (in outer function, used in generator)
        query_classification = None
        try:
            classifier = DomainActionClassifier()
            query_classification = await classifier.classify(user_query if user_query != "N/A" else "")
            logger.debug(
                "stream_proactivity_classification",
                session_id=session.id,
                domain=query_classification.domain.value,
                action=query_classification.action.value,
                sub_domain=query_classification.sub_domain,
                confidence=query_classification.confidence,
            )
        except Exception as classification_error:
            logger.warning(
                "stream_classification_failed_non_critical",
                session_id=session.id,
                error=str(classification_error),
            )

        # =====================================================================
        # PRE-RESPONSE PROACTIVITY DETECTION (DEV-179: Simplified Engine)
        # =====================================================================
        # Shows interactive question BEFORE LLM call ONLY for explicit calculation
        # requests (e.g., "calcola IRPEF", "quanto IVA") that are missing required
        # parameters like income amount or tax rate.
        #
        # The simplified engine uses pattern matching (not classification) so it
        # won't trigger for vague queries like "Non so cosa posso dedurre" - these
        # go directly to the LLM for a helpful answer.
        #
        # Skip: When skip_proactivity flag is set (follow-up queries from answered questions).
        # =====================================================================
        pre_response_question = None
        pre_response_explanation = None
        if chat_request.skip_proactivity:
            logger.info(
                "pre_response_proactivity_skipped",
                session_id=session.id,
                reason="skip_proactivity flag set (follow-up query)",
            )
        else:
            try:
                # DEV-179: Use simplified engine (no classification dependency)
                simplified_engine = get_simplified_proactivity_engine()
                simplified_result = simplified_engine.process_query(
                    query=user_query if user_query != "N/A" else "",
                    document=None,  # No document for pre-response
                )

                logger.debug(
                    "pre_response_proactivity_check",
                    session_id=session.id,
                    user_query=user_query[:100] if user_query else "N/A",
                    has_question=simplified_result.interactive_question is not None,
                    use_llm_actions=simplified_result.use_llm_actions,
                )

                # If simplified engine detected a calculable intent with missing params
                if simplified_result.interactive_question:
                    question_dict = simplified_result.interactive_question
                    question_id = question_dict.get("id", "unknown")

                    # Convert dict to InteractiveQuestion pydantic model
                    # Handle field name mapping: prefilled -> prefilled_params
                    from app.schemas.proactivity import InputField, InteractiveQuestion

                    fields = [InputField(**f) if isinstance(f, dict) else f for f in question_dict.get("fields", [])]
                    pre_response_question = InteractiveQuestion(
                        id=question_id,
                        text=question_dict.get("text", "Ho bisogno di alcune informazioni:"),
                        question_type=question_dict.get("question_type", "multi_field"),
                        fields=fields,
                        prefilled_params=question_dict.get("prefilled"),
                    )

                    # Generate explanation based on the calculation type
                    if "irpef" in question_id:
                        pre_response_explanation = "L'IRPEF dipende dal tuo reddito e dalla tua situazione personale. Inserisci i dati per un calcolo preciso."
                    elif "iva" in question_id:
                        pre_response_explanation = (
                            "Per calcolare l'IVA correttamente, ho bisogno di conoscere l'importo e l'aliquota."
                        )
                    elif "inps" in question_id or "contributi" in question_id:
                        pre_response_explanation = "I contributi INPS variano in base al reddito e alla categoria. Inserisci i dati per il calcolo."
                    elif "ravvedimento" in question_id:
                        pre_response_explanation = (
                            "Per calcolare il ravvedimento operoso, ho bisogno di conoscere importo e data scadenza."
                        )
                    elif "f24" in question_id:
                        pre_response_explanation = "Per compilare il modello F24, ho bisogno di alcune informazioni."
                    else:
                        pre_response_explanation = "Per aiutarti al meglio, ho bisogno di qualche dettaglio in più."

                    logger.info(
                        "pre_response_proactivity_triggered",
                        session_id=session.id,
                        question_id=question_id,
                        question_type=question_dict.get("question_type"),
                    )
                else:
                    # No question needed - query will go to LLM
                    logger.debug(
                        "pre_response_proactivity_no_question",
                        session_id=session.id,
                        reason="no_calculable_intent" if simplified_result.use_llm_actions else "document_actions",
                    )
            except Exception as pre_proactivity_error:
                logger.warning(
                    "pre_response_proactivity_failed_non_critical",
                    session_id=session.id,
                    error=str(pre_proactivity_error),
                )

        # If we have a pre-response question, return explanation + question WITHOUT calling LLM
        if pre_response_question:

            async def question_only_generator():
                """Generate SSE stream with explanation + interactive question (no LLM call)."""
                # Send short explanation first (so user knows why we're asking)
                if pre_response_explanation:
                    explanation_event = StreamResponse(
                        content=pre_response_explanation + "\n\n",
                        done=False,
                        event_type="content",
                    )
                    yield write_sse(None, format_sse_event(explanation_event), request_id=request_id)

                # Send the interactive question event
                question_data = pre_response_question.model_dump()
                logger.info(
                    "yielding_pre_response_question_sse",
                    session_id=session.id,
                    question_id=pre_response_question.id,
                    question_type=pre_response_question.question_type,
                )
                question_event = StreamResponse(
                    content="",
                    event_type="interactive_question",
                    interactive_question=question_data,
                )
                yield write_sse(None, format_sse_event(question_event), request_id=request_id)

                # Send done frame
                sse_done = format_sse_done()
                yield write_sse(None, sse_done, request_id=request_id)

                # Log summary
                log_sse_summary(request_id=request_id)

            # Save pre-response interaction to LangGraph checkpoint BEFORE returning response
            # This ensures the interaction appears in /messages endpoint on page refresh
            if pre_response_explanation and user_query and user_query.strip():
                try:
                    await agent.add_messages_to_history(
                        session_id=session.id,
                        user_message=user_query.strip(),
                        assistant_message=pre_response_explanation.strip(),
                    )
                    logger.info(
                        "pre_response_chat_history_saved",
                        session_id=session.id,
                        user_query_preview=user_query[:50],
                    )
                except Exception as save_error:
                    logger.warning(
                        "pre_response_chat_history_save_failed",
                        session_id=session.id,
                        error=str(save_error),
                    )

            return StreamingResponse(question_only_generator(), media_type="text/event-stream")

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
                    # DEV-245 Phase 5.15: Removed graph_proactivity_actions tracking (feature removed)
                    # DEV-244: Collect KB sources metadata for persistence in chat history
                    collected_kb_sources_metadata: list[dict] | None = None
                    # DEV-245: Collect web verification metadata for persistence in chat history
                    collected_web_verification_data: dict | None = None

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
                                elif chunk.startswith("__PROACTIVITY_ACTIONS__:"):
                                    # DEV-245 Phase 5.15: Suggested actions feature removed
                                    # Ignore any legacy action markers from graph
                                    pass
                                elif chunk.startswith("__REASONING_TRACE__:"):
                                    # DEV-242: Reasoning trace for Chain of Thought display
                                    # Format: __REASONING_TRACE__:<json_object>
                                    try:
                                        import json as _json

                                        reasoning_json = chunk.replace("__REASONING_TRACE__:", "")
                                        reasoning_data = _json.loads(reasoning_json)
                                        logger.info(
                                            "reasoning_trace_received_from_graph",
                                            session_id=session.id,
                                            has_tema=bool(reasoning_data.get("tema_identificato")),
                                        )
                                        # Send reasoning as SSE event immediately
                                        reasoning_event = StreamResponse(
                                            content="",
                                            event_type="reasoning",
                                            reasoning=reasoning_data,
                                        )
                                        yield write_sse(None, format_sse_event(reasoning_event), request_id=request_id)
                                    except Exception as parse_err:
                                        logger.warning(
                                            "reasoning_trace_parse_failed",
                                            session_id=session.id,
                                            error=str(parse_err),
                                        )
                                elif chunk.startswith("__STRUCTURED_SOURCES__:"):
                                    # DEV-242 Phase 12B: Structured sources for SourcesIndex
                                    # Format: __STRUCTURED_SOURCES__:<json_array>
                                    try:
                                        import json as _json

                                        sources_json = chunk.replace("__STRUCTURED_SOURCES__:", "")
                                        structured_sources_data = _json.loads(sources_json)
                                        logger.info(
                                            "structured_sources_received_from_graph",
                                            session_id=session.id,
                                            sources_count=len(structured_sources_data),
                                        )
                                        # Send structured sources as SSE event immediately
                                        sources_event = StreamResponse(
                                            content="",
                                            event_type="structured_sources",
                                            structured_sources=structured_sources_data,
                                        )
                                        yield write_sse(None, format_sse_event(sources_event), request_id=request_id)
                                    except Exception as parse_err:
                                        logger.warning(
                                            "structured_sources_parse_failed",
                                            session_id=session.id,
                                            error=str(parse_err),
                                        )
                                elif chunk.startswith("__KB_SOURCE_URLS__:"):
                                    # DEV-244: KB source URLs (deterministic, independent of LLM output)
                                    # Format: __KB_SOURCE_URLS__:<json_array>
                                    try:
                                        import json as _json_kb

                                        urls_json = chunk.replace("__KB_SOURCE_URLS__:", "")
                                        kb_urls_data = _json_kb.loads(urls_json)
                                        # DEV-244: Store for persistence in chat history
                                        collected_kb_sources_metadata = kb_urls_data
                                        logger.info(
                                            "kb_source_urls_received_from_graph",
                                            session_id=session.id,
                                            sources_count=len(kb_urls_data),
                                        )
                                        # Send KB source URLs as SSE event immediately
                                        urls_event = StreamResponse(
                                            content="",
                                            event_type="kb_source_urls",
                                            kb_source_urls=kb_urls_data,
                                        )
                                        yield write_sse(None, format_sse_event(urls_event), request_id=request_id)
                                    except Exception as parse_err:
                                        logger.warning(
                                            "kb_source_urls_parse_failed",
                                            session_id=session.id,
                                            error=str(parse_err),
                                        )
                                elif chunk.startswith("__WEB_VERIFICATION__:"):
                                    # DEV-245: Web verification results from Brave Search
                                    # Format: __WEB_VERIFICATION__:<json_object>
                                    try:
                                        import json as _json_web

                                        web_json = chunk.replace("__WEB_VERIFICATION__:", "")
                                        web_verification_data = _json_web.loads(web_json)
                                        # DEV-245: Store for persistence in chat history
                                        collected_web_verification_data = web_verification_data
                                        logger.info(
                                            "web_verification_received_from_graph",
                                            session_id=session.id,
                                            web_sources_checked=web_verification_data.get("web_sources_checked", 0),
                                            has_caveats=web_verification_data.get("has_caveats", False),
                                            has_synthesized=web_verification_data.get(
                                                "has_synthesized_response", False
                                            ),
                                        )
                                        # DEV-245: Don't send web_verification SSE event - caveats are already
                                        # included inline in the LLM response, so showing them again in a
                                        # separate "Verifica Web" section would be redundant.
                                        # Data is still collected for persistence in chat history.
                                    except Exception as parse_err:
                                        logger.warning(
                                            "web_verification_parse_failed",
                                            session_id=session.id,
                                            error=str(parse_err),
                                        )
                                else:
                                    # This is regular content (plain text string from graph)
                                    # Collect chunk for chat history
                                    collected_response_chunks.append(chunk)
                                    # Wrap as proper SSE data event: data: {"content":"...","done":false}\n\n
                                    # Frontend expects this format (api.ts:756-784)
                                    stream_response = StreamResponse(content=chunk, done=False, event_type="content")
                                    sse_event = format_sse_event(stream_response)
                                    yield write_sse(None, sse_event, request_id=request_id)

                    # DEV-201: Send content_cleaned event to strip XML tags from user view
                    # The LLM outputs <answer> and <suggested_actions> tags, but users should
                    # never see raw XML. Clean the accumulated content and send replacement.
                    if collected_response_chunks:
                        raw_content = "".join(collected_response_chunks)
                        cleaned_content = clean_proactivity_content(raw_content)
                        if cleaned_content != raw_content:
                            logger.info(
                                "content_cleaned_xml_stripped",
                                session_id=session.id,
                                original_len=len(raw_content),
                                cleaned_len=len(cleaned_content),
                            )
                            # Send content_cleaned event - frontend will replace displayed content
                            cleaned_event = StreamResponse(
                                content=cleaned_content,
                                done=False,
                                event_type="content_cleaned",
                            )
                            yield write_sse(None, format_sse_event(cleaned_event), request_id=request_id)

                    # DEV-245 Phase 5.15: Suggested actions feature removed per user feedback
                    # The SSE event emission for suggested_actions has been removed.
                    # Interactive questions (pre-response) are still supported.

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
                                    kb_sources_metadata=collected_kb_sources_metadata,  # DEV-244
                                    web_verification_metadata=collected_web_verification_data,  # DEV-245
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

    FIXED: Now reads from PostgreSQL (industry standard) instead of LangGraph checkpoint.
    LangGraph checkpoints are for workflow state, not persistent chat history.
    PostgreSQL ensures:
    - GDPR compliance (export/deletion)
    - Multi-device sync
    - Reliable persistence across server restarts

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages.
    """
    try:
        # Read from PostgreSQL (source of truth for chat history)
        # Each record contains a Q&A pair: {query, response}
        history_records = await chat_history_service.get_session_history(
            user_id=session.user_id,
            session_id=session.id,
        )

        # Transform PostgreSQL records to Message format
        # Each record becomes TWO messages: user (query) + assistant (response)
        messages: list[Message] = []
        for record in history_records:
            # User message from 'query' field
            if record.get("query"):
                messages.append(Message(role="user", content=record["query"]))
            # Assistant message from 'response' field
            if record.get("response"):
                messages.append(
                    Message(
                        role="assistant",
                        content=record["response"],
                        # DEV-244: Include KB sources for Fonti section on page refresh
                        kb_source_urls=record.get("kb_sources_metadata"),
                    )
                )

        # DEV-244: Debug logging for kb_source_urls persistence
        kb_sources_count = sum(1 for r in history_records if r.get("kb_sources_metadata"))
        logger.info(
            "chat_history_loaded_from_postgresql",
            session_id=session.id,
            record_count=len(history_records),
            message_count=len(messages),
            records_with_kb_sources=kb_sources_count,
        )

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

    FIXED: Now clears from PostgreSQL (source of truth) instead of LangGraph checkpoint.

    Args:
        request: The FastAPI request object for rate limiting.
        session: The current session from the auth token.

    Returns:
        dict: A message indicating the chat history was cleared.
    """
    try:
        # Clear from PostgreSQL (source of truth)
        deleted_count = await chat_history_service.delete_session(
            user_id=session.user_id,
            session_id=session.id,
        )
        # Also clear LangGraph checkpoint for consistency during active sessions
        await agent.clear_chat_history(session.id)

        logger.info(
            "chat_history_cleared",
            session_id=session.id,
            deleted_count=deleted_count,
        )
        return {"message": "Chat history cleared successfully", "deleted_count": deleted_count}
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

        # Execute action as regular chat query using Message format
        input_messages = [Message(role="user", content=prompt)]
        response = await agent.get_response(
            input_messages,
            action_request.session_id,
            user_id=session.user_id,
        )

        # Convert response to messages for return
        messages = [Message(role="assistant", content=str(response))]

        # DEV-179: Process proactivity using simplified engine (interactive questions only)
        # DEV-245 Phase 5.15: suggested_actions feature removed per user feedback
        simplified_proactivity_result: SimplifiedProactivityResult | None = None
        interactive_question = None
        try:
            simplified_engine = get_simplified_proactivity_engine()
            simplified_proactivity_result = simplified_engine.process_query(
                query=prompt,
                document=None,
            )

            # Convert to schema types if present (interactive questions only)
            if simplified_proactivity_result.interactive_question:
                from app.schemas.proactivity import InputField, InteractiveQuestion

                question_dict = simplified_proactivity_result.interactive_question
                fields = [InputField(**f) if isinstance(f, dict) else f for f in question_dict.get("fields", [])]
                interactive_question = InteractiveQuestion(
                    id=question_dict.get("id", "unknown"),
                    text=question_dict.get("text", "Ho bisogno di alcune informazioni:"),
                    question_type=question_dict.get("question_type", "multi_field"),
                    fields=fields,
                    prefilled_params=question_dict.get("prefilled"),
                )

        except Exception as proactivity_error:
            logger.warning(
                "action_proactivity_processing_failed",
                action_id=action_request.action_id,
                session_id=action_request.session_id,
                error=str(proactivity_error),
            )

        logger.info(
            "action_execution_completed",
            action_id=action_request.action_id,
            session_id=action_request.session_id,
        )

        # DEV-162: Fire-and-forget analytics tracking
        await track_action_click_async(
            session_id=action_request.session_id,
            user_id=session.user_id,
            action=action,
            domain="default",  # TODO: Get from proactivity context when available
            context_hash=None,
        )

        # DEV-245 Phase 5.15: suggested_actions removed from response
        return ChatResponse(
            messages=messages,
            interactive_question=interactive_question,
            extracted_params=None,  # DEV-179: Not available in simplified engine
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
        # =====================================================================
        # MULTI-FIELD QUESTION HANDLING
        # =====================================================================
        # Multi-field questions (question_type == "multi_field") bypass template
        # lookup and option validation since they're dynamically generated.
        # =====================================================================
        is_multifield = answer_request.field_values is not None

        # List of dynamically generated question IDs that bypass template lookup
        DYNAMIC_QUESTION_IDS = {
            "tax_type_selection",
            "deadline_type_selection",
            "topic_clarification",
            "irpef_input_fields",
            "iva_input_fields",
            "inps_input_fields",
            "tfr_input_fields",
        }
        is_dynamic_question = answer_request.question_id in DYNAMIC_QUESTION_IDS

        if is_multifield:
            # Handle multi-field question answer
            logger.info(
                "multifield_question_answer_processing",
                question_id=answer_request.question_id,
                field_count=len(answer_request.field_values),
                session_id=answer_request.session_id,
                user_id=session.user_id,
            )

            # Build prompt from field values
            # Format: "Calcola IRPEF con: reddito=45000, deduzioni=5000, detrazioni=1200"
            field_parts = [f"{k}={v}" for k, v in answer_request.field_values.items() if v]
            prompt = f"Calcola con i seguenti dati: {', '.join(field_parts)}"

            # DEV-162: Fire-and-forget analytics tracking for multi-field
            await track_question_answer_async(
                session_id=answer_request.session_id,
                user_id=session.user_id,
                question_id=answer_request.question_id,
                option_id="multi_field",
                custom_input=json.dumps(answer_request.field_values),
            )
        elif is_dynamic_question:
            # =====================================================================
            # DYNAMIC SINGLE-CHOICE QUESTION HANDLING
            # =====================================================================
            # These questions are generated dynamically by the proactivity engine.
            # Instead of running through full RAG pipeline (which requires context),
            # return the prompt as "answer" for frontend to send as new chat message.
            # =====================================================================
            logger.info(
                "dynamic_question_answer_processing",
                question_id=answer_request.question_id,
                selected_option=answer_request.selected_option,
                custom_input=answer_request.custom_input,
                session_id=answer_request.session_id,
                user_id=session.user_id,
            )

            # Build a prompt based on the selected option
            if answer_request.custom_input:
                prompt = answer_request.custom_input
            else:
                # Map option IDs to meaningful prompts
                option_prompts = {
                    # tax_type_selection options
                    "irpef": "Voglio informazioni sull'IRPEF (imposta sul reddito)",
                    "iva": "Voglio informazioni sull'IVA",
                    "contributi": "Voglio informazioni sui contributi INPS",
                    "imu_tari": "Voglio informazioni su IMU e TARI",
                    # deadline_type_selection options
                    "f24": "Quali sono le scadenze per il pagamento F24?",
                    "dichiarazione_redditi": "Quali sono le scadenze per la dichiarazione dei redditi?",
                    "dichiarazione_iva": "Quali sono le scadenze per la dichiarazione IVA?",
                    "inps": "Quali sono le scadenze per i contributi INPS?",
                    # topic_clarification options
                    "calcolo_tasse": "Voglio calcolare imposte o contributi",
                    "scadenze": "Voglio informazioni su scadenze fiscali",
                    "normativa": "Voglio informazioni sulla normativa fiscale",
                    "situazione_specifica": "Ho una situazione fiscale specifica",
                    # Generic fallback
                    "altro": answer_request.custom_input or "Ho una domanda specifica",
                }
                prompt = option_prompts.get(
                    answer_request.selected_option, f"Ho selezionato: {answer_request.selected_option}"
                )

            # Track the answer
            await track_question_answer_async(
                session_id=answer_request.session_id,
                user_id=session.user_id,
                question_id=answer_request.question_id,
                option_id=answer_request.selected_option,
                custom_input=answer_request.custom_input,
            )

            # Return prompt as answer - frontend will send this as a new chat message
            # This avoids running through full RAG pipeline without proper context
            logger.info(
                "dynamic_question_returning_prompt",
                question_id=answer_request.question_id,
                prompt=prompt,
                session_id=answer_request.session_id,
            )
            return QuestionAnswerResponse(answer=prompt)
        else:
            # =====================================================================
            # SINGLE-CHOICE QUESTION HANDLING (template-based)
            # =====================================================================
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

        # Execute as chat query using Message format
        messages = [Message(role="user", content=prompt)]
        response = await agent.get_response(
            messages,
            answer_request.session_id,
            user_id=session.user_id,
        )

        # DEV-245 Phase 5.15: suggested_actions feature removed per user feedback
        # No longer processing proactivity for template actions

        logger.info(
            "question_answer_completed",
            question_id=answer_request.question_id,
            session_id=answer_request.session_id,
            is_multifield=is_multifield,
        )

        # DEV-162: Fire-and-forget analytics tracking for terminal question
        # Skip for multi-field since we already tracked at the start
        if not is_multifield:
            await track_question_answer_async(
                session_id=answer_request.session_id,
                user_id=session.user_id,
                question_id=answer_request.question_id,
                option_id=answer_request.selected_option or "unknown",
                custom_input=answer_request.custom_input,
            )

        # DEV-245 Phase 5.15: suggested_actions removed from response
        return QuestionAnswerResponse(
            answer=str(response),
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
