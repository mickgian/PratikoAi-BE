"""API endpoint for /consigli insight report (ADR-038)."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.database import get_db
from app.models.user import User
from app.schemas.consigli import ConsigliReportResponse
from app.services.consigli_service import consigli_service

router = APIRouter()


@router.get("/report", response_model=ConsigliReportResponse)
@limiter.limit("3 per day")
async def generate_consigli_report(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsigliReportResponse:
    """Generate on-demand insight report for the authenticated user.

    Rate limited to 3 per user per 24 hours (RC-2).
    """
    logger.info("consigli_report_requested", user_id=user.id)

    result = await consigli_service.generate_report(user.id, db)

    return ConsigliReportResponse(
        status=result["status"],
        message_it=result["message_it"],
        html_report=result.get("html_report"),
        stats_summary=result.get("stats_summary"),
    )
