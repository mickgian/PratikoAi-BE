"""Feature flags endpoint for frontend consumption.

Returns the current state of feature flags so the frontend can
conditionally enable/disable UI features without redeployment.

Flags are sourced from environment variables (via app.core.config)
with future support for Flagsmith remote configuration.
"""

from fastapi import APIRouter

from app.core import config
from app.core.config import settings

router = APIRouter()


@router.get("/features")
async def get_features() -> dict:
    """Return active feature flags for the frontend.

    Public endpoint - no authentication required.
    Frontend polls this to enable/disable features dynamically.

    Returns:
        Dictionary of feature flag names to boolean values.
    """
    return {
        "features": {
            "web_verification": settings.WEB_VERIFICATION_ENABLED,
            "query_normalization": settings.QUERY_NORMALIZATION_ENABLED,
            "cache": settings.CACHE_ENABLED,
            "ocr": config.OCR_ENABLED,
            "content_structure_validation": settings.ENABLE_CONTENT_STRUCTURE_VALIDATION,
            "slack_notifications": settings.SLACK_ENABLED,
            "external_av_scan": settings.ENABLE_EXTERNAL_AV_SCAN,
        },
        "environment": settings.ENVIRONMENT.value,
    }
