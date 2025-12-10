"""Scraper API endpoints for manual triggering of web scrapers.

These endpoints allow manual triggering of Gazzetta Ufficiale and Cassazione
court decision scrapers for document collection and knowledge base enrichment.
"""

import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_session
from app.core.database import get_async_session
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.cassazione_data import CourtSection
from app.models.session import Session
from app.services.scrapers.cassazione_scraper import CassazioneScraper
from app.services.scrapers.gazzetta_scraper import GazzettaScraper

router = APIRouter()


class GazzettaScrapeRequest(BaseModel):
    """Request model for triggering Gazzetta scraping."""

    days_back: int = Field(default=1, ge=1, le=30, description="Number of days to look back")
    filter_tax: bool = Field(default=True, description="Include tax-related documents")
    filter_labor: bool = Field(default=True, description="Include labor-related documents")
    limit: int | None = Field(default=None, ge=1, le=100, description="Maximum documents to scrape")


class CassazioneScrapeRequest(BaseModel):
    """Request model for triggering Cassazione scraping."""

    days_back: int = Field(default=7, ge=1, le=90, description="Number of days to look back")
    sections: list[str] = Field(
        default=["tributaria", "lavoro"], description="Court sections to scrape (tributaria, lavoro, civile, penale)"
    )
    limit: int | None = Field(default=None, ge=1, le=100, description="Maximum decisions to scrape")


class ScrapeResponse(BaseModel):
    """Response model for scraping operations."""

    success: bool
    message: str
    documents_found: int = 0
    documents_processed: int = 0
    documents_saved: int = 0
    errors: int = 0
    duration_seconds: int = 0
    task_id: str | None = None


async def _run_gazzetta_scraping(
    db: AsyncSession,
    days_back: int,
    filter_tax: bool,
    filter_labor: bool,
    limit: int | None,
) -> dict[str, Any]:
    """Background task for Gazzetta scraping."""
    start_time = time.time()
    try:
        async with GazzettaScraper(db_session=db) as scraper:
            result = await scraper.scrape_recent_documents(
                days_back=days_back,
                filter_tax=filter_tax,
                filter_labor=filter_labor,
                limit=limit,
            )

            logger.info(
                "gazzetta_scraping_task_completed",
                documents_found=result.documents_found,
                documents_saved=result.documents_saved,
                errors=result.errors,
            )

            return {
                "success": True,
                "documents_found": result.documents_found,
                "documents_processed": result.documents_processed,
                "documents_saved": result.documents_saved,
                "errors": result.errors,
                "duration_seconds": result.duration_seconds,
            }

    except Exception as e:
        logger.error("gazzetta_scraping_task_failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "duration_seconds": int(time.time() - start_time),
        }


async def _run_cassazione_scraping(
    db: AsyncSession,
    days_back: int,
    sections: list[str],
    limit: int | None,
) -> dict[str, Any]:
    """Background task for Cassazione scraping."""
    start_time = time.time()
    try:
        # Convert section strings to CourtSection enum
        section_map = {
            "tributaria": CourtSection.TRIBUTARIA,
            "lavoro": CourtSection.LAVORO,
            "civile": CourtSection.CIVILE,
            "penale": CourtSection.PENALE,
            "sezioni_unite": CourtSection.SEZIONI_UNITE,
        }
        court_sections = [section_map.get(s.lower(), CourtSection.CIVILE) for s in sections]

        async with CassazioneScraper(db_session=db) as scraper:
            result = await scraper.scrape_recent_decisions(
                sections=court_sections,
                days_back=days_back,
                limit=limit,
            )

            logger.info(
                "cassazione_scraping_task_completed",
                decisions_found=result.decisions_found,
                decisions_saved=result.decisions_saved,
                errors=result.errors,
            )

            return {
                "success": True,
                "documents_found": result.decisions_found,
                "documents_processed": result.decisions_processed,
                "documents_saved": result.decisions_saved,
                "errors": result.errors,
                "duration_seconds": result.duration_seconds,
            }

    except Exception as e:
        logger.error("cassazione_scraping_task_failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "duration_seconds": int(time.time() - start_time),
        }


@router.post(
    "/gazzetta/scrape",
    response_model=ScrapeResponse,
    summary="Trigger Gazzetta Ufficiale scraping",
    description="Manually trigger scraping of Italian Official Gazette documents",
)
@limiter.limit("5 per hour")
async def scrape_gazzetta(
    request: Request,
    scrape_request: GazzettaScrapeRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session),
) -> ScrapeResponse:
    """Trigger Gazzetta Ufficiale scraping.

    This endpoint runs scraping synchronously and returns results.
    For large scraping jobs (days_back > 7), consider using the background option.
    """
    logger.info(
        "gazzetta_scraping_triggered",
        user_id=session.user_id,
        days_back=scrape_request.days_back,
        filter_tax=scrape_request.filter_tax,
        filter_labor=scrape_request.filter_labor,
        limit=scrape_request.limit,
    )

    try:
        result = await _run_gazzetta_scraping(
            db=db,
            days_back=scrape_request.days_back,
            filter_tax=scrape_request.filter_tax,
            filter_labor=scrape_request.filter_labor,
            limit=scrape_request.limit,
        )

        if result.get("success"):
            return ScrapeResponse(
                success=True,
                message="Gazzetta scraping completed successfully",
                documents_found=result.get("documents_found", 0),
                documents_processed=result.get("documents_processed", 0),
                documents_saved=result.get("documents_saved", 0),
                errors=result.get("errors", 0),
                duration_seconds=result.get("duration_seconds", 0),
            )
        else:
            raise HTTPException(status_code=500, detail=f"Scraping failed: {result.get('error')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("gazzetta_scraping_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}") from e


@router.post(
    "/cassazione/scrape",
    response_model=ScrapeResponse,
    summary="Trigger Cassazione court decision scraping",
    description="Manually trigger scraping of Italian Supreme Court decisions",
)
@limiter.limit("5 per hour")
async def scrape_cassazione(
    request: Request,
    scrape_request: CassazioneScrapeRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_async_session),
) -> ScrapeResponse:
    """Trigger Cassazione court decision scraping.

    This endpoint runs scraping synchronously and returns results.
    For large scraping jobs (days_back > 30), consider using the background option.
    """
    logger.info(
        "cassazione_scraping_triggered",
        user_id=session.user_id,
        days_back=scrape_request.days_back,
        sections=scrape_request.sections,
        limit=scrape_request.limit,
    )

    try:
        result = await _run_cassazione_scraping(
            db=db,
            days_back=scrape_request.days_back,
            sections=scrape_request.sections,
            limit=scrape_request.limit,
        )

        if result.get("success"):
            return ScrapeResponse(
                success=True,
                message="Cassazione scraping completed successfully",
                documents_found=result.get("documents_found", 0),
                documents_processed=result.get("documents_processed", 0),
                documents_saved=result.get("documents_saved", 0),
                errors=result.get("errors", 0),
                duration_seconds=result.get("duration_seconds", 0),
            )
        else:
            raise HTTPException(status_code=500, detail=f"Scraping failed: {result.get('error')}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cassazione_scraping_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}") from e


@router.get(
    "/status",
    summary="Get scraper status",
    description="Get the current status and configuration of scrapers",
)
@limiter.limit("60 per hour")
async def get_scraper_status(
    request: Request,
    session: Session = Depends(get_current_session),
) -> dict[str, Any]:
    """Get scraper status and configuration."""
    return {
        "scrapers": {
            "gazzetta": {
                "enabled": True,
                "source": "Gazzetta Ufficiale",
                "url": "https://www.gazzettaufficiale.it",
                "default_days_back": 1,
                "filters": ["tax", "labor"],
            },
            "cassazione": {
                "enabled": True,
                "source": "Corte di Cassazione",
                "url": "https://www.cortedicassazione.it",
                "default_days_back": 7,
                "sections": ["tributaria", "lavoro", "civile", "penale"],
            },
        },
        "rate_limits": {
            "scrape_endpoints": "5 per hour",
            "status_endpoint": "60 per hour",
        },
    }
