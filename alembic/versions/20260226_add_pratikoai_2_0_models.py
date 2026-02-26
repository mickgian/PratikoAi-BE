"""DEV-307: Add PratikoAI 2.0 Phase 0 tables.

Creates 8 tables for Waves 0-1 models:
  - studios: Multi-tenant root entity
  - clients: Studio clients with encrypted PII and soft delete
  - client_profiles: 1:1 business/fiscal metadata + 1536-dim vector
  - matching_rules: Normative matching engine rules
  - communications: Draft/approve workflow with audit trail
  - procedure: Interactive procedures with versioning
  - procedura_progress: User progress through procedures
  - proactive_suggestions: Background matching results

Also creates:
  - HNSW vector index on client_profiles.profile_vector (m=16, ef_construction=64)
  - Composite indexes for common query patterns
  - Foreign key constraints with CASCADE where appropriate

Revision ID: add_pratikoai_2_0_20260226
Revises: add_release_notes_20260226
Create Date: 2026-02-26 21:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "add_pratikoai_2_0_20260226"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_release_notes_20260226"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    def _table_exists(name: str) -> bool:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :name)"
            ),
            {"name": name},
        )
        return result.scalar()  # type: ignore[return-value]

    # Ensure pgvector extension is available for profile_vector column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # =========================================================================
    # 1. studios - multi-tenant root entity (DEV-300)
    # =========================================================================
    if not _table_exists("studios"):
        op.create_table(
            "studios",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("settings", postgresql.JSONB(), nullable=True),
            sa.Column("max_clients", sa.Integer(), nullable=False, server_default="100"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index("ix_studios_slug", "studios", ["slug"])
        op.create_index("ix_studios_name", "studios", ["name"])

    # =========================================================================
    # 2. clients - studio clients with encrypted PII (DEV-301)
    # =========================================================================
    if not _table_exists("clients"):
        op.create_table(
            "clients",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("codice_fiscale", sa.LargeBinary(), nullable=False),
            sa.Column("partita_iva", sa.LargeBinary(), nullable=True),
            sa.Column("nome", sa.LargeBinary(), nullable=False),
            sa.Column("email", sa.LargeBinary(), nullable=True),
            sa.Column("phone", sa.LargeBinary(), nullable=True),
            sa.Column("tipo_cliente", sa.String(length=30), nullable=False),
            sa.Column(
                "stato_cliente",
                sa.String(length=20),
                nullable=False,
                server_default="attivo",
            ),
            sa.Column("indirizzo", sa.String(length=300), nullable=True),
            sa.Column("cap", sa.String(length=5), nullable=True),
            sa.Column("comune", sa.String(length=100), nullable=False),
            sa.Column("provincia", sa.String(length=2), nullable=False),
            sa.Column("data_nascita_titolare", sa.Date(), nullable=True),
            sa.Column("note_studio", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["studio_id"],
                ["studios.id"],
                name="fk_clients_studio_id",
            ),
        )
        op.create_index("ix_clients_studio_id", "clients", ["studio_id"])
        op.create_index("ix_clients_studio_stato", "clients", ["studio_id", "stato_cliente"])

    # =========================================================================
    # 3. client_profiles - 1:1 business metadata + vector (DEV-302)
    # =========================================================================
    if not _table_exists("client_profiles"):
        op.create_table(
            "client_profiles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("client_id", sa.Integer(), nullable=False),
            sa.Column("codice_ateco_principale", sa.String(length=10), nullable=False),
            sa.Column(
                "codici_ateco_secondari",
                postgresql.ARRAY(sa.String(10)),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("regime_fiscale", sa.String(length=20), nullable=False),
            sa.Column("ccnl_applicato", sa.String(length=100), nullable=True),
            sa.Column("n_dipendenti", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("data_inizio_attivita", sa.Date(), nullable=False),
            sa.Column("data_cessazione_attivita", sa.Date(), nullable=True),
            sa.Column("immobili", postgresql.JSONB(), nullable=True),
            sa.Column("posizione_agenzia_entrate", sa.String(length=15), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["client_id"],
                ["clients.id"],
                name="fk_client_profiles_client_id",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("client_id", name="uq_client_profiles_client_id"),
        )
        op.create_index("ix_client_profiles_client_id", "client_profiles", ["client_id"])
        op.create_index("ix_client_profiles_regime", "client_profiles", ["regime_fiscale"])
        op.create_index("ix_client_profiles_ateco", "client_profiles", ["codice_ateco_principale"])

    # Add the profile_vector column as raw SQL (pgvector type not in sa dialects)
    conn.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='client_profiles') "
            "AND NOT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name='client_profiles' AND column_name='profile_vector') "
            "THEN ALTER TABLE client_profiles ADD COLUMN profile_vector vector(1536); "
            "END IF; "
            "END $$"
        )
    )

    # HNSW index for profile_vector with m=16, ef_construction=64
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_client_profiles_vector_hnsw "
        "ON client_profiles USING hnsw (profile_vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # =========================================================================
    # 4. matching_rules - normative matching rules (DEV-303)
    # =========================================================================
    if not _table_exists("matching_rules"):
        op.create_table(
            "matching_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("rule_type", sa.String(length=20), nullable=False),
            sa.Column("conditions", postgresql.JSONB(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column("valid_from", sa.Date(), nullable=False),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("categoria", sa.String(length=50), nullable=False),
            sa.Column("fonte_normativa", sa.String(length=200), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_matching_rules_name", "matching_rules", ["name"])
        op.create_index(
            "ix_matching_rules_type_active",
            "matching_rules",
            ["rule_type", "is_active"],
        )
        op.create_index("ix_matching_rules_priority", "matching_rules", ["priority"])

    # =========================================================================
    # 5. communications - draft/approve workflow (DEV-304)
    # =========================================================================
    if not _table_exists("communications"):
        op.create_table(
            "communications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_id", sa.Integer(), nullable=True),
            sa.Column("subject", sa.String(length=300), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("channel", sa.String(length=15), nullable=False),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("normativa_riferimento", sa.String(length=200), nullable=True),
            sa.Column("matching_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["studio_id"],
                ["studios.id"],
                name="fk_communications_studio_id",
            ),
            sa.ForeignKeyConstraint(
                ["client_id"],
                ["clients.id"],
                name="fk_communications_client_id",
            ),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["user.id"],
                name="fk_communications_created_by",
            ),
            sa.ForeignKeyConstraint(
                ["approved_by"],
                ["user.id"],
                name="fk_communications_approved_by",
            ),
            sa.ForeignKeyConstraint(
                ["matching_rule_id"],
                ["matching_rules.id"],
                name="fk_communications_matching_rule_id",
            ),
        )
        op.create_index("ix_communications_studio_id", "communications", ["studio_id"])
        op.create_index("ix_communications_client_id", "communications", ["client_id"])
        op.create_index(
            "ix_communications_studio_status",
            "communications",
            ["studio_id", "status"],
        )
        op.create_index("ix_communications_created_by", "communications", ["created_by"])

    # =========================================================================
    # 6. procedure - interactive procedures (DEV-305)
    # =========================================================================
    if not _table_exists("procedure"):
        op.create_table(
            "procedure",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=20), nullable=False),
            sa.Column("steps", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("estimated_time_minutes", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column("last_updated", sa.Date(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_procedure_code", "procedure", ["code"])
        op.create_index("ix_procedure_category_active", "procedure", ["category", "is_active"])

    # =========================================================================
    # 7. procedura_progress - user progress tracking (DEV-306)
    # =========================================================================
    if not _table_exists("procedura_progress"):
        op.create_table(
            "procedura_progress",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("procedura_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_id", sa.Integer(), nullable=True),
            sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "completed_steps",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["user.id"],
                name="fk_procedura_progress_user_id",
            ),
            sa.ForeignKeyConstraint(
                ["studio_id"],
                ["studios.id"],
                name="fk_procedura_progress_studio_id",
            ),
            sa.ForeignKeyConstraint(
                ["procedura_id"],
                ["procedure.id"],
                name="fk_procedura_progress_procedura_id",
            ),
            sa.ForeignKeyConstraint(
                ["client_id"],
                ["clients.id"],
                name="fk_procedura_progress_client_id",
            ),
        )
        op.create_index("ix_procedura_progress_user_id", "procedura_progress", ["user_id"])
        op.create_index("ix_procedura_progress_studio", "procedura_progress", ["studio_id"])
        op.create_index(
            "ix_procedura_progress_procedura_id",
            "procedura_progress",
            ["procedura_id"],
        )
        op.create_index("ix_procedura_progress_client_id", "procedura_progress", ["client_id"])
        op.create_index(
            "ix_procedura_progress_user_procedura",
            "procedura_progress",
            ["user_id", "procedura_id"],
        )

    # =========================================================================
    # 8. proactive_suggestions - background matching results (DEV-324)
    # =========================================================================
    if not _table_exists("proactive_suggestions"):
        op.create_table(
            "proactive_suggestions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("knowledge_item_id", sa.Integer(), nullable=False),
            sa.Column(
                "matched_client_ids",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column("match_score", sa.Float(), nullable=False),
            sa.Column("suggestion_text", sa.Text(), nullable=False),
            sa.Column(
                "is_read",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "is_dismissed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["studio_id"],
                ["studios.id"],
                name="fk_proactive_suggestions_studio_id",
            ),
            sa.ForeignKeyConstraint(
                ["knowledge_item_id"],
                ["knowledge_items.id"],
                name="fk_proactive_suggestions_knowledge_item_id",
            ),
        )
        op.create_index(
            "ix_proactive_suggestions_studio_id",
            "proactive_suggestions",
            ["studio_id"],
        )
        op.create_index(
            "ix_proactive_suggestions_knowledge_item_id",
            "proactive_suggestions",
            ["knowledge_item_id"],
        )
        op.create_index(
            "ix_proactive_suggestions_studio_read",
            "proactive_suggestions",
            ["studio_id", "is_read"],
        )
        op.create_index(
            "ix_proactive_suggestions_score",
            "proactive_suggestions",
            ["match_score"],
        )


def downgrade() -> None:
    # Remove tables in reverse dependency order
    op.drop_table("proactive_suggestions")
    op.drop_table("procedura_progress")
    op.drop_table("procedure")
    op.drop_table("communications")
    op.drop_table("matching_rules")
    op.drop_table("client_profiles")
    op.drop_table("clients")
    op.drop_table("studios")
