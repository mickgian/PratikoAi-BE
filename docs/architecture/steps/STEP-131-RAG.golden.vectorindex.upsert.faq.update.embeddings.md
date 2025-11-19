# RAG STEP 131 — VectorIndex.upsert_faq update embeddings (DEPRECATED)

**DEPRECATION NOTICE (2025-11-19):** This step has been removed as part of DEV-BE-68 (Pinecone removal).

**Status:** 🔴 DEPRECATED
**Type:** process
**Category:** golden
**Node ID:** `VectorReindex` (obsolete)

---

## Migration Information

**Why Deprecated:**
- Pinecone vector database replaced with PostgreSQL + pgvector (ADR-003)
- Vector embeddings are now **automatically managed** by pgvector database triggers
- No manual reindexing step required when FAQ entries are created/updated

**Migration Path:**
- Step 129 (PublishGolden) now writes directly to PostgreSQL
- pgvector triggers automatically generate and update embeddings for `faqs` table
- Embedding column: `faqs.embedding` (vector(1536) using text-embedding-3-small)
- Database function: `update_faq_embedding_trigger()` executes on INSERT/UPDATE

**Architecture Change:**
```
BEFORE (Pinecone):
Step 129 → Step 131 (manual Pinecone upsert) → Embeddings updated

AFTER (pgvector):
Step 129 → PostgreSQL INSERT/UPDATE → Automatic trigger → Embeddings updated
```

**Related Documentation:**
- [ADR-012: Remove Step 131 Vector Reindexing](../decisions.md#adr-012-remove-step-131-vector-reindexing)
- ADR-003: pgvector over Pinecone (`../decisions.md#adr-003-pgvector-over-pinecone`)
- DEV-BE-67: FAQ Embeddings Migration
- DEV-BE-68: Pinecone Removal
- Database schema: `docs/DATABASE_ARCHITECTURE.md`

---

## Historical Context

This step previously managed Pinecone vector index updates using `EmbeddingManager.update_pinecone_embeddings()`. It ran in parallel with Step 130 (InvalidateFAQCache) after Step 129 (PublishGolden). The step processed FAQ content and metadata to create/update vector embeddings in Pinecone's external index.

**Original Implementation:**
- **Location:** `app/orchestrators/golden.py:step_131__vector_reindex` (lines 1264-1410)
- **Function:** Async orchestrator wrapping EmbeddingManager.update_pinecone_embeddings
- **Behavior:** Updated Pinecone vector index with FAQ embeddings
- **Parallel execution:** Ran alongside Step 130 (InvalidateFAQCache)

**Code Reference:**
The original implementation is preserved (commented out) in `app/orchestrators/golden.py` lines 1259-1410 with deprecation notice.

---

## Reasons for Removal

1. **Cost Savings:** Pinecone: $70-200/month → pgvector: $0/month (included in PostgreSQL)
2. **Consistency:** Database triggers guarantee embeddings always match FAQ data (ACID transactions)
3. **Latency:** Eliminated external API call to Pinecone (~50-100ms saved per FAQ update)
4. **GDPR Compliance:** All data (including embeddings) now hosted in EU (Hetzner Germany)
5. **Simplicity:** Removed orchestration complexity, retry logic, and failure modes

---

## Rollback Plan (If Needed)

If pgvector triggers prove problematic:

1. Uncomment `app/orchestrators/golden.py:step_131__vector_reindex()` (lines 1264-1410)
2. Modify to call pgvector upsert instead of Pinecone
3. Disable database triggers to prevent duplicate updates
4. Restore imports in `app/orchestrators/__init__.py`
5. Update Mermaid diagrams to re-add S131 node

**Estimated effort:** 2-4 hours
**Risk:** Low (pgvector triggers tested in 69.5% test coverage suite)

---

**Deprecated:** 2025-11-19
**Replacement:** Automatic pgvector database triggers
**Last Active:** DEV-BE-68 merge date
