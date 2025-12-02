-- Verification SQL for Phase 2.2c GREEN - Expert FAQ Embeddings
-- Run this after deploying migration to verify embeddings are working

-- ============================================================================
-- 1. Verify table structure
-- ============================================================================
\echo '=== 1. Verifying expert_faq_candidates table structure ==='
\d+ expert_faq_candidates

-- Expected: question_embedding column of type vector(1536)

-- ============================================================================
-- 2. Verify indexes exist
-- ============================================================================
\echo ''
\echo '=== 2. Verifying IVFFlat index exists ==='
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'expert_faq_candidates'
  AND indexname LIKE '%embedding%';

-- Expected: idx_expert_faq_candidates_question_embedding_ivfflat
-- Expected: USING ivfflat (question_embedding vector_cosine_ops) WITH (lists = 50)

-- ============================================================================
-- 3. Check record counts
-- ============================================================================
\echo ''
\echo '=== 3. Checking FAQ candidate records ==='
SELECT
    COUNT(*) as total_faqs,
    COUNT(question_embedding) as faqs_with_embeddings,
    COUNT(*) FILTER (WHERE question_embedding IS NULL) as faqs_without_embeddings,
    ROUND(100.0 * COUNT(question_embedding) / COUNT(*), 2) as embedding_coverage_percent
FROM expert_faq_candidates;

-- Expected (new deployment): 0 total_faqs (no records yet)
-- Expected (after expert feedback): embedding_coverage_percent > 95%

-- ============================================================================
-- 4. Verify embedding dimensions (for records that have embeddings)
-- ============================================================================
\echo ''
\echo '=== 4. Verifying embedding dimensions (if records exist) ==='
SELECT
    id,
    LEFT(question, 50) as question_preview,
    array_length(question_embedding::float[], 1) as embedding_dimensions,
    source,
    approval_status,
    created_at
FROM expert_faq_candidates
WHERE question_embedding IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;

-- Expected: embedding_dimensions = 1536 for all records

-- ============================================================================
-- 5. Check for records missing embeddings (need backfill)
-- ============================================================================
\echo ''
\echo '=== 5. Identifying records needing embedding backfill ==='
SELECT
    COUNT(*) as needs_backfill,
    ARRAY_AGG(id) as faq_ids
FROM expert_faq_candidates
WHERE question_embedding IS NULL;

-- Expected (optimal): needs_backfill = 0
-- If > 0: Run backfill script to generate missing embeddings

-- ============================================================================
-- 6. Test semantic similarity search (if records exist)
-- ============================================================================
\echo ''
\echo '=== 6. Testing semantic similarity search (sample query) ==='
SELECT
    id,
    LEFT(question, 60) as question_preview,
    1 - (question_embedding <=> '[0.1, 0.2, ...]'::vector) as cosine_similarity,
    source,
    approval_status
FROM expert_faq_candidates
WHERE question_embedding IS NOT NULL
ORDER BY question_embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;

-- Note: Replace '[0.1, 0.2, ...]'::vector with actual query embedding to test
-- Expected: Results ordered by cosine similarity (descending)

-- ============================================================================
-- 7. Index statistics (check if index is being used)
-- ============================================================================
\echo ''
\echo '=== 7. Checking index usage statistics ==='
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'expert_faq_candidates'
  AND indexname LIKE '%embedding%';

-- Expected (after queries): idx_scan > 0 (index is being used)

-- ============================================================================
-- 8. Recent FAQ candidates with embedding status
-- ============================================================================
\echo ''
\echo '=== 8. Recent FAQ candidates with embedding status ==='
SELECT
    id,
    LEFT(question, 50) as question,
    CASE
        WHEN question_embedding IS NOT NULL THEN '✅ Has embedding'
        ELSE '❌ Missing embedding'
    END as embedding_status,
    array_length(question_embedding::float[], 1) as dimensions,
    source,
    expert_trust_score,
    approval_status,
    created_at
FROM expert_faq_candidates
ORDER BY created_at DESC
LIMIT 20;

-- Expected: All recent records should have '✅ Has embedding'
-- Expected: dimensions = 1536 for all records with embeddings

-- ============================================================================
-- VERIFICATION SUMMARY
-- ============================================================================
\echo ''
\echo '=== VERIFICATION SUMMARY ==='
\echo '✅ Table structure: Check \d+ output above for question_embedding column'
\echo '✅ Index exists: Check pg_indexes output for IVFFlat index'
\echo '✅ Embedding coverage: Should be >95% (ideally 100%)'
\echo '✅ Embedding dimensions: Should be 1536 for all records'
\echo '✅ Missing embeddings: Identify records needing backfill'
\echo '✅ Index usage: Check pg_stat_user_indexes after running queries'
\echo ''
\echo 'If any checks fail, review deployment logs and check Step 127 embedding generation.'
