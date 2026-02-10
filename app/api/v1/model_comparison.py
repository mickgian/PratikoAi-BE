"""Model Comparison API Endpoints (DEV-256).

Provides REST API endpoints for SUPER_USERs to:
- Run multi-model LLM comparisons
- Vote for best responses (Elo rating)
- Manage model preferences
- View leaderboard and statistics
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.logging import logger
from app.models.database import get_db
from app.models.user import User, UserRole
from app.schemas.comparison import (
    AvailableModelsResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonStatsResponse,
    ComparisonWithExistingRequest,
    CreatePendingComparisonRequest,
    LeaderboardResponse,
    ModelPreferencesRequest,
    PendingComparisonData,
    PendingComparisonResponse,
    VoteRequest,
    VoteResponse,
)
from app.services.comparison_service import get_comparison_service

router = APIRouter(prefix="/model-comparison", tags=["Model Comparison"])


def _require_super_user(user: User) -> None:
    """Validate user has SUPER_USER or ADMIN role.

    Args:
        user: Authenticated user

    Raises:
        HTTPException: 403 if user lacks required role
    """
    if user.role not in [UserRole.SUPER_USER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso non autorizzato",
        )


@router.post("/compare", response_model=ComparisonResponse)
async def run_comparison(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Run a multi-model comparison.

    Sends the same query to multiple LLM models in parallel and returns
    all responses for comparison.

    Args:
        request: Comparison request with query and optional model_ids
        current_user: Authenticated user
        db: Database session

    Returns:
        ComparisonResponse with all model responses

    Raises:
        HTTPException: 403 if not SUPER_USER, 400/500 on validation/execution errors
    """
    _require_super_user(current_user)

    service = get_comparison_service()

    try:
        result = await service.run_comparison(
            query=request.query,
            user_id=current_user.id,
            db=db,
            model_ids=request.model_ids,
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        logger.warning(
            "comparison_validation_error",
            user_id=current_user.id,
            error=error_msg,
        )
        # Determine appropriate status code based on error message
        if "fallito" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.post("/compare-with-existing", response_model=ComparisonResponse)
async def run_comparison_with_existing(
    request: ComparisonWithExistingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonResponse:
    """Run comparison using an existing response for the current model.

    This endpoint avoids re-calling the current model by reusing the response
    already obtained in the main chat. Only calls the 4 other best models,
    saving cost on the current model.

    Args:
        request: Request with query and existing response from main chat
        current_user: Authenticated user
        db: Database session

    Returns:
        ComparisonResponse with all model responses (existing + new)

    Raises:
        HTTPException: 403 if not SUPER_USER, 400/500 on validation/execution errors
    """
    _require_super_user(current_user)

    service = get_comparison_service()

    try:
        result = await service.run_comparison_with_existing(
            query=request.query,
            user_id=current_user.id,
            db=db,
            existing_response=request.existing_response,
            enriched_prompt=request.enriched_prompt,
            model_ids=request.model_ids,
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        logger.warning(
            "comparison_with_existing_validation_error",
            user_id=current_user.id,
            error=error_msg,
        )
        # Determine appropriate status code based on error message
        if "fallito" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.post("/vote", response_model=VoteResponse)
async def submit_vote(
    request: VoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoteResponse:
    """Submit a vote for the best model in a comparison.

    Updates Elo ratings based on the vote.

    Args:
        request: Vote request with batch_id and winner_model_id
        current_user: Authenticated user
        db: Database session

    Returns:
        VoteResponse with success status and Elo changes

    Raises:
        HTTPException: 403 if not SUPER_USER, 400/404/409 on validation errors
    """
    _require_super_user(current_user)

    service = get_comparison_service()

    try:
        result = await service.submit_vote(
            batch_id=request.batch_id,
            winner_model_id=request.winner_model_id,
            user_id=current_user.id,
            db=db,
            comment=request.comment,
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        logger.warning(
            "vote_validation_error",
            user_id=current_user.id,
            batch_id=request.batch_id,
            error=error_msg,
        )

        # Determine appropriate status code
        if "non trovata" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        if "già registrato" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.get("/models", response_model=AvailableModelsResponse)
async def get_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AvailableModelsResponse:
    """Get all available models with user preferences.

    Returns the list of all configured models with their Elo ratings
    and whether they are enabled for the current user.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        AvailableModelsResponse with list of models
    """
    _require_super_user(current_user)

    service = get_comparison_service()
    models = await service.get_available_models(current_user.id, db)

    return AvailableModelsResponse(models=models)


@router.put("/models/preferences")
async def update_preferences(
    request: ModelPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update user model preferences.

    Sets which models are enabled for the user's comparisons.

    Args:
        request: Preferences request with enabled_model_ids
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    _require_super_user(current_user)

    service = get_comparison_service()
    await service.update_preferences(
        user_id=current_user.id,
        enabled_model_ids=request.enabled_model_ids,
        db=db,
    )

    logger.info(
        "preferences_updated",
        user_id=current_user.id,
        enabled_count=len(request.enabled_model_ids),
    )

    return {"message": "Preferenze aggiornate con successo"}


@router.get("/stats", response_model=ComparisonStatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonStatsResponse:
    """Get user comparison statistics.

    Returns stats about the user's comparison activity.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        ComparisonStatsResponse with user statistics
    """
    _require_super_user(current_user)

    service = get_comparison_service()
    stats = await service.get_user_stats(current_user.id, db)

    return ComparisonStatsResponse(stats=stats)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=20, le=100, ge=1),
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    """Get the model leaderboard.

    Returns models ranked by Elo rating. This endpoint is public
    (no authentication required) to allow viewing the leaderboard.

    Args:
        limit: Maximum number of results (default 20, max 100)
        db: Database session

    Returns:
        LeaderboardResponse with ranked models
    """
    service = get_comparison_service()
    rankings = await service.get_leaderboard(db, limit=limit)

    return LeaderboardResponse(
        rankings=rankings,
        last_updated=datetime.utcnow(),
    )


@router.post("/pending", response_model=PendingComparisonResponse)
async def create_pending_comparison(
    request: CreatePendingComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingComparisonResponse:
    """Store pending comparison data from main chat.

    Creates a temporary record with the query and response from main chat,
    allowing the comparison page to retrieve it. Records expire after 1 hour.

    Args:
        request: Request with query, response, model_id, and metrics
        current_user: Authenticated user
        db: Database session

    Returns:
        PendingComparisonResponse with the pending_id UUID

    Raises:
        HTTPException: 403 if not SUPER_USER
    """
    _require_super_user(current_user)

    service = get_comparison_service()
    pending_id = await service.create_pending_comparison(
        user_id=current_user.id,
        query=request.query,
        response=request.response,
        model_id=request.model_id,
        db=db,
        enriched_prompt=request.enriched_prompt,
        latency_ms=request.latency_ms,
        cost_eur=request.cost_eur,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        trace_id=request.trace_id,
    )

    logger.info(
        "pending_comparison_created",
        user_id=current_user.id,
        pending_id=pending_id,
        model_id=request.model_id,
        has_enriched_prompt=request.enriched_prompt is not None,
        has_metrics=request.latency_ms is not None,
    )

    return PendingComparisonResponse(pending_id=pending_id)


@router.get("/pending/{pending_id}", response_model=PendingComparisonData)
async def get_pending_comparison(
    pending_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingComparisonData:
    """Retrieve and delete pending comparison data.

    Retrieves the pending comparison data and deletes it (one-time use).
    Only the user who created the pending comparison can retrieve it.

    Args:
        pending_id: UUID of the pending comparison
        current_user: Authenticated user
        db: Database session

    Returns:
        PendingComparisonData with query, response, and model_id

    Raises:
        HTTPException: 403 if not SUPER_USER, 404 if not found or wrong user
    """
    _require_super_user(current_user)

    service = get_comparison_service()
    data = await service.get_pending_comparison(
        pending_id=pending_id,
        user_id=current_user.id,
        db=db,
    )

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Confronto pendente non trovato",
        )

    logger.info(
        "pending_comparison_retrieved",
        user_id=current_user.id,
        pending_id=pending_id,
    )

    return data
