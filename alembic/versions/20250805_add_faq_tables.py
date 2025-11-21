"""Add Intelligent FAQ System tables

Revision ID: add_faq_tables_20250805
Revises: add_regulatory_docs_20250804
Create Date: 2025-08-05

This migration adds tables to support the Intelligent FAQ System:
- faq_entries: Core FAQ questions and answers with semantic search support
- faq_usage_logs: Track FAQ usage for analytics and cost optimization
- faq_version_history: Version control for FAQ content changes
- faq_obsolescence_checks: Track obsolescence against regulatory updates
- faq_categories: Organize FAQs by category
- faq_variation_cache: Cache GPT-3.5 response variations
- faq_analytics_summary: Aggregated performance and cost metrics
- query_normalization_log: Track Italian query normalization
- query_normalization_stats: Aggregated normalization statistics
- query_normalization_patterns: Identified query patterns

"""

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_faq_tables_20250805"
down_revision = "add_regulatory_docs_20250804"
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='{table_name}')")
    ).scalar()
    return result


def upgrade():
    """Add Intelligent FAQ System tables."""
    # Create faq_entries table
    if not table_exists("faq_entries"):
        op.create_table(
            "faq_entries",
            sa.Column("id", sa.String(length=100), primary_key=True, comment="FAQ entry UUID"),
            sa.Column("question", sa.Text(), nullable=False, comment="The FAQ question"),
            sa.Column("answer", sa.Text(), nullable=False, comment="The FAQ answer"),
            sa.Column("category", sa.String(length=100), nullable=False, default="generale", comment="FAQ category"),
            sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True, comment="Tags for filtering and search"),
            sa.Column("language", sa.String(length=10), nullable=False, default="it", comment="Content language"),
            sa.Column("last_validated", sa.DateTime(timezone=True), nullable=True, comment="Last validation date"),
            sa.Column("needs_review", sa.Boolean(), nullable=False, default=False, comment="Whether FAQ needs review"),
            sa.Column("regulatory_refs", postgresql.JSON(), nullable=True, comment="References to regulatory documents"),
            sa.Column(
                "update_sensitivity",
                sa.String(length=20),
                nullable=False,
                default="medium",
                comment="How sensitive FAQ is to regulatory changes",
            ),
            sa.Column("hit_count", sa.Integer(), nullable=False, default=0, comment="Total number of times FAQ was used"),
            sa.Column("last_used", sa.DateTime(timezone=True), nullable=True, comment="Last time FAQ was accessed"),
            sa.Column("avg_helpfulness", sa.Float(), nullable=True, comment="Average helpfulness score (0.0-1.0)"),
            sa.Column("version", sa.Integer(), nullable=False, default=1, comment="Current version number"),
            sa.Column(
                "previous_version_id",
                sa.String(length=100),
                nullable=True,
                comment="Previous version ID for version history",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Creation timestamp",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Last update timestamp",
            ),
            sa.Column("search_vector", sa.Text(), nullable=True, comment="Full-text search vector (auto-generated)"),
        )

    # Create indexes for faq_entries
    op.create_index("idx_faq_entries_category", "faq_entries", ["category"])
    op.create_index("idx_faq_entries_language", "faq_entries", ["language"])
    op.create_index("idx_faq_entries_needs_review", "faq_entries", ["needs_review"])
    op.create_index("idx_faq_entries_update_sensitivity", "faq_entries", ["update_sensitivity"])
    op.create_index("idx_faq_entries_hit_count", "faq_entries", ["hit_count"])
    op.create_index("idx_faq_entries_last_used", "faq_entries", ["last_used"])
    op.create_index("idx_faq_entries_created_at", "faq_entries", ["created_at"])
    op.create_index("idx_faq_entries_updated_at", "faq_entries", ["updated_at"])

    # Create compound indexes for common queries
    op.create_index("idx_faq_entries_category_needs_review", "faq_entries", ["category", "needs_review"])
    op.create_index("idx_faq_entries_language_category", "faq_entries", ["language", "category"])

    # Create PostgreSQL full-text search index (Italian language)
    op.execute(
        """
        CREATE INDEX idx_faq_entries_fts
        ON faq_entries
        USING GIN(to_tsvector('italian', question || ' ' || answer))
    """
    )

    # Create faq_usage_logs table
    if not table_exists("faq_usage_logs"):
        op.create_table(
            "faq_usage_logs",
            sa.Column("id", sa.String(length=100), primary_key=True, comment="Usage log UUID"),
            sa.Column("faq_id", sa.String(length=100), nullable=False, comment="FAQ entry that was used"),
            sa.Column("user_id", sa.String(length=100), nullable=True, comment="User who accessed the FAQ"),
            sa.Column(
                "used_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="When FAQ was accessed",
            ),
            sa.Column("response_variation", sa.Text(), nullable=False, comment="The actual response sent to user"),
            sa.Column(
                "from_cache", sa.Boolean(), nullable=False, default=False, comment="Whether variation came from cache"
            ),
            sa.Column(
                "variation_cost_euros",
                sa.Float(),
                nullable=False,
                default=0.0003,
                comment="Cost of variation generation in EUR",
            ),
            sa.Column(
                "variation_cost_cents",
                sa.Integer(),
                nullable=False,
                default=3,
                comment="Cost in 0.01 cent units (for precision)",
            ),
            sa.Column("was_helpful", sa.Boolean(), nullable=True, comment="User feedback: was the response helpful?"),
            sa.Column("followup_needed", sa.Boolean(), nullable=True, comment="User indicated need for followup"),
            sa.Column("comments", sa.Text(), nullable=True, comment="User comments/feedback"),
            sa.Column(
                "feedback_submitted_at", sa.DateTime(timezone=True), nullable=True, comment="When feedback was submitted"
            ),
        )

    # Create foreign key constraint for faq_usage_logs
    op.create_foreign_key(
        "fk_faq_usage_logs_faq_id", "faq_usage_logs", "faq_entries", ["faq_id"], ["id"], ondelete="CASCADE"
    )

    # Create indexes for faq_usage_logs
    op.create_index("idx_faq_usage_logs_faq_id", "faq_usage_logs", ["faq_id"])
    op.create_index("idx_faq_usage_logs_user_id", "faq_usage_logs", ["user_id"])
    op.create_index("idx_faq_usage_logs_used_at", "faq_usage_logs", ["used_at"])
    op.create_index("idx_faq_usage_logs_from_cache", "faq_usage_logs", ["from_cache"])
    op.create_index("idx_faq_usage_logs_was_helpful", "faq_usage_logs", ["was_helpful"])
    op.create_index("idx_faq_usage_logs_followup_needed", "faq_usage_logs", ["followup_needed"])

    # Create compound indexes for analytics
    op.create_index("idx_faq_usage_logs_faq_used_at", "faq_usage_logs", ["faq_id", "used_at"])
    op.create_index("idx_faq_usage_logs_user_used_at", "faq_usage_logs", ["user_id", "used_at"])

    # Create faq_version_history table
    if not table_exists("faq_version_history"):
        op.create_table(
            "faq_version_history",
            sa.Column("id", sa.String(length=100), primary_key=True, comment="Version history UUID"),
            sa.Column("faq_id", sa.String(length=100), nullable=False, comment="FAQ entry this version belongs to"),
            sa.Column("version", sa.Integer(), nullable=False, comment="Version number"),
            sa.Column("question", sa.Text(), nullable=False, comment="Question at this version"),
            sa.Column("answer", sa.Text(), nullable=False, comment="Answer at this version"),
            sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True, comment="Tags at this version"),
            sa.Column(
                "regulatory_refs", postgresql.JSON(), nullable=True, comment="Regulatory references at this version"
            ),
            sa.Column("change_reason", sa.Text(), nullable=True, comment="Reason for this version change"),
            sa.Column("changed_by", sa.String(length=100), nullable=True, comment="User who made this change"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="When this version was created",
            ),
        )

    # Create foreign key constraint for faq_version_history
    op.create_foreign_key(
        "fk_faq_version_history_faq_id", "faq_version_history", "faq_entries", ["faq_id"], ["id"], ondelete="CASCADE"
    )

    # Create indexes for faq_version_history
    op.create_index("idx_faq_version_history_faq_id", "faq_version_history", ["faq_id"])
    op.create_index("idx_faq_version_history_version", "faq_version_history", ["version"])
    op.create_index("idx_faq_version_history_created_at", "faq_version_history", ["created_at"])
    op.create_index("idx_faq_version_history_changed_by", "faq_version_history", ["changed_by"])

    # Create faq_obsolescence_checks table
    if not table_exists("faq_obsolescence_checks"):
        op.create_table(
            "faq_obsolescence_checks",
            sa.Column("id", sa.String(length=100), primary_key=True, comment="Obsolescence check UUID"),
            sa.Column("faq_id", sa.String(length=100), nullable=False, comment="FAQ entry that was checked"),
            sa.Column(
                "checked_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="When obsolescence check was performed",
            ),
            sa.Column(
                "is_potentially_obsolete",
                sa.Boolean(),
                nullable=False,
                default=False,
                comment="Whether FAQ might be obsolete",
            ),
            sa.Column(
                "confidence_score",
                sa.Float(),
                nullable=False,
                default=0.0,
                comment="Confidence in obsolescence detection (0.0-1.0)",
            ),
            sa.Column("reason", sa.Text(), nullable=True, comment="Reason for potential obsolescence"),
            sa.Column(
                "affecting_updates",
                postgresql.JSON(),
                nullable=True,
                comment="Regulatory updates that might affect this FAQ",
            ),
            sa.Column(
                "action_taken",
                sa.String(length=50),
                nullable=True,
                comment="Action taken based on check (review_flagged, auto_updated, etc.)",
            ),
            sa.Column(
                "reviewed_by", sa.String(length=100), nullable=True, comment="Admin who reviewed the obsolescence alert"
            ),
            sa.Column(
                "reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="When obsolescence alert was reviewed"
            ),
        )

    # Create foreign key constraint for faq_obsolescence_checks
    op.create_foreign_key(
        "fk_faq_obsolescence_checks_faq_id",
        "faq_obsolescence_checks",
        "faq_entries",
        ["faq_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create indexes for faq_obsolescence_checks
    op.create_index("idx_faq_obsolescence_checks_faq_id", "faq_obsolescence_checks", ["faq_id"])
    op.create_index("idx_faq_obsolescence_checks_checked_at", "faq_obsolescence_checks", ["checked_at"])
    op.create_index("idx_faq_obsolescence_checks_is_obsolete", "faq_obsolescence_checks", ["is_potentially_obsolete"])
    op.create_index("idx_faq_obsolescence_checks_confidence", "faq_obsolescence_checks", ["confidence_score"])
    op.create_index("idx_faq_obsolescence_checks_reviewed_by", "faq_obsolescence_checks", ["reviewed_by"])

    # Create faq_categories table
    if not table_exists("faq_categories"):
        op.create_table(
            "faq_categories",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=100), nullable=False, unique=True, comment="Category identifier"),
            sa.Column("display_name", sa.String(length=200), nullable=False, comment="Human-readable category name"),
            sa.Column("description", sa.Text(), nullable=True, comment="Category description"),
            sa.Column(
                "parent_category",
                sa.String(length=100),
                nullable=True,
                comment="Parent category for hierarchical organization",
            ),
            sa.Column("sort_order", sa.Integer(), nullable=False, default=0, comment="Display order"),
            sa.Column("faq_count", sa.Integer(), nullable=False, default=0, comment="Number of FAQs in this category"),
            sa.Column("total_hits", sa.Integer(), nullable=False, default=0, comment="Total hits across all FAQs"),
            sa.Column("avg_helpfulness", sa.Float(), nullable=True, comment="Average helpfulness across category"),
            sa.Column("is_active", sa.Boolean(), nullable=False, default=True, comment="Whether category is active"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Creation timestamp",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Last update timestamp",
            ),
        )

    # Create indexes for faq_categories
    op.create_index("idx_faq_categories_parent_category", "faq_categories", ["parent_category"])
    op.create_index("idx_faq_categories_sort_order", "faq_categories", ["sort_order"])
    op.create_index("idx_faq_categories_is_active", "faq_categories", ["is_active"])
    op.create_index("idx_faq_categories_faq_count", "faq_categories", ["faq_count"])

    # Create faq_variation_cache table
    if not table_exists("faq_variation_cache"):
        op.create_table(
            "faq_variation_cache",
            sa.Column("id", sa.String(length=100), primary_key=True, comment="Variation cache UUID"),
            sa.Column("faq_id", sa.String(length=100), nullable=False, comment="FAQ entry this variation is for"),
            sa.Column("user_id", sa.String(length=100), nullable=True, comment="User this variation was generated for"),
            sa.Column(
                "cache_key",
                sa.String(length=200),
                nullable=False,
                unique=True,
                comment="Unique cache key for this variation",
            ),
            sa.Column("original_answer", sa.Text(), nullable=False, comment="Original FAQ answer"),
            sa.Column("variation_text", sa.Text(), nullable=False, comment="Generated variation"),
            sa.Column(
                "model_used",
                sa.String(length=50),
                nullable=False,
                default="gpt-3.5-turbo",
                comment="LLM model used for generation",
            ),
            sa.Column("tokens_used", sa.Integer(), nullable=True, comment="Tokens consumed for generation"),
            sa.Column(
                "generation_cost_euros",
                sa.Float(),
                nullable=False,
                default=0.0003,
                comment="Cost of generating this variation",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="When variation was cached",
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="When cache entry expires"),
            sa.Column(
                "hit_count",
                sa.Integer(),
                nullable=False,
                default=0,
                comment="How many times this cached variation was used",
            ),
            sa.Column(
                "last_used", sa.DateTime(timezone=True), nullable=True, comment="Last time cached variation was accessed"
            ),
        )

    # Create foreign key constraint for faq_variation_cache
    op.create_foreign_key(
        "fk_faq_variation_cache_faq_id", "faq_variation_cache", "faq_entries", ["faq_id"], ["id"], ondelete="CASCADE"
    )

    # Create indexes for faq_variation_cache
    op.create_index("idx_faq_variation_cache_faq_id", "faq_variation_cache", ["faq_id"])
    op.create_index("idx_faq_variation_cache_user_id", "faq_variation_cache", ["user_id"])
    op.create_index("idx_faq_variation_cache_expires_at", "faq_variation_cache", ["expires_at"])
    op.create_index("idx_faq_variation_cache_created_at", "faq_variation_cache", ["created_at"])
    op.create_index("idx_faq_variation_cache_hit_count", "faq_variation_cache", ["hit_count"])

    # Create faq_analytics_summary table
    if not table_exists("faq_analytics_summary"):
        op.create_table(
            "faq_analytics_summary",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False, comment="Analytics period start"),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False, comment="Analytics period end"),
            sa.Column("period_type", sa.String(length=20), nullable=False, comment="Period type (daily, weekly, monthly)"),
            sa.Column("total_queries", sa.Integer(), nullable=False, default=0, comment="Total queries handled"),
            sa.Column("faq_responses", sa.Integer(), nullable=False, default=0, comment="Responses from FAQ system"),
            sa.Column("full_llm_responses", sa.Integer(), nullable=False, default=0, comment="Responses from full LLM"),
            sa.Column("cache_hits", sa.Integer(), nullable=False, default=0, comment="Variation cache hits"),
            sa.Column("cache_misses", sa.Integer(), nullable=False, default=0, comment="Variation cache misses"),
            sa.Column("avg_response_time_ms", sa.Float(), nullable=False, default=0.0, comment="Average response time"),
            sa.Column("avg_search_time_ms", sa.Float(), nullable=False, default=0.0, comment="Average search time"),
            sa.Column("cache_hit_rate", sa.Float(), nullable=False, default=0.0, comment="Cache hit rate (0.0-1.0)"),
            sa.Column(
                "total_variation_costs_euros", sa.Float(), nullable=False, default=0.0, comment="Total variation costs"
            ),
            sa.Column(
                "total_full_llm_costs_euros", sa.Float(), nullable=False, default=0.0, comment="Total full LLM costs"
            ),
            sa.Column(
                "cost_savings_euros", sa.Float(), nullable=False, default=0.0, comment="Cost savings vs all full LLM"
            ),
            sa.Column("cost_savings_percent", sa.Float(), nullable=False, default=0.0, comment="Cost savings percentage"),
            sa.Column("avg_helpfulness_score", sa.Float(), nullable=False, default=0.0, comment="Average helpfulness"),
            sa.Column("followup_rate", sa.Float(), nullable=False, default=0.0, comment="Rate of followup requests"),
            sa.Column(
                "obsolescence_flags", sa.Integer(), nullable=False, default=0, comment="Number of obsolescence flags"
            ),
            sa.Column("top_categories", postgresql.JSON(), nullable=True, comment="Most popular FAQ categories"),
            sa.Column("top_faqs", postgresql.JSON(), nullable=True, comment="Most accessed FAQs"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="When summary was generated",
            ),
        )

    # Create indexes for faq_analytics_summary
    op.create_index("idx_faq_analytics_summary_period_start", "faq_analytics_summary", ["period_start"])
    op.create_index("idx_faq_analytics_summary_period_end", "faq_analytics_summary", ["period_end"])
    op.create_index("idx_faq_analytics_summary_period_type", "faq_analytics_summary", ["period_type"])
    op.create_index("idx_faq_analytics_summary_created_at", "faq_analytics_summary", ["created_at"])

    # Create compound index for period queries
    op.create_index(
        "idx_faq_analytics_summary_period_type_start", "faq_analytics_summary", ["period_type", "period_start"]
    )

    # Create query_normalization_log table
    if not table_exists("query_normalization_log"):
        op.create_table(
            "query_normalization_log",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("original_query", sa.Text(), nullable=False, comment="Original user query"),
            sa.Column("normalized_query", sa.Text(), nullable=False, comment="Normalized query form"),
            sa.Column("query_hash", sa.String(length=64), nullable=False, comment="SHA256 hash of original query"),
            sa.Column("cache_key", sa.String(length=100), nullable=False, comment="Generated cache key"),
            sa.Column("applied_rules", postgresql.JSON(), nullable=True, comment="List of applied normalization rules"),
            sa.Column("processing_time_ms", sa.Float(), nullable=False, comment="Processing time in milliseconds"),
            sa.Column("cache_hit", sa.Boolean(), nullable=True, comment="Whether query resulted in cache hit"),
            sa.Column(
                "cache_hit_after_normalization", sa.Boolean(), nullable=True, comment="Cache hit after normalization"
            ),
            sa.Column("user_id", sa.String(length=100), nullable=True, comment="User who made the query"),
            sa.Column("session_id", sa.String(length=100), nullable=True, comment="Session ID"),
            sa.Column(
                "detected_language", sa.String(length=10), nullable=False, default="it", comment="Detected query language"
            ),
            sa.Column(
                "confidence_score", sa.Float(), nullable=False, default=1.0, comment="Normalization confidence (0-1)"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Log entry timestamp",
            ),
        )

    # Create indexes for query_normalization_log
    op.create_index("idx_query_normalization_log_query_hash", "query_normalization_log", ["query_hash"])
    op.create_index("idx_query_normalization_log_cache_key", "query_normalization_log", ["cache_key"])
    op.create_index("idx_query_normalization_log_user_id", "query_normalization_log", ["user_id"])
    op.create_index("idx_query_normalization_log_session_id", "query_normalization_log", ["session_id"])
    op.create_index("idx_query_normalization_log_created_at", "query_normalization_log", ["created_at"])
    op.create_index("idx_query_normalization_log_processing_time", "query_normalization_log", ["processing_time_ms"])
    op.create_index("idx_query_normalization_log_cache_hit", "query_normalization_log", ["cache_hit"])

    # Create query_normalization_stats table
    if not table_exists("query_normalization_stats"):
        op.create_table(
            "query_normalization_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False, comment="Statistics period start"),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False, comment="Statistics period end"),
            sa.Column("period_type", sa.String(length=20), nullable=False, comment="Period type (hourly, daily, weekly)"),
            sa.Column("total_queries", sa.Integer(), nullable=False, default=0, comment="Total queries processed"),
            sa.Column(
                "normalized_queries", sa.Integer(), nullable=False, default=0, comment="Queries that were normalized"
            ),
            sa.Column(
                "avg_processing_time_ms", sa.Float(), nullable=False, default=0.0, comment="Average processing time"
            ),
            sa.Column(
                "max_processing_time_ms", sa.Float(), nullable=False, default=0.0, comment="Maximum processing time"
            ),
            sa.Column(
                "min_processing_time_ms", sa.Float(), nullable=False, default=0.0, comment="Minimum processing time"
            ),
            sa.Column(
                "cache_hits_before", sa.Integer(), nullable=False, default=0, comment="Cache hits before normalization"
            ),
            sa.Column(
                "cache_hits_after", sa.Integer(), nullable=False, default=0, comment="Cache hits after normalization"
            ),
            sa.Column(
                "cache_hit_improvement", sa.Float(), nullable=False, default=0.0, comment="Cache hit rate improvement %"
            ),
            sa.Column("rule_frequency", postgresql.JSON(), nullable=True, comment="Frequency of each normalization rule"),
            sa.Column("common_patterns", postgresql.JSON(), nullable=True, comment="Most common query patterns"),
            sa.Column("avg_confidence_score", sa.Float(), nullable=False, default=1.0, comment="Average confidence score"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Statistics creation timestamp",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Last update timestamp",
            ),
        )

    # Create indexes for query_normalization_stats
    op.create_index("idx_query_normalization_stats_period_start", "query_normalization_stats", ["period_start"])
    op.create_index("idx_query_normalization_stats_period_type", "query_normalization_stats", ["period_type"])
    op.create_index("idx_query_normalization_stats_created_at", "query_normalization_stats", ["created_at"])

    # Create query_normalization_patterns table
    if not table_exists("query_normalization_patterns"):
        op.create_table(
            "query_normalization_patterns",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "pattern_hash", sa.String(length=64), nullable=False, unique=True, comment="Unique pattern identifier"
            ),
            sa.Column("normalized_form", sa.Text(), nullable=False, comment="Canonical normalized form"),
            sa.Column("frequency", sa.Integer(), nullable=False, default=1, comment="How often this pattern occurs"),
            sa.Column(
                "unique_queries", sa.Integer(), nullable=False, default=1, comment="Number of unique original queries"
            ),
            sa.Column("example_queries", postgresql.JSON(), nullable=True, comment="Example original queries"),
            sa.Column(
                "avg_processing_time_ms", sa.Float(), nullable=False, comment="Average processing time for this pattern"
            ),
            sa.Column(
                "cache_hit_rate", sa.Float(), nullable=False, default=0.0, comment="Cache hit rate for this pattern"
            ),
            sa.Column("category", sa.String(length=50), nullable=True, comment="Pattern category (tax, legal, general)"),
            sa.Column(
                "complexity",
                sa.String(length=20),
                nullable=False,
                default="medium",
                comment="Pattern complexity (simple, medium, complex)",
            ),
            sa.Column(
                "faq_candidate", sa.Boolean(), nullable=False, default=False, comment="Whether pattern is FAQ candidate"
            ),
            sa.Column("faq_score", sa.Float(), nullable=False, default=0.0, comment="FAQ suitability score (0-1)"),
            sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, comment="First occurrence"),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, comment="Most recent occurrence"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Record creation timestamp",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=text("NOW()"),
                comment="Last update timestamp",
            ),
        )

    # Create indexes for query_normalization_patterns
    op.create_index("idx_query_normalization_patterns_frequency", "query_normalization_patterns", ["frequency"])
    op.create_index(
        "idx_query_normalization_patterns_cache_hit_rate", "query_normalization_patterns", ["cache_hit_rate"]
    )
    op.create_index("idx_query_normalization_patterns_category", "query_normalization_patterns", ["category"])
    op.create_index("idx_query_normalization_patterns_complexity", "query_normalization_patterns", ["complexity"])
    op.create_index(
        "idx_query_normalization_patterns_faq_candidate", "query_normalization_patterns", ["faq_candidate"]
    )
    op.create_index("idx_query_normalization_patterns_first_seen", "query_normalization_patterns", ["first_seen"])
    op.create_index("idx_query_normalization_patterns_last_seen", "query_normalization_patterns", ["last_seen"])

    # Create triggers to update updated_at timestamp
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_faq_entries_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_faq_entries_updated_at_trigger
        BEFORE UPDATE ON faq_entries
        FOR EACH ROW
        EXECUTE FUNCTION update_faq_entries_updated_at();
    """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_faq_categories_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_faq_categories_updated_at_trigger
        BEFORE UPDATE ON faq_categories
        FOR EACH ROW
        EXECUTE FUNCTION update_faq_categories_updated_at();
    """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_query_normalization_stats_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_query_normalization_stats_updated_at_trigger
        BEFORE UPDATE ON query_normalization_stats
        FOR EACH ROW
        EXECUTE FUNCTION update_query_normalization_stats_updated_at();
    """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_query_normalization_patterns_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_query_normalization_patterns_updated_at_trigger
        BEFORE UPDATE ON query_normalization_patterns
        FOR EACH ROW
        EXECUTE FUNCTION update_query_normalization_patterns_updated_at();
    """
    )

    # Insert initial FAQ categories
    op.execute(
        """
        INSERT INTO faq_categories (name, display_name, description, sort_order, faq_count, total_hits, is_active) VALUES
        ('generale', 'Domande Generali', 'Domande generali su tasse e normative italiane', 0, 0, 0, TRUE),
        ('iva', 'IVA - Imposta sul Valore Aggiunto', 'Domande su IVA, aliquote, fatturazione elettronica', 1, 0, 0, TRUE),
        ('irpef', 'IRPEF - Imposta sui Redditi', 'Domande su IRPEF, calcolo imposte, detrazioni', 2, 0, 0, TRUE),
        ('imu', 'IMU - Imposta Municipale Unica', 'Domande su IMU, scadenze, calcolo imposta', 3, 0, 0, TRUE),
        ('tari', 'TARI - Tassa sui Rifiuti', 'Domande su TARI, tariffe, pagamenti', 4, 0, 0, TRUE),
        ('fatturazione', 'Fatturazione Elettronica', 'Domande su fatture elettroniche, SDI, XML', 5, 0, 0, TRUE),
        ('detrazioni', 'Detrazioni e Deduzioni', 'Domande su detrazioni fiscali, spese deducibili', 6, 0, 0, TRUE),
        ('scadenze', 'Scadenze Fiscali', 'Calendario scadenze, F24, versamenti', 7, 0, 0, TRUE),
        ('società', 'Tassazione Società', 'Domande su tassazione società, IRES, IRAP', 8, 0, 0, TRUE),
        ('partita_iva', 'Partita IVA', 'Domande su apertura, gestione, chiusura partita IVA', 9, 0, 0, TRUE),
        ('previdenza', 'Previdenza e Contributi', 'Domande su INPS, contributi, pensioni', 10, 0, 0, TRUE),
        ('normative', 'Normative e Decreti', 'Domande su nuove normative, circolari, decreti', 11, 0, 0, TRUE)
    """
    )


def downgrade():
    """Remove Intelligent FAQ System tables."""
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_faq_entries_updated_at_trigger ON faq_entries;")
    op.execute("DROP TRIGGER IF EXISTS update_faq_categories_updated_at_trigger ON faq_categories;")
    op.execute(
        "DROP TRIGGER IF EXISTS update_query_normalization_stats_updated_at_trigger ON query_normalization_stats;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_query_normalization_patterns_updated_at_trigger ON query_normalization_patterns;"
    )

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_faq_entries_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_faq_categories_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_query_normalization_stats_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_query_normalization_patterns_updated_at();")

    # Drop tables (indexes and constraints will be dropped automatically)
    op.drop_table("query_normalization_patterns")
    op.drop_table("query_normalization_stats")
    op.drop_table("query_normalization_log")
    op.drop_table("faq_analytics_summary")
    op.drop_table("faq_variation_cache")
    op.drop_table("faq_categories")
    op.drop_table("faq_obsolescence_checks")
    op.drop_table("faq_version_history")
    op.drop_table("faq_usage_logs")
    op.drop_table("faq_entries")
