"""API v1 router configuration.

This module sets up the main API router and includes all sub-routers for different
endpoints like authentication and chatbot functionality.
"""

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.ccnl_calculations import router as ccnl_calculations_router
from app.api.v1.ccnl_search import router as ccnl_search_router
from app.api.v1.chatbot import router as chatbot_router

# Wave 4: New API routers (DEV-311, DEV-312, DEV-332, DEV-342, DEV-373)
from app.api.v1.clients import router as clients_router
from app.api.v1.communications import router as communications_router
from app.api.v1.data_rights import router as data_rights_router
from app.api.v1.data_sources import router as data_sources_router
from app.api.v1.deadlines import router as deadlines_router
from app.api.v1.demo import router as demo_router
from app.api.v1.documents import router as documents_router
from app.api.v1.dpa import router as dpa_router
from app.api.v1.expert_feedback import router as expert_feedback_router
from app.api.v1.features import router as features_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.financial_validation import router as financial_validation_router

# from app.api.v1.gdpr_cleanup import router as gdpr_cleanup_router
from app.api.v1.gdpr_audit import router as gdpr_audit_router
from app.api.v1.health import router as health_router
from app.api.v1.intent_labeling import router as intent_labeling_router
from app.api.v1.italian import router as italian_router
from app.api.v1.matching import router as matching_router
from app.api.v1.model_comparison import router as model_comparison_router

# TEMPORARY: Commented out due to duplicate Subscription model conflict
# TODO: Re-enable after consolidating payment.py and subscription.py models
# from app.api.v1.italian_subscriptions import router as italian_subscriptions_router
# from app.api.v1.data_export import router as data_export_router
# Temporarily disabled routers due to import issues
# from app.api.v1.search import router as search_router
# from app.api.v1.security import router as security_router
# from app.api.v1.performance import router as performance_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.payments import router as payments_router
from app.api.v1.privacy import router as privacy_router
from app.api.v1.procedure import router as procedure_router

# from app.api.v1.faq import router as faq_router
from app.api.v1.regional_taxes import router as regional_taxes_router
from app.api.v1.regulatory import router as regulatory_router
from app.api.v1.release_notes import router as release_notes_router
from app.api.v1.scrapers import router as scrapers_router
from app.api.v1.studio import router as studio_router
from app.api.v1.success_criteria import router as success_criteria_router
from app.core.logging import logger

api_router = APIRouter()

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(privacy_router, prefix="/privacy", tags=["privacy"])
api_router.include_router(italian_router, prefix="/italian", tags=["italian"])
api_router.include_router(expert_feedback_router)  # Includes /expert-feedback prefix from router
api_router.include_router(intent_labeling_router)  # Includes /labeling prefix from router
# TEMPORARY: Commented out due to duplicate Subscription model conflict
# api_router.include_router(italian_subscriptions_router, prefix="/billing", tags=["billing"])
# api_router.include_router(data_export_router, prefix="/gdpr", tags=["data-export"])
# api_router.include_router(search_router, prefix="/search", tags=["search"])
# api_router.include_router(security_router, prefix="/security", tags=["security"])
# api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(regulatory_router, prefix="/regulatory", tags=["regulatory"])
api_router.include_router(scrapers_router, prefix="/scrapers", tags=["scrapers"])
# api_router.include_router(faq_router, tags=["faq"])
api_router.include_router(regional_taxes_router, prefix="/taxes", tags=["regional-taxes"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(demo_router, tags=["demo"])
# api_router.include_router(gdpr_cleanup_router, tags=["gdpr-compliance"])
api_router.include_router(gdpr_audit_router, tags=["gdpr-audit"])
api_router.include_router(financial_validation_router, prefix="/financial", tags=["financial-validation"])
api_router.include_router(ccnl_calculations_router, tags=["ccnl-calculations"])
api_router.include_router(ccnl_search_router, tags=["ccnl-search"])
api_router.include_router(data_sources_router, tags=["data-sources"])
api_router.include_router(success_criteria_router, tags=["success-criteria"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
api_router.include_router(model_comparison_router)  # Includes /model-comparison prefix from router
api_router.include_router(features_router, tags=["features"])
api_router.include_router(release_notes_router)  # Includes /release-notes prefix from router

# Wave 4: New routers (DEV-311, DEV-312, DEV-332, DEV-342, DEV-373)
api_router.include_router(studio_router)  # Includes /studios prefix from router
api_router.include_router(clients_router)  # Includes /clients prefix from router
api_router.include_router(communications_router)  # Includes /communications prefix from router
api_router.include_router(procedure_router)  # Includes /procedure prefix from router
api_router.include_router(dpa_router)  # Includes /dpa prefix from router
api_router.include_router(matching_router)  # Includes /matching prefix from router (DEV-326)
api_router.include_router(data_rights_router)  # Includes /data-rights prefix from router (DEV-377)
api_router.include_router(deadlines_router)  # Includes /deadlines prefix from router (DEV-385)


@api_router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
