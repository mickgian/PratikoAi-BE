"""Application configuration management.

This module handles environment-specific configuration loading, parsing, and management
for the application. It includes environment detection, .env file loading, and
configuration value parsing.
"""

import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv


# Define environment types
class Environment(str, Enum):
    """Application environment types.

    Defines the possible environments the application can run in:
    - development: Local development
    - qa: Quality assurance and testing
    - production: Live production
    """

    DEVELOPMENT = "development"
    QA = "qa"
    PRODUCTION = "production"


# Determine environment
def get_environment() -> Environment:
    """Get the current environment from APP_ENV variable.

    Returns:
        Environment: The current environment

    Supported APP_ENV values:
    - "qa" → Environment.QA
    - "production" or "prod" → Environment.PRODUCTION
    - default → Environment.DEVELOPMENT
    """
    env_str = os.getenv("APP_ENV", "development").lower()

    match env_str:
        case "qa":
            return Environment.QA
        case "production" | "prod":
            return Environment.PRODUCTION
        case _:
            return Environment.DEVELOPMENT


# Load appropriate .env file based on environment
def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    print(f"Loading environment: {env}")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Define env files in priority order
    env_files = [
        os.path.join(base_dir, f".env.{env.value}.local"),
        os.path.join(base_dir, f".env.{env.value}"),
        os.path.join(base_dir, ".env.local"),
        os.path.join(base_dir, ".env"),
    ]

    # Load the first env file that exists
    for env_file in env_files:
        if os.path.isfile(env_file):
            load_dotenv(dotenv_path=env_file)
            print(f"Loaded environment from {env_file}")
            return env_file

    # Fall back to default if no env file found
    return None


ENV_FILE = load_env_file()


# Parse list values from environment variables
def parse_list_from_env(env_key, default=None):
    """Parse a comma-separated list from an environment variable."""
    value = os.getenv(env_key)
    if not value:
        return default or []

    # Remove quotes if they exist
    value = value.strip("\"'")
    # Handle single value case
    if "," not in value:
        return [value]
    # Split comma-separated values
    return [item.strip() for item in value.split(",") if item.strip()]


# Parse dict of lists from environment variables with prefix
def parse_dict_of_lists_from_env(prefix, default_dict=None):
    """Parse dictionary of lists from environment variables with a common prefix."""
    result = default_dict or {}

    # Look for all env vars with the given prefix
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix) :].lower()  # Extract endpoint name
            # Parse the values for this endpoint
            if value:
                value = value.strip("\"'")
                if "," in value:
                    result[endpoint] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    result[endpoint] = [value]

    return result


class Settings:
    """Application settings without using pydantic."""

    def __init__(self):
        """Initialize application settings from environment variables.

        Loads and sets all configuration values from environment variables,
        with appropriate defaults for each setting. Also applies
        environment-specific overrides based on the current environment.
        """
        # Set the environment
        self.ENVIRONMENT = get_environment()

        # Application Settings
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "FastAPI LangGraph Template")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION = os.getenv(
            "DESCRIPTION", "A production-ready FastAPI template with LangGraph and Langfuse integration"
        )
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        from app.core.remote_config import get_config, get_feature_flag

        self.DEBUG = get_feature_flag("DEBUG", default=False)

        # Base URL configuration
        self.BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

        # CORS Settings
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        # OAuth Configuration
        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
        self.LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
        self.OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", f"{self.BASE_URL}/api/v1/auth/oauth/callback")

        # Langfuse Configuration
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        # Sampling rate for production (0.0-1.0). DEV/QA always sample 100%.
        # Set via env var to override the default 10% for production.
        _sampling_rate_str = os.getenv("LANGFUSE_SAMPLING_RATE")
        self.LANGFUSE_SAMPLING_RATE: float | None = float(_sampling_rate_str) if _sampling_rate_str else None

        # LLM Configuration - Multi-Provider Support
        # Legacy OpenAI config (for backward compatibility)
        self.LLM_API_KEY = os.getenv("LLM_API_KEY", "")
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

        # Multi-provider configuration
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", ""))
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "gpt-4o-mini"))

        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

        # Additional providers for model comparison (DEV-256)
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        self.MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
        self.MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

        # Production LLM model (format: provider:model, e.g., "openai:gpt-4o")
        # Used in normal chat and marked as "Modello Corrente" in comparison feature
        # Runtime-tunable via Flagsmith (ADR-031)

        self.PRODUCTION_LLM_MODEL = get_config("PRODUCTION_LLM_MODEL", "openai:gpt-4o")

        # LLM routing configuration
        self.LLM_ROUTING_STRATEGY = os.getenv(
            "LLM_ROUTING_STRATEGY", "cost_optimized"
        )  # cost_optimized, quality_first, balanced, failover
        self.LLM_MAX_COST_EUR = float(os.getenv("LLM_MAX_COST_EUR", "0.020"))  # Max €0.02 per request
        self.LLM_PREFERRED_PROVIDER = os.getenv("LLM_PREFERRED_PROVIDER", "")  # openai, anthropic

        # Query Normalization (LLM-based document reference extraction)
        self.QUERY_NORMALIZATION_ENABLED = os.getenv("QUERY_NORMALIZATION_ENABLED", "true").lower() == "true"
        self.QUERY_NORMALIZATION_MODEL = os.getenv("QUERY_NORMALIZATION_MODEL", "gpt-4o-mini")
        self.QUERY_NORMALIZATION_CACHE_TTL = int(os.getenv("QUERY_NORMALIZATION_CACHE_TTL", "3600"))  # 1 hour

        # General LLM settings
        # Runtime-tunable via Flagsmith (ADR-031)
        self.DEFAULT_LLM_TEMPERATURE = float(get_config("DEFAULT_LLM_TEMPERATURE", "0.2"))
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
        self.MAX_LLM_CALL_RETRIES = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))

        # JWT Configuration
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        # Access token expires in 30 days for faster development (TODO: reduce for production)
        self.JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", str(30 * 24))
        )  # 30 days in hours
        # Refresh token expires in 365 days for faster development (TODO: reduce for production)
        self.JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "365"))

        # Logging Configuration
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
        self.LOG_LEVEL = get_config("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" or "console"

        # Postgres Configuration
        self.POSTGRES_URL = os.getenv("POSTGRES_URL", "")
        self.POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
        self.CHECKPOINT_TABLES = ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]

        # Redis Configuration for Caching
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        self.REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        self.REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))

        # Caching Configuration
        self.CACHE_ENABLED = get_feature_flag("CACHE_ENABLED", default=True)
        self.CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))  # 1 hour
        self.CACHE_CONVERSATION_TTL = int(os.getenv("CACHE_CONVERSATION_TTL", "7200"))  # 2 hours
        self.CACHE_LLM_RESPONSE_TTL = int(os.getenv("CACHE_LLM_RESPONSE_TTL", "86400"))  # 24 hours
        self.CACHE_MAX_QUERY_SIZE = int(os.getenv("CACHE_MAX_QUERY_SIZE", "10000"))  # Max chars to cache

        # Privacy and GDPR Configuration
        self.PRIVACY_ANONYMIZE_LOGS = os.getenv("PRIVACY_ANONYMIZE_LOGS", "true").lower() in ("true", "1", "t", "yes")
        self.PRIVACY_ANONYMIZE_REQUESTS = os.getenv("PRIVACY_ANONYMIZE_REQUESTS", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.PRIVACY_DATA_RETENTION_DAYS = int(os.getenv("PRIVACY_DATA_RETENTION_DAYS", "365"))  # 1 year default
        self.PRIVACY_CONSENT_EXPIRY_DAYS = int(
            os.getenv("PRIVACY_CONSENT_EXPIRY_DAYS", "365")
        )  # 1 year consent validity
        self.PRIVACY_PII_CONFIDENCE_THRESHOLD = float(
            os.getenv("PRIVACY_PII_CONFIDENCE_THRESHOLD", "0.7")
        )  # PII detection threshold

        # Billing Configuration (DEV-257)
        self.BILLING_DEFAULT_PLAN = os.getenv("BILLING_DEFAULT_PLAN", "base")
        self.BILLING_CREDIT_RECHARGE_AMOUNTS = [5, 10, 25, 50, 100]

        # System test user ID for E2E test cost tracking (DEV-257)
        # Non-numeric user_ids (e.g., "e2e_test_abc") are mapped to this ID.
        # Must match the seeded user in migration 20260213_seed_system_test_user.
        self.SYSTEM_TEST_USER_ID: int = 50000

        # Stripe Payment Configuration
        self.STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        self.STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
        self.STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.STRIPE_MONTHLY_PRICE_ID = os.getenv("STRIPE_MONTHLY_PRICE_ID", "")  # €69/month price ID
        self.STRIPE_TRIAL_PERIOD_DAYS = int(os.getenv("STRIPE_TRIAL_PERIOD_DAYS", "7"))  # 7-day trial
        self.STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", f"{self.BASE_URL}/payment/success")
        self.STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", f"{self.BASE_URL}/payment/cancel")

        # Domain-Action Classification Configuration
        self.CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv("CLASSIFICATION_CONFIDENCE_THRESHOLD", "0.6"))

        # Vector Database Configuration (PostgreSQL + pgvector)
        self.VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))  # text-embedding-3-small dimension
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.VECTOR_SIMILARITY_THRESHOLD = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.7"))
        self.MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "10"))

        # Rate Limiting Configuration
        self.RATE_LIMIT_DEFAULT = parse_list_from_env("RATE_LIMIT_DEFAULT", ["200 per day", "50 per hour"])

        # Rate limit endpoints defaults
        default_endpoints = {
            "chat": ["30 per minute"],
            "chat_stream": ["20 per minute"],
            "messages": ["50 per minute"],
            "register": ["10 per hour"],
            "login": ["20 per minute"],
            "root": ["10 per minute"],
            "health": ["20 per minute"],
        }

        # Update rate limit endpoints from environment variables
        self.RATE_LIMIT_ENDPOINTS = default_endpoints.copy()
        for endpoint in default_endpoints:
            env_key = f"RATE_LIMIT_{endpoint.upper()}"
            value = parse_list_from_env(env_key)
            if value:
                self.RATE_LIMIT_ENDPOINTS[endpoint] = value

        # Evaluation Configuration
        self.EVALUATION_LLM = os.getenv("EVALUATION_LLM", "gpt-4o-mini")
        self.EVALUATION_BASE_URL = os.getenv("EVALUATION_BASE_URL", "https://api.openai.com/v1")
        self.EVALUATION_API_KEY = os.getenv("EVALUATION_API_KEY", self.LLM_API_KEY)
        self.EVALUATION_SLEEP_TIME = int(os.getenv("EVALUATION_SLEEP_TIME", "10"))

        # Email Settings
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@pratikoai.com")

        # Stakeholder Configuration
        self.STAKEHOLDER_EMAIL = os.getenv("STAKEHOLDER_EMAIL", "admin@pratikoai.com")

        # Metrics Report Recipients (comma-separated)
        self.METRICS_REPORT_RECIPIENTS = os.getenv("METRICS_REPORT_RECIPIENTS", "admin@pratikoai.com")
        self.METRICS_REPORT_RECIPIENTS_ADMIN = os.getenv("METRICS_REPORT_RECIPIENTS_ADMIN", "")
        self.METRICS_REPORT_RECIPIENTS_TECH = os.getenv("METRICS_REPORT_RECIPIENTS_TECH", "")
        self.METRICS_REPORT_RECIPIENTS_BUSINESS = os.getenv("METRICS_REPORT_RECIPIENTS_BUSINESS", "")

        # Daily Ingestion Report Configuration
        # Recipients (comma-separated) - same recipients receive reports from ALL environments
        self.INGESTION_REPORT_RECIPIENTS = os.getenv("INGESTION_REPORT_RECIPIENTS", "")
        # Time to send report in HH:MM format (Europe/Rome timezone)
        self.INGESTION_REPORT_TIME = os.getenv("INGESTION_REPORT_TIME", "06:00")
        # Enable/disable the daily ingestion report
        self.INGESTION_REPORT_ENABLED = get_feature_flag("INGESTION_REPORT_ENABLED", default=True)

        # Embedding Backfill Configuration
        # Automatically repairs missing embeddings from failed API calls during ingestion
        self.EMBEDDING_BACKFILL_ENABLED = os.getenv("EMBEDDING_BACKFILL_ENABLED", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        # Time to run backfill in HH:MM format (Europe/Rome timezone)
        # Default: 03:00 (after RSS ingestion at 01:00, before reports at 06:00)
        self.EMBEDDING_BACKFILL_TIME = os.getenv("EMBEDDING_BACKFILL_TIME", "03:00")

        # Daily Cost Report Configuration (DEV-246)
        # Recipients (comma-separated) for cost spending reports
        self.DAILY_COST_REPORT_RECIPIENTS = os.getenv("DAILY_COST_REPORT_RECIPIENTS", "")
        # Time to send report in HH:MM format (Europe/Rome timezone)
        self.DAILY_COST_REPORT_TIME = os.getenv("DAILY_COST_REPORT_TIME", "07:00")
        # Enable/disable the daily cost report
        self.DAILY_COST_REPORT_ENABLED = get_feature_flag("DAILY_COST_REPORT_ENABLED", default=True)

        # Evaluation Report Configuration (DEV-252)
        # Recipients (comma-separated) for nightly/weekly evaluation reports
        self.EVAL_REPORT_RECIPIENTS = os.getenv("EVAL_REPORT_RECIPIENTS", "")
        # Time to run daily evaluation report in HH:MM format (Europe/Rome timezone)
        self.EVAL_REPORT_TIME = os.getenv("EVAL_REPORT_TIME", "06:00")
        # Enable/disable evaluation report emails
        self.EVAL_REPORT_ENABLED = get_feature_flag("EVAL_REPORT_ENABLED", default=True)

        # RSS Collection Configuration
        # Time to run daily RSS collection in HH:MM format (Europe/Rome timezone)
        self.RSS_COLLECTION_TIME = os.getenv("RSS_COLLECTION_TIME", "01:00")

        # Slack Notification Settings (for Subagent System)
        # Modern Slack webhooks require separate webhooks for each channel
        self.SLACK_WEBHOOK_URL_ARCHITECT = os.getenv("SLACK_WEBHOOK_URL_ARCHITECT", "")
        self.SLACK_WEBHOOK_URL_SCRUM = os.getenv("SLACK_WEBHOOK_URL_SCRUM", "")
        self.SLACK_ENABLED = get_feature_flag("SLACK_ENABLED", default=False)

        # Security and Antivirus Settings
        self.ENABLE_EXTERNAL_AV_SCAN = os.getenv("ENABLE_EXTERNAL_AV_SCAN", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.CLAMAV_HOST = os.getenv("CLAMAV_HOST", "localhost")
        self.CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
        self.CLAMAV_TIMEOUT = int(os.getenv("CLAMAV_TIMEOUT", "30"))
        self.VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
        self.VIRUSTOTAL_TIMEOUT = int(os.getenv("VIRUSTOTAL_TIMEOUT", "60"))
        self.VIRUS_SCAN_MAX_FILE_SIZE_MB = int(os.getenv("VIRUS_SCAN_MAX_FILE_SIZE_MB", "100"))
        self.QUARANTINE_INFECTED_FILES = os.getenv("QUARANTINE_INFECTED_FILES", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.SECURITY_SCAN_TIMEOUT = int(os.getenv("SECURITY_SCAN_TIMEOUT", "30"))

        # Web Verification Settings (DEV-245)
        self.BRAVE_SEARCH_API_KEY: str | None = os.getenv("BRAVE_SEARCH_API_KEY") or None
        self.WEB_VERIFICATION_ENABLED = get_feature_flag("WEB_VERIFICATION_ENABLED", default=True)
        # DEV-245: Configurable Brave search weight for Parallel Hybrid RAG
        # Equal to BM25 (0.3) for balanced KB + web influence
        # Range: 0.0 (disabled) to 0.4 (max recommended)
        self.BRAVE_SEARCH_WEIGHT: float = float(os.getenv("BRAVE_SEARCH_WEIGHT", "0.30"))

        # Document Security Settings
        self.MAX_DOCUMENT_ENTROPY = float(os.getenv("MAX_DOCUMENT_ENTROPY", "7.5"))
        self.ALLOW_MACROS_IN_DOCUMENTS = os.getenv("ALLOW_MACROS_IN_DOCUMENTS", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.ALLOW_JAVASCRIPT_IN_PDF = os.getenv("ALLOW_JAVASCRIPT_IN_PDF", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.MAX_EXTERNAL_REFERENCES = int(os.getenv("MAX_EXTERNAL_REFERENCES", "5"))
        self.ENABLE_CONTENT_STRUCTURE_VALIDATION = os.getenv(
            "ENABLE_CONTENT_STRUCTURE_VALIDATION", "true"
        ).lower() in ("true", "1", "t", "yes")

        # Apply environment-specific settings
        self.apply_environment_settings()

    def apply_environment_settings(self):
        """Apply environment-specific settings.

        Settings are applied only if not explicitly set via environment variables.
        This allows for environment-specific defaults while preserving manual overrides.
        """
        # PRODUCTION config
        production_config = {
            "DEBUG": False,
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "json",
            "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
        }

        env_settings = {
            Environment.DEVELOPMENT: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
            },
            Environment.QA: {
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "LOG_FORMAT": "json",
                "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
            },
            Environment.PRODUCTION: production_config.copy(),
        }

        # Get settings for current environment
        current_env_settings = env_settings.get(self.ENVIRONMENT, {})

        # Apply settings if not explicitly set in environment variables or Flagsmith
        from app.core.remote_config import _flagsmith_has_key

        for key, value in current_env_settings.items():
            env_var_name = key.upper()
            # Only override if neither environment variable nor Flagsmith provides this value
            if env_var_name not in os.environ and not _flagsmith_has_key(env_var_name):
                setattr(self, key, value)


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


# ==============================================================================
# Hybrid RAG Configuration
# Runtime-tunable values use Flagsmith fallback chain (ADR-031)
# ==============================================================================
from app.core.remote_config import get_config as _rc_get_config

# Embedding Model Configuration
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")  # 1536-d
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))

# Chunking Configuration
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "900"))
CHUNK_OVERLAP = float(os.getenv("CHUNK_OVERLAP", "0.12"))  # 12% overlap

# PDF Extraction Configuration
EXTRACTOR_PRIMARY = os.getenv("EXTRACTOR_PRIMARY", "pdfplumber")  # "pdfplumber" (MIT)
PDF_EXTRACTOR = os.getenv("PDF_EXTRACTOR", "pdfplumber")  # Feature flag for extraction method
OCR_ENABLED = _rc_get_config("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "ita")  # Tesseract language codes
OCR_PAGE_SAMPLE = int(os.getenv("OCR_PAGE_SAMPLE", "3"))  # Pages to sample for quality check
OCR_MAX_PAGES = int(os.getenv("OCR_MAX_PAGES", "12"))  # Max pages to OCR per document
OCR_MIN_PAGE_WIDTH = int(os.getenv("OCR_MIN_PAGE_WIDTH", "1500"))  # Min raster width for OCR

# Text Quality Thresholds
CLEAN_MIN_LEN = int(os.getenv("CLEAN_MIN_LEN", "20"))  # Minimum chunk length
CLEAN_PRINTABLE_RATIO = float(os.getenv("CLEAN_PRINTABLE_RATIO", "0.60"))  # Min printable chars ratio
CLEAN_ALPHA_RATIO = float(os.getenv("CLEAN_ALPHA_RATIO", "0.25"))  # Min alphabetic chars ratio
CLEAN_MIN_WORDS = int(os.getenv("CLEAN_MIN_WORDS", "5"))  # Minimum word count
JUNK_DROP_CHUNK = os.getenv("JUNK_DROP_CHUNK", "true").lower() in ("true", "1", "yes")  # Drop junk chunks on ingestion

# Repair/Re-extraction Configuration
REPAIR_BATCH_SIZE = int(os.getenv("REPAIR_BATCH_SIZE", "5"))  # Embeddings batch size for repair
REPAIR_LIMIT_DEFAULT = int(os.getenv("REPAIR_LIMIT_DEFAULT", "20"))  # Default repair limit
QUALITY_MIN_DOC = float(os.getenv("QUALITY_MIN_DOC", "0.60"))  # Min quality threshold for repair

# Hybrid Retrieval Weights (must sum to ~1.0)
# DEV-BE-78: Rebalanced weights to include quality and source authority
# Original: FTS=0.50, Vec=0.35, Recency=0.15
# New: FTS=0.45, Vec=0.30, Recency=0.10, Quality=0.10, Source=0.05
# Runtime-tunable via Flagsmith (ADR-031)
HYBRID_WEIGHT_FTS = float(_rc_get_config("HYBRID_WEIGHT_FTS", "0.45"))
HYBRID_WEIGHT_VEC = float(_rc_get_config("HYBRID_WEIGHT_VEC", "0.30"))
HYBRID_WEIGHT_RECENCY = float(_rc_get_config("HYBRID_WEIGHT_RECENCY", "0.10"))
HYBRID_WEIGHT_QUALITY = float(_rc_get_config("HYBRID_WEIGHT_QUALITY", "0.10"))
HYBRID_WEIGHT_SOURCE = float(_rc_get_config("HYBRID_WEIGHT_SOURCE", "0.05"))

# Source Authority Weights for official Italian sources
# Used by ranking_utils.get_source_authority_boost()
SOURCE_AUTHORITY_WEIGHTS = {
    # Official government sources: +0.15 boost
    "agenzia_entrate": 0.15,
    "agenzia_entrate_riscossione": 0.15,  # DEV-242 Phase 35A: AdER official rules
    "inps": 0.15,
    "mef": 0.15,
    "gazzetta_ufficiale": 0.15,
    "ministero_lavoro": 0.15,
    "inail": 0.15,
    "corte_cassazione": 0.15,
    # Semi-official professional associations: +0.10 boost
    "confindustria": 0.10,
    "ordine_commercialisti": 0.10,
    "consiglio_nazionale_forense": 0.10,
    "cndcec": 0.10,
}

# HuggingFace Intent Classifier Configuration (DEV-251, DEV-253)
# Model for intent classification to replace GPT router calls.
# Zero-shot: "mdeberta" (default), "bart"
# Fine-tuned: any HuggingFace Hub path, e.g. "pratikoai/intent-classifier-v1"
# The classifier auto-detects pipeline type from the model config.
HF_INTENT_MODEL = _rc_get_config("HF_INTENT_MODEL", "mdeberta")

# HyDE-specific Model Configuration (DEV-251 Phase 5b)
# Uses provider:model format via resolve_model_from_env().
# Separate from BASIC tier to allow HyDE to use faster Haiku while other
# BASIC operations remain on GPT-4o-mini. This reduces HyDE latency from ~20s to ~3-5s.
HYDE_MODEL = _rc_get_config("HYDE_MODEL", "anthropic:claude-3-haiku-20240307")

# Map short names to full HuggingFace model names
HF_MODEL_MAP = {
    "mdeberta": "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",  # 280MB, native Italian support
    "bart": "facebook/bart-large-mnli",  # 400MB, multilingual (fair Italian)
}

# Retrieval Parameters
# DEV-242 Phase 21: Increased limits for more comprehensive context

# CONTEXT_TOP_K: Number of chunks to include in LLM context
# DEV-242 Phase 36: Was 22 to capture AdER chunks (5-day grace period info)
# DEV-244: Reduced to 18 - hard char limit in context_builder_merge.py now prevents overflow
# DEV-245: Increased from 18 to 25 for more complete responses
CONTEXT_TOP_K = int(_rc_get_config("CONTEXT_TOP_K", "25"))

# USE_GENERIC_EXTRACTION: Use generic extraction principles instead of topic-specific rules
# DEV-XXX: When True, replaces ~17KB of rottamazione-specific rules with ~4KB of generic patterns
# This enables scalability to hundreds of topics without per-topic configuration
USE_GENERIC_EXTRACTION = os.getenv("USE_GENERIC_EXTRACTION", "true").lower() == "true"

# USE_DYNAMIC_TOPIC_DETECTION: Use LLM-based semantic expansions instead of hardcoded TOPIC_KEYWORDS
# DEV-245: When True, relies on MultiQueryGeneratorService's semantic_expansions for topic detection
# This enables scalability to unlimited topics without manual keyword maintenance
USE_DYNAMIC_TOPIC_DETECTION = os.getenv("USE_DYNAMIC_TOPIC_DETECTION", "true").lower() == "true"

# HYBRID_K_FTS: Number of candidates from BM25/FTS search
HYBRID_K_FTS = int(os.getenv("HYBRID_K_FTS", "30"))

# HYBRID_K_VEC: Number of candidates from vector search (not yet implemented)
HYBRID_K_VEC = int(os.getenv("HYBRID_K_VEC", "30"))
