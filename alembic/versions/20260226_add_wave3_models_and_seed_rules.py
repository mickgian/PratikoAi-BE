"""DEV-321,380,372,374: Wave 3 models and matching rules seed.

Creates tables:
  - deadlines: Deadline definitions from multiple sources
  - client_deadlines: Many-to-many link between clients and deadlines
  - dpas: Data Processing Agreement versions
  - dpa_acceptances: Studio DPA acceptance records
  - breach_notifications: GDPR breach incident tracking

Seeds:
  - 15 matching rules (10 MVP + 5 extended) into matching_rules table

Revision ID: add_wave3_20260226
Revises: add_pratikoai_2_0_20260226
Create Date: 2026-02-26 22:00:00.000000

"""

import json
from pathlib import Path
from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

revision: str = "add_wave3_20260226"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "add_pratikoai_2_0_20260226"  # pragma: allowlist secret
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

    # =========================================================================
    # 1. deadlines (DEV-380)
    # =========================================================================
    if not _table_exists("deadlines"):
        op.create_table(
            "deadlines",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("deadline_type", sa.String(20), nullable=False),
            sa.Column("source", sa.String(20), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("recurrence_rule", sa.String(50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_deadlines_type_active", "deadlines", ["deadline_type", "is_active"])
        op.create_index("ix_deadlines_due_date", "deadlines", ["due_date"])

    # =========================================================================
    # 2. client_deadlines (DEV-380)
    # =========================================================================
    if not _table_exists("client_deadlines"):
        op.create_table(
            "client_deadlines",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("client_id", sa.Integer(), nullable=False),
            sa.Column("deadline_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"]),
            sa.ForeignKeyConstraint(["studio_id"], ["studios.id"]),
        )
        op.create_index("ix_client_deadlines_client_id", "client_deadlines", ["client_id"])
        op.create_index("ix_client_deadlines_deadline_id", "client_deadlines", ["deadline_id"])
        op.create_index("ix_client_deadlines_studio", "client_deadlines", ["studio_id"])
        op.create_index(
            "ix_client_deadlines_client_deadline",
            "client_deadlines",
            ["client_id", "deadline_id"],
            unique=True,
        )

    # =========================================================================
    # 3. dpas (DEV-372)
    # =========================================================================
    if not _table_exists("dpas"):
        op.create_table(
            "dpas",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("version", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_dpas_status", "dpas", ["status"])
        op.create_index("ix_dpas_version", "dpas", ["version"])

    # =========================================================================
    # 4. dpa_acceptances (DEV-372)
    # =========================================================================
    if not _table_exists("dpa_acceptances"):
        op.create_table(
            "dpa_acceptances",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dpa_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("accepted_by", sa.Integer(), nullable=False),
            sa.Column(
                "accepted_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("ip_address", sa.String(45), nullable=False),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["dpa_id"], ["dpas.id"]),
            sa.ForeignKeyConstraint(["studio_id"], ["studios.id"]),
            sa.ForeignKeyConstraint(["accepted_by"], ["user.id"]),
        )
        op.create_index("ix_dpa_acceptances_studio_dpa", "dpa_acceptances", ["studio_id", "dpa_id"])

    # =========================================================================
    # 5. breach_notifications (DEV-374)
    # =========================================================================
    if not _table_exists("breach_notifications"):
        op.create_table(
            "breach_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("studio_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(10), nullable=False),
            sa.Column("status", sa.String(25), nullable=False, server_default="detected"),
            sa.Column("reported_by", sa.Integer(), nullable=False),
            sa.Column(
                "detected_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("authority_notified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("affected_records_count", sa.Integer(), nullable=True),
            sa.Column("data_categories", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["studio_id"], ["studios.id"]),
            sa.ForeignKeyConstraint(["reported_by"], ["user.id"]),
        )
        op.create_index(
            "ix_breach_notifications_studio_status",
            "breach_notifications",
            ["studio_id", "status"],
        )
        op.create_index(
            "ix_breach_notifications_severity",
            "breach_notifications",
            ["severity"],
        )

    # =========================================================================
    # 6. Seed matching rules (DEV-321)
    # =========================================================================
    rules_file = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "matching_rules.json"
    if rules_file.exists():
        rules = json.loads(rules_file.read_text(encoding="utf-8"))

        for rule in rules:
            # Check if rule already exists by name
            exists = conn.execute(
                sa.text("SELECT 1 FROM matching_rules WHERE name = :name"),
                {"name": rule["name"]},
            ).scalar()
            if exists:
                continue

            conn.execute(
                sa.text(
                    """
                    INSERT INTO matching_rules
                        (id, name, description, rule_type, conditions, priority,
                         is_active, valid_from, valid_to, categoria, fonte_normativa, created_at)
                    VALUES
                        (gen_random_uuid(), :name, :description, :rule_type, CAST(:conditions AS jsonb),
                         :priority, true, :valid_from, :valid_to, :categoria, :fonte_normativa, now())
                    """
                ),
                {
                    "name": rule["name"],
                    "description": rule["description"],
                    "rule_type": rule["rule_type"],
                    "conditions": json.dumps(rule["conditions"]),
                    "priority": rule["priority"],
                    "valid_from": rule["valid_from"],
                    "valid_to": rule.get("valid_to"),
                    "categoria": rule["categoria"],
                    "fonte_normativa": rule["fonte_normativa"],
                },
            )


def downgrade() -> None:
    # Remove seeded matching rules
    op.execute(
        "DELETE FROM matching_rules WHERE name LIKE 'R0%'"
    )

    op.drop_table("breach_notifications")
    op.drop_table("dpa_acceptances")
    op.drop_table("dpas")
    op.drop_table("client_deadlines")
    op.drop_table("deadlines")
