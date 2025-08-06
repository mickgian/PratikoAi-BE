"""Add database encryption infrastructure

Revision ID: add_database_encryption_20250805
Revises: add_faq_tables_20250805
Create Date: 2025-08-05

This migration adds database encryption infrastructure:
- Enable pgcrypto extension for encryption functions
- Create encryption_keys table for key management
- Create encryption_audit_log table for compliance tracking
- Add encryption functions and triggers
- Set up initial encryption configuration

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_database_encryption_20250805'
down_revision = 'add_faq_tables_20250805'
branch_labels = None
depends_on = None


def upgrade():
    """Add database encryption infrastructure."""
    
    # Enable pgcrypto extension for encryption functions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    
    # Create encryption_keys table for key management
    op.create_table(
        'encryption_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key_version', sa.Integer(), unique=True, nullable=False,
                 comment='Version number of the encryption key'),
        sa.Column('encrypted_key', sa.LargeBinary(), nullable=False,
                 comment='Encrypted key data (encrypted with master key)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='Key creation timestamp'),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True,
                 comment='When key was rotated (deactivated)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True,
                 comment='Whether this key version is currently active'),
        sa.Column('algorithm', sa.String(50), nullable=False, default='AES-256-CBC',
                 comment='Encryption algorithm used with this key'),
        sa.Column('key_purpose', sa.String(50), nullable=False, default='general',
                 comment='Purpose of the key (general, backup, emergency)'),
        sa.Column('created_by', sa.String(100), nullable=True,
                 comment='User/system that created this key'),
        sa.Column('notes', sa.Text(), nullable=True,
                 comment='Additional notes about key creation/rotation')
    )
    
    # Create indexes for encryption_keys
    op.create_index('idx_encryption_keys_version', 'encryption_keys', ['key_version'])
    op.create_index('idx_encryption_keys_is_active', 'encryption_keys', ['is_active'])
    op.create_index('idx_encryption_keys_created_at', 'encryption_keys', ['created_at'])
    op.create_index('idx_encryption_keys_algorithm', 'encryption_keys', ['algorithm'])
    
    # Create unique constraint for active keys (only one active key per version)
    op.create_index(
        'idx_encryption_keys_active_unique',
        'encryption_keys',
        ['key_version', 'is_active'],
        unique=True,
        postgresql_where=text('is_active = true')
    )
    
    # Create encryption_audit_log table for compliance tracking
    op.create_table(
        'encryption_audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key_version', sa.Integer(), nullable=True,
                 comment='Version of encryption key used'),
        sa.Column('operation', sa.String(50), nullable=False,
                 comment='Type of operation (encrypt, decrypt, rotate, migrate)'),
        sa.Column('table_name', sa.String(100), nullable=True,
                 comment='Database table involved in operation'),
        sa.Column('column_name', sa.String(100), nullable=True,
                 comment='Database column involved in operation'),
        sa.Column('user_id', sa.String(100), nullable=True,
                 comment='User ID associated with operation'),
        sa.Column('session_id', sa.String(100), nullable=True,
                 comment='Session ID for request tracking'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='When operation occurred'),
        sa.Column('field_type', sa.String(50), nullable=True,
                 comment='Type of field (email, tax_id, personal_data, etc.)'),
        sa.Column('success', sa.Boolean(), nullable=False, default=True,
                 comment='Whether operation completed successfully'),
        sa.Column('error_message', sa.Text(), nullable=True,
                 comment='Error message if operation failed'),
        sa.Column('ip_address', sa.String(45), nullable=True,
                 comment='IP address of client (for audit)'),
        sa.Column('user_agent', sa.Text(), nullable=True,
                 comment='User agent string (for audit)'),
        sa.Column('processing_time_ms', sa.Float(), nullable=True,
                 comment='Time taken for operation in milliseconds'),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True,
                 comment='Size of data processed in bytes')
    )
    
    # Create indexes for encryption_audit_log
    op.create_index('idx_encryption_audit_log_timestamp', 'encryption_audit_log', ['timestamp'])
    op.create_index('idx_encryption_audit_log_operation', 'encryption_audit_log', ['operation'])
    op.create_index('idx_encryption_audit_log_table_name', 'encryption_audit_log', ['table_name'])
    op.create_index('idx_encryption_audit_log_user_id', 'encryption_audit_log', ['user_id'])
    op.create_index('idx_encryption_audit_log_key_version', 'encryption_audit_log', ['key_version'])
    op.create_index('idx_encryption_audit_log_success', 'encryption_audit_log', ['success'])
    op.create_index('idx_encryption_audit_log_field_type', 'encryption_audit_log', ['field_type'])
    
    # Create compound indexes for common queries
    op.create_index(
        'idx_encryption_audit_log_user_timestamp',
        'encryption_audit_log',
        ['user_id', 'timestamp']
    )
    op.create_index(
        'idx_encryption_audit_log_table_operation',
        'encryption_audit_log',
        ['table_name', 'operation']
    )
    op.create_index(
        'idx_encryption_audit_log_timestamp_success',
        'encryption_audit_log',
        ['timestamp', 'success']
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_encryption_audit_log_key_version',
        'encryption_audit_log',
        'encryption_keys',
        ['key_version'],
        ['key_version'],
        ondelete='SET NULL'
    )
    
    # Create encryption_config table for system configuration
    op.create_table(
        'encryption_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('config_key', sa.String(100), unique=True, nullable=False,
                 comment='Configuration parameter name'),
        sa.Column('config_value', sa.Text(), nullable=True,
                 comment='Configuration parameter value'),
        sa.Column('config_type', sa.String(50), nullable=False, default='string',
                 comment='Type of configuration value (string, integer, boolean, json)'),
        sa.Column('description', sa.Text(), nullable=True,
                 comment='Description of configuration parameter'),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, default=False,
                 comment='Whether this config contains sensitive data'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='Last update timestamp'),
        sa.Column('updated_by', sa.String(100), nullable=True,
                 comment='User who last updated this config')
    )
    
    # Create indexes for encryption_config
    op.create_index('idx_encryption_config_key', 'encryption_config', ['config_key'])
    op.create_index('idx_encryption_config_type', 'encryption_config', ['config_type'])
    op.create_index('idx_encryption_config_sensitive', 'encryption_config', ['is_sensitive'])
    
    # Create encrypted_field_registry table to track which fields are encrypted
    op.create_table(
        'encrypted_field_registry',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('table_name', sa.String(100), nullable=False,
                 comment='Name of the database table'),
        sa.Column('column_name', sa.String(100), nullable=False,
                 comment='Name of the encrypted column'),
        sa.Column('field_type', sa.String(50), nullable=False,
                 comment='Type of field (email, tax_id, personal_data, etc.)'),
        sa.Column('encryption_enabled', sa.Boolean(), nullable=False, default=True,
                 comment='Whether encryption is currently enabled for this field'),
        sa.Column('key_version', sa.Integer(), nullable=True,
                 comment='Key version used for this field'),
        sa.Column('migration_status', sa.String(50), nullable=False, default='pending',
                 comment='Migration status (pending, in_progress, completed, failed)'),
        sa.Column('total_records', sa.Integer(), nullable=True,
                 comment='Total number of records in table'),
        sa.Column('encrypted_records', sa.Integer(), nullable=False, default=0,
                 comment='Number of records successfully encrypted'),
        sa.Column('failed_records', sa.Integer(), nullable=False, default=0,
                 comment='Number of records that failed encryption'),
        sa.Column('last_migration_at', sa.DateTime(timezone=True), nullable=True,
                 comment='Last migration attempt timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='Registry entry creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                 server_default=text('NOW()'), comment='Last update timestamp')
    )
    
    # Create unique constraint for table/column combination
    op.create_index(
        'idx_encrypted_field_registry_table_column_unique',
        'encrypted_field_registry',
        ['table_name', 'column_name'],
        unique=True
    )
    
    # Create indexes for encrypted_field_registry
    op.create_index('idx_encrypted_field_registry_table', 'encrypted_field_registry', ['table_name'])
    op.create_index('idx_encrypted_field_registry_field_type', 'encrypted_field_registry', ['field_type'])
    op.create_index('idx_encrypted_field_registry_migration_status', 'encrypted_field_registry', ['migration_status'])
    op.create_index('idx_encrypted_field_registry_encryption_enabled', 'encrypted_field_registry', ['encryption_enabled'])
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_encrypted_field_registry_key_version',
        'encrypted_field_registry',
        'encryption_keys',
        ['key_version'],
        ['key_version'],
        ondelete='SET NULL'
    )
    
    # Create stored procedures for encryption operations
    
    # Function to log encryption operations
    op.execute("""
        CREATE OR REPLACE FUNCTION log_encryption_operation(
            p_key_version INTEGER,
            p_operation VARCHAR(50),
            p_table_name VARCHAR(100) DEFAULT NULL,
            p_column_name VARCHAR(100) DEFAULT NULL,
            p_user_id VARCHAR(100) DEFAULT NULL,
            p_session_id VARCHAR(100) DEFAULT NULL,
            p_field_type VARCHAR(50) DEFAULT NULL,
            p_success BOOLEAN DEFAULT TRUE,
            p_error_message TEXT DEFAULT NULL,
            p_processing_time_ms FLOAT DEFAULT NULL,
            p_data_size_bytes INTEGER DEFAULT NULL
        ) RETURNS VOID AS $$
        BEGIN
            INSERT INTO encryption_audit_log (
                key_version, operation, table_name, column_name,
                user_id, session_id, field_type, success, error_message,
                processing_time_ms, data_size_bytes
            ) VALUES (
                p_key_version, p_operation, p_table_name, p_column_name,
                p_user_id, p_session_id, p_field_type, p_success, p_error_message,
                p_processing_time_ms, p_data_size_bytes
            );
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Function to get active encryption key version
    op.execute("""
        CREATE OR REPLACE FUNCTION get_active_key_version() 
        RETURNS INTEGER AS $$
        DECLARE
            active_version INTEGER;
        BEGIN
            SELECT key_version INTO active_version
            FROM encryption_keys
            WHERE is_active = TRUE
            ORDER BY key_version DESC
            LIMIT 1;
            
            IF active_version IS NULL THEN
                RAISE EXCEPTION 'No active encryption key found';
            END IF;
            
            RETURN active_version;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Function to validate encryption key
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_encryption_key(p_key_version INTEGER)
        RETURNS BOOLEAN AS $$
        DECLARE
            key_exists BOOLEAN;
        BEGIN
            SELECT EXISTS(
                SELECT 1 FROM encryption_keys 
                WHERE key_version = p_key_version
            ) INTO key_exists;
            
            RETURN key_exists;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Function to clean up old audit logs
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_encryption_audit_logs(retention_days INTEGER DEFAULT 730)
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM encryption_audit_log
            WHERE timestamp < NOW() - INTERVAL '1 day' * retention_days;
            
            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            
            -- Log the cleanup operation
            PERFORM log_encryption_operation(
                NULL, 'cleanup_audit_logs', 'encryption_audit_log', NULL,
                'system', NULL, NULL, TRUE, 
                'Deleted ' || deleted_count || ' old audit log entries'
            );
            
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create triggers for automatic timestamp updates
    op.execute("""
        CREATE OR REPLACE FUNCTION update_encryption_config_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER update_encryption_config_updated_at_trigger
        BEFORE UPDATE ON encryption_config
        FOR EACH ROW
        EXECUTE FUNCTION update_encryption_config_updated_at();
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION update_encrypted_field_registry_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER update_encrypted_field_registry_updated_at_trigger
        BEFORE UPDATE ON encrypted_field_registry
        FOR EACH ROW
        EXECUTE FUNCTION update_encrypted_field_registry_updated_at();
    """)
    
    # Insert default encryption configuration
    op.execute("""
        INSERT INTO encryption_config (config_key, config_value, config_type, description) VALUES
        ('encryption_enabled', 'true', 'boolean', 'Whether database encryption is enabled'),
        ('default_algorithm', 'AES-256-CBC', 'string', 'Default encryption algorithm'),
        ('key_rotation_interval_days', '90', 'integer', 'Number of days between key rotations'),
        ('audit_log_retention_days', '730', 'integer', 'Number of days to retain audit logs (2 years)'),
        ('max_key_versions', '10', 'integer', 'Maximum number of key versions to keep'),
        ('performance_monitoring_enabled', 'true', 'boolean', 'Whether to monitor encryption performance'),
        ('compliance_mode', 'italian_gdpr', 'string', 'Compliance mode (italian_gdpr, eu_gdpr, custom)'),
        ('emergency_decryption_enabled', 'false', 'boolean', 'Whether emergency decryption procedures are enabled'),
        ('backup_encryption_enabled', 'true', 'boolean', 'Whether database backups should be encrypted'),
        ('field_level_audit_enabled', 'true', 'boolean', 'Whether to audit individual field operations')
    """)
    
    # Register encrypted fields for Italian tax/financial data
    op.execute("""
        INSERT INTO encrypted_field_registry (
            table_name, column_name, field_type, encryption_enabled, migration_status
        ) VALUES
        ('users', 'email', 'email', true, 'pending'),
        ('users', 'phone', 'phone', true, 'pending'),
        ('users', 'tax_id', 'tax_id', true, 'pending'),
        ('query_logs', 'query', 'query', true, 'pending'),
        ('faq_usage_logs', 'response_variation', 'personal_data', true, 'pending'),
        ('faq_usage_logs', 'comments', 'personal_data', true, 'pending'),
        ('subscription_data', 'stripe_customer_id', 'financial_data', true, 'pending'),
        ('subscription_data', 'invoice_data', 'financial_data', true, 'pending'),
        ('payment_logs', 'customer_details', 'financial_data', true, 'pending'),
        ('document_processing_log', 'error_details', 'personal_data', true, 'pending')
    """)
    
    # Create view for encryption status monitoring
    op.execute("""
        CREATE VIEW encryption_status_view AS
        SELECT 
            r.table_name,
            r.column_name,
            r.field_type,
            r.encryption_enabled,
            r.migration_status,
            r.total_records,
            r.encrypted_records,
            r.failed_records,
            CASE 
                WHEN r.total_records > 0 THEN 
                    ROUND((r.encrypted_records::DECIMAL / r.total_records::DECIMAL) * 100, 2)
                ELSE 0 
            END AS encryption_percentage,
            r.last_migration_at,
            k.algorithm,
            k.is_active as key_active
        FROM encrypted_field_registry r
        LEFT JOIN encryption_keys k ON r.key_version = k.key_version
        ORDER BY r.table_name, r.column_name;
    """)
    
    # Create view for audit log summary
    op.execute("""
        CREATE VIEW encryption_audit_summary_view AS
        SELECT 
            DATE(timestamp) as audit_date,
            operation,
            table_name,
            field_type,
            COUNT(*) as operation_count,
            COUNT(*) FILTER (WHERE success = true) as successful_operations,
            COUNT(*) FILTER (WHERE success = false) as failed_operations,
            AVG(processing_time_ms) as avg_processing_time_ms,
            SUM(data_size_bytes) as total_data_size_bytes
        FROM encryption_audit_log
        WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY DATE(timestamp), operation, table_name, field_type
        ORDER BY audit_date DESC, operation;
    """)


def downgrade():
    """Remove database encryption infrastructure."""
    
    # Drop views
    op.execute("DROP VIEW IF EXISTS encryption_audit_summary_view;")
    op.execute("DROP VIEW IF EXISTS encryption_status_view;")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_encrypted_field_registry_updated_at_trigger ON encrypted_field_registry;")
    op.execute("DROP TRIGGER IF EXISTS update_encryption_config_updated_at_trigger ON encryption_config;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_encrypted_field_registry_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS update_encryption_config_updated_at();")
    op.execute("DROP FUNCTION IF EXISTS cleanup_encryption_audit_logs(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS validate_encryption_key(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS get_active_key_version();")
    op.execute("DROP FUNCTION IF EXISTS log_encryption_operation(INTEGER, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, VARCHAR, BOOLEAN, TEXT, FLOAT, INTEGER);")
    
    # Drop tables (foreign key constraints will be dropped automatically)
    op.drop_table('encrypted_field_registry')
    op.drop_table('encryption_config')
    op.drop_table('encryption_audit_log')
    op.drop_table('encryption_keys')
    
    # Note: We don't drop the pgcrypto extension as it might be used by other parts of the system