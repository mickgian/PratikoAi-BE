"""Expert Feedback API Endpoints.

Provides REST API endpoints for:
- Submitting expert feedback on AI responses
- Retrieving feedback history
- Getting feedback details
- Accessing expert profile

All endpoints require authentication and verified expert status.
"""

import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.models.database import AsyncSessionLocal, get_db
from app.models.quality_analysis import (
    ExpertFeedback,
    ExpertProfile,
    FeedbackType,
    ItalianFeedbackCategory,
)
from app.models.user import User, UserRole
from app.schemas.expert_feedback import (
    ExpertProfileResponse,
    FeedbackDetailResponse,
    FeedbackHistoryResponse,
    FeedbackRecord,
    FeedbackResult,
    FeedbackSubmission,
)
from app.services.task_generator_service import TaskGeneratorService

router = APIRouter(prefix="/expert-feedback", tags=["Expert Feedback"])


async def _trigger_golden_set_workflow(feedback_id: UUID, expert_id: UUID) -> None:
    """Trigger S127-S130: Golden Set candidate proposal and publishing.

    This async helper function implements the workflow integration between expert feedback
    collection and the Golden Set update pipeline. When an expert marks an answer as CORRECT,
    we automatically propose it as a FAQ candidate for the Golden Set.

    This function runs as a background task (fire-and-forget) to not block the API response.
    Creates its own database session to avoid using the closed request session.

    Steps:
    1. S127: Propose FAQ candidate from expert feedback
    2. S128: Check auto-approval threshold (based on expert trust score)
    3. S129: Publish to Golden Set if approved
    4. S130: Cache invalidation (handled in step_129)

    Args:
        feedback_id: UUID of the ExpertFeedback record
        expert_id: UUID of the ExpertProfile providing feedback
    """
    # Create new session for background task (request session will be closed)
    async with AsyncSessionLocal() as db:
        try:
            # Load feedback and expert from database
            feedback = await db.get(ExpertFeedback, feedback_id)
            expert = await db.get(ExpertProfile, expert_id)

            if not feedback or not expert:
                logger.error(f"Failed to load feedback {feedback_id} or expert {expert_id}")
                return

            # Load user to get role for ADMIN quality_score override
            from app.models.user import User

            user = await db.get(User, expert.user_id)
            if not user:
                logger.error(f"Failed to load user {expert.user_id} for expert {expert_id}")
                return

            from app.orchestrators.golden import (
                step_127__golden_candidate,
                step_128__golden_approval,
                step_129__publish_golden,
            )

            # Build context for Golden Set workflow
            # This matches the expected structure from the orchestrator
            ctx = {
                "request_id": f"feedback_{feedback.id}",
                "expert_feedback": {
                    "id": str(feedback.id),
                    "query_text": feedback.query_text,
                    "expert_answer": feedback.expert_answer or feedback.original_answer,
                    "category": feedback.category if feedback.category else "generale",
                    "regulatory_references": feedback.regulatory_references,
                    "confidence_score": feedback.confidence_score,
                    "frequency": 1,
                    "feedback_type": feedback.feedback_type if feedback.feedback_type else None,
                },
                "expert_id": str(expert.id),
                "trust_score": expert.trust_score,
                "user_role": user.role,  # Include user role for ADMIN quality_score override
                "db_session": db,  # CRITICAL FIX: Pass database session to Steps 127-129 for FAQ persistence
            }

            # S127: Propose candidate from expert feedback
            logger.info(f"S127: Proposing Golden Set candidate from feedback {feedback.id}")
            result_127 = await step_127__golden_candidate(ctx=ctx)

            if not result_127.get("faq_candidate"):
                logger.info(f"S127: No candidate proposed for feedback {feedback.id}")
                feedback.task_creation_success = False
                await db.commit()
                return

            logger.info(
                f"S127: Candidate proposed with priority_score={result_127['faq_candidate'].get('priority_score')}"
            )

            # S128: Check approval threshold
            logger.info(f"S128: Checking approval threshold for candidate from feedback {feedback.id}")
            result_128 = await step_128__golden_approval(ctx=result_127)

            approval_decision = result_128.get("approval_decision", {})
            # Handle both dict and string formats for backwards compatibility
            if isinstance(approval_decision, dict):
                approval_status = approval_decision.get("status")
            elif isinstance(approval_decision, str):
                approval_status = approval_decision
            else:
                approval_status = None

            if approval_status not in ["auto_approved", "manual_approved"]:
                logger.info(f"S128: Candidate not approved for feedback {feedback.id}: {approval_status}")
                feedback.task_creation_success = False
                await db.commit()
                return

            logger.info(f"S128: Candidate approved ({approval_status}) for feedback {feedback.id}")

            # S129: Publish to Golden Set
            logger.info(f"S129: Publishing to Golden Set from feedback {feedback.id}")
            result_129 = await step_129__publish_golden(ctx=result_128)

            # Extract FAQ ID from published_faq object
            published_faq = result_129.get("published_faq", {})
            faq_id = published_faq.get("id") if isinstance(published_faq, dict) else None
            if faq_id:
                # Update feedback record with generated FAQ ID
                feedback.generated_faq_id = faq_id
                feedback.task_creation_success = True
                await db.commit()

                logger.info(
                    f"✅ S129: Published FAQ {faq_id} from feedback {feedback.id}. "
                    f"Version: {result_129.get('version', 'N/A')}"
                )

                # S130: Cache invalidation (handled automatically in step_129)
                logger.info(f"S130: Cache invalidation triggered for FAQ {faq_id}")
            else:
                feedback.task_creation_success = False
                await db.commit()
                logger.warning(f"S129: Failed to publish FAQ from feedback {feedback.id}")

        except ImportError as e:
            logger.error(
                f"Failed to import Golden Set orchestrator steps: {e}. "
                f"Feedback {feedback_id} stored but not added to Golden Set."
            )
            if feedback:
                feedback.task_creation_success = False
                feedback.task_creation_error = f"Import error: {str(e)}"
                await db.commit()

        except Exception as e:
            logger.error(
                f"Failed to process Golden Set workflow for feedback {feedback_id}: {e}",
                exc_info=True,
            )
            if feedback:
                feedback.task_creation_success = False
                feedback.task_creation_error = str(e)
                await db.commit()


@router.post("/submit", response_model=FeedbackResult, status_code=status.HTTP_201_CREATED)
async def submit_expert_feedback(
    submission: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit expert feedback on AI response.

    Requirements:
    - User must be a SUPER_USER (role-based access control)
    - User must have expert profile
    - Expert must be active and verified

    For 'incomplete' or 'incorrect' feedback with additional_details:
    - Automatically creates task in SUPER_USER_TASKS.md (async, non-blocking)
    - Tracks task in expert_generated_tasks table

    Args:
        submission: Feedback submission data
        current_user: Authenticated user
        db: Database session

    Returns:
        FeedbackResult with feedback_id, task_id (if created), and metadata

    Raises:
        403: User is not a SUPER_USER, not an expert, or not verified
        500: Internal server error during feedback processing
    """
    try:
        # Validate user role (only SUPER_USER and ADMIN can give feedback)
        if current_user.role not in [UserRole.SUPER_USER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super users can provide feedback on AI responses",
            )

        # Get expert profile
        result = await db.execute(select(ExpertProfile).where(ExpertProfile.user_id == current_user.id))
        expert = result.scalar_one_or_none()

        # Validate expert exists
        if not expert:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not an expert")

        # Validate expert is active and verified
        if not expert.is_active or not expert.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Expert profile is not active or verified",
            )

        logger.info(
            f"Expert {expert.id} (user {current_user.id}) submitting feedback " f"for query {submission.query_id}"
        )

        # Create feedback record (convert string values to enum instances)
        feedback = ExpertFeedback(
            query_id=submission.query_id,
            expert_id=expert.id,
            feedback_type=FeedbackType(submission.feedback_type),
            category=ItalianFeedbackCategory(submission.category) if submission.category else None,
            query_text=submission.query_text,
            original_answer=submission.original_answer,
            expert_answer=submission.expert_answer,
            improvement_suggestions=submission.improvement_suggestions or [],
            regulatory_references=submission.regulatory_references or [],
            confidence_score=submission.confidence_score,
            time_spent_seconds=submission.time_spent_seconds,
            complexity_rating=submission.complexity_rating,
            additional_details=submission.additional_details,
            task_creation_attempted=False,  # Will be set to True if task creation is attempted
        )

        db.add(feedback)
        await db.flush()  # Get feedback.id before commit

        logger.info(f"Created feedback record {feedback.id}")

        # Mark if task creation will be attempted (but don't start yet - wait for commit)
        should_generate_task = submission.additional_details and submission.feedback_type in [
            "incomplete",
            "incorrect",
        ]
        should_generate_faq = submission.feedback_type == "correct"

        if should_generate_task or should_generate_faq:
            feedback.task_creation_attempted = True

        # Commit feedback record FIRST (before background tasks)
        await db.commit()
        await db.refresh(feedback)

        # NOW start background tasks AFTER commit (so they can query the committed record)

        # Async task generation (fire and forget) for incomplete/incorrect feedback
        if should_generate_task:
            logger.info(f"Triggering async task generation for feedback {feedback.id}")

            # Create background task (fire and forget - doesn't block response)
            # Pass IDs instead of session - service will create its own session
            asyncio.create_task(
                TaskGeneratorService().generate_task_from_feedback(feedback_id=feedback.id, expert_id=expert.id)
            )

        # Golden Set workflow integration for CORRECT feedback
        # S127-S130: Propose and publish FAQ candidate from expert feedback
        if should_generate_faq:
            logger.info(
                f"Triggering Golden Set workflow for CORRECT feedback {feedback.id}",
                extra={
                    "feedback_id": str(feedback.id),
                    "expert_id": str(expert.id),
                    "trust_score": expert.trust_score,
                },
            )

            # Create background task (fire and forget - doesn't block response)
            # Pass IDs instead of session - function will create its own session
            asyncio.create_task(_trigger_golden_set_workflow(feedback.id, expert.id))

        logger.info(
            f"Feedback {feedback.id} submitted successfully. Task creation attempted: "
            f"{feedback.task_creation_attempted}, FAQ generated: {feedback.generated_faq_id is not None}"
        )

        return FeedbackResult(
            feedback_id=feedback.id,
            feedback_type=feedback.feedback_type,
            expert_trust_score=expert.trust_score,
            task_creation_attempted=feedback.task_creation_attempted,
            generated_task_id=feedback.generated_task_id,
            generated_faq_id=feedback.generated_faq_id,
            message="Feedback submitted successfully",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}",
        )


@router.get("/history", response_model=FeedbackHistoryResponse)
async def get_feedback_history(
    limit: int = 20,
    offset: int = 0,
    feedback_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get feedback history for current expert.

    Returns paginated list of feedback records submitted by the current expert.
    Optionally filter by feedback_type.

    Args:
        limit: Page size (max 100)
        offset: Offset for pagination
        feedback_type: Optional filter by 'correct', 'incomplete', or 'incorrect'
        current_user: Authenticated user
        db: Database session

    Returns:
        FeedbackHistoryResponse with paginated feedback records

    Raises:
        403: User is not an expert
        422: Invalid feedback_type filter
    """
    # Validate pagination params
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 20
    if offset < 0:
        offset = 0

    try:
        # Get expert profile
        result = await db.execute(select(ExpertProfile).where(ExpertProfile.user_id == current_user.id))
        expert = result.scalar_one_or_none()

        if not expert:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not an expert")

        # Build base query
        query = select(ExpertFeedback).where(ExpertFeedback.expert_id == expert.id)

        # Apply feedback_type filter if provided
        if feedback_type:
            if feedback_type not in ["correct", "incomplete", "incorrect"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid feedback_type: {feedback_type}",
                )
            query = query.where(ExpertFeedback.feedback_type == feedback_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Get paginated results
        query = query.order_by(ExpertFeedback.feedback_timestamp.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        feedbacks = result.scalars().all()

        logger.info(
            f"Retrieved {len(feedbacks)} feedback records for expert {expert.id} "
            f"(total: {total_count}, offset: {offset})"
        )

        return FeedbackHistoryResponse(
            total_count=total_count,
            limit=limit,
            offset=offset,
            items=[
                FeedbackRecord(
                    id=f.id,
                    query_id=f.query_id,
                    feedback_type=f.feedback_type,
                    category=f.category if f.category else None,
                    query_text=f.query_text,
                    original_answer=f.original_answer,
                    expert_answer=f.expert_answer,
                    confidence_score=f.confidence_score,
                    time_spent_seconds=f.time_spent_seconds,
                    complexity_rating=f.complexity_rating,
                    feedback_timestamp=f.feedback_timestamp,
                    generated_task_id=f.generated_task_id,
                    generated_faq_id=f.generated_faq_id,
                    task_creation_success=f.task_creation_success,
                )
                for f in feedbacks
            ],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedback history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback history: {str(e)}",
        )


@router.get("/{feedback_id}", response_model=FeedbackDetailResponse)
async def get_feedback_detail(
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed feedback record.

    Returns complete feedback record including all fields.
    User can only view their own feedback (ownership check).

    Args:
        feedback_id: UUID of feedback record
        current_user: Authenticated user
        db: Database session

    Returns:
        FeedbackDetailResponse with complete feedback details

    Raises:
        403: User is not authorized to view this feedback
        404: Feedback not found
    """
    try:
        # Get feedback record
        result = await db.execute(select(ExpertFeedback).where(ExpertFeedback.id == feedback_id))
        feedback = result.scalar_one_or_none()

        if not feedback:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

        # Verify ownership (expert can only see their own feedback)
        result = await db.execute(select(ExpertProfile).where(ExpertProfile.user_id == current_user.id))
        expert = result.scalar_one_or_none()

        if not expert or feedback.expert_id != expert.id:
            # TODO: Allow admins to view all feedback
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this feedback",
            )

        logger.info(f"Retrieved feedback detail {feedback_id} for expert {expert.id}")

        return FeedbackDetailResponse(
            id=feedback.id,
            query_id=feedback.query_id,
            feedback_type=feedback.feedback_type,
            category=feedback.category if feedback.category else None,
            query_text=feedback.query_text,
            original_answer=feedback.original_answer,
            expert_answer=feedback.expert_answer,
            improvement_suggestions=feedback.improvement_suggestions,
            regulatory_references=feedback.regulatory_references,
            confidence_score=feedback.confidence_score,
            time_spent_seconds=feedback.time_spent_seconds,
            complexity_rating=feedback.complexity_rating,
            additional_details=feedback.additional_details,
            feedback_timestamp=feedback.feedback_timestamp,
            generated_task_id=feedback.generated_task_id,
            generated_faq_id=feedback.generated_faq_id,
            task_creation_attempted=feedback.task_creation_attempted,
            task_creation_success=feedback.task_creation_success,
            task_creation_error=feedback.task_creation_error,
            action_taken=feedback.action_taken,
            improvement_applied=feedback.improvement_applied,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedback detail: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback detail: {str(e)}",
        )


@router.get("/experts/me/profile", response_model=ExpertProfileResponse)
async def get_my_expert_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's expert profile.

    Returns complete expert profile with credentials, metrics, and status.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        ExpertProfileResponse with profile data

    Raises:
        404: Expert profile not found for this user
    """
    try:
        # Get expert profile
        result = await db.execute(select(ExpertProfile).where(ExpertProfile.user_id == current_user.id))
        expert = result.scalar_one_or_none()

        if not expert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert profile not found for this user",
            )

        logger.info(f"Retrieved expert profile {expert.id} for user {current_user.id}")

        return ExpertProfileResponse(
            id=expert.id,
            user_id=expert.user_id,
            role=current_user.role,
            credentials=expert.credentials,
            credential_types=expert.credential_types,  # Already stored as strings
            experience_years=expert.experience_years,
            specializations=expert.specializations,
            feedback_count=expert.feedback_count,
            feedback_accuracy_rate=expert.feedback_accuracy_rate,
            average_response_time_seconds=expert.average_response_time_seconds,
            trust_score=expert.trust_score,
            professional_registration_number=expert.professional_registration_number,
            organization=expert.organization,
            location_city=expert.location_city,
            is_verified=expert.is_verified,
            verification_date=expert.verification_date,
            is_active=expert.is_active,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving expert profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve expert profile: {str(e)}",
        )
