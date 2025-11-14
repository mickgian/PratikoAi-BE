# pgvector Setup Guide

## Current Status

✅ **Completed**:
- Created Alembic migrations for pgvector enablement
- Created vector index migrations
- Created verification script
- Compiled pgvector v0.7.4 for PostgreSQL 16
- **Added pgvector to project dependencies** (`pyproject.toml`)
- **Installed and running in production**

## Dependency Management

### pyproject.toml

The `pgvector` Python package is now included in project dependencies:

```toml
dependencies = [
    # ... other dependencies ...
    # Vector database dependencies
    "pgvector>=0.2.0",
]
```

This ensures pgvector is installed during:
- **Local development**: `uv sync`
- **Docker builds**: `uv sync --all-groups` (via Dockerfile)
- **CI/CD pipelines**: `uv sync --all-groups`

### Pre-Commit Hook for Dependency Validation

A pre-commit hook validates that critical dependencies (including pgvector) are present in `pyproject.toml`:

**File**: `.pre-commit-config.yaml`
```yaml
# Check critical dependencies are present
- repo: local
  hooks:
    - id: check-critical-dependencies
      name: Check critical dependencies in pyproject.toml
      entry: python -c "import sys; from pathlib import Path; content = Path('pyproject.toml').read_text(); critical_deps = ['pgvector', 'asyncpg', 'feedparser', 'sentence-transformers']; missing = [dep for dep in critical_deps if dep not in content]; print(f'❌ Missing critical dependencies: {missing}') if missing else print('✅ All critical dependencies present'); sys.exit(1) if missing else sys.exit(0)"
      language: system
      pass_filenames: false
      files: ^pyproject.toml$
      always_run: false
```

**How It Works**:
- Runs automatically on every commit when `pyproject.toml` changes
- Validates presence of: `pgvector`, `asyncpg`, `feedparser`, `sentence-transformers`
- Blocks commit if any critical dependency is missing
- Prevents repeat of missing dependency issues (like the pgvector Docker error)

**Testing the Hook**:
```bash
# Test locally
python -c "import sys; from pathlib import Path; content = Path('pyproject.toml').read_text(); critical_deps = ['pgvector', 'asyncpg', 'feedparser', 'sentence-transformers']; missing = [dep for dep in critical_deps if dep not in content]; print(f'❌ Missing critical dependencies: {missing}') if missing else print('✅ All critical dependencies present'); sys.exit(1) if missing else sys.exit(0)"

# Expected output:
# ✅ All critical dependencies present
```

## Step-by-Step Installation

### 1. Install pgvector Extension

The extension has been compiled in `/tmp/pgvector`. Complete the installation:

```bash
cd /tmp/pgvector
export PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
sudo make install
```

You'll be prompted for your password to install the extension files.

### 2. Run Alembic Migrations

After installing pgvector, run the migrations:

```bash
cd /Users/micky/PycharmProjects/PratikoAi-BE
source scripts/set_env.sh development
DATABASE_URL=$POSTGRES_URL alembic upgrade head
```

This will:
- Enable the pgvector extension in your database
- Add embedding columns to knowledge_items and knowledge_chunks
- Create ivfflat indexes for vector similarity search
- Run VACUUM ANALYZE for planner statistics

### 3. Verify Installation

Run the verification script to confirm everything is working:

```bash
source scripts/set_env.sh development
python scripts/diag/verify_pgvector.py
```

Expected output:
```
✅ vector extension installed (version 0.7.4)
✅ knowledge_items.embedding (vector)
✅ knowledge_chunks.embedding (vector)
✅ knowledge_chunks.idx_kc_vec
✅ knowledge_items.idx_ki_vec
```

The EXPLAIN ANALYZE output should show:
- `Index Scan using idx_kc_vec` for vector queries
- `Bitmap Index Scan using idx_knowledge_items_search_vector` for FTS queries

### 4. Test End-to-End

Test the full ingestion and retrieval pipeline:

```bash
# Ingest 3 documents from RSS feed
python scripts/diag/ingest_smoke.py

# Test hybrid retrieval
python scripts/diag/retrieval_smoke.py
```

## Troubleshooting

### Extension Not Available

If you see "pgvector extension not available":
```sql
-- Check if extension files are in the right place
SELECT * FROM pg_available_extensions WHERE name='vector';
```

If empty, verify installation path:
```bash
pg_config --sharedir
# Should show: /opt/homebrew/opt/postgresql@16/share/postgresql@16
# Extension files should be in: .../extension/vector.control
```

### Index Not Being Used

If EXPLAIN shows Seq Scan instead of Index Scan:

```sql
-- Rebuild index
REINDEX INDEX CONCURRENTLY idx_kc_vec;

-- Update statistics
VACUUM ANALYZE knowledge_chunks;

-- Check if index exists
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'knowledge_chunks'
  AND indexname LIKE '%vec%';
```

### Old Migration Conflicts

If you get "Multiple head revisions" error:
```bash
# Check current state
alembic current

# Stamp both heads as applied
alembic stamp enable_pgvector_20251103
alembic stamp vector_indexes_20251103
```

## File Reference

### Created Files

**Migrations**:
- `alembic/versions/20251103_enable_pgvector.py` - Enable pgvector extension
- `alembic/versions/20251103_vector_indexes.py` - Create vector indexes

**Verification**:
- `scripts/diag/verify_pgvector.py` - Verify installation and index usage

### Migration Details

#### Migration 1: Enable pgvector
```python
# Checks if pgvector is available, enables if present
# Safe to re-run, will not fail if extension already exists
```

#### Migration 2: Vector Indexes
```python
# Creates ivfflat indexes on embedding columns
# Only runs if pgvector type exists
# Runs VACUUM ANALYZE for planner statistics
```

## Next Steps After Installation

1. **Run full ingestion**:
   ```bash
   python scripts/diag/ingest_smoke.py
   ```

2. **Test hybrid retrieval**:
   ```bash
   python scripts/diag/retrieval_smoke.py
   ```

3. **Monitor performance**:
   ```sql
   -- Check index usage
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
   FROM pg_stat_user_indexes
   WHERE indexname LIKE '%vec%';

   -- Check table sizes
   SELECT
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
   FROM pg_tables
   WHERE tablename IN ('knowledge_items', 'knowledge_chunks');
   ```

4. **Tune ivfflat parameters** (if needed for large datasets):
   ```sql
   -- Drop old index
   DROP INDEX CONCURRENTLY idx_kc_vec;

   -- Recreate with adjusted lists parameter
   -- Rule of thumb: lists = sqrt(row_count)
   CREATE INDEX idx_kc_vec
   ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 200);  -- Adjust based on row count
   ```

## Architecture Notes

### Hybrid Retrieval Flow

1. **Query arrives** → Generate embedding
2. **FTS Search** → `ts_rank_cd(search_vector, query)`
3. **Vector Search** → `embedding <-> query_embedding`
4. **Recency Boost** → `EXP(-(now - kb_epoch) / days)`
5. **Combine Scores** → `0.4*FTS + 0.4*Vector + 0.2*Recency`
6. **Return Top K** → Ordered by combined_score

### Index Strategy

- **FTS**: GIN index on `search_vector` (already exists)
- **Vector**: ivfflat index on `embedding` (new)
- **Recency**: B-tree index on `kb_epoch DESC` (already exists)

### Why ivfflat?

- **Fast**: Approximate nearest neighbor (ANN) search
- **Scalable**: Works well up to millions of vectors
- **Trade-off**: 98-99% recall vs 100% recall (exact search)
- **Alternative**: HNSW (pgvector 0.5.0+) for higher recall

## References

- pgvector docs: https://github.com/pgvector/pgvector
- Hybrid RAG implementation: `HYBRID_RAG_IMPLEMENTATION.md`
- Ingestion code: `app/ingest/rss_normativa.py`
- Retrieval code: `app/retrieval/postgres_retriever.py`
