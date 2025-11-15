"""Add GDPR deletion system

Revision ID: 20250805_add_gdpr_deletion_system
Revises: 20250805_add_database_encryption
Create Date: 2025-08-05 14:30:00.000000

"""

from datetime import (
    datetime,
    timezone,
)

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250805_add_gdpr_deletion_system"
down_revision = "add_database_encryption_20250805"
branch_labels = None
depends_on = None


def upgrade():
    """Add GDPR deletion system tables and indexes."""
    # Create GDPR deletion requests table
    op.create_table(
        "gdpr_deletion_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("initiated_by_user", sa.Boolean(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False, default="normal"),
        # Timestamps
        sa.Column("request_timestamp", sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column("deletion_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_execution", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Results
        sa.Column("deletion_certificate_id", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Audit
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["user.id"],
        ),
    )

    # Create indexes for deletion requests
    op.create_index("ix_gdpr_deletion_requests_request_id", "gdpr_deletion_requests", ["request_id"], unique=True)
    op.create_index("ix_gdpr_deletion_requests_user_id", "gdpr_deletion_requests", ["user_id"])
    op.create_index("ix_gdpr_deletion_requests_status", "gdpr_deletion_requests", ["status"])
    op.create_index("ix_gdpr_deletion_requests_deletion_deadline", "gdpr_deletion_requests", ["deletion_deadline"])
    op.create_index("ix_gdpr_deletion_requests_created_at", "gdpr_deletion_requests", ["created_at"])

    # Composite index for overdue requests
    op.create_index(
        "ix_gdpr_deletion_requests_overdue",
        "gdpr_deletion_requests",
        ["deletion_deadline", "status"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # Create GDPR deletion audit log table
    op.create_table(
        "gdpr_deletion_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(50), nullable=False),
        sa.Column("original_user_id", sa.Integer(), nullable=False),
        sa.Column("anonymized_user_id", sa.String(100), nullable=True),
        # Deletion details
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("table_name", sa.String(50), nullable=True),
        sa.Column("records_deleted", sa.Integer(), nullable=False, default=0),
        sa.Column("system_type", sa.String(20), nullable=False),
        # Results
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Float(), nullable=False, default=0.0),
        # Audit trail
        sa.Column("deletion_timestamp", sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column("verification_hash", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for audit log
    op.create_index("ix_gdpr_deletion_audit_log_request_id", "gdpr_deletion_audit_log", ["request_id"])
    op.create_index("ix_gdpr_deletion_audit_log_original_user_id", "gdpr_deletion_audit_log", ["original_user_id"])
    op.create_index("ix_gdpr_deletion_audit_log_operation", "gdpr_deletion_audit_log", ["operation"])
    op.create_index("ix_gdpr_deletion_audit_log_timestamp", "gdpr_deletion_audit_log", ["deletion_timestamp"])
    op.create_index("ix_gdpr_deletion_audit_log_success", "gdpr_deletion_audit_log", ["success"])

    # Create GDPR deletion certificates table
    op.create_table(
        "gdpr_deletion_certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certificate_id", sa.String(50), nullable=False),
        sa.Column("request_id", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Certificate details
        sa.Column("is_complete_deletion", sa.Boolean(), nullable=False),
        sa.Column("compliance_attestation", sa.Boolean(), nullable=False),
        sa.Column("certificate_text", sa.Text(), nullable=False),
        sa.Column("verification_details", sa.Text(), nullable=False),  # JSON
        # Issuance
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, default=datetime.utcnow),
        sa.Column("issued_by", sa.String(100), nullable=False, default="PratikoAI-GDPR-System"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for certificates
    op.create_index(
        "ix_gdpr_deletion_certificates_certificate_id", "gdpr_deletion_certificates", ["certificate_id"], unique=True
    )
    op.create_index("ix_gdpr_deletion_certificates_request_id", "gdpr_deletion_certificates", ["request_id"])
    op.create_index("ix_gdpr_deletion_certificates_user_id", "gdpr_deletion_certificates", ["user_id"])
    op.create_index("ix_gdpr_deletion_certificates_issued_at", "gdpr_deletion_certificates", ["issued_at"])

    # Add trigger to update updated_at timestamp on gdpr_deletion_requests
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_gdpr_deletion_requests_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_gdpr_deletion_requests_updated_at
        BEFORE UPDATE ON gdpr_deletion_requests
        FOR EACH ROW EXECUTE FUNCTION update_gdpr_deletion_requests_updated_at();
    """
    )

    # Add check constraints for data validation
    op.create_check_constraint(
        "ck_gdpr_deletion_requests_status",
        "gdpr_deletion_requests",
        sa.text("status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')"),
    )

    op.create_check_constraint(
        "ck_gdpr_deletion_requests_priority",
        "gdpr_deletion_requests",
        sa.text("priority IN ('low', 'normal', 'high', 'urgent')"),
    )

    op.create_check_constraint(
        "ck_gdpr_deletion_requests_deadline",
        "gdpr_deletion_requests",
        sa.text("deletion_deadline > request_timestamp"),
    )

    op.create_check_constraint(
        "ck_gdpr_deletion_audit_log_system_type",
        "gdpr_deletion_audit_log",
        sa.text("system_type IN ('database', 'redis', 'logs', 'backups', 'stripe', 'external_api')"),
    )

    # Add comments for documentation
    op.execute(
        "COMMENT ON TABLE gdpr_deletion_requests IS 'GDPR Article 17 deletion requests with 30-day deadline tracking'"
    )
    op.execute(
        "COMMENT ON TABLE gdpr_deletion_audit_log IS 'Audit trail for GDPR deletion operations across all systems'"
    )
    op.execute("COMMENT ON TABLE gdpr_deletion_certificates IS 'GDPR deletion compliance certificates'")

    op.execute("COMMENT ON COLUMN gdpr_deletion_requests.deletion_deadline IS '30-day GDPR compliance deadline'")
    op.execute(
        "COMMENT ON COLUMN gdpr_deletion_audit_log.anonymized_user_id IS 'Anonymized identifier for audit trail preservation'"
    )
    op.execute(
        "COMMENT ON COLUMN gdpr_deletion_certificates.verification_details IS 'JSON containing detailed verification results'"
    )


def downgrade():
    """Remove GDPR deletion system tables."""
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS update_gdpr_deletion_requests_updated_at ON gdpr_deletion_requests")
    op.execute("DROP FUNCTION IF EXISTS update_gdpr_deletion_requests_updated_at()")

    # Drop tables (foreign key constraints will be dropped automatically)
    op.drop_table("gdpr_deletion_certificates")
    op.drop_table("gdpr_deletion_audit_log")
    op.drop_table("gdpr_deletion_requests")
