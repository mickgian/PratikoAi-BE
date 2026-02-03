"""This file contains the main application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    Dict,
)

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    Response,
)
from langfuse import Langfuse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import setup_metrics
from app.core.middleware import MetricsMiddleware
from app.core.middleware.cost_limiter import (
    CostLimiterMiddleware,
    CostOptimizationMiddleware,
)
from app.core.middleware.prometheus_middleware import PrometheusMiddleware
from app.core.monitoring.metrics import get_metrics_content
from app.services.database import database_service

# Load environment variables
load_dotenv()

# Initialize Langfuse
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
)


async def check_pgvector_availability() -> bool:
    """Check if pgvector extension is available in the database."""
    try:
        from sqlalchemy import text

        from app.models.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "SELECT installed_version FROM pg_available_extensions WHERE name='vector' AND installed_version IS NOT NULL"
                )
            )
            return result.scalar() is not None
    except Exception as e:
        logger.warning("pgvector_check_failed", error=str(e))
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    logger.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
    )

    # Log Hybrid RAG configuration and capabilities
    from app.core.config import (
        CHUNK_OVERLAP,
        CHUNK_TOKENS,
        CONTEXT_TOP_K,
        EMBED_DIM,
        EMBED_MODEL,
        HYBRID_WEIGHT_FTS,
        HYBRID_WEIGHT_RECENCY,
        HYBRID_WEIGHT_VEC,
    )

    # Check pgvector availability
    pgvector_available = await check_pgvector_availability()
    retrieval_mode = "Hybrid (FTS + Vector + Recency)" if pgvector_available else "FTS-only (Vector unavailable)"

    logger.info(
        "retrieval_capabilities",
        mode=retrieval_mode,
        pgvector_enabled=pgvector_available,
        embed_model=EMBED_MODEL,
        embed_dim=EMBED_DIM,
        chunk_tokens=CHUNK_TOKENS,
        chunk_overlap=f"{CHUNK_OVERLAP:.0%}",
        weights=f"FTS={HYBRID_WEIGHT_FTS:.2f}, VEC={HYBRID_WEIGHT_VEC:.2f}, RECENCY={HYBRID_WEIGHT_RECENCY:.2f}",
        context_top_k=CONTEXT_TOP_K,
    )

    # Start the scheduler service for RSS feed collection
    from app.services.scheduler_service import (
        start_scheduler,
        stop_scheduler,
    )

    logger.info("Starting scheduler service for RSS feed collection...")
    await start_scheduler()
    logger.info("Scheduler service started successfully")

    # DEV-251: Pre-warm HuggingFace classifier in background thread
    # This prevents the first user query from waiting for model download/load (~5-30s)
    from concurrent.futures import ThreadPoolExecutor

    from app.services.hf_intent_classifier import get_hf_intent_classifier

    def warmup_hf_classifier() -> None:
        """Load HuggingFace model in background to avoid first-query latency."""
        try:
            classifier = get_hf_intent_classifier()
            # Trigger model load with a simple query
            classifier.classify("warmup query")
            logger.info("hf_classifier_warmed_up", model=classifier.model_name)
        except Exception as e:
            # Don't fail startup if warmup fails - will lazy load on first real query
            logger.warning(
                "hf_classifier_warmup_failed",
                error_type=type(e).__name__,
                error_message=str(e),
            )

    # Run in background thread to not block startup
    warmup_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hf-warmup-")
    loop = asyncio.get_running_loop()
    loop.run_in_executor(warmup_executor, warmup_hf_classifier)
    logger.info("hf_classifier_warmup_started")

    yield

    # Stop the scheduler service during shutdown
    logger.info("Stopping scheduler service...")
    await stop_scheduler()
    logger.info("Scheduler service stopped")
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up Prometheus metrics
setup_metrics(app)

# Add custom metrics middleware
app.add_middleware(MetricsMiddleware)

# Set up rate limiter exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Add validation exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from request data.

    Args:
        request: The request that caused the validation error
        exc: The validation error

    Returns:
        JSONResponse: A formatted error response
    """
    # Log the validation error
    logger.error(
        "validation_error",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        errors=str(exc.errors()),
    )

    # Format the errors to be more user-friendly
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join([str(loc_part) for loc_part in error["loc"] if loc_part != "body"])
        formatted_errors.append({"field": loc, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": formatted_errors},
    )


# Set up middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add cost limiter middleware for payment enforcement
app.add_middleware(CostLimiterMiddleware)
app.add_middleware(CostOptimizationMiddleware)
app.add_middleware(PrometheusMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request):
    """Root endpoint returning basic API information."""
    logger.info("root_endpoint_called")
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT.value,
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(request: Request) -> dict[str, Any]:
    """Health check endpoint with environment-specific information.

    Returns:
        Dict[str, Any]: Health status information
    """
    logger.info("health_check_called")

    # Check database connectivity
    db_healthy = await database_service.health_check()

    # Check cache connectivity
    from app.services.cache import cache_service

    cache_healthy = await cache_service.health_check()

    # Overall system health
    overall_healthy = db_healthy and cache_healthy

    response = {
        "status": "healthy" if overall_healthy else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {
            "api": "healthy",
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy",
        },
        "timestamp": datetime.now().isoformat(),
    }

    # If any critical component is unhealthy, set the appropriate status code
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint for scraping."""
    from fastapi.responses import PlainTextResponse
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from prometheus_client import REGISTRY as DEFAULT_REGISTRY

    try:
        # Get metrics from both registries
        custom_metrics = get_metrics_content()
        default_metrics = generate_latest(DEFAULT_REGISTRY).decode("utf-8")

        # Combine both metric sets
        combined_metrics = default_metrics + "\n" + custom_metrics

        return Response(content=combined_metrics, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error("metrics_endpoint_failed", error=str(e), exc_info=True)
        return PlainTextResponse("# Metrics unavailable\n", status_code=500)
