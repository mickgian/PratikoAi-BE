import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import (
    engine_from_config,
    pool,
    text,
)
from sqlmodel import SQLModel

from alembic import context  # type: ignore[attr-defined]
from alembic.script import ScriptDirectory

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.development"))
from app.models.cassazione import CassazioneDecision

# Phase 2: CCNL Database Models
from app.models.ccnl_database import (
    CCNLAgreementDB,
    CCNLSectorDB,
    JobLevelDB,
    LeaveEntitlementDB,
    NoticePeriodsDB,
    OvertimeRulesDB,
    SalaryTableDB,
    SpecialAllowanceDB,
    WorkingHoursDB,
)
from app.models.ccnl_update_models import (
    CCNLChangeLog,
    CCNLDatabase,
    CCNLMonitoringMetric,
    CCNLUpdateEvent,
    CCNLVersion,
)

# DEV-256: Multi-Model LLM Comparison Feature
from app.models.comparison import (
    ModelComparisonResponse,
    ModelComparisonSession,
    ModelEloRating,
    UserModelPreference,
)

# Phase 3: GDPR Data Export Models
from app.models.data_export import (
    DataExportRequest,
    ElectronicInvoice,
    ExportAuditLog,
    ExportDocumentAnalysis,
    FAQInteraction,
    KnowledgeBaseSearch,
    QueryHistory,
)
from app.models.data_export import (
    TaxCalculation as ExportTaxCalculation,
)
from app.models.document import (
    Document,
    DocumentAnalysis,
    DocumentProcessingJob,
)

# Temporarily exclude encrypted models due to CI dependency issues
# from app.models.encrypted_user import EncryptedUser, EncryptedQueryLog, EncryptedSubscriptionData
from app.models.faq import (
    FAQAnalyticsSummary,
    FAQCategory,
    FAQEntry,
    FAQObsolescenceCheck,
    FAQUsageLog,
    FAQVariationCache,
    FAQVersionHistory,
)

# Phase 3: FAQ Automation Models
from app.models.faq_automation import (
    FAQCandidate,
    FAQGenerationJob,
    GeneratedFAQ,
    QueryCluster,
    RSSFAQImpact,
)
from app.models.italian_data import (
    ComplianceCheck,
    ItalianKnowledgeSource,
    ItalianLegalTemplate,
    ItalianOfficialDocument,
    ItalianRegulation,
    ItalianTaxRate,
    TaxCalculation,
)
from app.models.knowledge import (
    KnowledgeFeedback,
    KnowledgeItem,
)
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.payment import (
    Customer,
    Invoice,
    Payment,
    Subscription,
    WebhookEvent,
)

# Proactivity Analytics Models - DEV-156
from app.models.proactivity_analytics import (
    InteractiveQuestionAnswer,
    SuggestedActionClick,
)

# Phase 3: Expert Feedback & Quality Analysis Models
from app.models.quality_analysis import (
    ExpertFeedback,
    ExpertGeneratedTask,
    ExpertProfile,
    ExpertValidation,
    FailurePattern,
    PromptTemplate,
    QualityMetric,
    SystemImprovement,
)
from app.models.query_normalization import (
    QueryNormalizationLog,
    QueryNormalizationPattern,
    QueryNormalizationStats,
)

# Phase 4: Regional Tax Models
from app.models.regional_taxes import (
    ComunalTaxRate,
    Comune,
    RegionalTaxRate,
    Regione,
)

# Phase 3: Italian Subscription Models
# TEMPORARILY COMMENTED OUT: Conflicts with payment.py models (duplicate table names)
# TODO: Create separate migration to evolve payment.py schema -> subscription.py schema
# from app.models.subscription import (
#     Invoice as SubscriptionInvoice,
#     Subscription as UserSubscription,
#     SubscriptionPlan,
#     SubscriptionPlanChange,
# )
from app.models.regulatory_documents import (
    DocumentCollection,
    DocumentProcessingLog,
    FeedStatus,
    RegulatoryDocument,
)
from app.models.session import Session
from app.models.thread import Thread
from app.models.usage import (
    CostAlert,
    CostOptimizationSuggestion,
    UsageEvent,
    UsageQuota,
    UserUsageSummary,
)

# Import all models to ensure they are registered with SQLModel.metadata
from app.models.user import User

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with DATABASE_URL (or POSTGRES_URL fallback)
_db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if _db_url:
    # Alembic requires a sync driver — replace asyncpg if present
    config.set_main_option("sqlalchemy.url", _db_url.replace("+asyncpg", ""))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Create alembic_version table with VARCHAR(64) if it doesn't exist
        # This accommodates long revision IDs (some are 33 characters)
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(64) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
                """
            )
        )
        connection.commit()

        # Check if this is a fresh database (no migrations have ever run).
        result = connection.execute(text("SELECT COUNT(*) FROM alembic_version"))
        is_fresh_db = result.scalar() == 0

        if is_fresh_db:
            # Fresh database: create all tables from current SQLModel models
            # and stamp to head (skip migrations — schema is already current).
            # Install extensions that migrations would normally create.
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            connection.commit()
            target_metadata.create_all(connection)
            script = ScriptDirectory.from_config(config)
            head_rev = script.get_current_head()
            if head_rev:
                connection.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
                    {"rev": head_rev},
                )
            connection.commit()
        else:
            # Existing database: run migrations normally.
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
