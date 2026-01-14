# ADR-023: Tiered Document Ingestion System

## Status

Accepted

## Date

2026-01-09

## Context

PratikoAI needs to properly handle critical Italian legal documents like Legge di Bilancio, which can exceed 500 pages. The current flat chunking approach has several problems:

1. **Lost Document Structure**: Article boundaries, Titoli, and Capi are lost during chunking
2. **Context Fragmentation**: Related content spread across disconnected chunks
3. **Poor Retrieval for Critical Laws**: Search returns generic headers/TOC instead of relevant articles
4. **LLM Hallucination**: Without proper context, LLM falls back to training data with outdated information

### Current State Problem

```
Legge 199/2025 (500+ pages)
    ↓ Current Ingestion
[Chunk 1: Header/TOC] [Chunk 2: Random section] [Chunk 3: ...]
    ↓ Search for "rottamazione"
❌ Returns: Generic header chunk without actual article content
❌ LLM hallucinates: "30 giugno 2022" (old rottamazione quater dates)
```

### Specific Issue (DEV-242)

When users ask about "rottamazione quinquies" (from Legge di Bilancio 2026), the system:
1. Correctly identifies the document reference via ADR-022
2. Finds chunks in the database
3. But returns only header/TOC content without the actual rottamazione article
4. LLM falls back to training data, providing outdated dates

## Decision

Implement a **three-tier document ingestion system** that classifies documents by importance and applies appropriate parsing strategies:

### Tier Classification

| Tier | Name | Documents | Parsing Strategy |
|------|------|-----------|------------------|
| **1** | CRITICAL | Leggi, Decreti, DPR, Codici | Article-level parsing with topic tagging |
| **2** | IMPORTANT | Circolari, Interpelli, Risoluzioni | Standard chunking with metadata |
| **3** | REFERENCE | News, Comunicati, FAQ | Light indexing (truncated) |

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TIERED DOCUMENT INGESTION SYSTEM                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    DocumentClassifier                             │   │
│  │  • Pattern matching (regex + explicit list)                       │   │
│  │  • Source-based classification                                    │   │
│  │  • Topic detection from content                                   │   │
│  │  • Confidence scoring                                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│              ┌───────────────┼───────────────┐                          │
│              ▼               ▼               ▼                          │
│       ┌──────────┐    ┌──────────┐    ┌──────────┐                     │
│       │  TIER 1  │    │  TIER 2  │    │  TIER 3  │                     │
│       │ CRITICAL │    │ IMPORTANT│    │REFERENCE │                     │
│       ├──────────┤    ├──────────┤    ├──────────┤                     │
│       │ Article- │    │ Standard │    │  Light   │                     │
│       │  Level   │    │ Chunking │    │ Indexing │                     │
│       │ Parsing  │    │          │    │          │                     │
│       └──────────┘    └──────────┘    └──────────┘                     │
│              │               │               │                          │
│              └───────────────┼───────────────┘                          │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    TieredIngestionService                         │   │
│  │  • Orchestrates classification and parsing                        │   │
│  │  • Hierarchical storage (parent-child)                           │   │
│  │  • Topic tagging                                                  │   │
│  │  • Database commit                                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Database Schema Extensions

New fields added to `knowledge_items`:

| Field | Type | Description |
|-------|------|-------------|
| `tier` | Integer | 1=CRITICAL, 2=IMPORTANT, 3=REFERENCE |
| `parent_document_id` | Integer FK | Parent document for hierarchical storage |
| `article_number` | String(50) | Article identifier (e.g., "Art. 1") |
| `topics` | Text[] | Topic tags for enhanced search |
| `document_type` | String(50) | "full_document", "article", "chunk", "allegato" |
| `parsing_metadata` | JSONB | Cross-references, commi count, etc. |

### Tier 1: Article-Level Parsing

For critical legal documents, the `ItalianLawParser` extracts:

- **Articles**: Art. 1, Art. 2, Art. 2-bis, etc.
- **Commi**: Numbered paragraphs within articles
- **Cross-references**: "comma 3 dell'articolo 12"
- **Structure**: Titoli, Capi hierarchy
- **Topics**: Automatic tagging based on keywords

Storage pattern:
```
knowledge_items:
  [id=1] LEGGE 199/2025 (full_document, parent)
    ├── [id=2] Art. 1 - IRPEF (article, topics=[irpef])
    ├── [id=3] Art. 2 - Rottamazione (article, topics=[rottamazione])
    ├── [id=4] Art. 3 - Bonus (article, topics=[bonus])
    └── [id=5] Allegato A (allegato)
```

### Tier 2: Standard Chunking

For circulars and guidance, existing chunking with:
- 1500 character chunks with 150 overlap
- Sentence/paragraph boundary awareness
- Topic tagging preserved

### Tier 3: Light Indexing

For news and reference material:
- Single record with first 5000 characters
- Minimal metadata

## Consequences

### Positive

1. **Better Retrieval for Critical Laws**: Article-level search returns complete, relevant content
2. **Citable Responses**: LLM can cite "Art. 2, comma 3 della Legge 199/2025"
3. **Topic-Based Search**: Filter by topics like "rottamazione", "irpef"
4. **Hierarchical Navigation**: Parent-child relationships enable context expansion
5. **Reduced Hallucination**: Correct dates and details from actual article content

### Negative

1. **Increased Storage**: Article-level parsing creates more records per document
2. **Ingestion Complexity**: More complex parsing logic to maintain
3. **Re-ingestion Required**: Critical documents need re-processing

### Neutral

1. **Classification Rules**: YAML-based rules need periodic updates for new document types
2. **Backward Compatibility**: Existing chunks default to Tier 2

## Implementation

### Files Created

| File | Purpose |
|------|---------|
| `config/document_tiers.yaml` | Classification rules and topic keywords |
| `app/services/document_classifier.py` | DocumentClassifier service |
| `app/services/italian_law_parser.py` | ItalianLawParser service |
| `app/services/tiered_ingestion_service.py` | TieredIngestionService |
| `alembic/versions/20260109_add_tiered_document_ingestion.py` | Database migration |
| `scripts/reingest_critical_law.py` | Re-ingestion utility |

### Files Modified

| File | Change |
|------|--------|
| `app/models/knowledge.py` | Added tier, topics, parent_document_id, etc. |

### Usage Example

```python
from app.services.tiered_ingestion_service import TieredIngestionService
from app.models.database import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    service = TieredIngestionService(db_session=db)

    result = await service.ingest(
        title="LEGGE 30 dicembre 2025, n. 199",
        content=law_content,
        source="gazzetta_ufficiale",
        publication_date="2025-12-30",
    )

    print(f"Tier: {result.tier}")  # 1 (CRITICAL)
    print(f"Articles: {result.articles_parsed}")  # e.g., 200
    print(f"Topics: {result.topics_detected}")  # ['rottamazione', 'irpef', ...]
```

## Related

- **DEV-242**: Response Quality & Suggested Actions Fixes
- **ADR-022**: LLM-Based Document Identification
- **Section 13.7**: Hybrid RAG Architecture
