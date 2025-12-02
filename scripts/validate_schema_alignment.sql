-- Schema Alignment Validation Script
-- Run this to verify database schema matches expectations
-- Author: Database Designer (Primo)
-- Date: 2025-11-28

\echo '============================================'
\echo 'PratikoAI Schema Alignment Validation'
\echo '============================================'
\echo ''

-- ==========================================
-- 1. Verify User Table Schema
-- ==========================================
\echo '1. USER TABLE VALIDATION'
\echo '   Checking user.id is INTEGER...'
SELECT
    CASE
        WHEN data_type = 'integer' THEN '   ✅ PASS: user.id is INTEGER'
        ELSE '   ❌ FAIL: user.id is ' || data_type || ' (expected INTEGER)'
    END as validation
FROM information_schema.columns
WHERE table_name = 'user' AND column_name = 'id' AND table_schema = 'public';

\echo ''

-- ==========================================
-- 2. Verify All User FK Columns are INTEGER
-- ==========================================
\echo '2. USER FK COLUMN TYPE VALIDATION'
\echo '   Checking all user_id foreign keys are INTEGER...'
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    CASE
        WHEN c.data_type = 'integer' AND fk.constraint_name IS NOT NULL THEN '✅ CORRECT'
        WHEN c.data_type = 'character varying' AND fk.constraint_name IS NULL THEN '⚠️  VARCHAR (no FK - legacy)'
        WHEN c.data_type = 'integer' AND fk.constraint_name IS NULL THEN '⚠️  INTEGER but no FK'
        ELSE '❌ WRONG TYPE'
    END as status
FROM information_schema.columns c
LEFT JOIN (
    SELECT tc.table_name, kcu.column_name, tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
WHERE c.column_name IN ('user_id', 'approved_by')
    AND c.table_schema = 'public'
ORDER BY
    CASE WHEN c.data_type = 'integer' THEN 1 ELSE 2 END,
    c.table_name;

\echo ''

-- ==========================================
-- 3. Count Tables by Category
-- ==========================================
\echo '3. TABLE INVENTORY'
SELECT
    '   Total tables' as category,
    COUNT(*) as count
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT
    '   Tables with user_id FK',
    COUNT(DISTINCT tc.table_name)
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND EXISTS (
        SELECT 1 FROM information_schema.key_column_usage kcu
        WHERE kcu.constraint_name = tc.constraint_name
            AND kcu.column_name IN ('user_id', 'approved_by')
    );

\echo ''

-- ==========================================
-- 4. Check for Orphaned Records (FK Integrity)
-- ==========================================
\echo '4. REFERENTIAL INTEGRITY CHECK'
\echo '   Checking for orphaned user_id records...'

-- Expert Profiles
SELECT
    'expert_profiles' as table_name,
    COUNT(*) as orphaned_records
FROM expert_profiles
WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
-- Subscriptions
SELECT 'subscriptions', COUNT(*)
FROM subscriptions
WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
-- Expert FAQ Candidates
SELECT 'expert_faq_candidates', COUNT(*)
FROM expert_faq_candidates
WHERE approved_by IS NOT NULL AND approved_by NOT IN (SELECT id FROM "user")
UNION ALL
-- Documents
SELECT 'documents', COUNT(*)
FROM documents
WHERE user_id NOT IN (SELECT id FROM "user")
UNION ALL
-- Customers
SELECT 'customers', COUNT(*)
FROM customers
WHERE user_id NOT IN (SELECT id FROM "user");

\echo ''
\echo '   Expected result: 0 orphaned records for all tables'
\echo ''

-- ==========================================
-- 5. Verify Alembic Migration Status
-- ==========================================
\echo '5. ALEMBIC MIGRATION STATUS'
SELECT
    '   Current migration: ' || version_num as status
FROM alembic_version;

\echo ''

-- ==========================================
-- 6. Check for Missing Base Model Tables
-- ==========================================
\echo '6. MISSING BASE MODEL TABLES'
\echo '   Checking for tables that should exist based on Base models...'

WITH expected_tables AS (
    SELECT unnest(ARRAY[
        'regione', 'comune', 'regional_tax_rates', 'comunal_tax_rates',
        'ccnl_sectors', 'ccnl_agreements', 'job_levels', 'salary_tables',
        'working_hours', 'overtime_rules', 'leave_entitlements', 'notice_periods',
        'special_allowances', 'ccnl_database', 'ccnl_versions', 'ccnl_update_events',
        'ccnl_change_logs', 'ccnl_monitoring_metrics', 'prompt_templates',
        'failure_patterns', 'system_improvements', 'quality_metrics',
        'expert_validations', 'query_clusters', 'faq_candidates', 'generated_faqs',
        'rss_faq_impact', 'faq_generation_jobs', 'subscription_plans',
        'subscription_plan_changes', 'data_export_requests', 'export_audit_logs',
        'query_history', 'faq_interactions', 'knowledge_base_searches',
        'electronic_invoices'
    ]) as table_name
)
SELECT
    et.table_name,
    CASE
        WHEN t.table_name IS NULL THEN '❌ MISSING'
        ELSE '✅ EXISTS'
    END as status
FROM expected_tables et
LEFT JOIN information_schema.tables t
    ON et.table_name = t.table_name AND t.table_schema = 'public'
ORDER BY status DESC, et.table_name;

\echo ''

-- ==========================================
-- 7. Summary Statistics
-- ==========================================
\echo '7. SUMMARY STATISTICS'
SELECT
    'INTEGER user_id with FK' as category,
    COUNT(*) as count
FROM information_schema.columns c
JOIN (
    SELECT tc.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
WHERE c.column_name IN ('user_id', 'approved_by')
    AND c.data_type = 'integer'
    AND c.table_schema = 'public'
UNION ALL
SELECT
    'VARCHAR user_id (no FK)',
    COUNT(*)
FROM information_schema.columns c
LEFT JOIN (
    SELECT tc.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
WHERE c.column_name = 'user_id'
    AND c.data_type = 'character varying'
    AND c.table_schema = 'public'
    AND fk.column_name IS NULL;

\echo ''
\echo '============================================'
\echo 'VALIDATION COMPLETE'
\echo '============================================'
\echo ''
\echo 'Expected Results:'
\echo '  - user.id: INTEGER ✅'
\echo '  - 11 INTEGER user_id columns with FK ✅'
\echo '  - 9 VARCHAR user_id columns without FK ⚠️'
\echo '  - 0 orphaned records ✅'
\echo '  - 36 missing Base model tables ❌'
\echo ''
\echo 'Next Steps:'
\echo '  1. Fix UUID→Integer code mismatches (3 files)'
\echo '  2. Decide on missing Base model tables'
\echo '  3. Proceed with SQLModel migration'
\echo ''
