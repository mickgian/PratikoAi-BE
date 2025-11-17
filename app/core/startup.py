"""Application startup handlers for NormoAI system initialization."""

import asyncio
import logging

from fastapi import FastAPI

from app.services.scheduler_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


async def startup_handler():
    """Handle application startup tasks."""
    try:
        logger.info("Starting NormoAI application...")

        # Start scheduler service for automated tasks
        logger.info("Starting scheduler service...")
        await start_scheduler()

        logger.info("NormoAI application startup completed successfully")

    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise


async def shutdown_handler():
    """Handle application shutdown tasks."""
    try:
        logger.info("Shutting down NormoAI application...")

        # Stop scheduler service
        logger.info("Stopping scheduler service...")
        await stop_scheduler()

        logger.info("NormoAI application shutdown completed successfully")

    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


def setup_startup_handlers(app: FastAPI):
    """Setup startup and shutdown handlers for the FastAPI application."""

    @app.on_event("startup")
    async def startup_event():
        await startup_handler()

    @app.on_event("shutdown")
    async def shutdown_event():
        await shutdown_handler()
