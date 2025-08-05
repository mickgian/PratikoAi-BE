"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.payments import router as payments_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.privacy import router as privacy_router
from app.api.v1.italian import router as italian_router
from app.api.v1.search import router as search_router
from app.api.v1.security import router as security_router
from app.api.v1.performance import router as performance_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.regulatory import router as regulatory_router
from app.core.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(privacy_router, prefix="/privacy", tags=["privacy"])
api_router.include_router(italian_router, prefix="/italian", tags=["italian"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(security_router, prefix="/security", tags=["security"])
api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(regulatory_router, prefix="/regulatory", tags=["regulatory"])


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
