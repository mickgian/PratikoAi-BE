"""Phase 2: Convert CCNL models to SQLModel (14 models)

Revision ID: 6c9df3d39110
Revises: 20251126_add_query_signature
Create Date: 2025-11-28 12:49:19.542076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c9df3d39110'
down_revision: Union[str, Sequence[str], None] = '20251126_add_query_signature'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create 14 CCNL tables."""
    # Create base tables first (no foreign key dependencies)

    # 1. ccnl_database (from ccnl_update_models.py)
    op.create_table('ccnl_database',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('sector_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('ccnl_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('official_name', sa.Text(), nullable=False),
    sa.Column('current_version_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ccnl_code')
    )
    op.create_index('idx_ccnl_database_active', 'ccnl_database', ['is_active'], unique=False)
    op.create_index('idx_ccnl_database_code', 'ccnl_database', ['ccnl_code'], unique=False)
    op.create_index('idx_ccnl_database_sector', 'ccnl_database', ['sector_name'], unique=False)

    # 2. ccnl_monitoring_metrics (from ccnl_update_models.py)
    op.create_table('ccnl_monitoring_metrics',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('metric_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('metric_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('value', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('unit', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('metric_metadata', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_monitoring_metrics_timestamp', 'ccnl_monitoring_metrics', ['timestamp'], unique=False)
    op.create_index('idx_monitoring_metrics_type', 'ccnl_monitoring_metrics', ['metric_type'], unique=False)

    # 3. ccnl_sectors (from ccnl_database.py)
    op.create_table('ccnl_sectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sector_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('italian_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('priority_level', sa.Integer(), nullable=False),
    sa.Column('worker_coverage_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('priority_level >= 1 AND priority_level <= 6', name='valid_priority_level'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ccnl_sectors_priority_active', 'ccnl_sectors', ['priority_level', 'active'], unique=False)
    op.create_index(op.f('ix_ccnl_sectors_sector_code'), 'ccnl_sectors', ['sector_code'], unique=True)

    # Create tables with foreign key dependencies

    # 4. ccnl_agreements (from ccnl_database.py) - depends on ccnl_sectors
    op.create_table('ccnl_agreements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sector_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('signatory_unions', sa.JSON(), nullable=True),
    sa.Column('signatory_employers', sa.JSON(), nullable=True),
    sa.Column('renewal_status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.Column('data_source', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('verification_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['sector_code'], ['ccnl_sectors.sector_code'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ccnl_agreements_dates', 'ccnl_agreements', ['valid_from', 'valid_to'], unique=False)
    op.create_index('idx_ccnl_agreements_sector_valid', 'ccnl_agreements', ['sector_code', 'valid_from', 'valid_to'], unique=False)

    # 5. ccnl_update_events (from ccnl_update_models.py) - depends on ccnl_database
    op.create_table('ccnl_update_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('ccnl_id', sa.Uuid(), nullable=False),
    sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('detected_at', sa.DateTime(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('content_summary', sa.Text(), nullable=True),
    sa.Column('classification_confidence', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['ccnl_id'], ['ccnl_database.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_update_events_ccnl_id', 'ccnl_update_events', ['ccnl_id'], unique=False)
    op.create_index('idx_update_events_detected', 'ccnl_update_events', ['detected_at'], unique=False)
    op.create_index('idx_update_events_status', 'ccnl_update_events', ['status'], unique=False)

    # 6. ccnl_versions (from ccnl_update_models.py) - depends on ccnl_database
    op.create_table('ccnl_versions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('ccnl_id', sa.Uuid(), nullable=False),
    sa.Column('version_number', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('effective_date', sa.Date(), nullable=False),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('signed_date', sa.Date(), nullable=True),
    sa.Column('document_url', sa.Text(), nullable=True),
    sa.Column('salary_data', sa.JSON(), nullable=False),
    sa.Column('working_conditions', sa.JSON(), nullable=False),
    sa.Column('leave_provisions', sa.JSON(), nullable=False),
    sa.Column('other_benefits', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['ccnl_id'], ['ccnl_database.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ccnl_versions_ccnl_id', 'ccnl_versions', ['ccnl_id'], unique=False)
    op.create_index('idx_ccnl_versions_current', 'ccnl_versions', ['is_current'], unique=False)
    op.create_index('idx_ccnl_versions_effective', 'ccnl_versions', ['effective_date'], unique=False)

    # 7. ccnl_change_logs (from ccnl_update_models.py) - depends on ccnl_database and ccnl_versions
    op.create_table('ccnl_change_logs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('ccnl_id', sa.Uuid(), nullable=False),
    sa.Column('old_version_id', sa.Uuid(), nullable=True),
    sa.Column('new_version_id', sa.Uuid(), nullable=False),
    sa.Column('change_type', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('changes_summary', sa.Text(), nullable=False),
    sa.Column('detailed_changes', sa.JSON(), nullable=False),
    sa.Column('significance_score', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
    sa.ForeignKeyConstraint(['ccnl_id'], ['ccnl_database.id'], ),
    sa.ForeignKeyConstraint(['new_version_id'], ['ccnl_versions.id'], ),
    sa.ForeignKeyConstraint(['old_version_id'], ['ccnl_versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_change_logs_ccnl_id', 'ccnl_change_logs', ['ccnl_id'], unique=False)
    op.create_index('idx_change_logs_created', 'ccnl_change_logs', ['created_at'], unique=False)
    op.create_index('idx_change_logs_significance', 'ccnl_change_logs', ['significance_score'], unique=False)

    # 8. ccnl_job_levels (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_job_levels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('level_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('level_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('worker_category', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('minimum_experience_months', sa.Integer(), nullable=False),
    sa.Column('required_qualifications', sa.JSON(), nullable=True),
    sa.Column('typical_tasks', sa.JSON(), nullable=True),
    sa.Column('decision_making_level', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
    sa.Column('supervision_responsibilities', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_job_levels_agreement_code', 'ccnl_job_levels', ['agreement_id', 'level_code'], unique=False)
    op.create_index('idx_job_levels_category', 'ccnl_job_levels', ['worker_category'], unique=False)

    # 9. ccnl_leave_entitlements (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_leave_entitlements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('leave_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('base_annual_days', sa.Integer(), nullable=True),
    sa.Column('base_annual_hours', sa.Integer(), nullable=True),
    sa.Column('seniority_bonus_schedule', sa.JSON(), nullable=True),
    sa.Column('calculation_method', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('minimum_usage_hours', sa.Integer(), nullable=True),
    sa.Column('advance_notice_hours', sa.Integer(), nullable=True),
    sa.Column('compensation_percentage', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('mandatory_period', sa.Boolean(), nullable=False),
    sa.Column('additional_optional_days', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('compensation_percentage >= 0 AND compensation_percentage <= 1', name='valid_compensation'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_leave_entitlements_agreement_type', 'ccnl_leave_entitlements', ['agreement_id', 'leave_type'], unique=False)

    # 10. ccnl_notice_periods (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_notice_periods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('worker_category', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('seniority_months_min', sa.Integer(), nullable=False),
    sa.Column('seniority_months_max', sa.Integer(), nullable=False),
    sa.Column('notice_days', sa.Integer(), nullable=False),
    sa.Column('termination_by', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('notice_days > 0', name='positive_notice_days'),
    sa.CheckConstraint('seniority_months_max >= seniority_months_min', name='valid_seniority_range'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notice_periods_agreement_category', 'ccnl_notice_periods', ['agreement_id', 'worker_category'], unique=False)

    # 11. ccnl_overtime_rules (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_overtime_rules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('daily_threshold_hours', sa.Integer(), nullable=False),
    sa.Column('weekly_threshold_hours', sa.Integer(), nullable=False),
    sa.Column('daily_overtime_rate', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('weekend_rate', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('holiday_rate', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('maximum_daily_overtime', sa.Integer(), nullable=True),
    sa.Column('maximum_weekly_overtime', sa.Integer(), nullable=True),
    sa.Column('maximum_monthly_overtime', sa.Integer(), nullable=True),
    sa.Column('maximum_annual_overtime', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('daily_overtime_rate >= 1.0', name='valid_overtime_rate'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_overtime_rules_agreement', 'ccnl_overtime_rules', ['agreement_id'], unique=False)

    # 12. ccnl_salary_tables (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_salary_tables',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('level_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('base_monthly_salary', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('geographic_area', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=True),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('thirteenth_month', sa.Boolean(), nullable=False),
    sa.Column('fourteenth_month', sa.Boolean(), nullable=False),
    sa.Column('additional_allowances', sa.JSON(), nullable=True),
    sa.Column('company_size_adjustments', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('base_monthly_salary > 0', name='positive_salary'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_salary_tables_agreement_level', 'ccnl_salary_tables', ['agreement_id', 'level_code', 'geographic_area'], unique=False)
    op.create_index('idx_salary_tables_dates', 'ccnl_salary_tables', ['valid_from', 'valid_to'], unique=False)

    # 13. ccnl_special_allowances (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_special_allowances',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('allowance_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('amount', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('frequency', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
    sa.Column('conditions', sa.JSON(), nullable=True),
    sa.Column('applicable_job_levels', sa.JSON(), nullable=True),
    sa.Column('geographic_areas', sa.JSON(), nullable=True),
    sa.Column('company_sizes', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('amount > 0', name='positive_allowance_amount'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_special_allowances_agreement_type', 'ccnl_special_allowances', ['agreement_id', 'allowance_type'], unique=False)

    # 14. ccnl_working_hours (from ccnl_database.py) - depends on ccnl_agreements
    op.create_table('ccnl_working_hours',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_id', sa.Integer(), nullable=False),
    sa.Column('ordinary_weekly_hours', sa.Integer(), nullable=False),
    sa.Column('maximum_weekly_hours', sa.Integer(), nullable=False),
    sa.Column('daily_rest_hours', sa.Integer(), nullable=False),
    sa.Column('weekly_rest_hours', sa.Integer(), nullable=False),
    sa.Column('flexible_hours_allowed', sa.Boolean(), nullable=False),
    sa.Column('flexible_hours_range_min', sa.Integer(), nullable=True),
    sa.Column('flexible_hours_range_max', sa.Integer(), nullable=True),
    sa.Column('core_hours_start', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True),
    sa.Column('core_hours_end', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True),
    sa.Column('part_time_allowed', sa.Boolean(), nullable=False),
    sa.Column('minimum_part_time_hours', sa.Integer(), nullable=True),
    sa.Column('shift_work_allowed', sa.Boolean(), nullable=False),
    sa.Column('shift_patterns', sa.JSON(), nullable=True),
    sa.Column('night_shift_allowance', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('maximum_weekly_hours >= ordinary_weekly_hours', name='max_hours_valid'),
    sa.CheckConstraint('ordinary_weekly_hours > 0', name='positive_weekly_hours'),
    sa.ForeignKeyConstraint(['agreement_id'], ['ccnl_agreements.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_working_hours_agreement', 'ccnl_working_hours', ['agreement_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Drop 14 CCNL tables in reverse order (respecting foreign keys)."""
    # Drop tables in reverse order of creation to respect foreign key constraints

    # Drop tables dependent on ccnl_agreements (9 tables total from this group)
    op.drop_index('idx_working_hours_agreement', table_name='ccnl_working_hours')
    op.drop_table('ccnl_working_hours')

    op.drop_index('idx_special_allowances_agreement_type', table_name='ccnl_special_allowances')
    op.drop_table('ccnl_special_allowances')

    op.drop_index('idx_salary_tables_dates', table_name='ccnl_salary_tables')
    op.drop_index('idx_salary_tables_agreement_level', table_name='ccnl_salary_tables')
    op.drop_table('ccnl_salary_tables')

    op.drop_index('idx_overtime_rules_agreement', table_name='ccnl_overtime_rules')
    op.drop_table('ccnl_overtime_rules')

    op.drop_index('idx_notice_periods_agreement_category', table_name='ccnl_notice_periods')
    op.drop_table('ccnl_notice_periods')

    op.drop_index('idx_leave_entitlements_agreement_type', table_name='ccnl_leave_entitlements')
    op.drop_table('ccnl_leave_entitlements')

    op.drop_index('idx_job_levels_category', table_name='ccnl_job_levels')
    op.drop_index('idx_job_levels_agreement_code', table_name='ccnl_job_levels')
    op.drop_table('ccnl_job_levels')

    # Drop table dependent on ccnl_database and ccnl_versions
    op.drop_index('idx_change_logs_significance', table_name='ccnl_change_logs')
    op.drop_index('idx_change_logs_created', table_name='ccnl_change_logs')
    op.drop_index('idx_change_logs_ccnl_id', table_name='ccnl_change_logs')
    op.drop_table('ccnl_change_logs')

    # Drop tables dependent on ccnl_database
    op.drop_index('idx_ccnl_versions_effective', table_name='ccnl_versions')
    op.drop_index('idx_ccnl_versions_current', table_name='ccnl_versions')
    op.drop_index('idx_ccnl_versions_ccnl_id', table_name='ccnl_versions')
    op.drop_table('ccnl_versions')

    op.drop_index('idx_update_events_status', table_name='ccnl_update_events')
    op.drop_index('idx_update_events_detected', table_name='ccnl_update_events')
    op.drop_index('idx_update_events_ccnl_id', table_name='ccnl_update_events')
    op.drop_table('ccnl_update_events')

    # Drop table dependent on ccnl_sectors
    op.drop_index('idx_ccnl_agreements_sector_valid', table_name='ccnl_agreements')
    op.drop_index('idx_ccnl_agreements_dates', table_name='ccnl_agreements')
    op.drop_table('ccnl_agreements')

    # Drop base tables (no dependencies)
    op.drop_index(op.f('ix_ccnl_sectors_sector_code'), table_name='ccnl_sectors')
    op.drop_index('idx_ccnl_sectors_priority_active', table_name='ccnl_sectors')
    op.drop_table('ccnl_sectors')

    op.drop_index('idx_monitoring_metrics_type', table_name='ccnl_monitoring_metrics')
    op.drop_index('idx_monitoring_metrics_timestamp', table_name='ccnl_monitoring_metrics')
    op.drop_table('ccnl_monitoring_metrics')

    op.drop_index('idx_ccnl_database_sector', table_name='ccnl_database')
    op.drop_index('idx_ccnl_database_code', table_name='ccnl_database')
    op.drop_index('idx_ccnl_database_active', table_name='ccnl_database')
    op.drop_table('ccnl_database')
