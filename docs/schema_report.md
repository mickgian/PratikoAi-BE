# PostgreSQL RAG Schema Report

**Generated:** 2025-11-03T10:11:28.432068Z
**Database:** `POSTGRES_URL`

## PostgreSQL Extensions

| Extension | Default Version | Installed Version |
|-----------|----------------|-------------------|
| plpgsql | 1.0 | 1.0 |

### Extensions Analysis
- ⚠️ **Missing `pg_trgm`**: Useful for fuzzy text matching
- ⚠️ **Missing `pgvector`**: Required for vector embeddings/semantic search

## RAG/Knowledge Tables

Found **11** tables:

- `cassazione_decisions`
- `document_analyses`
- `document_collections`
- `document_processing_jobs`
- `document_processing_log`
- `documents`
- `feed_status`
- `knowledge_chunks` ✨ **NEW** - Document chunks with FTS + vector embeddings
- `knowledge_feedback`
- `knowledge_items`
- `regulatory_documents`

## Table Sizes & Row Counts

| Table | Total Size | Table Size | Indexes Size | Rows |
|-------|------------|------------|--------------|------|
| knowledge_items | 9136 kB | 40 kB | 176 kB | 27 |
| document_processing_log | 216 kB | 56 kB | 112 kB | 62 |
| feed_status | 128 kB | 8192 bytes | 112 kB | 5 |
| regulatory_documents | 104 kB | 0 bytes | 96 kB | 0 |
| documents | 72 kB | 0 bytes | 64 kB | 0 |
| knowledge_feedback | 56 kB | 0 bytes | 48 kB | 0 |
| document_processing_jobs | 48 kB | 0 bytes | 40 kB | 0 |
| document_collections | 48 kB | 0 bytes | 40 kB | 0 |
| document_analyses | 40 kB | 0 bytes | 32 kB | 0 |
| cassazione_decisions | 24 kB | 0 bytes | 16 kB | 0 |

## Table Details

### `cassazione_decisions`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| created_at | timestamp without time zone | ✗ |  |
| id | integer | ✗ | nextval('cassazione_decisions_id_seq'... |
| decision_id | character varying | ✗ |  |
| decision_number | integer | ✗ |  |
| decision_year | integer | ✗ |  |
| section | USER-DEFINED | ✗ |  |
| decision_type | USER-DEFINED | ✗ |  |
| decision_date | date | ✗ |  |
| publication_date | date | ✓ |  |
| filing_date | date | ✓ |  |
| title | character varying | ✗ |  |
| summary | text | ✓ |  |
| full_text | text | ✓ |  |
| legal_principle | text | ✓ |  |
| keywords | json | ✓ |  |
| legal_areas | json | ✓ |  |
| related_sectors | json | ✓ |  |
| precedent_value | character varying | ✗ |  |
| cited_decisions | json | ✓ |  |
| citing_decisions | json | ✓ |  |
| related_laws | json | ✓ |  |
| related_ccnl | json | ✓ |  |
| appellant | character varying | ✓ |  |
| respondent | character varying | ✓ |  |
| case_subject | text | ✓ |  |
| court_of_origin | character varying | ✓ |  |
| outcome | character varying | ✓ |  |
| damages_awarded | character varying | ✓ |  |
| source_url | character varying | ✓ |  |
| confidence_score | integer | ✗ |  |

#### Indexes

- **cassazione_decisions_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX cassazione_decisions_pkey ON public.cassazione_decisions USING btree (id)
  ```
- **ix_cassazione_decisions_decision_id** (BTREE)
  ```sql
  CREATE UNIQUE INDEX ix_cassazione_decisions_decision_id ON public.cassazione_decisions USING btree (decision_id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

*No triggers*

---

### `document_analyses`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| created_at | timestamp without time zone | ✗ |  |
| id | uuid | ✗ |  |
| document_id | uuid | ✗ |  |
| user_id | integer | ✗ |  |
| query | character varying | ✗ |  |
| analysis_type | character varying | ✗ |  |
| requested_at | timestamp without time zone | ✗ |  |
| completed_at | timestamp without time zone | ✓ |  |
| duration_seconds | integer | ✓ |  |
| analysis_result | jsonb | ✓ |  |
| ai_response | character varying | ✓ |  |
| confidence_score | integer | ✓ |  |
| context_used | jsonb | ✓ |  |
| llm_model | character varying | ✓ |  |
| cost | integer | ✓ |  |
| quality_score | integer | ✓ |  |
| validation_status | character varying | ✗ |  |
| expert_validated | boolean | ✗ |  |

#### Indexes

- **document_analyses_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX document_analyses_pkey ON public.document_analyses USING btree (id)
  ```
- **ix_document_analyses_document_id** (BTREE)
  ```sql
  CREATE INDEX ix_document_analyses_document_id ON public.document_analyses USING btree (document_id)
  ```
- **ix_document_analyses_id** (BTREE)
  ```sql
  CREATE INDEX ix_document_analyses_id ON public.document_analyses USING btree (id)
  ```
- **ix_document_analyses_user_id** (BTREE)
  ```sql
  CREATE INDEX ix_document_analyses_user_id ON public.document_analyses USING btree (user_id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **FK**: `document_id` → `documents.id`
- **PK**: `id`
- **FK**: `user_id` → `user.id`

#### Triggers

*No triggers*

---

### `document_collections`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | ✗ | nextval('document_collections_id_seq'... |
| name | character varying | ✗ |  |
| description | text | ✓ |  |
| source | character varying | ✗ |  |
| document_type | character varying | ✗ |  |
| document_count | integer | ✗ |  |
| total_content_length | integer | ✗ |  |
| earliest_document | timestamp with time zone | ✓ |  |
| latest_document | timestamp with time zone | ✓ |  |
| status | character varying | ✗ |  |
| created_at | timestamp with time zone | ✗ | now() |
| updated_at | timestamp with time zone | ✗ | now() |

#### Indexes

- **document_collections_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX document_collections_pkey ON public.document_collections USING btree (id)
  ```
- **idx_document_collections_created_at** (BTREE)
  ```sql
  CREATE INDEX idx_document_collections_created_at ON public.document_collections USING btree (created_at)
  ```
- **idx_document_collections_document_type** (BTREE)
  ```sql
  CREATE INDEX idx_document_collections_document_type ON public.document_collections USING btree (document_type)
  ```
- **idx_document_collections_source** (BTREE)
  ```sql
  CREATE INDEX idx_document_collections_source ON public.document_collections USING btree (source)
  ```
- **idx_document_collections_status** (BTREE)
  ```sql
  CREATE INDEX idx_document_collections_status ON public.document_collections USING btree (status)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

- **update_document_collections_updated_at_trigger**: BEFORE UPDATE
  - Action: `EXECUTE FUNCTION update_document_collections_updated_at()`

---

### `document_processing_jobs`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| created_at | timestamp without time zone | ✗ |  |
| id | uuid | ✗ |  |
| document_id | uuid | ✗ |  |
| job_type | character varying | ✗ |  |
| priority | integer | ✗ |  |
| status | character varying | ✗ |  |
| started_at | timestamp without time zone | ✓ |  |
| completed_at | timestamp without time zone | ✓ |  |
| worker_id | character varying | ✓ |  |
| attempts | integer | ✗ |  |
| max_attempts | integer | ✗ |  |
| result | jsonb | ✓ |  |
| error_message | character varying | ✓ |  |
| expires_at | timestamp without time zone | ✗ |  |

#### Indexes

- **document_processing_jobs_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX document_processing_jobs_pkey ON public.document_processing_jobs USING btree (id)
  ```
- **ix_document_processing_jobs_document_id** (BTREE)
  ```sql
  CREATE INDEX ix_document_processing_jobs_document_id ON public.document_processing_jobs USING btree (document_id)
  ```
- **ix_document_processing_jobs_expires_at** (BTREE)
  ```sql
  CREATE INDEX ix_document_processing_jobs_expires_at ON public.document_processing_jobs USING btree (expires_at)
  ```
- **ix_document_processing_jobs_id** (BTREE)
  ```sql
  CREATE INDEX ix_document_processing_jobs_id ON public.document_processing_jobs USING btree (id)
  ```
- **ix_document_processing_jobs_status** (BTREE)
  ```sql
  CREATE INDEX ix_document_processing_jobs_status ON public.document_processing_jobs USING btree (status)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **FK**: `document_id` → `documents.id`
- **PK**: `id`

#### Triggers

*No triggers*

---

### `document_processing_log`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | ✗ | nextval('document_processing_log_id_s... |
| document_id | character varying | ✓ |  |
| document_url | text | ✗ |  |
| operation | character varying | ✗ |  |
| status | character varying | ✗ |  |
| processing_time_ms | double precision | ✓ |  |
| content_length | integer | ✓ |  |
| error_message | text | ✓ |  |
| error_details | json | ✓ |  |
| triggered_by | character varying | ✗ |  |
| feed_url | text | ✓ |  |
| created_at | timestamp with time zone | ✗ | now() |

#### Indexes

- **document_processing_log_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX document_processing_log_pkey ON public.document_processing_log USING btree (id)
  ```
- **idx_document_processing_log_created_at** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_created_at ON public.document_processing_log USING btree (created_at)
  ```
- **idx_document_processing_log_document_id** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_document_id ON public.document_processing_log USING btree (document_id)
  ```
- **idx_document_processing_log_operation** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_operation ON public.document_processing_log USING btree (operation)
  ```
- **idx_document_processing_log_status** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_status ON public.document_processing_log USING btree (status)
  ```
- **idx_document_processing_log_status_date** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_status_date ON public.document_processing_log USING btree (status, created_at)
  ```
- **idx_document_processing_log_triggered_by** (BTREE)
  ```sql
  CREATE INDEX idx_document_processing_log_triggered_by ON public.document_processing_log USING btree (triggered_by)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

*No triggers*

#### Sample Data (3 rows)

```json
[
  {
    "id": 2,
    "document_id": null,
    "document_url": "https://www.agenziaentrate.gov.it/portale/documents/20143/9354005/provvedimento-del-31-ottobre-2025/ee343555-e60b-e78b-03ab-5ab834afcae8",
    "operation": "create",
    "status": "failed",
    "processing_time_ms": null,
    "content_length": null,
    "error_details": null,
    "triggered_by": "scheduler",
    "feed_url": "",
    "created_at": "2025-11-03 09:14:43.694968+01:00"
  },
  {
    "id": 3,
    "document_id": null,
    "document_url": "https://www.agenziaentrate.gov.it/portale/documents/20143/9354001/Risposta+n.+271_2025/f3371d12-2c16-178c-23a0-14bf7d82bc99",
    "operation": "create",
    "status": "processing",
    "processing_time_ms": null,
    "content_length": null,
    "error_message": null,
    "error_details": null,
    "triggered_by": "scheduler",
    "feed_url": "",
    "created_at": "2025-11-03 09:14:43.699331+01:00"
  },
  {
    "id": 4,
    "document_id": null,
    "document_url": "https://www.agenziaentrate.gov.it/portale/documents/d/guest/risoluzione-n-62_2025",
    "operation": "create",
    "status": "failed",
    "processing_time_ms": null,
    "content_length": null,
    "error_details": null,
    "triggered_by": "scheduler",
    "feed_url": "",
    "created_at": "2025-11-03 09:14:44.176863+01:00"
  }
]
```

---

### `documents`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| created_at | timestamp without time zone | ✗ |  |
| id | uuid | ✗ |  |
| user_id | integer | ✗ |  |
| filename | character varying | ✗ |  |
| original_filename | character varying | ✗ |  |
| file_type | character varying | ✗ |  |
| file_size | integer | ✗ |  |
| mime_type | character varying | ✗ |  |
| file_hash | character varying | ✗ |  |
| upload_timestamp | timestamp without time zone | ✗ |  |
| upload_ip | character varying | ✓ |  |
| processing_status | character varying | ✗ |  |
| processing_started_at | timestamp without time zone | ✓ |  |
| processing_completed_at | timestamp without time zone | ✓ |  |
| processing_duration_seconds | integer | ✓ |  |
| document_category | character varying | ✓ |  |
| document_confidence | integer | ✓ |  |
| extracted_text | character varying | ✓ |  |
| extracted_data | jsonb | ✓ |  |
| extracted_tables | jsonb | ✓ |  |
| processing_log | jsonb | ✓ |  |
| error_message | character varying | ✓ |  |
| warnings | jsonb | ✓ |  |
| virus_scan_status | character varying | ✗ |  |
| virus_scan_result | character varying | ✓ |  |
| is_sensitive_data | boolean | ✗ |  |
| expires_at | timestamp without time zone | ✗ |  |
| is_deleted | boolean | ✗ |  |
| deleted_at | timestamp without time zone | ✓ |  |
| analysis_count | integer | ✗ |  |
| last_analyzed_at | timestamp without time zone | ✓ |  |

#### Indexes

- **documents_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX documents_pkey ON public.documents USING btree (id)
  ```
- **ix_documents_expires_at** (BTREE)
  ```sql
  CREATE INDEX ix_documents_expires_at ON public.documents USING btree (expires_at)
  ```
- **ix_documents_file_hash** (BTREE)
  ```sql
  CREATE INDEX ix_documents_file_hash ON public.documents USING btree (file_hash)
  ```
- **ix_documents_id** (BTREE)
  ```sql
  CREATE INDEX ix_documents_id ON public.documents USING btree (id)
  ```
- **ix_documents_is_deleted** (BTREE)
  ```sql
  CREATE INDEX ix_documents_is_deleted ON public.documents USING btree (is_deleted)
  ```
- **ix_documents_processing_status** (BTREE)
  ```sql
  CREATE INDEX ix_documents_processing_status ON public.documents USING btree (processing_status)
  ```
- **ix_documents_upload_timestamp** (BTREE)
  ```sql
  CREATE INDEX ix_documents_upload_timestamp ON public.documents USING btree (upload_timestamp)
  ```
- **ix_documents_user_id** (BTREE)
  ```sql
  CREATE INDEX ix_documents_user_id ON public.documents USING btree (user_id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`
- **FK**: `user_id` → `user.id`

#### Triggers

*No triggers*

---

### `feed_status`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | ✗ | nextval('feed_status_id_seq'::regclass) |
| feed_url | text | ✗ |  |
| source | character varying | ✓ |  |
| feed_type | character varying | ✓ |  |
| status | character varying | ✗ |  |
| last_checked | timestamp with time zone | ✗ | now() |
| last_success | timestamp with time zone | ✓ |  |
| response_time_ms | double precision | ✓ |  |
| items_found | integer | ✓ |  |
| consecutive_errors | integer | ✗ |  |
| errors | integer | ✗ |  |
| last_error | text | ✓ |  |
| last_error_at | timestamp with time zone | ✓ |  |
| check_interval_minutes | integer | ✗ |  |
| enabled | boolean | ✗ |  |
| created_at | timestamp with time zone | ✗ | now() |
| updated_at | timestamp with time zone | ✗ | now() |

#### Indexes

- **feed_status_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX feed_status_pkey ON public.feed_status USING btree (id)
  ```
- **idx_feed_status_enabled** (BTREE)
  ```sql
  CREATE INDEX idx_feed_status_enabled ON public.feed_status USING btree (enabled)
  ```
- **idx_feed_status_errors** (BTREE)
  ```sql
  CREATE INDEX idx_feed_status_errors ON public.feed_status USING btree (consecutive_errors)
  ```
- **idx_feed_status_last_checked** (BTREE)
  ```sql
  CREATE INDEX idx_feed_status_last_checked ON public.feed_status USING btree (last_checked)
  ```
- **idx_feed_status_source** (BTREE)
  ```sql
  CREATE INDEX idx_feed_status_source ON public.feed_status USING btree (source)
  ```
- **idx_feed_status_status** (BTREE)
  ```sql
  CREATE INDEX idx_feed_status_status ON public.feed_status USING btree (status)
  ```
- **idx_feed_status_url_unique** (BTREE)
  ```sql
  CREATE UNIQUE INDEX idx_feed_status_url_unique ON public.feed_status USING btree (feed_url)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

- **update_feed_status_updated_at_trigger**: BEFORE UPDATE
  - Action: `EXECUTE FUNCTION update_feed_status_updated_at()`

#### Sample Data (3 rows)

```json
[
  {
    "id": 3,
    "feed_url": "https://www.inps.it/rss/circolari.xml",
    "source": "inps",
    "feed_type": "circolari",
    "status": "pending",
    "last_success": null,
    "response_time_ms": null,
    "items_found": null,
    "consecutive_errors": 0,
    "errors": 0,
    "last_error": null,
    "last_error_at": null,
    "check_interval_minutes": 240,
    "enabled": true,
    "created_at": "2025-10-31 19:02:21.691341+01:00",
    "updated_at": "2025-10-31 19:02:21.691341+01:00"
  },
  {
    "id": 4,
    "feed_url": "https://www.gazzettaufficiale.it/rss/serie_generale.xml",
    "source": "gazzetta_ufficiale",
    "feed_type": "serie_generale",
    "status": "pending",
    "last_success": null,
    "response_time_ms": null,
    "items_found": null,
    "consecutive_errors": 0,
    "errors": 0,
    "last_error": null,
    "last_error_at": null,
    "check_interval_minutes": 240,
    "enabled": true,
    "created_at": "2025-10-31 19:02:21.691341+01:00",
    "updated_at": "2025-10-31 19:02:21.691341+01:00"
  },
  {
    "id": 5,
    "feed_url": "https://www.governo.it/rss/decreti-legge.xml",
    "source": "governo",
    "feed_type": "decreti_legge",
    "status": "pending",
    "last_success": null,
    "response_time_ms": null,
    "items_found": null,
    "consecutive_errors": 0,
    "errors": 0,
    "last_error": null,
    "last_error_at": null,
    "check_interval_minutes": 240,
    "enabled": true,
    "created_at": "2025-10-31 19:02:21.691341+01:00",
    "updated_at": "2025-10-31 19:02:21.691341+01:00"
  }
]
```

---

### `knowledge_feedback`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | ✗ | nextval('knowledge_feedback_id_seq'::... |
| knowledge_item_id | integer | ✗ |  |
| user_id | character varying | ✗ |  |
| session_id | character varying | ✗ |  |
| rating | integer | ✗ |  |
| feedback_text | text | ✓ |  |
| feedback_type | character varying | ✗ |  |
| search_query | character varying | ✓ |  |
| context | json | ✓ |  |
| created_at | timestamp without time zone | ✗ |  |
| ip_address | character varying | ✓ |  |
| user_agent | character varying | ✓ |  |

#### Indexes

- **idx_feedback_created** (BTREE)
  ```sql
  CREATE INDEX idx_feedback_created ON public.knowledge_feedback USING btree (created_at)
  ```
- **idx_feedback_knowledge_item** (BTREE)
  ```sql
  CREATE INDEX idx_feedback_knowledge_item ON public.knowledge_feedback USING btree (knowledge_item_id)
  ```
- **idx_feedback_rating** (BTREE)
  ```sql
  CREATE INDEX idx_feedback_rating ON public.knowledge_feedback USING btree (rating)
  ```
- **idx_feedback_type** (BTREE)
  ```sql
  CREATE INDEX idx_feedback_type ON public.knowledge_feedback USING btree (feedback_type)
  ```
- **idx_feedback_user** (BTREE)
  ```sql
  CREATE INDEX idx_feedback_user ON public.knowledge_feedback USING btree (user_id)
  ```
- **knowledge_feedback_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX knowledge_feedback_pkey ON public.knowledge_feedback USING btree (id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **FK**: `knowledge_item_id` → `knowledge_items.id`
- **PK**: `id`

#### Triggers

*No triggers*

---

### `knowledge_items`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | ✗ | nextval('knowledge_items_id_seq'::reg... |
| title | character varying | ✗ |  |
| content | text | ✓ |  |
| category | character varying | ✗ |  |
| subcategory | character varying | ✓ |  |
| source | character varying | ✗ |  |
| source_url | character varying | ✓ |  |
| source_id | character varying | ✓ |  |
| language | character varying | ✗ |  |
| content_type | character varying | ✗ |  |
| tags | json | ✓ |  |
| search_vector | tsvector | ✓ |  |
| relevance_score | double precision | ✗ |  |
| view_count | integer | ✗ |  |
| last_accessed | timestamp without time zone | ✓ |  |
| accuracy_score | double precision | ✓ |  |
| user_feedback_score | double precision | ✓ |  |
| feedback_count | integer | ✗ |  |
| related_items | json | ✓ |  |
| legal_references | json | ✓ |  |
| status | character varying | ✗ |  |
| version | character varying | ✗ |  |
| created_at | timestamp without time zone | ✗ |  |
| updated_at | timestamp without time zone | ✗ |  |
| reviewed_at | timestamp without time zone | ✓ |  |
| extra_metadata | json | ✓ |  |

#### Indexes

- **idx_knowledge_access** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_access ON public.knowledge_items USING btree (last_accessed)
  ```
- **idx_knowledge_category** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_category ON public.knowledge_items USING btree (category, subcategory)
  ```
- **idx_knowledge_category_relevance** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_category_relevance ON public.knowledge_items USING btree (category, relevance_score)
  ```
- **idx_knowledge_language** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_language ON public.knowledge_items USING btree (language)
  ```
- **idx_knowledge_relevance** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_relevance ON public.knowledge_items USING btree (relevance_score)
  ```
- **idx_knowledge_source** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_source ON public.knowledge_items USING btree (source)
  ```
- **idx_knowledge_status** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_status ON public.knowledge_items USING btree (status)
  ```
- **idx_knowledge_status_updated** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_status_updated ON public.knowledge_items USING btree (status, updated_at)
  ```
- **idx_knowledge_title** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_title ON public.knowledge_items USING btree (title)
  ```
- **idx_knowledge_updated** (BTREE)
  ```sql
  CREATE INDEX idx_knowledge_updated ON public.knowledge_items USING btree (updated_at)
  ```
- **knowledge_items_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX knowledge_items_pkey ON public.knowledge_items USING btree (id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

*No triggers*

#### Full-Text Search

- **TSVector column**: `search_vector`
  - ⚠️ **Missing GIN index** (recommended for FTS performance)
  - ⚠️ **Missing auto-update trigger** (tsvector may not be maintained)

#### Sample Data (3 rows)

```json
[
  {
    "id": 1,
    "title": "Circolare Test n. 1/T del 09 settembre 2025",
    "content": "Questa \u00e8 una circolare di test per verificare il funzionamento del sistema di ricerca italiano. Include termini come IVA, imposte, detrazioni fiscali e normative tributarie.",
    "category": "test_agenzia_entrate",
    "subcategory": "circolari",
    "source": "test",
    "source_url": "https://test.example.com/circolare-test.pdf",
    "source_id": null,
    "language": "it",
    "content_type": "text",
    "relevance_score": 0.8,
    "view_count": 0,
    "last_accessed": null,
    "accuracy_score": null,
    "user_feedback_score": null,
    "feedback_count": 0,
    "status": "active",
    "version": "1.0",
    "created_at": "2025-09-09 13:14:12.449840",
    "updated_at": "2025-09-09 13:14:12.449872",
    "reviewed_at": null
  },
  {
    "id": 2,
    "title": "Tardiva registrazione dei contratti di locazione e sublocazione di immobili urbani di durata pluriennale soggetti a imposta di registro - Determinazione della sanzione - Articolo 69 del Testo unico de",
    "category": "tax_guide",
    "subcategory": "documenti",
    "source": "regulatory_update",
    "source_url": "https://www.agenziaentrate.gov.it/portale/documents/20143/8413112/Sanzione_Tardiva_Registrazione_Locazione_Risoluzione+n.+56+del+13+ottobre+2015/f285985c-6cf0-94b2-cca0-96a114eff280",
    "source_id": null,
    "language": "it",
    "content_type": "text",
    "search_vector": null,
    "relevance_score": 1.0,
    "view_count": 0,
    "last_accessed": null,
    "accuracy_score": null,
    "user_feedback_score": null,
    "feedback_count": 0,
    "status": "active",
    "version": "1.0",
    "created_at": "2025-11-03 09:38:39.724204",
    "updated_at": "2025-11-03 09:38:39.724273",
    "reviewed_at": null
  },
  {
    "id": 3,
    "title": "Adempimento collaborativo: patti chiari, per imprese forti. Si chiude a Milano il roadshow di Confindustria, Mef e Agenzia Entrate . In Lombardia pi\u00f9 di 4.300 aziende potenzialmente interessate (comun",
    "category": "agenzia_entrate_circolari",
    "subcategory": "documenti",
    "source": "regulatory_update",
    "source_url": "https://www.agenziaentrate.gov.it/portale/cs-29-settembre",
    "source_id": null,
    "language": "it",
    "content_type": "text",
    "search_vector": null,
    "relevance_score": 0.9500000000000001,
    "view_count": 0,
    "last_accessed": null,
    "accuracy_score": null,
    "user_feedback_score": null,
    "feedback_count": 0,
    "status": "active",
    "version": "1.0",
    "created_at": "2025-11-03 09:38:39.824370",
    "updated_at": "2025-11-03 09:38:39.824453",
    "reviewed_at": null
  }
]
```

---

### `regulatory_documents`

#### Columns

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | character varying | ✗ |  |
| source | character varying | ✗ |  |
| source_type | character varying | ✗ |  |
| title | text | ✗ |  |
| url | text | ✗ |  |
| published_date | timestamp with time zone | ✓ |  |
| content | text | ✗ |  |
| content_hash | character varying | ✗ |  |
| document_number | character varying | ✓ |  |
| authority | character varying | ✓ |  |
| document_metadata | json | ✓ |  |
| version | integer | ✗ |  |
| previous_version_id | character varying | ✓ |  |
| status | character varying | ✗ |  |
| processed_at | timestamp with time zone | ✓ |  |
| processing_errors | text | ✓ |  |
| knowledge_item_id | integer | ✓ |  |
| topics | text | ✓ |  |
| importance_score | double precision | ✗ |  |
| created_at | timestamp with time zone | ✗ | now() |
| updated_at | timestamp with time zone | ✗ | now() |
| archived_at | timestamp with time zone | ✓ |  |
| archive_reason | text | ✓ |  |

#### Indexes

- **idx_regulatory_documents_content_hash** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_content_hash ON public.regulatory_documents USING btree (content_hash)
  ```
- **idx_regulatory_documents_created_at** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_created_at ON public.regulatory_documents USING btree (created_at)
  ```
- **idx_regulatory_documents_published_date** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_published_date ON public.regulatory_documents USING btree (published_date)
  ```
- **idx_regulatory_documents_source** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_source ON public.regulatory_documents USING btree (source)
  ```
- **idx_regulatory_documents_source_status** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_source_status ON public.regulatory_documents USING btree (source, status)
  ```
- **idx_regulatory_documents_source_type** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_source_type ON public.regulatory_documents USING btree (source_type)
  ```
- **idx_regulatory_documents_status** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_status ON public.regulatory_documents USING btree (status)
  ```
- **idx_regulatory_documents_status_published** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_status_published ON public.regulatory_documents USING btree (status, published_date)
  ```
- **idx_regulatory_documents_updated_at** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_updated_at ON public.regulatory_documents USING btree (updated_at)
  ```
- **idx_regulatory_documents_url** (BTREE)
  ```sql
  CREATE INDEX idx_regulatory_documents_url ON public.regulatory_documents USING btree (url)
  ```
- **idx_regulatory_documents_url_unique** (BTREE)
  ```sql
  CREATE UNIQUE INDEX idx_regulatory_documents_url_unique ON public.regulatory_documents USING btree (url)
  ```
- **regulatory_documents_pkey** (BTREE)
  ```sql
  CREATE UNIQUE INDEX regulatory_documents_pkey ON public.regulatory_documents USING btree (id)
  ```

#### Constraints

- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **CHECK**: ``
- **PK**: `id`

#### Triggers

- **update_regulatory_documents_updated_at_trigger**: BEFORE UPDATE
  - Action: `EXECUTE FUNCTION update_regulatory_documents_updated_at()`

---

## Trigger Functions

### `public.update_document_collections_updated_at`

```sql
CREATE OR REPLACE FUNCTION public.update_document_collections_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $function$

```

### `public.update_feed_status_updated_at`

```sql
CREATE OR REPLACE FUNCTION public.update_feed_status_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $function$

```

### `public.update_regulatory_documents_updated_at`

```sql
CREATE OR REPLACE FUNCTION public.update_regulatory_documents_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $function$

```

## Summary & Recommendations

### Issues Found

- ⚠️ **1 tsvector column(s) missing GIN index**
- ⚠️ **1 tsvector column(s) missing auto-update trigger**
- ℹ️ No vector embeddings found (pgvector not installed)

### Recommendations

1. **Add GIN indexes** to tsvector columns for efficient full-text search
   ```sql
   CREATE INDEX idx_knowledge_items_search_vector_gin ON knowledge_items USING gin(search_vector);
   ```

2. **Add triggers** to automatically maintain tsvector columns

3. **Consider installing pgvector** for semantic search capabilities
   ```sql
   CREATE EXTENSION vector;
   ```

---

## Database Queries for Manual Inspection

### View All RSS Feed Sources
```sql
SELECT
    id,
    source,
    feed_type,
    enabled,
    feed_url,
    status,
    last_success,
    items_found
FROM feed_status
ORDER BY id;
```

### View Documents by Source (News vs Normativa)
```sql
-- News documents
SELECT
    id,
    title,
    source,
    category,
    subcategory,
    created_at
FROM knowledge_items
WHERE source = 'agenzia_entrate_news'
ORDER BY created_at DESC
LIMIT 10;

-- Normativa documents
SELECT
    id,
    title,
    source,
    category,
    subcategory,
    created_at
FROM knowledge_items
WHERE source = 'agenzia_entrate_normativa'
ORDER BY created_at DESC
LIMIT 10;
```

### View Document Chunks with Quality Metrics
```sql
SELECT
    kc.id,
    ki.title AS document_title,
    ki.source,
    kc.chunk_index,
    kc.token_count,
    kc.quality_score,
    kc.junk,
    kc.ocr_used,
    LEFT(kc.chunk_text, 100) AS preview
FROM knowledge_chunks kc
JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
ORDER BY ki.created_at DESC, kc.chunk_index
LIMIT 20;
```

### View Hybrid Retrieval Test
```sql
-- Test FTS (Full-Text Search)
SELECT
    ki.title,
    kc.chunk_index,
    ts_rank_cd(kc.search_vector, websearch_to_tsquery('italian', 'IVA detrazioni')) AS fts_score,
    LEFT(kc.chunk_text, 150) AS preview
FROM knowledge_chunks kc
JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
WHERE kc.search_vector @@ websearch_to_tsquery('italian', 'IVA detrazioni')
  AND kc.junk = FALSE
ORDER BY fts_score DESC
LIMIT 10;
```

### View Document Ingestion Statistics
```sql
SELECT
    source,
    COUNT(*) AS document_count,
    SUM((SELECT COUNT(*) FROM knowledge_chunks WHERE knowledge_item_id = knowledge_items.id)) AS total_chunks,
    AVG((SELECT AVG(quality_score) FROM knowledge_chunks WHERE knowledge_item_id = knowledge_items.id)) AS avg_quality,
    MAX(created_at) AS last_ingested
FROM knowledge_items
GROUP BY source
ORDER BY document_count DESC;
```

### View Feed Health Status
```sql
SELECT
    source,
    feed_type,
    status,
    last_success,
    items_found,
    errors,
    consecutive_errors,
    EXTRACT(EPOCH FROM (NOW() - last_success))/3600 AS hours_since_last_success
FROM feed_status
WHERE enabled = TRUE
ORDER BY last_success DESC;
```

### View Scheduler Activity (from logs)
```bash
# Docker logs showing scheduler activity
docker-compose logs app | grep -E "(rss_feeds_4h|Scheduler|RSS)" | tail -50

# Expected patterns:
# - "Added scheduled task: rss_feeds_4h (4_hours)"
# - "Scheduler started"
# - "rss_feed_collection_task_started"
# - "rss_feed_collection_feed_completed"
```

### Verify pgvector Installation
```sql
-- Check pgvector extension
SELECT
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname = 'vector';

-- Check vector columns exist
SELECT
    table_name,
    column_name,
    udt_name
FROM information_schema.columns
WHERE udt_name = 'vector'
ORDER BY table_name, column_name;

-- Expected output:
-- knowledge_items.embedding (vector)
-- knowledge_chunks.embedding (vector)
```

### View Index Usage Statistics
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename IN ('knowledge_items', 'knowledge_chunks')
ORDER BY idx_scan DESC;
```

### View Context Formatting Test
```sql
-- Retrieve documents as they appear in RAG context
SELECT
    CASE
        WHEN ki.source = 'agenzia_entrate_news' THEN '[NEWS - AGENZIAENTRATE]'
        WHEN ki.source = 'agenzia_entrate_normativa' THEN '[NORMATIVA/PRASSI - AGENZIAENTRATE]'
        ELSE '[' || UPPER(ki.source) || ']'
    END AS doc_type_label,
    ki.title,
    kc.chunk_index,
    LEFT(kc.chunk_text, 200) AS preview,
    '📎 Source link: ' || kc.source_url AS source_link
FROM knowledge_chunks kc
JOIN knowledge_items ki ON kc.knowledge_item_id = ki.id
WHERE kc.junk = FALSE
ORDER BY ki.created_at DESC
LIMIT 10;
```

---

## Quick Diagnostics

### Check Feed Status
```bash
# Check all feeds
psql $POSTGRES_URL -c "SELECT id, source, feed_type, status, last_success FROM feed_status;"

# Check enabled feeds only
psql $POSTGRES_URL -c "SELECT id, source, feed_type, enabled, items_found FROM feed_status WHERE enabled = TRUE;"
```

### Check Recent Documents
```bash
# Recent documents by source
psql $POSTGRES_URL -c "SELECT source, COUNT(*) FROM knowledge_items GROUP BY source ORDER BY COUNT(*) DESC;"

# Recent chunks quality
psql $POSTGRES_URL -c "SELECT COUNT(*) as total_chunks, COUNT(*) FILTER (WHERE junk) as junk_chunks, AVG(quality_score) as avg_quality FROM knowledge_chunks;"
```

### Check Scheduler Status
```bash
# From Docker logs
docker-compose logs app --tail=100 | grep -E "(rss_feeds_4h|Scheduler)"

# From PostgreSQL (if you log task executions to DB)
# This would require a scheduler_logs table - not currently implemented
```
