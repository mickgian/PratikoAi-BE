"""Wave 5: Multi-Tenancy + Import/Export + Advanced Matching.

DEV-422: Notifications table
DEV-316: Tenant context middleware (no migration needed)
DEV-313: Client import (no migration needed)
DEV-317: Client GDPR deletion (no migration needed)
DEV-325: Background matching job (no migration needed)
DEV-326: Matching API (no migration needed)
DEV-338: Communication audit logging (no migration needed)
DEV-346: Procedura analytics (no migration needed)
DEV-382: Deadline extraction (no migration needed)
DEV-383: Client-deadline matching (no migration needed)
DEV-384: Deadline notification job (no migration needed)
DEV-385: Deadlines API (no migration needed)
DEV-377: Data rights API (no migration needed)

Revision ID: wave5_20260227
Revises: wave4_20260227
"""

import sqlalchemy as sa

from alembic import op

revision = "wave5_20260227"
down_revision = "wave4_20260227"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # DEV-422: Notifications table
    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("studio_id", sa.Uuid(), sa.ForeignKey("studios.id"), nullable=False),
            sa.Column("notification_type", sa.String(20), nullable=False),
            sa.Column("priority", sa.String(10), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("reference_id", sa.Uuid(), nullable=True),
            sa.Column("reference_type", sa.String(50), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("dismissed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_studio_id", "notifications", ["studio_id"])
        op.create_index("ix_notifications_reference_id", "notifications", ["reference_id"])
        op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])
        op.create_index("ix_notifications_studio_type", "notifications", ["studio_id", "notification_type"])
        op.create_index("ix_notifications_created", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created", table_name="notifications")
    op.drop_index("ix_notifications_studio_type", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_reference_id", table_name="notifications")
    op.drop_index("ix_notifications_studio_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
