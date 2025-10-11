"""Logging configuration and setup for the application.

This module provides structured logging configuration using structlog,
with environment-specific formatters and handlers. It supports both
console-friendly development logging and JSON-formatted production logging.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import structlog

from app.core.config import (
    Environment,
    settings,
)

# Lazy import to avoid circular dependencies
_anonymizer = None


def _get_anonymizer():
    """Get anonymizer instance with lazy loading."""
    global _anonymizer
    if _anonymizer is None:
        try:
            from app.core.privacy.anonymizer import anonymizer
            _anonymizer = anonymizer
        except ImportError:
            # If privacy module is not available, create a no-op anonymizer
            class NoOpAnonymizer:
                def anonymize_text(self, text, **kwargs):
                    from app.core.privacy.anonymizer import AnonymizationResult
                    return AnonymizationResult(anonymized_text=text)
            _anonymizer = NoOpAnonymizer()
    return _anonymizer


def _anonymize_pii_processor(logger, method_name, event_dict):
    """Structlog processor to anonymize PII in log messages."""
    # Only anonymize if privacy features are enabled
    privacy_enabled = getattr(settings, 'PRIVACY_ANONYMIZE_LOGS', True)
    if not privacy_enabled:
        return event_dict
    
    anonymizer = _get_anonymizer()
    
    # Fields that should be anonymized
    sensitive_fields = [
        'message', 'error', 'user_input', 'query', 'response', 
        'email', 'phone', 'address', 'content', 'text'
    ]
    
    for field in sensitive_fields:
        if field in event_dict and isinstance(event_dict[field], str):
            try:
                result = anonymizer.anonymize_text(event_dict[field])
                if result.pii_matches:  # Only replace if PII was found
                    event_dict[field] = result.anonymized_text
                    # Add anonymization metadata (but not in production to avoid noise)
                    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
                        event_dict[f'{field}_pii_anonymized'] = len(result.pii_matches)
            except Exception:
                # If anonymization fails, continue without anonymizing
                # We don't want logging failures to break the application
                pass
    
    return event_dict

# Ensure log directory exists
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_log_file_path() -> Path:
    """Get the current log file path based on date and environment.

    Returns:
        Path: The path to the log file
    """
    env_prefix = settings.ENVIRONMENT.value
    return settings.LOG_DIR / f"{env_prefix}-{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def cleanup_old_logs(retention_days: int = 30) -> None:
    """Delete log files older than retention_days.

    Args:
        retention_days: Number of days to keep logs (default 30)
    """
    import time
    cutoff_time = time.time() - (retention_days * 86400)
    deleted_count = 0

    for log_file in settings.LOG_DIR.glob("*.jsonl"):
        try:
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
        except Exception:
            # Silently continue if we can't delete a file
            pass

    if deleted_count > 0:
        # Note: Can't use logger here as it may not be initialized yet
        print(f"Cleaned up {deleted_count} old log file(s) older than {retention_days} days")


def cleanup_old_rag_traces(retention_days: int = 7) -> None:
    """Delete RAG trace files older than retention_days.

    RAG trace files are per-request log files containing only RAG step logs,
    used for debugging in development and staging environments.

    Args:
        retention_days: Number of days to keep RAG traces (default 7)
    """
    import time
    trace_dir = settings.LOG_DIR / "rag_traces"

    # Skip if trace directory doesn't exist
    if not trace_dir.exists():
        return

    cutoff_time = time.time() - (retention_days * 86400)
    deleted_count = 0

    for trace_file in trace_dir.glob("trace_*.jsonl"):
        try:
            if trace_file.stat().st_mtime < cutoff_time:
                trace_file.unlink()
                deleted_count += 1
        except Exception:
            # Silently continue if we can't delete a file
            pass

    if deleted_count > 0:
        # Note: Can't use logger here as it may not be initialized yet
        print(f"Cleaned up {deleted_count} old RAG trace file(s) older than {retention_days} days")


class JsonlFileHandler(logging.Handler):
    """Custom handler for writing JSONL logs to daily files."""

    def __init__(self, file_path: Path):
        """Initialize the JSONL file handler.

        Args:
            file_path: Path to the log file where entries will be written.
        """
        super().__init__()
        self.file_path = file_path

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record to the JSONL file."""
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "filename": record.pathname,
                "line": record.lineno,
                "environment": settings.ENVIRONMENT.value,
            }
            if hasattr(record, "extra"):
                log_entry.update(record.extra)

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Close the handler."""
        super().close()


def get_structlog_processors(include_file_info: bool = True) -> List[Any]:
    """Get the structlog processors based on configuration.

    Args:
        include_file_info: Whether to include file information in the logs

    Returns:
        List[Any]: List of structlog processors
    """
    # Set up processors that are common to both outputs
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add callsite parameters if file info is requested
    if include_file_info:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.PATHNAME,
                }
            )
        )

    # Add environment info
    processors.append(lambda _, __, event_dict: {**event_dict, "environment": settings.ENVIRONMENT.value})
    
    # Add PII anonymization processor
    processors.append(_anonymize_pii_processor)

    return processors


def setup_logging() -> None:
    """Configure structlog with different formatters based on environment.

    In development: pretty console output
    In staging/production: structured JSON logs
    """
    # Clean up old log files based on environment
    if settings.ENVIRONMENT == Environment.DEVELOPMENT:
        cleanup_old_logs(retention_days=30)  # Keep 30 days in development
        cleanup_old_rag_traces(retention_days=7)  # Keep 7 days of RAG traces in development
    elif settings.ENVIRONMENT == Environment.QA:
        cleanup_old_logs(retention_days=60)  # Keep 60 days in QA
        cleanup_old_rag_traces(retention_days=14)  # Keep 14 days of RAG traces in QA
    elif settings.ENVIRONMENT == Environment.PREPROD:
        cleanup_old_logs(retention_days=90)  # Keep 90 days in PREPROD (mirrors production)
        # No RAG traces in PREPROD (mirrors production - feature disabled)
    else:  # PRODUCTION
        cleanup_old_logs(retention_days=90)  # Keep 90 days in production
        # No RAG traces in production (feature disabled)

    # Create file handler for JSON logs
    file_handler = JsonlFileHandler(get_log_file_path())
    file_handler.setLevel(settings.LOG_LEVEL)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)

    # Get shared processors
    shared_processors = get_structlog_processors(
        # Include detailed file info only in development (not QA/PREPROD/PROD)
        include_file_info=settings.ENVIRONMENT == Environment.DEVELOPMENT
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=settings.LOG_LEVEL,
        handlers=[file_handler, console_handler],
    )

    # Configure structlog based on environment
    if settings.LOG_FORMAT == "console":
        # Development-friendly console logging
        structlog.configure(
            processors=[
                *shared_processors,
                # Use ConsoleRenderer for pretty output to the console
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Production JSON logging
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


# Initialize logging
setup_logging()

# Create logger instance
logger = structlog.get_logger()
logger.info(
    "logging_initialized",
    environment=settings.ENVIRONMENT.value,
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
)
