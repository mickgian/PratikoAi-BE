-- ============================================================================
-- MIGRATION PREVIEW: 20251124_add_generated_faq_id
-- ============================================================================
-- This file shows the exact SQL commands that will be executed
-- when applying the migration: alembic upgrade head
-- ============================================================================

-- ============================================================================
-- UPGRADE (Apply Migration)
-- ============================================================================

-- Step 1: Add generated_faq_id column to expert_feedback table
ALTER TABLE expert_feedback
ADD COLUMN generated_faq_id VARCHAR(100) NULL;

-- Step 2: Create foreign key constraint
ALTER TABLE expert_feedback
ADD CONSTRAINT fk_expert_feedback_generated_faq_id
    FOREIGN KEY (generated_faq_id)
    REFERENCES faq_entries(id)
    ON DELETE SET NULL;

-- Step 3: Create index for performance
CREATE INDEX idx_expert_feedback_generated_faq_id
ON expert_feedback(generated_faq_id);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column exists
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'expert_feedback'
  AND column_name = 'generated_faq_id';

-- Expected result:
-- column_name       | data_type         | is_nullable | column_default
-- ----------------- | ----------------- | ----------- | --------------
-- generated_faq_id  | character varying | YES         | NULL

-- Verify foreign key constraint
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = 'expert_feedback'
  AND kcu.column_name = 'generated_faq_id';

-- Expected result:
-- constraint_name                        | table_name       | column_name       | foreign_table_name | foreign_column_name | delete_rule
-- -------------------------------------- | ---------------- | ----------------- | ------------------ | ------------------- | -----------
-- fk_expert_feedback_generated_faq_id    | expert_feedback  | generated_faq_id  | faq_entries        | id                  | SET NULL

-- Verify index exists
SELECT
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE tablename = 'expert_feedback'
  AND indexname = 'idx_expert_feedback_generated_faq_id';

-- Expected result:
-- indexname                              | tablename       | indexdef
-- -------------------------------------- | --------------- | --------
-- idx_expert_feedback_generated_faq_id   | expert_feedback | CREATE INDEX idx_expert_feedback_generated_faq_id ON expert_feedback USING btree (generated_faq_id)

-- ============================================================================
-- DOWNGRADE (Rollback Migration)
-- ============================================================================

-- Step 1: Drop index
DROP INDEX idx_expert_feedback_generated_faq_id;

-- Step 2: Drop foreign key constraint
ALTER TABLE expert_feedback
DROP CONSTRAINT fk_expert_feedback_generated_faq_id;

-- Step 3: Drop column
ALTER TABLE expert_feedback
DROP COLUMN generated_faq_id;

-- ============================================================================
-- SAMPLE USAGE QUERIES
-- ============================================================================

-- Insert feedback with NULL generated_faq_id (default case)
INSERT INTO expert_feedback (
    id, query_id, expert_id, feedback_type, category,
    query_text, original_answer, time_spent_seconds,
    generated_faq_id  -- NULL by default
)
VALUES (
    gen_random_uuid(),
    gen_random_uuid(),
    (SELECT id FROM expert_profiles LIMIT 1),
    'incomplete',
    'calcolo_sbagliato',
    'Come calcolo IVA?',
    'L''IVA si calcola...',
    120,
    NULL  -- No FAQ generated
);

-- Insert feedback with generated_faq_id (FAQ was created)
INSERT INTO expert_feedback (
    id, query_id, expert_id, feedback_type, category,
    query_text, original_answer, time_spent_seconds,
    generated_faq_id
)
VALUES (
    gen_random_uuid(),
    gen_random_uuid(),
    (SELECT id FROM expert_profiles LIMIT 1),
    'correct',
    NULL,
    'Come calcolo la ritenuta d''acconto?',
    'La ritenuta d''acconto è...',
    180,
    (SELECT id FROM faq_entries WHERE category = 'ritenute' LIMIT 1)  -- Link to FAQ
);

-- Query feedback with generated FAQs
SELECT
    ef.id,
    ef.query_text,
    ef.feedback_type,
    ef.generated_faq_id,
    fe.question AS faq_question,
    fe.category AS faq_category
FROM expert_feedback ef
LEFT JOIN faq_entries fe ON ef.generated_faq_id = fe.id
WHERE ef.generated_faq_id IS NOT NULL
ORDER BY ef.created_at DESC;

-- Count FAQs generated per expert
SELECT
    ep.professional_registration_number,
    ep.organization,
    COUNT(ef.generated_faq_id) AS faqs_generated,
    COUNT(*) AS total_feedback,
    ROUND(
        COUNT(ef.generated_faq_id)::numeric / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS faq_generation_rate_pct
FROM expert_feedback ef
JOIN expert_profiles ep ON ef.expert_id = ep.id
WHERE ef.feedback_type = 'correct'
GROUP BY ep.id, ep.professional_registration_number, ep.organization
ORDER BY faqs_generated DESC;

-- ============================================================================
-- PERFORMANCE MONITORING
-- ============================================================================

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE indexname = 'idx_expert_feedback_generated_faq_id';

-- Check foreign key validation cost
EXPLAIN ANALYZE
SELECT ef.*, fe.question
FROM expert_feedback ef
LEFT JOIN faq_entries fe ON ef.generated_faq_id = fe.id
WHERE ef.generated_faq_id IS NOT NULL;

-- ============================================================================
-- CLEANUP (FOR TESTING ONLY - DO NOT RUN IN PRODUCTION)
-- ============================================================================

-- Clear generated_faq_id values (testing only)
-- UPDATE expert_feedback SET generated_faq_id = NULL;

-- ============================================================================
