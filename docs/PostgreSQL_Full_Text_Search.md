# PostgreSQL Full-Text Search Implementation

This document provides comprehensive information about the PostgreSQL Full-Text Search (FTS) implementation for PratikoAI knowledge base.

## Overview

PostgreSQL Full-Text Search provides efficient, language-aware text search capabilities with:
- Italian language support with proper stemming
- Accent-insensitive search
- Partial word matching
- Result ranking with `ts_rank`
- High performance with GIN indexes
- Automatic search vector updates via triggers

## Architecture

### Database Layer
- **search_vector column**: `tsvector` type for indexed text search
- **GIN Index**: Fast full-text search performance
- **Trigger Function**: Automatic search vector updates
- **Italian Configuration**: Language-specific text processing

### Service Layer
- **SearchService**: Core search functionality with caching
- **Result Ranking**: `ts_rank` scoring with relevance weights
- **Query Normalization**: Italian text preprocessing
- **Cache Integration**: Redis caching for performance

### API Layer
- **REST Endpoints**: `/api/v1/search/knowledge`
- **Pagination Support**: Offset/limit with performance optimization
- **Filtering**: Category, source, and language filters
- **Feedback System**: User rating and improvement tracking

## Usage Examples

### Basic Search

```bash
# Search for tax information
GET /api/v1/search/knowledge?q=dichiarazione redditi

# Search with category filter
GET /api/v1/search/knowledge?q=IVA&category=tax_guide

# Paginated search
GET /api/v1/search/knowledge?q=fattura elettronica&limit=10&offset=20
```

### Advanced Search Features

```bash
# Accent-insensitive search (both return same results)
GET /api/v1/search/knowledge?q=società
GET /api/v1/search/knowledge?q=societa

# Partial word matching
GET /api/v1/search/knowledge?q=fattur  # Matches "fattura", "fatturazione"

# Minimum relevance threshold
GET /api/v1/search/knowledge?q=codice fiscale&min_relevance=0.1
```

### Search Suggestions

```bash
# Get autocomplete suggestions
GET /api/v1/search/knowledge/suggestions?q=fattu&limit=5

# Response:
{
  "query": "fattu",
  "suggestions": ["fattura", "fatturazione", "fatturare"],
  "count": 3
}
```

## Query Syntax

### Basic Queries
- **Simple terms**: `dichiarazione redditi`
- **Phrases**: `"fattura elettronica"`
- **Multiple words**: `IVA società limitata`

### Italian Language Support
- **Stemming**: `fattura` matches `fatture`, `fatturazione`
- **Accents**: `società` matches `societa` 
- **Articles**: `il`, `la`, `dei` are handled as stop words
- **Conjugations**: Verb forms are reduced to stems

### Performance Considerations

#### Optimal Query Patterns
```sql
-- Fast: Uses GIN index effectively
SELECT * FROM knowledge_items 
WHERE search_vector @@ websearch_to_tsquery('italian', 'fattura elettronica');

-- Slower: Full table scan
SELECT * FROM knowledge_items 
WHERE content ILIKE '%fattura elettronica%';
```

#### Index Usage
- **GIN Index**: Provides sub-second search on 100k+ documents
- **Prefix Matching**: Supported via `:*` operator
- **Rank Ordering**: `ts_rank` calculation is fast with proper indexes

## Performance Benchmarks

### Search Performance Targets
- **< 100ms**: Search response time for 10,000 records
- **< 200ms**: Search with complex filters and ranking
- **< 50ms**: Cached search results
- **99.9% uptime**: Service availability target

### Optimization Techniques

#### 1. Query Optimization
```python
# Optimized query with minimal rank calculation
query = text("""
    SELECT id, title, content, category, 
           ts_rank(search_vector, query, 32) as rank
    FROM knowledge_items, 
         websearch_to_tsquery('italian', :search_term) query
    WHERE search_vector @@ query
    ORDER BY rank DESC
    LIMIT :limit
""")
```

#### 2. Caching Strategy
```python
# Multi-level caching
cache_key = f"search:{normalized_query}:{category}:{limit}:{offset}"
cached_results = await redis.get(cache_key)
if cached_results:
    return cached_results
```

#### 3. Index Maintenance
```sql
-- Monitor index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes 
WHERE tablename = 'knowledge_items';

-- Rebuild index if needed (rarely required)
REINDEX INDEX idx_knowledge_items_search_vector;
```

## API Reference

### Search Knowledge Base

**Endpoint**: `GET /api/v1/search/knowledge`

**Parameters**:
- `q` (required): Search query string (1-500 chars)
- `category` (optional): Filter by knowledge category
- `subcategory` (optional): Filter by subcategory
- `source` (optional): Filter by source type
- `language` (optional): Search language (default: "it")
- `limit` (optional): Results per page (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)
- `min_relevance` (optional): Minimum ts_rank score (0.0-1.0, default: 0.01)

**Response**:
```json
{
  "query": "dichiarazione redditi",
  "results": [
    {
      "id": "123",
      "title": "Guida alla dichiarazione dei redditi 2024",
      "content": "La dichiarazione dei redditi deve essere presentata...",
      "category": "tax_guide",
      "source": "official_docs",
      "rank_score": 0.8742,
      "relevance_score": 0.9,
      "highlight": "La <b>dichiarazione</b> dei <b>redditi</b> deve essere...",
      "updated_at": "2024-08-04T10:30:00Z"
    }
  ],
  "total_count": 15,
  "page_size": 20,
  "page": 1,
  "search_time_ms": 45.2,
  "suggestions": ["dichiarazione unica", "redditi società"]
}
```

### Get Search Suggestions

**Endpoint**: `GET /api/v1/search/knowledge/suggestions`

**Parameters**:
- `q` (required): Partial query (2-100 chars)
- `limit` (optional): Max suggestions (1-20, default: 5)

### Submit Feedback

**Endpoint**: `POST /api/v1/search/knowledge/feedback`

**Parameters**:
- `knowledge_item_id` (required): Item ID
- `rating` (required): Rating 1-5
- `feedback_text` (optional): Text feedback
- `feedback_type` (required): helpful|accurate|outdated|incorrect
- `search_query` (optional): Original search query

### Get Categories

**Endpoint**: `GET /api/v1/search/knowledge/categories`

Returns available categories and their document counts.

## Administration

### Reindex Search Vectors

**Endpoint**: `POST /api/v1/search/knowledge/admin/reindex`

Manually update search vectors (typically not needed due to triggers):

```bash
# Reindex specific items
POST /api/v1/search/knowledge/admin/reindex
{
  "knowledge_ids": [1, 2, 3]
}

# Reindex all items
POST /api/v1/search/knowledge/admin/reindex
```

### Clear Search Cache

**Endpoint**: `DELETE /api/v1/search/knowledge/admin/cache`

Clears all search-related cache entries.

## Database Schema

### Knowledge Items Table

```sql
CREATE TABLE knowledge_items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    source VARCHAR(100) NOT NULL,
    search_vector TSVECTOR,
    relevance_score REAL DEFAULT 0.5,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Search indexes
CREATE INDEX idx_knowledge_items_search_vector 
ON knowledge_items USING gin(search_vector);

CREATE INDEX idx_knowledge_items_category_search 
ON knowledge_items USING gin(category, search_vector);
```

### Search Vector Trigger

```sql
CREATE OR REPLACE FUNCTION update_knowledge_search_vector() 
RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('italian', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('italian', COALESCE(NEW.content, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_knowledge_search_vector_trigger
BEFORE INSERT OR UPDATE OF title, content
ON knowledge_items
FOR EACH ROW
EXECUTE FUNCTION update_knowledge_search_vector();
```

## Troubleshooting

### Common Issues

#### 1. Slow Search Performance
```sql
-- Check if indexes are being used
EXPLAIN ANALYZE 
SELECT * FROM knowledge_items 
WHERE search_vector @@ websearch_to_tsquery('italian', 'query');

-- Should show "Bitmap Index Scan on idx_knowledge_items_search_vector"
```

**Solutions**:
- Ensure GIN indexes exist and are up to date
- Check query complexity and consider simplification
- Monitor cache hit rates and increase cache TTL if needed

#### 2. No Search Results
**Possible causes**:
- Search vector not populated (check trigger function)
- Invalid Italian text configuration
- Minimum relevance threshold too high

**Debug queries**:
```sql
-- Check if search vectors exist
SELECT id, title, search_vector IS NOT NULL as has_vector 
FROM knowledge_items LIMIT 10;

-- Test text search configuration
SELECT to_tsvector('italian', 'fattura elettronica società');

-- Check trigger function exists
SELECT proname FROM pg_proc WHERE proname = 'update_knowledge_search_vector';
```

#### 3. Italian Language Issues
```sql
-- Verify Italian configuration
SELECT cfgname FROM pg_ts_config WHERE cfgname = 'italian';

-- Test stemming and stop words
SELECT to_tsvector('italian', 'le fatture elettroniche delle società');
-- Should reduce words to stems and remove stop words
```

### Performance Monitoring

#### Key Metrics to Track
- Search response time (target < 100ms)
- Cache hit rate (target > 80%)
- Index scan vs sequential scan ratio
- Search result relevance scores
- User feedback ratings

#### Monitoring Queries
```sql
-- Index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'knowledge_items';

-- Search vector coverage
SELECT 
    COUNT(*) as total_items,
    COUNT(search_vector) as indexed_items,
    (COUNT(search_vector)::float / COUNT(*) * 100) as coverage_pct
FROM knowledge_items;
```

## Future Enhancements

### Planned Features
1. **Multi-language Support**: Add English and other European languages
2. **Semantic Search Integration**: Hybrid FTS + vector similarity
3. **Advanced Filters**: Date ranges, author, document type
4. **Search Analytics**: User behavior tracking and optimization
5. **AI-Powered Suggestions**: ML-based query expansion

### Performance Improvements
1. **Parallel Search**: Multi-threaded search for large datasets
2. **Incremental Indexing**: Real-time updates for new content
3. **Distributed Search**: Sharding for very large knowledge bases
4. **Caching Optimization**: Predictive caching based on user patterns

## Migration and Deployment

### Running the Migration

```bash
# Apply the FTS migration
alembic upgrade head

# Verify migration success
psql -d your_db -c "\d knowledge_items" | grep search_vector
```

### Post-Migration Steps

1. **Populate Search Vectors**:
```sql
UPDATE knowledge_items 
SET search_vector = 
    setweight(to_tsvector('italian', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('italian', COALESCE(content, '')), 'B')
WHERE search_vector IS NULL;
```

2. **Verify Index Creation**:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'knowledge_items' 
AND indexdef LIKE '%gin%';
```

3. **Test Search Functionality**:
```bash
curl -X GET "http://localhost:8000/api/v1/search/knowledge?q=test"
```

This completes the PostgreSQL Full-Text Search implementation with comprehensive documentation, performance optimization, and troubleshooting guides.