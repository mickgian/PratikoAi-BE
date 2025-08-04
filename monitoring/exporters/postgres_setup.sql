-- PostgreSQL monitoring user setup for PratikoAI
-- This script creates a read-only monitoring user for the postgres_exporter

-- Create monitoring user
CREATE USER postgres_exporter WITH PASSWORD 'monitoring_secret_2024';

-- Grant connection privileges
GRANT CONNECT ON DATABASE aifinance TO postgres_exporter;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO postgres_exporter;

-- Grant select on all current tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres_exporter;

-- Grant select on all future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO postgres_exporter;

-- Grant access to system catalogs and statistics
GRANT SELECT ON pg_stat_database TO postgres_exporter;
GRANT SELECT ON pg_stat_user_tables TO postgres_exporter;
GRANT SELECT ON pg_stat_user_indexes TO postgres_exporter;
GRANT SELECT ON pg_stat_activity TO postgres_exporter;
GRANT SELECT ON pg_stat_replication TO postgres_exporter;

-- Enable pg_stat_statements extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant access to pg_stat_statements
GRANT SELECT ON pg_stat_statements TO postgres_exporter;

-- Create function for safe monitoring access
CREATE OR REPLACE FUNCTION postgres_exporter.pg_stat_activity_limited()
RETURNS TABLE (
    datid oid,
    datname name,
    pid integer,
    usesysid oid,
    usename name,
    application_name text,
    client_addr inet,
    client_hostname text,
    client_port integer,
    backend_start timestamp with time zone,
    xact_start timestamp with time zone,
    query_start timestamp with time zone,
    state_change timestamp with time zone,
    wait_event_type text,
    wait_event text,
    state text,
    backend_xid xid,
    backend_xmin xid,
    query text
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.datid, a.datname, a.pid, a.usesysid, a.usename,
        a.application_name, a.client_addr, a.client_hostname,
        a.client_port, a.backend_start, a.xact_start,
        a.query_start, a.state_change, a.wait_event_type,
        a.wait_event, a.state, a.backend_xid, a.backend_xmin,
        CASE 
            WHEN a.usename = 'postgres_exporter' THEN a.query
            ELSE '<query hidden>'
        END as query
    FROM pg_stat_activity a;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on the function
GRANT EXECUTE ON FUNCTION postgres_exporter.pg_stat_activity_limited() TO postgres_exporter;

-- Create schema for monitoring functions
CREATE SCHEMA IF NOT EXISTS postgres_exporter;
GRANT USAGE ON SCHEMA postgres_exporter TO postgres_exporter;

-- Verify the setup
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL monitoring user setup completed successfully';
    RAISE NOTICE 'User: postgres_exporter';
    RAISE NOTICE 'Permissions: Read-only access to all tables and system statistics';
    RAISE NOTICE 'Extensions: pg_stat_statements enabled';
END $$;