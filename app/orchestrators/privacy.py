# AUTO-GENERATED ORCHESTRATOR STUBS (safe to edit below stubs)
# These functions are the functional *nodes* that mirror the Mermaid diagram.
# Implement thin coordination here (call services/factories), not core business logic.

from contextlib import nullcontext
from datetime import UTC
from typing import Any, Dict, List, Optional

try:
    from app.observability.rag_logging import rag_step_log, rag_step_timer
except Exception:  # pragma: no cover

    def rag_step_log(**kwargs):
        return None

    def rag_step_timer(*args, **kwargs):
        return nullcontext()


async def step_4__gdprlog(*, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs) -> Any:
    """RAG STEP 4 — GDPRCompliance.record_processing Log data processing
    ID: RAG.privacy.gdprcompliance.record.processing.log.data.processing
    Type: process | Category: privacy | Node: GDPRLog

    Records data processing activities for GDPR compliance as per ChatbotController.chat.
    This orchestrator coordinates with GDPR compliance services for audit logging.
    """
    from datetime import datetime, timezone

    from app.core.config import settings
    from app.core.logging import logger
    from app.core.privacy.gdpr import DataCategory, ProcessingPurpose, gdpr_compliance

    with rag_step_timer(
        4, "RAG.privacy.gdprcompliance.record.processing.log.data.processing", "GDPRLog", stage="start"
    ):
        rag_step_log(
            step=4,
            step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
            node_label="GDPRLog",
            category="privacy",
            type="process",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        validation_result = kwargs.get("validation_result") or context.get("validation_result")
        request_metadata = kwargs.get("request_metadata") or context.get("request_metadata", {})
        request_id = request_metadata.get("request_id", "unknown")

        # Initialize result structure
        result = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "gdpr_logged": False,
            "processing_recorded": False,
            "processing_id": None,
            "gdpr_record": None,
            "next_step": "PrivacyCheck",
            "ready_for_privacy_check": False,
            "validated_request": None,
            "session": None,
            "user": None,
            "error": None,
            "skip_reason": None,
            "anonymized": settings.PRIVACY_ANONYMIZE_REQUESTS,
        }

        try:
            # Step 1: Validate input from Step 3 (ValidCheck)
            if not validation_result:
                result["error"] = "Missing validation result from Step 3"
                logger.error("GDPR logging failed: Missing validation result", request_id=request_id)
                rag_step_log(
                    step=4,
                    step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                    node_label="GDPRLog",
                    processing_stage="completed",
                    error="missing_validation_result",
                    gdpr_logged=False,
                    processing_recorded=False,
                    request_id=request_id,
                )
                return result

            # Extract validation components
            is_valid = validation_result.get("is_valid", False)
            validated_request = validation_result.get("validated_request")
            session = validation_result.get("session")
            user = validation_result.get("user")

            # Preserve data for next step
            result["validated_request"] = validated_request
            result["session"] = session
            result["user"] = user

            # Step 2: Skip GDPR logging for invalid requests
            if not is_valid:
                result["skip_reason"] = "invalid_request"
                result["ready_for_privacy_check"] = True
                logger.info("Skipping GDPR logging for invalid request", request_id=request_id)
                rag_step_log(
                    step=4,
                    step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                    node_label="GDPRLog",
                    processing_stage="completed",
                    gdpr_logged=False,
                    processing_recorded=False,
                    skip_reason="invalid_request",
                    request_id=request_id,
                )
                return result

            # Step 3: Record GDPR processing
            if not session or not session.user_id:
                result["error"] = "Missing session or user_id for GDPR logging"
                logger.error("GDPR logging failed: Missing session or user_id", request_id=request_id)
                rag_step_log(
                    step=4,
                    step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                    node_label="GDPRLog",
                    processing_stage="completed",
                    error="missing_session_or_user",
                    gdpr_logged=False,
                    processing_recorded=False,
                    request_id=request_id,
                )
                return result

            # Determine data category based on request content
            data_category = DataCategory.CONTENT
            if validated_request and validated_request.get("attachments"):
                # Requests with attachments use different category
                data_category = DataCategory.CONTENT  # Could be extended to CONTENT_WITH_ATTACHMENTS

            # Record processing with GDPR service
            gdpr_record = gdpr_compliance.data_processor.record_processing(
                user_id=session.user_id,
                data_category=data_category,
                processing_purpose=ProcessingPurpose.SERVICE_PROVISION,
                data_source="chat_api",
                legal_basis="Service provision under contract",
                anonymized=settings.PRIVACY_ANONYMIZE_REQUESTS,
            )

            # Step 4: Process successful logging
            result["gdpr_logged"] = True
            result["processing_recorded"] = True
            result["processing_id"] = gdpr_record.get("processing_id")
            result["gdpr_record"] = gdpr_record
            result["ready_for_privacy_check"] = True

            session_id = session.id if session else "unknown"
            user_id = session.user_id if session else "unknown"

            logger.info(
                "GDPR processing recorded successfully",
                processing_id=result["processing_id"],
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                data_category=data_category.value,
                anonymized=result["anonymized"],
                extra={
                    "gdpr_event": "processing_recorded",
                    "processing_id": result["processing_id"],
                    "anonymized": result["anonymized"],
                },
            )

            rag_step_log(
                step=4,
                step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                node_label="GDPRLog",
                processing_stage="completed",
                gdpr_logged=True,
                processing_recorded=True,
                processing_id=result["processing_id"],
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                next_step="PrivacyCheck",
                ready_for_privacy_check=True,
                anonymized=result["anonymized"],
            )

            return result

        except Exception as e:
            # Handle GDPR service errors gracefully
            result["error"] = f"GDPR logging error: {str(e)}"
            result["ready_for_privacy_check"] = True  # Continue despite logging failure

            session_id = result["session"].id if result["session"] else "unknown"
            user_id = result["session"].user_id if result["session"] else "unknown"

            logger.error(
                "GDPR processing failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                exc_info=True,
            )

            rag_step_log(
                step=4,
                step_id="RAG.privacy.gdprcompliance.record.processing.log.data.processing",
                node_label="GDPRLog",
                processing_stage="completed",
                error=str(e),
                gdpr_logged=False,
                processing_recorded=False,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                next_step="PrivacyCheck",
            )

            return result


async def step_6__privacy_check(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 6 — PRIVACY_ANONYMIZE_REQUESTS enabled?
    ID: RAG.privacy.privacy.anonymize.requests.enabled
    Type: decision | Category: privacy | Node: PrivacyCheck

    Decision node that checks if privacy anonymization is enabled.
    Routes to either text anonymization or direct workflow initialization.
    """
    from datetime import datetime, timezone

    from app.core.config import settings
    from app.core.logging import logger

    with rag_step_timer(6, "RAG.privacy.privacy.anonymize.requests.enabled", "PrivacyCheck", stage="start"):
        rag_step_log(
            step=6,
            step_id="RAG.privacy.privacy.anonymize.requests.enabled",
            node_label="PrivacyCheck",
            category="privacy",
            type="decision",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        gdpr_record = kwargs.get("gdpr_record") or context.get("gdpr_record")
        validated_request = kwargs.get("validated_request") or context.get("validated_request")
        session = kwargs.get("session") or context.get("session")
        user = kwargs.get("user") or context.get("user")
        request_metadata = kwargs.get("request_metadata") or context.get("request_metadata", {})
        request_id = request_metadata.get("request_id", "unknown")

        # Initialize result structure
        result = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "privacy_enabled": settings.PRIVACY_ANONYMIZE_REQUESTS,
            "anonymization_required": False,
            "decision": None,
            "next_step": None,
            "ready_for_anonymization": False,
            "ready_for_workflow_init": False,
            "privacy_settings": {},
            "validated_request": validated_request,
            "session": session,
            "user": user,
            "gdpr_record": gdpr_record,
            "warning": None,
            "user_preference_override": False,
            "environment": getattr(settings, "ENVIRONMENT", "development"),
        }

        try:
            # Step 1: Check for missing context
            if not validated_request or not session:
                result["warning"] = "Missing context data from previous steps"
                logger.warning(
                    "Privacy check with incomplete context",
                    request_id=request_id,
                    has_validated_request=bool(validated_request),
                    has_session=bool(session),
                )

            # Step 2: Check user-specific privacy preferences (if available)
            global_privacy_setting = settings.PRIVACY_ANONYMIZE_REQUESTS
            privacy_enabled = global_privacy_setting

            if user and hasattr(user, "privacy_settings") and user.privacy_settings:
                user_preference = user.privacy_settings.get("anonymize_requests")
                if user_preference is not None:
                    privacy_enabled = user_preference
                    result["user_preference_override"] = True
                    logger.info(
                        "User privacy preference overriding global setting",
                        user_id=user.id if user else "unknown",
                        global_setting=global_privacy_setting,
                        user_preference=user_preference,
                        request_id=request_id,
                    )

            # Step 3: Make routing decision
            result["privacy_enabled"] = privacy_enabled

            if privacy_enabled:
                # Route to anonymization
                result["anonymization_required"] = True
                result["decision"] = "anonymize_enabled"
                result["next_step"] = "AnonymizeText"
                result["ready_for_anonymization"] = True
                result["ready_for_workflow_init"] = False

                logger.info(
                    "Privacy anonymization enabled - routing to text anonymization",
                    session_id=session.id if session else "unknown",
                    user_id=session.user_id if session else "unknown",
                    request_id=request_id,
                    user_override=result["user_preference_override"],
                    extra={"privacy_event": "anonymization_enabled", "next_step": "AnonymizeText"},
                )
            else:
                # Route directly to workflow initialization
                result["anonymization_required"] = False
                result["decision"] = "anonymize_disabled"
                result["next_step"] = "InitAgent"
                result["ready_for_anonymization"] = False
                result["ready_for_workflow_init"] = True

                logger.info(
                    "Privacy anonymization disabled - routing to workflow initialization",
                    session_id=session.id if session else "unknown",
                    user_id=session.user_id if session else "unknown",
                    request_id=request_id,
                    extra={"privacy_event": "anonymization_disabled", "next_step": "InitAgent"},
                )

            # Step 4: Populate privacy settings for context
            result["privacy_settings"] = {
                "global_anonymization": settings.PRIVACY_ANONYMIZE_REQUESTS,
                "effective_anonymization": privacy_enabled,
                "user_preference_override": result["user_preference_override"],
                "environment": result["environment"],
            }

            # Complete logging
            session_id = session.id if session else "unknown"
            user_id = session.user_id if session else "unknown"

            rag_step_log(
                step=6,
                step_id="RAG.privacy.privacy.anonymize.requests.enabled",
                node_label="PrivacyCheck",
                processing_stage="completed",
                privacy_enabled=result["privacy_enabled"],
                anonymization_required=result["anonymization_required"],
                decision=result["decision"],
                next_step=result["next_step"],
                ready_for_anonymization=result["ready_for_anonymization"],
                ready_for_workflow_init=result["ready_for_workflow_init"],
                user_preference_override=result["user_preference_override"],
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
            )

            return result

        except Exception as e:
            # Handle any unexpected errors - default to safe behavior
            error_msg = f"Privacy check error: {str(e)}"
            result["error"] = error_msg
            result["privacy_enabled"] = True  # Default to privacy enabled for safety
            result["anonymization_required"] = True
            result["decision"] = "anonymize_enabled_fallback"
            result["next_step"] = "AnonymizeText"
            result["ready_for_anonymization"] = True

            session_id = session.id if session else "unknown"
            user_id = session.user_id if session else "unknown"

            logger.error(
                "Privacy check failed - defaulting to privacy enabled",
                error=str(e),
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                exc_info=True,
            )

            rag_step_log(
                step=6,
                step_id="RAG.privacy.privacy.anonymize.requests.enabled",
                node_label="PrivacyCheck",
                processing_stage="completed",
                error=str(e),
                privacy_enabled=True,
                anonymization_required=True,
                decision="anonymize_enabled_fallback",
                next_step="AnonymizeText",
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
            )

            return result


async def step_7__anonymize_text(
    *, messages: list[Any] | None = None, ctx: dict[str, Any] | None = None, **kwargs
) -> Any:
    """RAG STEP 7 — Anonymizer.anonymize_text Anonymize PII
    ID: RAG.privacy.anonymizer.anonymize.text.anonymize.pii
    Type: process | Category: privacy | Node: AnonymizeText

    Anonymizes PII in message content using the privacy anonymizer service.
    This orchestrator coordinates text anonymization before workflow initialization.
    """
    from datetime import datetime, timezone

    from app.core.logging import logger
    from app.core.privacy.anonymizer import anonymizer

    with rag_step_timer(7, "RAG.privacy.anonymizer.anonymize.text.anonymize.pii", "AnonymizeText", stage="start"):
        rag_step_log(
            step=7,
            step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
            node_label="AnonymizeText",
            category="privacy",
            type="process",
            processing_stage="started",
        )

        # Extract context parameters
        context = ctx or {}
        validated_request = kwargs.get("validated_request") or context.get("validated_request")
        session = kwargs.get("session") or context.get("session")
        user = kwargs.get("user") or context.get("user")
        request_metadata = kwargs.get("request_metadata") or context.get("request_metadata", {})
        request_id = request_metadata.get("request_id", "unknown")

        # Initialize result structure
        result = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "anonymization_completed": False,
            "pii_detected": False,
            "pii_anonymized": False,
            "anonymized_messages": [],
            "pii_matches": [],
            "next_step": "InitAgent",
            "ready_for_workflow_init": False,
            "validated_request": validated_request,
            "session": session,
            "user": user,
            "error": None,
        }

        try:
            # Step 1: Validate input
            if not validated_request or not validated_request.get("messages"):
                result["error"] = "Missing validated request or messages"
                logger.error("Anonymization failed: Missing messages", request_id=request_id)
                rag_step_log(
                    step=7,
                    step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
                    node_label="AnonymizeText",
                    processing_stage="completed",
                    error="missing_messages",
                    anonymization_completed=False,
                    request_id=request_id,
                )
                return result

            # Step 2: Anonymize each message
            anonymized_messages = []
            all_pii_matches = []

            for message in validated_request["messages"]:
                if isinstance(message, dict) and "content" in message:
                    # Anonymize the message content
                    anonymization_result = anonymizer.anonymize_text(message["content"])

                    # Create anonymized message
                    anonymized_message = message.copy()
                    anonymized_message["content"] = anonymization_result.anonymized_text
                    anonymized_messages.append(anonymized_message)

                    # Collect PII matches
                    if anonymization_result.pii_matches:
                        all_pii_matches.extend(anonymization_result.pii_matches)
                else:
                    # Preserve non-dict messages or messages without content
                    anonymized_messages.append(message)

            # Step 3: Update result with anonymized data
            result["anonymization_completed"] = True
            result["pii_detected"] = len(all_pii_matches) > 0
            result["pii_anonymized"] = len(all_pii_matches) > 0
            result["anonymized_messages"] = anonymized_messages
            result["pii_matches"] = [
                {"pii_type": match.pii_type.value, "anonymized": True} for match in all_pii_matches
            ]
            result["ready_for_workflow_init"] = True

            # Update validated request with anonymized messages
            result["validated_request"] = validated_request.copy()
            result["validated_request"]["messages"] = anonymized_messages

            session_id = session.id if session else "unknown"
            user_id = session.user_id if session else "unknown"

            logger.info(
                "Text anonymization completed",
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                pii_detected=result["pii_detected"],
                pii_count=len(all_pii_matches),
                message_count=len(anonymized_messages),
                extra={
                    "privacy_event": "text_anonymized",
                    "pii_detected": result["pii_detected"],
                    "pii_count": len(all_pii_matches),
                },
            )

            rag_step_log(
                step=7,
                step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
                node_label="AnonymizeText",
                processing_stage="completed",
                anonymization_completed=True,
                pii_detected=result["pii_detected"],
                pii_anonymized=result["pii_anonymized"],
                pii_count=len(all_pii_matches),
                message_count=len(anonymized_messages),
                next_step="InitAgent",
                ready_for_workflow_init=True,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
            )

            return result

        except Exception as e:
            # Handle anonymization errors
            result["error"] = f"Anonymization error: {str(e)}"
            result["ready_for_workflow_init"] = True  # Continue workflow even if anonymization fails

            session_id = session.id if session else "unknown"
            user_id = session.user_id if session else "unknown"

            logger.error(
                "Text anonymization failed",
                error=str(e),
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
                exc_info=True,
            )

            rag_step_log(
                step=7,
                step_id="RAG.privacy.anonymizer.anonymize.text.anonymize.pii",
                node_label="AnonymizeText",
                processing_stage="completed",
                error=str(e),
                anonymization_completed=False,
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
            )

            return result
