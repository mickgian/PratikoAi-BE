"""add_expert_generated_task_table

Revision ID: c1e8314d9b6d
Revises: 9c4322e06e4d
Create Date: 2025-11-28 16:21:48.910226

"""

from typing import Sequence, Union

import pgvector.sqlalchemy.vector
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "c1e8314d9b6d"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "9c4322e06e4d"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _safe_create_enum(enum_name: str, values: list[str]) -> None:
    """Create ENUM type only if it doesn't exist."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"),
        {"name": enum_name},
    )
    if not result.scalar():
        values_str = ", ".join(f"'{v}'" for v in values)
        op.execute(sa.text(f"CREATE TYPE {enum_name} AS ENUM ({values_str})"))


def _table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
        {"name": table_name},
    )
    return bool(result.scalar())


def _index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"),
        {"name": index_name},
    )
    return bool(result.scalar())


def safe_create_index(index_name, table_name, columns, **kwargs) -> None:
    """Create index only if table exists and index doesn't exist."""
    # Handle op.f() wrapper
    actual_name = index_name.name if hasattr(index_name, "name") else index_name
    if _table_exists(table_name) and not _index_exists(actual_name):
        op.create_index(index_name, table_name, columns, **kwargs)


def safe_create_table(table_name: str, *args, **kwargs) -> None:
    """Create table only if it doesn't exist."""
    if not _table_exists(table_name):
        op.create_table(table_name, *args, **kwargs)


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.table_constraints WHERE table_name = :table AND constraint_name = :constraint)"
        ),
        {"table": table_name, "constraint": constraint_name},
    )
    return bool(result.scalar())


def _fk_exists_between(source_table: str, local_col: str, referent_table: str) -> bool:
    """Check if a FK already exists from source_table.local_col to referent_table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = :source_table
                AND kcu.column_name = :local_col
                AND ccu.table_name = :referent_table
            )
        """
        ),
        {"source_table": source_table, "local_col": local_col, "referent_table": referent_table},
    )
    return bool(result.scalar())


def safe_create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs) -> None:
    """Create foreign key only if tables exist and constraint doesn't exist."""
    # Check if tables exist
    if not _table_exists(source_table) or not _table_exists(referent_table):
        return
    # Handle op.f() wrapper
    actual_name = constraint_name.name if hasattr(constraint_name, "name") else constraint_name
    # Check by constraint name
    if actual_name and _constraint_exists(source_table, actual_name):
        return
    # Check by FK columns
    if local_cols and _fk_exists_between(source_table, local_cols[0], referent_table):
        return
    op.create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs)


def safe_drop_table(table_name: str) -> None:
    """Drop table only if it exists."""
    if _table_exists(table_name):
        op.drop_table(table_name)


def safe_drop_index(index_name, table_name: str, **kwargs) -> None:
    """Drop index only if it exists. Extra kwargs are ignored (for compatibility with create_index args)."""
    # Handle op.f() wrapper
    actual_name = index_name.name if hasattr(index_name, "name") else index_name
    if _index_exists(actual_name):
        op.drop_index(index_name, table_name)


def safe_drop_constraint(constraint_name, table_name: str, **kwargs) -> None:
    """Drop constraint only if it exists."""
    # Handle op.f() wrapper
    actual_name = constraint_name.name if hasattr(constraint_name, "name") else constraint_name
    if _constraint_exists(table_name, actual_name):
        op.drop_constraint(constraint_name, table_name, **kwargs)


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :table AND column_name = :column)"
        ),
        {"table": table_name, "column": column_name},
    )
    return bool(result.scalar())


def safe_drop_column(table_name: str, column_name: str) -> None:
    """Drop column only if table and column exist."""
    if _table_exists(table_name) and _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def safe_add_column(table_name: str, column, **kwargs) -> None:
    """Add column only if table exists and column doesn't exist."""
    if _table_exists(table_name) and not _column_exists(table_name, column.name):
        op.add_column(table_name, column, **kwargs)


def safe_alter_column(table_name: str, column_name: str, **kwargs) -> None:
    """Alter column only if table and column exist."""
    if _table_exists(table_name) and _column_exists(table_name, column_name):
        op.alter_column(table_name, column_name, **kwargs)


def safe_create_unique_constraint(constraint_name, table_name: str, columns, **kwargs) -> None:
    """Create unique constraint only if table exists and constraint doesn't exist."""
    if not _table_exists(table_name):
        return
    # Handle op.f() wrapper
    actual_name = constraint_name.name if hasattr(constraint_name, "name") else constraint_name
    if actual_name and not _constraint_exists(table_name, actual_name):
        op.create_unique_constraint(constraint_name, table_name, columns, **kwargs)


def upgrade() -> None:
    """Upgrade schema."""
    # Pre-create ENUM types to avoid errors if they already exist (CI runs SQLModel.metadata.create_all)
    _safe_create_enum(
        "cassazionesection",
        [
            "CIVILE_LAVORO",
            "CIVILE_PRIMA",
            "CIVILE_SECONDA",
            "CIVILE_TERZA",
            "PENALE_PRIMA",
            "PENALE_SECONDA",
            "SEZIONI_UNITE_CIVILI",
            "SEZIONI_UNITE_PENALI",
        ],
    )
    _safe_create_enum("decisiontype", ["SENTENZA", "ORDINANZA", "DECRETO", "MASSIMA", "ORIENTAMENTO"])
    _safe_create_enum(
        "documenttype",
        [
            "CONTRACT",
            "INVOICE",
            "RECEIPT",
            "DECLARATION",
            "FORM",
            "POWER_OF_ATTORNEY",
            "ARTICLES_OF_ASSOCIATION",
            "PRIVACY_POLICY",
            "TERMS_CONDITIONS",
        ],
    )
    _safe_create_enum("compliancestatus", ["COMPLIANT", "NON_COMPLIANT", "WARNING", "NEEDS_REVIEW", "UNKNOWN"])
    _safe_create_enum("plantype", ["TRIAL", "MONTHLY", "YEARLY", "ENTERPRISE"])
    _safe_create_enum("usagetype", ["LLM_QUERY", "LLM_STREAM", "CACHE_HIT", "CACHE_MISS", "API_REQUEST"])
    _safe_create_enum("costcategory", ["LLM_INFERENCE", "STORAGE", "COMPUTE", "BANDWIDTH", "THIRD_PARTY"])
    _safe_create_enum("paymentstatus", ["PENDING", "SUCCEEDED", "FAILED", "CANCELED", "REFUNDED"])
    _safe_create_enum(
        "documentcategory",
        ["CIRCOLARE", "RISOLUZIONE", "PROVVEDIMENTO", "DECRETO", "LEGGE", "MESSAGGIO", "COMUNICATO", "ALTRO"],
    )
    _safe_create_enum(
        "subscriptionstatus",
        ["ACTIVE", "INACTIVE", "PAST_DUE", "CANCELED", "UNPAID", "INCOMPLETE", "INCOMPLETE_EXPIRED", "TRIALING"],
    )
    _safe_create_enum(
        "taxtype",
        ["VAT", "INCOME_TAX", "CORPORATE_TAX", "WITHHOLDING_TAX", "REGIONAL_TAX", "PROPERTY_TAX", "STAMP_DUTY"],
    )
    _safe_create_enum(
        "processingstatus", ["PENDING", "PROCESSING", "PROCESSED", "FAILED", "ACTIVE", "SUPERSEDED", "ARCHIVED"]
    )

    # ### commands auto generated by Alembic - please adjust! ###
    if not _table_exists("cassazione_decisions"):
        safe_create_table(
            "cassazione_decisions",
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("decision_id", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column("decision_number", sa.Integer(), nullable=False),
            sa.Column("decision_year", sa.Integer(), nullable=False),
            sa.Column(
                "section",
                sa.Enum(
                    "CIVILE_LAVORO",
                    "CIVILE_PRIMA",
                    "CIVILE_SECONDA",
                    "CIVILE_TERZA",
                    "PENALE_PRIMA",
                    "PENALE_SECONDA",
                    "SEZIONI_UNITE_CIVILI",
                    "SEZIONI_UNITE_PENALI",
                    name="cassazionesection",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "decision_type",
                sa.Enum(
                    "SENTENZA",
                    "ORDINANZA",
                    "DECRETO",
                    "MASSIMA",
                    "ORIENTAMENTO",
                    name="decisiontype",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("decision_date", sa.Date(), nullable=False),
            sa.Column("publication_date", sa.Date(), nullable=True),
            sa.Column("filing_date", sa.Date(), nullable=True),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("full_text", sa.Text(), nullable=True),
            sa.Column("legal_principle", sa.Text(), nullable=True),
            sa.Column("keywords", sa.JSON(), nullable=True),
            sa.Column("legal_areas", sa.JSON(), nullable=True),
            sa.Column("related_sectors", sa.JSON(), nullable=True),
            sa.Column("precedent_value", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
            sa.Column("cited_decisions", sa.JSON(), nullable=True),
            sa.Column("citing_decisions", sa.JSON(), nullable=True),
            sa.Column("related_laws", sa.JSON(), nullable=True),
            sa.Column("related_ccnl", sa.JSON(), nullable=True),
            sa.Column("appellant", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
            sa.Column("respondent", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
            sa.Column("case_subject", sa.Text(), nullable=True),
            sa.Column("court_of_origin", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
            sa.Column("outcome", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
            sa.Column("damages_awarded", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
            sa.Column("source_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
            sa.Column("confidence_score", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    safe_create_index(
        op.f("ix_cassazione_decisions_decision_id"), "cassazione_decisions", ["decision_id"], unique=True
    )
    safe_create_table(
        "compliance_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("check_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "CONTRACT",
                "INVOICE",
                "RECEIPT",
                "DECLARATION",
                "FORM",
                "POWER_OF_ATTORNEY",
                "ARTICLES_OF_ASSOCIATION",
                "PRIVACY_POLICY",
                "TERMS_CONDITIONS",
                name="documenttype",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("document_content", sa.Text(), nullable=True),
        sa.Column("check_parameters", sa.JSON(), nullable=True),
        sa.Column(
            "overall_status",
            sa.Enum(
                "COMPLIANT",
                "NON_COMPLIANT",
                "WARNING",
                "NEEDS_REVIEW",
                "UNKNOWN",
                name="compliancestatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("compliance_score", sa.Float(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("regulations_checked", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("check_date", sa.DateTime(), nullable=False),
        sa.Column("check_method", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False),
        sa.Column("follow_up_date", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_compliance_date", "compliance_checks", ["check_date"], unique=False)
    safe_create_index(
        "idx_compliance_followup", "compliance_checks", ["follow_up_required", "follow_up_date"], unique=False
    )
    safe_create_index("idx_compliance_session", "compliance_checks", ["session_id"], unique=False)
    safe_create_index("idx_compliance_status", "compliance_checks", ["overall_status"], unique=False)
    safe_create_index("idx_compliance_type", "compliance_checks", ["check_type"], unique=False)
    safe_create_index("idx_compliance_user", "compliance_checks", ["user_id"], unique=False)
    safe_create_table(
        "document_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("document_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("total_content_length", sa.Integer(), nullable=False),
        sa.Column("earliest_document", sa.DateTime(), nullable=True),
        sa.Column("latest_document", sa.DateTime(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "expert_validations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_id", sa.Uuid(), nullable=False),
        sa.Column("validation_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("complexity_level", sa.Integer(), nullable=False),
        sa.Column("specialization_required", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("assigned_experts", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("completed_validations", sa.Integer(), nullable=False),
        sa.Column("required_validations", sa.Integer(), nullable=False),
        sa.Column("consensus_reached", sa.Boolean(), nullable=False),
        sa.Column("consensus_confidence", sa.Float(), nullable=False),
        sa.Column("disagreement_areas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("validated_answer", sa.Text(), nullable=True),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("regulatory_confirmations", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("final_confidence_score", sa.Float(), nullable=False),
        sa.Column("expert_agreement_score", sa.Float(), nullable=False),
        sa.Column("requested_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("target_completion", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("completed_validations <= required_validations", name="logical_validation_counts"),
        sa.CheckConstraint("complexity_level >= 1 AND complexity_level <= 5", name="complexity_level_range"),
        sa.CheckConstraint(
            "consensus_confidence >= 0.0 AND consensus_confidence <= 1.0", name="consensus_confidence_range"
        ),
        sa.CheckConstraint(
            "expert_agreement_score >= 0.0 AND expert_agreement_score <= 1.0", name="agreement_score_range"
        ),
        sa.CheckConstraint(
            "final_confidence_score >= 0.0 AND final_confidence_score <= 1.0", name="final_confidence_range"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_expert_validations_complexity", "expert_validations", ["complexity_level"], unique=False)
    safe_create_index("idx_expert_validations_query", "expert_validations", ["query_id"], unique=False)
    safe_create_index("idx_expert_validations_status", "expert_validations", ["status"], unique=False)
    safe_create_index("idx_expert_validations_target", "expert_validations", ["target_completion"], unique=False)
    safe_create_table(
        "failure_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pattern_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("pattern_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("categories", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("example_queries", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("frequency_count", sa.Integer(), nullable=False),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("detection_algorithm", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("cluster_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("first_detected", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_occurrence", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("resolution_date", sa.DateTime(), nullable=True),
        sa.Column("resolution_method", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="confidence_score_range"),
        sa.CheckConstraint("frequency_count >= 0", name="non_negative_frequency"),
        sa.CheckConstraint("impact_score >= 0.0 AND impact_score <= 1.0", name="impact_score_range"),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_failure_patterns_frequency", "failure_patterns", ["frequency_count"], unique=False)
    safe_create_index("idx_failure_patterns_impact", "failure_patterns", ["impact_score"], unique=False)
    safe_create_index("idx_failure_patterns_resolved", "failure_patterns", ["is_resolved"], unique=False)
    safe_create_index("idx_failure_patterns_type", "failure_patterns", ["pattern_type"], unique=False)
    safe_create_table(
        "faq_analytics_summary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False),
        sa.Column("faq_responses", sa.Integer(), nullable=False),
        sa.Column("full_llm_responses", sa.Integer(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.Column("cache_misses", sa.Integer(), nullable=False),
        sa.Column("avg_response_time_ms", sa.Float(), nullable=False),
        sa.Column("avg_search_time_ms", sa.Float(), nullable=False),
        sa.Column("cache_hit_rate", sa.Float(), nullable=False),
        sa.Column("total_variation_costs_euros", sa.Float(), nullable=False),
        sa.Column("total_full_llm_costs_euros", sa.Float(), nullable=False),
        sa.Column("cost_savings_euros", sa.Float(), nullable=False),
        sa.Column("cost_savings_percent", sa.Float(), nullable=False),
        sa.Column("avg_helpfulness_score", sa.Float(), nullable=False),
        sa.Column("followup_rate", sa.Float(), nullable=False),
        sa.Column("obsolescence_flags", sa.Integer(), nullable=False),
        sa.Column("top_categories", sa.JSON(), nullable=True),
        sa.Column("top_faqs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "faq_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_category", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("faq_count", sa.Integer(), nullable=False),
        sa.Column("total_hits", sa.Integer(), nullable=False),
        sa.Column("avg_helpfulness", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    safe_create_table(
        "italian_knowledge_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("authority", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("base_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rss_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("api_endpoint", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("api_key_required", sa.Boolean(), nullable=False),
        sa.Column("content_types", sa.JSON(), nullable=True),
        sa.Column("update_frequency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("data_format", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rate_limit", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=False),
        sa.Column("last_accessed", sa.DateTime(), nullable=False),
        sa.Column("last_document_date", sa.DateTime(), nullable=True),
        sa.Column("access_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("documents_collected", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact_info", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_source_authority", "italian_knowledge_sources", ["authority"], unique=False)
    safe_create_index("idx_source_name", "italian_knowledge_sources", ["source_name"], unique=False)
    safe_create_index("idx_source_reliability", "italian_knowledge_sources", ["reliability_score"], unique=False)
    safe_create_index("idx_source_status", "italian_knowledge_sources", ["access_status"], unique=False)
    safe_create_index("idx_source_type", "italian_knowledge_sources", ["source_type"], unique=False)
    safe_create_table(
        "italian_legal_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "CONTRACT",
                "INVOICE",
                "RECEIPT",
                "DECLARATION",
                "FORM",
                "POWER_OF_ATTORNEY",
                "ARTICLES_OF_ASSOCIATION",
                "PRIVACY_POLICY",
                "TERMS_CONDITIONS",
                name="documenttype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title_en", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("legal_basis", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("required_fields", sa.JSON(), nullable=True),
        sa.Column("optional_fields", sa.JSON(), nullable=True),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subcategory", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("industry_specific", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("compliance_notes", sa.Text(), nullable=True),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("author", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_code"),
    )
    safe_create_index("idx_template_category", "italian_legal_templates", ["category", "subcategory"], unique=False)
    safe_create_index("idx_template_code", "italian_legal_templates", ["template_code"], unique=False)
    safe_create_index("idx_template_industry", "italian_legal_templates", ["industry_specific"], unique=False)
    safe_create_index("idx_template_type", "italian_legal_templates", ["document_type"], unique=False)
    safe_create_index("idx_template_validity", "italian_legal_templates", ["valid_from", "valid_to"], unique=False)
    safe_create_table(
        "italian_official_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "CIRCOLARE",
                "RISOLUZIONE",
                "PROVVEDIMENTO",
                "DECRETO",
                "LEGGE",
                "MESSAGGIO",
                "COMUNICATO",
                "ALTRO",
                name="documentcategory",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("authority", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rss_feed", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("full_content", sa.Text(), nullable=True),
        sa.Column("content_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("publication_date", sa.DateTime(), nullable=False),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("expiry_date", sa.DateTime(), nullable=True),
        sa.Column("tax_types", sa.JSON(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("processing_status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("vector_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("file_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    safe_create_index("idx_doc_authority", "italian_official_documents", ["authority"], unique=False)
    safe_create_index("idx_doc_category", "italian_official_documents", ["category"], unique=False)
    safe_create_index("idx_doc_collection_date", "italian_official_documents", ["collected_at"], unique=False)
    safe_create_index("idx_doc_hash", "italian_official_documents", ["content_hash"], unique=False)
    safe_create_index("idx_doc_id", "italian_official_documents", ["document_id"], unique=False)
    safe_create_index("idx_doc_pub_date", "italian_official_documents", ["publication_date"], unique=False)
    safe_create_index("idx_doc_status", "italian_official_documents", ["processing_status"], unique=False)
    safe_create_table(
        "italian_regulations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("regulation_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("number", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("full_text_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("authority", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("jurisdiction", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("enacted_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("repealed_date", sa.Date(), nullable=True),
        sa.Column("amends", sa.JSON(), nullable=True),
        sa.Column("amended_by", sa.JSON(), nullable=True),
        sa.Column("subjects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("last_verified", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_regulation_authority", "italian_regulations", ["authority"], unique=False)
    safe_create_index("idx_regulation_dates", "italian_regulations", ["enacted_date", "effective_date"], unique=False)
    safe_create_index("idx_regulation_status", "italian_regulations", ["repealed_date"], unique=False)
    safe_create_index(
        "idx_regulation_subjects", "italian_regulations", ["subjects"], unique=False, postgresql_using="gin"
    )
    safe_create_index(
        "idx_regulation_type_number", "italian_regulations", ["regulation_type", "number", "year"], unique=False
    )
    safe_create_table(
        "italian_tax_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tax_type",
            sa.Enum(
                "VAT",
                "INCOME_TAX",
                "CORPORATE_TAX",
                "WITHHOLDING_TAX",
                "REGIONAL_TAX",
                "PROPERTY_TAX",
                "STAMP_DUTY",
                name="taxtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("tax_code", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description_en", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("rate_percentage", sa.Numeric(), nullable=False),
        sa.Column("minimum_amount", sa.Numeric(), nullable=True),
        sa.Column("maximum_amount", sa.Numeric(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("law_reference", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("article_reference", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("region", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("municipality", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("exemptions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_tax_rate_code", "italian_tax_rates", ["tax_code"], unique=False)
    safe_create_index("idx_tax_rate_location", "italian_tax_rates", ["region", "municipality"], unique=False)
    safe_create_index("idx_tax_rate_type", "italian_tax_rates", ["tax_type"], unique=False)
    safe_create_index("idx_tax_rate_validity", "italian_tax_rates", ["valid_from", "valid_to"], unique=False)
    safe_create_table(
        "prompt_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("specialization_areas", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("complexity_level", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("clarity_score", sa.Float(), nullable=False),
        sa.Column("completeness_score", sa.Float(), nullable=False),
        sa.Column("accuracy_score", sa.Float(), nullable=False),
        sa.Column("overall_quality_score", sa.Float(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("average_user_rating", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("variant_group", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("accuracy_score >= 0.0 AND accuracy_score <= 1.0", name="accuracy_score_range"),
        sa.CheckConstraint("clarity_score >= 0.0 AND clarity_score <= 1.0", name="clarity_score_range"),
        sa.CheckConstraint("completeness_score >= 0.0 AND completeness_score <= 1.0", name="completeness_score_range"),
        sa.CheckConstraint(
            "overall_quality_score >= 0.0 AND overall_quality_score <= 1.0", name="overall_quality_score_range"
        ),
        sa.CheckConstraint("success_rate >= 0.0 AND success_rate <= 1.0", name="success_rate_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    safe_create_index("idx_prompt_templates_active", "prompt_templates", ["is_active"], unique=False)
    safe_create_index("idx_prompt_templates_category", "prompt_templates", ["category"], unique=False)
    safe_create_index("idx_prompt_templates_quality", "prompt_templates", ["overall_quality_score"], unique=False)
    safe_create_index("idx_prompt_templates_usage", "prompt_templates", ["usage_count"], unique=False)
    safe_create_table(
        "quality_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("metric_category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_unit", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("measurement_period", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("query_category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("expert_specialization", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("user_segment", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("confidence_interval", sa.Float(), nullable=True),
        sa.Column("standard_deviation", sa.Float(), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("benchmark_percentile", sa.Float(), nullable=True),
        sa.Column("measurement_date", sa.DateTime(), nullable=False),
        sa.Column("measurement_window_start", sa.DateTime(), nullable=False),
        sa.Column("measurement_window_end", sa.DateTime(), nullable=False),
        sa.Column("calculated_by", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("calculation_method", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("data_sources", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("sample_size >= 0", name="non_negative_sample_size"),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_quality_metrics_category", "quality_metrics", ["metric_category"], unique=False)
    safe_create_index(
        "idx_quality_metrics_name_date", "quality_metrics", ["metric_name", "measurement_date"], unique=False
    )
    safe_create_index(
        "idx_quality_metrics_period", "quality_metrics", ["measurement_period", "measurement_date"], unique=False
    )
    safe_create_table(
        "query_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_query", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("normalized_form", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("query_count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_cost_cents", sa.Integer(), nullable=False),
        sa.Column("avg_cost_cents", sa.Integer(), nullable=False),
        sa.Column("potential_savings_cents", sa.Integer(), nullable=False),
        sa.Column("avg_quality_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("avg_response_time_ms", sa.Integer(), nullable=False),
        sa.Column("query_variations", postgresql.ARRAY(sa.String(length=500)), nullable=False),
        sa.Column("semantic_tags", postgresql.ARRAY(sa.String(length=50)), nullable=False),
        sa.Column("topic_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("roi_score", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("priority_score", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("processing_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("last_analyzed", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(
        "idx_query_clusters_cost", "query_clusters", ["potential_savings_cents", "query_count"], unique=False
    )
    safe_create_index("idx_query_clusters_priority", "query_clusters", ["priority_score", "roi_score"], unique=False)
    safe_create_index(
        "idx_query_clusters_quality", "query_clusters", ["avg_quality_score", "processing_status"], unique=False
    )
    safe_create_index(op.f("ix_query_clusters_canonical_query"), "query_clusters", ["canonical_query"], unique=False)
    safe_create_index(op.f("ix_query_clusters_first_seen"), "query_clusters", ["first_seen"], unique=False)
    safe_create_index(op.f("ix_query_clusters_last_seen"), "query_clusters", ["last_seen"], unique=False)
    safe_create_index(op.f("ix_query_clusters_normalized_form"), "query_clusters", ["normalized_form"], unique=False)
    safe_create_table(
        "query_normalization_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=True),
        sa.Column("normalized_query", sa.Text(), nullable=True),
        sa.Column("query_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("cache_key", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("applied_rules", sa.JSON(), nullable=True),
        sa.Column("processing_time_ms", sa.Float(), nullable=False),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("cache_hit_after_normalization", sa.Boolean(), nullable=True),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("detected_language", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "query_normalization_patterns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pattern_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("normalized_form", sa.Text(), nullable=True),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("unique_queries", sa.Integer(), nullable=False),
        sa.Column("example_queries", sa.JSON(), nullable=True),
        sa.Column("avg_processing_time_ms", sa.Float(), nullable=False),
        sa.Column("cache_hit_rate", sa.Float(), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("complexity", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("faq_candidate", sa.Boolean(), nullable=False),
        sa.Column("faq_score", sa.Float(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern_hash"),
    )
    safe_create_table(
        "query_normalization_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False),
        sa.Column("normalized_queries", sa.Integer(), nullable=False),
        sa.Column("avg_processing_time_ms", sa.Float(), nullable=False),
        sa.Column("max_processing_time_ms", sa.Float(), nullable=False),
        sa.Column("min_processing_time_ms", sa.Float(), nullable=False),
        sa.Column("cache_hits_before", sa.Integer(), nullable=False),
        sa.Column("cache_hits_after", sa.Integer(), nullable=False),
        sa.Column("cache_hit_improvement", sa.Float(), nullable=False),
        sa.Column("rule_frequency", sa.JSON(), nullable=True),
        sa.Column("common_patterns", sa.JSON(), nullable=True),
        sa.Column("avg_confidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "tax_calculations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "calculation_type",
            sa.Enum(
                "VAT",
                "INCOME_TAX",
                "CORPORATE_TAX",
                "WITHHOLDING_TAX",
                "REGIONAL_TAX",
                "PROPERTY_TAX",
                "STAMP_DUTY",
                name="taxtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("base_amount", sa.Numeric(), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("input_parameters", sa.JSON(), nullable=True),
        sa.Column("tax_amount", sa.Numeric(), nullable=False),
        sa.Column("effective_rate", sa.Numeric(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column("regulations_used", sa.JSON(), nullable=True),
        sa.Column("tax_rates_used", sa.JSON(), nullable=True),
        sa.Column("calculation_date", sa.DateTime(), nullable=False),
        sa.Column("calculation_method", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("reviewed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("review_date", sa.DateTime(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_tax_calc_date", "tax_calculations", ["calculation_date"], unique=False)
    safe_create_index("idx_tax_calc_session", "tax_calculations", ["session_id"], unique=False)
    safe_create_index("idx_tax_calc_type", "tax_calculations", ["calculation_type"], unique=False)
    safe_create_index("idx_tax_calc_user", "tax_calculations", ["user_id"], unique=False)
    safe_create_index("idx_tax_calc_year", "tax_calculations", ["tax_year"], unique=False)
    safe_create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_event_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id"),
    )
    safe_create_index("idx_webhook_created_at", "webhook_events", ["created_at"], unique=False)
    safe_create_index("idx_webhook_event_type", "webhook_events", ["event_type"], unique=False)
    safe_create_index("idx_webhook_processed", "webhook_events", ["processed"], unique=False)
    safe_create_index("idx_webhook_stripe_event_id", "webhook_events", ["stripe_event_id"], unique=False)
    safe_create_table(
        "cost_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("threshold_eur", sa.Float(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("current_cost_eur", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("notification_sent", sa.Boolean(), nullable=False),
        sa.Column("notification_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("extra_data", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(op.f("ix_cost_alerts_user_id"), "cost_alerts", ["user_id"], unique=False)
    safe_create_table(
        "cost_optimization_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("suggestion_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("estimated_savings_eur", sa.Float(), nullable=False),
        sa.Column("estimated_savings_percentage", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("implementation_effort", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("auto_implementable", sa.Boolean(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("implemented_at", sa.DateTime(), nullable=True),
        sa.Column("actual_savings_eur", sa.Float(), nullable=True),
        sa.Column("effectiveness_score", sa.Float(), nullable=True),
        sa.Column("extra_data", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(
        op.f("ix_cost_optimization_suggestions_user_id"), "cost_optimization_suggestions", ["user_id"], unique=False
    )
    safe_create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_line1", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_line2", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_city", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_state", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_postal_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address_country", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tax_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tax_exempt", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("user_id"),
    )
    safe_create_index("idx_customer_email", "customers", ["email"], unique=False)
    safe_create_index("idx_customer_stripe_id", "customers", ["stripe_customer_id"], unique=False)
    safe_create_index("idx_customer_user_id", "customers", ["user_id"], unique=False)
    safe_create_table(
        "data_export_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("format", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("privacy_level", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("include_sensitive", sa.Boolean(), nullable=False),
        sa.Column("anonymize_pii", sa.Boolean(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("include_fatture", sa.Boolean(), nullable=False),
        sa.Column("include_f24", sa.Boolean(), nullable=False),
        sa.Column("include_dichiarazioni", sa.Boolean(), nullable=False),
        sa.Column("mask_codice_fiscale", sa.Boolean(), nullable=False),
        sa.Column("include_profile", sa.Boolean(), nullable=False),
        sa.Column("include_queries", sa.Boolean(), nullable=False),
        sa.Column("include_documents", sa.Boolean(), nullable=False),
        sa.Column("include_calculations", sa.Boolean(), nullable=False),
        sa.Column("include_subscriptions", sa.Boolean(), nullable=False),
        sa.Column("include_invoices", sa.Boolean(), nullable=False),
        sa.Column("include_usage_stats", sa.Boolean(), nullable=False),
        sa.Column("include_faq_interactions", sa.Boolean(), nullable=False),
        sa.Column("include_knowledge_searches", sa.Boolean(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("download_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("max_downloads", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("request_ip", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("download_ips", sa.JSON(), nullable=True),
        sa.Column("gdpr_lawful_basis", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("data_controller", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("retention_notice", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "document_processing_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("document_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("operation", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("processing_time_ms", sa.Float(), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("feed_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["regulatory_documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "documents",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("original_filename", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("file_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("file_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("upload_timestamp", sa.DateTime(), nullable=False),
        sa.Column("upload_ip", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("processing_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(), nullable=True),
        sa.Column("processing_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("document_category", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("document_confidence", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extracted_tables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("processing_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("virus_scan_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("virus_scan_result", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("is_sensitive_data", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("analysis_count", sa.Integer(), nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(op.f("ix_documents_expires_at"), "documents", ["expires_at"], unique=False)
    safe_create_index(op.f("ix_documents_file_hash"), "documents", ["file_hash"], unique=False)
    safe_create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    safe_create_index(op.f("ix_documents_is_deleted"), "documents", ["is_deleted"], unique=False)
    safe_create_index(op.f("ix_documents_processing_status"), "documents", ["processing_status"], unique=False)
    safe_create_index(op.f("ix_documents_upload_timestamp"), "documents", ["upload_timestamp"], unique=False)
    safe_create_index(op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False)
    safe_create_table(
        "electronic_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("xml_content", sa.Text(), nullable=True),
        sa.Column("xml_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("sdi_transmission_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("sdi_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("sdi_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("transmitted_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "export_document_analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("file_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("analysis_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("analysis_status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("entities_found", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("document_category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "export_tax_calculations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("calculation_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("input_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("region", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("municipality", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "faq_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("suggested_question", sa.Text(), nullable=False),
        sa.Column("best_response_content", sa.Text(), nullable=False),
        sa.Column("best_response_id", sa.Uuid(), nullable=True),
        sa.Column("suggested_category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("suggested_tags", postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column("regulatory_references", postgresql.ARRAY(sa.String(length=200)), nullable=True),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("estimated_monthly_savings", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("roi_score", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("priority_score", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("generation_model_suggested", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("quality_threshold", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("generation_attempts", sa.Integer(), nullable=False),
        sa.Column("max_generation_attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["query_clusters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_faq_candidates_priority", "faq_candidates", ["priority_score", "status"], unique=False)
    safe_create_index(
        "idx_faq_candidates_roi", "faq_candidates", ["roi_score", "estimated_monthly_savings"], unique=False
    )
    safe_create_index("idx_faq_candidates_status", "faq_candidates", ["status", "created_at"], unique=False)
    safe_create_table(
        "faq_generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("job_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("progress_percentage", sa.Integer(), nullable=False),
        sa.Column("progress_description", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_seconds", sa.Integer(), nullable=True),
        sa.Column("items_processed", sa.Integer(), nullable=False),
        sa.Column("items_successful", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column("total_cost_cents", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_references", postgresql.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("celery_task_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_faq_jobs_celery", "faq_generation_jobs", ["celery_task_id"], unique=False)
    safe_create_index("idx_faq_jobs_status", "faq_generation_jobs", ["status", "priority", "created_at"], unique=False)
    safe_create_index("idx_faq_jobs_type", "faq_generation_jobs", ["job_type", "status"], unique=False)
    safe_create_index(
        op.f("ix_faq_generation_jobs_celery_task_id"), "faq_generation_jobs", ["celery_task_id"], unique=False
    )
    safe_create_table(
        "faq_interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("viewed_at", sa.DateTime(), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        sa.Column("helpful_rating", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("italian_content", sa.Boolean(), nullable=False),
        sa.Column("tax_related", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "faq_obsolescence_checks",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_potentially_obsolete", sa.Boolean(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("affecting_updates", sa.JSON(), nullable=True),
        sa.Column("action_taken", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reviewed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "faq_usage_logs",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_variation", sa.Text(), nullable=True),
        sa.Column("from_cache", sa.Boolean(), nullable=False),
        sa.Column("variation_cost_euros", sa.Float(), nullable=False),
        sa.Column("variation_cost_cents", sa.Integer(), nullable=False),
        sa.Column("was_helpful", sa.Boolean(), nullable=True),
        sa.Column("followup_needed", sa.Boolean(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("feedback_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_entries.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "faq_variation_cache",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("cache_key", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("original_answer", sa.Text(), nullable=True),
        sa.Column("variation_text", sa.Text(), nullable=True),
        sa.Column("model_used", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("generation_cost_euros", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_entries.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    safe_create_table(
        "faq_version_history",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("regulatory_refs", sa.JSON(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("changed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "knowledge_base_searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_query", sa.Text(), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False),
        sa.Column("clicked_result_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("clicked_position", sa.Integer(), nullable=True),
        sa.Column("search_filters", sa.JSON(), nullable=True),
        sa.Column("search_category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("italian_query", sa.Boolean(), nullable=False),
        sa.Column("regulatory_content", sa.Boolean(), nullable=False),
        sa.Column("searched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "query_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("response_cached", sa.Boolean(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=True),
        sa.Column("model_used", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("query_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("italian_content", sa.Boolean(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_subscription_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stripe_customer_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stripe_price_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "INACTIVE",
                "PAST_DUE",
                "CANCELED",
                "UNPAID",
                "INCOMPLETE",
                "INCOMPLETE_EXPIRED",
                "TRIALING",
                name="subscriptionstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "plan_type",
            sa.Enum("TRIAL", "MONTHLY", "YEARLY", "ENTERPRISE", name="plantype", create_type=False),
            nullable=False,
        ),
        sa.Column("amount_eur", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("current_period_start", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("trial_start", sa.DateTime(), nullable=True),
        sa.Column("trial_end", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_subscription_customer_id", "subscriptions", ["stripe_customer_id"], unique=False)
    safe_create_index("idx_subscription_status", "subscriptions", ["status"], unique=False)
    safe_create_index("idx_subscription_stripe_id", "subscriptions", ["stripe_subscription_id"], unique=False)
    safe_create_index("idx_subscription_user_id", "subscriptions", ["user_id"], unique=False)
    safe_create_table(
        "system_improvements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("improvement_type", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("trigger_pattern_id", sa.Uuid(), nullable=True),
        sa.Column("expert_feedback_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("implementation_details", sa.JSON(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("target_metrics", sa.JSON(), nullable=True),
        sa.Column("baseline_metrics", sa.JSON(), nullable=True),
        sa.Column("actual_metrics", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("estimated_impact", sa.Float(), nullable=False),
        sa.Column("planned_start_date", sa.DateTime(), nullable=True),
        sa.Column("actual_start_date", sa.DateTime(), nullable=True),
        sa.Column("planned_completion_date", sa.DateTime(), nullable=True),
        sa.Column("actual_completion_date", sa.DateTime(), nullable=True),
        sa.Column("requires_expert_validation", sa.Boolean(), nullable=False),
        sa.Column("expert_approved", sa.Boolean(), nullable=True),
        sa.Column("approving_expert_id", sa.Uuid(), nullable=True),
        sa.Column("approval_date", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="improvement_confidence_range"),
        sa.CheckConstraint("estimated_impact >= 0.0 AND estimated_impact <= 1.0", name="estimated_impact_range"),
        sa.CheckConstraint("priority_score >= 0.0 AND priority_score <= 1.0", name="priority_score_range"),
        sa.ForeignKeyConstraint(
            ["trigger_pattern_id"],
            ["failure_patterns.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_system_improvements_pattern", "system_improvements", ["trigger_pattern_id"], unique=False)
    safe_create_index("idx_system_improvements_priority", "system_improvements", ["priority_score"], unique=False)
    safe_create_index("idx_system_improvements_status", "system_improvements", ["status"], unique=False)
    safe_create_index("idx_system_improvements_type", "system_improvements", ["improvement_type"], unique=False)
    safe_create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "LLM_QUERY",
                "LLM_STREAM",
                "CACHE_HIT",
                "CACHE_MISS",
                "API_REQUEST",
                name="usagetype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_eur", sa.Float(), nullable=True),
        sa.Column(
            "cost_category",
            sa.Enum(
                "LLM_INFERENCE",
                "STORAGE",
                "COMPUTE",
                "BANDWIDTH",
                "THIRD_PARTY",
                name="costcategory",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("request_size", sa.Integer(), nullable=True),
        sa.Column("response_size", sa.Integer(), nullable=True),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("user_agent", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("country_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("error_occurred", sa.Boolean(), nullable=False),
        sa.Column("error_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("pii_detected", sa.Boolean(), nullable=False),
        sa.Column("pii_types", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(op.f("ix_usage_events_session_id"), "usage_events", ["session_id"], unique=False)
    safe_create_index(op.f("ix_usage_events_timestamp"), "usage_events", ["timestamp"], unique=False)
    safe_create_index(op.f("ix_usage_events_user_id"), "usage_events", ["user_id"], unique=False)
    safe_create_table(
        "usage_quotas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("daily_requests_limit", sa.Integer(), nullable=False),
        sa.Column("daily_cost_limit_eur", sa.Float(), nullable=False),
        sa.Column("monthly_cost_limit_eur", sa.Float(), nullable=False),
        sa.Column("daily_token_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_token_limit", sa.Integer(), nullable=False),
        sa.Column("current_daily_requests", sa.Integer(), nullable=False),
        sa.Column("current_daily_cost_eur", sa.Float(), nullable=False),
        sa.Column("current_monthly_cost_eur", sa.Float(), nullable=False),
        sa.Column("current_daily_tokens", sa.Integer(), nullable=False),
        sa.Column("current_monthly_tokens", sa.Integer(), nullable=False),
        sa.Column("daily_reset_at", sa.DateTime(), nullable=False),
        sa.Column("monthly_reset_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(), nullable=True),
        sa.Column("plan_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(op.f("ix_usage_quotas_user_id"), "usage_quotas", ["user_id"], unique=True)
    safe_create_table(
        "user_usage_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("llm_requests", sa.Integer(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.Column("cache_misses", sa.Integer(), nullable=False),
        sa.Column("total_input_tokens", sa.Integer(), nullable=False),
        sa.Column("total_output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_eur", sa.Float(), nullable=False),
        sa.Column("llm_cost_eur", sa.Float(), nullable=False),
        sa.Column("avg_response_time_ms", sa.Float(), nullable=True),
        sa.Column("cache_hit_rate", sa.Float(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("model_usage", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("provider_usage", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("pii_detections", sa.Integer(), nullable=False),
        sa.Column("anonymization_rate", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="unique_user_date_summary"),
    )
    safe_create_index(op.f("ix_user_usage_summaries_date"), "user_usage_summaries", ["date"], unique=False)
    safe_create_index(op.f("ix_user_usage_summaries_user_id"), "user_usage_summaries", ["user_id"], unique=False)
    safe_create_table(
        "document_analyses",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("analysis_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("analysis_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_response", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("context_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_model", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("cost", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("validation_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("expert_validated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(op.f("ix_document_analyses_document_id"), "document_analyses", ["document_id"], unique=False)
    safe_create_index(op.f("ix_document_analyses_id"), "document_analyses", ["id"], unique=False)
    safe_create_index(op.f("ix_document_analyses_user_id"), "document_analyses", ["user_id"], unique=False)
    safe_create_table(
        "document_processing_jobs",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("worker_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index(
        op.f("ix_document_processing_jobs_document_id"), "document_processing_jobs", ["document_id"], unique=False
    )
    safe_create_index(
        op.f("ix_document_processing_jobs_expires_at"), "document_processing_jobs", ["expires_at"], unique=False
    )
    safe_create_index(op.f("ix_document_processing_jobs_id"), "document_processing_jobs", ["id"], unique=False)
    safe_create_index(op.f("ix_document_processing_jobs_status"), "document_processing_jobs", ["status"], unique=False)
    safe_create_table(
        "export_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("export_request_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("activity_timestamp", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("activity_data", sa.JSON(), nullable=True),
        sa.Column("suspicious_activity", sa.Boolean(), nullable=False),
        sa.Column("security_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["export_request_id"],
            ["data_export_requests.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_table(
        "generated_faqs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column("quality_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("quality_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("regulatory_refs", postgresql.ARRAY(sa.String(length=200)), nullable=True),
        sa.Column("legal_review_required", sa.Boolean(), nullable=False),
        sa.Column("compliance_notes", sa.Text(), nullable=True),
        sa.Column("generation_model", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("generation_cost_cents", sa.Integer(), nullable=False),
        sa.Column("generation_tokens", sa.Integer(), nullable=True),
        sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_monthly_savings", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("source_query_count", sa.Integer(), nullable=False),
        sa.Column("approval_status", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("faq_id", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("satisfaction_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("feedback_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("auto_generated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["faq_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "question", name="uq_candidate_question"),
    )
    safe_create_index("idx_generated_faqs_approval", "generated_faqs", ["approval_status", "created_at"], unique=False)
    safe_create_index(
        "idx_generated_faqs_performance", "generated_faqs", ["usage_count", "satisfaction_score"], unique=False
    )
    safe_create_index(
        "idx_generated_faqs_quality", "generated_faqs", ["quality_score", "approval_status"], unique=False
    )
    safe_create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("stripe_payment_intent_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stripe_invoice_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("stripe_charge_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("amount_eur", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "SUCCEEDED", "FAILED", "CANCELED", "REFUNDED", name="paymentstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("payment_method_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("payment_method_last4", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("payment_method_brand", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("failure_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_payment_created_at", "payments", ["created_at"], unique=False)
    safe_create_index("idx_payment_status", "payments", ["status"], unique=False)
    safe_create_index("idx_payment_stripe_intent_id", "payments", ["stripe_payment_intent_id"], unique=False)
    safe_create_index("idx_payment_subscription_id", "payments", ["subscription_id"], unique=False)
    safe_create_index("idx_payment_user_id", "payments", ["user_id"], unique=False)
    safe_create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("stripe_invoice_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stripe_subscription_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("invoice_number", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("amount_eur", sa.Float(), nullable=False),
        sa.Column("tax_eur", sa.Float(), nullable=False),
        sa.Column("total_eur", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("invoice_pdf_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("hosted_invoice_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_invoice_period", "invoices", ["period_start", "period_end"], unique=False)
    safe_create_index("idx_invoice_status", "invoices", ["status"], unique=False)
    safe_create_index("idx_invoice_stripe_id", "invoices", ["stripe_invoice_id"], unique=False)
    safe_create_index("idx_invoice_subscription_id", "invoices", ["subscription_id"], unique=False)
    safe_create_index("idx_invoice_user_id", "invoices", ["user_id"], unique=False)
    safe_create_table(
        "rss_faq_impacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("faq_id", sa.Uuid(), nullable=False),
        sa.Column("rss_update_id", sa.Uuid(), nullable=False),
        sa.Column("impact_level", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("impact_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("rss_source", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("rss_title", sa.Text(), nullable=False),
        sa.Column("rss_summary", sa.Text(), nullable=True),
        sa.Column("rss_published_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rss_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("matching_tags", postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column("matching_keywords", postgresql.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column("regulatory_changes", postgresql.ARRAY(sa.String(length=200)), nullable=True),
        sa.Column("action_required", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("action_taken", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("action_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_by", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("processing_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["action_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["generated_faqs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    safe_create_index("idx_rss_impacts_date", "rss_faq_impacts", ["rss_published_date", "created_at"], unique=False)
    safe_create_index("idx_rss_impacts_faq", "rss_faq_impacts", ["faq_id", "impact_level"], unique=False)
    safe_create_index(
        "idx_rss_impacts_priority", "rss_faq_impacts", ["impact_level", "action_required", "processed"], unique=False
    )
    safe_drop_table("checkpoint_migrations")
    safe_drop_index(op.f("idx_expert_faq_candidates_category"), table_name="expert_faq_candidates")
    safe_drop_index(op.f("idx_expert_faq_candidates_expert"), table_name="expert_faq_candidates")
    safe_drop_index(op.f("idx_expert_faq_candidates_priority"), table_name="expert_faq_candidates")
    safe_drop_index(
        op.f("idx_expert_faq_candidates_question_embedding_ivfflat"),
        table_name="expert_faq_candidates",
        postgresql_with={"lists": "50"},
        postgresql_using="ivfflat",
    )
    safe_drop_index(op.f("idx_expert_faq_candidates_status"), table_name="expert_faq_candidates")
    safe_drop_index(op.f("ix_expert_faq_candidates_query_signature"), table_name="expert_faq_candidates")
    safe_drop_table("expert_faq_candidates")
    safe_drop_index(op.f("checkpoint_writes_thread_id_idx"), table_name="checkpoint_writes")
    safe_drop_table("checkpoint_writes")
    safe_drop_index(op.f("checkpoint_blobs_thread_id_idx"), table_name="checkpoint_blobs")
    safe_drop_table("checkpoint_blobs")
    safe_drop_index(op.f("checkpoints_thread_id_idx"), table_name="checkpoints")
    safe_drop_table("checkpoints")
    safe_alter_column(
        "expert_feedback",
        "feedback_type",
        existing_type=postgresql.ENUM("correct", "incomplete", "incorrect", name="feedback_type"),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=False,
    )
    safe_alter_column(
        "expert_feedback",
        "category",
        existing_type=postgresql.ENUM(
            "normativa_obsoleta",
            "interpretazione_errata",
            "caso_mancante",
            "calcolo_sbagliato",
            "troppo_generico",
            name="italian_feedback_category",
        ),
        type_=sqlmodel.sql.sqltypes.AutoString(length=50),
        existing_nullable=True,
    )
    safe_alter_column(
        "expert_feedback",
        "regulatory_references",
        existing_type=postgresql.ARRAY(sa.TEXT()),
        type_=postgresql.ARRAY(sa.String()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_alter_column(
        "expert_feedback",
        "confidence_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
        existing_server_default=sa.text("0.0"),
    )
    safe_alter_column(
        "expert_feedback",
        "feedback_timestamp",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_feedback",
        "improvement_applied",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        existing_server_default=sa.text("false"),
    )
    safe_alter_column(
        "expert_feedback",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_feedback",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_drop_index(op.f("idx_expert_feedback_generated_faq_id"), table_name="expert_feedback")
    safe_drop_index(
        op.f("idx_expert_feedback_task_id"),
        table_name="expert_feedback",
        postgresql_where="(generated_task_id IS NOT NULL)",
    )
    safe_drop_index(op.f("idx_expert_feedback_timestamp"), table_name="expert_feedback")
    safe_create_index("idx_expert_feedback_timestamp", "expert_feedback", ["feedback_timestamp"], unique=False)
    safe_drop_constraint(op.f("expert_feedback_expert_id_fkey"), "expert_feedback", type_="foreignkey")
    safe_create_foreign_key(None, "expert_feedback", "expert_profiles", ["expert_id"], ["id"])
    safe_drop_column("expert_feedback", "task_creation_attempted")
    safe_drop_column("expert_feedback", "task_creation_success")
    safe_drop_column("expert_feedback", "additional_details")
    safe_drop_column("expert_feedback", "generated_task_id")
    safe_drop_column("expert_feedback", "generated_faq_id")
    safe_drop_column("expert_feedback", "task_creation_error")
    safe_add_column(
        "expert_generated_tasks",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    safe_alter_column(
        "expert_generated_tasks",
        "task_name",
        existing_type=sa.VARCHAR(length=50),
        type_=sqlmodel.sql.sqltypes.AutoString(length=200),
        existing_nullable=False,
    )
    safe_alter_column("expert_generated_tasks", "additional_details", existing_type=sa.TEXT(), nullable=True)
    safe_alter_column(
        "expert_generated_tasks",
        "file_path",
        existing_type=sa.VARCHAR(length=200),
        type_=sqlmodel.sql.sqltypes.AutoString(length=500),
        nullable=False,
        existing_server_default=sa.text("'SUPER_USER_TASKS.md'::character varying"),
    )
    safe_alter_column(
        "expert_generated_tasks",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_drop_constraint(op.f("expert_generated_tasks_task_id_key"), "expert_generated_tasks", type_="unique")
    safe_drop_index(op.f("idx_egt_created_at"), table_name="expert_generated_tasks")
    safe_drop_index(op.f("idx_egt_expert_id"), table_name="expert_generated_tasks")
    safe_drop_index(op.f("idx_egt_feedback_id"), table_name="expert_generated_tasks")
    safe_drop_index(op.f("idx_egt_task_id"), table_name="expert_generated_tasks")
    safe_create_index("idx_expert_generated_tasks_created_at", "expert_generated_tasks", ["created_at"], unique=False)
    safe_create_index("idx_expert_generated_tasks_expert_id", "expert_generated_tasks", ["expert_id"], unique=False)
    safe_create_index(
        "idx_expert_generated_tasks_feedback_id", "expert_generated_tasks", ["feedback_id"], unique=False
    )
    safe_create_index(op.f("ix_expert_generated_tasks_task_id"), "expert_generated_tasks", ["task_id"], unique=True)
    safe_drop_constraint(op.f("expert_generated_tasks_feedback_id_fkey"), "expert_generated_tasks", type_="foreignkey")
    safe_create_foreign_key(None, "expert_generated_tasks", "expert_feedback", ["feedback_id"], ["id"])
    safe_alter_column(
        "expert_profiles",
        "credentials",
        existing_type=postgresql.ARRAY(sa.TEXT()),
        type_=postgresql.ARRAY(sa.String()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_alter_column(
        "expert_profiles",
        "credential_types",
        existing_type=postgresql.ARRAY(
            postgresql.ENUM(
                "dottore_commercialista",
                "revisore_legale",
                "consulente_fiscale",
                "consulente_lavoro",
                "caf_operator",
                "ADMIN",
                name="expert_credential_type",
            )
        ),
        type_=postgresql.ARRAY(sa.String()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::expert_credential_type[]"),
    )
    safe_alter_column(
        "expert_profiles",
        "experience_years",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "specializations",
        existing_type=postgresql.ARRAY(sa.TEXT()),
        type_=postgresql.ARRAY(sa.String()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_alter_column(
        "expert_profiles",
        "feedback_count",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "feedback_accuracy_rate",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
        existing_server_default=sa.text("0.0"),
    )
    safe_alter_column(
        "expert_profiles",
        "average_response_time_seconds",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "trust_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
        existing_server_default=sa.text("0.5"),
    )
    safe_alter_column(
        "expert_profiles",
        "is_verified",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        existing_server_default=sa.text("false"),
    )
    safe_alter_column(
        "expert_profiles",
        "verification_date",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    safe_alter_column(
        "expert_profiles",
        "is_active",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        existing_server_default=sa.text("true"),
    )
    safe_alter_column(
        "expert_profiles",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_profiles",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_drop_constraint(op.f("expert_profiles_user_id_key"), "expert_profiles", type_="unique")
    safe_drop_constraint(op.f("expert_profiles_user_id_fkey"), "expert_profiles", type_="foreignkey")
    safe_create_foreign_key(None, "expert_profiles", "user", ["user_id"], ["id"])
    safe_add_column("faq_entries", sa.Column("similarity_score", sa.Float(), nullable=True))
    safe_alter_column("faq_entries", "question", existing_type=sa.TEXT(), nullable=True)
    safe_alter_column("faq_entries", "answer", existing_type=sa.TEXT(), nullable=True)
    safe_alter_column(
        "faq_entries",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "faq_entries",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "faq_entries",
        "search_vector",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=True,
    )
    safe_drop_index(op.f("idx_faq_entries_category"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_category_needs_review"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_created_at"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_fts"), table_name="faq_entries", postgresql_using="gin")
    safe_drop_index(op.f("idx_faq_entries_hit_count"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_language"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_language_category"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_last_used"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_needs_review"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_update_sensitivity"), table_name="faq_entries")
    safe_drop_index(op.f("idx_faq_entries_updated_at"), table_name="faq_entries")
    safe_alter_column(
        "feed_status",
        "feed_url",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=False,
    )
    safe_alter_column(
        "feed_status",
        "last_checked",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "feed_status",
        "consecutive_errors",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "feed_status", "errors", existing_type=sa.INTEGER(), nullable=False, existing_server_default=sa.text("0")
    )
    safe_alter_column(
        "feed_status",
        "last_error",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=True,
    )
    safe_alter_column(
        "feed_status",
        "check_interval_minutes",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("240"),
    )
    safe_alter_column(
        "feed_status", "enabled", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true")
    )
    safe_alter_column(
        "feed_status",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "feed_status",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_drop_index(op.f("idx_feed_status_last_success"), table_name="feed_status")
    safe_alter_column(
        "knowledge_chunks", "created_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True
    )
    safe_alter_column(
        "knowledge_feedback", "user_id", existing_type=sa.VARCHAR(), type_=sa.Integer(), existing_nullable=False
    )
    safe_create_foreign_key(None, "knowledge_feedback", "user", ["user_id"], ["id"])
    safe_alter_column(
        "knowledge_items", "created_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True
    )
    safe_alter_column(
        "knowledge_items", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True
    )
    safe_drop_index(
        op.f("idx_ki_publication_date"),
        table_name="knowledge_items",
        postgresql_where="(publication_date IS NOT NULL)",
    )
    safe_drop_index(op.f("idx_knowledge_publication_date"), table_name="knowledge_items")
    safe_add_column("regulatory_documents", sa.Column("document_metadata", sa.JSON(), nullable=True))
    safe_alter_column(
        "regulatory_documents",
        "title",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=False,
    )
    safe_alter_column(
        "regulatory_documents",
        "url",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=False,
    )
    safe_alter_column(
        "regulatory_documents",
        "published_date",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    safe_alter_column("regulatory_documents", "content", existing_type=sa.TEXT(), nullable=True)
    safe_alter_column(
        "regulatory_documents",
        "status",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum(
            "PENDING",
            "PROCESSING",
            "PROCESSED",
            "FAILED",
            "ACTIVE",
            "SUPERSEDED",
            "ARCHIVED",
            name="processingstatus",
            create_type=False,
        ),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'::character varying"),
    )
    safe_alter_column(
        "regulatory_documents",
        "processed_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "processing_errors",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "topics",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "regulatory_documents",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "regulatory_documents",
        "archived_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "archive_reason",
        existing_type=sa.TEXT(),
        type_=sqlmodel.sql.sqltypes.AutoString(),
        existing_nullable=True,
    )
    safe_drop_index(op.f("idx_regulatory_documents_source"), table_name="regulatory_documents")
    safe_drop_index(op.f("idx_regulatory_documents_status"), table_name="regulatory_documents")
    safe_create_unique_constraint(None, "regulatory_documents", ["url"])
    safe_drop_column("regulatory_documents", "metadata")
    safe_alter_column(
        "user",
        "role",
        existing_type=sa.VARCHAR(length=20),
        type_=sqlmodel.sql.sqltypes.AutoString(length=50),
        existing_nullable=False,
        existing_server_default=sa.text("'user'::character varying"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    safe_alter_column(
        "user",
        "role",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=50),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'user'::character varying"),
    )
    safe_add_column(
        "regulatory_documents",
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    )
    safe_drop_constraint(None, "regulatory_documents", type_="unique")
    safe_create_index(op.f("idx_regulatory_documents_status"), "regulatory_documents", ["status"], unique=False)
    safe_create_index(op.f("idx_regulatory_documents_source"), "regulatory_documents", ["source"], unique=False)
    safe_alter_column(
        "regulatory_documents",
        "archive_reason",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "archived_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "regulatory_documents",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "regulatory_documents",
        "topics",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "processing_errors",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "processed_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "status",
        existing_type=sa.Enum(
            "PENDING",
            "PROCESSING",
            "PROCESSED",
            "FAILED",
            "ACTIVE",
            "SUPERSEDED",
            "ARCHIVED",
            name="processingstatus",
            create_type=False,
        ),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'::character varying"),
    )
    safe_alter_column("regulatory_documents", "content", existing_type=sa.TEXT(), nullable=False)
    safe_alter_column(
        "regulatory_documents",
        "published_date",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    safe_alter_column(
        "regulatory_documents",
        "url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=False,
    )
    safe_alter_column(
        "regulatory_documents",
        "title",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=False,
    )
    safe_drop_column("regulatory_documents", "document_metadata")
    safe_create_index(op.f("idx_knowledge_publication_date"), "knowledge_items", ["publication_date"], unique=False)
    safe_create_index(
        op.f("idx_ki_publication_date"),
        "knowledge_items",
        ["publication_date"],
        unique=False,
        postgresql_where="(publication_date IS NOT NULL)",
    )
    safe_alter_column(
        "knowledge_items", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False
    )
    safe_alter_column(
        "knowledge_items", "created_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False
    )
    safe_drop_constraint(None, "knowledge_feedback", type_="foreignkey")
    safe_alter_column(
        "knowledge_feedback", "user_id", existing_type=sa.Integer(), type_=sa.VARCHAR(), existing_nullable=False
    )
    safe_alter_column(
        "knowledge_chunks", "created_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False
    )
    safe_create_index(op.f("idx_feed_status_last_success"), "feed_status", ["last_success"], unique=False)
    safe_alter_column(
        "feed_status",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "feed_status",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "feed_status", "enabled", existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true")
    )
    safe_alter_column(
        "feed_status",
        "check_interval_minutes",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("240"),
    )
    safe_alter_column(
        "feed_status",
        "last_error",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    safe_alter_column(
        "feed_status", "errors", existing_type=sa.INTEGER(), nullable=True, existing_server_default=sa.text("0")
    )
    safe_alter_column(
        "feed_status",
        "consecutive_errors",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "feed_status",
        "last_checked",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "feed_status",
        "feed_url",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=False,
    )
    safe_create_index(op.f("idx_faq_entries_updated_at"), "faq_entries", ["updated_at"], unique=False)
    safe_create_index(op.f("idx_faq_entries_update_sensitivity"), "faq_entries", ["update_sensitivity"], unique=False)
    safe_create_index(op.f("idx_faq_entries_needs_review"), "faq_entries", ["needs_review"], unique=False)
    safe_create_index(op.f("idx_faq_entries_last_used"), "faq_entries", ["last_used"], unique=False)
    safe_create_index(op.f("idx_faq_entries_language_category"), "faq_entries", ["language", "category"], unique=False)
    safe_create_index(op.f("idx_faq_entries_language"), "faq_entries", ["language"], unique=False)
    safe_create_index(op.f("idx_faq_entries_hit_count"), "faq_entries", ["hit_count"], unique=False)
    safe_create_index(
        op.f("idx_faq_entries_fts"),
        "faq_entries",
        [sa.literal_column("to_tsvector('italian'::regconfig, (question || ' '::text) || answer)")],
        unique=False,
        postgresql_using="gin",
    )
    safe_create_index(op.f("idx_faq_entries_created_at"), "faq_entries", ["created_at"], unique=False)
    safe_create_index(
        op.f("idx_faq_entries_category_needs_review"), "faq_entries", ["category", "needs_review"], unique=False
    )
    safe_create_index(op.f("idx_faq_entries_category"), "faq_entries", ["category"], unique=False)
    safe_alter_column(
        "faq_entries",
        "search_vector",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        type_=sa.TEXT(),
        existing_nullable=True,
    )
    safe_alter_column(
        "faq_entries",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "faq_entries",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column("faq_entries", "answer", existing_type=sa.TEXT(), nullable=False)
    safe_alter_column("faq_entries", "question", existing_type=sa.TEXT(), nullable=False)
    safe_drop_column("faq_entries", "similarity_score")
    safe_drop_constraint(None, "expert_profiles", type_="foreignkey")
    safe_create_foreign_key(
        op.f("expert_profiles_user_id_fkey"), "expert_profiles", "user", ["user_id"], ["id"], ondelete="CASCADE"
    )
    safe_create_unique_constraint(op.f("expert_profiles_user_id_key"), "expert_profiles", ["user_id"])
    safe_alter_column(
        "expert_profiles",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_profiles",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_profiles",
        "is_active",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        existing_server_default=sa.text("true"),
    )
    safe_alter_column(
        "expert_profiles",
        "verification_date",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    safe_alter_column(
        "expert_profiles",
        "is_verified",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        existing_server_default=sa.text("false"),
    )
    safe_alter_column(
        "expert_profiles",
        "trust_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
        existing_server_default=sa.text("0.5"),
    )
    safe_alter_column(
        "expert_profiles",
        "average_response_time_seconds",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "feedback_accuracy_rate",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
        existing_server_default=sa.text("0.0"),
    )
    safe_alter_column(
        "expert_profiles",
        "feedback_count",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "specializations",
        existing_type=postgresql.ARRAY(sa.String()),
        type_=postgresql.ARRAY(sa.TEXT()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_alter_column(
        "expert_profiles",
        "experience_years",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("0"),
    )
    safe_alter_column(
        "expert_profiles",
        "credential_types",
        existing_type=postgresql.ARRAY(sa.String()),
        type_=postgresql.ARRAY(
            postgresql.ENUM(
                "dottore_commercialista",
                "revisore_legale",
                "consulente_fiscale",
                "consulente_lavoro",
                "caf_operator",
                "ADMIN",
                name="expert_credential_type",
            )
        ),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::expert_credential_type[]"),
    )
    safe_alter_column(
        "expert_profiles",
        "credentials",
        existing_type=postgresql.ARRAY(sa.String()),
        type_=postgresql.ARRAY(sa.TEXT()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_drop_constraint(None, "expert_generated_tasks", type_="foreignkey")
    safe_create_foreign_key(
        op.f("expert_generated_tasks_feedback_id_fkey"),
        "expert_generated_tasks",
        "expert_feedback",
        ["feedback_id"],
        ["id"],
        ondelete="CASCADE",
    )
    safe_drop_index(op.f("ix_expert_generated_tasks_task_id"), table_name="expert_generated_tasks")
    safe_drop_index("idx_expert_generated_tasks_feedback_id", table_name="expert_generated_tasks")
    safe_drop_index("idx_expert_generated_tasks_expert_id", table_name="expert_generated_tasks")
    safe_drop_index("idx_expert_generated_tasks_created_at", table_name="expert_generated_tasks")
    safe_create_index(op.f("idx_egt_task_id"), "expert_generated_tasks", ["task_id"], unique=False)
    safe_create_index(op.f("idx_egt_feedback_id"), "expert_generated_tasks", ["feedback_id"], unique=False)
    safe_create_index(op.f("idx_egt_expert_id"), "expert_generated_tasks", ["expert_id"], unique=False)
    safe_create_index(
        op.f("idx_egt_created_at"), "expert_generated_tasks", [sa.literal_column("created_at DESC")], unique=False
    )
    safe_create_unique_constraint(op.f("expert_generated_tasks_task_id_key"), "expert_generated_tasks", ["task_id"])
    safe_alter_column(
        "expert_generated_tasks",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_generated_tasks",
        "file_path",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=500),
        type_=sa.VARCHAR(length=200),
        nullable=True,
        existing_server_default=sa.text("'SUPER_USER_TASKS.md'::character varying"),
    )
    safe_alter_column("expert_generated_tasks", "additional_details", existing_type=sa.TEXT(), nullable=False)
    safe_alter_column(
        "expert_generated_tasks",
        "task_name",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=200),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
    safe_drop_column("expert_generated_tasks", "updated_at")
    safe_add_column("expert_feedback", sa.Column("task_creation_error", sa.TEXT(), autoincrement=False, nullable=True))
    safe_add_column(
        "expert_feedback", sa.Column("generated_faq_id", sa.VARCHAR(length=100), autoincrement=False, nullable=True)
    )
    safe_add_column(
        "expert_feedback", sa.Column("generated_task_id", sa.VARCHAR(length=50), autoincrement=False, nullable=True)
    )
    safe_add_column("expert_feedback", sa.Column("additional_details", sa.TEXT(), autoincrement=False, nullable=True))
    safe_add_column(
        "expert_feedback", sa.Column("task_creation_success", sa.BOOLEAN(), autoincrement=False, nullable=True)
    )
    safe_add_column(
        "expert_feedback",
        sa.Column(
            "task_creation_attempted",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=True,
        ),
    )
    safe_drop_constraint(None, "expert_feedback", type_="foreignkey")
    safe_create_foreign_key(
        op.f("expert_feedback_expert_id_fkey"),
        "expert_feedback",
        "expert_profiles",
        ["expert_id"],
        ["id"],
        ondelete="CASCADE",
    )
    safe_drop_index("idx_expert_feedback_timestamp", table_name="expert_feedback")
    safe_create_index(
        op.f("idx_expert_feedback_timestamp"),
        "expert_feedback",
        [sa.literal_column("feedback_timestamp DESC")],
        unique=False,
    )
    safe_create_index(
        op.f("idx_expert_feedback_task_id"),
        "expert_feedback",
        ["generated_task_id"],
        unique=False,
        postgresql_where="(generated_task_id IS NOT NULL)",
    )
    safe_create_index(
        op.f("idx_expert_feedback_generated_faq_id"), "expert_feedback", ["generated_faq_id"], unique=False
    )
    safe_alter_column(
        "expert_feedback",
        "updated_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_feedback",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_feedback",
        "improvement_applied",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        existing_server_default=sa.text("false"),
    )
    safe_alter_column(
        "expert_feedback",
        "feedback_timestamp",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
    )
    safe_alter_column(
        "expert_feedback",
        "confidence_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
        existing_server_default=sa.text("0.0"),
    )
    safe_alter_column(
        "expert_feedback",
        "regulatory_references",
        existing_type=postgresql.ARRAY(sa.String()),
        type_=postgresql.ARRAY(sa.TEXT()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::text[]"),
    )
    safe_alter_column(
        "expert_feedback",
        "category",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=50),
        type_=postgresql.ENUM(
            "normativa_obsoleta",
            "interpretazione_errata",
            "caso_mancante",
            "calcolo_sbagliato",
            "troppo_generico",
            name="italian_feedback_category",
        ),
        existing_nullable=True,
    )
    safe_alter_column(
        "expert_feedback",
        "feedback_type",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=postgresql.ENUM("correct", "incomplete", "incorrect", name="feedback_type"),
        existing_nullable=False,
    )
    safe_create_table(
        "checkpoints",
        sa.Column("thread_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("checkpoint_ns", sa.TEXT(), server_default=sa.text("''::text"), autoincrement=False, nullable=False),
        sa.Column("checkpoint_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("parent_checkpoint_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("thread_id", "checkpoint_ns", "checkpoint_id", name=op.f("checkpoints_pkey")),
    )
    safe_create_index(op.f("checkpoints_thread_id_idx"), "checkpoints", ["thread_id"], unique=False)
    safe_create_table(
        "checkpoint_blobs",
        sa.Column("thread_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("checkpoint_ns", sa.TEXT(), server_default=sa.text("''::text"), autoincrement=False, nullable=False),
        sa.Column("channel", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("version", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("blob", postgresql.BYTEA(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint(
            "thread_id", "checkpoint_ns", "channel", "version", name=op.f("checkpoint_blobs_pkey")
        ),
    )
    safe_create_index(op.f("checkpoint_blobs_thread_id_idx"), "checkpoint_blobs", ["thread_id"], unique=False)
    safe_create_table(
        "checkpoint_writes",
        sa.Column("thread_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("checkpoint_ns", sa.TEXT(), server_default=sa.text("''::text"), autoincrement=False, nullable=False),
        sa.Column("checkpoint_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("task_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("idx", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("channel", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("blob", postgresql.BYTEA(), autoincrement=False, nullable=False),
        sa.Column("task_path", sa.TEXT(), server_default=sa.text("''::text"), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint(
            "thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx", name=op.f("checkpoint_writes_pkey")
        ),
    )
    safe_create_index(op.f("checkpoint_writes_thread_id_idx"), "checkpoint_writes", ["thread_id"], unique=False)
    safe_create_table(
        "expert_faq_candidates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), autoincrement=False, nullable=False),
        sa.Column("question", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("answer", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "source",
            sa.VARCHAR(length=20),
            server_default=sa.text("'expert_feedback'::character varying"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("expert_id", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column("expert_trust_score", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column(
            "approval_status",
            sa.VARCHAR(length=20),
            server_default=sa.text("'pending'::character varying"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("approved_by", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.Column("suggested_category", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.Column(
            "suggested_tags",
            postgresql.ARRAY(sa.TEXT()),
            server_default=sa.text("'{}'::text[]"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "regulatory_references",
            postgresql.ARRAY(sa.TEXT()),
            server_default=sa.text("'{}'::text[]"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("frequency", sa.INTEGER(), server_default=sa.text("0"), autoincrement=False, nullable=True),
        sa.Column(
            "estimated_monthly_savings",
            sa.NUMERIC(precision=10, scale=2),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "roi_score",
            sa.NUMERIC(precision=10, scale=2),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "priority_score",
            sa.NUMERIC(precision=10, scale=2),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "question_embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=1536),
            autoincrement=False,
            nullable=True,
            comment="Vector embedding of FAQ question for semantic similarity search (OpenAI ada-002, 1536d)",
        ),
        sa.Column("query_signature", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        sa.CheckConstraint(
            "approval_status::text = ANY (ARRAY['pending'::character varying, 'approved'::character varying, 'rejected'::character varying]::text[])",
            name=op.f("expert_faq_candidates_approval_status_check"),
        ),
        sa.CheckConstraint(
            "source::text = ANY (ARRAY['expert_feedback'::character varying, 'auto_generated'::character varying]::text[])",
            name=op.f("expert_faq_candidates_source_check"),
        ),
        sa.CheckConstraint("estimated_monthly_savings >= 0::numeric", name=op.f("non_negative_savings")),
        sa.CheckConstraint("frequency >= 0", name=op.f("non_negative_frequency")),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["user.id"], name=op.f("expert_faq_candidates_approved_by_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["expert_id"],
            ["expert_profiles.id"],
            name=op.f("expert_faq_candidates_expert_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("expert_faq_candidates_pkey")),
    )
    safe_create_index(
        op.f("ix_expert_faq_candidates_query_signature"), "expert_faq_candidates", ["query_signature"], unique=False
    )
    safe_create_index(
        op.f("idx_expert_faq_candidates_status"),
        "expert_faq_candidates",
        ["approval_status", sa.literal_column("created_at DESC")],
        unique=False,
    )
    safe_create_index(
        op.f("idx_expert_faq_candidates_question_embedding_ivfflat"),
        "expert_faq_candidates",
        ["question_embedding"],
        unique=False,
        postgresql_with={"lists": "50"},
        postgresql_using="ivfflat",
    )
    safe_create_index(
        op.f("idx_expert_faq_candidates_priority"),
        "expert_faq_candidates",
        [sa.literal_column("priority_score DESC"), "approval_status"],
        unique=False,
    )
    safe_create_index(
        op.f("idx_expert_faq_candidates_expert"),
        "expert_faq_candidates",
        ["expert_id", sa.literal_column("expert_trust_score DESC")],
        unique=False,
    )
    safe_create_index(
        op.f("idx_expert_faq_candidates_category"), "expert_faq_candidates", ["suggested_category"], unique=False
    )
    safe_create_table(
        "checkpoint_migrations",
        sa.Column("v", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("v", name=op.f("checkpoint_migrations_pkey")),
    )
    safe_drop_index("idx_rss_impacts_priority", table_name="rss_faq_impacts")
    safe_drop_index("idx_rss_impacts_faq", table_name="rss_faq_impacts")
    safe_drop_index("idx_rss_impacts_date", table_name="rss_faq_impacts")
    safe_drop_table("rss_faq_impacts")
    safe_drop_index("idx_invoice_user_id", table_name="invoices")
    safe_drop_index("idx_invoice_subscription_id", table_name="invoices")
    safe_drop_index("idx_invoice_stripe_id", table_name="invoices")
    safe_drop_index("idx_invoice_status", table_name="invoices")
    safe_drop_index("idx_invoice_period", table_name="invoices")
    safe_drop_table("invoices")
    safe_drop_index("idx_payment_user_id", table_name="payments")
    safe_drop_index("idx_payment_subscription_id", table_name="payments")
    safe_drop_index("idx_payment_stripe_intent_id", table_name="payments")
    safe_drop_index("idx_payment_status", table_name="payments")
    safe_drop_index("idx_payment_created_at", table_name="payments")
    safe_drop_table("payments")
    safe_drop_index("idx_generated_faqs_quality", table_name="generated_faqs")
    safe_drop_index("idx_generated_faqs_performance", table_name="generated_faqs")
    safe_drop_index("idx_generated_faqs_approval", table_name="generated_faqs")
    safe_drop_table("generated_faqs")
    safe_drop_table("export_audit_logs")
    safe_drop_index(op.f("ix_document_processing_jobs_status"), table_name="document_processing_jobs")
    safe_drop_index(op.f("ix_document_processing_jobs_id"), table_name="document_processing_jobs")
    safe_drop_index(op.f("ix_document_processing_jobs_expires_at"), table_name="document_processing_jobs")
    safe_drop_index(op.f("ix_document_processing_jobs_document_id"), table_name="document_processing_jobs")
    safe_drop_table("document_processing_jobs")
    safe_drop_index(op.f("ix_document_analyses_user_id"), table_name="document_analyses")
    safe_drop_index(op.f("ix_document_analyses_id"), table_name="document_analyses")
    safe_drop_index(op.f("ix_document_analyses_document_id"), table_name="document_analyses")
    safe_drop_table("document_analyses")
    safe_drop_index(op.f("ix_user_usage_summaries_user_id"), table_name="user_usage_summaries")
    safe_drop_index(op.f("ix_user_usage_summaries_date"), table_name="user_usage_summaries")
    safe_drop_table("user_usage_summaries")
    safe_drop_index(op.f("ix_usage_quotas_user_id"), table_name="usage_quotas")
    safe_drop_table("usage_quotas")
    safe_drop_index(op.f("ix_usage_events_user_id"), table_name="usage_events")
    safe_drop_index(op.f("ix_usage_events_timestamp"), table_name="usage_events")
    safe_drop_index(op.f("ix_usage_events_session_id"), table_name="usage_events")
    safe_drop_table("usage_events")
    safe_drop_index("idx_system_improvements_type", table_name="system_improvements")
    safe_drop_index("idx_system_improvements_status", table_name="system_improvements")
    safe_drop_index("idx_system_improvements_priority", table_name="system_improvements")
    safe_drop_index("idx_system_improvements_pattern", table_name="system_improvements")
    safe_drop_table("system_improvements")
    safe_drop_index("idx_subscription_user_id", table_name="subscriptions")
    safe_drop_index("idx_subscription_stripe_id", table_name="subscriptions")
    safe_drop_index("idx_subscription_status", table_name="subscriptions")
    safe_drop_index("idx_subscription_customer_id", table_name="subscriptions")
    safe_drop_table("subscriptions")
    safe_drop_table("query_history")
    safe_drop_table("knowledge_base_searches")
    safe_drop_table("faq_version_history")
    safe_drop_table("faq_variation_cache")
    safe_drop_table("faq_usage_logs")
    safe_drop_table("faq_obsolescence_checks")
    safe_drop_table("faq_interactions")
    safe_drop_index(op.f("ix_faq_generation_jobs_celery_task_id"), table_name="faq_generation_jobs")
    safe_drop_index("idx_faq_jobs_type", table_name="faq_generation_jobs")
    safe_drop_index("idx_faq_jobs_status", table_name="faq_generation_jobs")
    safe_drop_index("idx_faq_jobs_celery", table_name="faq_generation_jobs")
    safe_drop_table("faq_generation_jobs")
    safe_drop_index("idx_faq_candidates_status", table_name="faq_candidates")
    safe_drop_index("idx_faq_candidates_roi", table_name="faq_candidates")
    safe_drop_index("idx_faq_candidates_priority", table_name="faq_candidates")
    safe_drop_table("faq_candidates")
    safe_drop_table("export_tax_calculations")
    safe_drop_table("export_document_analysis")
    safe_drop_table("electronic_invoices")
    safe_drop_index(op.f("ix_documents_user_id"), table_name="documents")
    safe_drop_index(op.f("ix_documents_upload_timestamp"), table_name="documents")
    safe_drop_index(op.f("ix_documents_processing_status"), table_name="documents")
    safe_drop_index(op.f("ix_documents_is_deleted"), table_name="documents")
    safe_drop_index(op.f("ix_documents_id"), table_name="documents")
    safe_drop_index(op.f("ix_documents_file_hash"), table_name="documents")
    safe_drop_index(op.f("ix_documents_expires_at"), table_name="documents")
    safe_drop_table("documents")
    safe_drop_table("document_processing_log")
    safe_drop_table("data_export_requests")
    safe_drop_index("idx_customer_user_id", table_name="customers")
    safe_drop_index("idx_customer_stripe_id", table_name="customers")
    safe_drop_index("idx_customer_email", table_name="customers")
    safe_drop_table("customers")
    safe_drop_index(op.f("ix_cost_optimization_suggestions_user_id"), table_name="cost_optimization_suggestions")
    safe_drop_table("cost_optimization_suggestions")
    safe_drop_index(op.f("ix_cost_alerts_user_id"), table_name="cost_alerts")
    safe_drop_table("cost_alerts")
    safe_drop_index("idx_webhook_stripe_event_id", table_name="webhook_events")
    safe_drop_index("idx_webhook_processed", table_name="webhook_events")
    safe_drop_index("idx_webhook_event_type", table_name="webhook_events")
    safe_drop_index("idx_webhook_created_at", table_name="webhook_events")
    safe_drop_table("webhook_events")
    safe_drop_index("idx_tax_calc_year", table_name="tax_calculations")
    safe_drop_index("idx_tax_calc_user", table_name="tax_calculations")
    safe_drop_index("idx_tax_calc_type", table_name="tax_calculations")
    safe_drop_index("idx_tax_calc_session", table_name="tax_calculations")
    safe_drop_index("idx_tax_calc_date", table_name="tax_calculations")
    safe_drop_table("tax_calculations")
    safe_drop_table("query_normalization_stats")
    safe_drop_table("query_normalization_patterns")
    safe_drop_table("query_normalization_log")
    safe_drop_index(op.f("ix_query_clusters_normalized_form"), table_name="query_clusters")
    safe_drop_index(op.f("ix_query_clusters_last_seen"), table_name="query_clusters")
    safe_drop_index(op.f("ix_query_clusters_first_seen"), table_name="query_clusters")
    safe_drop_index(op.f("ix_query_clusters_canonical_query"), table_name="query_clusters")
    safe_drop_index("idx_query_clusters_quality", table_name="query_clusters")
    safe_drop_index("idx_query_clusters_priority", table_name="query_clusters")
    safe_drop_index("idx_query_clusters_cost", table_name="query_clusters")
    safe_drop_table("query_clusters")
    safe_drop_index("idx_quality_metrics_period", table_name="quality_metrics")
    safe_drop_index("idx_quality_metrics_name_date", table_name="quality_metrics")
    safe_drop_index("idx_quality_metrics_category", table_name="quality_metrics")
    safe_drop_table("quality_metrics")
    safe_drop_index("idx_prompt_templates_usage", table_name="prompt_templates")
    safe_drop_index("idx_prompt_templates_quality", table_name="prompt_templates")
    safe_drop_index("idx_prompt_templates_category", table_name="prompt_templates")
    safe_drop_index("idx_prompt_templates_active", table_name="prompt_templates")
    safe_drop_table("prompt_templates")
    safe_drop_index("idx_tax_rate_validity", table_name="italian_tax_rates")
    safe_drop_index("idx_tax_rate_type", table_name="italian_tax_rates")
    safe_drop_index("idx_tax_rate_location", table_name="italian_tax_rates")
    safe_drop_index("idx_tax_rate_code", table_name="italian_tax_rates")
    safe_drop_table("italian_tax_rates")
    safe_drop_index("idx_regulation_type_number", table_name="italian_regulations")
    safe_drop_index("idx_regulation_subjects", table_name="italian_regulations", postgresql_using="gin")
    safe_drop_index("idx_regulation_status", table_name="italian_regulations")
    safe_drop_index("idx_regulation_dates", table_name="italian_regulations")
    safe_drop_index("idx_regulation_authority", table_name="italian_regulations")
    safe_drop_table("italian_regulations")
    safe_drop_index("idx_doc_status", table_name="italian_official_documents")
    safe_drop_index("idx_doc_pub_date", table_name="italian_official_documents")
    safe_drop_index("idx_doc_id", table_name="italian_official_documents")
    safe_drop_index("idx_doc_hash", table_name="italian_official_documents")
    safe_drop_index("idx_doc_collection_date", table_name="italian_official_documents")
    safe_drop_index("idx_doc_category", table_name="italian_official_documents")
    safe_drop_index("idx_doc_authority", table_name="italian_official_documents")
    safe_drop_table("italian_official_documents")
    safe_drop_index("idx_template_validity", table_name="italian_legal_templates")
    safe_drop_index("idx_template_type", table_name="italian_legal_templates")
    safe_drop_index("idx_template_industry", table_name="italian_legal_templates")
    safe_drop_index("idx_template_code", table_name="italian_legal_templates")
    safe_drop_index("idx_template_category", table_name="italian_legal_templates")
    safe_drop_table("italian_legal_templates")
    safe_drop_index("idx_source_type", table_name="italian_knowledge_sources")
    safe_drop_index("idx_source_status", table_name="italian_knowledge_sources")
    safe_drop_index("idx_source_reliability", table_name="italian_knowledge_sources")
    safe_drop_index("idx_source_name", table_name="italian_knowledge_sources")
    safe_drop_index("idx_source_authority", table_name="italian_knowledge_sources")
    safe_drop_table("italian_knowledge_sources")
    safe_drop_table("faq_categories")
    safe_drop_table("faq_analytics_summary")
    safe_drop_index("idx_failure_patterns_type", table_name="failure_patterns")
    safe_drop_index("idx_failure_patterns_resolved", table_name="failure_patterns")
    safe_drop_index("idx_failure_patterns_impact", table_name="failure_patterns")
    safe_drop_index("idx_failure_patterns_frequency", table_name="failure_patterns")
    safe_drop_table("failure_patterns")
    safe_drop_index("idx_expert_validations_target", table_name="expert_validations")
    safe_drop_index("idx_expert_validations_status", table_name="expert_validations")
    safe_drop_index("idx_expert_validations_query", table_name="expert_validations")
    safe_drop_index("idx_expert_validations_complexity", table_name="expert_validations")
    safe_drop_table("expert_validations")
    safe_drop_table("document_collections")
    safe_drop_index("idx_compliance_user", table_name="compliance_checks")
    safe_drop_index("idx_compliance_type", table_name="compliance_checks")
    safe_drop_index("idx_compliance_status", table_name="compliance_checks")
    safe_drop_index("idx_compliance_session", table_name="compliance_checks")
    safe_drop_index("idx_compliance_followup", table_name="compliance_checks")
    safe_drop_index("idx_compliance_date", table_name="compliance_checks")
    safe_drop_table("compliance_checks")
    safe_drop_index(op.f("ix_cassazione_decisions_decision_id"), table_name="cassazione_decisions")
    safe_drop_table("cassazione_decisions")
    # ### end Alembic commands ###
