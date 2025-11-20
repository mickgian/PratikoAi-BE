#!/usr/bin/env python3
"""Initialize database tables from SQLModel metadata.

This script creates all tables defined in SQLModel models before running Alembic migrations.
This is necessary because the first Alembic migration assumes base tables already exist.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlmodel import SQLModel

# Import all models to ensure they're registered with SQLModel.metadata
from app.models.cassazione import CassazioneDecision
from app.models.document import (
    Document,
    DocumentAnalysis,
    DocumentProcessingJob,
)
from app.models.faq import (
    FAQAnalyticsSummary,
    FAQCategory,
    FAQEntry,
    FAQObsolescenceCheck,
    FAQUsageLog,
    FAQVariationCache,
    FAQVersionHistory,
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
from app.models.query_normalization import (
    QueryNormalizationLog,
    QueryNormalizationPattern,
    QueryNormalizationStats,
)
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
from app.models.user import User


def main():
    """Create all database tables from SQLModel metadata."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not database_url:
        print("ERROR: DATABASE_URL or POSTGRES_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Convert postgres:// to postgresql:// if needed (for SQLAlchemy compatibility)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print("Creating tables in database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")

    # Create engine
    engine = create_engine(database_url, echo=True)

    # Create all tables
    print("\nCreating all tables from SQLModel metadata...")
    SQLModel.metadata.create_all(engine)

    print("\n✅ Database tables created successfully!")
    print(f"Total tables created: {len(SQLModel.metadata.tables)}")
    print(f"Tables: {', '.join(sorted(SQLModel.metadata.tables.keys()))}")


if __name__ == "__main__":
    main()
