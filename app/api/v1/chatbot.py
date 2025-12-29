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

# DEV-178: Archived services - use simplified engine instead
# These imports are kept for backwards compatibility but will be removed in DEV-179
try:
    from archived.phase5_templates.services.action_template_service import ActionTemplateService
    from archived.phase5_templates.services.atomic_facts_extractor import AtomicFactsExtractor

    _LEGACY_SERVICES_AVAILABLE = True
except ImportError:
    ActionTemplateService = None  # type: ignore
    AtomicFactsExtractor = None  # type: ignore
    _LEGACY_SERVICES_AVAILABLE = False

from app.core.prompts import SUGGESTED_ACTIONS_PROMPT
from app.core.utils.xml_stripper import clean_proactivity_content
from app.services.attachment_resolver import (
    AttachmentNotFoundError,
    AttachmentOwnershipError,
    attachment_resolver,
)
from app.services.chat_history_service import chat_history_service
from app.services.domain_action_classifier import DomainActionClassifier
from app.services.llm_response_parser import parse_llm_response
from app.services.proactivity_analytics_service import ProactivityAnalyticsService
from app.services.proactivity_engine import ProactivityEngine

# DEV-179: Import simplified proactivity engine and parser
from app.services.proactivity_engine_simplified import (
    ProactivityEngine as SimplifiedProactivityEngine,
)
from app.services.proactivity_engine_simplified import (
    ProactivityResult as SimplifiedProactivityResult,
)

router = APIRouter()
agent = LangGraphAgent()

# DEV-158: Singleton ProactivityEngine instance
# DEV-178: DEPRECATED - Will be replaced by simplified engine in DEV-179
_proactivity_engine: ProactivityEngine | None = None


def get_proactivity_engine() -> ProactivityEngine:
    """Get or create the ProactivityEngine singleton.

    DEPRECATED: This function uses the legacy ProactivityEngine.
    DEV-179 will update this to use the simplified engine.

    Returns:
        ProactivityEngine: The singleton engine instance

    Raises:
        RuntimeError: If legacy services are not available
    """
    global _proactivity_engine
    if _proactivity_engine is None:
        if not _LEGACY_SERVICES_AVAILABLE:
            # DEV-178: Legacy services archived, return None for now
            # DEV-179 will implement the new engine integration
            logger.warning(
                "proactivity_legacy_unavailable",
                extra={"message": "Legacy proactivity services archived. Use simplified engine."},
            )
            raise RuntimeError(
                "Legacy ProactivityEngine services have been archived. "
                "Please update to use the simplified engine from DEV-177."
            )
        template_service = ActionTemplateService()
        template_service.load_templates()
        facts_extractor = AtomicFactsExtractor()
        _proactivity_engine = ProactivityEngine(
            template_service=template_service,
            facts_extractor=facts_extractor,
        )
    return _proactivity_engine


# DEV-160: Singleton ActionTemplateService instance
# DEV-178: DEPRECATED - Service archived to archived/phase5_templates/
_template_service = None


def get_template_service():
    """Get or create the ActionTemplateService singleton.

    DEPRECATED: This service has been archived as of DEV-178.
    Use DOCUMENT_ACTION_TEMPLATES from app.core.proactivity_constants instead.

    Returns:
        ActionTemplateService: The singleton service instance

    Raises:
        RuntimeError: If legacy service is not available
    """
    global _template_service
    if _template_service is None:
        if not _LEGACY_SERVICES_AVAILABLE:
            logger.warning(
                "template_service_archived",
                extra={"message": "ActionTemplateService archived. Use proactivity_constants."},
            )
            raise RuntimeError(
                "ActionTemplateService has been archived. "
                "Use DOCUMENT_ACTION_TEMPLATES from app.core.proactivity_constants."
            )
        _template_service = ActionTemplateService()
        _template_service.load_templates()
    return _template_service


# =============================================================================
# DEV-179: LLM-First Proactivity Helpers
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


def inject_proactivity_prompt(base_prompt: str) -> str:
    """Inject suggested_actions prompt into base system prompt.

    DEV-179: Appends the suggested_actions output format prompt to the
    system prompt. This instructs the LLM to output responses with
    <answer> and <suggested_actions> XML-like tags.

    Args:
        base_prompt: The base system prompt

    Returns:
        str: Combined prompt with suggested_actions instructions appended
    """
    return f"{base_prompt}\n\n{SUGGESTED_ACTIONS_PROMPT}"


def apply_action_override(
    llm_actions: list[dict] | None,
    template_actions: list[dict] | None,
) -> list[dict]:
    """Apply action override logic for LLM-First proactivity.

    DEV-179: Template actions take priority over LLM-generated actions.
    This ensures consistent, high-quality actions for known document types.

    Priority:
    1. Template actions (if present) - from DOCUMENT_ACTION_TEMPLATES
    2. LLM actions (if template not applicable)
    3. Empty list (if neither available)

    Args:
        llm_actions: Actions parsed from LLM response
        template_actions: Actions from DOCUMENT_ACTION_TEMPLATES

    Returns:
        list[dict]: Final list of actions to return
    """
    # Template actions take priority
    if template_actions:
        return template_actions

    # Use LLM actions if no template
    if llm_actions:
        return llm_actions

    # Return empty list if neither
    return []


# =============================================================================
# DEV-180: Streaming Tag Stripping and Buffering Helpers
# =============================================================================

import re

# Compiled regex patterns for XML tag stripping
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

            # DEV-158: Process proactivity for suggested actions and questions
            # BUGFIX: Integrate DomainActionClassifier to provide domain/action/sub_domain
            proactivity_result: ProactivityResult | None = None
            try:
                proactivity_engine = get_proactivity_engine()

                # Classify query to get domain, action, and sub_domain
                query_text = user_query if user_query else ""
                classifier = DomainActionClassifier()
                classification = await classifier.classify(query_text)

                logger.debug(
                    "proactivity_classification",
                    session_id=session.id,
                    domain=classification.domain.value,
                    action=classification.action.value,
                    sub_domain=classification.sub_domain,
                    confidence=classification.confidence,
                )

                # Build ProactivityContext with classification results
                proactivity_context = ProactivityContext(
                    session_id=str(session.id),
                    domain=classification.domain.value.lower(),
                    action_type=classification.action.value.lower(),
                    sub_domain=classification.sub_domain,
                    classification_confidence=classification.confidence,
                    document_type=None,
                )
                proactivity_result = proactivity_engine.process(
                    query=query_text,
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
        # PRE-RESPONSE PROACTIVITY DETECTION
        # =====================================================================
        # For ALL vague/generic queries with missing parameters, show interactive
        # question FIRST (before LLM call) to avoid generic Wikipedia-style
        # responses. This improves UX by collecting all needed data upfront.
        #
        # Applies to: Any query where proactivity determines we need more info.
        # Exception: Queries that match KB/Golden Set should proceed to RAG.
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
        elif query_classification:
            try:
                proactivity_engine = get_proactivity_engine()

                # Handle potentially null domain/action from failed classification
                domain_value = "default"
                action_value = "information_request"
                if query_classification.domain:
                    domain_value = (
                        query_classification.domain.value.lower()
                        if hasattr(query_classification.domain, "value")
                        else str(query_classification.domain).lower()
                    )
                if query_classification.action:
                    action_value = (
                        query_classification.action.value.lower()
                        if hasattr(query_classification.action, "value")
                        else str(query_classification.action).lower()
                    )

                logger.debug(
                    "pre_response_proactivity_starting",
                    session_id=session.id,
                    domain=domain_value,
                    action=action_value,
                    confidence=query_classification.confidence,
                    user_query=user_query[:100] if user_query else "N/A",
                )

                # Build context with classification
                pre_context = ProactivityContext(
                    session_id=str(session.id),
                    domain=domain_value,
                    action_type=action_value,
                    sub_domain=query_classification.sub_domain,
                    classification_confidence=query_classification.confidence,
                    document_type=None,
                )

                # Extract parameters and check coverage
                pre_result = proactivity_engine.process(
                    query=user_query if user_query != "N/A" else "",
                    context=pre_context,
                )

                # If proactivity engine says we should ask a question,
                # return it BEFORE calling LLM
                if pre_result.question and proactivity_engine.should_ask_question(
                    pre_result.extraction_result, user_query
                ):
                    pre_response_question = pre_result.question
                    # Generate explanation based on the ACTUAL question being shown
                    # (not the possibly-wrong classification)
                    detected_intent = (
                        pre_result.extraction_result.intent if pre_result.extraction_result else "unknown"
                    )
                    question_id = pre_result.question.id

                    # Match explanation to the specific question being shown
                    if question_id == "irpef_input_fields":
                        pre_response_explanation = "L'IRPEF dipende dal tuo reddito e dalla tua situazione personale. Inserisci i dati per un calcolo preciso."
                    elif question_id == "iva_input_fields":
                        pre_response_explanation = (
                            "Per calcolare l'IVA correttamente, ho bisogno di conoscere l'importo e l'aliquota."
                        )
                    elif question_id == "inps_input_fields":
                        pre_response_explanation = "I contributi INPS variano in base al reddito e alla categoria. Inserisci i dati per il calcolo."
                    elif question_id == "tfr_input_fields":
                        pre_response_explanation = (
                            "Il TFR dipende dalla retribuzione e dagli anni di servizio. Inserisci i dati."
                        )
                    elif question_id == "tax_type_selection":
                        pre_response_explanation = "Le tasse variano molto in base al tipo e alla tua situazione. Aiutami a capire di cosa hai bisogno."
                    elif question_id == "deadline_type_selection":
                        pre_response_explanation = (
                            "Le scadenze fiscali variano in base all'adempimento. Quale ti interessa verificare?"
                        )
                    elif question_id == "topic_clarification":
                        # Fallback question - use a generic but helpful explanation
                        pre_response_explanation = (
                            "Per darti una risposta utile e precisa, aiutami a capire meglio la tua richiesta."
                        )
                    else:
                        pre_response_explanation = "Per aiutarti al meglio, ho bisogno di qualche dettaglio in più."

                    logger.info(
                        "pre_response_proactivity_triggered",
                        session_id=session.id,
                        question_id=pre_result.question.id,
                        question_type=pre_result.question.question_type,
                        action_type=action_value,
                        coverage=pre_result.extraction_result.coverage if pre_result.extraction_result else 0,
                        intent=pre_result.extraction_result.intent if pre_result.extraction_result else None,
                    )
                else:
                    # Log why no question was triggered
                    logger.debug(
                        "pre_response_proactivity_no_question",
                        session_id=session.id,
                        has_question=pre_result.question is not None,
                        should_ask=proactivity_engine.should_ask_question(pre_result.extraction_result, user_query)
                        if pre_result.extraction_result
                        else False,
                        coverage=pre_result.extraction_result.coverage if pre_result.extraction_result else 0,
                        intent=pre_result.extraction_result.intent if pre_result.extraction_result else None,
                        can_proceed=pre_result.extraction_result.can_proceed if pre_result.extraction_result else True,
                        missing_required=pre_result.extraction_result.missing_required
                        if pre_result.extraction_result
                        else [],
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
                    # DEV-200: Track proactivity actions from graph Step 100
                    graph_proactivity_actions: list[dict] = []

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
                                    # DEV-200: Proactivity actions from graph Step 100
                                    # Format: __PROACTIVITY_ACTIONS__:<json_array>
                                    try:
                                        import json as _json

                                        actions_json = chunk.replace("__PROACTIVITY_ACTIONS__:", "")
                                        graph_proactivity_actions = _json.loads(actions_json)
                                        logger.info(
                                            "proactivity_actions_received_from_graph",
                                            session_id=session.id,
                                            action_count=len(graph_proactivity_actions),
                                        )
                                    except Exception as parse_err:
                                        logger.warning(
                                            "proactivity_actions_parse_failed",
                                            session_id=session.id,
                                            error=str(parse_err),
                                        )
                                        graph_proactivity_actions = []
                                    # Don't yield - will be sent as SSE event below
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

                    # DEV-200: Yield proactivity events from graph Step 100
                    # The actions are now set by PostProactivity node in the graph
                    # Skip if skip_proactivity flag is set (follow-up queries from answered questions)
                    if chat_request.skip_proactivity:
                        logger.debug(
                            "post_response_proactivity_skipped",
                            session_id=session.id,
                            reason="skip_proactivity flag set (follow-up query)",
                        )
                    elif graph_proactivity_actions:
                        # DEV-200: Use actions from graph Step 100 (PostProactivity node)
                        logger.info(
                            "yielding_graph_proactivity_actions_sse",
                            session_id=session.id,
                            action_count=len(graph_proactivity_actions),
                            action_ids=[a.get("id") for a in graph_proactivity_actions],
                        )
                        actions_event = StreamResponse(
                            content="",
                            event_type="suggested_actions",
                            suggested_actions=graph_proactivity_actions,
                            extracted_params=None,
                        )
                        yield write_sse(None, format_sse_event(actions_event), request_id=request_id)

                        # NOTE: Post-response proactivity should NOT yield interactive questions.
                        # Questions are for PRE-response proactivity (gathering info before LLM call).
                        # After the LLM has already answered, only suggested_actions make sense.

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

        # Execute action as regular chat query using Message format
        input_messages = [Message(role="user", content=prompt)]
        response = await agent.get_response(
            input_messages,
            action_request.session_id,
            user_id=session.user_id,
        )

        # Convert response to messages for return
        messages = [Message(role="assistant", content=str(response))]

        # Process proactivity for follow-up actions
        # BUGFIX: Use DomainActionClassifier for better intent detection
        proactivity_result: ProactivityResult | None = None
        try:
            proactivity_engine = get_proactivity_engine()

            # Classify the executed prompt
            classifier = DomainActionClassifier()
            classification = await classifier.classify(prompt)

            proactivity_context = ProactivityContext(
                session_id=action_request.session_id,
                domain=classification.domain.value.lower(),
                action_type=classification.action.value.lower(),
                sub_domain=classification.sub_domain,
                classification_confidence=classification.confidence,
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

        # Process proactivity for follow-up actions
        # BUGFIX: Use DomainActionClassifier for better intent detection
        suggested_actions = None
        try:
            proactivity_engine = get_proactivity_engine()

            # Classify the question answer prompt
            classifier = DomainActionClassifier()
            classification = await classifier.classify(prompt)

            proactivity_context = ProactivityContext(
                session_id=answer_request.session_id,
                domain=classification.domain.value.lower(),
                action_type=classification.action.value.lower(),
                sub_domain=classification.sub_domain,
                classification_confidence=classification.confidence,
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
